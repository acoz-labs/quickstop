#!/usr/bin/env python3
"""Claudit 4.3 helper: a deterministic, read-only scan of a project's Claude Code setup.

Subcommands: scan, new-pages, dismiss, deep. Standard library only; Python 3.9+.
The only write is `dismiss`: per user to ${CLAUDE_PLUGIN_DATA}, or with --shared
to <root>/.claude/claudit-dismissed.json. `deep` runs Claude Code's own
read-only `/doctor prompt-audit` and `claude doctor`. The helper never prints
secret values and never reads ~/.claude.json.
"""
import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

VERSION = '4.3.1'
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
DISMISSED = '.claude/claudit-dismissed.json'  # shared with the team (dismiss --shared)
USER_DISMISSED = '${CLAUDE_PLUGIN_DATA}/dismissed/%s.json'  # per user, keyed by repository (dismiss)
DEFAULT_MODE_IGNORED = (2, 1, 257)
AGENTS_MD_READ = (2, 1, 277)  # first Claude Code version that reads AGENTS.md without an import
NUMBERED = re.compile(r'^\s*\d+[.)]\s')
FENCE = re.compile(r'^\s*(```|~~~)')
PROCEDURE_WORDS = re.compile(r'release|deploy|runbook|procedure|playbook|rollout|onboarding|sdlc|delivery|review', re.I)
RUNNER = re.compile(r'((?:make|just) (?:test|check|lint|ci)\b|(?:npm|pnpm|yarn|bun)(?: run)? (?:test|lint|check|typecheck)\b[\w:-]*'
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
EXTENSIONS = ('.py', '.js', '.ts', '.go', '.rs', '.java', '.rb', '.c', '.cpp', '.cs', '.swift', '.kt', '.php')
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
    'broken-import': 'Fix the imports in {path}', 'stale-ref': 'Fix the stale facts in {path}',
    'stale-command': 'Fix the stale facts in {path}', 'stale-dep': 'Fix the stale facts in {path}',
    'missing-name': 'Fix the stale facts in {path}', 'long-description': 'Shorten the skill descriptions',
    'agent-descriptions': 'Shorten the subagent descriptions', 'visible-skill': 'Hide {path} from the skill listing',
    'duplicate': 'Keep each repeated rule in one place', 'gate-ask': 'Ask before {subject}',
    'git-hooks': 'Enable the git hooks in agent sessions',
    'no-instructions': 'Add a short CLAUDE.md', 'undocumented-checks': 'Record the check commands in {path}',
    'allowlist': 'Pre-approve the check commands', 'secret-deny': 'Deny reads of secret paths',
    'stop-hook': 'Enforce the check with a Stop hook', 'procedure-skill': 'Add a skill for {path}',
    'plugin-validate': 'Run claude plugin validate', 'plugin-eval': 'Add evals for {subject}',
    'lsp': 'Install a code-intelligence plugin',
}
# Findings that a named path, command, dependency, skill or subagent doesn't exist: one plan item per file, and
# Alignment can't be A while one stands (#193).
STALE_KINDS = ('stale-ref', 'stale-command', 'stale-dep', 'missing-name')
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
# The empty group `why` marks where the stated reason starts (see decline_reason).
DECLINE_TAIL = (r'(?:\s+(?:in this (?:repository|repo|project)|here))?(?:\s*$|(?:,?\s+(?=(?:because|since|in favou?r of)\s)'
                r'|,\s+(?=so\s|and replaced (?:them|it) with\s)|\s*[;:](?=\s)\s*)(?P<why>)|,?\s+%s\s*$)' % DELIBERATE)
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
# A reason may also lead a deliberate absence: "<reason>, so it deliberately has no evals", "Because <reason>, we
# deliberately run without hooks". At most three words stand between it and the decline.
LEAD_REASON = re.compile(r'^(?:(?P<so>.+?),?\s+so|(?P<because>(?:because|since)\s+.+?),)\s+(?:\S+\s+){0,3}$', re.I)
# Stated reasons that current Claude Code or the project itself contradicts. Each pattern must match a whole reason
# clause (after its because, since or so), so a clause with any other word (a limit such as "in CI" or "on Windows",
# a reversal, a time, an aside) never matches and gets no note: allow-only. Evidence is a catalog doc key (a page
# showing the limitation is gone) or a scan fact ('check': a check command exists; 'typed': typed code exists).
CANT = r"(?:can ?not|can't|are unable to|is unable to)"
CC = r'(?:claude code|claude)'
NO_RUNNER = (r'(?:%s (?:has|offers|provides) no|there is no) (?:way to run (?:plugin )?evals|(?:built-in )?(?:plugin )?'
             r'evals? runner)' % CC)
NO_VALIDATOR = (r'(?:%s (?:has|offers|provides) no|there is no) (?:way to validate plugins|(?:built-in )?plugin '
                r'validator)' % CC)
NO_CHECK = (r'(?:there (?:is|are) no|(?:the )?(?:project|repository|repo) has no) (?:check(?: command| script)?s?|tests?|'
            r'test suite)(?: to run)?|there is nothing to (?:check|run)')
UNTYPED = r'(?:the )?(?:project|repository|repo|code|codebase) (?:is untyped|is not typed|has no typed code)|there is no typed code'
STALE_REASONS = (
    ('stop-hook', r'(?:%s )?(?:hooks|a hook|stop hooks|they|it) %s (?:block|stop|prevent) %s from (?:stopping|finishing)'
     % (CC, CANT, CC), 'doc', 'hooks-stop',
     'a Stop hook can keep Claude from stopping: exit code 2 prevents it and continues the conversation'),
    ('plugin-eval', NO_RUNNER, 'doc', 'plugin-evals', '`claude plugin eval` runs a plugin\'s eval suite and scores it'),
    ('plugin-validate', NO_VALIDATOR, 'doc', 'plugin-validate',
     '`claude plugin validate` checks a plugin\'s files for syntax and schema errors'),
    ('lsp', r"%s (?:has no|doesn't support|does not support) (?:lsp|language servers|code intelligence)(?: support)?" % CC,
     'doc', 'code-intelligence', 'code intelligence plugins connect Claude Code to a language server'),
    ('procedure-skill', r'(?:skills|they) %s be shared (?:with the team|through the (?:repository|repo))'
     % r"(?:can ?not|can't)", 'doc', 'skill-locations',
     'a skill committed under .claude/skills/ loads for everyone who works in the repository'),
    ('stop-hook', NO_CHECK, 'repo', 'check', 'the project has a check command now'),
    ('allowlist', NO_CHECK, 'repo', 'check', 'the project has a check command now'),
    ('lsp', UNTYPED, 'repo', 'typed', 'the project has typed code now'),
)
STALE_FORMS = [(feature, re.compile(pattern), kind, key, claim) for feature, pattern, kind, key, claim in STALE_REASONS]
# Correctness defects in a declined feature's own configuration: the decline left them behind, so they stay in the
# plan, graded as usual, and cite the decline.
DECLINE_DEFECTS = {'stop-hook': ('matcher-type', 'matcher-ignored', 'hook-script', 'hooks-file'),
                   'allowlist': ('default-mode', 'auto-mode', 'write-rule'),
                   'procedure-skill': ('flat-skill', 'skill-missing')}
NO_REASON = 'no reason given'


def decline_reason(sentence, match):
    """The reason a decline states, as exact parts of its sentence: a clause before it and the clause after it."""
    parts = []
    lead = LEAD_REASON.match(sentence[:match.start()])
    if lead:
        parts.append((lead.start(lead.lastgroup), lead.group(lead.lastgroup).strip()))
    if match.start('why') >= 0:
        tail = sentence[match.start('why'):].strip()
        if tail:
            parts.append((match.start('why'), tail))
    return parts


def stale_reason(feature, parts):
    """The first STALE_REASONS row a reason part matches as a whole clause, or None."""
    for _, part in parts:
        clause = re.sub(r'\s+', ' ', part.replace('`', '').replace('’', "'")).strip().rstrip('.!').lower()
        clause = re.sub(r'^(?:because|since|so)\s+', '', clause)
        for row in STALE_FORMS:
            if row[0] == feature and row[1].fullmatch(clause):
                return row
    return None


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
# Command contexts (see code_snippets).
SHELL_FENCES = {'', 'sh', 'bash', 'zsh', 'fish', 'shell', 'console', 'shell-session', 'shellsession', 'terminal',
                'powershell', 'pwsh', 'ps1', 'bat', 'cmd'}
CONSOLE_FENCES = {'console', 'shell-session', 'shellsession', 'terminal'}  # prompts mixed with output
# `$` and `%` start a prompt line. `>` is also Markdown's quote, so a `>` line counts only when it is just a command
# with flag or path arguments (`> bin/ci --fast`), never a sentence (`> bin/ci is slow`).
PROMPT = re.compile(r'^\s*(?:[$%]\s+(\S.*)|>\s+(\S+(?:\s+(?:-\S+|\S*[/.=]\S*))*)\s*)$')
# A run word followed by what may stand between it and the command.
RUN_WORDS = re.compile(r'\b(?:run|execute|invoke|call)(?:\s*:\s*|\s+(?:the\s+)?(?:command|script)\s+|'
                       r'(?:\s+[\w-]+){0,4}\s+(?:with|using|via)\s+|\s+)$', re.I)
# ... counts only as an instruction: at the start of a sentence, clause, list item or label, after
# please/then/first/also/always/now/just/next/finally or make sure to/remember to/be sure to, or after a
# reader or agent subject with a modal ("you can", "agents must").
IMPERATIVE = re.compile(r"(?:^[\s>|]*|[.!?;:(|]\s*|,\s+|(?:^|[.!?;:(|,]\s*)then\s+)(?:(?:please|then|first|also|always|now|just|next|finally|"
                        r"simply)\s+)?(?:(?:make sure|remember|be sure) to\s+)?$"
                        r"|\b(?:you|we|agents?|contributors?|maintainers?)\s+(?:can|must|should|may|need to|have to)\s+"
                        r"(?:(?:always|also|first|then|just)\s+)?$", re.I)
# A future, conditional or past auxiliary earlier in the sentence makes a run word a description ("CI will, first,
# run `x`"), whatever punctuation follows it.
DESCRIBING = re.compile(r"\b(?:will|would|could|might|shall|does|did|used to|automatically)\b", re.I)
NEGATED = re.compile(r"\b(?:not|never|don['’]t|doesn['’]t|avoid|no need to)(?:,?\s+(?:ever|even|again|once))?,?\s+$",
                     re.I)
COMMAND_LABEL = re.compile(r'\b(?:commands?|checks?|tests?|usage|verify|verification|validation|lint|build)\s*:\s*$',
                           re.I)
# A list item led by a command is a call only when the command is followed by the end, `:`, a dash or `(`.
LIST_LEAD_END = re.compile('\\s*(?:$|:|-\\s|–|—|\\()')
# Words right after a command that make the line describe it rather than call it.
DESCRIBED = re.compile(r"\b(?:is|was|were|has been|had|used to|no longer|removed|deprecated|obsolete|gone|replaced|"
                       r"broken|don['’]t|never|do not)\b", re.I)
# Anywhere after a command (or in its table row): it is history or a warning.
HISTORY = re.compile(r"\b(?:no longer|deprecated|obsolete|removed|is gone|used to|don['\u2019]t run|never run|do not run)\b",
                     re.I)
# History narrative (#193 4.3.1): a sentence telling what happened rather than what holds now. Each form needs a
# tensed past verb (`verb`) that is the sentence's own statement: not in a relative clause ("the last release that
# passed CI is tagged latest"), a condition ("If the previous build failed, rerun it") or a hedge ("may have
# failed"). So a present rule ("Hooks are disabled in CI") or a description of something that exists now is never
# history. A date counts only as when something happened ("On 2026-03-02 the docs moved"), never as a name ("a
# 2026-07-28 server", "negotiates 2026-07-28").
RETIRED = r'(?:retired|removed|dropped|replaced|deprecated|superseded|phased out|abandoned|disabled|discontinued)'
PAST = (r'(?:passed|failed|ran|worked|succeeded|broke|moved|changed|switched|added|introduced|became|was|were|'
        r'had|used|showed|found)')
DATE = (r'(?:20\d\d-\d\d-\d\d|(?:January|February|March|April|May|June|July|August|September|October|November|'
        r'December)\s+(?:\d{1,2},\s+)?20\d\d|20\d\d)')
HISTORY_FORMS = (
    ('retirement', re.compile(r'\b(?P<verb>(?:have|has|had)\s+been|was|were)\s+%s\b' % RETIRED, re.I)),
    ('past run', re.compile(r'\b(?:initial|first|earlier|previous|original|last|old)\s+(?:[\w-]+\s+){0,2}?'
                            r'(?:runs?|releases?|migrations?|attempts?|pass|checks?|builds?|versions?)\b[^.;]{0,80}?'
                            r'\b(?P<verb>%s)\b' % PAST, re.I)),
    # The date leads a time phrase and isn't followed by its noun ("Since 2026-07-28 servers were …").
    ('dated', re.compile(r'(?<![\w`-])(?:on|in|since|until|as of|by|before|after|from|during)\s+(?:the\s+)?%s\b'
                         r'(?![\w`-]|\s+[a-z][\w-]*\s+(?:is|are|was|were|has|have)\b)[^.;]*?\b(?P<verb>%s)\b'
                         % (DATE, PAST), re.I)),
    ('past version', re.compile(r'\b(?:in|until|before|prior to)\s+(?:version\s+|v)\d+(?:\.\d+)+\b[^.;]{0,60}?'
                                r'\b(?P<verb>%s)\b' % PAST, re.I)),
)
SPECULATIVE = re.compile(r'\b(?:may|might|could|would|should|will|must|can)\b', re.I)  # "may have failed"
# A relative clause's own verb: "… that was added", "… which we used", "… whose first run passed".
RELATIVE = re.compile(r'\b(?:(?:that|which|who|whom)\s+(?:\S+\s+)?|(?:whose|where)\s+(?:\S+\s+){0,3})$', re.I)
CONDITION = re.compile(r'\b(?:if|unless|whether|once|when|whenever)\b[^.;]*$', re.I)  # "If the build failed, …"
# Where a project records decisions and history on purpose: a decision record (decisions.md, docs/adr/...) owns a
# decline, and changelogs, release notes, migration and upgrade guides and what's-new pages tell history as
# their contract ("`X` has been removed; use `Y`").
DECISION_RECORD = re.compile(r'decision|(?:^|/)adrs?(?:/|[-_.])', re.I)
HISTORY_FILE = re.compile(r'(?:^|/)(?:change-?log|changes|history|news|release[-_ ]?notes|releases|migrat\w*|'
                          r'upgrad\w*|what[\'’]?s[-_ ]?new|deprecat\w*|breaking[-_ ]changes)[^/]*$', re.I)
HISTORY_TITLE = re.compile(r'^#\s+.*\b(?:change-?log|release notes|migrat\w*|upgrad\w*|what[\'’]?s new|'
                           r'deprecat\w*|breaking changes)\b', re.I | re.M)


def history_form(sentence):
    """(name, offset) of the first history form a sentence holds as its own statement, or None."""
    for name, form in HISTORY_FORMS:
        for match in form.finditer(sentence):
            before = sentence[:match.start('verb')]
            if SPECULATIVE.search(match.group()) or RELATIVE.search(before) or CONDITION.search(before):
                continue
            return name, match.start()
    return None


CHAIN = re.compile(r'\s*(?:,\s*(?:and\s+|or\s+|then\s+)?|\s(?:and|or|then)\s+|\s*\(or\s+)\s*', re.I)


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


def code_spans(text):
    """Every inline code span and fenced code line: where a project names its tools, called or not."""
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


def code_snippets(text):
    """The commands a Markdown text documents as calls, from command contexts only.

    - Fenced blocks with no language or a shell one (sh, bash, zsh, shell, console, ...), and indented code
      blocks. In a console or shell-session block only prompt lines (`$`, `%`, `>`) count; other languages
      (text, output, json, ...) are not commands.
    - A prose line starting with a shell prompt: `$ bin/ci`.
    - A backticked command that begins a list item ("- `bin/ci`: runs the suite") or fills a table cell.
      A fence with no language counts, so output belongs in a `text` or `console` fence.
    - A backticked command after run, execute, invoke or call ("Run `bin/ci`", "run: `x`", "Run the tests with
      `x`"), unless negated ("never run `x`"), and the spans chained to it by a comma, and, or or then.
    - A backticked command after a label naming commands: "Commands: `x`", "Test: `x`".
    Inline code anywhere else (a sentence naming a tool, a heading) is not a call.
    """
    fence, info, previous, last_top, in_block, last_line = None, '', '', '', False, ''
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            if fence is None:
                fence, info = match.group(1), line.strip()[3:].strip().split(' ')[0].lower()
            elif line.strip().startswith(fence):
                fence = None
            continue
        if fence is not None:
            if info in SHELL_FENCES:
                prompt = re.match(r'^\s*[$%>]\s+(\S.*)$', line)  # inside a shell block, any prompt counts
                if prompt or info not in CONSOLE_FENCES:
                    yield (prompt.group(1) if prompt else line).strip()
            continue
        # An indented code block starts after a blank line that doesn't continue a list item.
        in_block = bool(re.match(r'(?: {4}|\t)\S', line)) and (
            in_block or (not previous.strip() and not LIST_ITEM.match(last_top)))
        previous = line
        if in_block:
            yield line.strip()
            continue
        wrapped, last_line = last_line, line  # a run phrase may end on the previous line
        if line.strip() and not line[0].isspace():
            last_top = line
        body = line.strip()
        if body.startswith('#'):
            continue  # a heading names things; it doesn't run them
        prompt = PROMPT.match(line)
        if prompt and '`' not in line:
            yield (prompt.group(1) or prompt.group(2)).strip()
            continue
        if body.startswith('|'):
            cells = body.strip('|').split('|')
            if not any(HISTORY.search(cell) for cell in cells):  # | `bin/old` | removed in 2.0 | is history
                for cell in cells:
                    cell = re.fullmatch(r'\s*`([^`\n]+)`\s*', cell)
                    if cell:
                        yield cell.group(1).strip()
        item = LIST_ITEM.match(line)
        start = item.end() if item else 0
        called = False
        for span in re.finditer(r'`([^`\n]+)`', line):
            before = line[start:span.start()]
            if start == 0 and not before.strip() and wrapped.strip() and not wrapped.lstrip().startswith(('#', '|')):
                before = wrapped.strip() + ' '
            run = RUN_WORDS.search(before)
            after = re.split(r'[.!?;]\s', line[span.end():], maxsplit=1)[0]
            lead = item and start == item.end() and not line[item.end():span.start()].strip() \
                and LIST_LEAD_END.match(line[span.end():])
            # "Execute `a`, invoke `b` or call `c`": a run word coordinated with a call is an instruction too.
            sentence = re.split(r'[.!?;:]\s', before[:run.start()])[-1] if run else ''
            instructed = run and not DESCRIBING.search(sentence) and (IMPERATIVE.search(before[:run.start()]) or (
                called and re.fullmatch(r'\s*,?\s*(?:and|or)?\s*', before[:run.start()]))) \
                and not NEGATED.search(before[:run.start()])
            if (lead or instructed or COMMAND_LABEL.search(before) or (called and CHAIN.fullmatch(before))) \
                    and not DESCRIBED.match(after.lstrip(' :(–—-')) \
                    and not HISTORY.search(after):
                called = True
                yield span.group(1).strip()
            else:
                called = False
            start = span.end()


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


WORD = re.compile(r'\S+')
# Translations and reference pages are not team procedures, whatever their numbered lists say (#193).
NOT_PROCEDURES = {'i18n', 'l10n', 'locale', 'locales', 'translations', 'reference', 'references', 'api', 'api-reference'}
# A command named only where it exists ("`bin/container bin/ci` where supported") is not a stale fact.
CONDITIONAL = re.compile(r'\b(?:where|when|if)\s+(?:supported|available|present|installed|provided|it exists)\b', re.I)
# Words that open a procedure step ("Run `bin/ci`", "Tag the commit") or order the steps; a numbered list without
# them is declarative ("1. The public API is stable"), standing rules or facts rather than a procedure (#193).
STEP_VERBS = frozenset("""
    add apply approve ask attach back backport branch build bump call cd change check choose clean clone close commit
    compile configure confirm copy create cut delete deploy document download draft edit enable disable ensure enter
    export fetch file fill find finish fix follow format generate get give go group install keep label leave link lint
    list log look make mark merge monitor move name note notify open pack paste pick post prepare press publish pull
    push put read rebase record release remove rename repeat replace request restart retry review revert roll run save
    search select send set ship sign squash start stop submit switch tag test type update upload use validate verify
    visit wait write""".split())
SEQUENCE = re.compile(r'\b(?:then|next|afterwards|first|finally|once (?:it|the|that|this)|until)\b', re.I)
# A person must approve a gate verb: "Never merge to main without a human approving", "A release needs a go-ahead".
GATE_VERBS = (('merge', re.compile(r'\bmerg(?:e|es|ed|ing)\b', re.I)),
              ('push to main', re.compile(r'\bpush(?:es|ed|ing)?\b[^.;]{0,40}\b(?:main|master)\b', re.I)),
              ('deploy', re.compile(r'\bdeploy(?:s|ed|ing|ment|ments)?\b', re.I)),
              ('release', re.compile(r'\breleas(?:e|es|ed|ing)\b', re.I)),
              ('publish', re.compile(r'\bpublish(?:es|ed|ing)?\b', re.I)))
GATE_STEMS = {'merge': 'merge', 'push to main': 'push', 'deploy': 'deploy', 'release': 'release', 'publish': 'publish'}
PERSON = re.compile(r"\b(?:humans?|person|people|maintainers?|reviewers?|owners?|approv\w*|go-ahead|sign-?off|"
                    r"someone|the user)\b", re.I)
NEED = re.compile(r"\b(?:never|must|mustn't|needs?|requires?|required|only|without|until|don't|do not)\b", re.I)
MANIFESTS = ('pyproject.toml', 'package.json', 'requirements.txt', 'go.mod', 'Cargo.toml', 'Gemfile', 'setup.cfg',
             'setup.py', 'composer.json')
DEP_WORDS = re.compile(r'\b(?:pin(?:s|ned)?|dependenc(?:y|ies)|depends on|declared|installed|requires?|librar(?:y|ies)|'
                       r'packages?|render(?:s|ed)? through|built on)\b', re.I)
NAMED = re.compile(r'`/?([a-z0-9][a-z0-9_-]*)`\s+(?:skill|subagent|agent)s?\b|\b(?:skill|subagent)\s+`/?([a-z0-9][a-z0-9_-]*)`',
                   re.I)
BUILT_IN_NAMES = {'general-purpose', 'explore', 'plan', 'statusline-setup', 'claude-code-guide', 'doctor', 'code-review',
                  'batch', 'debug', 'loop', 'claude-api', 'verify', 'run', 'run-skill-generator', 'simplify', 'init',
                  'skill-doctor', 'fewer-permission-prompts', 'review', 'security-review', 'context', 'insights'}
GIT_HOOK_DECLINE = re.compile(r'\b(?:git|pre-commit|pre-push|commit-msg|husky|lefthook)\b[^.]{0,40}\bhooks?\b[^.]{0,60}'
                              r'\b(?:retired|removed|dropped|declined|disabled|not used|don[\'’]t use|do not use)\b|'
                              r'\b(?:no|retired|removed|dropped|declined|disabled)\b[^.]{0,30}\b(?:git|pre-commit|pre-push)'
                              r' hooks?\b', re.I)
STOPWORDS = frozenset('the a an and or of to in on for with by is are be it its this that as at from not no never your '
                      'you we our into than then so if when one any all each every can do does'.split())
DUP_MIN_WORDS = 8  # a sentence shorter than this is too generic to call a copy
# A script's string literals and comments, read left to right so a string never spans two: the long ones are the
# text duplication is judged on, cited by the file's own line.
SCRIPT_TEXT = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|#\s*(.*)$')
SCRIPT_TEXT_MIN = 40  # characters
# A file is generated output only when a line near its top says so ("Generated from ...", "This file is generated
# by ...", "... DO NOT EDIT") or `.gitattributes` marks it `linguist-generated`. The script that writes it is
# its generator, never generated itself.
GENERATED_HEAD = re.compile(r'^[\s#/*<!>-]*(?:(?:this|the) (?:file|page|document|list|table) (?:is|was) )?(?:auto-?)?'
                            r'generated (?:from|by|with|using)\b|(?-i:\bDO NOT EDIT\b)', re.I)
# A paraphrase shares at least this many content words, and 40% of the shorter sentence's (common words such as
# "change", "only", "setting" and "install" alone are no paraphrase).
PARAPHRASE_MIN_STEMS = 5
LISTING_CAP = 1536  # characters of description plus when_to_use in the skill listing (skills#frontmatter-reference)
AGENT_WARNING = 15000  # tokens of custom subagent descriptions before the startup warning (sub-agents)


def words(text):
    return len(WORD.findall(text or ''))


def tokens(text):
    """A rough token estimate: about four characters a token for English prose and code."""
    return int(round(len(text or '') / 4.0))


def frontmatter(text):
    """A Markdown file's YAML frontmatter as plain values: strings (quoted, plain or block scalars) and lists."""
    if not (text or '').startswith('---'):
        return {}
    end = text.find('\n---', 3)
    if end < 0:
        return {}
    out, key = {}, None
    for line in text[3:end].splitlines():
        match = re.match(r'^([A-Za-z_][\w-]*)\s*:\s*(.*)$', line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            if value in ('|', '>', '|-', '>-', '|+', '>+', ''):
                out[key] = ''
            elif value.startswith('[') and value.endswith(']'):
                out[key] = [v.strip().strip('\'"') for v in value[1:-1].split(',') if v.strip()]
            elif len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
                out[key] = value[1:-1]
            else:
                out[key] = value
            continue
        if key is None or not line.strip():
            continue
        item = re.match(r'^\s+-\s+(.*)$', line)
        if item and (out.get(key) == '' or isinstance(out.get(key), list)):
            out[key] = (out[key] or []) + [item.group(1).strip().strip('\'"')]
        elif isinstance(out.get(key), str) and line[:1].isspace():
            out[key] = (out[key] + ' ' + line.strip()).strip()
    return out


def truthy(value):
    return value is True or (isinstance(value, str) and value.strip().lower() == 'true')


def as_names(value):
    """A frontmatter list or comma-separated string as a list of names."""
    items = value if isinstance(value, list) else re.split(r'[,\s]+', value) if isinstance(value, str) else []
    return [i.strip() for i in items if isinstance(i, str) and i.strip()]


def procedural(line):
    """True when a numbered step reads as an instruction: it opens with a verb or orders the steps."""
    body = re.sub(r'^[\s*_`\[(]+', '', NUMBERED.sub('', line, count=1))
    first = re.match(r"[A-Za-z][\w'-]*", body)
    return bool(first and first.group().lower() in STEP_VERBS) or SEQUENCE.search(body) is not None


def normalized(sentence):
    return re.sub(r'\s+', ' ', re.sub(r'[`*_>"“”]', '', sentence)).strip().rstrip('.!:;').lower()


def stems(sentence):
    return {re.sub(r'(?:ing|ed|es|s)$', '', w) for w in re.findall(r'[a-z0-9]+', sentence.lower())
            if len(w) > 2 and w not in STOPWORDS}


def joined(names):
    names = list(names)
    if len(names) <= 1:
        return ''.join(names)
    return ', '.join(names[:-1]) + ' and ' + names[-1]


def repo_key(root, git):
    """The per-user dismissal file's key: the origin URL when there is one, else the real root path."""
    proc = run(['git', '-C', root, 'config', '--get', 'remote.origin.url']) if git else None
    origin = proc.stdout.strip() if proc is not None and proc.returncode == 0 else ''
    return hashlib.sha256((origin or os.path.realpath(root)).encode('utf-8')).hexdigest()[:16]


def user_dismissed(data_dir, root, git):
    """The per-user dismissal file for a repository, or None without a plugin data folder."""
    return os.path.join(data_dir, 'dismissed', repo_key(root, git) + '.json') if data_dir else None


class Scan:
    """One read-only scan of a project root."""

    ceiling = None  # highest directory checked for CLAUDE files above the project; None is the filesystem root

    def __init__(self, root, git, catalog, claude_version, user=False, data_dir=None):
        self.root, self.git, self.catalog, self.user = root, git, catalog, user
        self.data_dir = data_dir
        self.claude_version = claude_version
        self.findings, self.limits, self.truncated, self.exact, self.history = [], [], {}, {}, []
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

    def add(self, fid, grade, severity, title, path, evidence, fix, doc, confidence='high', line=None, subject=None,
            problem=None):
        finding = {'id': fid, 'grade': grade, 'severity': severity, 'title': title, 'path': path,
                   'change': CHANGE_TITLES[fid.split(':')[0]].format(path=path, subject=subject or path),
                   'evidence': evidence[:300], 'fix': fix, 'source': self.source(doc), 'confidence': confidence}
        if line:
            finding['line'] = line
        if problem:
            finding['problem'] = problem[:600]
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
        justfile = next((f for f in ('justfile', 'Justfile', '.justfile') if f in self.fileset), None)
        for recipe in re.findall(r'^@?(test|check|lint|ci)\b[^:=\n]*:(?!=)', self.text(justfile) or '' if justfile else '',
                                 re.M):
            add('just ' + recipe, justfile)
        state, package, _ = self.load_json('package.json') if 'package.json' in self.fileset else ('missing', None, None)
        if state == 'ok' and isinstance(package, dict) and isinstance(package.get('scripts'), dict):
            said = '\n'.join(list(corpus.values()) + [ci_text])
            bun = 'bun.lock' in self.fileset or 'bun.lockb' in self.fileset or re.search(
                r'\bbun (?:run|test)\b', said) or any(isinstance(v, str) and re.match(r'bun\b', v)
                                                     for v in package['scripts'].values())
            runner = ('pnpm' if 'pnpm-lock.yaml' in self.fileset else 'yarn' if 'yarn.lock' in self.fileset else
                      'bun' if bun else 'npm')
            for name in ('test', 'lint', 'check', 'typecheck'):
                script = package['scripts'].get(name)
                if isinstance(script, str) and 'no test specified' not in script:
                    # `bun test` is Bun's own test runner, not the script, so Bun always says `run`.
                    run_word = '' if (name == 'test' and runner != 'bun') or runner == 'yarn' else 'run '
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
            # Which runner the project uses is read from every mention; only calls become rules (below).
            for snippet in [s for text in corpus.values() for s in code_spans(text)] + ci_text.splitlines():
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
                    or NOT_PROCEDURES & {p.lower() for p in parts[:-1]} \
                    or parts[0] == '.claude' or re.match(r'(README|CHANGELOG|LICENSE)', name, re.I) or self.data(rel):
                continue
            ident = identity(self.abs(rel))
            if ident in product:
                continue
            text = self.text(rel) or ''
            numbered = [line for _, line in prose(text) if NUMBERED.match(line)]
            # A declarative list (standing principles, facts) is not a procedure: count only steps that instruct.
            steps = sum(1 for line in numbered if procedural(line))
            if steps * 2 < len(numbered):
                steps = 0
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

    def history_line(self, path, line, sentence, why, label=None):
        """Record a stale candidate once per line; `label` names the feature it reads like a decline of."""
        entry = next((c for c in self.history if c['path'] == path and c['line'] == line), None)
        if entry is None:
            entry = {'path': path, 'line': line, 'quote': sentence[:400], 'why': why}
            self.history.append(entry)
        if label:  # it reads like a decline, but only a decision record makes one
            entry['not_a_decline'] = '%s: no decision record says so, so it is not listed as declined; Claudit ' \
                'still does not recommend it while this line stands' % label

    def stale_history(self, paths):
        """History narrative (dated runs, "have been retired", past versions) in the given instruction files, skills,
        subagents and docs: stale candidates for the report, never graded. Decision records and changelogs tell
        history on purpose and are skipped."""
        for path in paths:
            text = self.text(path) or ''
            if DECISION_RECORD.search(path) or HISTORY_FILE.search(path) or HISTORY_TITLE.search(text[:2000]) \
                    or self.data(path) or os.path.isabs(path) or path.startswith('..'):
                continue
            for sentence, line_at in sentences(text):
                form = history_form(sentence)
                if form and not UNSURE.search(sentence):
                    self.history_line(path, line_at(form[1]), sentence, form[0])

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
                body = sentence.rstrip('.!')
                for feature, label, noun, forms in DECLINE_FORMS:
                    # The first decline of each feature counts; a decision record's replaces a history line's.
                    match = next((m for m in (form.search(body) for form in forms) if m), None) \
                        if feature not in found or found[feature].get('history') else None
                    form = None if not match or DECISION_RECORD.search(path) else history_form(sentence)
                    if match and form and feature in found:
                        self.history_line(path, line_at(form[1]), sentence, form[0], label)
                    elif match:
                        parts = decline_reason(body, match)
                        found[feature] = {'feature': feature, 'label': label, 'path': path,
                                          'line': line_at(noun.search(sentence).start()), 'quote': sentence[:400],
                                          'reason': ' \u2026 '.join(text for _, text in parts)[:400] or NO_REASON,
                                          'reason_line': line_at(parts[0][0]) if parts else None,
                                          'stale': stale_reason(feature, parts)}
                        if form:  # history narrative outside a decision record: a stale candidate, never a decline
                            found[feature]['history'] = True
                            self.history_line(path, line_at(form[1]), sentence, form[0], label)
        return [found[feature] for feature, _, _ in DECLINABLE if feature in found]

    def reconsider(self, stale, checks, documented, corpus, typed_at):
        """A "Worth reconsidering" note for a decline whose stated reason no longer holds, or None.

        Only with concrete evidence: the catalog's doc page showing the cited limitation is gone (and only when this
        Claude Code has the feature), or the file and line showing the situation the decision assumed has changed.
        """
        if not stale:
            return None
        _, _, kind, key, claim = stale
        if kind == 'doc':
            doc = self.source(key)
            needs = next((f.get('min_version') for f in self.catalog.get('features', []) if f.get('doc') == key
                          and f.get('min_version')), None)
            have = version_tuple(self.claude_version)
            if not doc['url'] or (needs and have and have < version_tuple(needs)):
                return None
            return {'claim': claim, 'evidence': {'url': doc['url'], 'heading': doc['heading']}}
        at = None
        if key == 'check':
            for command in documented:
                at = next(((path, number) for path, text in corpus.items() for number, line in prose(text)
                           if self.mentioned(command, line)), None)
                if at:
                    break
            if not at and checks and checks[0]['source'] in self.fileset:
                at = (checks[0]['source'], 1)
        elif key == 'typed' and typed_at:
            at = typed_at[0]
        return {'claim': claim, 'evidence': {'path': at[0], 'line': at[1]}} if at else None

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
                         '%d lines, %s words (about %s tokens), past the 200-line target' % (
                             item['lines'], format(words(item['text']), ','), format(tokens(item['text']), ',')),
                         "Cut it to what Claude can't learn from the repo; move "
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
                    self.stale_path(path, number, token)

    def stale_path(self, path, number, token):
        self.add('stale-ref:%s:%s' % (path, token), 'correctness', 'medium', 'Referenced path does not exist',
                 path, '%s line %d mentions %s' % (path, number, token),
                 'Point at an existing file, remove the reference, or create %s.' % token,
                 'memory-size', confidence='medium', line=number,
                 problem='`%s` does not exist; `%s:%d` names it.' % (token, path, number))

    # -- skills, subagents and context (#193) ------------------------------
    def project_skills(self):
        out = []
        for rel in self.files:
            if re.fullmatch(r'\.claude/skills/[^/]+/SKILL\.md', rel):
                text = self.text(rel) or ''
                fm = frontmatter(text)
                name = fm.get('name') if isinstance(fm.get('name'), str) and fm.get('name') else rel.split('/')[2]
                out.append({'path': rel, 'dir': rel.rsplit('/', 1)[0], 'name': name, 'fm': fm, 'text': text})
        return out

    def project_agents(self):
        out = []
        for rel in self.files:
            if re.fullmatch(r'\.claude/agents/[^/]+\.md', rel):
                text = self.text(rel) or ''
                fm = frontmatter(text)
                name = fm.get('name') if isinstance(fm.get('name'), str) and fm.get('name') else rel.split('/')[-1][:-3]
                out.append({'path': rel, 'name': name, 'fm': fm, 'text': text})
        return out

    def context(self, instructions, skills, agents):
        """The always-loaded table: instruction files and imports, visible skill and subagent descriptions, in words
        and estimated tokens; plus files an unconditional "see X" makes likely to be read (not loaded)."""
        rows = []
        for item in instructions:
            if item['loaded'] and item['kind'] in ('project', 'import', 'user'):
                how = 'every session' + (' (imported by `%s`)' % item['parent']['path'] if item.get('parent') else '')
                rows.append({'path': item['path'], 'what': 'instructions', 'loads': how,
                             'words': words(item['text']), 'tokens': tokens(item['text'])})
        for skill in skills:
            if truthy(skill['fm'].get('disable-model-invocation')):
                continue
            listing = ' '.join(v for v in (skill['fm'].get('description'), skill['fm'].get('when_to_use'))
                               if isinstance(v, str))
            rows.append({'path': skill['path'], 'what': '`%s` skill description' % skill['name'],
                         'loads': 'every session (skill listing)', 'words': words(listing), 'tokens': tokens(listing)})
            if len(listing) > LISTING_CAP:
                self.add('long-description:' + skill['path'], 'alignment', 'low', 'Skill description is cut short',
                         skill['path'], 'description and when_to_use are %d characters; the listing keeps %d'
                         % (len(listing), LISTING_CAP), 'Put the key use case first and cut the description and '
                         'when_to_use of %s to under %d characters.' % (skill['path'], LISTING_CAP),
                         'skill-frontmatter', problem='The description of `%s` is %d characters, so the skill listing '
                         'cuts it at %d.' % (skill['path'], len(listing), LISTING_CAP))
        agent_tokens = 0
        for agent in agents:
            text = agent['fm'].get('description') if isinstance(agent['fm'].get('description'), str) else ''
            agent_tokens += tokens(text)
            rows.append({'path': agent['path'], 'what': '`%s` subagent description' % agent['name'],
                         'loads': 'every session (subagent list)', 'words': words(text), 'tokens': tokens(text)})
        if agent_tokens > AGENT_WARNING:
            self.add('agent-descriptions', 'alignment', 'low', 'Subagent descriptions trigger the startup warning',
                     '.claude/agents', 'about %d tokens of subagent descriptions; the warning starts at %d'
                     % (agent_tokens, AGENT_WARNING), "Trim each subagent's description and move detail into its "
                     'system prompt, which loads only when it runs.', 'subagents')
        likely, seen = [], {os.path.realpath(i['abs']) for i in instructions if i['loaded']}
        for item in team_instructions(instructions):
            for _, number, line, rel in self.references(item['text'], os.path.dirname(item['abs'])):
                real = os.path.realpath(rel if os.path.isabs(rel) else self.abs(rel))
                if real in seen or not rel.endswith('.md') or UNSURE.search(line) or \
                        not re.search(r'\b(?:see|read|follow)\b', line, re.I):
                    continue
                seen.add(real)
                text = self.text(rel) or ''
                likely.append({'path': rel, 'what': 'linked from `%s:%d`' % (item['path'], number),
                               'loads': 'likely read, not loaded', 'words': words(text), 'tokens': tokens(text)})
        total = {'words': sum(r['words'] for r in rows), 'tokens': sum(r['tokens'] for r in rows)}
        lines = ['| File | What | Loads | Words | Tokens (est.) |', '|---|---|---|---|---|']
        for r in rows[:15] + likely[:5]:
            lines.append('| `%s` | %s | %s | %s | %s |' % (r['path'], r['what'], r['loads'], format(r['words'], ','),
                                                         format(r['tokens'], ',')))
        lines.append('| **Loaded every session** | | | %s | %s |' % (format(total['words'], ','),
                                                                     format(total['tokens'], ',')))
        return {'rows': rows[:CAP], 'likely_read': likely[:CAP], 'total': total, 'table': '\n'.join(lines)}

    def check_visible_skills(self, skills, agents, team):
        """A skill only a subagent reads (by path or `skills:`), named nowhere else, still loads its description."""
        commands = [self.text(f) or '' for f in self.files if re.fullmatch(r'\.claude/commands/.+\.md', f)]
        for skill in skills:
            if truthy(skill['fm'].get('disable-model-invocation')):
                continue
            by_path = [a for a in agents if skill['path'] in a['text'] or skill['dir'] + '/' in a['text']]
            preload = [a for a in agents if skill['name'] in as_names(a['fm'].get('skills'))]
            if not by_path and not preload:
                continue
            name = re.compile(r'(?<![\w/-])/?%s(?![\w-])' % re.escape(skill['name']))
            texts = [i['text'] for i in team] + [o['text'] for o in skills if o is not skill] + commands
            if any(name.search(t) or skill['path'] in t for t in texts):
                continue
            agent = (by_path or preload)[0]
            if preload:  # disable-model-invocation also stops preloading into the subagent
                fix = ("Move the rules in %s into the `%s` subagent's prompt (%s) and delete the skill, so its "
                       'description stops loading in every session; `disable-model-invocation: true` would also stop '
                       'the `skills:` preload.' % (skill['path'], agent['name'], agent['path']))
            else:
                fix = ('Add `disable-model-invocation: true` to the frontmatter of %s so its description stops loading '
                       'in every session; the `%s` subagent still reads the file by path:\n```yaml\n---\nname: %s\n'
                       'description: %s\ndisable-model-invocation: true\n---\n```'
                       % (skill['path'], agent['name'], skill['name'], skill['fm'].get('description') or '...'))
            self.add('visible-skill:' + skill['path'], 'alignment', 'low', 'Subagent-only skill is in the listing',
                     skill['path'], 'read only by %s (%s); named nowhere else' % (
                         agent['path'], 'by path' if by_path else 'skills: preload'), fix, 'skill-invocation',
                     problem='`%s` is read only by the `%s` subagent, but Claude can invoke it, so its description '
                     'loads in every session.' % (skill['name'], agent['name']))

    def generated(self):
        """{path: 'path:line' evidence} for files that say they are generated output (in their first ten lines) or
        that `.gitattributes` marks `linguist-generated`. A script is never called generated here."""
        marked = {}
        for number, line in enumerate((self.text('.gitattributes') or '').splitlines(), 1):
            parts = line.split()
            if len(parts) > 1 and re.fullmatch(r'linguist-generated(?:=true)?', parts[-1]) and '*' not in parts[0]:
                marked[parts[0].lstrip('/')] = '.gitattributes:%d' % number
        scripts = [f for f in self.files if f.count('/') == 1 and f.split('/')[0] in ('bin', 'scripts', 'script')]
        out = {}
        for path in self.files:
            evidence = marked.get(path)
            if not evidence and not self.data(path) and path not in scripts and \
                    os.path.splitext(path)[1] in ('', '.md', '.txt', '.json', '.yml', '.yaml', '.toml'):
                head = (self.text(path) or '').splitlines()[:10]
                at = next((n for n, line in enumerate(head, 1) if GENERATED_HEAD.search(line)), None)
                evidence = '%s:%d' % (path, at) if at else None
            if evidence:
                out[path] = evidence
        return out

    def duplicate_sources(self, instructions, skills, agents):
        """(path, line, sentence, normalized, stems) for each long sentence of the files duplication is judged on."""
        paths = [i['path'] for i in instructions if i['kind'] in ('project', 'import', 'nested')] + \
            [x['path'] for x in skills + agents] + \
            [f for f in self.files if f.endswith('.md') and (f.startswith('docs/') or '/' not in f) and not self.data(f)] + \
            [f for f in self.files if f.count('/') == 1 and f.split('/')[0] in ('bin', 'scripts', 'script')]
        sources, seen = [], set()
        for path in paths:
            real = os.path.realpath(self.abs(path))
            if real in seen or os.path.isabs(path) or path.startswith('..'):
                continue  # a symlinked file counts once, under its first name
            seen.add(real)
            text = self.text(path)
            if text is None:
                continue
            if not path.endswith('.md'):  # a script's long string literals and comments, each on its own line
                for number, line in enumerate(text.splitlines(), 1):
                    for literal in (next((g for g in m if g), '') for m in SCRIPT_TEXT.findall(line)):
                        if len(literal) < SCRIPT_TEXT_MIN:
                            continue
                        sources.extend((path, number, sentence, normalized(sentence), stems(sentence))
                                       for sentence, _ in sentences(literal) if words(sentence) >= DUP_MIN_WORDS)
                continue
            offset = 0
            if text.startswith('---') and '\n---' in text[3:]:
                end = text.find('\n---', 3) + 4
                offset, text = text[:end].count('\n'), text[end:]
            for sentence, line_at in sentences(text):
                if words(sentence) >= DUP_MIN_WORDS:
                    sources.append((path, line_at(0) + offset, sentence, normalized(sentence), stems(sentence)))
        return sources

    def check_duplicates(self, instructions, skills, agents, generated):
        """Rules copied word for word (and paraphrase candidates) across instruction files, skills, subagents, docs
        and script strings. A finding needs copies in at least three files: two uses don't earn an abstraction."""
        sources = self.duplicate_sources(instructions, skills, agents)
        groups = {}
        for path, line, sentence, norm, _ in sources:
            groups.setdefault(norm, []).append((path, line, sentence))
        out = []
        for norm, places in groups.items():
            files = []
            for path, line, _ in places:
                if path not in [p for p, _ in files]:
                    files.append((path, line))
            if len(files) < 2:
                continue
            mine, paraphrases = stems(places[0][2]), []
            for path, line, _, other, theirs in sources:
                if other == norm or path in [p for p, _ in files + paraphrases]:
                    continue
                shared = mine & theirs
                if len(shared) >= PARAPHRASE_MIN_STEMS and len(shared) >= 0.4 * min(len(mine), len(theirs)):
                    paraphrases.append((path, line))
            entry = {'text': places[0][2][:300], 'copies': ['%s:%d' % f for f in files],
                     'paraphrases': ['%s:%d' % f for f in paraphrases]}
            made = [p for p, _ in files if p in generated]
            if made and all(p in made or any(m in (self.text(p) or '') for m in made) for p, _ in files):
                continue  # generated output and the script that names it as an output: one source, not a copy
            if made:
                entry['generated'] = made
            out.append(entry)
        out.sort(key=lambda d: (-len(d['copies']), d['copies']))
        counted = [d for d in out if len(d['copies']) >= 3]
        if counted:
            first = counted[0]
            owner = next((c for c in first['copies'] if re.search(r'decision|adr', c, re.I)), first['copies'][0])
            owner_file = owner.rsplit(':', 1)[0]
            problem = 'One rule is copied word for word into %d files, %s: "%s"%s' % (
                len(first['copies']), joined('`%s`' % c for c in first['copies']), first['text'],
                ' It is paraphrased in %s.' % joined('`%s`' % c for c in first['paraphrases'])
                if first['paraphrases'] else '')
            if len(counted) > 1:
                problem += ' %d more rules are copied into three or more files.' % (len(counted) - 1)
            self.add('duplicate', 'alignment', 'low', 'Rule copied into several files', owner_file,
                     '%d rules copied into 3+ files' % len(counted),
                     'Keep the rule in %s and replace each other copy with a pointer to it, or drop the copy where %s '
                     'already loads; check the paraphrases say the same thing.' % (owner, owner_file),
                     'memory-size', confidence='medium', problem=problem)
        return out[:CAP]

    # -- stale facts (#193) ------------------------------------------------
    def stale_facts(self, path, text, base):
        """Commands, scripts and dependencies a file names that don't exist."""
        state, package, _ = self.load_json('package.json') if 'package.json' in self.fileset else ('missing', None, None)
        scripts = package.get('scripts') if state == 'ok' and isinstance(package, dict) else None
        makefile = self.text('Makefile') if 'Makefile' in self.fileset else None
        just = next((self.text(f) for f in ('justfile', 'Justfile', '.justfile') if f in self.fileset), None)
        targets = set(re.findall(r'^([\w.-]+)(?:[ \t]+[\w.-]+)*[ \t]*:(?!=)', makefile or '', re.M))
        recipes = set(re.findall(r'^@?([\w-]+)(?:[ \t]+[^:=\n]*)?:(?!=)', just or '', re.M))
        previous = ''
        for number, line in prose(text):
            context, previous = previous + ' ' + line, line
            if HISTORY.search(line) or CONDITIONAL.search(line):
                continue
            for span in re.findall(r'`([^`\n]+)`', line):
                if re.search(r'\b(?:no|not|never|without|lacks?)\b[^`.;]{0,25}`%s`' % re.escape(span), context, re.I):
                    continue  # the file says it isn't there ("this repository provides no `bin/container`")
                for part in split_commands(span):
                    tokens_ = strip_dot(part).split()
                    if not tokens_ or re.search(r'[<>{}$*]', part):
                        continue
                    missing, command = None, tokens_[0]
                    match = re.match(r'(npm|pnpm|yarn|bun) run ([\w:.-]+)$', ' '.join(tokens_[:3]))
                    if match and isinstance(scripts, dict) and match.group(2) not in scripts:
                        missing, command = '`package.json` has no `%s` script' % match.group(2), match.group(0)
                    elif tokens_[0] == 'make' and len(tokens_) > 1 and makefile is not None and '=' not in tokens_[1] \
                            and not re.search(r'^\s*-?include\b|%', makefile, re.M) and tokens_[1] not in targets:
                        missing, command = '`Makefile` has no `%s` target' % tokens_[1], ' '.join(tokens_[:2])
                    elif tokens_[0] == 'just' and len(tokens_) > 1 and just is not None and tokens_[1] not in recipes:
                        missing, command = 'the justfile has no `%s` recipe' % tokens_[1], ' '.join(tokens_[:2])
                    elif re.fullmatch(r'(?:bin|scripts?)/[\w.-]+', tokens_[0]) and not self.exists(tokens_[0]) and \
                            not os.path.exists(os.path.join(base, tokens_[0])):
                        missing = 'there is no such file'
                    if missing:
                        self.add('stale-command:%s:%s' % (path, command), 'correctness', 'medium',
                                 'Named command does not exist', path, '%s line %d names %s' % (path, number, command),
                                 'Point at the command that exists, or remove the reference.', 'memory-size',
                                 confidence='medium', line=number,
                                 problem='`%s` does not exist (%s); `%s:%d` names it.' % (command, missing, path, number))
        for sentence, line_at in sentences(text):
            named = [m for m in MANIFESTS if m in sentence]
            if not named or not DEP_WORDS.search(sentence) or HISTORY.search(sentence):
                continue
            manifest = named[0]
            content = self.text(manifest) if manifest in self.fileset else None
            if content is None:
                continue
            flat = re.sub(r'[-_.]', '', content.lower())
            empty = bool(manifest == 'pyproject.toml' and re.search(r'^dependencies\s*=\s*\[\s*\]', content, re.M)) or (
                manifest == 'package.json' and '"dependencies"' not in content)
            for name in re.findall(r'`([A-Za-z][\w.-]*)`', sentence):
                if name in MANIFESTS or re.search(r'\.(?:md|py|js|ts|toml|json|txt|ya?ml|cfg|lock)$', name) \
                        or re.sub(r'[-_.]', '', name.lower()) in flat:
                    continue
                self.add('stale-dep:%s:%s' % (path, name), 'correctness', 'medium', 'Named dependency is not declared',
                         path, '%s line %d names %s; %s does not declare it' % (path, line_at(0), name, manifest),
                         'Remove or correct the dependency claim, or declare %s in %s.' % (name, manifest),
                         'memory-size', confidence='medium', line=line_at(0),
                         problem='`%s` is not a declared dependency in `%s`%s; `%s:%d` names it.' % (
                             name, manifest, '; `%s` declares no dependencies' % manifest if empty else '',
                             path, line_at(0)))

    def missing_names(self, path, text, known):
        """Skill and subagent names a file names, as "the `x` skill", that no project file defines."""
        for number, line in prose(text):
            if HISTORY.search(line):
                continue
            for match in NAMED.finditer(line):
                name = (match.group(1) or match.group(2) or '').lower()
                if name and name not in known and name not in BUILT_IN_NAMES:
                    self.add('missing-name:%s:%s' % (path, name), 'correctness', 'medium',
                             'Named skill or subagent does not exist', path, '%s line %d names %s' % (path, number, name),
                             'Create it, point at the one that exists, or remove the reference.', 'skill-locations',
                             confidence='medium', line=number,
                             problem='No skill, command or subagent named `%s` exists; `%s:%d` names it.' % (
                                 name, path, number))

    # -- enforcement (#193) ------------------------------------------------
    def check_gates(self, team, settings):
        """Gate verbs the instructions say need a person, with no ask or deny rule for the command."""
        rules = [r for s in settings if s['scope'] == 'project' for kind in ('ask', 'deny')
                 for r in rules_of(s['data'], kind)]
        spans = [span for item in team for span in code_spans(item['text'])]
        gates = []
        for item in team:
            for sentence, line_at in sentences(item['text']):
                if '?' in sentence or not PERSON.search(sentence) or not NEED.search(sentence) \
                        or HISTORY.search(sentence):
                    continue
                for verb, pattern in GATE_VERBS:
                    if not pattern.search(sentence) or any(g['verb'] == verb for g in gates):
                        continue
                    command = self.gate_command(verb, re.findall(r'`([^`\n]+)`', sentence) + spans)
                    if command:
                        gates.append({'verb': verb, 'command': command, 'path': item['path'], 'line': line_at(0)})
        unguarded = [g for g in gates if not any(bash_rule_matches(r, g['command'])
                                                 or bash_rule_matches(r, g['command'] + ' x') for r in rules)]
        if not unguarded:
            return gates
        ask = ['Bash(%s *)' % g['command'] for g in unguarded]
        real_gate = ('Branch protection on `main` (required reviews before a merge) is the real gate'
                     if any(g['verb'] in ('merge', 'push to main') for g in unguarded) else
                     "The deploy or release system's own approval is the real gate")
        self.add('gate-ask', 'coverage', 'medium', 'Human gates are prose only', '.claude/settings.json',
                 '; '.join('%s:%d needs a person for %s; no ask or deny rule covers %s'
                           % (g['path'], g['line'], g['verb'], g['command']) for g in unguarded),
                 'Add to .claude/settings.json: %s. %s: an ask rule only prompts inside Claude Code, and a client-side '
                 'rule can be got around by running the command another way.'
                 % (json.dumps({'permissions': {'ask': ask}}), real_gate), 'bash-rule-limits', confidence='medium',
                 subject=joined(g['verb'] for g in unguarded), line=unguarded[0]['line'],
                 problem=' '.join('`%s:%d` says a person must approve %s, but no ask or deny rule covers `%s`, so '
                                  'Claude can run it without asking.' % (g['path'], g['line'], g['verb'], g['command'])
                                  for g in unguarded))
        return gates

    def gate_command(self, verb, spans):
        """The command a gate verb runs: one the instructions name (a script named for the verb, or a command cut
        after the verb word), a project script named for it, or the usual command for a merge or a push."""
        stem = GATE_STEMS[verb]
        for span in spans:
            for part in split_commands(span):
                tokens_ = strip_dot(part).split()
                if not tokens_ or not re.fullmatch(r'[\w./-]+', tokens_[0]):
                    continue
                if re.fullmatch(r'(?:bin|scripts?)/[\w.-]+', tokens_[0]):
                    if tokens_[0].split('/')[1].split('.')[0] == stem:
                        return tokens_[0]
                    continue
                for i, token in enumerate(tokens_[1:4], 1):
                    if not re.fullmatch(r'[\w-]+', token):
                        break
                    if token.lower() == stem:
                        return ' '.join(tokens_[:i + 1])
        script = next((f for f in self.files if f.count('/') == 1 and f.split('/')[0] in ('bin', 'scripts', 'script')
                       and f.split('/')[1].split('.')[0] == stem), None)
        return script or {'merge': 'gh pr merge', 'push to main': 'git push'}.get(verb)

    def check_git_hooks(self, sources, settings):
        """Opt-in git hooks (core.hooksPath, husky, lefthook, pre-commit) that nothing enables in agent sessions."""
        texts = {f: self.text(f) or '' for f in sources}
        found = None
        for path, text in texts.items():
            match = re.search(r'core\.hooksPath[ \t=]+([\w./-]+)', text)
            if match:
                found = ('git config core.hooksPath %s' % match.group(1), path)
                break
        for marker, command in (('.husky', 'npx husky'), ('lefthook.yml', 'lefthook install'),
                                ('.pre-commit-config.yaml', 'pre-commit install')):
            if not found and (marker in self.dirs or marker in self.fileset):
                found = (command, marker)
        if not found or any(GIT_HOOK_DECLINE.search(t) for t in texts.values()):
            return
        starts = [h['command'] for s in settings if s['scope'] == 'project' and isinstance(s['data'].get('hooks'), dict)
                  for g in as_list(s['data']['hooks'].get('SessionStart')) if isinstance(g, dict)
                  for h in as_list(g.get('hooks')) if isinstance(h, dict) and isinstance(h.get('command'), str)]
        if any(re.search(r'hooksPath|husky|lefthook|pre-commit', c) for c in starts):
            return
        tool = found[0].split()[0]
        command = found[0] if tool == 'git' else 'command -v %s >/dev/null 2>&1 && %s || true' % (tool, found[0])
        hook = {'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': command}]}]}}
        self.add('git-hooks', 'coverage', 'low', 'Git hooks are opt-in', found[1],
                 '%s sets up git hooks with %s; no SessionStart hook runs it' % (found[1], found[0]),
                 'Add to .claude/settings.json: %s, so agent and cloud sessions get the hooks too.' % json.dumps(hook),
                 'hooks-session-start', confidence='medium',
                 problem='The git hooks need `%s` (`%s`), and nothing runs it in agent or cloud sessions, so their '
                 'commits skip the hooks.' % (found[0], found[1]))

    # -- scope (#193) -------------------------------------------------------
    def scope(self, instructions):
        """Files above the git root (one line, not graded), whether they change how the repo's files load, and
        symlinked instruction files with their real paths."""
        above, parent = [], os.path.dirname(self.root)
        while self.ceiling is None or os.path.commonpath([parent, self.ceiling]) == self.ceiling:
            for rel in ROOT_INSTRUCTIONS:
                path = os.path.join(parent, rel)
                if os.path.isfile(path) and path != os.path.join(HOME, '.claude', 'CLAUDE.md'):
                    above.append(os.path.relpath(path, self.root).replace(os.sep, '/'))
            if os.path.dirname(parent) == parent:
                break
            parent = os.path.dirname(parent)
        links = []
        for rel in ROOT_INSTRUCTIONS:
            if rel in self.fileset and os.path.islink(self.abs(rel)):
                links.append({'path': rel, 'real': self.display(os.path.realpath(self.abs(rel)))})
        lines = []
        if above:
            claude_above = [a for a in above if a.split('/')[-1] in ('CLAUDE.md', 'CLAUDE.local.md')]
            lines.append('Outside the repo, not graded: %s above the repo%s.' % (
                joined('`%s`' % a for a in above),
                '; %s %s in every session here' % (joined('`%s`' % a for a in claude_above),
                                                   'loads' if len(claude_above) == 1 else 'load')
                if claude_above else ''))
            if claude_above and 'AGENTS.md' in self.fileset:
                link = next((l for l in links if l['real'] == 'AGENTS.md'), None)
                real = os.path.realpath(self.abs('AGENTS.md'))
                imported = any(i['loaded'] and real in i.get('reals', ()) for i in instructions)
                lines.append("Because `%s` above the repo loads, the repo's `AGENTS.md` is not read on its own%s." % (
                    claude_above[0], '; here it still loads because `%s` is a symlink to it' % link['path'] if link else
                    '; here it still loads because a loaded file imports it' if imported else
                    '; import it with `@AGENTS.md` from a `CLAUDE.md` in the repo'))
        for link in links:
            lines.append('`%s` is a symlink to `%s`; the audit reads `%s`.' % (link['path'], link['real'], link['real']))
        return {'above': above, 'symlinks': links, 'lines': lines}

    # -- main -------------------------------------------------------------
    def run(self):
        instructions = self.instructions()
        settings = self.settings()
        manifests = self.plugin_manifests()
        self.check_settings(settings)
        self.check_files(manifests)
        self.check_instructions(instructions)
        skill_docs, agent_docs = self.project_skills(), self.project_agents()
        team = team_instructions(instructions)
        commands = [f for f in self.files if re.fullmatch(r'\.claude/commands/.+\.md', f)]
        # Skill, command and subagent names defined anywhere in the repository, plugins' included.
        known = {x['name'].lower() for x in skill_docs + agent_docs} | {
            f.split('/')[-2].lower() for f in self.files if f.endswith('/SKILL.md')} | {
            f.split('/')[-1][:-3].lower() for f in self.files if re.search(r'(?:^|/)(?:agents|commands)/[^/]+\.md$', f)}
        plugins_on = any(isinstance(s['data'].get('enabledPlugins'), dict) and any(s['data']['enabledPlugins'].values())
                         for s in settings)
        for item in [i for i in instructions if i['kind'] in ('project', 'nested', 'import')
                     and not os.path.isabs(i['path'])]:
            self.stale_facts(item['path'], item['text'], os.path.dirname(item['abs']))
            if item in team and not plugins_on:  # an enabled plugin can supply names the scan can't see
                self.missing_names(item['path'], item['text'], known)
        for rel in [x['path'] for x in skill_docs + agent_docs] + commands:
            text, base = self.text(rel) or '', os.path.dirname(self.abs(rel))
            for number, line in prose(text):
                for token in path_tokens(line):
                    if not (os.path.exists(os.path.join(self.root, token)) or os.path.exists(os.path.join(base, token))
                            or self.ignored([token])):
                        self.stale_path(rel, number, token)
            self.stale_facts(rel, text, base)
            if not plugins_on:
                self.missing_names(rel, text, known)
        gates = self.check_gates(team, settings)
        generated = self.generated()
        duplicates = self.check_duplicates(instructions, skill_docs, agent_docs, generated)
        context = self.context(instructions, skill_docs, agent_docs)
        self.stale_history(dict.fromkeys(
            [i['path'] for i in instructions if i['kind'] in ('project', 'nested', 'import')] +
            [x['path'] for x in skill_docs + agent_docs] + commands + [r['path'] for r in context['likely_read']]))
        self.check_visible_skills(skill_docs, agent_docs, team)
        scope = self.scope(instructions)
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
        typed, typed_at = [], []
        for f in self.files:
            name = f.split('/')[-1]
            if f.count('/') <= 2 and (name in LANGUAGES or name.endswith('.csproj')) and name not in typed \
                    and not self.data(f):
                typed.append(name)
                typed_at.append((f, 1))
        pyproject = self.text('pyproject.toml') or ''
        tool = re.search(r'^\[tool\.(mypy|pyright)\]', pyproject, re.M)
        if tool:
            typed.append('pyproject.toml [tool.mypy/pyright]')
            typed_at.append(('pyproject.toml', pyproject.count('\n', 0, tool.start()) + 1))
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
                        or (re.search(r'\brun\b', line, re.I) and any(checking(span) for span in re.findall(
                            r'`([^`\n]+)`', line)))
                        or (checks and re.search(r'\b(?:check|test|lint|verify)\b[^.]{0,30}\b(?:work|changes?|code)\b',
                                                 line, re.I))):
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
            entry['reconsider'] = self.reconsider(entry.pop('stale'), checks, documented, corpus, typed_at)
        gone = {fid for entry in declined for fid in entry['finding_ids']}
        self.findings = [f for f in self.findings if f['id'] not in gone]
        # A retirement told as history still keeps its feature out of the plan, but only a decision record lists it.
        told = [entry for entry in declined if entry.pop('history', None)]
        declined = [entry for entry in declined if entry not in told]
        if not any(entry['feature'] == 'stop-hook' for entry in declined + told):  # a stated decision against hooks
            self.check_git_hooks([i['path'] for i in team] + [f for f in self.files if f in (
                'README.md', 'CONTRIBUTING.md', 'Makefile', 'package.json', 'justfile') or (
                f.startswith('docs/') and f.endswith('.md') and not self.data(f)) or (
                f.count('/') == 1 and f.split('/')[0] in ('bin', 'scripts', 'script'))], settings)

        # dismissed findings
        dismissed, reasons, where = [], {}, {}
        mine = user_dismissed(self.data_dir, self.root, self.git)
        for label, rel, path in (('shared', DISMISSED, self.abs(DISMISSED) if DISMISSED in self.fileset else None),
                                 ('per user', USER_DISMISSED % repo_key(self.root, self.git), mine)):
            if not path or not os.path.isfile(path):
                continue
            state, data, _ = self.load_json(rel, path)
            entries = data.get('dismissed') if state == 'ok' and isinstance(data, dict) else None
            if not isinstance(entries, list):
                self.limits.append('%s is not valid; nothing dismissed from it' % rel)
                continue
            for e in entries:
                if isinstance(e, dict) and isinstance(e.get('id'), str) and e['id'] not in reasons:
                    reasons[e['id']], where[e['id']] = e.get('reason', ''), (label, rel)
        dismissed = [dict(f, reason=reasons[f['id']], stored=where[f['id']][1]) for f in self.findings
                     if f['id'] in reasons]
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
        for entry in declined + told:
            item = {'allowlist': 'allowlist', 'stop-hook': 'enforced'}.get(entry['feature'])
            if item and entry['finding_ids']:
                status[item] = ('declined', '%s in %s:%d' % ('declined' if entry in declined else
                                                             'not recommended: history line', entry['path'],
                                                             entry['line']), [])
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
            'instructions': capped([dict({'path': i['path'], 'lines': i['lines'], 'words': words(i['text']),
                                          'tokens': tokens(i['text']), 'kind': i['kind'], 'loaded': i['loaded']},
                                         **({'real': self.display(os.path.realpath(i['abs']))}
                                            if os.path.islink(i['abs']) else {}),
                                         **({'gitignored': 'CLAUDE.local.md' in self.ignored(['CLAUDE.local.md'])}
                                            if i['path'] == 'CLAUDE.local.md' else {}))
                                    for i in instructions], 'inventory.instructions', t),
            'instruction_loading': self.loading(instructions),
            'instruction_words_loaded': sum(words(i['text']) for i in instructions
                                            if i['loaded'] and i['kind'] != 'nested'),
            'rules': capped([{'path': f, 'paths_frontmatter': 'paths' in frontmatter(self.text(f) or '')}
                             for f in self.files if f.startswith('.claude/rules/') and f.endswith('.md')],
                            'inventory.rules', t),
            'settings': [settings_entry(s) for s in settings],
            'skills': capped([{'path': f, 'name': 'name' in frontmatter(self.text(f) or ''),
                               'description': 'description' in frontmatter(self.text(f) or '')} for f in skills],
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
        for entry in declined:
            entry['defects'] = []
            for item in plan['items'] + plan['overflow']:
                if item['kind'] in DECLINE_DEFECTS.get(entry['feature'], ()):
                    item['declined'] = {'label': entry['label'], 'path': entry['path'], 'line': entry['line']}
                    entry['defects'].append(item['title'])
        setup = bool(roots or project_settings or '.claude' in self.dirs)
        kinds = {f['id'].split(':')[0] for f in self.findings}
        handoffs = []
        if len(skill_docs) >= 10 or 'long-description' in kinds:
            handoffs.append({'command': '/skill-doctor', 'why': 'see what each skill costs and how often it runs'})
        if 'allowlist' in kinds:
            handoffs.append({'command': '/fewer-permission-prompts', 'why': 'confirm the allowlist from real use'})
        if not checks and any(f.endswith(tuple(EXTENSIONS)) for f in self.files):
            handoffs.append({'command': '/run-skill-generator', 'why': 'record how to build and run the project'})
            handoffs.append({'command': '/verify', 'why': 'confirm changes against the running project'})
        if 'oversized' in kinds or context['total']['words'] > 3000:
            handoffs.append({'command': '/context', 'why': 'see what fills the context window in a live session'})
        footer_lines = []
        if dismissed:
            stores = sorted({d['stored'] for d in dismissed})
            footer_lines.append('Dismissed: %d (stored in %s).' % (len(dismissed), joined('`%s`' % x for x in stores)))
        out = {'claudit': VERSION, 'catalog_version': self.catalog.get('catalog_version'),
               'claude_version': self.claude_version, 'root': '.', 'git': self.git, 'inventory': inventory,
               'signals': signals, 'profiles': profiles, 'findings': capped(self.findings, 'findings', t),
               'plan': plan, 'grades': grades_of(plan, setup), 'optional': optional, 'declined': declined,
               'context': context, 'scope': scope, 'duplicates': duplicates, 'gates': gates, 'handoffs': handoffs,
               'generated': [{'path': p, 'evidence': e} for p, e in sorted(generated.items())][:CAP],
               'stale_candidates': sorted(self.history, key=lambda c: (c['path'], c['line']))[:CAP],
               'footer': audited(self.root, self.git), 'footer_lines': footer_lines,
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


# A Markdown admonition marker (`!!! tip`, `??? note "Title"`): a heading for its indented text, never part of it.
ADMONITION = re.compile(r'(?:!!!|\?\?\?\+?)\s+[\w-]+(?:\s+"[^"]*")?\s*$')


def sentences(text):
    """(sentence, line number of an offset in it) for a text's prose; a paragraph or list item may wrap over lines."""
    units, current, last = [], [], None
    for number, line in prose(text):
        body = line.strip().lstrip('>').strip()
        heading = body.startswith(('#', '|')) or ADMONITION.match(body) is not None
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
        kind = 'stale' if kind in STALE_KINDS else kind  # every stale fact in one file is one item
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
    medium, and a stale fact (a Correctness finding) as one Alignment low, so Alignment is never A while one
    stands. Coverage: A to D for 0, 1, 2 or 3+ gaps, F with no setup at all.
    """
    groups = plan['items'] + plan['overflow']
    grades = {}
    for grade in GRADES:
        mine = [g for g in groups if grade in g['grades'] or (grade == 'alignment' and g['kind'] in (
            'no-instructions', 'stale'))]
        if grade == 'coverage':
            letter = 'F' if not setup else 'ABCD'[min(len(mine), 3)]
        else:
            severities = ['medium' if g['kind'] == 'no-instructions' else
                          'low' if g['kind'] == 'stale' and grade == 'alignment' else g['severity'] for g in mine]
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


def run(argv, stdin=None, timeout=10, cwd=None, env=None):
    try:
        return subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=timeout, cwd=cwd,
                              stdin=None if stdin is not None else subprocess.DEVNULL,
                              env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', **(env or {})))
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


def dismiss(root, fid, reason, shared=False, data_dir=None, git=True):
    """Record a dismissal: per user in the plugin's data folder, keyed by repository, or with `shared` in the
    project's .claude/claudit-dismissed.json for the whole team."""
    if not fid.strip() or not reason.strip():
        raise UsageError('--id and --reason must be non-empty')
    if shared:
        folder, shown = os.path.join(root, '.claude'), DISMISSED
        inside = os.path.join(os.path.realpath(root), '.claude')
    elif data_dir:
        folder = os.path.join(data_dir, 'dismissed')
        shown = USER_DISMISSED % repo_key(root, git)
        inside = os.path.realpath(folder) if not os.path.islink(folder) else None
    else:
        raise UsageError('CLAUDE_PLUGIN_DATA is not set; pass --data, or --shared to write %s' % DISMISSED)
    path = os.path.join(folder, 'claudit-dismissed.json' if shared else repo_key(root, git) + '.json')
    if os.path.islink(folder) or os.path.islink(path) or (os.path.exists(path) and not os.path.isfile(path)) \
            or (os.path.exists(folder) and not os.path.isdir(folder)) \
            or os.path.dirname(os.path.realpath(path)) != inside:
        raise UsageError('refusing to write %s: it or its folder is a symlink, not a file/directory, '
                         'or not where it belongs' % shown)
    data = {'version': 1, 'dismissed': []}
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            raise UsageError('%s is not valid JSON; fix or remove it first' % shown)
        if not isinstance(data, dict) or not isinstance(data.get('dismissed'), list):
            raise UsageError('%s has no "dismissed" list' % shown)
    added = not any(isinstance(e, dict) and e.get('id') == fid for e in data['dismissed'])
    if added:
        data['dismissed'].append({'id': fid, 'reason': reason, 'date': datetime.date.today().isoformat()})
        os.makedirs(folder, exist_ok=True)
        if os.path.dirname(os.path.realpath(path)) != (inside or os.path.realpath(folder)):
            raise UsageError('refusing to write %s: its folder moved' % shown)
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
    return {'dismissed': fid, 'added': added, 'path': shown}


# `deep`: Claude Code's own instruction audit, headless and read-only, as the doctor-combined baseline runs it (#192):
# project settings only (so no user plugin, Claudit included, loads), no file edits and no Bash (denied by flag, so
# a trusted project's allow rules can't grant it; in an untrusted folder print mode denies it anyway), no MCP
# servers, no saved session.
DEEP_PROMPT = '/doctor prompt-audit .'
DEEP_FLAGS = ('--setting-sources', 'project', '--disallowedTools', 'Edit', 'Write', 'NotebookEdit', 'Bash',
              'Skill(claudit:claudit)', 'Skill(claudit:claudit *)', '--strict-mcp-config', '--no-session-persistence',
              '--output-format', 'json')
DEEP_MODEL = 'CLAUDIT_DEEP_MODEL'  # the eval runner pins the nested model to its arm's model
DEEP_TIMEOUT = 170  # seconds, inside the 180 s --deep budget
DEEP_RECORD = 'CLAUDIT_DEEP_RECORD'  # a file the eval runner reads the nested call's cost and time from


def claude_doctor(root):
    """`claude doctor`'s invalid-settings section (user settings included) as one line; never graded."""
    proc = run(['claude', 'doctor'], timeout=30, cwd=root, env={'DISABLE_AUTOUPDATER': '1'})
    if proc is None or proc.returncode != 0:
        return {'status': 'unavailable', 'line': 'claude doctor: could not run (%s).' % (
            'not found or timed out' if proc is None else 'exit %d' % proc.returncode)}
    found, inside = [], False
    for line in proc.stdout.splitlines():
        if line.strip() == 'Invalid settings':
            inside = True
        elif inside and line.startswith('- '):
            found.append(line[2:].replace(root, '.').replace(HOME, '~').split(' Suggested fix')[0].strip())
        elif inside and line.strip() and not line.startswith(' '):
            inside = False
    if not found:
        return {'status': 'ok', 'line': 'claude doctor: no invalid settings.', 'invalid': []}
    return {'status': 'ok', 'invalid': found[:CAP], 'line': 'claude doctor: %d invalid setting%s: %s.' % (
        len(found), '' if len(found) == 1 else 's', '; '.join(found[:5])[:600])}


def deep(root, model, budget):
    """Run `/doctor prompt-audit .` headless in the project, read-only, and `claude doctor`; never raises. A model
    in CLAUDIT_DEEP_MODEL (set by the eval runner) replaces `model`."""
    model = os.environ.get(DEEP_MODEL) or model
    command = ['claude', '-p', DEEP_PROMPT, *DEEP_FLAGS, '--model', model, '--max-budget-usd', '%g' % budget]
    started = datetime.datetime.now()
    proc = run(command, timeout=DEEP_TIMEOUT, cwd=root, env={'DISABLE_AUTOUPDATER': '1'})
    seconds = round((datetime.datetime.now() - started).total_seconds(), 1)
    try:
        raw = json.loads(proc.stdout) if proc is not None else {}
    except ValueError:
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    report = raw.get('result') if isinstance(raw.get('result'), str) else ''
    if proc is None:
        status = 'could not run: claude was not found or timed out after %d s' % DEEP_TIMEOUT
    elif proc.returncode != 0 or raw.get('is_error') or not report.strip():
        reason = (report or proc.stderr or proc.stdout or '').strip().splitlines()
        status = 'could not run: exit %d%s' % (proc.returncode, ', ' + reason[0][:200] if reason else '')
    else:
        status = 'ran'
    denials = raw.get('permission_denials')
    audit = {'status': status, 'report': report if status == 'ran' else '', 'model': model,
             'max_budget_usd': budget, 'seconds': seconds,
             'cost_usd': raw.get('total_cost_usd') if isinstance(raw.get('total_cost_usd'), (int, float)) else 0,
             'permission_denials': len(denials) if isinstance(denials, list) else 0,
             'command': ' '.join(command)}
    out = {'prompt_audit': audit, 'claude_doctor': claude_doctor(root)}
    record = os.environ.get(DEEP_RECORD)
    if record:
        try:
            with open(record, 'a', encoding='utf-8') as handle:
                handle.write(json.dumps(redact(dict(audit, report=report))) + '\n')  # its raw text is evidence
        except OSError:
            pass
    return redact(out)


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
    scan.add_argument('--data', default=os.environ.get('CLAUDE_PLUGIN_DATA') or None)
    pages = sub.add_parser('new-pages')
    pages.add_argument('--pages', required=True)
    nested = sub.add_parser('deep')
    nested.add_argument('--root', default='.')
    nested.add_argument('--model', default='sonnet')
    nested.add_argument('--max-budget-usd', type=float, default=0.5)
    gone = sub.add_parser('dismiss')
    gone.add_argument('--root', default='.')
    gone.add_argument('--id', required=True)
    gone.add_argument('--reason', required=True)
    gone.add_argument('--shared', action='store_true')
    gone.add_argument('--data', default=os.environ.get('CLAUDE_PLUGIN_DATA') or None)
    try:
        args = parser.parse_args(argv)
        if args.command == 'scan':
            root, git = resolve_root(args.root)
            result = Scan(root, git, load_catalog(), claude_version(args.claude_version), args.user, args.data).run()
        elif args.command == 'new-pages':
            text = sys.stdin.read() if args.pages == '-' else args.pages
            result = new_pages(text, load_catalog())
        elif args.command == 'deep':
            if not args.max_budget_usd > 0:
                raise UsageError('--max-budget-usd must be above 0')
            result = deep(resolve_root(args.root)[0], args.model, args.max_budget_usd)
        elif args.command == 'dismiss':
            root, git = resolve_root(args.root)
            result = dismiss(root, args.id, args.reason, args.shared, args.data, git)
        else:
            raise UsageError('expected a subcommand: scan, new-pages, deep or dismiss')
    except UsageError as error:
        print(json.dumps({'error': redact(str(error))}))
        return 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
