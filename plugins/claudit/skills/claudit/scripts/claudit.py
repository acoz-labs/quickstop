#!/usr/bin/env python3
"""Claudit 5 helper: a deterministic, read-only scan that lists what is wrong in a project's Claude Code setup.

Subcommands: scan, dismiss. Standard library only; Python 3.9+. Every finding the
report shows comes from this scan, with a real file and line and an exact fix.
The only write is `dismiss`: per user to ${CLAUDE_PLUGIN_DATA}, or with --shared
to <root>/.claude/claudit-dismissed.json. The helper never prints secret values
and never reads ~/.claude.json.
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

VERSION = '5.0.0'
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
FENCE = re.compile(r'^\s*(```|~~~)')
RUNNER = re.compile(r'((?:make|just) (?:test|check|lint|ci)\b|(?:npm|pnpm|yarn|bun)(?: run)? (?:test|lint|check|typecheck)\b[\w:-]*'
                    r'|go test\b(?: \./\.\.\.)?|cargo (?:test|clippy|check)\b|pytest\b'
                    r'|python3?(?:\.\d+)? -m (?:pytest|unittest)\b)')
# A must-run rule enforces a check at the end of the work, so it names that moment (#207 dev set: "always run the test
# with the CI flags when updating snapshots" or "Python commands must run in the virtualenv" are not must-run rules).
COMPLETION = re.compile(r"\bbefore (?:you (?:\w+ )?)?(?:report|finish|commit|push|mark|say|claim|hand|open|merg|declar|"
                        r"complet|submit)|\bbefore (?:every|each|any|a|the) (?:commit|push|pull request|PR|merge|hand-?off)\b|"
                        r"\bat the end of (?:a|the|each|every|your) (?:task|change|session|turn)\b|"
                        r"\bwhen (?:you(?:['\u2019]re| are)? )?(?:done|finished)\b", re.I)
MUST_NOT = re.compile(r"\b(must not|mustn't|never)\b", re.I)
LINK = re.compile(r'\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)')
LINK_DEF = re.compile(r'^\s{0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?')
MD_PATH = re.compile(r'(?<![\w/.@-])((?:\.{1,2}/)*[\w.-]+(?:/[\w.-]+)*\.md)(?![\w/-])', re.I)
IMPORT = re.compile(r'(?:^|(?<=\s))@([^\s`\'"()<>\[\]]+)')
TOKEN_SPLIT = re.compile(r'[\s`"\'()\[\],;|]+')
HOME = os.path.expanduser('~')
# The docs page and heading each finding cites, so reports quote them verbatim. Checked against the live docs when
# a release is built; nothing is downloaded at run time.
DOCS = {
    'memory-size': ('https://code.claude.com/docs/en/memory', 'Write effective instructions'),
    'memory-imports': ('https://code.claude.com/docs/en/memory', 'Import additional files'),
    'memory-agents-md': ('https://code.claude.com/docs/en/memory', 'AGENTS.md'),
    'permission-rules': ('https://code.claude.com/docs/en/permissions', 'Permission rule syntax'),
    'bash-rule-limits': ('https://code.claude.com/docs/en/permissions', "What a Bash rule doesn't match"),
    'ignored-values': ('https://code.claude.com/docs/en/settings', 'A value you set is ignored'),
    'stop-hook': ('https://code.claude.com/docs/en/best-practices', 'Enforce the check with a Stop hook'),
    'hooks-stop': ('https://code.claude.com/docs/en/hooks', 'Stop'),
    'skill-locations': ('https://code.claude.com/docs/en/skills', 'Choose where skills load'),
    'skill-frontmatter': ('https://code.claude.com/docs/en/skills', 'Frontmatter reference'),
    'skill-invocation': ('https://code.claude.com/docs/en/skills', 'Control who invokes a skill'),
    'subagents': ('https://code.claude.com/docs/en/sub-agents', 'Create custom subagents'),
}
# Features a project can decline in its docs: (finding kind, label, the feature as a bare noun). A decline is of
# the feature itself, never of one instance ("the old SessionStart hook"), an item in it ("rm from the allowlist")
# or a place ("disabled in CI", "secrets in hooks").
# Only these two declines matter in Claudit 5: they hold back the stop-hook and allowlist findings.
DECLINABLE = (
    ('stop-hook', 'Hooks', r'hooks'),
    ('allowlist', 'Pre-approved commands', r'allow-?lists?|allow rules|pre-?approvals|pre-?approved commands'),
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
# a reversal, a time, an aside) never matches and keeps the decision: allow-only. Evidence is a DOCS key (a page
# showing the limitation is gone) or a scan fact ('check': a check command exists).
CANT = r"(?:can ?not|can't|are unable to|is unable to)"
CC = r'(?:claude code|claude)'
NO_CHECK = (r'(?:there (?:is|are) no|(?:the )?(?:project|repository|repo) has no) (?:check(?: command| script)?s?|tests?|'
            r'test suite)(?: to run)?|there is nothing to (?:check|run)')
STALE_REASONS = (
    ('stop-hook', r'(?:%s )?(?:hooks|a hook|stop hooks|they|it) %s (?:block|stop|prevent) %s from (?:stopping|finishing)'
     % (CC, CANT, CC), 'doc', 'hooks-stop',
     'a Stop hook can keep Claude from stopping: exit code 2 prevents it and continues the conversation'),
    ('stop-hook', NO_CHECK, 'repo', 'check', 'the project has a check command now'),
    ('allowlist', NO_CHECK, 'repo', 'check', 'the project has a check command now'),
)
STALE_FORMS = [(feature, re.compile(pattern), kind, key, claim) for feature, pattern, kind, key, claim in STALE_REASONS]
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
# decline, and a history page tells history as its contract ("`X` has been removed; use `Y`"). A docs page (never an
# instruction file, import, skill, subagent or command) is a history page by its file name (a changelog, release
# notes or a guide name such as migration-guide, upgrading, whats-new, deprecations, breaking-changes) or by its
# first heading naming such a guide ("Migration guide: v1 to v2", "Upgrading to v2", "What's new in v2"). A topic
# word alone ("Writing database migrations", "Release procedure", "Acme upgrade service") makes no history page.
DECISION_RECORD = re.compile(r'decision|(?:^|/)adrs?(?:/|[-_.])', re.I)
HISTORY_FILE = re.compile(r'(?:^|/)(?:change-?log|changes|history|news|release[-_ ]?notes|migration[-_]guide|'
                          r'migrating[-_]to\b[^/]*|upgrading(?:[-_][^/]*)?|whats?[-_]new|deprecations|'
                          r'breaking[-_]changes)(?:\.[\w]+)?$', re.I)
HISTORY_TITLE = re.compile(r'^(?:.*\b(?:migration|upgrade|upgrading)\s+guide\b|(?:migrating|upgrading)\s+(?:from|to)\b|'
                           r'what[\'’]?s\s+new\b|change\s*-?log\b|release\s+notes\b|deprecations\b|'
                           r'breaking\s+changes\b)', re.I)


def first_heading(text):
    """The text of a Markdown file's first heading (outside code fences), or ''."""
    for _, line in prose(text):
        match = re.match(r'\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$', line)
        if match:
            return match.group(1)
    return ''


def history_form(sentence):
    """(name, offset, matched text) of the first history form a sentence holds as its own statement, or None."""
    for name, form in HISTORY_FORMS:
        for match in form.finditer(sentence):
            before = sentence[:match.start('verb')]
            if SPECULATIVE.search(match.group()) or RELATIVE.search(before) or CONDITION.search(before):
                continue
            return name, match.start(), match.group()
    return None


# A history sentence's clauses: at "; " and at "and" before a present-tense verb ("was retired on 2026-11-05 and is
# kept for reference only"). The clause holding the history is moved out; the others are what holds now.
CLAUSE = re.compile(r';\s+|,?\s+and\s+(?=(?:is|are|stays?|remains?)\b)', re.I)
DATE_PHRASE = re.compile(r'(?<![\w`-])(?:on|in|since|until|as of|by|before|after|from|during)\s+(?:the\s+)?%s\b' % DATE,
                         re.I)


PRESENT = {'was': 'is', 'were': 'are', 'has been': 'is', 'have been': 'are', 'had been': 'is'}


def history_finding(entry):
    """(problem, fix) for a history line. The fix keeps what holds now and moves only the dated narrative out;
    it never says to delete a sentence that still states a current fact."""
    quote = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', entry['quote'])  # a link reads as its text
    told = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', entry['told'])
    clauses = [c.strip().rstrip('.') for c in CLAUSE.split(quote) if c.strip()]
    past = next((c for c in clauses if told in c or told.split()[0] in c), clauses[0])
    now = [c for c in clauses if c is not past]
    date = DATE_PHRASE.search(quote)
    problem = '`%s:%d` tells history, not what holds now: "%s"' % (entry['path'], entry['line'], quote)
    if entry.get('not_a_decline'):
        problem += (' It reads like a decision against %s, but no decision record says so, so Claudit does not '
                    'treat it as one.' % entry['not_a_decline'].lower())
    where = 'a changelog or a decision record'
    detail = 'the date (`%s`)' % date.group() if date else 'when and why it happened'
    kept = joined('"%s"' % c for c in now)
    if entry['why'] == 'retirement':
        subject = past[:past.find(told)].rstrip() if told in past else ''
        verb, state = told.rsplit(None, 1)
        present = '"%s %s %s"' % (subject, PRESENT.get(verb.lower(), 'is'), state) if subject else 'that it is retired'
        fix = 'Keep what holds now, in the present tense: %s%s. Move %s to %s.' % (
            present, ', and %s' % kept if now else '', detail, where)
    elif now:
        fix = 'Keep what holds now (%s); move "%s" to %s.' % (kept, past, where)
    elif date:
        fix = 'Keep the current fact and cut %s, or move the sentence to %s.' % (detail, where)
    else:
        fix = 'Move the sentence to %s: it says what happened, not what holds now.' % where
    return problem, fix


def frontmatter_line(text):
    """The line of a Markdown file's `description:` frontmatter key, or 1."""
    for number, line in enumerate(text.splitlines()[:60], 1):
        if re.match(r'description\s*:', line):
            return number
    return 1


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


def secret_like(rel):
    """True for paths whose contents must never be read or printed."""
    parts = rel.rstrip('/').split('/')
    name = parts[-1]
    if 'secrets' in parts[:-1] or name in SECRET_EXAMPLES:
        return 'secrets' in parts[:-1]
    return (name == '.env' or name.startswith('.env.') or name.endswith(('.pem', '.key'))
            or name.startswith('id_rsa') or fnmatch.fnmatch(name, 'credentials*.json'))


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
            # A run inside a purpose ("To run the slow suite, use ... and run `y`") or limited by "only" is a situational
            # call, not the routine check (#207 dev set). It is read over the whole sentence, not since the last span.
            whole = re.split(r'[.!?;]\s', (wrapped.strip() + ' ' if start == 0 and wrapped.strip() else '')
                             + line[:span.start()])[-1]
            situational = run and (re.match(r'\s*(?:[-*+]\s+)?to\s+\w+\b', whole, re.I)
                                   or re.search(r'\bonly\b', whole, re.I))
            instructed = run and not DESCRIBING.search(sentence) and not situational and (
                IMPERATIVE.search(before[:run.start()]) or (
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
# A command named only where it exists ("`bin/container bin/ci` where supported") is not a stale fact.
CONDITIONAL = re.compile(r'\b(?:where|when|if)\s+(?:supported|available|present|installed|provided|it exists|exists|any)\b',
                         re.I)
# A line that places what it names in another repository or package, by naming it ("part of the `vercel/next.js`
# repository", "the acme/tools repo") or calling it another one ("inside that installed package", "In the Turborepo
# source repository", "an upstream project"): its paths aren't this repository's. "From the root of the repository" and
# "in the main package" are about this one.
ELSEWHERE = re.compile(r'(?:`[^`\n]+`|\b[\w.-]+/[\w.-]+)\s+(?:repository|repo|package|project)\b|'
                       r'\b(?:another|other|upstream|installed|source|external|third[- ]party|vendored)\s+'
                       r'(?:\S+\s+){0,2}?(?:repository|repo|package|project)\b', re.I)
# Example names stand for any path or argument: `src/foo/bar.py`, `test/path/to/test.ts`, `tests/...`, `spec::test_name`.
# Only a whole path segment (or `::` part) is one, so `src/nav-bar.md` and `status_bar.py` are real names.
PLACEHOLDER = re.compile(r'(?:^|[/\s]|::)(?:foo|bar|baz|qux|xxx|test_name|your[_-]\w+|my[_-]\w+)(?:\.\w+)?(?=$|[/\s]|::)|'
                         r'(?:^|[/\s])path/to(?=/|$)|\.\.\.', re.I)
MANIFEST_FILES = ('package.json', 'pyproject.toml', 'setup.py', 'Cargo.toml', 'go.mod')
# On such a line an `owner/name` whose owner is no folder here is a repository name (`vercel/next.js`), not a path.
REPO_WORDS = re.compile(r'\b(?:github|gitlab|fork|forks|repository|repo|pull requests?|PRs?|merge target)\b', re.I)
SCRIPT_EXTENSIONS = ('', '.sh', '.bash', '.py', '.js', '.mjs', '.cjs', '.ts', '.rb', '.pl')
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


def normalized(sentence):
    return re.sub(r'\s+', ' ', re.sub(r'[`*_>"“”]', '', sentence)).strip().rstrip('.!:;').lower()


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

    def __init__(self, root, git, claude_version, data_dir=None):
        self.root, self.git, self.data_dir = root, git, data_dir
        self.claude_version = claude_version
        self.findings, self.limits, self.truncated, self.exact, self.history = [], [], {}, {}, []
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
    @staticmethod
    def source(key):
        """The doc URL and heading for a DOCS key, so reports cite them verbatim."""
        url, heading = DOCS[key]
        return {'url': url, 'heading': heading}

    def add(self, fid, path, line, problem, fix, doc=None):
        """Record one finding: the file and real line it is about, what's wrong and the exact fix."""
        if any(f['id'] == fid for f in self.findings):
            return
        finding = {'id': fid, 'kind': fid.split(':')[0], 'path': path, 'line': line or 1, 'problem': problem[:600],
                   'fix': fix}
        if doc:
            finding['source'] = self.source(doc)
        self.findings.append(finding)

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
        out = []
        for rel in PROJECT_SETTINGS:
            state, data, raw = self.load_json(rel)
            if state == 'missing':
                continue
            out.append({'path': rel, 'scope': 'project', 'state': state, 'root': data if state == 'ok' else None,
                        'data': data if state == 'ok' and isinstance(data, dict) else {}, 'raw': raw or ''})
        return out

    def check_commands(self, corpus, ci_text, loaded=()):
        """Check commands; sets self.exact to the exact, non-mutating calls of each to pre-approve."""
        self.calls_documented = False
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
            # Which runner the project uses is read from the instructions' code spans, then CI; only calls become
            # rules (below). The runner starts the command (not `coverage run -m pytest`); a wrapper it runs through
            # (`uv run --frozen pytest`) is part of it, and of several documented forms the shortest is the everyday one.
            mentioned = None
            for snippets in ([s for text in corpus.values() for s in code_spans(text)], ci_text.splitlines()):
                for snippet in snippets:
                    match = re.search(r'(?:^|\brun:\s*|&&\s*)((?:(?:uv|poetry|pdm|pipenv|hatch) run'
                                      r'(?: --?[\w-]+(?:[ =][\w.]+)??)* )?'
                                      r'(?:python3?(?:\.\d+)? -m (?:pytest|unittest)|pytest))\b', snippet.strip())
                    if match and (mentioned is None or len(match.group(1)) < len(mentioned)):
                        mentioned = match.group(1)
                if mentioned:
                    break
            pyproject = self.text('pyproject.toml') or ''
            configured = '[tool.pytest' in pyproject or 'pytest.ini' in self.fileset or 'conftest.py' in self.fileset \
                or '[tool:pytest]' in (self.text('setup.cfg') or '')
            if mentioned or configured:  # never a guessed runner (#207 dev set)
                add(mentioned or 'pytest', python_markers[0])
        # Commands documented in instruction files.
        for path, text in corpus.items():
            for snippet in code_snippets(text):
                for written in split_commands(snippet):
                    # `./x` and `x` are one command, but a rule keeps the written form. A leading `VAR=1` still documents
                    # the command it runs; no exact rule fits that call, so none is suggested for it.
                    part = re.sub(r'^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+', '', strip_dot(written))
                    if part != strip_dot(written):
                        part = strip_dot(part)
                        if part.split() and (RUNNER.match(part) or part.split()[0] in ('cargo', 'go', 'npm', 'pnpm',
                                                                                     'yarn', 'bun', 'make', 'just')):
                            self.calls_documented = True
                        continue
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
                    invocations.setdefault(base, []).append(written)
        # Commands a list item leads with, described rather than called ("- `x` runs the tests"). A command named
        # mid-sentence ("only run `x` where file events arrive") is not named here (#207 dev set).
        named = {}
        for text in corpus.values():
            for _, line in prose(text):
                lead = re.match(r'\s*(?:[-*+]|[0-9]+[.)])\s+`([^`\n]+)`', line)
                for written in split_commands(lead.group(1)) if lead else []:
                    base = next((c['command'] for c in detected if strip_dot(written) == strip_dot(c['command'])
                                 or strip_dot(written).startswith(strip_dot(c['command']) + ' ')), None)
                    if base:
                        named.setdefault(base, []).append(written)
        # Only exact calls are pre-approved, as written: a rule matches the exact command text, and a wildcard such as
        # `make test *` also allows `make test deploy`. A command the instructions document as a call gets rules for
        # those calls only; one they only name gets the form they name it in; one they don't mention (it's found from
        # package.json, a Makefile, bin/ or CI) gets its own form.
        def safe(calls):
            out = []
            for p in calls:
                # Go's `./...` is a package pattern, not a placeholder.
                bare = p.replace('...', '') if p.startswith('go ') else p
                if PLAIN_CALL.fullmatch(p) and not re.search(r'\b[A-Z][A-Z_]+\b', p) and not mutating(p) \
                        and not PLACEHOLDER.search(bare) \
                        and not re.search(r'(?:^|\s)(?:--help|-h|--version)(?:\s|$)', p) \
                        and p not in out:
                    out.append(p)
            return out

        self.exact = {}
        self.calls_documented = self.calls_documented or bool(invocations)  # check calls documented, usable or not
        for entry in list(detected):
            command = entry['command']
            seen = invocations.get(command, [])
            entry['args'] = any(strip_dot(p) != strip_dot(command) for p in seen)
            called = safe([p for p in seen if command not in from_mention or checking(p)])
            entry['documented'] = bool(called)
            entry['named'] = bool(named.get(command))
            exact = called or ([] if command in from_mention else safe(named.get(command, [])) or safe([command]))
            if not exact:
                detected.remove(entry)
                continue
            self.exact[command] = exact
        return detected

    def mentioned(self, command, corpus_text):
        pattern = r'(?<![\w/.-])(?:\./)?' + re.escape(strip_dot(command)) + r'(?![\w-])'
        return re.search(pattern, corpus_text) is not None

    def history_line(self, path, line, sentence, form, label=None):
        """Record a history line once per line; `form` is history_form's (name, offset, text) and `label` names the
        feature the sentence reads like a decision against."""
        entry = next((c for c in self.history if c['path'] == path and c['line'] == line), None)
        if entry is None:
            entry = {'path': path, 'line': line, 'quote': sentence[:400], 'why': form[0], 'told': form[2]}
            self.history.append(entry)
        if label:  # it reads like a decision, but only a decision record makes one
            entry['not_a_decline'] = label

    def stale_history(self, paths, docs):
        """History narrative (dated runs, "have been retired", past versions) in the given instruction files, skills,
        subagents and docs. Decision records, and the history pages among `docs` (docs pages only), tell history on
        purpose and are skipped."""
        for path in paths:
            text = self.text(path) or ''
            history_page = path in docs and (HISTORY_FILE.search(path) or HISTORY_TITLE.match(first_heading(text)))
            if DECISION_RECORD.search(path) or history_page or self.data(path) or os.path.isabs(path) \
                    or path.startswith('..'):
                continue
            for sentence, line_at in sentences(text):
                form = history_form(sentence)
                if form and not UNSURE.search(sentence):
                    self.history_line(path, line_at(form[1]), sentence, form)

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
                        self.history_line(path, line_at(form[1]), sentence, form, label)
                    elif match:
                        parts = decline_reason(body, match)
                        found[feature] = {'feature': feature, 'label': label, 'path': path,
                                          'line': line_at(noun.search(sentence).start()), 'quote': sentence[:400],
                                          'reason': ' \u2026 '.join(text for _, text in parts)[:400] or NO_REASON,
                                          'reason_line': line_at(parts[0][0]) if parts else None,
                                          'stale': stale_reason(feature, parts)}
                        if form:  # history narrative outside a decision record: a stale candidate, never a decline
                            found[feature]['history'] = True
                            self.history_line(path, line_at(form[1]), sentence, form, label)
        return [found[feature] for feature, _, _ in DECLINABLE if feature in found]

    def reconsider(self, stale, documented, checks, corpus):
        """Evidence that a decision's stated reason no longer holds, or None: the docs page showing the limitation is
        gone, or the file and line showing the situation the decision assumed has changed."""
        if not stale:
            return None
        _, _, kind, key, claim = stale
        if kind == 'doc':
            return {'claim': claim, 'evidence': self.source(key)}
        at = None
        for command in documented:
            at = next(((path, number) for path, text in corpus.items() for number, line in prose(text)
                       if self.mentioned(command, line)), None)
            if at:
                break
        if not at and checks and checks[0]['source'] in self.fileset:
            at = (checks[0]['source'], 1)
        return {'claim': claim, 'evidence': {'path': at[0], 'line': at[1]}} if at else None

    def check_instructions(self, instructions):
        for item in instructions:
            path = item['path']
            if item['kind'] == 'project' and not item['loaded']:
                self.add('agents-md-not-loaded:' + path, path, 1, '`%s` does not load: %s.' % (path, item['why']),
                         'Add "@%s" to %s so both load, or move what Claude needs into it.' % (
                             os.path.relpath(item['abs'], os.path.dirname(item['blocked_by'][0][1])),
                             item['blocked_by'][0][0])
                         if item['blocked_by'] and not os.path.isabs(item['blocked_by'][0][0]) else
                         'Create CLAUDE.md in the project containing "@%s"; %s above the project otherwise keeps it '
                         'from loading.' % (path, item['blocked_by'][0][0])
                         if item['blocked_by'] else 'Upgrade Claude Code to %s or later, or create a CLAUDE.md containing '
                         '"@%s".' % ('.'.join(map(str, AGENTS_MD_READ)), path), 'memory-agents-md')
            if item['kind'] == 'project' and item['loaded'] and item['lines'] > 200:
                self.add('oversized:' + path, path, 1, '`%s` is %d lines (%s words, about %s tokens), past the '
                         'documented target of under 200 lines, and it loads in every session.' % (
                             path, item['lines'], format(words(item['text']), ','), format(tokens(item['text']), ',')),
                         "Cut %s to what Claude can't learn from the repository, and move path-specific rules to "
                         '.claude/rules/.' % path, 'memory-size')
            for imp in item['imports']:
                target = imp['target']
                scope_like = re.fullmatch(r'[\w.-]+/[\w.-]+', target) and not re.search(r'\.[A-Za-z]\w*$', target)
                if not imp['exists'] and not scope_like:
                    self.add('broken-import:%s:%s' % (path, target), path, imp['line'],
                             '`@%s` does not resolve from `%s`, so nothing is imported.' % (target, path),
                             'Point the import at an existing file or remove it.', 'memory-imports')
            if path.startswith(('/', '~')):
                continue
            base = os.path.dirname(item['abs'])
            candidates = []
            for number, line in prose(item['text']):
                for token in self.checked_paths(line):
                    if self.present(token, base):
                        continue
                    rel = os.path.relpath(os.path.normpath(os.path.join(self.root, token)), self.root)
                    if not rel.startswith('..'):
                        candidates.append((number, token, rel.replace(os.sep, '/')))
            ignored = self.ignored(sorted({c[2] for c in candidates}))
            for number, token, rel in candidates:
                if rel not in ignored:
                    self.stale_path(path, number, token)

    def checked_paths(self, line):
        """The path tokens of a line worth checking: not on a conditional line or one placing them in another
        repository or package, and neither a placeholder nor a module of a declared dependency (`react-dom/x`)."""
        if CONDITIONAL.search(line) or ELSEWHERE.search(line):
            return []
        slugs = REPO_WORDS.search(line)
        return [t for t in path_tokens(line) if not PLACEHOLDER.search(t) and t.split('/')[0] not in self.dependencies()
                and not (slugs and t.count('/') == 1 and t.split('/')[0] not in self.known_paths())]

    def present(self, token, base):
        """True when a named path exists from the root, the naming file's folder or a package root (a folder with a
        package.json, pyproject.toml, setup.py, Cargo.toml or go.mod, its `src/`, or a top-level Python package):
        `src/cli/next-dev.ts` in packages/next/, `lib/foundry.py` in src/anthropic/. A folder also counts when any
        tracked folder ends with it (`generics/legacy/` deep in a crate's test data); a file never does that way, so an
        unrelated `packages/old/config/settings.toml` doesn't hide a missing `config/settings.toml`."""
        if os.path.exists(os.path.join(self.root, token)) or os.path.exists(os.path.join(base, token)):
            return True
        bare = re.sub(r'^(?:\./)+', '', token).rstrip('/')
        known = self.known_paths()
        if any((r + '/' + bare if r else bare) in known for r in self.package_roots()):
            return True
        is_dir = token.endswith('/') or not re.search(r'\.[A-Za-z][A-Za-z0-9]{0,9}$', bare.split('/')[-1])
        return is_dir and any(p.endswith('/' + bare) and p in self.known_dirs() for p in known)

    def package_roots(self):
        """Folders a project's own paths are written from: each manifest's folder and its `src/`, and each top-level
        Python package (a folder with `__init__.py` whose parent has none)."""
        if getattr(self, '_roots', None) is None:
            known = self.known_paths()
            roots = set()
            for p in known:
                head, _, name = p.rpartition('/')
                if name in MANIFEST_FILES:
                    roots.update({head, (head + '/src') if head else 'src'})
                elif name == '__init__.py' and head and (head.rpartition('/')[0] + '/__init__.py').lstrip('/') not in known:
                    roots.add(head)
            self._roots = sorted(roots)
        return self._roots

    def known_dirs(self):
        if getattr(self, '_known_dirs', None) is None:
            known = self.known_paths()
            self._known_dirs = {p.rpartition('/')[0] for p in known if '/' in p} | self.dirs
        return self._known_dirs

    def known_paths(self):
        """Every tracked or untracked-but-not-ignored file and folder (git ls-files, complete however large the repo),
        or the walked ones outside git."""
        if getattr(self, '_known', None) is None:
            files = None
            if self.git:
                proc = run(['git', '-C', self.root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                           timeout=60)
                if proc is not None and proc.returncode == 0:
                    files = [f for f in proc.stdout.split('\0') if f]
            files = files if files is not None else self.files
            known = set(files)
            for f in files:
                parts = f.split('/')
                known.update('/'.join(parts[:n]) for n in range(1, len(parts)))
            self._known = known | self.dirs
        return self._known

    def dependencies(self):
        """Package names declared in the repository's package.json files (two levels deep)."""
        if getattr(self, '_dependencies', None) is None:
            names = set()
            for rel in [f for f in self.files if f.split('/')[-1] == 'package.json' and f.count('/') <= 2
                        and not self.data(f)]:
                state, data, _ = self.load_json(rel)
                for key in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
                    if state == 'ok' and isinstance(data, dict) and isinstance(data.get(key), dict):
                        names.update(name.split('/')[0] if not name.startswith('@') else name for name in data[key])
            self._dependencies = names
        return self._dependencies

    def stale_path(self, path, number, token):
        self.add('stale-ref:%s:%s' % (path, token), path, number, '`%s` does not exist; `%s:%d` names it.'
                 % (token, path, number), 'Point at an existing file, remove the reference, or create %s.' % token,
                 'memory-size')

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
            if item['loaded'] and item['kind'] in ('project', 'import'):
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
                self.add('long-description:' + skill['path'], skill['path'], frontmatter_line(skill['text']),
                         'The description of `%s` is %d characters, so the skill listing cuts it at %d.'
                         % (skill['path'], len(listing), LISTING_CAP),
                         'Put the key use case first and cut the description and when_to_use of %s to under %d '
                         'characters.' % (skill['path'], LISTING_CAP), 'skill-frontmatter')
        agent_tokens, first_agent = 0, agents[0] if agents else None
        for agent in agents:
            text = agent['fm'].get('description') if isinstance(agent['fm'].get('description'), str) else ''
            agent_tokens += tokens(text)
            rows.append({'path': agent['path'], 'what': '`%s` subagent description' % agent['name'],
                         'loads': 'every session (subagent list)', 'words': words(text), 'tokens': tokens(text)})
        if agent_tokens > AGENT_WARNING:
            self.add('agent-descriptions', first_agent['path'], frontmatter_line(first_agent['text']),
                     'The subagent descriptions in `.claude/agents/` come to about %s tokens; Claude Code warns at '
                     'startup past %s.' % (format(agent_tokens, ','), format(AGENT_WARNING, ',')),
                     "Trim each subagent's description and move detail into its system prompt, which loads only "
                     'when it runs.', 'subagents')
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
            self.add('visible-skill:' + skill['path'], skill['path'], frontmatter_line(skill['text']),
                     '`%s` is read only by the `%s` subagent (%s), but Claude can invoke it, so its description '
                     'loads in every session.' % (skill['name'], agent['name'], agent['path']), fix,
                     'skill-invocation')

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
        """(path, line, sentence, normalized) for each long sentence of the files duplication is judged on."""
        paths = [i['path'] for i in instructions if i['kind'] in ('project', 'import', 'nested')] + \
            [x['path'] for x in skills + agents] + \
            [f for f in self.files if f.endswith('.md') and (f.startswith('docs/') or '/' not in f) and not self.data(f)] + \
            [f for f in self.files if f.count('/') == 1 and f.split('/')[0] in ('bin', 'scripts', 'script')
             and os.path.splitext(f)[1] in SCRIPT_EXTENSIONS]  # a script's strings, never a lock or data file
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
                        sources.extend((path, number, sentence, normalized(sentence))
                                       for sentence, _ in sentences(literal) if words(sentence) >= DUP_MIN_WORDS)
                continue
            offset = 0
            if text.startswith('---') and '\n---' in text[3:]:
                end = text.find('\n---', 3) + 4
                offset, text = text[:end].count('\n'), text[end:]
            for sentence, line_at in sentences(text):
                if words(sentence) >= DUP_MIN_WORDS:
                    sources.append((path, line_at(0) + offset, sentence, normalized(sentence)))
        return sources

    def check_duplicates(self, instructions, skills, agents, generated):
        """Rules copied word for word across instruction files, skills, subagents, docs and script strings, each copy
        with its real line. A finding needs copies in at least three files: two uses don't earn an abstraction."""
        groups = {}
        for path, line, sentence, norm in self.duplicate_sources(instructions, skills, agents):
            groups.setdefault(norm, []).append((path, line, sentence))
        out = []
        for places in groups.values():
            files = []
            for path, line, _ in places:
                if path not in [p for p, _ in files]:
                    files.append((path, line))
            if len(files) < 2:
                continue
            made = [p for p, _ in files if p in generated]
            if made and all(p in made or any(m in (self.text(p) or '') for m in made) for p, _ in files):
                continue  # generated output and the script that names it as an output: one source, not a copy
            if all(re.match(r'\.claude/(?:agents|skills|commands)/', p) for p, _ in files):
                continue  # text shared by prompts that each load in their own context is a template, not drift
            out.append({'text': places[0][2][:300], 'copies': files})
        out.sort(key=lambda d: (-len(d['copies']), d['copies']))
        counted = [d for d in out if len(d['copies']) >= 3]
        if counted:
            first = counted[0]
            owner = next((c for c in first['copies'] if re.search(r'decision|adr', c[0], re.I)), first['copies'][0])
            problem = 'One rule is copied word for word into %d files, %s: "%s"' % (
                len(first['copies']), joined('`%s:%d`' % c for c in first['copies']), first['text'])
            if len(counted) > 1:
                problem += ' %d more rules are copied into three or more files.' % (len(counted) - 1)
            self.add('duplicate', owner[0], owner[1], problem,
                     'Keep the rule in %s:%d and replace each other copy with a pointer to it, or drop the copy '
                     'where %s already loads.' % (owner[0], owner[1], owner[0]), 'memory-size')
        return [{'text': d['text'], 'copies': ['%s:%d' % c for c in d['copies']]} for d in out[:CAP]]

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
            if HISTORY.search(line) or CONDITIONAL.search(line) or ELSEWHERE.search(line):
                continue
            for span in re.findall(r'`([^`\n]+)`', line):
                if PLACEHOLDER.search(span):
                    continue
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
                        self.add('stale-command:%s:%s' % (path, command), path, number,
                                 '`%s` does not exist (%s); `%s:%d` names it.' % (command, missing, path, number),
                                 'Point at the command that exists, or remove the reference.', 'memory-size')
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
                self.add('stale-dep:%s:%s' % (path, name), path, line_at(0),
                         '`%s` is not a declared dependency in `%s`%s; `%s:%d` names it.' % (
                             name, manifest, '; `%s` declares no dependencies' % manifest if empty else '',
                             path, line_at(0)),
                         'Remove or correct the dependency claim, or declare %s in %s.' % (name, manifest),
                         'memory-size')

    def missing_names(self, path, text, known):
        """Skill and subagent names a file names, as "the `x` skill", that no project file defines."""
        for number, line in prose(text):
            if HISTORY.search(line):
                continue
            for match in NAMED.finditer(line):
                name = (match.group(1) or match.group(2) or '').lower()
                if name and name not in known and name not in BUILT_IN_NAMES:
                    self.add('missing-name:%s:%s' % (path, name), path, number,
                             'No skill, command or subagent named `%s` exists; `%s:%d` names it.' % (name, path, number),
                             'Create it, point at the one that exists, or remove the reference.', 'skill-locations')

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
        self.add('gate-ask', unguarded[0]['path'], unguarded[0]['line'],
                 ' '.join('`%s:%d` says a person must approve %s, but no ask or deny rule covers `%s`, so '
                          'Claude can run it without asking.' % (g['path'], g['line'], g['verb'], g['command'])
                          for g in unguarded),
                 'Add to .claude/settings.json: %s. %s: an ask rule only prompts inside Claude Code, and a client-side '
                 'rule can be got around by running the command another way.'
                 % (json.dumps({'permissions': {'ask': ask}}), real_gate), 'bash-rule-limits')
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

    def scope(self, instructions):
        """Files above the git root (one line, not checked), whether they change how the repo's files load, and
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
            lines.append('Outside the repo, not checked: %s above the repo%s.' % (
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
                for token in self.checked_paths(line):
                    if not (self.present(token, base) or self.ignored([token])):
                        self.stale_path(rel, number, token)
            self.stale_facts(rel, text, base)
            if not plugins_on:
                self.missing_names(rel, text, known)
        # Settings that don't parse are /doctor's to report; the checks that read them are skipped, so a broken file
        # never reads as "no rule covers this".
        blind = ['`%s` (%s)' % (s['path'], s['state'] if s['state'] != 'ok' else 'not an object')
                 for s in settings if not isinstance(s['root'], dict)]
        if blind:
            self.limits.append('Not checked: %s could not be read, so the allowlist, ask-rule and Stop-hook checks were '
                               'skipped.' % joined(blind))
        gates = self.check_gates(team, settings) if not blind else []
        generated = self.generated()
        duplicates = self.check_duplicates(instructions, skill_docs, agent_docs, generated)
        context = self.context(instructions, skill_docs, agent_docs)
        own = [i['path'] for i in instructions if i['kind'] in ('project', 'nested', 'import')] + \
            [x['path'] for x in skill_docs + agent_docs] + commands
        docs = [r['path'] for r in context['likely_read'] if r['path'] not in own]
        self.stale_history(dict.fromkeys(own + docs), set(docs))  # the history-page skip is for docs pages only
        self.check_visible_skills(skill_docs, agent_docs, team)
        scope = self.scope(instructions)
        project_instr = [i for i in instructions if i['kind'] in ('project', 'nested', 'import')]
        corpus = {i['path']: i['text'] for i in project_instr}
        ci = [f for f in self.files if (f.startswith('.github/workflows/') and f.count('/') == 2
                                        and f.endswith(('.yml', '.yaml'))) or f == '.gitlab-ci.yml']
        ci_text = '\n'.join(self.text(f) or '' for f in ci)
        loaded = [i for i in project_instr if i['loaded'] and i['kind'] != 'nested']
        checks = self.check_commands(corpus, ci_text, {i['path'] for i in loaded})
        documented = [c['command'] for c in checks if c['documented']]  # called in the instructions, not just named
        allow = [r for s in settings for r in rules_of(s['data'], 'allow')]
        hooks = {}
        for s in settings:
            for event, groups in (s['data'].get('hooks') or {}).items() if isinstance(s['data'].get('hooks'), dict) else []:
                hooks.setdefault(event, []).extend(groups if isinstance(groups, list) else [])

        # The commands the instructions call; else, when they document no call at all (not even one no exact rule
        # fits, such as `X=1 cargo test`), those they name; else every command found in the repository.
        targets = [c for c in checks if c['documented']] or ([] if self.calls_documented else (
            [c for c in checks if c['named']] or checks))
        uncovered = [c for c in targets if not all(any(bash_rule_matches(r, call) for r in allow)
                                                   for call in self.exact[c['command']])]
        if uncovered and not blind:
            calls = [call for c in uncovered for call in self.exact[c['command']]]
            path, line = self.command_at(uncovered[0], self.exact[uncovered[0]['command']], corpus)
            self.add('allowlist', path, line, 'No `permissions.allow` rule in `.claude/settings.json` covers %s, so '
                     'every run of %s asks first.' % (joined('`%s`' % call for call in calls),
                                                       'it' if len(calls) == 1 else 'them'),
                     'Add to .claude/settings.json: ' + json.dumps({'permissions': {'allow': [
                         'Bash(%s)' % call for call in calls]}}), 'permission-rules')
        must_rules = []
        for item in project_instr:
            for number, line in prose(item['text']):
                if COMPLETION.search(line) and not MUST_NOT.search(line) and (
                        any(self.mentioned(c['command'], line) for c in checks if c['documented'] or c['named'])
                        or (re.search(r'\brun\b', line, re.I) and any(checking(span) for span in re.findall(
                            r'`([^`\n]+)`', line)))):
                    must_rules.append({'path': item['path'], 'line': number, 'text': LIST_ITEM.sub('', line.strip())[:160]})
        if must_rules and not any(hooks.get(e) for e in STOP_EVENTS) and not blind:
            rule = must_rules[0]
            cmd = next((c['command'] for c in checks if self.mentioned(c['command'], rule['text'])),
                       (documented or [c['command'] for c in checks] or ['<your check command>'])[0])
            cmd = self.exact[cmd][0] if cmd in self.exact else cmd
            settings_json = json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command':
                                        '"$CLAUDE_PROJECT_DIR"/.claude/hooks/stop-check.sh'}]}]}})
            script = ('#!/usr/bin/env bash\n# Block finishing until the check passes.\ninput=$(cat)\n'
                      'case "$input" in *\'"stop_hook_active":true\'*|*\'"stop_hook_active": true\'*) exit 0 ;; esac\n'
                      'cd "$CLAUDE_PROJECT_DIR" || exit 0\nif ! out=$(%s 2>&1); then\n'
                      '  printf \'%%s\\n\' "%s failed:" "$out" | tail -n 60 >&2\n  exit 2\nfi\n' % (cmd, cmd))
            self.add('stop-hook', rule['path'], rule['line'], '`%s:%d` says "%s", but no Stop hook runs `%s`, so '
                     'nothing makes Claude run it before finishing.' % (rule['path'], rule['line'], rule['text'], cmd),
                     'Add to .claude/settings.json: %s and create .claude/hooks/stop-check.sh (chmod +x):\n%s'
                     % (settings_json, script), 'stop-hook')

        respected = self.weigh_declines(instructions, settings, checks, documented, corpus)
        for entry in sorted(self.history, key=lambda c: (c['path'], c['line'])):
            problem, fix = history_finding(entry)
            self.add('history:%s:%d' % (entry['path'], entry['line']), entry['path'], entry['line'], problem, fix,
                     'memory-size')

        # dismissed findings
        reasons, where = {}, {}
        mine = user_dismissed(self.data_dir, self.root, self.git)
        for label, rel, path in (('shared', DISMISSED, self.abs(DISMISSED) if DISMISSED in self.fileset else None),
                                 ('per user', USER_DISMISSED % repo_key(self.root, self.git), mine)):
            if not path or not os.path.isfile(path):
                continue
            state, data, _ = self.load_json(rel, path)
            entries = data.get('dismissed') if state == 'ok' and isinstance(data, dict) else None
            if not isinstance(entries, list):
                self.limits.append('`%s` is not valid; nothing dismissed from it.' % rel)
                continue
            for e in entries:
                if isinstance(e, dict) and isinstance(e.get('id'), str) and e['id'] not in reasons:
                    reasons[e['id']], where[e['id']] = e.get('reason', ''), rel
        dismissed = [dict(f, reason=reasons[f['id']], stored=where[f['id']]) for f in self.findings
                     if f['id'] in reasons]
        self.findings = sorted((f for f in self.findings if f['id'] not in reasons),
                               key=lambda f: (f['path'], f['line'], f['id']))

        if self.claude_version == 'unknown':
            self.limits.append('Claude Code version unknown; AGENTS.md loading assumes a current version.')
        if not self.git:
            self.limits.append('Not a git repository; .gitignore matched approximately.')
        footer = scope['lines'] + self.limits + [
            'Not checked: user and managed settings, settings validity, server-side branch protection.',
            'Run `/doctor prompt-audit` for contradictions and wording.',
            audited(self.root, self.git) + ('; %d dismissed (stored in %s)' % (len(dismissed), joined(
                '`%s`' % x for x in sorted({d['stored'] for d in dismissed}))) if dismissed else '')]
        count = len(self.findings)
        t = self.truncated
        out = {'claudit': VERSION, 'claude_version': self.claude_version, 'root': '.', 'git': self.git,
               'summary': 'Nothing found.' if not count else '%d finding%s.' % (count, '' if count == 1 else 's'),
               'findings': capped(self.findings, 'findings', t), 'respected': respected,
               'context': context, 'duplicates': duplicates, 'gates': gates, 'scope': scope, 'footer': footer, 'dismissed': dismissed,
               'inventory': {'instructions': capped([dict({'path': i['path'], 'lines': i['lines'], 'kind': i['kind'],
                                                           'loaded': i['loaded']},
                                                          **({'real': self.display(os.path.realpath(i['abs']))}
                                                             if os.path.islink(i['abs']) else {}))
                                                     for i in instructions], 'inventory.instructions', t),
                             'instruction_loading': self.loading(instructions),
                             'instruction_words_loaded': sum(words(i['text']) for i in instructions
                                                             if i['loaded'] and i['kind'] != 'nested'),
                             'settings': [{'path': s['path'], 'state': s['state']} for s in settings],
                             'check_commands': capped(checks, 'inventory.check_commands', t),
                             'must_rules': capped(must_rules, 'inventory.must_rules', t)}}
        if t:
            out['truncated'] = t
        return redact(out)

    def command_at(self, check, calls, corpus):
        """(path, line) of the first line holding one of a check command's suggested calls as written (code blocks
        included), or where the command is defined when the instructions don't name it."""
        for path, text in corpus.items():
            for number, line in enumerate(text.splitlines(), 1):
                # The whole call: nothing but its end, a closing backtick or a comment may follow it.
                if any(re.search(r'(?<![\w./-])%s(?=\s*(?:$|`|#|;|&|\||\)))' % re.escape(call), line) for call in calls):
                    return path, number
        source = check['source']
        name = check['command'].split()[-1]
        return source, (line_of(self.text(source), '"%s"' % name) if source == 'package.json' else None) or 1

    def weigh_declines(self, instructions, settings, checks, documented, corpus):
        """Hold back a stop-hook or allowlist finding the project decided against, as a respected decision; keep it,
        citing both, when a fact contradicts the decision's stated reason. A history line is never a decision."""
        respected = []
        bypass = next(((s, s['data']['permissions']['defaultMode']) for s in settings
                       if isinstance(s['data'].get('permissions'), dict)
                       and s['data']['permissions'].get('defaultMode') in ('bypassPermissions', 'auto')), None)
        version = version_tuple(self.claude_version)
        for entry in self.declines(instructions):
            mine = [f for f in self.findings if f['kind'] == entry['feature']]
            if entry.get('history') or not mine:
                continue
            evidence = self.reconsider(entry['stale'], documented, checks, corpus)
            if not evidence and entry['feature'] == 'allowlist' and bypass and not (
                    version and version < DEFAULT_MODE_IGNORED):
                s, mode = bypass
                evidence = {'claim': 'Claude Code ignores `defaultMode: "%s"` in project settings, so the check '
                                     'commands still ask' % mode,
                            'evidence': {'path': s['path'], 'line': line_of(s['raw'], '"defaultMode"') or 1},
                            'doc': 'ignored-values'}
            said = '"%s"' % entry['reason'] if entry['reason'] != NO_REASON else 'no reason given'
            decision = '`%s:%d` decided against %s (%s)' % (entry['path'], entry['line'], entry['label'].lower(), said)
            for f in mine:
                if evidence:
                    at = evidence['evidence']
                    shown = '`%s:%d`' % (at['path'], at['line']) if 'path' in at else '%s, %s' % (
                        at['heading'], at['url'])
                    f['problem'] += ' %s, but %s (%s).' % (decision, evidence['claim'], shown)
                    if evidence.get('doc') or 'url' in at:
                        f['source'] = self.source(evidence['doc']) if evidence.get('doc') else at
                    continue
                self.findings.remove(f)
                respected.append({'id': f['id'], 'path': f['path'], 'line': f['line'],
                                  'decision': '%s:%d' % (entry['path'], entry['line']), 'reason': entry['reason'],
                                  'text': 'Respected: `%s:%d` %s; %s.' % (
                                      f['path'], f['line'], 'has no Stop hook' if f['kind'] == 'stop-hook'
                                      else 'names a check command no allow rule covers', decision)})
        return respected


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


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def main(argv=None):
    parser = Parser(prog='claudit.py', description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command')
    scan = sub.add_parser('scan')
    scan.add_argument('--root', default='.')
    scan.add_argument('--claude-version')
    scan.add_argument('--data', default=os.environ.get('CLAUDE_PLUGIN_DATA') or None)
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
            result = Scan(root, git, claude_version(args.claude_version), args.data).run()
        elif args.command == 'dismiss':
            root, git = resolve_root(args.root)
            result = dismiss(root, args.id, args.reason, args.shared, args.data, git)
        else:
            raise UsageError('expected a subcommand: scan or dismiss')
    except UsageError as error:
        print(json.dumps({'error': redact(str(error))}))
        return 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
