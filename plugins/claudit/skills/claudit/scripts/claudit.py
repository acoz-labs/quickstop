#!/usr/bin/env python3
"""Claudit 4.1 helper: a deterministic, read-only scan of a project's Claude Code setup.

Subcommands: scan, new-pages, dismiss. Standard library only; Python 3.9+.
The only write is `dismiss`, to <root>/.claude/claudit-dismissed.json. The
helper never prints secret values and never reads ~/.claude.json.
"""
import argparse
import datetime
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

VERSION = '4.1.0'
HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, '..', 'catalog.json')
CAP = 40
MAX_FILES = 20000
MAX_DEPTH = 6
MAX_READ = 512 * 1024
SKIP_DIRS = {'.git', 'node_modules', 'vendor', 'dist', 'build', '__pycache__', '.venv', 'venv',
             'target', '.tox', '.mypy_cache', '.pytest_cache', 'coverage', '.next'}
DEPENDENCY_DIRS = {'node_modules', 'vendor', 'venv'}  # never skill directories without a SKILL.md
# Test data is judged by the words of a directory name: split at punctuation and case changes, lower-cased,
# trailing digits dropped. A name with a test word as a whole word is a test directory (`tests`, `e2e-tests`,
# `tests_old`, `TestCases`); one with a data word is a data directory (`fixtures`, `__snapshots__`, `golden-files`,
# `evals-v2`). A word inside a word doesn't count (`testimonials`, `attest`, `latest`), and record words alone
# (`reports`, `results`, `data`) aren't data. A plugin root is exempt (see PLUGIN_DIRS).
DATA_WORDS = {'fixture', 'fixtures', 'testdata', 'golden', 'goldens', 'snapshot', 'snapshots', 'cassette', 'cassettes',
              'eval', 'evals', 'grader', 'graders'}
TEST_WORDS = {'test', 'tests'}
PLUGIN_DIRS = ('.claude-plugin', '.codex-plugin')  # a directory holding one is a plugin root, never data by name
EVAL_CASE_FILES = ('case.yaml', 'case.yml')  # a directory holding one is an eval case: everything below is data
STOP_EVENTS = ('Stop', 'SubagentStop', 'TaskCompleted')
CHECK_NAMES = ('ci', 'test', 'check', 'lint', 'verify')
MUTATING = {'release', 'publish', 'promote', 'deploy', 'apply', 'push', 'write', 'cascade', 'install', 'delete', 'rm',
            'fix', 'migrate'}
# Calls Claudit suggests are plain words, paths and flags: no quotes, substitutions or shell operators.
PLAIN_CALL = re.compile(r'[\w./=,:+@%-]+(?: [\w./=,:+@%-]+)*')
SECRET_EXAMPLES = ('.env.example', '.env.sample', '.env.template')
CLAUDE_FILES = ('CLAUDE.md', '.claude/CLAUDE.md', 'CLAUDE.local.md')  # any one keeps AGENTS.md from loading by default
AGENTS_FILES = ('AGENTS.md', '.claude/AGENTS.md')
ROOT_INSTRUCTIONS = CLAUDE_FILES + AGENTS_FILES
PROJECT_SETTINGS = ('.claude/settings.json', '.claude/settings.local.json')
DISMISSED = '.claude/claudit-dismissed.json'
DEFAULT_MODE_IGNORED = (2, 1, 257)
AGENTS_MD_READ = (2, 1, 277)  # first Claude Code version that reads AGENTS.md without an import
NUMBERED = re.compile(r'^\s*\d+[.)]\s')
FENCE = re.compile(r'^\s*(```|~~~)')
PROCEDURE_WORDS = re.compile(r'release|deploy|runbook|procedure|playbook|rollout|onboarding|sdlc|delivery|review', re.I)
RUNNER = re.compile(r'(make (?:test|check|lint|ci)\b|(?:npm|pnpm|yarn)(?: run)? (?:test|lint|check|typecheck)\b[\w:-]*'
                    r'|go test\b(?: \./\.\.\.)?|cargo (?:test|clippy|check)\b|pytest\b'
                    r'|python3?(?:\.\d+)? -m (?:pytest|unittest)\b)')
MUST = re.compile(r'\b(always|must|before (?:you )?(?:report|finish|commit|push|mark|say|claim|hand|open|merg|declar|complet))', re.I)
MUST_NOT = re.compile(r"\b(must not|mustn't|never)\b", re.I)
AGENT_DIRECTIVE = re.compile(r'\b(agents?\s+(?:run|must|should|own|act|acting|are|may|will|can|author|review|implement)'
                             r'|agent-run|agent-driven|autonomous(?:ly)?)\b', re.I)
ON_DEMAND = re.compile(r'\bon[- ]demand\b', re.I)
SKILL_WORDS = re.compile(r'\b(?:skills?|slash commands?|invok\w*)\b', re.I)
LINK = re.compile(r'\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)')
LINK_DEF = re.compile(r'^\s{0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?')
MD_PATH = re.compile(r'(?<![\w/.@-])((?:\.{1,2}/)*[\w.-]+(?:/[\w.-]+)*\.md)(?![\w/-])', re.I)
IMPORT = re.compile(r'(?:^|(?<=\s))@([^\s`\'"()<>\[\]]+)')
TOKEN_SPLIT = re.compile(r'[\s`"\'()\[\],;|]+')
LANGUAGES = {'tsconfig.json': 'typescript', 'go.mod': 'go', 'Cargo.toml': 'rust', 'pom.xml': 'java',
             'build.gradle': 'java', 'build.gradle.kts': 'kotlin', 'mypy.ini': 'python',
             'pyrightconfig.json': 'python'}
GRADES = {'correctness': 0, 'alignment': 1, 'coverage': 2}
SEVERITIES = {'high': 0, 'medium': 1, 'low': 2}
HOME = os.path.expanduser('~')
PLAN_MAX = 7
# The plan item title for each finding kind; findings of one kind on one path are one item.
CHANGE_TITLES = {
    'invalid-json': 'Fix the JSON in {path}', 'wrong-type': 'Fix the value types in {path}',
    'too-large': 'Check {path} by hand', 'write-rule': 'Replace the path rules that never match in {path}',
    'default-mode': 'Remove defaultMode from {path}', 'auto-mode': 'Move autoMode out of {path}',
    'mcp-location': 'Move the MCP servers to .mcp.json', 'matcher-type': 'Make the hook matchers in {path} strings',
    'matcher-ignored': 'Remove the ignored hook matchers in {path}', 'hook-script': 'Fix the hook scripts in {path}',
    'claudeignore': 'Replace .claudeignore with deny rules', 'hooks-file': 'Move {path} into settings hooks',
    'flat-skill': 'Move {path} into a skill directory', 'skill-missing': 'Add a SKILL.md to {path}',
    'agents-md-not-loaded': 'Make {path} load', 'oversized': 'Cut {path} to what Claude needs',
    'broken-import': 'Fix the imports in {path}', 'stale-ref': 'Fix the stale paths in {path}',
    'no-instructions': 'Add a short CLAUDE.md', 'undocumented-checks': 'Record the check commands in {path}',
    'allowlist': 'Pre-approve the check commands', 'secret-deny': 'Deny reads of secret paths',
    'stop-hook': 'Enforce the check with a Stop hook', 'procedure-skill': 'Add a skill for {path}',
    'plugin-validate': 'Run claude plugin validate', 'plugin-eval': 'Add evals for {subject}',
    'lsp': 'Install a code-intelligence plugin',
}
FATAL = ('invalid-json', 'matcher-type')  # configuration that doesn't load (a file, or hooks dropped): Correctness F
# Features a project can decline in its docs: (finding kind, label, the feature as a bare noun). A decline is of
# the feature itself, never of one instance ("the old SessionStart hook"), an item in it ("rm from the allowlist")
# or a place ("disabled in CI", "secrets in hooks").
DECLINABLE = (
    ('stop-hook', 'Hooks', r'hooks'),
    ('plugin-eval', 'Plugin evals', r'evals|(?:eval(?:uation)?|tuning) (?:suites?|campaigns?|cases)|claude plugin eval'),
    ('plugin-validate', 'Plugin validation', r'plugin validation|claude plugin validate'),
    ('allowlist', 'Pre-approved commands', r'allow-?lists?|allow rules|pre-?approvals|pre-?approved commands'),
    ('procedure-skill', 'Procedure skills', r'skills'),
    ('lsp', 'Code-intelligence plugins', r'lsp(?: plugins)?|code[- ]intelligence(?: plugins)?|language servers'),
)
# Words that may qualify the feature without making it an instance: articles, owners and the kind of hook.
QUALIFIER = (r'(?:the|all|any|our|its|this|these|a|an|repository|repo|project|claude|code|claude-code|plugin|'
             r'procedure|agent|stop|push|shell-match)')
DECLINED = r'(?:retired|removed|dropped|declined|abandoned|phased out|disabled)'
DELIBERATE = r'(?:deliberately|intentionally|on purpose|by design|by choice)'
# What may follow a decline, and nothing else: an optional project scope, then the end of the sentence, a reason
# ("because", "since", "in favour of", ", so", ", and replaced them with", "by design") or a ";" or ":" clause.
DECLINE_TAIL = (r'(?:\s+(?:in this (?:repository|repo|project)|here))?(?:\s*$|,?\s+(?:because|since|in favou?r of)\s'
                r'|,\s+so\s|,\s+and replaced (?:them|it) with\s|,?\s+%s\s*$|\s*[;:]\s)' % DELIBERATE)
# An exception, limit, partial scope, time limit or reversal anywhere in the sentence means it is no decline.
DECLINE_LIMIT = re.compile(r'\b(?:except\w*|apart from|other than|but|only|for now|temporar\w*|for the time being|'
                           r'then|back|re-?add\w*|re-?enabl\w*|enabl\w*|replaced by|being (?:written|rebuilt|reworked)|'
                           r'new (?:ones?|suite|set|version)|moving (?:them|it)|moved (?:them|it)|keeps? (?:its|their) own|'
                           r'still|a few|some|several|one of|most|mostly|partly|partially|yet)\b', re.I)
# Sentences that only consider, plan or reverse a decline never count.
UNSURE = re.compile(r'\?|\b(?:if|unless|whether|would|could|might|maybe|perhaps|until|consider\w*|todo)\b'
                    r'|\b(?:will|to|going to) be\b|\b(?:restored|reinstated|re-?enabled|re-?added|brought back|again)\b'
                    r"|(?:\b(?:not|never|no longer)|n['’]t)\s+(?:been\s+|be\s+)?"
                    r'(?:retired|removed|dropped|declined|disabled|abandoned)\b', re.I)
# A sentence about another tool's hooks, skills or evals (push hooks are Git's) declines nothing in Claude Code
# unless it names Claude.
OTHER_TOOLS = re.compile(r'\b(?:git|push|pre-commit|pre-push|commit-msg|husky|lefthook|webhooks?|cursor|codex|copilot|'
                         r'windsurf|gemini|aider|eslint|prettier)\b', re.I)
CLAUDE_NAMED = re.compile(r'\bclaude\b', re.I)


def decline_forms(feature):
    """The three decline forms for one feature, each matched against a whole sentence.

    1. The feature is the subject: "Claude Code hooks were retired", "Hooks: retired".
    2. The feature is the object: "We retired hooks", "We decided against the allowlist".
    3. A deliberate absence: "deliberately has no eval campaign", "no hooks, by design".
    Each is followed only by a DECLINE_TAIL, so a scoped, specific or limited remark is not a decline.
    """
    noun = r'(?:%s\s+){0,3}(?:%s)' % (QUALIFIER, feature)
    subject = r'^(?:here,?\s+|in this (?:repository|repo|project),?\s+)?%s(?:\s+and\s+%s)*' % (noun, noun)
    return [re.compile(subject + r'(?:\s*:\s*|\s+(?:(?:have|has|had)\s+been|were|was|are|is|stay|stays|remain|'
                       r'remains)\s+(?:%s\s+|permanently\s+)?)%s\b%s' % (DELIBERATE, DECLINED, DECLINE_TAIL), re.I),
            re.compile(r"^(?:we|this (?:repository|repo|project)|the project|maintainers)\s+(?:have\s+|deliberately\s+)?"
                       r"(?:retired|removed|dropped|declined|abandoned|phased out|disabled|decided against(?: using| adding)?"
                       r"|chose not to (?:use|add|adopt|run)|opted out of)\s+%s\b%s" % (noun, DECLINE_TAIL), re.I),
            re.compile(r"(?:%s\b.*\b(?:no|without)\s+%s\b%s|\b(?:no|without)\s+%s\b[\s,]*%s\s*$)"
                       % (DELIBERATE, noun, DECLINE_TAIL, noun, DELIBERATE), re.I)]


DECLINE_FORMS = [(feature, label, re.compile(r'\b(?:%s)\b' % pattern, re.I), decline_forms(pattern))
                 for feature, label, pattern in DECLINABLE]
LIST_ITEM = re.compile(r'^\s*(?:[-*+]|[0-9]+[.)])\s+')


class UsageError(Exception):
    """A bad argument: reported as JSON with exit status 2."""


def redact(value):
    """Replace the home directory prefix with ~ in every string of a JSON value."""
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str) and len(HOME) > 1:
        for home in sorted({HOME, os.path.realpath(HOME)}, key=len, reverse=True):
            value = value.replace(home + '/', '~/')
            if value == home:
                value = '~'
    return value


def load_catalog():
    with open(CATALOG, encoding='utf-8') as handle:
        return json.load(handle)


def secret_like(rel):
    """True for paths whose contents must never be read or printed."""
    parts = rel.rstrip('/').split('/')
    name = parts[-1]
    if 'secrets' in parts[:-1] or name in SECRET_EXAMPLES:
        return 'secrets' in parts[:-1]
    return (name == '.env' or name.startswith('.env.') or name.endswith(('.pem', '.key'))
            or name.startswith('id_rsa') or fnmatch.fnmatch(name, 'credentials*.json'))


def secret_pattern(entry):
    """True for ignore-file entries that name secret-like paths."""
    e = entry.strip().lstrip('/')
    if e.startswith('**/'):
        e = e[3:]
    if not e or e.startswith('!') or e.rstrip('/').split('/')[-1] in SECRET_EXAMPLES:
        return False
    low = e.lower()
    return (low.startswith('.env') or low.rstrip('/').endswith(('.pem', '.key')) or 'secret' in low
            or 'credential' in low or low.startswith('id_rsa'))


def prose(text):
    """Yield (line number, line) outside fenced code blocks."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if match:
            fence = match.group(1) if fence is None else (None if line.strip().startswith(fence) else fence)
            continue
        if fence is None:
            yield number, line


def code_snippets(text):
    """Inline backtick spans and fenced code lines, the places commands are documented."""
    fence = None
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            fence = match.group(1) if fence is None else (None if line.strip().startswith(fence) else fence)
            continue
        if fence is not None:
            yield line.strip()
        else:
            for span in re.findall(r'`([^`\n]+)`', line):
                yield span.strip()


def split_commands(snippet):
    for part in re.split(r'&&|\|\||;|\|', snippet):
        part = part.strip()
        if part.startswith('$ '):
            part = part[2:].strip()
        if part:
            yield part


def strip_dot(command):
    return command[2:] if command.startswith('./') else command


def bash_rule_matches(rule, command):
    """Permission-rule semantics for Bash: exact, ` *`/`:*`/`*` prefix, bare Bash allows all."""
    rule = rule.strip()
    if rule in ('Bash', 'Bash(*)'):
        return True
    match = re.fullmatch(r'Bash\((.*)\)', rule, re.S)
    if not match:
        return False
    pattern = strip_dot(match.group(1).strip())
    command = strip_dot(command.strip())
    if pattern.endswith(':*'):
        pattern = pattern[:-2] + ' *'
    if '*' not in pattern:
        return command == pattern
    regex = '.*'.join(re.escape(piece) for piece in pattern.split('*'))
    if pattern.endswith(' *'):
        regex = regex[:-len(re.escape(' ') + '.*')] + '(?: .*)?'
    return re.fullmatch(regex, command, re.S) is not None


def read_pattern_matches(pattern, path):
    """gitignore-like Read(...) matching of a deny pattern against a root-relative path."""
    if pattern.startswith(('//', '~')):
        return False
    anchored = pattern.startswith(('./', '/'))
    p = pattern[2:] if pattern.startswith('./') else pattern.lstrip('/')
    if p.startswith('**/'):
        p, anchored = p[3:], False
    if p in ('', '*', '**'):
        return True
    if '/' in p.rstrip('/'):
        anchored = True
    p = p.rstrip('/')
    parts = path.split('/')
    candidates = [path] if anchored else ['/'.join(parts[i:]) for i in range(len(parts))]
    flat = p.replace('**', '*')
    for cand in candidates:
        if fnmatch.fnmatchcase(cand, flat) or fnmatch.fnmatchcase(cand, flat + '/*') or cand.startswith(p + '/'):
            return True
    return False


def sample_for(entry):
    """A concrete path an ignore pattern stands for, used to test deny coverage."""
    e = entry.strip().lstrip('/')
    if e.startswith('**/'):
        e = e[3:]
    if e.endswith('/'):
        e += 'x'
    e = re.sub(r'(?<=[^.*/])\*$', '', e)
    return e.replace('*', 'x')


def deny_rule(entry):
    e = entry.strip()
    if e.startswith('/'):
        e = e[1:]
    pattern = e if e.startswith('**/') else './' + e
    if pattern.endswith('/'):
        pattern += '**'
    return 'Read(%s)' % pattern


def command_words(command):
    """Lower-case words of a command: its name, flags and their non-path values, and non-path arguments."""
    words = set()
    for i, token in enumerate(command.lower().replace('"', ' ').replace("'", ' ').split()):
        if i and token.startswith('-'):
            flag, _, value = token.partition('=')
            token = flag if '/' in value else token  # --fix=src/ checks fix; --mode=apply checks apply too
        elif i and '/' in token:
            continue  # a path such as tests/fix_parser.py
        words.update(w for w in re.split(r'[/=._:-]+', token) if w)
    return words


def mutating(command):
    """True when a word of a command is a mutating verb, as in `bin/sdlc apply` or `npm run lint:fix`."""
    return bool(command_words(command) & MUTATING)


def checking(command):
    """True when a word of a command names a check, as in `bin/sdlc check`."""
    return bool(command_words(command) & set(CHECK_NAMES))


def version_tuple(version):
    return tuple(int(n) for n in version.split('.')) if re.fullmatch(r'\d+\.\d+\.\d+', version or '') else None


def frontmatter_keys(text):
    if not text.startswith('---'):
        return set()
    end = text.find('\n---', 3)
    block = text[3:end] if end > 0 else ''
    return set(re.findall(r'^([A-Za-z_-]+)\s*:', block, re.M))


def line_of(text, needle):
    for number, line in enumerate((text or '').splitlines(), 1):
        if needle in line:
            return number
    return None


def scrub(command):
    """Mask token-looking values in hook commands before printing."""
    return re.sub(r'(?i)((?:token|secret|password|passwd|api[_-]?key|bearer|authorization)\S*?[=: ]\s*)\S+',
                  r'\1***', command)


def link_targets(line):
    """Relative paths a prose line points at: Markdown links and link definitions, and bare or backticked .md paths."""
    found = LINK.findall(line) + LINK_DEF.findall(line) + MD_PATH.findall(LINK.sub(' ', line))
    targets = []
    for target in found:
        if re.match(r'[a-z][a-z0-9+.-]*:', target, re.I) or target.startswith(('#', '/', '~')):
            continue  # a URL, an anchor in the same file or an absolute path
        target = urllib.parse.unquote(target.split('#', 1)[0].split('?', 1)[0])
        if target and target not in targets:
            targets.append(target)
    return targets


def identity(path):
    """The file a path names, through symlinks and case-insensitive file systems; None when it doesn't exist."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return stat.st_dev, stat.st_ino


def capped(items, name, truncated):
    if len(items) > CAP:
        truncated[name] = len(items) - CAP
        return items[:CAP]
    return items


def dir_words(segment):
    """Lower-case words of one directory name, split at punctuation and case changes, trailing digits dropped."""
    words = (re.sub(r'[0-9]+$', '', w.lower()) for w in re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+', segment))
    return {w for w in words if w}


def dir_kind(name):
    """'data' for a directory name with a data word, 'test' for one with a test word, else None."""
    words = dir_words(name)
    return 'data' if words & DATA_WORDS else 'test' if words & TEST_WORDS else None


def data_path(rel, nested_instruction=False, eval_cases=(), plugin_roots=()):
    """True for test data: a path below a data directory, a test directory or an eval case.

    A test directory's own CLAUDE.md is a nested instruction file; one any deeper is data. A plugin root's own
    name never makes it data.
    """
    dirs = rel.split('/')[:-1]
    for index, name in enumerate(dirs):
        kind = dir_kind(name)
        if not kind or '/'.join(dirs[:index + 1]) in plugin_roots:
            continue
        if kind == 'data' or not nested_instruction or index < len(dirs) - 1:
            return True
    return any(rel.startswith(case + '/') for case in eval_cases)


class Scan:
    """One read-only scan of a project root."""

    ceiling = None  # highest directory checked for CLAUDE files above the project; None is the filesystem root

    def __init__(self, root, git, catalog, claude_version, user=False):
        self.root, self.git, self.catalog, self.user = root, git, catalog, user
        self.claude_version = claude_version
        self.findings, self.limits, self.truncated, self.exact = [], [], {}, {}
        self.no_matcher = set(catalog.get('no_matcher_events') or [])
        self.files, self.dirs = self.walk()
        self.fileset = set(self.files)
        self.eval_cases = sorted({f.rsplit('/', 1)[0] for f in self.files
                                  if '/' in f and f.split('/')[-1] in EVAL_CASE_FILES})
        self.plugin_roots = {d.rsplit('/', 1)[0] if '/' in d else '' for d in self.dirs
                             if d.split('/')[-1] in PLUGIN_DIRS}

    # -- filesystem -------------------------------------------------------
    def walk(self):
        files, dirs = [], set()
        for current, subdirs, names in os.walk(self.root):
            rel = os.path.relpath(current, self.root).replace(os.sep, '/')
            rel = '' if rel == '.' else rel
            depth = rel.count('/') + 1 if rel else 0
            in_skills = rel.split('/')[-1] == 'skills'

            def skill_like(d):  # skill names such as build/ are not build output; node_modules/, .git/ never are
                return in_skills and re.fullmatch(r'[a-z0-9][a-z0-9-]*', d) and (
                    d not in DEPENDENCY_DIRS or os.path.isfile(os.path.join(current, d, 'SKILL.md')))
            subdirs[:] = sorted(d for d in subdirs if (d not in SKIP_DIRS or skill_like(d))
                                and not os.path.islink(os.path.join(current, d)))
            if depth >= MAX_DEPTH:
                subdirs[:] = []
            dirs.update(rel + '/' + d if rel else d for d in subdirs)
            for name in sorted(names):
                files.append(rel + '/' + name if rel else name)
                if len(files) >= MAX_FILES:
                    self.limits.append('tree walk stopped at %d files; later files not checked' % MAX_FILES)
                    return files, dirs
        return files, dirs

    def abs(self, rel):
        return os.path.join(self.root, *rel.split('/'))

    def exists(self, rel):
        return rel in self.fileset or rel in self.dirs or os.path.exists(self.abs(rel))

    def read(self, path, rel=None):
        """Read a text file, refusing secret-like paths and ~/.claude.json."""
        rel = rel or os.path.basename(path)
        if secret_like(rel) or os.path.realpath(path) == os.path.realpath(os.path.join(HOME, '.claude.json')):
            return None
        try:
            with open(path, 'rb') as handle:
                data = handle.read(MAX_READ)
        except OSError:
            return None
        if b'\0' in data[:1024]:
            return None
        return data.decode('utf-8', 'replace')

    def text(self, rel):
        return self.read(self.abs(rel), rel) if rel in self.fileset else None

    def load_json(self, rel, path=None):
        """Return (state, data, raw) for a JSON file: ok, invalid-json, too-large, unreadable or missing."""
        path = path or self.abs(rel)
        if not os.path.isfile(path):
            return 'missing', None, None
        if os.path.getsize(path) > MAX_READ:
            return 'too-large', None, None
        raw = self.read(path, rel)
        if raw is None:
            return 'unreadable', None, None
        try:
            return 'ok', json.loads(raw), raw
        except ValueError as error:
            return 'invalid-json', 'line %s: %s' % (getattr(error, 'lineno', '?'), getattr(error, 'msg', 'invalid')), raw

    def ignored(self, rels):
        """Root-relative paths ignored by git (or a plain .gitignore match without git)."""
        rels = [r for r in rels if r and not r.startswith('..')]
        if not rels:
            return set()
        if self.git:
            proc = run(['git', '-C', self.root, 'check-ignore', '--stdin'], '\n'.join(rels) + '\n')
            if proc is not None and proc.returncode in (0, 1):
                return set(proc.stdout.splitlines())
        patterns = [p.strip().lstrip('/') for p in (self.text('.gitignore') or '').splitlines()
                    if p.strip() and not p.startswith(('#', '!'))]
        return {r for r in rels if any(read_pattern_matches(p, r) for p in patterns)}

    def data(self, rel, nested_instruction=False):
        """True when a project file is test data (see data_path), also through a symlink, or a link out of the project."""
        if data_path(rel, nested_instruction, self.eval_cases, self.plugin_roots):
            return True
        if not os.path.islink(self.abs(rel)):
            return False
        real = os.path.relpath(os.path.realpath(self.abs(rel)), self.root).replace(os.sep, '/')
        return real.startswith('../') or real == '..' or data_path(real, nested_instruction, self.eval_cases, self.plugin_roots)

    def inside(self, path):
        real = os.path.realpath(path)
        return os.path.commonpath([real, self.root]) == self.root

    def references(self, text, base):
        """(file identity, line number, line, path) for each project file a text's prose points at, from base or the root."""
        found = []
        for number, line in prose(text):
            for target in link_targets(line):
                for start in (base, self.root):
                    path = os.path.normpath(os.path.join(start, target))
                    if os.path.isfile(path) and self.inside(path):
                        found.append((identity(path), number, line, self.display(path)))
                        break
        return found

    def display(self, path):
        rel = os.path.relpath(path, self.root)
        return rel.replace(os.sep, '/') if not rel.startswith('..') else path

    # -- findings ---------------------------------------------------------
    def source(self, key):
        """The catalog's doc URL and heading for a doc key, so reports cite them verbatim."""
        doc = self.catalog.get('docs', {}).get(key) or {}
        return {'url': doc.get('url'), 'heading': doc.get('heading')}

    def add(self, fid, grade, severity, title, path, evidence, fix, doc, confidence='high', line=None, subject=None):
        finding = {'id': fid, 'grade': grade, 'severity': severity, 'title': title, 'path': path,
                   'change': CHANGE_TITLES[fid.split(':')[0]].format(path=path, subject=subject or path),
                   'evidence': evidence[:300], 'fix': fix, 'source': self.source(doc), 'confidence': confidence}
        if line:
            finding['line'] = line
        if not any(f['id'] == fid for f in self.findings):
            self.findings.append(finding)

    def typed(self, value, expected, path, key, doc, raw=None, required=False):
        """True when value has the expected type; otherwise records a wrong-type finding."""
        kinds = {'list': list, 'object': dict, 'string or list': (str, list)}
        if (value is None and not required) or isinstance(value, kinds[expected]):
            return value is not None
        self.add('wrong-type:%s:%s' % (path, key), 'correctness', 'high', 'Config value has the wrong type', path,
                 '%s is %s, expected %s' % (key, 'null' if value is None else type(value).__name__, expected),
                 'Make %s a%s %s; Claude Code rejects or ignores a value of the wrong type.'
                 % (key, 'n' if expected[0] == 'o' else '', expected), doc,
                 line=line_of(raw, '"%s"' % key.split('.')[-1].split('[')[0]))
        return False

    def too_large(self, path, doc):
        self.add('too-large:' + path, 'correctness', 'low', 'File too large to check', path,
                 'over %d KiB; not parsed, so its contents were not checked' % (MAX_READ // 1024),
                 'Check %s by hand, or shrink it.' % path, doc, confidence='medium')

    # -- inventory --------------------------------------------------------
    def instructions(self):
        """Instruction files, their @imports (recursively) and whether each is loaded."""
        found, seen = [], set()

        def keep(path, abs_path, kind):  # one entry per real file, under its first displayed name
            if os.path.realpath(abs_path) not in seen:
                seen.add(os.path.realpath(abs_path))
                found.append({'path': path, 'abs': abs_path, 'kind': kind})

        for rel in ROOT_INSTRUCTIONS:
            if rel in self.fileset:
                keep(rel, self.abs(rel), 'project')
        for rel in self.files:
            if rel.endswith('/CLAUDE.md') and rel != '.claude/CLAUDE.md' and rel.count('/') <= 3 \
                    and not self.data(rel, nested_instruction=True):
                keep(rel, self.abs(rel), 'nested')
        if self.user:
            config = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(HOME, '.claude')
            path = os.path.join(config, 'CLAUDE.md')
            if os.path.isfile(path):
                keep(path, path, 'user')
        queue = list(found)
        while queue:
            item = queue.pop(0)
            item['text'] = self.read(item['abs'], item['path']) or ''
            item['lines'] = len(item['text'].splitlines())
            item['imports'], item['reals'] = [], set()
            for number, line in prose(item['text']):
                for target in IMPORT.findall(re.sub(r'`[^`]*`', ' ', line)):
                    target = target.rstrip('.,;:!?)')
                    if '/' not in target and not re.search(r'\.[A-Za-z][\w-]*$', target):
                        continue
                    if target.startswith('~/'):
                        resolved = os.path.join(HOME, target[2:])
                    else:
                        resolved = os.path.normpath(os.path.join(os.path.dirname(item['abs']), target))
                    ok = os.path.exists(resolved)
                    item['imports'].append({'target': target, 'line': number, 'exists': ok})
                    real = os.path.realpath(resolved)
                    item['reals'].add(real)
                    if ok and resolved.endswith('.md') and real not in seen and item.get('depth', 0) < 5:
                        seen.add(real)
                        queue.append({'path': self.display(resolved), 'abs': resolved, 'kind': 'import',
                                      'depth': item.get('depth', 0) + 1, 'parent': item})
                        found.append(queue[-1])
        # Which files load follows the docs' default Project instructions setting (memory#agents-md).
        claude_files = [(f['path'], f['abs']) for f in found if f['kind'] == 'project' and f['path'] in CLAUDE_FILES]
        parent = os.path.dirname(self.root)  # one above the project counts too; ~/.claude/CLAUDE.md doesn't
        while self.ceiling is None or os.path.commonpath([parent, self.ceiling]) == self.ceiling:
            claude_files += [(path, path) for path in (os.path.join(parent, rel) for rel in CLAUDE_FILES)
                             if os.path.isfile(path) and path != os.path.join(HOME, '.claude', 'CLAUDE.md')]
            if os.path.dirname(parent) == parent:
                break
            parent = os.path.dirname(parent)
        version = version_tuple(self.claude_version)
        direct = not claude_files and not (version and version < AGENTS_MD_READ)
        for item in found:
            item['loaded'] = item['kind'] != 'import' and (item['path'] not in AGENTS_FILES or direct)
            if item['path'] in AGENTS_FILES and item['kind'] == 'project':
                item['blocked_by'] = claude_files
                if direct:
                    item['why'] = ('read directly: no CLAUDE.md, .claude/CLAUDE.md or CLAUDE.local.md; adding one '
                                   'stops that unless it imports this file')
                elif claude_files:
                    names = [name for name, _ in claude_files]
                    item['why'] = ("%s exists and doesn't import it" % names[0] if len(names) == 1 else
                                   "%s exist and don't import it" % ' and '.join(names))
                else:
                    item['why'] = 'Claude Code %s reads it only through an import; %s and later read it directly' % (
                        self.claude_version, '.'.join(map(str, AGENTS_MD_READ)))
        changed = True
        while changed:  # an import loads with its parent; an AGENTS file also loads when a loaded file imports it
            changed = False
            for item in found:
                if item['loaded']:
                    continue
                real = os.path.realpath(item['abs'])
                importer = item['parent'] if item['kind'] == 'import' else next(
                    (o for o in found if o is not item and o['loaded'] and real in o['reals']), None)
                if importer and importer['loaded']:
                    item['loaded'] = changed = True
                    if item['kind'] != 'import':
                        item['why'] = 'imported by %s' % importer['path']
        return found

    @staticmethod
    def loading(instructions):
        """One sentence on which project instruction files load, for the report to quote."""
        roots = [i for i in instructions if i['kind'] == 'project']
        if not roots:
            return 'No project instruction file exists, so none loads.'
        text = 'Loaded at session start: %s.' % (', '.join(
            i['path'] + (' (%s)' % i['why'] if i.get('why') else '') for i in roots if i['loaded']) or 'none')
        skipped = ['%s (%s)' % (i['path'], i['why']) for i in roots if not i['loaded']]
        if skipped:
            text += ' Not loaded: %s.' % '; '.join(skipped)
        if any(i['loaded'] and i.get('why', '').startswith('read directly') for i in roots):
            return text + (' This assumes the default Project instructions setting. A user-level setting, a disabled '
                           'built-in AGENTS.md plugin, the first session after upgrading from 2.1.276 or earlier, or '
                           '2.1.277 to 2.1.280 on Amazon Bedrock or with telemetry off can stop AGENTS.md loading.')
        return text + ' This is the default Project instructions setting; a user-level setting can change it.'

    def settings(self):
        files = [(rel, self.abs(rel), 'project') for rel in PROJECT_SETTINGS]
        if self.user:
            config = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(HOME, '.claude')
            path = os.path.join(config, 'settings.json')
            files.append((self.display(path), path, 'user'))
        out = []
        for rel, path, scope in files:
            state, data, raw = self.load_json(os.path.basename(rel), path)
            if state == 'missing':
                continue
            out.append({'path': rel, 'scope': scope, 'state': state, 'root': data if state == 'ok' else None,
                        'data': data if state == 'ok' and isinstance(data, dict) else {},
                        'raw': raw or '', 'error': data if state == 'invalid-json' else None})
        return out

    def plugin_manifests(self):
        manifests = []
        for rel in self.files:
            parts = rel.split('/')
            if len(parts) >= 2 and parts[-2] == '.claude-plugin' and parts[-1] in ('plugin.json', 'marketplace.json') \
                    and len(parts) - 2 <= 3 and not self.data(rel):
                root = '/'.join(parts[:-2])
                state, data, _ = self.load_json(rel)
                skills, named = set(), set()
                base = (root + '/') if root else ''
                if self.exists(base + 'skills'):
                    skills.add(base + 'skills')
                if state == 'ok' and isinstance(data, dict):
                    declared = data.get('skills')
                    if self.typed(declared, 'string or list', rel, 'skills', 'plugins'):
                        for item in [declared] if isinstance(declared, str) else declared:
                            if isinstance(item, str):
                                cand = os.path.normpath(base + strip_dot(item)).replace(os.sep, '/')
                                if cand in self.dirs:
                                    skills.add(cand)
                                    named.add(cand)
                    plugins = data.get('plugins')
                    for plugin in plugins if self.typed(plugins, 'list', rel, 'plugins', 'plugins') else []:
                        source = plugin.get('source') if isinstance(plugin, dict) else None
                        if isinstance(source, str) and source.startswith('./'):
                            cand = os.path.normpath(base + source[2:] + '/skills').replace(os.sep, '/')
                            if cand in self.dirs:
                                skills.add(cand)
                manifests.append({'path': rel, 'root': root or '.', 'kind': parts[-1][:-5], 'state': state,
                                  'data': data if state == 'ok' else None, 'skill_dirs': sorted(skills),
                                  'declared_skills': named - {base + 'skills'}})
        return manifests

    # -- signals ----------------------------------------------------------
    def check_commands(self, corpus, ci_text, loaded=()):
        """Check commands; sets self.exact to the exact, non-mutating calls of each to pre-approve."""
        detected, invocations, from_mention = [], {}, set()

        def add(command, source):
            if not any(c['command'] == command for c in detected):
                detected.append({'command': command, 'source': source})

        for rel in self.files:
            parts = rel.split('/')
            if len(parts) == 2 and parts[0] in ('bin', 'script', 'scripts') and parts[1].split('.')[0] in CHECK_NAMES \
                    and not re.search(r'\s', parts[1]) \
                    and os.access(self.abs(rel), os.X_OK):
                add(rel, rel)
        makefile = self.text('Makefile') or ''
        for target in re.findall(r'^(test|check|lint|ci)\s*:(?!=)', makefile, re.M):
            add('make ' + target, 'Makefile')
        state, package, _ = self.load_json('package.json') if 'package.json' in self.fileset else ('missing', None, None)
        if state == 'ok' and isinstance(package, dict) and isinstance(package.get('scripts'), dict):
            runner = 'pnpm' if 'pnpm-lock.yaml' in self.fileset else 'yarn' if 'yarn.lock' in self.fileset else 'npm'
            for name in ('test', 'lint', 'check', 'typecheck'):
                script = package['scripts'].get(name)
                if isinstance(script, str) and 'no test specified' not in script:
                    run_word = '' if name == 'test' or runner == 'yarn' else 'run '
                    add('%s %s%s' % (runner, run_word, name), 'package.json')
        if 'go.mod' in self.fileset:
            add('go test ./...', 'go.mod')
        if 'Cargo.toml' in self.fileset:
            add('cargo test', 'Cargo.toml')
        python_markers = [m for m in ('pyproject.toml', 'setup.cfg', 'setup.py') if m in self.fileset]
        if not python_markers and any(f.startswith('tests/') and f.endswith('.py') for f in self.files):
            python_markers = ['tests/']
        if python_markers:
            mentioned = None
            for snippet in [s for text in corpus.values() for s in code_snippets(text)] + ci_text.splitlines():
                match = re.search(r'(python3?(?:\.\d+)? -m (?:pytest|unittest)|\bpytest)\b', snippet)
                if match:
                    mentioned = match.group(1)
                    break
            pyproject = self.text('pyproject.toml') or ''
            configured = '[tool.pytest' in pyproject or 'pytest.ini' in self.fileset or 'conftest.py' in self.fileset \
                or '[tool:pytest]' in (self.text('setup.cfg') or '')
            add(mentioned or ('pytest' if configured else 'python -m unittest'), python_markers[0])
        # Commands documented in instruction files.
        for path, text in corpus.items():
            for snippet in code_snippets(text):
                for part in split_commands(snippet):
                    part = strip_dot(part)
                    base = next((c['command'] for c in detected if part == strip_dot(c['command'])
                                 or part.startswith(strip_dot(c['command']) + ' ')), None)
                    if base is None:
                        match = RUNNER.match(part)
                        first = part.split()[0]
                        if match:
                            base = match.group(1)
                        elif first.split('/')[0] in ('bin', 'script', 'scripts') and first in self.fileset \
                                and os.access(self.abs(first), os.X_OK) and (
                                re.search(r'test|check|lint|ci|verify', first.split('/')[-1]) or path in loaded):
                            base = first
                            from_mention.add(base)
                        else:
                            continue
                        add(base, path)
                    invocations.setdefault(base, []).append(part)
        # Only exact calls are pre-approved: a wildcard such as `make test *` also allows `make test deploy`.
        self.exact = {}
        for entry in list(detected):
            command = entry['command']
            seen = invocations.get(command, [])
            entry['args'] = any(p != strip_dot(command) for p in seen)
            calls = ([] if command in from_mention else [command]) + [
                p for p in seen if command not in from_mention or checking(p)]
            safe = []
            for p in calls:
                if PLAIN_CALL.fullmatch(p) and not re.search(r'\b[A-Z][A-Z_]+\b', p) and not mutating(p) \
                        and p not in safe:
                    safe.append(p)
            if not safe:
                detected.remove(entry)
                continue
            self.exact[command] = safe
        return detected

    def mentioned(self, command, corpus_text):
        pattern = r'(?<![\w/.-])(?:\./)?' + re.escape(strip_dot(command)) + r'(?![\w-])'
        return re.search(pattern, corpus_text) is not None

    def procedure_docs(self, instructions, skill_dirs=()):
        """Numbered procedure docs outside test data, whether a skill covers each, and where loaded instructions link it."""
        reached = {}
        for item in team_instructions(instructions):
            for ident, number, line, _ in self.references(item['text'], os.path.dirname(item['abs'])):
                reached.setdefault(ident, (item['path'], number, line))
        # Project skills and commands cover a doc by path or name. A doc a plugin's skill links (a SKILL.md in
        # skills/ beside .claude-plugin/ or .codex-plugin/, or in a manifest's skill directory) is that skill's
        # reference material, product content rather than a team procedure.
        project_skills = [self.text(f) or '' for f in self.files
                          if re.fullmatch(r'\.claude/skills/[^/]+/SKILL\.md|\.claude/commands/.+\.md', f)]
        plugin_skills = {(root + '/' if root else '') + 'skills' for root in self.plugin_roots} | set(skill_dirs)
        product = {ident for f in self.files if f.split('/')[-1] == 'SKILL.md' and not self.data(f)
                   and any(f.startswith(d + '/') for d in plugin_skills)
                   for ident, _, _, _ in self.references(self.text(f) or '', os.path.dirname(self.abs(f)))}
        paths = {i['path'] for i in instructions}
        docs = []
        for rel in self.files:
            name = rel.split('/')[-1]
            parts = rel.split('/')
            if not rel.endswith('.md') or rel in paths or name == 'SKILL.md' or 'skills' in parts \
                    or parts[0] == '.claude' or re.match(r'(README|CHANGELOG|LICENSE)', name, re.I) or self.data(rel):
                continue
            ident = identity(self.abs(rel))
            if ident in product:
                continue
            text = self.text(rel) or ''
            steps = sum(1 for _, line in prose(text) if NUMBERED.match(line))
            h1 = re.search(r'^#\s+(.+)$', text, re.M)
            title = h1.group(1).strip() if h1 else name[:-3]
            if re.match(r'CONTRIBUTING', name, re.I):
                hit = steps >= 5
            else:
                hit = steps >= 5 or (steps >= 3 and PROCEDURE_WORDS.search(name + ' ' + title) is not None)
            if hit:
                stem = name[:-3]
                has_skill = any(
                    rel in t or re.search(r'\b' + re.escape(stem) + r'\b', t, re.I) for t in project_skills)
                via = reached.get(ident)
                docs.append({'path': rel, 'steps': steps, 'title': title[:120], 'has_skill': has_skill,
                             'linked_from': '%s:%d' % via[:2] if via else None,
                             'on_demand': any(ON_DEMAND.search(line) and SKILL_WORDS.search(line)
                                              for line in [via[2] if via else ''] + [l for _, l in prose(text)])})
        return docs

    def declines(self, instructions):
        """Features the project documents a deliberate choice against, each with the sentence, file and line.

        Read from the loaded instructions, then the Markdown files their prose links (outside test data), then
        README.md; the first decline of each feature counts.
        """
        loaded = team_instructions(instructions)
        sources, seen = [], set()
        for path, abs_path in [(i['path'], i['abs']) for i in loaded] + [
                (rel, self.abs(rel)) for i in loaded
                for _, _, _, rel in self.references(i['text'], os.path.dirname(i['abs']))] + [
                ('README.md', self.abs('README.md'))]:
            ident = identity(abs_path)
            if ident and ident not in seen and path.lower().endswith('.md') and not self.data(path) \
                    and os.path.isfile(abs_path) and self.inside(abs_path):
                seen.add(ident)
                sources.append((path, self.read(abs_path, path) or ''))
        found = {}
        for path, text in sources:
            for sentence, line_at in sentences(text):
                if UNSURE.search(sentence) or (OTHER_TOOLS.search(sentence) and not CLAUDE_NAMED.search(sentence)):
                    continue
                if DECLINE_LIMIT.search(sentence):
                    continue
                for feature, label, noun, forms in DECLINE_FORMS:
                    if feature not in found and any(form.search(sentence.rstrip('.!')) for form in forms):
                        found[feature] = {'feature': feature, 'label': label, 'path': path,
                                          'line': line_at(noun.search(sentence).start()), 'quote': sentence[:400]}
        return [found[feature] for feature, _, _ in DECLINABLE if feature in found]

    # -- correctness checks -----------------------------------------------
    def check_settings(self, settings):
        for s in settings:
            path, raw, data = s['path'], s['raw'], s['data']
            if s['state'] == 'invalid-json':
                self.add('invalid-json:' + path, 'correctness', 'high', 'Settings file is not valid JSON', path,
                         s['error'], 'Fix the JSON syntax; Claude Code ignores the whole file until it parses.', 'config-causes')
                continue
            if s['state'] == 'too-large':
                self.too_large(path, 'settings-index')
                continue
            if s['state'] == 'ok' and not isinstance(s['root'], dict):
                self.typed(s['root'], 'object', path, '(root)', 'settings-index', raw, required=True)
                continue
            perms = data.get('permissions') if self.typed(data.get('permissions'), 'object', path, 'permissions',
                                                          'permission-rules', raw) else {}
            for kind in ('allow', 'deny', 'ask'):
                rules = perms.get(kind)
                for rule in rules if self.typed(rules, 'list', path, 'permissions.' + kind, 'permission-rules', raw) else []:
                    match = re.fullmatch(r'(Write|NotebookEdit|Glob)\((.+)\)', rule.strip(), re.S) if isinstance(rule, str) else None
                    if match:
                        tool = 'Read' if match.group(1) == 'Glob' else 'Edit'
                        self.add('write-rule:%s:%s' % (path, rule), 'correctness', 'medium',
                                 '%s(path) rule never matches' % match.group(1), path,
                                 'permissions.%s contains "%s"' % (kind, rule),
                                 'Replace with "%s(%s)"' % (tool, match.group(2)), 'write-rules',
                                 line=line_of(raw, json.dumps(rule)))
            if s['scope'] == 'project':
                mode = perms.get('defaultMode')
                version = version_tuple(self.claude_version)
                if mode in ('bypassPermissions', 'auto'):
                    self.add('default-mode:' + path, 'correctness', 'high',
                             'defaultMode "%s" in project settings' % mode, path,
                             ('permissions.defaultMode is "%s"; Claude Code %s applies it to everyone who opens the repo '
                              '(ignored from project/local settings only since 2.1.257)' % (mode, self.claude_version))
                             if version and version < DEFAULT_MODE_IGNORED else
                             'permissions.defaultMode is "%s"; ignored from project/local settings since 2.1.257; '
                             'before that bypass applied to everyone who opens the repo' % mode,
                             'Remove "defaultMode" from %s; users who want it set it in user settings '
                             '(~/.claude/settings.json).' % path, 'ignored-values', line=line_of(raw, '"defaultMode"'))
                if 'autoMode' in data:
                    self.add('auto-mode:' + path, 'correctness', 'medium', 'autoMode in project settings', path,
                             'autoMode is read from user or managed settings only',
                             'Move "autoMode" to ~/.claude/settings.json or managed settings.', 'settings-index',
                             line=line_of(raw, '"autoMode"'))
                if 'mcpServers' in data:
                    self.add('mcp-location:' + path, 'correctness', 'medium', 'mcpServers in settings is not read', path,
                             'mcpServers key in %s' % path, 'Move the servers to a root .mcp.json '
                             '({"mcpServers": {...}}).', 'config-causes', line=line_of(raw, '"mcpServers"'))
            hooks = data.get('hooks') if self.typed(data.get('hooks'), 'object', path, 'hooks', 'check-hooks', raw) else {}
            for event, groups in sorted(hooks.items()):
                groups = groups if self.typed(groups, 'list', path, 'hooks.' + event, 'check-hooks', raw) else []
                for index, group in enumerate(groups):
                    if not isinstance(group, dict):
                        continue
                    matcher = group.get('matcher')
                    if 'matcher' in group and not isinstance(matcher, str):
                        self.add('matcher-type:%s:%s' % (path, event), 'correctness', 'high',
                                 'Hook matcher is not a string', path,
                                 '%s matcher is %s' % (event, type(matcher).__name__),
                                 'Use one string, e.g. "matcher": "%s"' % ('|'.join(str(m) for m in matcher)
                                                                         if isinstance(matcher, list) else 'Edit|Write'),
                                 'check-hooks', line=line_of(raw, '"%s"' % event))
                    elif event in self.no_matcher and isinstance(matcher, str) and matcher not in ('', '*'):
                        self.add('matcher-ignored:%s:%s' % (path, event), 'correctness', 'low',
                                 '%s hooks ignore matchers' % event, path,
                                 '%s matcher "%s" is silently ignored' % (event, matcher),
                                 'Remove the matcher; %s hooks run on every %s event.' % (event, event),
                                 'hooks-matchers', line=line_of(raw, '"%s"' % event))
                    key = 'hooks.%s[%d].hooks' % (event, index)
                    if not self.typed(group.get('hooks'), 'list', path, key, 'check-hooks', raw) or s['scope'] != 'project':
                        continue
                    for hook in group['hooks']:
                        command = hook.get('command') if isinstance(hook, dict) else None
                        for script in hook_scripts(command if isinstance(command, str) else ''):
                            if not self.exists(script):
                                self.add('hook-script:%s:%s' % (path, script), 'correctness', 'high',
                                         'Hook script does not exist', path, '%s hook runs %s' % (event, script),
                                         'Create %s (executable) or fix the path in the hook command.' % script,
                                         'check-hooks', line=line_of(raw, script))

    def check_files(self, manifests):
        for rel in ['.mcp.json'] + [m['path'] for m in manifests]:
            if rel in self.fileset:
                state, error, _ = self.load_json(rel)
                if state == 'invalid-json':
                    self.add('invalid-json:' + rel, 'correctness', 'high', 'File is not valid JSON', rel, error,
                             'Fix the JSON syntax; Claude Code cannot load it.', 'config-causes')
                elif state == 'too-large':
                    self.too_large(rel, 'config-causes')
        if '.claudeignore' in self.fileset:
            entries = [e.strip() for e in (self.text('.claudeignore') or '').splitlines()
                       if e.strip() and not e.strip().startswith(('#', '!'))]
            secret = [e for e in entries if secret_pattern(e)]
            rules = [deny_rule(e) for e in (secret or entries)][:20]
            self.add('claudeignore', 'correctness', 'high' if secret else 'medium', '.claudeignore is not read',
                     '.claudeignore', 'Claude Code does not read .claudeignore; %d entr%s, %d secret-like'
                     % (len(entries), 'y' if len(entries) == 1 else 'ies', len(secret)),
                     'Add to .claude/settings.json: ' + json.dumps({'permissions': {'deny': rules}})
                     + ' then delete .claudeignore.', 'read-edit-rules')
        for rel in ('.claude/hooks.json', 'hooks.json'):
            if rel in self.fileset and not (rel == 'hooks.json' and '.claude-plugin/plugin.json' in self.fileset):
                self.add('hooks-file:' + rel, 'correctness', 'medium', 'Hooks file is not read', rel,
                         '%s is not a settings location' % rel,
                         'Move its contents under "hooks" in .claude/settings.json.', 'config-causes')
        for rel in ('.claude/.mcp.json', '.claude/mcp.json'):
            if rel in self.fileset:
                self.add('mcp-location:' + rel, 'correctness', 'medium', 'MCP config in the wrong place', rel,
                         'project MCP servers are read from the root .mcp.json',
                         'Move the servers to a root .mcp.json.', 'config-causes')
        skill_dirs = ['.claude/skills'] + [d for m in manifests for d in m['skill_dirs']]
        defaults = {'.claude/skills'} | (set(skill_dirs) - {d for m in manifests for d in m['declared_skills']})
        for base in sorted(set(skill_dirs)):
            try:
                names = sorted(os.listdir(self.abs(base)))
            except OSError:
                continue
            if 'SKILL.md' in names and base not in defaults:
                continue  # a manifest path naming one skill directory, not a directory of skills
            for name in names:
                rel = base + '/' + name
                if os.path.isfile(self.abs(rel)) and name.endswith('.md') and name != 'README.md':
                    self.add('flat-skill:' + rel, 'correctness', 'medium', 'Skill file is not in a skill directory', rel,
                             'skills load only from <name>/SKILL.md', 'Move it to %s/%s/SKILL.md with name and '
                             'description frontmatter.' % (base, name[:-3]), 'skill-locations')
                elif os.path.isdir(self.abs(rel)) and not name.startswith(('.', '_')):
                    try:
                        inner = os.listdir(self.abs(rel))
                    except OSError:
                        continue
                    if inner and 'SKILL.md' not in inner and name not in DEPENDENCY_DIRS:
                        self.add('skill-missing:' + rel, 'correctness', 'medium', 'Skill directory has no SKILL.md', rel,
                                 'contains %s' % ', '.join(sorted(inner)[:5]),
                                 'Add %s/SKILL.md with name and description frontmatter (exact file name).' % rel,
                                 'skill-locations')

    def check_instructions(self, instructions):
        for item in instructions:
            path = item['path']
            if item['kind'] == 'project' and not item['loaded']:
                self.add('agents-md-not-loaded:' + path, 'alignment', 'medium', 'AGENTS.md does not load', path,
                         '%s is not loaded: %s' % (path, item['why']),
                         'Add "@%s" to %s so both load, or move what Claude needs into it.' % (
                             os.path.relpath(item['abs'], os.path.dirname(item['blocked_by'][0][1])),
                             item['blocked_by'][0][0])
                         if item['blocked_by'] and not os.path.isabs(item['blocked_by'][0][0]) else
                         'Create CLAUDE.md in the project containing "@%s"; %s above the project otherwise keeps it '
                         'from loading.' % (path, item['blocked_by'][0][0])
                         if item['blocked_by'] else 'Upgrade Claude Code to %s or later, or create a CLAUDE.md containing '
                         '"@%s".' % ('.'.join(map(str, AGENTS_MD_READ)), path),
                         'memory-agents-md', confidence='medium')
            if item['kind'] == 'project' and item['loaded'] and item['lines'] > 200:
                self.add('oversized:' + path, 'alignment', 'medium', 'Instruction file over 200 lines', path,
                         '%d lines' % item['lines'], "Cut it to what Claude can't learn from the repo; move "
                         'procedures to skills and path-specific rules to .claude/rules/.', 'memory-size')
            for imp in item['imports']:
                target = imp['target']
                scope_like = re.fullmatch(r'[\w.-]+/[\w.-]+', target) and not re.search(r'\.[A-Za-z]\w*$', target)
                if not imp['exists'] and not scope_like:
                    self.add('broken-import:%s:%s' % (path, target), 'correctness', 'high', 'Import target missing',
                             path, '@%s does not resolve from %s' % (target, path),
                             'Point the import at an existing file or remove it.', 'memory-imports', line=imp['line'])
            if item['kind'] == 'user' or path.startswith(('/', '~')):
                continue
            base = os.path.dirname(item['abs'])
            candidates = []
            for number, line in prose(item['text']):
                for token in path_tokens(line):
                    if os.path.exists(os.path.join(self.root, token)) or os.path.exists(os.path.join(base, token)):
                        continue
                    rel = os.path.relpath(os.path.normpath(os.path.join(self.root, token)), self.root)
                    if not rel.startswith('..'):
                        candidates.append((number, token, rel.replace(os.sep, '/')))
            ignored = self.ignored(sorted({c[2] for c in candidates}))
            for number, token, rel in candidates:
                if rel not in ignored:
                    self.add('stale-ref:%s:%s' % (path, token), 'correctness', 'medium', 'Referenced path does not exist',
                             path, '%s line %d mentions %s' % (path, number, token),
                             'Point at an existing file, remove the reference, or create %s.' % token,
                             'memory-size', confidence='medium', line=number)

    # -- main -------------------------------------------------------------
    def run(self):
        instructions = self.instructions()
        settings = self.settings()
        manifests = self.plugin_manifests()
        self.check_settings(settings)
        self.check_files(manifests)
        self.check_instructions(instructions)
        project_instr = [i for i in instructions if i['kind'] in ('project', 'nested', 'import')]
        corpus = {i['path']: i['text'] for i in project_instr}
        corpus_text = '\n'.join(corpus.values())
        ci = [f for f in self.files if (f.startswith('.github/workflows/') and f.count('/') == 2
                                        and f.endswith(('.yml', '.yaml'))) or f == '.gitlab-ci.yml']
        ci_text = '\n'.join(self.text(f) or '' for f in ci)
        loaded = [i for i in project_instr if i['loaded'] and i['kind'] != 'nested']
        checks = self.check_commands(corpus, ci_text, {i['path'] for i in loaded})
        documented = [c['command'] for c in checks if self.mentioned(c['command'], corpus_text)]
        for c in checks:
            c['documented'] = c['command'] in documented
        skills = sorted(f for f in self.files if re.fullmatch(r'\.claude/skills/[^/]+/SKILL\.md', f))
        procedures = self.procedure_docs(instructions, [d for m in manifests for d in m['skill_dirs']])
        project_settings = [s for s in settings if s['scope'] == 'project']
        # Coverage that depends on settings contents is not judged when a project settings file was not read.
        blind = ['%s (%s)' % (s['path'], s['state'] if s['state'] != 'ok' else 'not an object')
                 for s in project_settings if not isinstance(s['root'], dict)]
        if blind:
            self.limits.append('%s not checked; allowlist, secret-deny, stop-hook and lsp coverage not judged'
                               % ', '.join(blind))
        allow = [r for s in project_settings for r in rules_of(s['data'], 'allow')]
        deny = [r for s in project_settings for r in rules_of(s['data'], 'deny')]
        hooks = {}
        for s in project_settings:
            for event, groups in (s['data'].get('hooks') or {}).items() if isinstance(s['data'].get('hooks'), dict) else []:
                hooks.setdefault(event, []).extend(groups if isinstance(groups, list) else [])
        plugins_enabled = [k for s in settings if isinstance(s['data'].get('enabledPlugins'), dict)
                           for k, v in s['data']['enabledPlugins'].items() if v]

        # signals
        agent_run = []
        if 'AGENTS.md' in self.fileset:
            agent_run.append('AGENTS.md exists')
        for item in project_instr:
            for number, line in prose(item['text']):
                if AGENT_DIRECTIVE.search(line):
                    agent_run.append('%s:%d addresses agents' % (item['path'], number))
                    break
        for f in ci:
            text = self.text(f) or ''
            if 'anthropics/claude-code-action' in text or re.search(r'\bclaude (-p|--print)\b', text):
                agent_run.append('%s runs Claude Code' % f)
        if 'docs/operations' in self.dirs or any(re.search(r'sdlc', f, re.I) and f.endswith('.md') and not self.data(f)
                                                 for f in self.files):
            agent_run.append('delivery/SDLC docs present')
        typed = []
        for f in self.files:
            name = f.split('/')[-1]
            if f.count('/') <= 2 and (name in LANGUAGES or name.endswith('.csproj')) and name not in typed \
                    and not self.data(f):
                typed.append(name)
        pyproject = self.text('pyproject.toml') or ''
        if re.search(r'^\[tool\.(mypy|pyright)\]', pyproject, re.M):
            typed.append('pyproject.toml [tool.mypy/pyright]')
        lsp_enabled = any('lsp' in k.lower() for k in plugins_enabled)
        secret_paths = []
        for f in self.files:
            parts = f.split('/')
            if self.data(f):
                continue  # sample secrets in test data are not the project's
            if 'secrets' in parts[:-1]:
                d = '/'.join(parts[:parts.index('secrets') + 1]) + '/'
                if not any(s['path_or_pattern'] == d for s in secret_paths):
                    secret_paths.append({'path_or_pattern': d, 'where': 'tree'})
            elif secret_like(f):
                secret_paths.append({'path_or_pattern': f, 'where': 'tree'})
        for ignore, where in (('.gitignore', 'gitignore'), ('.claudeignore', 'claudeignore')):
            for entry in (self.text(ignore) or '').splitlines():
                if entry.strip() and not entry.startswith('#') and secret_pattern(entry) \
                        and not any(s['path_or_pattern'] == entry.strip() for s in secret_paths):
                    secret_paths.append({'path_or_pattern': entry.strip(), 'where': where})
        plugin_checks = None
        evals = sorted({'/'.join(f.split('/')[:f.split('/').index('evals') + 1]) for f in self.files
                        if 'evals' in f.split('/')[:4] and f.split('/')[-1] in ('case.yaml', 'prompt.md')})
        if manifests:
            sources = [i['path'] for i in project_instr] + ci + [f for f in self.files if (
                re.match(r'(README|CONTRIBUTING)', f, re.I) or (f.startswith('docs/') and f.endswith('.md'))
                or f in ('Makefile', 'package.json') or (f.startswith('bin/') and f.count('/') == 1))]
            texts = [self.text(f) or '' for f in sources]
            eval_manifest = any(isinstance(m['data'], dict) and isinstance(m['data'].get('experimental'), dict)
                                and m['data']['experimental'].get('evals') for m in manifests)
            plugins = []
            for m in manifests:
                if m['kind'] != 'plugin':
                    continue
                data = m['data'] if isinstance(m['data'], dict) else {}
                name = data.get('name') if isinstance(data.get('name'), str) else os.path.basename(
                    os.path.abspath(self.abs(m['root'])))
                base = '' if m['root'] == '.' else m['root'] + '/'
                experimental = data.get('experimental') if isinstance(data.get('experimental'), dict) else {}
                suite = bool(experimental.get('evals')) or base + 'evals' in self.dirs or any(
                    e == base + 'evals' or e.startswith(base + 'evals/') for e in evals) or any(
                    f.startswith('evals/%s/' % name) and f.split('/')[-1] in ('case.yaml', 'prompt.md')
                    for f in self.files)
                plugins.append({'name': name, 'path': m['root'], 'eval_suite': suite})
            plugin_checks = {'validate_documented': any('claude plugin validate' in t for t in texts),
                             'eval_documented': any('claude plugin eval' in t for t in texts),
                             'eval_suite': all(p['eval_suite'] for p in plugins) if plugins
                             else bool(evals) or bool(eval_manifest),
                             'plugins': plugins[:CAP]}
        must_rules = []
        for item in project_instr:
            for number, line in prose(item['text']):
                if MUST.search(line) and not MUST_NOT.search(line) and (
                        any(self.mentioned(c['command'], line) for c in checks)
                        or ('`' in line and re.search(r'\brun', line, re.I))):
                    must_rules.append({'path': item['path'], 'line': number, 'text': line.strip()[:160]})

        # coverage findings
        roots = [i for i in instructions if i['kind'] == 'project']
        if not roots:
            listed = ', '.join(c['command'] for c in checks) or 'the build and test commands'
            self.add('no-instructions', 'coverage', 'high', 'No instruction file', '.',
                     'no CLAUDE.md, .claude/CLAUDE.md or AGENTS.md', 'Create a short CLAUDE.md (or run /init) '
                     'recording the check commands: %s.' % listed, 'memory-size', confidence='medium')
        elif checks and not documented:
            self.add('undocumented-checks', 'coverage', 'medium', 'Check commands are not in the instructions',
                     roots[0]['path'], 'found: ' + ', '.join(c['command'] for c in checks),
                     'Add a Commands section to %s listing: %s.' % (roots[0]['path'], ', '.join(
                         c['command'] for c in checks)), 'check-to-run', confidence='medium')
        targets = [c for c in checks if c['documented']] or checks

        uncovered = [c for c in targets if not all(any(bash_rule_matches(r, call) for r in allow)
                                                   for call in self.exact[c['command']])]
        if uncovered and not blind:
            rules = ['Bash(%s)' % call for c in uncovered for call in self.exact[c['command']]]
            self.add('allowlist', 'coverage', 'medium', 'Check commands are not pre-approved', '.claude/settings.json',
                     'no permissions.allow rule covers: ' + ', '.join(c['command'] for c in uncovered),
                     'Add to .claude/settings.json: ' + json.dumps({'permissions': {'allow': rules}}),
                     'permission-rules', confidence='medium')
        read_denies = [r for r in deny if r.strip() == 'Read' or re.fullmatch(r'Read\(.+\)', r.strip(), re.S)]

        def denied(sample):
            return any(r.strip() == 'Read' or read_pattern_matches(r.strip()[5:-1].strip(), sample) for r in read_denies)

        uncovered_secrets = [s for s in secret_paths if not denied(
            sample_for(s['path_or_pattern']) if s['where'] != 'tree' else
            (s['path_or_pattern'] + 'x' if s['path_or_pattern'].endswith('/') else s['path_or_pattern']))]
        if uncovered_secrets and not blind:
            rules = []
            for s in uncovered_secrets:
                rule = deny_rule(s['path_or_pattern'])
                if rule not in rules:
                    rules.append(rule)
            self.add('secret-deny', 'coverage', 'medium', 'Secret paths are not denied', '.claude/settings.json',
                     'not covered by a permissions.deny Read rule: ' + ', '.join(
                         s['path_or_pattern'] for s in uncovered_secrets[:10]),
                     'Add to .claude/settings.json: ' + json.dumps({'permissions': {'deny': rules[:20]}})
                     + ' (a Read deny also blocks Edit).', 'read-edit-rules', confidence='medium')
        stop_hook = any(hooks.get(e) for e in STOP_EVENTS)
        if must_rules and not stop_hook and not blind:
            cmd = next((c['command'] for c in checks for r in must_rules if self.mentioned(c['command'], r['text'])),
                       (documented or [c['command'] for c in checks] or ['<your check command>'])[0])
            cmd = self.exact[cmd][0] if cmd in self.exact else cmd
            settings_json = json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command':
                                        '"$CLAUDE_PROJECT_DIR"/.claude/hooks/stop-check.sh'}]}]}})
            script = ('#!/usr/bin/env bash\n# Block finishing until the check passes.\ninput=$(cat)\n'
                      'case "$input" in *\'"stop_hook_active":true\'*|*\'"stop_hook_active": true\'*) exit 0 ;; esac\n'
                      'cd "$CLAUDE_PROJECT_DIR" || exit 0\nif ! out=$(%s 2>&1); then\n'
                      '  printf \'%%s\\n\' "%s failed:" "$out" | tail -n 60 >&2\n  exit 2\nfi\n' % (cmd, cmd))
            self.add('stop-hook', 'coverage', 'medium', 'Must-run rule is prose only', must_rules[0]['path'],
                     '%s:%d: %s' % (must_rules[0]['path'], must_rules[0]['line'], must_rules[0]['text']),
                     'Add to .claude/settings.json: %s and create .claude/hooks/stop-check.sh (chmod +x):\n%s'
                     % (settings_json, script), 'stop-hook', confidence='medium', line=must_rules[0]['line'])
        optional = []
        for doc in procedures:
            if not doc['has_skill']:
                slug = re.sub(r'[^a-z0-9]+', '-', doc['path'].split('/')[-1][:-3].lower()).strip('-') or 'procedure'
                fix = ('Create .claude/skills/%s/SKILL.md with name and description frontmatter that follows '
                       'the steps in %s (keep the doc as the source and link it).' % (slug, doc['path']))
                if doc['linked_from'] and not doc['on_demand']:
                    # Loaded instructions already lead Claude to it; a skill is a convenience, not a gap.
                    optional.append({'id': 'procedure-skill:' + doc['path'], 'path': doc['path'],
                                     'change': CHANGE_TITLES['procedure-skill'].format(path=doc['path']),
                                     'reason': '%s links it from the loaded instructions' % doc['linked_from'],
                                     'fix': fix, 'source': self.source('procedures-skills')})
                else:
                    self.add('procedure-skill:' + doc['path'], 'coverage', 'medium', 'Procedure has no skill',
                             doc['path'], '%d numbered steps: %s' % (doc['steps'], doc['title']), fix,
                             'procedures-skills', confidence='medium')
        if plugin_checks:
            where = manifests[0]['path']
            if not plugin_checks['validate_documented']:
                dirs = sorted({m['root'] for m in manifests})
                self.add('plugin-validate', 'coverage', 'medium', 'Plugin validation is not run', where,
                         'no instructions, docs, CI or scripts mention claude plugin validate',
                         'Add %s to CI and the documented checks.' % ', '.join(
                             '`claude plugin validate %s`' % d for d in dirs), 'plugin-validate', confidence='medium')
            without = [p for p in plugin_checks['plugins'] if not p['eval_suite']]
            if not plugin_checks['eval_suite'] or not plugin_checks['eval_documented']:
                suites = ('no eval suite: ' + ', '.join('%s (%s)' % (p['name'], p['path']) for p in without)
                          if without else 'eval suite %s' % ('present' if plugin_checks['eval_suite'] else 'missing'))
                self.add('plugin-eval', 'coverage', 'medium', 'Plugin skills are not measured',
                         without[0]['path'] if without else where, '%s; claude plugin eval %s' % (
                             suites, 'documented' if plugin_checks['eval_documented'] else 'not documented'),
                         'Add evals/ cases for the skills of %s and run `claude plugin eval` as a release gate '
                         'or in CI.' % (', '.join(p['name'] for p in without) or 'each plugin'),
                         'plugin-evals', confidence='medium',
                         subject=', '.join(p['name'] for p in without) or 'the plugin skills')
        if typed and not lsp_enabled and not blind:
            langs = sorted({LANGUAGES.get(t, 'csharp' if t.endswith('.csproj') else 'python') for t in typed})
            self.add('lsp', 'coverage', 'low', 'No code-intelligence plugin', '.', 'typed markers: ' + ', '.join(typed),
                     'Install %s from the official marketplace; check /plugin for the exact name.' % ', '.join(
                         l + '-lsp' for l in langs), 'code-intelligence', confidence='medium')

        # documented declines
        declined = self.declines(instructions)
        for entry in declined:
            entry['finding_ids'] = [f['id'] for f in self.findings if f['id'].split(':')[0] == entry['feature']]
        gone = {fid for entry in declined for fid in entry['finding_ids']}
        self.findings = [f for f in self.findings if f['id'] not in gone]

        # dismissed findings
        dismissed = []
        if DISMISSED in self.fileset:
            state, data, _ = self.load_json(DISMISSED)
            entries = data.get('dismissed') if state == 'ok' and isinstance(data, dict) else None
            if not isinstance(entries, list):
                self.limits.append('%s is not valid; nothing dismissed' % DISMISSED)
                entries = []
            reasons = {e['id']: e.get('reason', '') for e in entries if isinstance(e, dict) and isinstance(e.get('id'), str)}
            dismissed = [dict(f, reason=reasons[f['id']]) for f in self.findings if f['id'] in reasons]
            self.findings = [f for f in self.findings if f['id'] not in reasons]
        self.findings.sort(key=lambda f: (GRADES[f['grade']], SEVERITIES[f['severity']], f['id']))

        # baseline
        def ids(*names):
            return [f['id'] for f in self.findings + dismissed if f['id'] in names or f['id'].split(':')[0] in names]

        def coverage(total, missing):
            return 'n/a' if not total else 'met' if not missing else 'missing' if missing == total else 'partial'

        unjudged = ('n/a', 'not checked: ' + ', '.join(blind), [])
        status = {
            'instructions': ('missing' if not roots else 'partial' if ids('oversized') else 'met',
                             ', '.join('%s (%d lines)' % (i['path'], i['lines']) for i in roots) or 'none',
                             ids('no-instructions', 'oversized')),
            'check': ('met' if documented else 'missing' if checks else 'n/a',
                      'documented: ' + (', '.join(documented) or 'none'), ids('undocumented-checks', 'no-instructions')),
            'allowlist': (coverage(len(targets), len(uncovered)), '%d of %d check commands allowed' % (
                len(targets) - len(uncovered), len(targets)), ids('allowlist')),
            'secrets': (coverage(len(secret_paths), len(uncovered_secrets)), '%d of %d secret paths denied' % (
                len(secret_paths) - len(uncovered_secrets), len(secret_paths)), ids('secret-deny')),
            'enforced': ('n/a' if not must_rules else 'met' if stop_hook else 'missing',
                         '%d must-run rules; stop-type hook %s' % (len(must_rules), 'present' if stop_hook else 'absent'),
                         ids('stop-hook')),
        }
        if blind:
            status.update(allowlist=unjudged, secrets=unjudged, enforced=unjudged)
        for entry in declined:
            item = {'allowlist': 'allowlist', 'stop-hook': 'enforced'}.get(entry['feature'])
            if item and entry['finding_ids']:
                status[item] = ('declined', 'declined in %s:%d' % (entry['path'], entry['line']), [])
        baseline = []
        for item in self.catalog.get('baseline', []):
            state, evidence, fids = status.get(item['id'], ('n/a', 'not evaluated', []))
            baseline.append({'id': item['id'], 'status': state, 'evidence': evidence, 'finding_ids': fids,
                             'source': self.source(item.get('doc'))})

        profiles = []
        evidence = {'agent-run': agent_run, 'plugin-repo': [m['path'] for m in manifests], 'typed-codebase': typed,
                    'procedure-docs': [d['path'] for d in procedures]}
        for profile in self.catalog.get('profiles', []):
            if evidence.get(profile['id']):
                profiles.append({'id': profile['id'], 'evidence': evidence[profile['id']][:5]})

        if not self.user:
            self.limits.append('user settings not read (project scope)')
        self.limits.append('managed settings not visible')
        self.limits.append('~/.claude.json (user MCP servers, per-project state) never read')
        self.limits.append('installed plugins and marketplaces not inspected')
        if self.claude_version == 'unknown':
            self.limits.append('Claude Code version unknown; version-gated features not filtered')
        if not self.git:
            self.limits.append('not a git repository; .gitignore matched approximately')

        t = self.truncated
        inventory = {
            'instructions': capped([dict({'path': i['path'], 'lines': i['lines'], 'kind': i['kind'],
                                          'loaded': i['loaded']},
                                         **({'gitignored': 'CLAUDE.local.md' in self.ignored(['CLAUDE.local.md'])}
                                            if i['path'] == 'CLAUDE.local.md' else {}))
                                    for i in instructions], 'inventory.instructions', t),
            'instruction_loading': self.loading(instructions),
            'instruction_lines_loaded': sum(i['lines'] for i in instructions
                                            if i['loaded'] and i['kind'] != 'nested'),
            'rules': capped([{'path': f, 'paths_frontmatter': 'paths' in frontmatter_keys(self.text(f) or '')}
                             for f in self.files if f.startswith('.claude/rules/') and f.endswith('.md')],
                            'inventory.rules', t),
            'settings': [settings_entry(s) for s in settings],
            'skills': capped([{'path': f, 'name': 'name' in frontmatter_keys(self.text(f) or ''),
                               'description': 'description' in frontmatter_keys(self.text(f) or '')} for f in skills],
                             'inventory.skills', t),
            'agents': capped([f for f in self.files if re.fullmatch(r'\.claude/agents/[^/]+\.md', f)], 'inventory.agents', t),
            'commands': capped([f for f in self.files if re.fullmatch(r'\.claude/commands/.+\.md', f)],
                               'inventory.commands', t),
            'mcp': mcp_servers(self.load_json('.mcp.json')) if '.mcp.json' in self.fileset else [],
            'plugins': capped([{'path': m['path'], 'kind': m['kind'], 'state': m['state'], 'skill_dirs': m['skill_dirs']}
                               for m in manifests], 'inventory.plugins', t),
            'ci': capped(ci, 'inventory.ci', t),
            'evals': capped(evals, 'inventory.evals', t),
        }
        signals = {
            'check_commands': capped(checks, 'signals.check_commands', t),
            'documented_checks': documented[:CAP],
            'procedure_docs': capped(procedures, 'signals.procedure_docs', t),
            'agent_run': agent_run[:CAP],
            'typed': typed,
            'lsp_enabled': lsp_enabled,
            'secret_paths': capped(secret_paths, 'signals.secret_paths', t),
            'plugin_checks': plugin_checks,
            'must_rules': capped(must_rules, 'signals.must_rules', t),
        }
        plan = plan_of(self.findings, optional, declined)
        setup = bool(roots or project_settings or '.claude' in self.dirs)
        out = {'claudit': VERSION, 'catalog_version': self.catalog.get('catalog_version'),
               'claude_version': self.claude_version, 'root': '.', 'git': self.git, 'inventory': inventory,
               'signals': signals, 'profiles': profiles, 'findings': capped(self.findings, 'findings', t),
               'plan': plan, 'grades': grades_of(plan, setup), 'optional': optional, 'declined': declined,
               'footer': audited(self.root, self.git),
               'baseline': baseline, 'dismissed': dismissed, 'limits': self.limits}
        if t:
            out['truncated'] = t
        return redact(out)


def team_instructions(instructions):
    """Loaded project instructions and their imports, without personal CLAUDE.local.md and what it imports."""
    def personal(item):
        while item.get('parent'):
            item = item['parent']
        return item['path'] == 'CLAUDE.local.md'
    return [i for i in instructions if i['loaded'] and i['kind'] in ('project', 'import') and not personal(i)]


def sentences(text):
    """(sentence, line number of an offset in it) for a text's prose; a paragraph or list item may wrap over lines."""
    units, current, last = [], [], None
    for number, line in prose(text):
        body = line.strip().lstrip('>').strip()
        heading = body.startswith(('#', '|'))
        if not body or heading or LIST_ITEM.match(line) or last is None or number != last + 1:
            if current:
                units.append(current)
            current = []
        if body and not heading:
            current.append((number, LIST_ITEM.sub('', body, count=1)))
        last = number
    if current:
        units.append(current)
    for unit in units:
        joined, marks = '', []
        for number, body in unit:
            joined += ' ' if joined else ''
            marks.append((len(joined), number))
            joined += body
        for match in re.finditer(r'(?:[^.!?]|[.!?](?=\S))+[.!?]?', joined):
            start = match.start() + len(match.group()) - len(match.group().lstrip())
            sentence = match.group().strip()
            if sentence:
                yield sentence, (lambda offset, start=start, marks=marks:
                                 max(n for o, n in marks if o <= start + offset))


def plan_of(findings, optional=(), declined=()):
    """The deterministic plan: findings of one kind on one path are one item, ranked by severity, grade and id.

    Up to PLAN_MAX items; the rest overflow. Secret deny rules join a .claudeignore item, whose fix adds them.
    """
    groups, index = [], {}
    ignore_file = any(f['id'] == 'claudeignore' for f in findings)
    for finding in sorted(findings, key=lambda f: (SEVERITIES[f['severity']], GRADES[f['grade']], f['id'])):
        kind = finding['id'].split(':')[0]
        merged = kind == 'claudeignore' or (kind == 'secret-deny' and ignore_file)
        key = ('claudeignore', '') if merged else (kind, finding['path'])
        if key not in index:
            index[key] = {'title': finding['change'], 'kind': kind, 'grades': [],
                          'severity': finding['severity'], 'finding_ids': []}
            groups.append(index[key])
        index[key]['finding_ids'].append(finding['id'])
        if finding['grade'] not in index[key]['grades']:
            index[key]['grades'].append(finding['grade'])
    items, overflow = groups[:PLAN_MAX], groups[PLAN_MAX:]
    for number, item in enumerate(items, 1):
        item['n'] = number
    count = len(items)
    if count >= 3:
        summary = '%d changes are worth making.' % count
        if overflow:
            summary += ' %d more %s under Also worth knowing.' % (len(overflow), 'is' if len(overflow) == 1 else 'are')
    else:
        reasons = ['the scan found no %sdefects or gaps' % ('other ' if count else '')]
        if optional:
            reasons.append('optional items are under Also worth knowing')
        if declined:
            reasons.append('declined features are under Declined by the project')
        head = 'No changes worth making' if not count else '%d change%s worth making' % (
            count, ' is' if count == 1 else 's are')
        summary = '%s: %s.' % (head, '; '.join(reasons))
    return {'items': items, 'overflow': overflow, 'summary': summary}


def grades_of(plan, setup):
    """Letters for the three grades from the plan, and which plan items would raise each.

    Correctness and Alignment: F for configuration that doesn't load (Correctness only), D for a high or several
    mediums, C for one medium, B for lows only, A for none; a missing instruction file counts as one Alignment
    medium. Coverage: A to D for 0, 1, 2 or 3+ gaps, F with no setup at all.
    """
    groups = plan['items'] + plan['overflow']
    grades = {}
    for grade in GRADES:
        mine = [g for g in groups if grade in g['grades'] or (grade == 'alignment' and g['kind'] == 'no-instructions')]
        if grade == 'coverage':
            letter = 'F' if not setup else 'ABCD'[min(len(mine), 3)]
        else:
            severities = ['medium' if g['kind'] == 'no-instructions' else g['severity'] for g in mine]
            letter = ('F' if any(g['kind'] in FATAL for g in mine) else
                      'D' if 'high' in severities or severities.count('medium') >= 2 else
                      'C' if 'medium' in severities else 'B' if severities else 'A')
        grades[grade] = {'letter': letter, 'items': [g['n'] for g in mine if 'n' in g],
                         'more': sum(1 for g in mine if 'n' not in g)}
    return grades


def audited(root, git):
    """The report footer's first line: Claudit's version and the audited commit."""
    if not git:
        return 'Claudit %s; not a git repo' % VERSION
    proc = run(['git', '-C', root, 'rev-parse', '--verify', '-q', 'HEAD^{commit}'])
    sha = proc.stdout.strip() if proc is not None and proc.returncode == 0 else ''
    if not re.fullmatch(r'[0-9a-f]{40,64}', sha):
        return 'Claudit %s; git repo with no commits' % VERSION
    status = run(['git', '-c', 'core.fsmonitor=false', '-C', root, 'status', '--porcelain'])
    state = ('' if status.stdout.strip() == '' else ' plus uncommitted changes') if (
        status is not None and status.returncode == 0) else ' (uncommitted changes unknown)'
    return 'Claudit %s; audited commit %s%s' % (VERSION, sha, state)


def path_tokens(line):
    """Path-like tokens worth checking: contain a /, end in an extension or a trailing /."""
    for raw in TOKEN_SPLIT.split(line):
        token = re.sub(r':\d+$', '', raw.strip('*_').rstrip('.:!?')).split('#', 1)[0]
        if '/' not in token or '://' in token or token[:1] in '~$/@' or re.search(r'[*<>{}$%=?@:\\]', token):
            continue
        if not re.fullmatch(r'[\w.-]+(?:/[\w.-]+)*/?', token):
            continue
        bare = re.sub(r'^(?:\.\.?/)+', '', token)
        if '/' not in bare.rstrip('/'):
            continue  # `./money.js`, `src/`: module specifiers and generic dirs, too ambiguous
        segments = bare.rstrip('/').split('/')
        if token.endswith('/'):
            if len(segments) < 2:
                continue
        elif not re.search(r'\.[A-Za-z][A-Za-z0-9]{0,9}$', segments[-1]):
            continue
        first = segments[0]
        if first in SKIP_DIRS or ('.' in first and not first.startswith('.')):
            continue
        yield token


def rules_of(data, kind):
    perms = data.get('permissions') if isinstance(data, dict) else None
    rules = perms.get(kind) if isinstance(perms, dict) else None
    return [r for r in rules if isinstance(r, str)] if isinstance(rules, list) else []


def as_list(value):
    return value if isinstance(value, list) else []


def hook_scripts(command):
    """Project script paths a hook command runs."""
    found = []
    for match in re.finditer(r'"?\$\{?CLAUDE_PROJECT_DIR\}?"?(/[^\s"\';|&)]+)', command):
        found.append(match.group(1).lstrip('/'))
    for match in re.finditer(r'(?:^|[\s"\'])(\./[^\s"\';|&)]+|\.claude/hooks/[^\s"\';|&)]+)', command):
        found.append(strip_dot(match.group(1)))
    return [f for f in found if f and '$' not in f]


def settings_entry(s):
    data = s['data'] if isinstance(s['data'], dict) else {}
    perms = data.get('permissions') if isinstance(data.get('permissions'), dict) else {}
    hooks = {}
    for event, groups in sorted((data.get('hooks') or {}).items()) if isinstance(data.get('hooks'), dict) else []:
        for group in groups if isinstance(groups, list) else []:
            if isinstance(group, dict):
                matcher = group.get('matcher')
                hooks.setdefault(event, []).append({
                    'matcher': matcher if isinstance(matcher, str) or matcher is None else json.dumps(matcher),
                    'commands': [scrub(h['command'])[:200] for h in as_list(group.get('hooks'))
                                 if isinstance(h, dict) and isinstance(h.get('command'), str)]})
    plugins = data.get('enabledPlugins')
    env = data.get('env')
    summary = {kind: rules_of(data, kind)[:CAP] for kind in ('allow', 'deny', 'ask')}
    summary.update({'defaultMode': perms.get('defaultMode'), 'hooks': hooks,
                    'enabledPlugins': sorted(plugins)[:CAP] if isinstance(plugins, dict) else [],
                    'env': sorted(env)[:CAP] if isinstance(env, dict) else []})
    return {'path': s['path'], 'scope': s['scope'], 'state': s['state'], 'summary': summary}


def mcp_servers(loaded):
    state, data, _ = loaded
    servers = data.get('mcpServers') if state == 'ok' and isinstance(data, dict) else None
    out = []
    for name, server in sorted((servers or {}).items()) if isinstance(servers, dict) else []:
        server = server if isinstance(server, dict) else {}
        kind = server.get('type') or ('stdio' if 'command' in server else 'http' if 'url' in server else 'unknown')
        out.append({'name': name, 'type': kind,
                    'env': sorted(server['env']) if isinstance(server.get('env'), dict) else [],
                    'headers': sorted(server['headers']) if isinstance(server.get('headers'), dict) else []})
    return out[:CAP]


def run(argv, stdin=None, timeout=10):
    try:
        return subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=timeout,
                              env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    except (OSError, subprocess.SubprocessError):
        return None


def resolve_root(path):
    """Resolve to the git toplevel when inside a repository; returns (root, git)."""
    root = os.path.realpath(path)
    if not os.path.isdir(root):
        raise UsageError('root is not a directory: %s' % path)
    proc = run(['git', '-C', root, 'rev-parse', '--show-toplevel'])
    if proc is not None and proc.returncode == 0 and proc.stdout.strip():
        return os.path.realpath(proc.stdout.strip()), True
    return root, False


def claude_version(given):
    if given:
        if not re.fullmatch(r'\d+\.\d+\.\d+', given):
            raise UsageError('--claude-version must look like X.Y.Z')
        return given
    proc = run(['claude', '--version'], timeout=5)
    match = re.match(r'\s*(\d+\.\d+\.\d+)', proc.stdout) if proc is not None and proc.returncode == 0 else None
    return match.group(1) if match else 'unknown'


def normalize_page(token):
    token = token.strip().split('#', 1)[0].split('?', 1)[0]
    if '_llms' in token or token.endswith('.txt'):
        return None
    match = re.search(r'/docs/en/(.+)$', token)
    if match:
        token = match.group(1)
    elif '://' in token:
        return None
    token = token.strip('/')
    if token.endswith('.md'):
        token = token[:-3]
    return token if re.fullmatch(r'[a-z0-9][a-z0-9_-]*(?:/[a-z0-9_-]+)*', token) else None


def new_pages(pages, catalog):
    reviewed = set(catalog.get('reviewed_pages', []))
    given = []
    for token in re.split(r'[\s,]+', pages):
        slug = normalize_page(token) if token else None
        if slug and slug not in given:
            given.append(slug)
    if not given:
        raise UsageError('--pages contained no documentation slugs')
    out = {'new_pages': [p for p in given if p not in reviewed and not p.startswith('whats-new/')],
           'new_whats_new': [p for p in given if p not in reviewed and p.startswith('whats-new/')]}
    missing = len(reviewed - set(given))
    if missing:
        out['missing_from_index'] = missing
    return out


def dismiss(root, fid, reason):
    if not fid.strip() or not reason.strip():
        raise UsageError('--id and --reason must be non-empty')
    folder = os.path.join(root, '.claude')
    path = os.path.join(folder, 'claudit-dismissed.json')
    real_root = os.path.realpath(root)
    if os.path.islink(folder) or os.path.islink(path) or (os.path.exists(path) and not os.path.isfile(path)) \
            or (os.path.exists(folder) and not os.path.isdir(folder)) \
            or os.path.dirname(os.path.realpath(path)) != os.path.join(real_root, '.claude'):
        raise UsageError('refusing to write %s: it or .claude is a symlink, not a file/directory, '
                         'or not inside the project' % DISMISSED)
    data = {'version': 1, 'dismissed': []}
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            raise UsageError('%s is not valid JSON; fix or remove it first' % DISMISSED)
        if not isinstance(data, dict) or not isinstance(data.get('dismissed'), list):
            raise UsageError('%s has no "dismissed" list' % DISMISSED)
    added = not any(isinstance(e, dict) and e.get('id') == fid for e in data['dismissed'])
    if added:
        data['dismissed'].append({'id': fid, 'reason': reason, 'date': datetime.date.today().isoformat()})
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.claudit-dismissed.', suffix='.tmp', dir=folder)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, indent=2)
                handle.write('\n')
            os.chmod(tmp, 0o644)
            os.replace(tmp, path)
        except OSError:
            os.unlink(tmp)
            raise
    return {'dismissed': fid, 'added': added, 'path': DISMISSED}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def main(argv=None):
    parser = Parser(prog='claudit.py', description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command')
    scan = sub.add_parser('scan')
    scan.add_argument('--root', default='.')
    scan.add_argument('--claude-version')
    scan.add_argument('--user', action='store_true')
    pages = sub.add_parser('new-pages')
    pages.add_argument('--pages', required=True)
    gone = sub.add_parser('dismiss')
    gone.add_argument('--root', default='.')
    gone.add_argument('--id', required=True)
    gone.add_argument('--reason', required=True)
    try:
        args = parser.parse_args(argv)
        if args.command == 'scan':
            root, git = resolve_root(args.root)
            result = Scan(root, git, load_catalog(), claude_version(args.claude_version), args.user).run()
        elif args.command == 'new-pages':
            text = sys.stdin.read() if args.pages == '-' else args.pages
            result = new_pages(text, load_catalog())
        elif args.command == 'dismiss':
            result = dismiss(resolve_root(args.root)[0], args.id, args.reason)
        else:
            raise UsageError('expected a subcommand: scan, new-pages or dismiss')
    except UsageError as error:
        print(json.dumps({'error': redact(str(error))}))
        return 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
