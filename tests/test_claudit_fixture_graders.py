"""Script graders for the issue #192 fixtures (f14 to f19), their adversarial controls and mutation checks.

The patterns are built here from named parts and committed as grader files; rebuild them after a change with

    python3 tests/test_claudit_fixture_graders.py --write

Each grader runs as a JavaScript regex inside `claude plugin eval`; the controls run in Python and, when node is
installed, in node. Every grader has controls a correct report passes and controls it fails: a negated line, a
negation elsewhere on the same line, a rhetorical question, Claudit's own `Source:` citation line and an invented
note. `test_every_guard_is_load_bearing` drops each named part of a pattern in turn and needs a control to flip.
"""
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_claudit_eval_graders import js_verdicts, regex_grader, verdict  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'evals/claudit/cases'

# Shared parts. No lookbehind or inline flags, so Python's re and JavaScript agree.
BOL = r'(?:^|\n)'
Q = r'[\x27’]'  # straight or curly apostrophe
TOK = r'(?:[^\s]+[ \t]+)'
NEG = (r'(?:no|not|never|without|nor|none|nothing|don%(q)st|doesn%(q)st|didn%(q)st|wouldn%(q)st|haven%(q)st|isn%(q)st|aren%(q)st|won%(q)st|needn%(q)st'
       r'|shouldn%(q)st|cannot|can%(q)st|skip|avoid)' % {'q': Q})
# Words that may sit between a negation and what it governs: "no need for a", "don't add an", "isn't the".
FILLER = (r'(?:(?:need\w*|requir\w*|ha(?:ve|s)|us(?:e|ing)|rely(?:ing)?[ \t]+on|bother(?:ing)?[ \t]+with|add(?:ing)?'
          r'|enabl\w*|set(?:ting)?[ \t]+up|configur\w*|turn(?:ing)?[ \t]+on|worth|is|are|be|any|a|an|the|for|of|to'
          r'|also|really|actually|even|yet|this|that|such)[ \t]+)')
SOURCE = r'(?![ \t]*(?:[-*>][ \t]+)?(?:\*\*|_)?Sources?\b)'
QUESTION = r'(?![^\n]*(?:\bwhy[ \t]+not\b|\?(?=[ \t*_"\x60)]|\n|(?![\s\S]))))'
HYPOTHETICAL = r'(?![^\n]*\b(?:if|unless|whether)\b)'
CONJ = r'[ \t]+(?:and|but|while|whereas|yet)\b'
# To the clause end: . , ; : ! ? before a space, "and", "but", "while", "whereas", "yet", or a line break.
CLAUSE = r'(?:(?!%s)[^\n.,;:!?]|[.,;:!?](?=\S))*(?=[.,;:!?]|%s|\n|(?![\s\S]))' % (CONJ, CONJ)
CTOK = r'(?:[^\s;:!?]*[^\s.,;:!?][ \t]+)'  # a word inside one clause
WINDOW = r'(?:(?!\n#{1,3}[ \t])[\s\S]){0,900}?'  # up to 900 characters, not past a heading


def neg_before(word):
    return r'(?![^\n]*\b%s[ \t]+%s{0,4}[\x60*"(]*%s)' % (NEG, FILLER, word)


def neg_after(word):
    """"<word> isn't needed", "<word> is unnecessary", within five words."""
    return (r'(?![^\n]*%s[\x60*")]{0,2}[ \t]+%s{0,5}?(?:(?:(?:is|are|was|were)n%st|(?:is|are|was|were|be)[ \t]+not'
            r'|not)[ \t]+(?:really[ \t]+)?(?:needed|necessary|required|worth\w*|useful|helpful|enough|relevant'
            r'|applicable|the[ \t]+(?:real[ \t]+)?gate|a[ \t]+gate)|(?:is|are|be)[ \t]+(?:unnecessary|overkill'
            r'|redundant|pointless)))' % (word, TOK, Q))


def already(word):
    """An invented note that the fix is in place: "already an ask rule", "an ask rule ... already exists" (in the
    same clause, so "CI already runs on PRs" after a full stop doesn't count)."""
    return (r'(?![^\n]*(?:\balready[ \t]+%s{0,3}?[\x60*"(]*%s|%s(?:[^\n.;:!?]|[.;:!?](?=\S)){0,60}?\balready[ \t]+(?:exists?|in[ \t]+place'
            r'|there|present|configured|set[ \t]+up|enabled|covered|an?|the|asks?|gates?|protects?|handles?|runs?|checks?'
            r'|enforces?|blocks?)\b))'
            % (TOK, word, word))


def guards(word):
    return {'neg-before': neg_before(word), 'neg-after': neg_after(word), 'already': already(word)}


def line(parts, drop):
    """A line holding every lookahead in `parts` (name -> pattern) whose name isn't in `drop`."""
    return BOL + ''.join(pattern for name, pattern in parts.items() if name not in drop) + r'[^\n]*'


def either(*forms):
    return '(?:' + '|'.join(forms) + ')'


def has(pattern):
    return '(?=[^\\n]*%s)' % pattern


def json_rule(key, rule):
    """A JSON array under "<key>" holding the rule, as in a settings.json snippet."""
    return r'"%s"[ \t]*:[ \t]*\[[^\]]*?"%s' % (key, rule)


def free_of(claim, negated, drop=(), require=''):
    """A not_contains pattern: a line (not a Source: line) with a claim that no negation directly governs. A negated
    clause (a negation, up to two words, then a governed word, to the end of the clause) is skipped as a unit, so a
    negation elsewhere on the line doesn't exempt a later claim; "why not" is never a negation."""
    skip = r'%s[ \t]+%s{0,2}?%s%s' % (NEG, CTOK, negated, CLAUSE)
    scan = (r'(?:\bwhy[ \t]+not\b|\b%s|(?!\b%s)[^\n])*?' % (skip, skip)) if 'skip-negated' not in drop else r'[^\n]*?'
    return BOL + ('' if 'source' in drop else SOURCE) + require + scan + claim


# f14-enforcement (issue F10): the prose-only gates and the unenforced must-run rule.
ASK_VERB = (r'(?:\b(?:add|adding|put|move|use|using|set|create|include|list|register|require|requir\w*|should'
            r'|recommend\w*|Change)\b|[^\w-]gate\b)')  # "gate" the verb, not "human-gate"


def ask_rule(command, drop=frozenset()):
    rule = r'Bash\([ \t]*%s' % command
    parts = {'source': SOURCE, 'question': QUESTION, **guards(r'(?:\bask\b|permissions\.ask)'),
             'ask': has(r'(?:\bask\b|permissions\.ask)'), 'rule': has(rule), 'verb': has(ASK_VERB)}
    return either(json_rule('ask', rule), line(parts, drop))


BRANCH = (r'(?:branch[ \t-]+protection|protected[ \t]+branch(?:es)?|branch[ \t]+(?:protection[ \t]+)?rules?'
          r'|rulesets?|required[ \t]+(?:pull[ \t]+request[ \t]+)?reviews?)')
GATE = (r'(?:\bgate\w*|\benforc\w*|\breal\b|\bonly\b|\bactual\w*|\bserver[- ]side\b|\bbypass\w*|\bbackstop\w*'
        r'|\bguarantee\w*|\bstops?\b|\bblocks?\b|\bprevents?\b)')


def branch_protection(drop=frozenset()):
    return line({'source': SOURCE, 'question': QUESTION, **guards(BRANCH), 'branch': has(BRANCH), 'gate': has(GATE)},
                drop)


HOOK = r'\b(?:PreToolUse|PostToolUse|Stop|pre-commit|precommit|git[ \t]+hooks?|hooks?)\b'
HOOK_VERB = (r'\b(?:add|adding|create|creating|install|installing|wire|wiring|use|using|set[ \t]+up|setting[ \t]+up'
             r'|register|configure|enforce\w*|Change)\b')
REASON = r'\b(?:because|since|as|given|so[ \t]+that|which|instead)\b|[:;—–]'


def commit_hook(drop=frozenset()):
    """A hook that runs bin/check (a JSON hooks block or a line), or a line saying why there's no hook."""
    hook_line = line({'source': SOURCE, 'question': QUESTION, **guards(HOOK), 'hook': has(HOOK),
                      'check': has(r'bin/check'), 'verb': has(HOOK_VERB)}, drop)
    # A hooks block, then bin/check in the same change: the block itself or a script it names, before the next
    # heading or column-0 numbered item.
    json_hook = r'"(?:PreToolUse|Stop)"[ \t]*:[ \t]*\[(?:(?!\n#{1,3}[ \t]|\n[0-9]+[.)][ \t])[\s\S]){0,1500}?bin/check'
    reason = BOL + ('' if 'source' in drop else SOURCE) + ('' if 'question' in drop else QUESTION) + (
        r'(?=[^\n]*(?:bin/check|\bcommit))[^\n]*?\b(?:%s|instead[ \t]+of|rather[ \t]+than|leave)[ \t]+%s{0,4}?[\x60*"]*'
        r'(?:a[ \t]+|an[ \t]+)?%s[^\n]*?(?:%s)' % (NEG, TOK, HOOK, REASON) if 'reason-shape' not in drop
        else r'[^\n]*%s[^\n]*(?:%s)' % (HOOK, REASON))
    return either(json_hook, hook_line, reason)


# f15-context-economy (issue F11).
ROW = r'(?:\n[ \t]*\|[^\n]*)*?\n[ \t]*\|(?=[^\n]*%s)(?=[^\n]*\b[0-9])[^\n]*'


def always_loaded_table(drop=frozenset()):
    """A Markdown table whose header counts words or tokens and whose rows give CLAUDE.md and the import a number."""
    header = BOL + r'[ \t]*\|%s[^\n]*\|[ \t]*\n[ \t]*\|?[ \t]*:?-{3,}[^\n]*' % (
        '' if 'units' in drop else r'(?=[^\n]*\b(?:words?|tokens?)\b)')
    rows = ''.join('(?=%s)' % (ROW % name) for key, name in (('claude-row', r'CLAUDE\.md'),
                                                              ('import-row', r'architecture\.md')) if key not in drop)
    return header + rows


DMI = r'disable-model-invocation'
MOVE = r'\b(?:move|moving|inline|inlining|fold|folding|merge|merging|put|putting|copy|copying)\b'


def visible_skill(drop=frozenset()):
    """The subagent-only skill hidden from the model: disable-model-invocation on schema-rules, or its rules moved
    into the migrator subagent."""
    dmi_line = line({'source': SOURCE, 'question': QUESTION, **guards(DMI), 'skill': has(r'schema-rules'),
                     'flag': has(DMI), 'not-false': r'(?![^\n]*%s[\x60*"]{0,2}[ \t]*:[ \t]*[\x60*"]?false)' % DMI},
                    drop)
    frontmatter = (r'name:[ \t]*schema-rules(?:(?!\x60{3})[\s\S]){0,400}?%s:[ \t]*true|%s:[ \t]*true'
                   r'(?:(?!\x60{3})[\s\S]){0,400}?name:[ \t]*schema-rules' % (DMI, DMI))
    move_line = line({'source': SOURCE, 'question': QUESTION, 'neg-before': neg_before(MOVE),
                      'skill': has(r'schema-rules'), 'move': has(MOVE + r'[^\n]*\b(?:into|to|in)\b[^\n]*migrator')},
                     drop)
    return either(frontmatter, dmi_line, move_line)


DUP = (r'(?:\bduplicat\w*|\brepeat\w*|\bcop(?:y|ies|ied)\b|\bword[ -]for[ -]word\b|\bverbatim\b|\bidentical\b'
       r'|\brestat\w*|\bsame[ \t]+(?:rule|sentence|line|text|instruction)s?\b|\b[3-5][ \t]+(?:files|places|copies)\b'
       r'|\b(?:three|four|five)[ \t]+(?:files|places|copies|times)\b)')


def duplicates_grouped(drop=frozenset()):
    """One stretch of the report (up to 900 characters, no heading) names the duplication, the migrations rule and
    the three files that copy it word for word, and doesn't deny the duplication."""
    parts = {'dup': DUP, 'rule': r'\bmigrat', 'claude': r'CLAUDE\.md', 'contributing': r'contributing\.md',
             'migrator': r'migrator\.md'}
    out = BOL + ''.join('(?=%s%s)' % (WINDOW, pattern) for name, pattern in parts.items() if name not in drop)
    if 'neg' not in drop:
        out += r'(?!%s\b%s[ \t]+%s{0,4}%s)' % (WINDOW, NEG, FILLER, DUP)
    return out


# f16-stale-facts (issue F12).
MISSING = (r'(?:\bdo(?:es)?(?:n%(q)st|[ \t]+not)[ \t]+exist|\bno[ \t]+longer[ \t]+exists?|\bnon-?existent\b'
           r'|\bmissing\b|\babsent\b|\bstale\b|\boutdated\b|\bout[ \t]+of[ \t]+date\b|\bwrong\b|\bincorrect\b'
           r'|\bfalse\b|\bno[ \t]+such\b|\bnot[ \t]+(?:present|found|there)\b|\bnot[ \t]+in[ \t]+(?:the[ \t]+)?'
           r'(?:repo\w*|tree|project|pyproject)|\bis(?:n%(q)st|[ \t]+not)[ \t]+(?:present|there|found|in[ \t]+)'
           r'|\bnot[ \t]+(?:a[ \t]+)?(?:declared[ \t]+|listed[ \t]+|installed[ \t]+)?dependenc\w*'
           r'|\b(?:is|are)(?:n%(q)st|[ \t]+not)[ \t]+(?:declared|listed|installed)\b|\bnot[ \t]+(?:declared|listed'
           r'|installed)\b|\b(?:none|neither)\b[^\n]{0,30}\bexists?\b)' % {'q': Q})
STALE_WORD = r'(?:missing|absent|stale|outdated|wrong|incorrect|false|out[ \t]+of[ \t]+date|broken)\b'


def stale(key, drop=frozenset()):
    return line({'source': SOURCE, 'question': QUESTION, 'hypothetical': HYPOTHETICAL,
                 'neg-before': neg_before(STALE_WORD), 'key': has(key), 'missing': has(MISSING)}, drop)


ALIGNMENT_BELOW_A = r'\*\*Alignment: [B-F]\*\*'

# f17-scope (issue F13).
PARENT = (r'(?:\bparent\b|\babove\b|\benclosing\b|\bancestor\w*|\boutside[ \t]+(?:the[ \t]+|this[ \t]+)?'
          r'(?:repo\w*|project|checkout)|\bcontaining[ \t]+(?:folder|directory)|\.\./|\bhome[ \t]+(?:folder'
          r'|directory)|~/(?:CLAUDE|AGENTS)\.md|\bup[ \t]+the[ \t]+tree|\bhigher[ \t]+up\b)')


def parent_noted(drop=frozenset()):
    no_parent = (r'(?![^\n]*\b(?:no|none|nothing)[ \t]+(?:(?!(?:findings?|issues?|problems?|changes?|grades?'
                 r'|grading)\b)[^\s]+[ \t]+){0,3}%s)' % PARENT)
    return line({'source': SOURCE, 'question': QUESTION, 'neg-before': neg_before(PARENT), 'no-parent': no_parent,
                 'parent': has(PARENT), 'file': has(r'(?:CLAUDE|AGENTS)\.md')}, drop)


LINK = (r'(?:\bsymlink\w*|\bsymbolic[ \t]+link|\blinks?[ \t]+to\b|\bpoints?[ \t]+(?:at|to)\b|->|→'
        r'|\bresolves?[ \t]+to\b|\balias\w*)')


def symlink_real_path(drop=frozenset()):
    return line({'source': SOURCE, 'question': QUESTION, 'neg-before': neg_before(LINK),
                 'claude': has(r'CLAUDE\.md'), 'agents': has(r'AGENTS\.md'), 'link': has(LINK)}, drop)


AGENTS_MISSING = (r'(?:AGENTS\.md[\x60*"]{0,2}[ \t]+(?:is|was)[ \t]+(?:missing|absent|not[ \t]+present)'
                  r'|AGENTS\.md[\x60*"]{0,2}[ \t]+(?:does[ \t]+not|doesn%(q)st|did[ \t]+not|didn%(q)st)[ \t]+exist'
                  r'|\b(?:no|missing|without)[ \t]+(?:an?[ \t]+)?[\x60*"]{0,2}AGENTS\.md[\x60*"]{0,2}(?=[ \t]*(?:[.,;:)]'
                  r'|\n|(?![\s\S]))|[ \t]+(?:file|exists|is[ \t]+present|in)\b)|\b(?:create|add|write)\w*[ \t]+'
                  r'(?:an?[ \t]+|the[ \t]+)?(?:missing[ \t]+)?[\x60*"]{0,2}AGENTS\.md)' % {'q': Q})


def agents_md_missing(drop=frozenset()):
    return free_of(AGENTS_MISSING, r'(?:creat\w*|add\w*|writ\w*|missing|absent)', drop)


BLOCK = (r'(?:\bstops?\b|\bstopping\b|\bprevents?\b|\bblocks?\b|\bshadows?\b|\bsuppress\w*|\boverrid\w*|\bmasks?\b'
         r'|\b(?:isn%(q)st|aren%(q)st|won%(q)st[ \t]+be|wouldn%(q)st[ \t]+be|will[ \t]+not[ \t]+be|would[ \t]+not'
         r'[ \t]+be|is[ \t]+not|are[ \t]+not|not|never)[ \t]+(?:\S+[ \t]+)?(?:read|loaded|picked[ \t]+up|used)\b'
         r'|\bno[ \t]+longer[ \t]+(?:read|loaded)\b|\bignored\b|\bskipped\b|\binstead[ \t]+of\b)' % {'q': Q})


def parent_blocks_agents(drop=frozenset()):
    denied = (r'(?![^\n]*\b(?:does(?:n%s|[ \t]+not)|won%s|will[ \t]+not|never|can%s|cannot|wouldn%s|would[ \t]+not)'
              r'[ \t]+(?:\S+[ \t]+)?(?:stop|prevent|block|shadow|suppress|override|mask|affect))' % (Q, Q, Q, Q))
    return line({'source': SOURCE, 'question': QUESTION, 'denied': denied, 'parent': has(PARENT),
                 'claude': has(r'CLAUDE\.md'), 'agents': has(r'AGENTS\.md'), 'block': has(BLOCK)}, drop)


FIX = r'\b(?:fix|update|remove|delete|replace|correct|change|rewrite|drop)\w*\b'
SCOPE = (r'(?:out[ \t]+of[ \t]+scope|outside[ \t]+(?:the[ \t]+|this[ \t]+)?(?:repo\w*|project|checkout)|not[ \t]+graded'
         r'|(?:is|are)n%s[ \t]+graded|not[ \t]+part[ \t]+of|ungraded|not[ \t]+(?:audited|reviewed|scored)|excluded'
         r'|above[ \t]+(?:the[ \t]+|this[ \t]+)?(?:repo\w*|project|checkout))' % Q)


def parent_findings(drop=frozenset()):
    """A finding on the parent's files: bin/legacy-build named with a fix, or as missing outside a scope note."""
    stale_claim = (r'(?=[^\n]*legacy-build)%s%s' % ('' if 'scope' in drop else r'(?![^\n]*%s)' % SCOPE,
                                                    has(MISSING)) + r'[^\n]*')
    fix_claim = free_of(r'(?:%s[^\n]*legacy-build|legacy-build[^\n]*?%s)' % (FIX, FIX), FIX, drop)
    return either(fix_claim, BOL + ('' if 'source' in drop else SOURCE) + stale_claim)


# f18-check-commands (issue F14).
ALLOW = r'(?:\ballow\w*|\bpre-?approv\w*|\bpermissions?\b)'
ALLOW_VERB = r'\b(?:add|adding|put|create|include|use|using|set|Change|allowlist|pre-?approve|approve)\b'


def check_allowlist(drop=frozenset()):
    rule = r'Bash\([ \t]*bun[ \t]+run[ \t]+check\b'
    return either(json_rule('allow', rule), line({'source': SOURCE, 'question': QUESTION, **guards(ALLOW),
                                                  'allow': has(ALLOW), 'rule': has(rule), 'verb': has(ALLOW_VERB)},
                                                 drop))


# f19-declarative-list (issue F15).
CL = r'(?:[^\n.;:!?]|[.;:!?](?=\S))'  # a character inside one clause
SKILL_VERB = r'\b(?:add|create|make|turn|convert|move|wrap|extract|package|write|promote|split)\w*\b'
SKILL_CLAIM = (r'(?:' + SKILL_VERB + CL + r'{0,60}?principles' + CL + r'{0,60}?\bskills?\b|' + SKILL_VERB + CL
               + r'{0,40}?\bskills?\b' + CL + r'{0,40}?principles|\bskills?\b' + CL + r'{0,30}?\bfor\b' + CL
               + r'{0,40}?principles|'
               r'\bprocedur\w*|SKILL\.md|\bslash'
               r'[ \t]+commands?\b|\.claude/(?:skills|commands)/|\b(?:needs?|deserves?|warrants?|should[ \t]+'
               r'(?:be|become|have)|would[ \t]+(?:benefit[ \t]+from|be[ \t]+better[ \t]+as|work[ \t]+better[ \t]+as)'
               r'|belongs?[ \t]+in)[ \t]+(?:a[ \t]+|an[ \t]+|its[ \t]+own[ \t]+)?(?:(?!(?:no|not)\b)\S+[ \t]+)?'
               r'(?:skill|slash[ \t]+command|command)\b)')
SKILL_NEGATED = (r'(?:skills?|procedur\w*|SKILL\.md|commands?|add\w*|creat\w*|mak\w*|turn\w*|convert\w*|mov\w*'
                 r'|wrap\w*|extract\w*|packag\w*|writ\w*|promot\w*|split\w*|needs?|deserves?|warrants?)\b')


def principles_skill(drop=frozenset()):
    return free_of(SKILL_CLAIM, SKILL_NEGATED, drop, '' if 'principles' in drop else has('principles'))


DOC_SCRIPT = ('Script-graded{flags}. The parts, and the controls each must pass and fail, are in '
              '`tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py '
              '--write`. A line never counts when it is a `Source:` citation line{line_rules}.')
LINE_RULES = (', a question (it has "why not" or a `?` before a space or the line end), or when a negation directly '
              'governs the finding ("no ask rule is needed", "not a symlink"; a negation elsewhere on the line '
              'doesn\'t count) or it says the fix is already in place')

GRADERS = {
    'f14-enforcement': [
        ('finding-ask-merge', ask_rule, (r'gh[ \t]+pr[ \t]+merge',), 'i', '',
         'CLAUDE.md says never to merge to main without a human approving the pull request (`gh pr merge`), but '
         '`.claude/settings.json` has no `ask` or `deny` rule, so the gate is prose only.\n\nPASS when the report '
         'adds an ask rule for the command: a JSON `"ask": [...]` array holding `"Bash(gh pr merge`, or one line '
         'with "ask" (or `permissions.ask`), `Bash(gh pr merge` and a recommending word (add, put, move, use, set, '
         'create, include, list, register, gate, require, should, recommend, or Claudit\'s "Change"; not the '
         '"gate" in "human-gate"). A hypothetical such as "an ask rule would do it" is not a recommendation.'),
        ('finding-ask-deploy', ask_rule, (r'(?:\./)?bin/deploy',), 'i', '',
         'CLAUDE.md says never to deploy to production without a human go-ahead, and `bin/deploy` has no `ask` '
         'rule.\n\nPASS when the report adds an ask rule for `Bash(bin/deploy` (or `./bin/deploy`), in an `"ask"` '
         'array or on a recommending line, as for `finding-ask-merge`.'),
        ('finding-ask-release', ask_rule, (r'(?:\./)?bin/release',), 'i', '',
         'CLAUDE.md says a release needs a human go-ahead before `bin/release` runs, and nothing asks.\n\nPASS when '
         'the report adds an ask rule for `Bash(bin/release` (or `./bin/release`), in an `"ask"` array or on a '
         'recommending line, as for `finding-ask-merge`.'),
        ('finding-branch-protection', branch_protection, (), 'i', '',
         'An ask rule only prompts in Claude Code; the gate on main that holds for everyone is branch protection on '
         'the host.\n\nPASS when one line names branch protection (also "protected branch", "branch rules", '
         '"ruleset" or "required reviews") with a word for what it does as a gate (gate, enforce, real, only, '
         'actual, server-side, bypass, backstop, guarantee, stop, block, prevent).'),
        ('finding-commit-hook', commit_hook, (), 'i', '',
         'CLAUDE.md says "You must run `bin/check` before every commit", and no hook runs it.\n\nPASS when the '
         'report adds a hook that runs `bin/check` (a JSON `"PreToolUse"` or `"Stop"` block, then `bin/check` in it or '
         'in a script it names before the next heading or column-0 numbered item, or one line '
         'with a hook word, `bin/check` and add, create, install, wire, use, set up, register, configure, enforce, '
         'run or "Change"), or gives the reason for not adding one: a line about `bin/check` or commits where a '
         'negation (or "instead of", "rather than", "leave") governs the hook and a reason follows (because, '
         'since, as, given, so that, which, instead, or a colon, semicolon or dash). Any hook that runs the check '
         'counts, as the issue asks for "a hook".'),
    ],
    'f15-context-economy': [
        ('finding-always-loaded-table', always_loaded_table, (), 'i', '',
         '`CLAUDE.md` is 10 lines but about 610 words, because its lines are long, and it imports '
         '`@docs/architecture.md` (about 415 words), so about 1,000 words load every session.\n\nPASS when the '
         'report has a Markdown table whose header names words or tokens, with a row naming `CLAUDE.md` and a row '
         'naming `architecture.md`, each holding a number. The numbers themselves are not checked.'),
        ('finding-visible-skill', visible_skill, (), 'i', '',
         '`.claude/skills/schema-rules/SKILL.md` is read only by the `migrator` subagent (by path), but it is '
         'model-invocable, so its description loads in every session.\n\nPASS when the report hides it: a line '
         'naming `schema-rules` and `disable-model-invocation` (not set to false), a frontmatter snippet with '
         '`name: schema-rules` and `disable-model-invocation: true`, or a line that moves (inlines, folds, merges, '
         'puts, copies) `schema-rules` into the `migrator` subagent. `user-invocable: false` keeps the '
         'description loaded and does not count.'),
        ('finding-duplicates-grouped', duplicates_grouped, (), 'i', '',
         'The rule "Never edit files under `migrations/` by hand; create a new one with `bin/migrate new <name>`." '
         'is word for word in `CLAUDE.md`, `docs/contributing.md` and `.claude/agents/migrator.md`, and '
         'paraphrased in the `schema-rules` skill and `docs/architecture.md`.\n\nPASS when one stretch of the '
         'report (a line and what follows, up to 900 characters, not past a heading) names the duplication '
         '(duplicate, repeat, copy, word for word, verbatim, identical, restate, same rule, "3 files"), the '
         'migrations rule, `CLAUDE.md`, `contributing.md` and `migrator.md`, with no negation governing the '
         'duplication word in that stretch.'),
    ],
    'f16-stale-facts': [
        ('finding-stale-folder', stale, (r'carriers/',), 'i', '',
         '`CLAUDE.md` says `src/labelmaker/carriers/` holds one module per carrier; the folder does not exist.\n\n'
         'PASS when one line names `carriers/` and says it is missing (doesn\'t exist, no longer exists, '
         'nonexistent, missing, absent, stale, outdated, out of date, wrong, incorrect, false, no such, not '
         'present/found/there, not in the repo/tree). A line with "if", "unless" or "whether" doesn\'t count, nor '
         'one where a negation governs the missing word ("nothing is stale").'),
        ('finding-stale-file', stale, (r'rates\.toml',), 'i', '',
         '`CLAUDE.md` says carrier rates load from `config/rates.toml`; the file does not exist (rates are '
         'constants in `label.py`).\n\nPASS when one line names `rates.toml` and says it is missing, as for '
         '`finding-stale-folder`.'),
        ('finding-stale-dependency', stale, (r'reportlab',), 'i', '',
         '`CLAUDE.md` says labels render through `reportlab`, pinned in `pyproject.toml`; the project has no '
         'dependencies.\n\nPASS when one line names `reportlab` and says it is missing or not a (declared, '
         'listed, installed) dependency, as for `finding-stale-folder`.'),
        ('structure-alignment-below-a', lambda drop=frozenset(): ALIGNMENT_BELOW_A, (), '', '',
         'Alignment is not A while `CLAUDE.md` states false facts (issue #192).\n\nScript-graded (case-sensitive): '
         'a grade `**Alignment: B**` to `**Alignment: F**`. A report without grades fails.'),
    ],
    'f17-scope': [
        ('finding-parent-noted', parent_noted, (), 'i', '',
         'The repo sits in a folder with its own `CLAUDE.md` and `AGENTS.md`, which load with it but are not the '
         'repo\'s.\n\nPASS when one line mentions the files above (parent, above, enclosing, ancestor, outside '
         'the repo, containing folder, `../`, home folder, higher up) and names `CLAUDE.md` or `AGENTS.md`, '
         'unless "no", "none" or "nothing" comes up to three words before the parent word (as in "no instruction '
         'files above").'),
        ('finding-symlink-real-path', symlink_real_path, (), 'i', '',
         'The repo\'s `CLAUDE.md` is a symlink to its `AGENTS.md`.\n\nPASS when one line names `CLAUDE.md`, '
         '`AGENTS.md` and the link (symlink, symbolic link, links to, points to/at, `->`, an arrow, resolves to, '
         'alias), with no negation governing the link word ("not a symlink").'),
        ('no-invented-agents-md-missing', agents_md_missing, (), 'i', 'not_contains',
         'The repo has an `AGENTS.md` (the real file behind `CLAUDE.md`).\n\nMust not match: a line that says '
         '`AGENTS.md` is missing, absent or not present, doesn\'t exist, "no/missing/without `AGENTS.md`" at the '
         'end of a clause or before file/exists/is present/in, or creates, adds or writes an `AGENTS.md`. A '
         'negated clause (a negation, up to two words, then create, add, write, missing or absent, to the end of '
         'the clause) is skipped, so "no need to create an AGENTS.md" passes while a later claim on the same line '
         'still fails; "why not" is never a negation.'),
        ('finding-parent-blocks-agents', parent_blocks_agents, (), 'i', '',
         'Claude Code reads `AGENTS.md` directly only when no `CLAUDE.md` loads, and a `CLAUDE.md` in a parent '
         'folder counts, so for anyone who has this parent the repo\'s `AGENTS.md` isn\'t read on its own (issue '
         '#192 F13).\n\nPASS when one line names the parent (as in `finding-parent-noted`), `CLAUDE.md`, '
         '`AGENTS.md` and the effect (stops, prevents, blocks, shadows, suppresses, overrides, masks, isn\'t / '
         'won\'t be / never read, loaded or used, no longer read, ignored, skipped, instead of), unless it says '
         'the parent does not (won\'t, never, can\'t) stop, prevent, block or affect it.'),
        ('no-invented-parent-findings', parent_findings, (), 'i', 'not_contains',
         'Only in-repo files are graded. The parent\'s `CLAUDE.md` and `AGENTS.md` name `bin/legacy-build`, '
         'which exists nowhere.\n\nMust not match: a line naming `legacy-build` with a fix word (fix, update, '
         'remove, delete, replace, correct, change, rewrite, drop) that no negation directly governs, or naming '
         'it as missing (as in `finding-stale-folder`) without a scope note (out of scope, outside the repo, not '
         'graded, not part of, excluded, not audited, above the repo).'),
    ],
    'f18-check-commands': [
        ('finding-check-allowlist', check_allowlist, (), 'i', '',
         'The check is defined only in `package.json` (`"check": "bun run lint && bun run typecheck && bun '
         'test"`) and CI (`bun run check`); `CLAUDE.md` says only "use bun run", and there is no settings '
         'file.\n\nPASS when the report allowlists the check: a JSON `"allow": [...]` array holding `"Bash(bun run '
         'check`, or one line with allow (allowlist, pre-approve, permissions), `Bash(bun run check` and a '
         'recommending word. `Bash(bun run:*)` alone does not name the check and does not count.'),
    ],
    'f19-declarative-list': [
        ('no-invented-principles-skill', principles_skill, (), 'i', 'not_contains',
         '`docs/principles.md` is a numbered list of standing principles with no imperative verbs or sequence '
         'words. It is not a procedure, so no skill is needed (issue #192 F15, a false-defect grader like F4).\n\n'
         'Must not match: a line naming the principles that recommends a skill (add, create, make, turn, convert, '
         'move, wrap, extract, package, write, promote or split, then "skill" within 60 characters; "skill for … '
         'principles"; needs/deserves/warrants/should be/belongs in a skill or command), calls it a procedure, or '
         'names `SKILL.md`, a slash command or `.claude/skills/`. A negated clause ("not a procedure", "no skill '
         'is needed") is skipped; "why not" is never a negation.'),
    ],
}


def built(case):
    """(name, pattern, flags, match, doc) for each #192 grader of a case."""
    out = []
    for name, build, args, flags, match, doc in GRADERS[case]:
        pattern = build(*args)
        rules = '' if match or name.startswith('structure-') else LINE_RULES
        text = doc if name.startswith('structure-') else doc + '\n\n' + DOC_SCRIPT.format(
            flags=' (case-insensitive)' if 'i' in flags else '', line_rules=rules)
        out.append((name, pattern, flags, match, text))
    return out


def write_all():
    for case in GRADERS:
        for name, pattern, flags, match, doc in built(case):
            text = "---\ntype: regex\npattern: '%s'\n%s%sweight: 1\n---\n%s\n" % (
                pattern.replace("'", "''"), 'flags: %s\n' % flags if flags else '',
                'match: %s\n' % match if match else '', doc)
            (CASES / case / 'graders' / (name + '.md')).write_text(text)
            print('wrote %s/graders/%s.md' % (case, name))


def plan_item(n, title, body):
    return '%d. **%s** (Coverage, effort S)\n%s\n   Source: [Permissions](https://code.claude.com/docs/en/permissions)\n' % (
        n, title, '\n'.join('   ' + part for part in body.split('\n')))


ASK_JSON = '```json\n{\n  "permissions": {\n    "ask": [\n      "Bash(gh pr merge:*)",\n      "Bash(bin/deploy:*)",\n      "Bash(bin/release:*)"\n    ]\n  }\n}\n```'

# name -> (reports that must pass, reports that must fail). The categories the lead's brief names come first:
# negated, a negation elsewhere on the line, rhetorical question, Source: line, invented note.
CONTROLS = {
    'finding-ask-merge': ([
        plan_item(1, 'Gate the merge, deploy and release commands', 'Change: add to `.claude/settings.json`:\n' + ASK_JSON),
        '- Add an ask rule `Bash(gh pr merge:*)` so no merge lands without a human.',
        'Change: put `Bash(gh pr merge *)` in `permissions.ask`.',
        '| Gate | Rule |\n|---|---|\n| merge | add `Bash(gh pr merge:*)` to ask |',
    ], [
        '- No ask rule is needed for `Bash(gh pr merge:*)`.',
        '- An ask rule for `Bash(gh pr merge:*)` isn\'t needed: branch protection covers it.',
        '- Why not add an ask rule for `Bash(gh pr merge:*)`?',
        '   Source: [Ask rules: `Bash(gh pr merge:*)`](https://code.claude.com/docs/en/permissions)',
        '- Note: `Bash(gh pr merge:*)` is already an ask rule.',
        '- Your settings ask before `Bash(gh pr merge:*)`.',
        '- Add an ask rule for deploys.\n- `Bash(gh pr merge:*)` is the merge command.',
        plan_item(1, 'Gate deploys', 'Change:\n```json\n{"permissions": {"ask": ["Bash(bin/deploy:*)"]}}\n```'),
        '- Add `Bash(gh pr merge:*)` to the allow list.',
        '- No need to add an ask rule for `Bash(gh pr merge:*)`.',
        '- Adding an ask rule for `Bash(gh pr merge:*)` isn\'t needed.',
        '- Should you add an ask rule for `Bash(gh pr merge:*)`?',
        '   Source: [Add ask rules](https://code.claude.com/docs/en/permissions) such as `Bash(gh pr merge:*)`',
        '- `Bash(gh pr merge:*)` is already in the ask list you set up.',
    ]),
    'finding-ask-deploy': ([
        plan_item(1, 'Gate the merge, deploy and release commands', 'Change: add to `.claude/settings.json`:\n' + ASK_JSON),
        '- Add an ask rule for `Bash(./bin/deploy production)`; no deploy should run unattended.',
    ], [
        '- You don\'t need an ask rule for `Bash(bin/deploy:*)`.',
        '- Is an ask rule for `Bash(bin/deploy:*)` worth it?',
        '**Source:** [ask `Bash(bin/deploy:*)`](https://code.claude.com/docs/en/permissions)',
        '- An ask rule for `Bash(bin/deploy:*)` already exists.',
        '- Add `Bash(bin/deploy:*)` to deny.',
        # Smoke a9fd63c (Claudit 4.2.0): a hypothetical left out of the plan is not a recommendation.
        '- Several rules are human-gate rules: merge, deploy and release. They are prose only. If you want them '
        'enforced, ask rather than assume. A `deny` or `ask` permission rule for `Bash(bin/deploy production:*)` and '
        '`Bash(bin/release:*)` would do it. I left them out of the plan because the scan didn\'t flag them.',
        '- No need to add an ask rule for `Bash(bin/deploy:*)`.',
        '- Should you add an ask rule for `Bash(bin/deploy:*)`?',
        '   Source: [Add ask rules](https://code.claude.com/docs/en/permissions) such as `Bash(bin/deploy:*)`',
        '- `Bash(bin/deploy:*)` is already in the ask list you set up.',
    ]),
    'finding-ask-release': ([
        plan_item(1, 'Gate the merge, deploy and release commands', 'Change: add to `.claude/settings.json`:\n' + ASK_JSON),
        '- Add `Bash(bin/release:*)` to the ask list, not to allow.',
    ], [
        '- `Bash(bin/release:*)` doesn\'t need an ask rule.',
        '- Why not ask before `Bash(bin/release:*)`.',
        '  - Source: ask rules for `Bash(bin/release:*)`',
        '- `Bash(bin/release:*)` is already gated by an ask rule.',
        '- No need to add an ask rule for `Bash(bin/release:*)`.',
        '- Should you add an ask rule for `Bash(bin/release:*)`?',
        '   Source: [Add ask rules](https://code.claude.com/docs/en/permissions) such as `Bash(bin/release:*)`',
        '- `Bash(bin/release:*)` is already in the ask list you set up.',
    ]),
    'finding-branch-protection': ([
        '- Branch protection on `main` is the real gate: an ask rule only prompts inside Claude Code.',
        '- Ask rules don\'t replace branch protection, which is the gate that holds for everyone.',
        '- Require reviews with a protected branch; nothing else enforces the merge rule outside Claude Code.',
        '- Turn on a ruleset for `main` so no merge bypasses review.',
        # Smoke a9fd63c (plain): "already" in a later sentence on the line is not a note that it's in place.
        '- **Branch protection:** require PR approval on `main` in GitHub. CI already runs on PRs, so also make `ci / '
        'check` a required status check. This is the only control that holds regardless of what the agent does.',
    ], [
        '- No branch protection is needed: the ask rule is enough.',
        '- No branch protection is needed to gate merges.',
        '- Branch protection isn\'t needed here, since the ask rule gates merges.',
        '- Is branch protection the real gate?',
        '   Source: [About protected branches](https://docs.github.com/en/repositories) enforce reviews',
        '- Branch protection on `main` is already the real gate.',
        '- Branch protection exists on GitHub.',
    ]),
    'finding-commit-hook': ([
        '- Add a PreToolUse hook on `git commit` that runs `bin/check`.',
        plan_item(2, 'Enforce the check with a Stop hook', 'Change: add to `.claude/settings.json`:\n```json\n'
                  '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "bin/check"}]}]}}\n```'),
        '- I didn\'t add a hook for `bin/check` because CI already runs it on every push.',
        # Smoke a9fd63c (Claudit 4.2.0): the hooks block names a script, and the script runs bin/check.
        plan_item(1, 'Enforce the check with a Stop hook', 'Change: add to `.claude/settings.json`:\n```json\n'
                  '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": ".claude/hooks/stop-check.sh"}]}]}}'
                  '\n```\nand create `.claude/hooks/stop-check.sh`:\n```bash\n#!/usr/bin/env bash\nbin/check >&2 || '
                  'exit 2\n```'),
        '- No hook for the commit rule: CI runs `bin/check` on every pull request.',
        '- Install a git pre-commit hook that runs `bin/check`; no commit should skip it.',
    ], [
        '- No hook is needed to run `bin/check`.',
        '- A hook that runs `bin/check` isn\'t needed.',
        '- Why not add a hook that runs `bin/check`?',
        '   Source: [Hooks](https://code.claude.com/docs/en/hooks) run `bin/check`',
        '- A PreToolUse hook already runs `bin/check`.',
        '- Problem: no hook runs `bin/check`, so a commit can skip it.',
        '- Not worth a hook for `bin/check`.',
        '- Problem: the hook config is missing; `bin/check` runs only in CI.',
        plan_item(1, 'Enforce the check with a Stop hook', 'Change:\n```json\n{"hooks": {"Stop": []}}\n```') + '\n'
        + plan_item(2, 'Pre-approve the check', 'Change: allow `bin/check`.'),
        '- No need to add a hook that runs `bin/check`.',
        '- Adding a hook that runs `bin/check` isn\'t needed.',
        '- Should you add a hook for `bin/check`?',
        '   Source: [Add hooks](https://code.claude.com/docs/en/hooks) that run `bin/check`',
        '- A PreToolUse hook you set up already runs `bin/check`.',
    ]),
    'finding-always-loaded-table': ([
        '| File | Lines | Words |\n|---|---|---|\n| `CLAUDE.md` | 10 | 610 |\n| `@docs/architecture.md` | 31 | 415 |\n',
        '| Always loaded | Tokens (approx.) |\n| :--- | ---: |\n| CLAUDE.md | ~820 |\n| docs/architecture.md (import) | ~560 |',
    ], [
        '| File | Lines |\n|---|---|\n| `CLAUDE.md` | 10 |\n| `docs/architecture.md` | 31 |',
        '| File | Words |\n|---|---|\n| `CLAUDE.md` | 610 |',
        '| File | Words |\n|---|---|\n| `CLAUDE.md` | 610 |\n\n- `docs/architecture.md` has 415 words.',
        '- `CLAUDE.md` is 610 words and `docs/architecture.md` adds 415 words.',
        '| File | Words |\n|---|---|\n| `CLAUDE.md` | many |\n| `docs/architecture.md` | some |',
        '| File | Words |\n|---|---|\n| `docs/architecture.md` | 415 |',
    ]),
    'finding-visible-skill': ([
        '- Set `disable-model-invocation: true` on `schema-rules`: only the migrator subagent reads it.',
        '```yaml\n---\nname: schema-rules\ndescription: Naming rules for migrations.\ndisable-model-invocation: true\n---\n```',
        '- Move the rules in `schema-rules` into `.claude/agents/migrator.md`; no other caller reads them.',
    ], [
        '- `schema-rules` doesn\'t need `disable-model-invocation`.',
        '- Why not set `disable-model-invocation` on `schema-rules`?',
        '   Source: [Skills: disable-model-invocation](https://code.claude.com/docs/en/skills) for schema-rules',
        '- `schema-rules` already has `disable-model-invocation: true`.',
        '- Set `disable-model-invocation: false` on `schema-rules`.',
        '- Set `user-invocable: false` on `schema-rules`.',
        '- Don\'t move `schema-rules` into the migrator subagent.',
    ]),
    'finding-duplicates-grouped': ([
        '### Duplicated rules\n\nThe migrations rule is copied word for word in `CLAUDE.md:4`, '
        '`docs/contributing.md:10` and `.claude/agents/migrator.md:9`, and paraphrased in two more places. Keep '
        'one copy.',
        '- The same rule ("Never edit files under `migrations/` by hand") appears in 3 files:\n  - `CLAUDE.md`\n'
        '  - `docs/contributing.md`\n  - `.claude/agents/migrator.md`\n  No other rule is repeated.',
    ], [
        '- The migrations rule is not duplicated: `CLAUDE.md`, `docs/contributing.md` and `migrator.md` each say '
        'something different.',
        '- The migrations rule appears in `CLAUDE.md`, `docs/contributing.md` and `migrator.md`.',
        '- The migrations rule is duplicated in `CLAUDE.md` and `docs/contributing.md`.',
        '- The migrations rule is duplicated in `CLAUDE.md` and `.claude/agents/migrator.md`.',
        '- Duplicated: `CLAUDE.md`.\n\n## Other\n\n- migrations in `docs/contributing.md` and `migrator.md`.',
    ]),
    'finding-stale-folder': ([
        '- `CLAUDE.md:8` names `src/labelmaker/carriers/`, which doesn\'t exist.',
        '| `src/labelmaker/carriers/` | missing |',
        '- Fix the stale path `src/labelmaker/carriers/`; no other path is wrong.',
    ], [
        '- `src/labelmaker/carriers/` is not missing.',
        '- Nothing is stale: `src/labelmaker/carriers/` exists.',
        '- Is `src/labelmaker/carriers/` missing?',
        '   Source: [Stale paths](https://code.claude.com/docs/en/memory) `carriers/` missing',
        '- `src/labelmaker/carriers/` holds one module per carrier.',
        '- If `src/labelmaker/carriers/` is missing, the CLI fails.',
    ]),
    'finding-stale-file': ([
        '- `config/rates.toml` does not exist; rates are constants in `label.py`.',
        '- CLAUDE.md names `config/rates.toml`, `src/labelmaker/carriers/` and `reportlab`; none of them exists.',
    ], [
        '- `config/rates.toml` isn\'t stale.',
        '- Why not check whether `config/rates.toml` exists?',
        '  Source: `config/rates.toml` not found',
        '- Rates load from `config/rates.toml`.',
        '- Is `config/rates.toml` missing?',
    ]),
    'finding-stale-dependency': ([
        '- `reportlab` is not a declared dependency: `pyproject.toml` lists none.',
        '- CLAUDE.md says labels render through `reportlab`, which is wrong; nothing imports it and no other fact '
        'is off.',
    ], [
        '- The `reportlab` pin is not wrong.',
        '- Is `reportlab` missing from `pyproject.toml`?',
        '   Source: `reportlab` missing',
        '- `reportlab` is pinned in `pyproject.toml`.',
    ]),
    'structure-alignment-below-a': ([
        '- **Alignment: C** (confidence: high). Items 1 and 2 would raise it to A.',
    ], [
        '- **Alignment: A** (confidence: high).', 'Alignment is C.',
    ]),
    'finding-parent-noted': ([
        '- The folder above this repo has its own `CLAUDE.md` and `AGENTS.md`; they load too but aren\'t graded.',
        '- `../CLAUDE.md` loads with this repo; no findings for the parent files.',
    ], [
        '- There is no `CLAUDE.md` or `AGENTS.md` above the repo.',
        '- Are there instruction files in the parent folder? Check `../CLAUDE.md`?',
        '   Source: [Memory](https://code.claude.com/docs/en/memory) parent CLAUDE.md files load',
        '- The parent folder exists.',
    ]),
    'finding-symlink-real-path': ([
        '- `CLAUDE.md` is a symlink to `AGENTS.md`, so they are one file.',
        '- `CLAUDE.md -> AGENTS.md`: no separate file to keep in sync.',
    ], [
        '- `CLAUDE.md` is not a symlink to `AGENTS.md`.',
        '- Is `CLAUDE.md` a symlink to `AGENTS.md`?',
        '   Source: `CLAUDE.md` symlink to `AGENTS.md`',
        '- `CLAUDE.md` and `AGENTS.md` both exist.',
    ]),
    'no-invented-agents-md-missing': ([
        '- `CLAUDE.md` is a symlink to `AGENTS.md`.',
        '- No need to create an `AGENTS.md`: `CLAUDE.md` links to it.',
        '- The repo has no `AGENTS.md` problem worth fixing.',
        '   Source: create an AGENTS.md (https://code.claude.com/docs/en/memory)',
        '- `AGENTS.md` isn\'t missing.',
    ], [
        '- `AGENTS.md` is missing.',
        '- Don\'t add hooks; create an `AGENTS.md` for other tools.',
        '- No need to add hooks, and `AGENTS.md` does not exist.',
        '- Why not create an `AGENTS.md`?',
        '- Note: the repo has no AGENTS.md.',
    ]),
    'finding-parent-blocks-agents': ([
        '- The parent folder\'s `CLAUDE.md` stops the repo\'s `AGENTS.md` being read directly for anyone who has '
        'that parent.',
        '- Because `../CLAUDE.md` loads, `AGENTS.md` won\'t be read on its own; the symlink is what loads it.',
    ], [
        '- The parent `CLAUDE.md` does not stop `AGENTS.md` loading.',
        '- Does the parent `CLAUDE.md` stop `AGENTS.md` being read?',
        '   Source: [AGENTS.md](https://code.claude.com/docs/en/memory) a parent CLAUDE.md stops it being read',
        '- The parent `CLAUDE.md` and the repo\'s `AGENTS.md` both load.',
    ]),
    'no-invented-parent-findings': ([
        '- `../CLAUDE.md` names `bin/legacy-build`, which doesn\'t exist; it is outside the repo, so not graded.',
        '- Don\'t fix `bin/legacy-build` in the parent file: it\'s not this repo\'s.',
        '   Source: fix `bin/legacy-build`',
        '- The parent mentions `bin/legacy-build`.',
    ], [
        '- Remove `bin/legacy-build` from `../CLAUDE.md`.',
        '- `bin/legacy-build` does not exist.',
        '- Don\'t add hooks; fix the `bin/legacy-build` reference.',
        '- Why not update `bin/legacy-build`?',
        '- Note: `bin/legacy-build` is stale.',
    ]),
    'finding-check-allowlist': ([
        plan_item(1, 'Pre-approve the check commands', 'Change: create `.claude/settings.json`:\n```json\n'
                  '{"permissions": {"allow": ["Bash(bun run check)"]}}\n```'),
        '- Add `Bash(bun run check:*)` to `permissions.allow`; no other command needs it.',
    ], [
        '- `Bash(bun run check)` doesn\'t need an allow rule.',
        '- Why not allow `Bash(bun run check)`?',
        '   Source: allow `Bash(bun run check)`',
        '- `Bash(bun run check)` is already allowed.',
        '- Add `Bash(bun run:*)` to `permissions.allow`.',
        '- Nothing allows `Bash(bun run check)` yet.',
        '- No need to add an allow rule for `Bash(bun run check)`.',
        '- Should you add an allow rule for `Bash(bun run check)`?',
        '   Source: [Add allow rules](https://code.claude.com/docs/en/permissions) such as `Bash(bun run check)`',
        '- `Bash(bun run check)` is already allowed; add nothing.',
        '- `permissions.allow` would hold `Bash(bun run check)`.',
    ]),
    'no-invented-principles-skill': ([
        '- `docs/principles.md` is a list of principles, not a procedure, so it needs no skill.',
        '- No procedure needs a skill: `docs/principles.md` holds standing principles.',
        '- Don\'t turn `docs/principles.md` into a skill.',
        '   Source: [Skills](https://code.claude.com/docs/en/skills) procedures and principles',
        '- `docs/principles.md` is imported correctly.',
        '- Add a skill for releases; the principles are fine as they are.',
        '- The release steps are a procedure; add a skill.',
    ], [
        '- Turn `docs/principles.md` into a skill.',
        '- Why not make `docs/principles.md` a skill?',
        '- Note: `docs/principles.md` is a procedure.',
        '- Don\'t add hooks; make `docs/principles.md` a skill.',
        '- `docs/principles.md` deserves its own skill.',
        '- Is a skill for the principles worth it?',
    ]),
}

# Each named part a builder can drop: the control it must flip is in CONTROLS. structure-alignment-below-a has none.
MUTATIONS = {
    'finding-ask-merge': ('source', 'question', 'neg-before', 'neg-after', 'already', 'verb', 'rule'),
    'finding-ask-deploy': ('source', 'question', 'neg-before', 'already'),
    'finding-ask-release': ('source', 'question', 'neg-before', 'already'),
    'finding-branch-protection': ('source', 'question', 'neg-before', 'neg-after', 'already', 'gate'),
    'finding-commit-hook': ('source', 'question', 'neg-before', 'neg-after', 'already', 'reason-shape'),
    'finding-always-loaded-table': ('units', 'claude-row', 'import-row'),
    'finding-visible-skill': ('source', 'question', 'neg-before', 'already', 'not-false'),
    'finding-duplicates-grouped': ('neg', 'contributing', 'migrator', 'dup'),
    'finding-stale-folder': ('source', 'question', 'neg-before', 'hypothetical', 'missing'),
    'finding-stale-file': ('source', 'question', 'neg-before', 'missing'),
    'finding-stale-dependency': ('source', 'question', 'neg-before', 'missing'),
    'finding-parent-noted': ('source', 'question', 'no-parent', 'file'),
    'finding-symlink-real-path': ('source', 'question', 'neg-before', 'link'),
    'no-invented-agents-md-missing': ('source', 'skip-negated'),
    'finding-parent-blocks-agents': ('source', 'question', 'denied', 'block'),
    'no-invented-parent-findings': ('source', 'skip-negated', 'scope'),
    'finding-check-allowlist': ('source', 'question', 'neg-before', 'already', 'verb'),
    'no-invented-principles-skill': ('source', 'skip-negated', 'principles'),
}


def builders():
    return {name: (build, args, flags, match) for case in GRADERS for name, build, args, flags, match, _ in GRADERS[case]}


class FixtureGraderTests(unittest.TestCase):
    def test_committed_graders_are_built_here(self):
        for case in GRADERS:
            for name, pattern, flags, match, _ in built(case):
                with self.subTest(case=case, grader=name):
                    grader = regex_grader(CASES / case / 'graders' / (name + '.md'))
                    self.assertEqual(grader['pattern'], pattern, 'rebuild with --write')
                    self.assertEqual(grader.get('flags', ''), flags)
                    self.assertEqual(grader.get('match', ''), match)

    def test_every_grader_has_controls(self):
        self.assertEqual(set(CONTROLS), set(builders()))
        for name, (passing, failing) in CONTROLS.items():
            self.assertTrue(passing and failing, name)

    def checks(self):
        out = []
        for case in GRADERS:
            for name, pattern, flags, match, _ in built(case):
                grader = {'pattern': pattern, 'flags': flags, 'match': match}
                passing, failing = CONTROLS[name]
                out += [(name, grader, text, True) for text in passing] + [(name, grader, text, False) for text in failing]
        return out

    def test_controls(self):
        for name, grader, text, want in self.checks():
            with self.subTest(grader=name, want=want, report=text[:70]):
                self.assertEqual(verdict(grader, text), want)

    def test_patterns_use_only_the_shared_regex_subset(self):
        for name, (build, args, flags, match) in builders().items():
            with self.subTest(grader=name):
                self.assertNotRegex(build(*args), r'\(\?[iPmsx<]|\\[AZz]|\(\?<[=!]')

    def test_every_guard_is_load_bearing(self):
        """Mutation check: dropping any named part of a pattern flips at least one control."""
        for name, parts in MUTATIONS.items():
            build, args, flags, match = builders()[name]
            passing, failing = CONTROLS[name]
            for part in parts:
                with self.subTest(grader=name, dropped=part):
                    mutant = {'pattern': build(*args, drop=frozenset({part})), 'flags': flags, 'match': match}
                    self.assertNotEqual(mutant['pattern'], build(*args), 'the part is not in the pattern')
                    flipped = [t for t in passing if not verdict(mutant, t)] + [t for t in failing if verdict(mutant, t)]
                    self.assertTrue(flipped, 'no control notices the dropped part')

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_engine_agrees(self):
        checks = self.checks()
        self.assertEqual(js_verdicts([[g['pattern'], g['flags'], g['match'], t] for _, g, t, _ in checks]),
                         [want for _, _, _, want in checks])


if __name__ == '__main__':
    if sys.argv[1:] == ['--write']:
        write_all()
    else:
        unittest.main()
