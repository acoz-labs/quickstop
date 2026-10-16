"""Offline advisory checks. Never executes input or grants authority."""
import json
import sys
import argparse
import hashlib
from pathlib import Path
import subprocess
import re
import os
import secrets
import shutil
import stat

CONTRACT_KEYS = set('schema run attempt generation repository issue base head spec config package guide harness role process session scope constraints commands effects limits capabilities stop tools'.split())
ABSENT = object()


def exact(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), 'unknown or missing fields')


def hexid(value, size):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def strings(value):
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value)


def contract_policy(c):
    exact(c, CONTRACT_KEYS)
    require(type(c['schema']) is int and c['schema'] == 1, 'unsupported schema')
    for key in ('run', 'attempt', 'process', 'session'):
        require(isinstance(c[key], str) and re.fullmatch('[a-zA-Z0-9_-]{1,64}', c[key]), 'invalid identifier')
    for key in ('generation', 'issue'):
        require(type(c[key]) is int and c[key] > 0, 'invalid integer')
    require(isinstance(c['repository'], str) and re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', c['repository']), 'repository required')
    for key in ('base', 'head', 'guide'):
        require(hexid(c[key], 40), 'exact revision required: ' + key)
    for key in ('spec', 'config', 'package', 'harness'):
        require(hexid(c[key], 64), 'exact digest required: ' + key)
    require(c['role'] in ('author', 'reviewer'), 'unsupported role')
    for key in ('scope', 'constraints', 'commands', 'limits', 'effects'):
        require(strings(c[key]), 'nonempty list required: ' + key)
    for path in c['scope']:
        require(not path.startswith('/') and ':' not in path and chr(92) not in path and chr(0) not in path and '..' not in path.split('/') and any(p not in ('', '.') for p in path.split('/')), 'unbounded scope')
    require(set(c['effects']) <= {'proposal', 'checkout-edit'}, 'unsupported effects')
    require(isinstance(c['capabilities'], list) and all(isinstance(x, str) for x in c['capabilities']), 'capability list required')
    require(c['stop'] in (None, 'paused', 'stop', 'quota', 'offline', 'revoked'), 'unsupported stop')
    require(isinstance(c['tools'], list) and c['tools'], 'tool pins required')
    for tool in c['tools']:
        exact(tool, ('path', 'sha256'))
        require(isinstance(tool['path'], str) and Path(tool['path']).is_absolute() and hexid(tool['sha256'], 64), 'invalid tool pin')


def decode(data):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    require(len(data) <= 65536, 'input exceeds 64 KiB')
    return json.loads(data, object_pairs_hook=unique)


def regular_bytes(path, limit, follow=False):
    flags = os.O_RDONLY | os.O_NONBLOCK
    if not follow:
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), 'input must be a regular file')
        require(info.st_size <= limit, 'input exceeds byte bound')
        data = stream.read(limit + 1)
        require(len(data) <= limit, 'input exceeds byte bound')
        return data


def load(path):
    return decode(regular_bytes(path, 65536))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path, follow=False):
    return hashlib.sha256(regular_bytes(path, 256 * 1024 * 1024, follow)).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def result_check(c, r):
    contract_policy(c)
    exact(r, 'schema contract role process session author_process author_session outcome commands evidence findings next_action limits effects'.split())
    require(type(r['schema']) is int and r['schema'] == 2, 'unsupported result schema')
    require(r['contract'] == hashlib.sha256(encoded(c)).hexdigest(), 'contract identity drift')
    for key in ('role', 'process', 'session', 'limits', 'effects'):
        require(r[key] == c[key], 'result binding mismatch: ' + key)
    for key in ('author_process', 'author_session'):
        require(isinstance(r[key], str) and r[key].strip(), 'author provenance required')
    if c['role'] == 'reviewer':
        require(r['process'] != r['author_process'] and r['session'] != r['author_session'], 'independent executing review required')
    else:
        require(r['process'] == r['author_process'] and r['session'] == r['author_session'], 'author provenance drift')
    require(r['outcome'] in ('passed', 'failed', 'blocked'), 'unsupported outcome')
    require(isinstance(r['findings'], list) and all(isinstance(x, str) and x for x in r['findings']), 'invalid findings')
    require(isinstance(r['next_action'], str) and r['next_action'].strip(), 'next action required')
    require(isinstance(r['commands'], list) and len(r['commands']) == len(c['commands']), 'command outcomes required')
    for expected, command in zip(c['commands'], r['commands']):
        require(isinstance(command, dict), 'command record required')
        require(command.get('command') == expected, 'command order mismatch')
        if command.get('status') == 'executed':
            exact(command, ('command', 'status', 'exit'))
            require(type(command['exit']) is int, 'integer exit required')
        else:
            exact(command, ('command', 'status', 'reason'))
            require(command['status'] == 'not-run' and isinstance(command['reason'], str) and command['reason'].strip(), 'not-run reason required')
    require(isinstance(r['evidence'], list) and r['evidence'], 'evidence required')
    for evidence in r['evidence']:
        exact(evidence, ('locator', 'sha256'))
        require(isinstance(evidence['locator'], str) and evidence['locator'].strip() and hexid(evidence['sha256'], 64), 'invalid evidence')
    if r['outcome'] == 'passed':
        require(not r['findings'] and all(x['status'] == 'executed' and x['exit'] == 0 for x in r['commands']), 'contradictory success')
        require(not c['stop'] and not c['capabilities'], 'success with missing capability')
    return {'class': 'success', 'decision': 'validated-claim-only'}


def inspect_git(root, *args, **options):
    # Only the platform Git is trusted, never a consumer PATH entry. Strip all
    # inherited Git knobs, including index/directory redirection and config injection.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", PATH="/usr/bin:/bin")
    return subprocess.run(["/usr/bin/git", "--no-pager", "--no-replace-objects",
                           "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
                           "-c", "core.untrackedCache=false", "-c", "diff.external=",
                           "-c", "core.pager=cat", "-C", str(root), *args],
                          env=env, timeout=10, **options)


def reviewer_source(root, head):
    def read(*args):
        return inspect_git(root, *args, capture_output=True, check=True).stdout
    config = read("config", "--null", "--list").lower()
    for entry in config.split(b"\0"):
        key, _, value = entry.partition(b"\n")
        require(not (key.startswith(b"filter.") or key.startswith(b"submodule.") or
                     key in (b"core.sparsecheckout", b"core.sparsecheckoutcone", b"core.autocrlf", b"core.eol")),
                "reviewer unsupported sparse/submodule/filter/normalization configuration")
    flags = read("ls-files", "-v", "-z").split(b"\0")
    require(all(not item or item[:1] == b"H" for item in flags),
            "reviewer unsupported index flags")
    tree = read("ls-tree", "-r", "-z", head)
    expected = []
    for record in tree.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, kind, oid = meta.split()
        require(kind == b"blob" and mode in (b"100644", b"100755"),
                "reviewer unsupported tracked mode or submodule")
        expected.append(mode + b" " + oid + b" 0\t" + name + b"\0")
        path = root / os.fsdecode(name)
        require(all(not parent.is_symlink() for parent in path.parents if parent != root.parent),
                "reviewer symlink directory uncertainty")
        data = regular_bytes(path, 256 * 1024 * 1024)
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest().encode()
        require(actual == oid, "reviewer requires clean source checkout")
        require(bool(path.stat().st_mode & 0o111) == (mode == b"100755"), "reviewer executable mode drift")
    require(read("ls-files", "--stage", "-z") == b"".join(expected), "reviewer index/tree drift")
    require(not read("ls-files", "--others", "-z"), "reviewer requires clean source checkout")


def contract_check(root, contract, observations=ABSENT):
    contract_policy(contract)
    if not (root / '.sdlc/config.json').is_file():
        return {'class': 'wait-missing-capability', 'reason': 'required config missing'}
    if shutil.which('git', path='/usr/bin:/bin') is None:
        return {'class': 'wait-missing-capability', 'reason': 'required git missing'}
    toplevel = inspect_git(root, 'rev-parse', '--show-toplevel',
                              capture_output=True, text=True, check=True).stdout.strip()
    require(Path(toplevel).resolve() == root.resolve(), 'repository root drift')
    origin = inspect_git(root, 'remote', 'get-url', 'origin',
                            capture_output=True, text=True, check=True).stdout.strip()
    match = re.fullmatch(r'(?:https://github[.]com/|ssh://git@github[.]com/|git@github[.]com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?', origin)
    require(match is not None and match[1] == contract['repository'], 'origin repository drift')
    require(digest(root / '.sdlc/config.json') == contract['config'], 'config drift')
    head = inspect_git(root, 'rev-parse', 'HEAD',
                          capture_output=True, text=True, check=True).stdout.strip()
    require(head == contract['head'], 'head drift')
    if contract['role'] == 'reviewer':
        reviewer_source(root, head)
    for revision in ('base', 'head'):
        checked = inspect_git(root, 'cat-file', '-t', contract[revision],
                                 capture_output=True, text=True)
        require(checked.returncode == 0 and checked.stdout.strip() == 'commit', 'missing commit: ' + revision)
    ancestry = inspect_git(root, 'merge-base', '--is-ancestor', contract['base'], contract['head'], capture_output=True)
    require(ancestry.returncode == 0, 'base is not head ancestor')
    config = load(root / '.sdlc/config.json')
    require(isinstance(config, dict) and config.get('delivery_profile') in ('service', 'artifact', 'non-deployable'), 'invalid delivery profile')
    require(strings(config.get('validation')), 'invalid validation commands')
    require(config.get('validation') == contract['commands'], 'command requirements drift')
    for tool in contract['tools']:
        if not Path(tool['path']).is_file():
            return {'class': 'wait-missing-capability', 'reason': 'required tool missing'}
        require(digest(tool['path'], follow=True) == tool['sha256'], 'tool revision drift')
    if contract['stop'] or contract['capabilities']:
        return {'class': 'wait-missing-capability', 'reason': 'stop or missing capabilities'}
    if observations is ABSENT:
        return {'class': 'wait-missing-capability', 'reason': 'trusted observations required'}
    exact(observations, ('spec', 'package', 'guide', 'harness'))
    for key in ('spec', 'package', 'guide', 'harness'):
        require(observations[key] == contract[key], 'observation drift: ' + key)
    return {'class': 'success', 'decision': 'preflight-only'}


def event_decide(state, event, snapshot):
    common = 'schema generation identity head base'.split()
    exact(state, common + ['seen', 'rounds', 'uncertain'])
    exact(event, common + ['key', 'kind'])
    flags = 'enrolled assigned draft closed blockers approval independent gate authority'.split()
    exact(snapshot, common + flags + ['merged_sha', 'review_head', 'stop'])
    for value in (state, event, snapshot):
        require(type(value['schema']) is int and value['schema'] == 1, 'unsupported event schema')
        require(type(value['generation']) is int and value['generation'] > 0, 'invalid generation')
        require(hexid(value['identity'], 64) and hexid(value['head'], 40) and hexid(value['base'], 40), 'missing event identity')
    require(all(type(snapshot[x]) is bool for x in flags), 'invalid snapshot flags')
    require(type(state['uncertain']) is bool and type(state['rounds']) is int and state['rounds'] >= 0, 'invalid state')
    require(isinstance(state['seen'], list) and all(isinstance(x, str) for x in state['seen']), 'invalid work keys')
    require(isinstance(event['key'], str) and 0 < len(event['key']) <= 128, 'invalid logical key')
    require(event['kind'] in ('review', 'head', 'merged', 'closed', 'reconcile', 'informational'), 'unknown event kind')
    for key in ('merged_sha', 'review_head'):
        require(snapshot[key] is None or hexid(snapshot[key], 40), 'invalid snapshot revision')
    require(snapshot['stop'] in (None, 'paused', 'stop', 'quota', 'offline', 'revoked'), 'unknown stop state')
    require(snapshot['merged_sha'] is None or snapshot['closed'], 'contradictory merge snapshot')
    if state['uncertain']:
        decision = 'reconcile'
    elif snapshot['stop']:
        decision = 'wait'
    elif any(value[key] != state[key] for value in (event, snapshot) for key in common[1:]):
        decision = 'reconcile'
    elif not snapshot['enrolled'] or not snapshot['assigned'] or snapshot['draft'] or event['kind'] == 'informational':
        decision = 'ignore'
    elif snapshot['merged_sha']:
        decision = 'acceptance-handoff'
    elif snapshot['closed']:
        decision = 'stop'
    elif snapshot['review_head'] != snapshot['head']:
        decision = 'review'
    elif snapshot['blockers']:
        decision = ('replan' if state['rounds'] >= 2 else 'correct') if snapshot['independent'] else 'blocked'
    elif all(snapshot[x] for x in ('approval', 'independent', 'gate', 'authority')):
        decision = 'merge-ready'
    else:
        decision = 'blocked'
    logical = {key: snapshot[key] for key in common[1:]}
    logical['phase'] = decision
    if decision == 'acceptance-handoff':
        logical['merged_sha'] = snapshot['merged_sha']
    key = hashlib.sha256(encoded(logical)).hexdigest()
    reason = snapshot['stop'] if decision == 'wait' else decision
    if key in state['seen'] and decision not in ('reconcile', 'wait'):
        decision = 'duplicate'
        reason = 'already-seen-work'
    output = {'class': 'wait-missing-capability' if decision == 'wait' else 'success',
              'decision': decision, 'key': key, 'reason': reason, 'effects': []}
    if decision == 'acceptance-handoff':
        output['candidate'] = snapshot['merged_sha']
    return output


def handoff_write(root, anchor, output, c, r):
    result_check(c, r)
    require(anchor.is_absolute() and '..' not in anchor.parts and anchor == anchor.resolve(), 'trusted canonical absolute anchor required')
    require(not anchor.is_relative_to(root.resolve()), 'handoff root must be outside consumer checkout')
    require(not output.is_absolute() and output.parts and '..' not in output.parts, 'relative contained output required')
    consumer_fd = os.open(root.resolve(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        consumer = os.fstat(consumer_fd)
    finally:
        os.close(consumer_fd)

    def outside_consumer(fd):
        current = os.fstat(fd)
        require((current.st_dev, current.st_ino) != (consumer.st_dev, consumer.st_ino),
                'handoff must be outside consumer checkout')
    # The operator trusts the canonical anchor and its ancestors. Only descendants
    # are untrusted; never traverse filesystem/home ancestors with openat.
    parent_fd = os.open(anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        outside_consumer(parent_fd)
        for part in output.parent.parts:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
            outside_consumer(parent_fd)
        # Refuse the consumer directory itself before making any changes.
        try:
            existing = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
            require((existing.st_dev, existing.st_ino) != (consumer.st_dev, consumer.st_ino),
                    'handoff must be outside consumer checkout')
        except FileNotFoundError:
            pass
        try:
            os.mkdir(output.name, mode=0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
        except FileExistsError:
            pass
        fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            outside_consumer(fd)
        except ValueError:
            os.close(fd)
            raise
    finally:
        os.close(parent_fd)
    locked = False
    temporary = None
    try:
        lock = os.open('.lock', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=fd)
        os.close(lock)
        locked = True
        generations = []
        with os.scandir(fd) as entries:
            for entry in entries:
                name = entry.name
                match = re.fullmatch(r'g([1-9][0-9]*)\.json', name)
                if match:
                    generations.append((int(match[1]), name))
                    require(len(generations) <= 64, 'handoff record limit; operator archive required')
                else:
                    require(name == '.lock', 'unrecognized handoff content; reconcile')
        payload = encoded({'contract': c, 'result': r})
        require(len(payload) <= 65536, 'handoff too large')
        for generation, name in sorted(generations):
            previous_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(previous_fd, 'rb') as stream:
                require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'prior record must be a regular file')
                previous = stream.read(65537)
            require(len(previous) <= 65536, 'prior handoff too large')
            prior = decode(previous)
            exact(prior, ('contract', 'result'))
            result_check(prior['contract'], prior['result'])
            require(prior['contract']['generation'] == generation, 'prior generation mismatch')
            require(all(prior['contract'][key] == c[key] for key in ('run', 'attempt', 'repository', 'issue')), 'unrelated attempt')
        if generations:
            require(c['generation'] >= generation, 'stale generation')
            if c['generation'] == generation:
                require(previous == payload, 'conflicting replay')
                return {'class': 'success', 'decision': 'replayed'}
        require(len(generations) < 64, 'handoff record limit; operator archive required')
        temporary = '.pending-' + secrets.token_hex(8)
        temp_fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(temp_fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, 'g' + str(c['generation']) + '.json', src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        os.fsync(fd)
        return {'class': 'success', 'decision': 'persisted'}
    finally:
        if temporary is not None:
            os.unlink(temporary, dir_fd=fd)
        if locked:
            os.unlink('.lock', dir_fd=fd)
            os.fsync(fd)
        os.close(fd)


class PolicyParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    try:
        action = sys.argv[1:3]
        require(action in (['contract', 'check'], ['result', 'check'], ['event', 'decide'], ['handoff', 'write']), 'unsupported action')
        parser = PolicyParser()
        if action == ['event', 'decide']:
            for flag in ('state', 'event', 'github-snapshot'):
                parser.add_argument('--' + flag, required=True)
        elif action == ['contract', 'check']:
            parser.add_argument('--repo-root', required=True, type=Path)
            parser.add_argument('--observations')
        else:
            parser.add_argument('--result', required=True)
            if action == ['handoff', 'write']:
                parser.add_argument('--repo-root', required=True, type=Path)
                parser.add_argument('--handoff-root', required=True, type=Path)
                parser.add_argument('--output', required=True, type=Path)
        if action != ['event', 'decide']:
            parser.add_argument('--contract', required=True)
        args = parser.parse_args(sys.argv[3:])
        if action == ['event', 'decide']:
            output = event_decide(load(args.state), load(args.event), load(args.github_snapshot))
        elif action == ['contract', 'check']:
            output = contract_check(args.repo_root, load(args.contract), load(args.observations) if args.observations else ABSENT)
        elif action == ['handoff', 'write']:
            output = handoff_write(args.repo_root, args.handoff_root, args.output, load(args.contract), load(args.result))
        else:
            output = result_check(load(args.contract), load(args.result))
    except (ValueError, KeyError, RecursionError, OSError, subprocess.SubprocessError) as error:
        output = {'class': 'invalid-policy', 'reason': str(error)}
    print(json.dumps(output, sort_keys=True))
    return {'success': 0, 'invalid-policy': 2, 'wait-missing-capability': 3}[output['class']]


if __name__ == '__main__':
    sys.exit(main())
