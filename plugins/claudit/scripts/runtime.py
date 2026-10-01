#!/usr/bin/env python3
"""Claudit's local, standard-library runtime. No model calls or consumer config writes."""
import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid

DOMAINS = {
    'core-config': ('settings', 'settings-reference', 'permissions', 'memory'),
    'ecosystem': ('mcp', 'hooks', 'skills', 'sub-agents', 'plugins-reference', 'plugins/components', 'plugins/measure', 'plugins/mods/overview'),
    'optimization': ('model-config', 'cli-reference', 'best-practices', 'costs'),
}
TTL = dt.timedelta(days=7)


def now():
    return dt.datetime.now(dt.timezone.utc)


def stamp(value=None):
    return (value or now()).isoformat()


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be a string')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return parsed.astimezone(dt.timezone.utc)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.claudit-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0)
            if not stream.read(1):
                stream.write(b'0')
                stream.flush()
            deadline = time.monotonic() + 30
            while True:
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Cache lock busy; retry later')
                    time.sleep(0.05)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            deadline = time.monotonic() + 30
            while True:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Cache lock busy; retry later')
                    time.sleep(0.05)
            yield


def cache_root():
    return Path(os.environ.get('CLAUDIT_CACHE_DIR', str(Path.home() / '.cache/claudit'))).expanduser()


def version(value):
    match = re.search(r'\b\d+\.\d+\.\d+\b', value if isinstance(value, str) else '')
    if not match:
        raise ValueError('Cannot determine host version; pass the actual claude --version output')
    return match.group()


def validate_record(record, domain):
    if not isinstance(record, dict) or record.get('schema_version') != 2 or record.get('domain') != domain:
        raise ValueError('Invalid domain record')
    version(record.get('host_version'))
    parse_time(record.get('fetched_at'))
    claims, sources = record.get('claims'), record.get('sources')
    if not isinstance(claims, list) or not claims or not isinstance(sources, list) or not sources:
        raise ValueError('Missing claims/sources')
    ids = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get('url'), str) or not source['url'].startswith('https://code.claude.com/docs/en/'):
            raise ValueError('Invalid official source')
        if not isinstance(source.get('id'), str) or not isinstance(source.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
            raise ValueError('Invalid source identity')
        parse_time(source.get('fetched_at'))
        ids.add(source['id'])
    if ids != set(DOMAINS[domain]):
        raise ValueError('Missing source coverage')
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get('text'), str) or not claim['text'].strip() or not isinstance(claim.get('section'), str) or not claim['section']:
            raise ValueError('Invalid claim')
        if not isinstance(claim.get('source_ids'), list) or not claim['source_ids'] or not all(isinstance(i, str) for i in claim['source_ids']) or not set(claim['source_ids']) <= ids:
            raise ValueError('Invalid claim source')
    for field in ('gaps', 'limitations'):
        values = record.get(field, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f'Invalid {field}')
    if record.get('content_sha256') != digest(json.dumps(claims, sort_keys=True).encode()):
        raise ValueError('Claim integrity mismatch')


def domain_state(root, domain, host, instant=None):
    instant = instant or now()
    path = root / 'v2' / f'{domain}.json'
    result = {'domain': domain, 'state': 'missing', 'reasons': [], 'record': str(path)}
    try:
        record = read_json(path)
        validate_record(record, domain)
        for source in record['sources']:
            source_path = Path(source['content_path']).resolve()
            source_path.relative_to((root / 'v2/research').resolve())
            if not source_path.is_file():
                raise ValueError('Retained source missing')
            if digest(source_path.read_bytes()) != source['sha256']:
                raise ValueError('Retained source integrity mismatch')
        fetched = parse_time(record['fetched_at'])
        result.update(fetched_at=record['fetched_at'], host_version=record['host_version'], state='fresh',
                      limitations=record.get('limitations', []))
        if record['host_version'] != host:
            result['reasons'].append('host-version-changed')
        if instant - fetched >= TTL or fetched > instant + dt.timedelta(minutes=5):
            result['reasons'].append('source-expired-or-future')
        if record.get('gaps'):
            result['reasons'].append('incomplete-source-coverage')
        if result['reasons']:
            result['state'] = 'stale'
    except FileNotFoundError:
        if (root / f'{domain}.md').exists() or (root / 'manifest.json').exists():
            result.update(state='stale', reasons=['legacy-unverified-cache-preserved'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        result.update(state='corrupt', reasons=['invalid-record-or-content-integrity'])
    try:
        attempt = read_json(root / 'v2' / f'{domain}.attempt.json')
        if attempt['status'] == 'failed' and ('fetched_at' not in result or
                parse_time(attempt['at']) >= parse_time(result['fetched_at'])):
            result.update(state='degraded', last_failure=attempt['reason'])
    except FileNotFoundError:
        pass
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        result.update(state='degraded', last_failure='unreadable attempt receipt')
    return result


def fail(root, domain, reason):
    with locked(root / 'v2' / f'{domain}.lock'):
        atomic(root / 'v2' / f'{domain}.attempt.json', {'status': 'failed', 'at': stamp(), 'reason': reason})
    return {'domain': domain, 'status': 'failed', 'last_good_preserved': True}


def fetch(root, domain, host, opener=urllib.request.urlopen):
    """Fetch source bytes before research; never turn old model memory into evidence."""
    started = stamp()
    bundle_dir = root / 'v2' / 'research' / f'{domain}-{uuid.uuid4().hex}'
    bundle_dir.mkdir(parents=True, mode=0o700)
    sources, errors = [], []
    for page in DOMAINS[domain]:
        url = f'https://code.claude.com/docs/en/{page}.md'
        try:
            with opener(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; Claudit/3.1)' }), timeout=30) as response:
                final = response.geturl()
                if not final.startswith('https://code.claude.com/docs/en/'):
                    raise ValueError('unexpected redirect outside official docs')
                data = response.read(2_000_001)
                if not data or len(data) > 2_000_000:
                    raise ValueError('empty or oversized source')
                content = data.decode('utf-8')
                if '<html' in content[:1000].lower() or not re.search(r'^# ', content, re.MULTILINE):
                    raise ValueError('expected official Markdown, not HTML/error response')
                source_path = bundle_dir / (page.replace('/', '_') + '.md')
                source_path.write_bytes(data)
                sources.append({'id': page, 'url': final, 'fetched_at': stamp(),
                                'sha256': digest(data), 'content_path': str(source_path)})
        except Exception as exc:
            errors.append({'source': page, 'error': type(exc).__name__})
    if errors:
        fail(root, domain, 'official-source-fetch-failed: ' + ', '.join(e['source'] for e in errors))
    bundle = {'schema_version': 2, 'domain': domain, 'host_version': host,
              'fetched_at': started, 'sources': sources, 'errors': errors}
    path = bundle_dir / 'bundle.json'
    atomic(path, bundle)
    return {'bundle': str(path), 'research_output': str(bundle_dir / 'synthesis.json'),
            'fetched': len(sources), 'errors': errors,
            'commit_allowed': not errors}


def commit_cache(root, bundle_path, research_path):
    bundle_path = Path(bundle_path).resolve()
    bundle_path.relative_to((root / 'v2/research').resolve())
    expected_output = bundle_path.parent / 'synthesis.json'
    if Path(research_path).resolve() != expected_output:
        raise ValueError('Use the exact research_output path returned by fetch for this bundle')
    bundle, research = read_json(bundle_path), read_json(research_path)
    domain = bundle['domain']
    if domain not in DOMAINS or bundle['errors']:
        raise ValueError('Partial fetch cannot replace last good research; report degraded evidence')
    if now() - parse_time(bundle['fetched_at']) >= TTL:
        raise ValueError('Research bundle expired')
    sources = {s['id']: s for s in bundle['sources']}
    if set(sources) != set(DOMAINS[domain]):
        raise ValueError('Incomplete source receipt')
    for source in sources.values():
        source_path = Path(source['content_path']).resolve()
        source_path.relative_to(bundle_path.parent)
        if digest(source_path.read_bytes()) != source['sha256']:
            raise ValueError('Fetched source changed since receipt')
    claims = research['claims']
    if not isinstance(claims, list) or not claims:
        raise ValueError('Research needs nonempty claims')
    used = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError('Invalid claim')
        if not isinstance(claim.get('text'), str) or not claim['text'].strip():
            raise ValueError('Empty claim')
        ids = claim.get('source_ids')
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids) or not set(ids) <= set(sources):
            raise ValueError('Every claim requires fetched source IDs')
        if not isinstance(claim.get('section'), str) or not claim['section']:
            raise ValueError('Every claim requires a source section to inspect')
        used.update(ids)
    if used != set(sources):
        raise ValueError('Research must cover every required source; record a failed attempt otherwise')
    gaps = research.get('gaps', [])
    if not isinstance(gaps, list) or not all(isinstance(value, str) for value in gaps) or gaps:
        raise ValueError('Fatal research gaps cannot replace last good cache')
    limitations = research.get('limitations', [])
    if not isinstance(limitations, list) or not all(isinstance(value, str) for value in limitations):
        raise ValueError('Research limitations must be a list of strings')
    record = {k: bundle[k] for k in ('schema_version', 'domain', 'host_version', 'fetched_at')}
    record.update(claims=claims, gaps=[], limitations=limitations, content_sha256=digest(json.dumps(claims, sort_keys=True).encode()),
                  sources=[{k: s[k] for k in ('id', 'url', 'fetched_at', 'sha256', 'content_path')} for s in sources.values()],
                  evidence_basis='official bytes fetched; semantic synthesis is model-authored, not mechanically verified')
    with locked(root / 'v2' / f'{domain}.lock'):
        target = root / 'v2' / f'{domain}.json'
        try:
            old = read_json(target)
            validate_record(old, domain)
            old_time = parse_time(old['fetched_at'])
            if old_time <= now() + dt.timedelta(minutes=5) and old_time > parse_time(record['fetched_at']):
                return {'status': 'superseded', 'domain': domain}
            # Preserve the previous bytes before every replacement, including corrupt data.
        except (FileNotFoundError, ValueError, KeyError, TypeError):
            pass
        if target.exists():
            backup = root / 'v2/history' / f'{domain}-{uuid.uuid4().hex}.json'
            backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            backup.write_bytes(target.read_bytes())
        atomic(target, record)
        atomic(root / 'v2' / f'{domain}.attempt.json', {'status': 'success', 'at': stamp()})
    return {'status': 'committed', 'domain': domain, 'record': str(target)}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


def file_state(path):
    try:
        if Path(path).absolute() != Path(path).resolve():
            return {'state': 'symlink', 'note': 'target not read; loading/trust requires scoped inspection'}
        content = Path(path).read_bytes()
        return {'state': 'present', 'bytes': len(content), 'lines': len(content.splitlines())}
    except FileNotFoundError:
        return {'state': 'missing'}
    except (PermissionError, OSError):
        return {'state': 'unreadable'}


def discover(cwd, home, config=None, managed=None, limit=200, scope='auto'):
    cwd, home = Path(cwd).resolve(), Path(home).resolve()
    config = Path(config or os.environ.get('CLAUDE_CONFIG_DIR', str(home / '.claude'))).expanduser().resolve()
    try:
        project = Path(git(cwd, 'rev-parse', '--show-toplevel'))
        common = Path(git(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        main = common.parent
        git_root = str(project)
    except subprocess.CalledProcessError:
        project = main = cwd
        git_root = None
    scope = ('comprehensive' if git_root else 'global') if scope == 'auto' else scope
    include_user, include_project = scope != 'project', scope != 'global'
    managed = Path(managed) if managed else Path('/Library/Application Support/ClaudeCode' if sys.platform == 'darwin' else '/etc/claude-code')
    files, seen, gaps, settings = [], set(), [], []

    def add(path, scope, kind, priority=0, note=None):
        path = Path(path)
        key = (str(path), kind, scope)
        if key in seen:
            return
        seen.add(key)
        entry = dict(path=str(path), scope=scope, kind=kind, priority=priority, **file_state(path))
        if note:
            entry['note'] = note
        files.append(entry)
        if kind == 'settings' and entry['state'] == 'present':
            try:
                value = read_json(path)
                if not isinstance(value, dict):
                    raise ValueError()
                settings.append((scope, path, value))
            except (ValueError, OSError):
                entry['state'] = 'corrupt'

    if include_user:
        add(config / 'settings.json', 'user', 'settings')
    if include_project:
        add(cwd / '.claude/settings.json', 'project', 'settings')
        if scope != 'project':
            add(cwd / '.claude/settings.local.json', 'local', 'settings')
    if include_project and scope != 'project' and main != cwd:
        add(main / '.claude/settings.local.json', 'local', 'settings', note='main worktree root; normally overrides cwd local settings on current POSIX host')
    for name in ('managed-settings.json', 'managed-mcp.json', 'CLAUDE.md'):
        add(managed / name, 'managed', 'settings' if name == 'managed-settings.json' else 'mcp' if name == 'managed-mcp.json' else 'instructions')
    for path in sorted((managed / 'managed-settings.d').glob('*.json')):
        add(path, 'managed', 'settings', note='managed drop-in; verify host merge/order')
    if include_user:
        add(config / 'CLAUDE.md', 'user', 'instructions')
    # Parent instructions apply even outside a git repository; children are conditional.
    for directory in reversed((cwd, *cwd.parents)) if include_project else []:
        if scope == 'project' and not directory.is_relative_to(project):
            continue
        for name in ('CLAUDE.md', 'CLAUDE.local.md', '.claude/CLAUDE.md', 'AGENTS.md'):
            if scope == 'project' and 'local' in name:
                continue
            add(directory / name, 'local' if 'local' in name else 'ancestor', 'instructions')
    bases = ([(config, 'user')] if include_user else []) + ([(cwd / '.claude', 'project')] if include_project else []) + [(managed / '.claude', 'managed')]
    for base, file_scope in bases:
        for folder, pattern, kind in (('rules', '*.md', 'rules'), ('skills', 'SKILL.md', 'skills'), ('agents', '*.md', 'agents'), ('commands', '*.md', 'commands')):
            for path in sorted((base / folder).rglob(pattern)):
                add(path, file_scope, kind, 1)
    # Never dump the host state/auth file. Expose only selected MCP metadata.
    state_path = config / '.claude.json' if config != home / '.claude' else home / '.claude.json'
    if include_user:
        add(state_path, 'personal', 'host-state', note='do not Read entire file; may contain authentication data')
    mcp = []
    def servers(value, scope, source):
        if value is None:
            return
        if not isinstance(value, dict):
            gaps.append(f'Invalid mcpServers object in {source}; {scope} MCP unknown')
            return
        for name, server in value.items():
            if not isinstance(server, dict):
                mcp.append({'name': name, 'scope': scope, 'source': str(source), 'state': 'invalid-object'})
                continue
            command = server.get('command')
            mcp.append({'name': name, 'scope': scope, 'source': str(source),
                        'transport': server.get('type', 'stdio' if command else 'unknown'),
                        'command': command if isinstance(command, str) and re.fullmatch(r'[\w./+@-]+', command) else None,
                        'argument_count': len(server.get('args', [])) if isinstance(server.get('args', []), list) else None,
                        'has_url': bool(server.get('url')), 'env_names': list(server['env']) if isinstance(server.get('env'), dict) else [],
                        'alwaysLoad': server.get('alwaysLoad', 'unspecified'),
                        'values_redacted': True})
    try:
        state = read_json(state_path) if include_user and file_state(state_path)['state'] == 'present' else {}
        servers(state.get('mcpServers'), 'user', state_path)
        for key in dict.fromkeys((str(cwd), str(project))) if include_project else []:
            servers(state.get('projects', {}).get(key, {}).get('mcpServers'), 'local', state_path)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, AttributeError, TypeError):
        gaps.append('Cannot parse personal MCP state; effective MCP unknown')
    for path, file_scope in ([(cwd / '.mcp.json', 'project')] if include_project else []) + [(managed / 'managed-mcp.json', 'managed')]:
        add(path, file_scope, 'mcp')
        try:
            if file_state(path)['state'] == 'present':
                servers(read_json(path).get('mcpServers'), file_scope, path)
            elif file_state(path)['state'] != 'missing':
                gaps.append(f'MCP source not read: {path}')
        except FileNotFoundError:
            pass
        except (OSError, ValueError, AttributeError, TypeError):
            gaps.append(f'Cannot parse MCP source: {path}')
    plugins = []
    registry = config / 'plugins/installed_plugins.json'
    if include_user:
        add(registry, 'personal', 'plugins')
        add(config / 'plugins/known_marketplaces.json', 'personal', 'marketplaces')
    try:
        installed = read_json(registry).get('plugins', {}) if include_user and file_state(registry)['state'] == 'present' else {}
        for name, entries in installed.items():
            for entry in entries if isinstance(entries, list) else [entries]:
                if not include_project and (entry.get('scope') in ('project', 'local') or entry.get('projectPath')):
                    continue
                if entry.get('projectPath') and Path(entry['projectPath']).resolve() not in (cwd, project, main):
                    continue
                root = Path(entry['installPath'])
                manifest_path = root / '.claude-plugin/plugin.json'
                add(manifest_path, 'plugin', 'plugin-manifest')
                components = plugin_components(root)
                plugins.append({'name': name, 'scope': entry.get('scope', 'unknown'), 'root': str(root),
                                'version': entry.get('version'), 'exists': root.is_dir(), 'components': components})
                for component in components:
                    if 'path' in component and component.get('contained'):
                        path = Path(component['path'])
                        if path.is_file():
                            add(path, 'plugin', component['kind'], 1)
                        elif path.is_dir() and component.get('contained'):
                            for member in sorted(path.rglob('*.md')):
                                if not member.resolve().is_relative_to(root.resolve()):
                                    gaps.append('Plugin member resolves outside install root; not read')
                                    continue
                                add(member, 'plugin', component['kind'], 2)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        gaps.append('Plugin registry unreadable or unsupported; inventory incomplete')
    override = None
    for file_scope, path, value in settings:
        if 'autoMemoryDirectory' in value:
            override = str(value['autoMemoryDirectory'])
    project_key = os.environ.get('CLAUDE_CODE_PROJECT_DIR_NAME') if os.environ.get('CLAUDE_CONFIG_DIR') else None
    project_key = project_key or re.sub(r'[^a-zA-Z0-9]', '-', str(main))
    memory = Path(override.replace('~/', str(home) + '/', 1)) if override else config / 'projects' / project_key / 'memory'
    if not memory.is_absolute():
        gaps.append('Invalid relative autoMemoryDirectory; effective memory unknown')
    elif include_user and include_project:
        add(memory / 'MEMORY.md', 'personal', 'auto-memory', note='candidate; confirm /memory, workspace trust, CLI overrides and managed sources')
    ignored = {'.git', 'node_modules', 'vendor', 'dist', 'build', '.venv', '.cache'}
    for directory, dirs, names in os.walk(project) if include_project else []:
        dirs[:] = sorted(d for d in dirs if d not in ignored and not Path(directory, d).is_symlink())
        for name in ('CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md'):
            if name in names and not (scope == 'project' and 'local' in name):
                add(Path(directory) / name, 'local' if 'local' in name else 'project', 'instructions', 2, 'conditional descendant; not necessarily loaded')
        directory_parts = Path(directory).parts
        if any(directory_parts[i:i + 2] == ('.claude', 'rules') for i in range(len(directory_parts) - 1)):
            for name in sorted(names):
                if name.endswith('.md'):
                    add(Path(directory) / name, 'project', 'rules', 2, 'conditional nested rule; confirm paths and exclusions')
    critical = [f for f in files if f['priority'] == 0]
    other = sorted((f for f in files if f['priority'] != 0), key=lambda f: (f['priority'], f['path']))
    kept = critical + other[:max(0, limit - len(critical))]
    omitted = other[max(0, limit - len(critical)):]
    gaps.extend(['Filesystem candidates do not prove effective CLI, environment, remote managed/MDM policy, trust or enabled-plugin state; confirm /status, /memory and /mcp when needed.',
                 'Instruction imports and claudeMdExcludes require source inspection; omitted files and excluded dependency directories are not assessed.'])
    history = decision_context(cache_root(), project, main, scope, plugins)
    gaps.extend(history['gaps'])
    return {'scope': scope, 'git_root': git_root, 'decision_context': history, 'cwd': str(cwd), 'project_root': str(project), 'main_worktree': str(main), 'config_dir': str(config),
            'files': kept, 'mcp': mcp, 'plugins': plugins, 'coverage': {'discovered': len(files), 'included': len(kept),
            'omitted': [{'path': f['path'], 'kind': f['kind']} for f in omitted], 'gaps': gaps},
            'precedence': 'managed > CLI/session > local > project > user; list merging and field-specific exceptions require current source verification'}


def plugin_components(root):
    root = Path(root).resolve()
    try:
        manifest_path = root / '.claude-plugin/plugin.json'
        if file_state(manifest_path)['state'] == 'symlink':
            return [{'kind': 'manifest', 'state': 'symlink-not-read'}]
        manifest = read_json(manifest_path)
    except FileNotFoundError:
        manifest = {}
    except (OSError, ValueError):
        return [{'kind': 'manifest', 'state': 'corrupt'}]
    if not isinstance(manifest, dict):
        return [{'kind': 'manifest', 'state': 'corrupt'}]
    defaults = {'skills': 'skills', 'commands': 'commands', 'agents': 'agents', 'hooks': 'hooks/hooks.json',
                'mcpServers': '.mcp.json', 'lspServers': '.lsp.json', 'outputStyles': 'output-styles',
                'workflows': 'workflows', 'experimental.themes': 'themes', 'experimental.monitors': 'monitors'}
    result = []
    for key, default in defaults.items():
        value = manifest.get(key)
        if '.' in key:
            outer, inner = key.split('.')
            value = manifest.get(outer, {}).get(inner) if isinstance(manifest.get(outer, {}), dict) else None
        paths = value if isinstance(value, list) else [value] if value is not None else []
        if value is None or key in ('skills', 'hooks', 'mcpServers', 'lspServers'):
            if (root / default).exists():
                paths = [f'./{default}'] + paths
        for item in paths:
            if not isinstance(item, str):
                result.append({'kind': key, 'state': 'inline', 'requires_schema_review': True})
                continue
            if item.startswith('https://') and key == 'mcpServers':
                result.append({'kind': key, 'state': 'remote-bundle', 'requires_network_review': True})
                continue
            path = (root / item).resolve()
            contained = path.is_relative_to(root)
            result.append({'kind': key, 'path': str(path), 'contained': contained,
                           'state': 'present' if contained and path.exists() else 'missing' if contained else 'outside-plugin'})
    if not manifest.get('skills') and not (root / 'skills').exists() and (root / 'SKILL.md').is_file():
        result.append({'kind': 'skills', 'path': str(root / 'SKILL.md'), 'contained': True, 'state': 'present'})
    return result


def identity(scope, root, path, category, issue):
    if scope not in ('project', 'local', 'user', 'managed', 'plugin'):
        raise ValueError('Explicit scope required')
    relative = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    return json.dumps([scope, relative, category, issue], separators=(',', ':'))


def decisions_read(path):
    try:
        data = read_json(path)
        if not isinstance(data, dict):
            raise ValueError('Invalid decision store')
        if data.get('schema_version') == 2 and isinstance(data.get('decisions'), list):
            for entry in data['decisions']:
                validate_decision(entry)
            return data
        if data.get('schema_version') == 1 and isinstance(data.get('decisions'), list):
            return {'schema_version': 2, 'decisions': [], 'legacy_unmatched': data['decisions']}
        raise ValueError('Unsupported decisions schema')
    except FileNotFoundError:
        return {'schema_version': 2, 'decisions': [], 'legacy_unmatched': []}


def decision_context(cache, project, main, scope, plugins):
    """Return applicable decision evidence without migrating or changing any store."""
    project, main = Path(project).resolve(), Path(main).resolve()
    project_ids = {str(project), str(main)}
    plugin_ids = {value for plugin in plugins for value in (plugin['name'], str(Path(plugin['root']).resolve()))}
    stores = [(Path(cache) / 'decisions-v2.json', 'private')]
    if scope != 'global':
        stores.append((project / '.claude/claudit-decisions-shared-v2.json', 'shared'))
        stores.append((project / '.claude/claudit-decisions.json', 'legacy'))
    if scope != 'project':
        stores.append((Path(cache) / 'decisions.json', 'legacy'))
    result = {'stores': [], 'decisions': [], 'gaps': [],
              'matching': 'Scoped fingerprint and full project/plugin identity; preserve conflicting applicable records separately'}
    for path, storage in stores:
        state = file_state(path)['state']
        receipt = {'path': str(path), 'storage': storage, 'state': state,
                   'applicable_count': 0, 'excluded_count': 0, 'legacy_unmatched_count': 0}
        result['stores'].append(receipt)
        if state == 'missing':
            continue
        if state != 'present':
            result['gaps'].append(f'Decision store {state}; history unassessed: {path}')
            continue
        try:
            data = decisions_read(path)
            receipt['legacy_unmatched_count'] = len(data.get('legacy_unmatched', []))
            if storage == 'legacy':
                receipt['legacy_unmatched_count'] += len(data['decisions'])
                continue
            for entry in data['decisions']:
                record_scope, relative, _, _ = validate_decision(entry)
                namespace = entry.get('project_id')
                if storage == 'shared':
                    applicable = record_scope == 'project' and not namespace and not personal_path(relative)
                    if not applicable:
                        result['gaps'].append(f'Shared decision store contains out-of-scope records; excluded: {path}')
                elif record_scope in ('project', 'local'):
                    applicable = scope != 'global' and namespace in project_ids
                    if scope == 'project' and record_scope != 'project':
                        applicable = False
                elif record_scope == 'plugin':
                    applicable = scope != 'project' and namespace in plugin_ids
                else:
                    applicable = scope != 'project' and (not namespace or namespace in project_ids)
                if applicable:
                    receipt['applicable_count'] += 1
                    result['decisions'].append({'source': str(path), 'storage': storage, 'record': entry})
                else:
                    receipt['excluded_count'] += 1
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            receipt['state'] = 'corrupt'
            result['gaps'].append(f'Invalid decision store; history unassessed: {path}')
    return result


def validate_decision(entry):
    if not isinstance(entry, dict):
        raise ValueError('Invalid decision record')
    parts = json.loads(entry['fingerprint'])
    if not isinstance(parts, list) or len(parts) != 4 or not all(isinstance(p, str) and p for p in parts):
        raise ValueError('Invalid scoped identity')
    scope, relative, category, issue = parts
    if scope not in ('project', 'local', 'user', 'managed', 'plugin') or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Invalid scoped path')
    if entry.get('action') not in ('accepted', 'rejected', 'deferred', 'alternative'):
        raise ValueError('Invalid decision action')
    if scope in ('local', 'plugin') and not entry.get('project_id'):
        raise ValueError('Private local/plugin decisions require a project/plugin namespace')
    return parts


def decision_save(path, entry_path, shared=False):
    entry = read_json(entry_path)
    scope, relative, category, issue = validate_decision(entry)
    if shared and (scope != 'project' or personal_path(relative) or entry.get('project_id')):
        raise ValueError('Personal identities/decisions cannot enter shared storage')
    if not shared and scope == 'project' and not entry.get('project_id'):
        raise ValueError('Private project decisions require project_id')
    key = (entry['fingerprint'], entry.get('project_id'))
    with locked(str(path) + '.lock'):
        data = decisions_read(path)
        if shared and data.get('legacy_unmatched'):
            raise ValueError('Legacy mixed-scope file preserved; use new shared-v2 destination')
        if shared:
            for previous in data['decisions'] + data.get('history', []):
                previous_scope, previous_path, _, _ = validate_decision(previous)
                if previous_scope != 'project' or personal_path(previous_path) or previous.get('project_id'):
                    raise ValueError('Existing shared store contains personal records; preserve and reconcile separately')
        old = next((x for x in data['decisions'] if (x['fingerprint'], x.get('project_id')) == key), None)
        if old:
            data.setdefault('history', []).append(old)
        data['decisions'] = [x for x in data['decisions'] if (x['fingerprint'], x.get('project_id')) != key] + [entry]
        atomic(path, data)
    return {'status': 'saved', 'path': str(path)}


def personal_path(path):
    p = Path(path)
    return (p.is_absolute() or '..' in p.parts or p.name in ('CLAUDE.local.md', 'settings.local.json',
            '.claude.json', 'claudit-decisions.json') or p.name.startswith('.env') or
            '.git' in p.parts or '.claude/projects' in p.as_posix())


def git_names(root, *args):
    raw = subprocess.check_output(['git', '-C', str(root), *args, '-z'])
    return [os.fsdecode(p) for p in raw.split(b'\0') if p]


def consumer_snapshot(root):
    result = {key: digest(subprocess.check_output(['git', '-C', str(root), *args])) for key, args in {
        'head': ('rev-parse', 'HEAD'), 'branch': ('rev-parse', '--abbrev-ref', 'HEAD'), 'status': ('status', '--porcelain=v1', '-z', '--untracked-files=all'),
        'index': ('diff', '--cached', '--binary'), 'worktree': ('diff', '--binary')}.items()}
    untracked = {}
    for name in git_names(root, 'ls-files', '--others', '--exclude-standard'):
        path = Path(root) / name
        untracked[name] = digest(os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes())
    result['untracked'] = untracked
    return result


def prepare_pr(root, destination, branch, paths):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination.is_relative_to(root):
        raise ValueError('Delivery worktree must be outside consumer tree')
    if not paths or any(personal_path(p) for p in paths):
        raise ValueError('Only explicitly selected shareable paths are eligible')
    dirty_targets = []
    for name in paths:
        target = (root / name).resolve()
        if not target.is_relative_to(root) or (root / name).is_symlink():
            raise ValueError('Symlink/outside target is not eligible')
        if git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--', name):
            dirty_targets.append(name)
    snapshot = consumer_snapshot(root)
    head, base = git(root, 'rev-parse', 'HEAD'), git(root, 'branch', '--show-current')
    if not base:
        raise ValueError('Detached consumer HEAD requires an explicitly chosen base before PR delivery')
    subprocess.run(['git', '-C', str(root), 'worktree', 'add', '-b', branch, str(destination), head], check=True, capture_output=True)
    receipt = {'root': str(root), 'worktree': str(destination), 'branch': branch, 'base': base, 'head': head,
               'paths': paths, 'dirty_targets_excluded': dirty_targets, 'consumer_snapshot': snapshot}
    receipt_path = destination.parent / f'{destination.name}.claudit-receipt.json'
    atomic(receipt_path, receipt)
    return {'receipt': str(receipt_path), **receipt}


def verify_pr(receipt_path):
    receipt = read_json(receipt_path)
    root, worktree = Path(receipt['root']), Path(receipt['worktree'])
    if consumer_snapshot(root) != receipt['consumer_snapshot']:
        raise ValueError('Consumer changed since preparation; inspect before proceeding, never restore over it')
    changed = set(git_names(worktree, 'diff', '--name-only', receipt['head']))
    changed.update(git_names(worktree, 'diff', '--name-only', receipt['head'], 'HEAD'))
    changed.update(git_names(worktree, 'diff', '--cached', '--name-only', receipt['head']))
    changed.update(git_names(worktree, 'ls-files', '--others', '--exclude-standard'))
    for name in changed:
        path = worktree / name
        if not path.resolve().is_relative_to(worktree) or any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(worktree)):
            raise ValueError('Delivery contains a symlink path')
    for command in (['ls-tree', '-r', '-z', 'HEAD'], ['ls-files', '--stage', '-z']):
        entries = subprocess.check_output(['git', '-C', str(worktree), *command]).split(b'\0')
        for entry in entries:
            if b'\t' in entry:
                metadata, name = entry.split(b'\t', 1)
                if metadata.split(b' ')[0] == b'120000' and os.fsdecode(name) in changed:
                    raise ValueError('Delivery commit/index contains a symlink')
    if not changed <= set(receipt['paths']) or any(personal_path(p) for p in changed):
        raise ValueError('Delivery contains unselected or personal paths')
    return {'status': 'verified', 'paths': sorted(changed), 'base': receipt['base'], 'head': receipt['head']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('status', 'knowledge', 'fetch'):
        p = sub.add_parser(name)
        p.add_argument('--host-version', required=True)
        p.add_argument('domains', nargs='*')
    p = sub.add_parser('cache-put'); p.add_argument('bundle'); p.add_argument('research')
    p = sub.add_parser('cache-fail'); p.add_argument('domain', choices=DOMAINS); p.add_argument('reason')
    p = sub.add_parser('discover'); p.add_argument('--cwd', default=os.getcwd()); p.add_argument('--home', default=str(Path.home())); p.add_argument('--config'); p.add_argument('--managed'); p.add_argument('--limit', type=int, default=200); p.add_argument('--scope', choices=['auto', 'global', 'project', 'comprehensive'], default='auto')
    p = sub.add_parser('identity'); p.add_argument('scope'); p.add_argument('root'); p.add_argument('path'); p.add_argument('category'); p.add_argument('issue')
    p = sub.add_parser('decisions-read'); p.add_argument('path')
    p = sub.add_parser('decision-save'); p.add_argument('path'); p.add_argument('entry'); p.add_argument('--shared', action='store_true')
    p = sub.add_parser('prepare-pr'); p.add_argument('--root', required=True); p.add_argument('--destination', required=True); p.add_argument('--branch', required=True); p.add_argument('paths', nargs='+')
    p = sub.add_parser('verify-pr'); p.add_argument('receipt')
    args = parser.parse_args()
    root = cache_root()
    if args.command in ('status', 'knowledge', 'fetch'):
        if any(d not in (*DOMAINS, 'all') for d in args.domains):
            raise ValueError('Unknown domain; choose core-config, ecosystem, optimization or all')
        domains = list(DOMAINS) if not args.domains or 'all' in args.domains else list(dict.fromkeys(args.domains))
        host = version(args.host_version)
        if args.command == 'fetch':
            result = [fetch(root, d, host) for d in domains]
        else:
            result = [domain_state(root, d, host) for d in domains]
            if args.command == 'knowledge':
                for item in result:
                    try:
                        item['knowledge'] = read_json(item['record'])
                    except (OSError, ValueError):
                        item['knowledge'] = None
    elif args.command == 'cache-put': result = commit_cache(root, args.bundle, args.research)
    elif args.command == 'cache-fail': result = fail(root, args.domain, args.reason)
    elif args.command == 'discover': result = discover(args.cwd, args.home, args.config, args.managed, args.limit, args.scope)
    elif args.command == 'identity': result = identity(args.scope, args.root, args.path, args.category, args.issue)
    elif args.command == 'decisions-read': result = decisions_read(args.path)
    elif args.command == 'decision-save': result = decision_save(args.path, args.entry, args.shared)
    elif args.command == 'prepare-pr': result = prepare_pr(args.root, args.destination, args.branch, args.paths)
    elif args.command == 'verify-pr': result = verify_pr(args.receipt)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'error': str(exc), 'operation_failed': True}), file=sys.stderr)
        sys.exit(1)
