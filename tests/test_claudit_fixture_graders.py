"""Script graders for the issue #192 fixtures (f14 to f19), their adversarial controls and mutation checks.

The patterns are built here from named parts and committed as grader files; rebuild them after a change with

    python3 tests/test_claudit_fixture_graders.py --write

Each grader runs as a JavaScript regex inside `claude plugin eval`; the controls run in Python and, when node is
installed, in node. Every grader has controls a correct report passes and controls it fails. For each accepted
form of a positive grader: a direct negation, a negation earlier in the sentence, a hypothetical or optional framing
and a declined-in-plan clause; and for every grader a negation elsewhere on the line, a rhetorical question, Claudit's
own `Source:` citation line and an invented note. `test_every_guard_is_load_bearing` drops each named part of a
pattern in turn and needs a control to flip.
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
NEG = (r'(?:no|not|never|without|nor|none|nothing|neither|don%(q)st|doesn%(q)st|didn%(q)st|wouldn%(q)st|haven%(q)st'
       r'|hasn%(q)st|isn%(q)st|aren%(q)st|wasn%(q)st|won%(q)st|needn%(q)st|shouldn%(q)st|cannot|can%(q)st|skip|avoid)'
       % {'q': Q})
# What blocks a claim inside its clause: a negation word, or "rather than" / "instead of".
NEGB = r'\b%s\b|\brather[ \t]+than\b|\binstead[ \t]+of\b' % NEG
# Clause boundaries for claims: . ; ! ? before a space or the end, "and"/"but"/"then"/"so"/"while"/"whereas" (not
# when a backticked name or rule follows, as in a list), or a spaced dash. Commas and colons don't end a clause, so
# "No paths are stale, including X" stays one negated clause.
JOIN = r'[ \t]+(?:and|but|then|so|while|whereas)[ \t]+(?![\x60*"]|Bash\()|[ \t]+[—–-][ \t]+'
CEND = r'[.;!?](?=[ \t*_)"\x60]|\n|(?![\s\S]))|' + JOIN
CSTART = r';[ \t]+|' + JOIN
# A character inside one sentence: . ! ? end it only before a space or the end (not inside a file name).
SENT = r'(?:[^\n.!?]|[.!?](?=[^\s*_)"\x60]))'
SOURCE = r'(?![ \t]*(?:[-*>][ \t]+)?(?:\*\*|_)?Sources?\b)'
QUESTION = r'(?!%s*?(?:\bwhy[ \t]+not\b|\?(?=[ \t*_"\x60)]|\n|(?![\s\S]))))' % SENT
# Hypothetical or optional framing: "would do it", "you could", "if you want", "If the parent had".
HYPO_P = (r'(?:[.;:!?][ \t]+if\b|\bif[ \t]+(?:you|we|they|needed|wanted|desired|preferred|so|there[ \t]+(?:were|was)|it[ \t]+(?:were|had))\b'
          r'|\bif\b[^\n]{0,40}?\bhad\b|\bunless\b|\bwhether\b|\b(?:could|might)\b|\bwould[ \t]+(?:\S+[ \t]+)?(?:do|work'
          r'|help|fix|cover|be|suffice|stop|catch|gate)\b|\boptional(?:ly)?\b|\bnice[ -]to[ -]have\b)')
# A line or sentence that opens with "If" is a hypothetical too.
HYPOTHETICAL = r'(?![ \t]*(?:[-*+>]|[0-9]+[.)])?[ \t]*(?:\*\*|_)?if\b)(?!%s*?%s)' % (SENT, HYPO_P)
# Declined from the plan: "I didn't add it to the plan", "left it out", "not recommended".
DECLINED_P = (r'(?:\b(?:not|n%st)[ \t]+(?:\S+[ \t]+){0,4}?(?:in|into|to|part[ \t]+of|on)[ \t]+(?:the|my|this)[ \t]+plan\b'
              r'|\bleft[ \t]+(?:\S+[ \t]+){0,2}?out\b|\bout[ \t]+of[ \t]+(?:the[ \t]+)?plan\b|\bnot[ \t]+(?:planned'
              r'|recommended|recommending|proposing|included)\b|\bdeclin\w*|\bskipped\b)' % Q)
DECLINED = r'(?![^\n]*%s)' % DECLINED_P
# A negated clause runs to . , ; : ! ? before a space or the end, "and", "but", "while", "whereas", "yet", or a line
# break; it can't stop early at the dot inside a file name.
CLAUSE = (r'(?:(?![ \t]+(?:and|but|while|whereas|yet)\b)[^\n.,;:!?]|[.,;:!?](?=\S))*'
          r'(?=[.,;:!?](?!\S)|[ \t]+(?:and|but|while|whereas|yet)\b|\n|(?![\s\S]))')
CTOK = r'(?:[^\s;:!?]*[^\s.,;:!?][ \t]+)'  # a word inside one clause
WINDOW = r'(?:(?!\n#{1,3}[ \t])[\s\S]){0,900}?'  # up to 900 characters, not past a heading


def has(pattern):
    """Later in the same sentence."""
    return '(?=%s*?%s)' % (SENT, pattern)


def either(*forms):
    return '(?:' + '|'.join(forms) + ')'


def claim(a, b, drop=frozenset()):
    """a and b in one clause of the line, in either order, with no negation (or "rather than", "instead of") before
    either of them in that clause. A cue that itself starts with a negation ("doesn't exist") still matches, because
    the cue is tried before the negation blocks."""
    if 'claim' in drop:
        return has(a) + has(b)
    run = r'(?:(?!%s|%s)[^\n])*?' % (NEGB, CEND)
    return r'(?=(?:%s*?(?:%s))?(?:%s%s%s(?:%s)|%s%s%s(?:%s)))' % (SENT, CSTART, run, a, run, b, run, b, run, a)


def neg_after(word):
    """"<word> isn't needed", "<word> is unnecessary", within five words."""
    return (r'(?!%s*?%s[\x60*")]{0,2}[ \t]+%s{0,5}?(?:(?:(?:is|are|was|were)n%st|(?:is|are|was|were|be)[ \t]+not'
            r'|not)[ \t]+(?:really[ \t]+)?(?:needed|necessary|required|worth\w*|useful|helpful|enough|relevant'
            r'|applicable|the[ \t]+(?:real[ \t]+)?gate|a[ \t]+gate)|(?:is|are|be)[ \t]+(?:unnecessary|overkill'
            r'|redundant|pointless)))' % (SENT, word, TOK, Q))


def already(word):
    """An invented note that the fix is in place: "already an ask rule", "an ask rule ... already exists" (in the
    same clause, so "CI already runs on PRs" after a full stop doesn't count)."""
    return (r'(?!%s*?(?:\balready[ \t]+%s{0,3}?[\x60*"(]*%s|%s(?:[^\n.;:!?]|[.;:!?](?=\S)){0,60}?\balready[ \t]+'
            r'(?:exists?|in[ \t]+place|there|present|configured|set[ \t]+up|enabled|covered|an?|the|asks?|gates?'
            r'|protects?|handles?|runs?|checks?|enforces?|blocks?)\b))' % (SENT, TOK, word, word))


def line(parts, drop):
    """A sentence holding every lookahead in `parts` (name -> pattern) whose name isn't in `drop`. The line must not
    be a Source: line or say the change was declined from the plan; the other parts look only at the sentence, so a
    hypothetical or question in another sentence doesn't hide a recommendation."""
    head = BOL + ''.join(parts[name] for name in ('source', 'declined') if name in parts and name not in drop)
    rest = ''.join(pattern for name, pattern in parts.items() if name not in drop and name not in ('source', 'declined'))
    return head + r'(?:[^\n]*?[.!?][ \t]+)?' + rest + r'[^\n]*'


def framing(drop):
    """The guards every finding line carries."""
    return {'source': SOURCE, 'question': QUESTION, 'hypothetical': HYPOTHETICAL, 'declined': DECLINED}


def block(inner, drop=frozenset()):
    """A fenced block holding `inner`, introduced by a line that isn't negated, hypothetical or declined."""
    intro = '' if 'intro' in drop else r'(?![^\n]*(?:%s|%s|\b(?:don%st|do[ \t]+not|never|avoid)\b))' % (
        HYPO_P, DECLINED_P, Q)
    # The fence opens the text, or follows a non-blank intro line (and at most one blank line).
    return (r'(?:^(?=[ \t]*\x60{3})|(?:^|\n)' + intro + r'[^\n]*\S[^\n]*\n(?:[ \t]*\n)?)[ \t]*\x60{3}[^\n]*\n'
            r'(?:(?!\x60{3})[\s\S])*?' + inner)


def free_of(found, negated, drop=(), require=''):
    """A not_contains pattern: a line (not a Source: line) with a claim that no negation directly governs. A negated
    clause (a negation, up to two words, then a governed word, to the end of the clause) is skipped as a unit, so a
    negation elsewhere on the line doesn't exempt a later claim; "why not" is never a negation."""
    skip = r'%s[ \t]+%s{0,2}?%s%s' % (NEG, CTOK, negated, CLAUSE)
    scan = (r'(?:\bwhy[ \t]+not\b|\b%s|(?!\b%s)[^\n])*?' % (skip, skip)) if 'skip-negated' not in drop else r'[^\n]*?'
    return BOL + ('' if 'source' in drop else SOURCE) + require + scan + found


def recommended(verb, rule, extra, drop):
    """A recommendation line for a settings rule: the rule and its key word on the line, and a recommending verb in a
    clause that names the rule (or "one", "it", "them") with no negation governing it."""
    pronoun = r'(?:%s|\b(?:one|it|them|these|those)\b)' % rule
    return line({**framing(drop), 'already': already(extra), 'neg-after': neg_after(extra), 'key': has(extra),
                 'rule': has(rule), 'claim': claim(verb + r'(?![ \t]+(?:nothing|no|none)\b)', pronoun, drop)}, drop)


# f14-enforcement (issue F10): the prose-only gates and the unenforced must-run rule.
ASK = r'(?:\bask\b|permissions\.ask)'
ASK_VERB = (r'(?:\b(?:add|adding|put|move|use|using|set|create|include|list|register|require|requir\w*|should'
            r'|recommend\w*|Change)\b|[^\w-]gate\b)')  # "gate" the verb, not "human-gate"


def ask_rule(command, drop=frozenset()):
    rule = r'Bash\([ \t]*%s' % command
    return either(block(r'"ask"[ \t]*:[ \t]*\[[^\]]*?"' + rule, drop), recommended(ASK_VERB, rule, ASK, drop))


BRANCH = (r'(?:branch[ \t-]+protection|protected[ \t]+branch(?:es)?|branch[ \t]+(?:protection[ \t]+)?rules?'
          r'|rulesets?|required[ \t]+(?:pull[ \t]+request[ \t]+)?reviews?)')
GATE = (r'(?:\bgate\w*|\benforc\w*|\breal[ \t]+(?:gate|control|guarantee|enforcement|protection)|\bonly[ \t]+(?:real'
        r'[ \t]+)?(?:control|gate|guarantee|enforcement|thing)|\bactual[ \t]+(?:gate|control)|\bserver[- ]side\b'
        r'|\bbypass\w*|\bbackstop\w*|\bguarantee\w*|\b(?:blocks?|prevents?|stops?)[ \t]+(?:\S+[ \t]+){0,2}?merg\w*'
        r'|\brequir\w*[ \t]+(?:\S+[ \t]+){0,2}?(?:approv\w*|reviews?|status[ \t]+checks?))')


def branch_protection(drop=frozenset()):
    # "... branch protection, which is the real gate": the relative clause says what branch protection is.
    which = r'(?=[^\n]*%s[\x60*]{0,2},?[ \t]+which[ \t]+(?:is|are)[ \t]+(?:(?!%s\b)\S+[ \t]+){0,3}?%s)' % (
        BRANCH, NEG, GATE)
    return line({**framing(drop), 'already': already(BRANCH), 'neg-after': neg_after(BRANCH),
                 'claim': either(claim(BRANCH, GATE, drop), which if 'which' not in drop else '(?!)')}, drop)


HOOK = r'\b(?:PreToolUse|PostToolUse|Stop|pre-commit|precommit|git[ \t]+hooks?|hooks?)\b'
HOOK_VERB = (r'\b(?:add|adding|create|creating|install|installing|wire|wiring|use|using|set[ \t]+up|setting[ \t]+up'
             r'|register|configure|enforce\w*|Change)\b')
# Not adding a hook: "I didn't add a hook", "no hook is needed", "skip the hook", "instead of a hook".
NO_HOOK = (r'(?:\b(?:did(?:n%(q)st|[ \t]+not)|do(?:n%(q)st|[ \t]+not)|won%(q)st|will[ \t]+not|wouldn%(q)st|would[ \t]+not)'
           r'[ \t]+(?:add|use|recommend|suggest|propose|need)\w*[ \t]+(?:\S+[ \t]+){0,2}?hooks?\b|\bno[ \t]+(?:\S+[ \t]+)?'
           r'hooks?[ \t]+(?:is[ \t]+|are[ \t]+)?(?:needed|necessary|required|worth\w*|recommended|planned)\b'
           r'|\b(?:skip(?:ped|ping)?|leav(?:e|ing)[ \t]+out|instead[ \t]+of|rather[ \t]+than)[ \t]+(?:a[ \t]+|an[ \t]+'
           r'|the[ \t]+|any[ \t]+)?(?:\S+[ \t]+)?hooks?\b|\bhooks?[ \t]+(?:isn%(q)st|is[ \t]+not|aren%(q)st|are[ \t]+not)'
           r'[ \t]+(?:needed|necessary|worth\w*)\b)' % {'q': Q})
BECAUSE = r'\b(?:because|since|as|given)\b'


def commit_hook(drop=frozenset()):
    """A hook that runs bin/check (a JSON hooks block or a line), or a line giving the reason for not adding one."""
    hook_line = line({**framing(drop), 'already': already(HOOK), 'neg-after': neg_after(HOOK),
                      'check': has(r'bin/check'), 'claim': claim(HOOK_VERB, HOOK, drop)}, drop)
    # A hooks block, then bin/check in the same change: the block itself or a script it names, before the next
    # heading or column-0 numbered item.
    json_hook = block(r'"(?:PreToolUse|Stop)"[ \t]*:[ \t]*\[', drop) + (
        r'(?:(?!\n#{1,3}[ \t]|\n[0-9]+[.)][ \t])[\s\S]){0,1500}?bin/check')
    reason = BOL + ('' if 'source' in drop else SOURCE) + ('' if 'question' in drop else QUESTION) + (
        r'(?=[^\n]*(?:bin/check|\bcommit))[^\n]*?%s[^\n]*?%s' % (NO_HOOK, BECAUSE) if 'reason-shape' not in drop
        else r'[^\n]*%s[^\n]*(?:%s|[:;])' % (HOOK, BECAUSE))
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
SET_VERB = r'\b(?:set|setting|add|adding|put|mark|marking|use|using|give|giving|turn[ \t]+on|enable|Change)\b'
MOVE = r'\b(?:move|moving|inline|inlining|fold|folding|merge|merging|put|putting|copy|copying)\b'


def visible_skill(drop=frozenset()):
    """The subagent-only skill hidden from the model: disable-model-invocation on schema-rules, or its rules moved
    into the migrator subagent."""
    dmi_line = line({**framing(drop), 'already': already(DMI), 'skill': has(r'schema-rules'),
                     'not-false': r'(?![^\n]*%s[\x60*"]{0,2}[ \t]*:[ \t]*[\x60*"]?false)' % DMI,
                     'claim': claim(SET_VERB, DMI, drop)}, drop)
    frontmatter = block(r'(?:name:[ \t]*schema-rules(?:(?!\x60{3})[\s\S]){0,400}?%s:[ \t]*true|%s:[ \t]*true'
                        r'(?:(?!\x60{3})[\s\S]){0,400}?name:[ \t]*schema-rules)' % (DMI, DMI), drop)
    move_line = line({**framing(drop), 'skill': has(r'schema-rules'), 'claim': claim(MOVE, r'migrator', drop)}, drop)
    return either(frontmatter, dmi_line, move_line)


DUP = (r'(?:\bduplicat\w*|\brepeat\w*|\bcop(?:y|ies|ied)\b|\bword[ -]for[ -]word\b|\bverbatim\b|\bidentical\b'
       r'|\brestat\w*|\bsame[ \t]+(?:rule|sentence|line|text|instruction)s?\b|\b[3-5][ \t]+(?:files|places|copies)\b'
       r'|\b(?:three|four|five)[ \t]+(?:files|places|copies|times)\b)')
FILLER = (r'(?:(?:need\w*|requir\w*|ha(?:ve|s)|us(?:e|ing)|is|are|be|any|a|an|the|for|of|to|also|really|actually'
          r'|even|yet|this|that|such|rule|rules)[ \t]+)')


def duplicates_grouped(drop=frozenset()):
    """One stretch of the report (up to 900 characters, no heading) names the duplication, the migrations rule and
    the three files that copy it word for word, and doesn't deny the duplication."""
    # The stretch starts on the line that names the duplication; that line carries the usual framing guards.
    start = BOL + ''.join(v for k, v in framing(drop).items() if k not in drop) + has(DUP)
    parts = {'rule': r'\bmigrat', 'claude': r'CLAUDE\.md', 'contributing': r'contributing\.md',
             'migrator': r'migrator\.md'}
    out = start + ''.join('(?=%s%s)' % (WINDOW, pattern) for name, pattern in parts.items() if name not in drop)
    if 'neg' not in drop:
        out += r'(?!%s\b%s[ \t]+%s{0,4}%s)' % (WINDOW, NEG, FILLER, DUP)
    return out


# f16-stale-facts (issue F12).
MISSING = (r'(?:\bdo(?:es)?(?:n%(q)st|[ \t]+not)[ \t]+exist|\bno[ \t]+longer[ \t]+(?:exists?|there|present)'
           r'|\bnon-?existent\b|\bmissing\b|\babsent\b|\bstale\b|\boutdated\b|\bout[ \t]+of[ \t]+date\b|\bwrong\b'
           r'|\bincorrect\b|\bfalse\b|\bgone\b|\bno[ \t]+such\b|\bnot[ \t]+(?:present|found|there)\b|\bnot[ \t]+in'
           r'[ \t]+(?:the[ \t]+)?(?:repo\w*|tree|project|pyproject)|\b(?:is|are|was)(?:n%(q)st|[ \t]+not)[ \t]+'
           r'(?:present|there|found|in[ \t]+)|\bnot[ \t]+(?:a[ \t]+)?(?:declared[ \t]+|listed[ \t]+|installed[ \t]+)?'
           r'dependenc\w*|\b(?:is|are)(?:n%(q)st|[ \t]+not)[ \t]+(?:declared|listed|installed)\b|\bnot[ \t]+'
           r'(?:declared|listed|installed)\b|\b(?:none|neither)\b[^\n]{0,30}\bexists?\b)' % {'q': Q})
NONE_EXIST = (r'\b(?:none|neither)[ \t]+of[ \t]+(?:them|these|those|the[ \t]+three)[ \t]+(?:exists?|is[ \t]+(?:present'
              r'|real|there))\b')


def stale(key, drop=frozenset()):
    return line({**framing(drop), 'key': has(key), 'claim': either(claim(key, MISSING, drop), has(NONE_EXIST))}, drop)


ALIGNMENT_BELOW_A = r'\*\*Alignment: [B-F]\*\*'

# f17-scope (issue F13).
PARENT = (r'(?:\bparent\b|\babove\b|\benclosing\b|\bancestor\w*|\boutside[ \t]+(?:the[ \t]+|this[ \t]+)?'
          r'(?:repo\w*|project|checkout)|\bcontaining[ \t]+(?:folder|directory)|\.\./|\bhome[ \t]+(?:folder'
          r'|directory)|~/(?:CLAUDE|AGENTS)\.md|\bup[ \t]+the[ \t]+tree|\bhigher[ \t]+up\b)')


def parent_noted(drop=frozenset()):
    return line({**framing(drop), 'claim': claim(PARENT, r'(?:CLAUDE|AGENTS)\.md', drop)}, drop)


LINK = (r'(?:\bsymlink\w*|\bsymbolic[ \t]+link|\blinks?[ \t]+to\b|\bpoints?[ \t]+(?:at|to)\b|->|→'
        r'|\bresolves?[ \t]+to\b|\balias\w*)')


def symlink_real_path(drop=frozenset()):
    """CLAUDE.md reported as a link to AGENTS.md, not a proposal to make it one ("Make CLAUDE.md a symlink")."""
    proposal = (r'(?![^\n]*\b(?:make|making|turn|convert|replace|change|create|should|ln[ \t]+-s)\b'
                r'(?:[^\n.;!?]|[.;!?](?=\S)){0,40}?%s)' % LINK)
    return line({**framing(drop), 'proposal': proposal, 'agents': has(r'AGENTS\.md'),
                 'claim': claim(r'CLAUDE\.md', LINK, drop)}, drop)


AGENTS_MISSING = (r'(?:AGENTS\.md[\x60*"]{0,2}:?[ \t]+(?:is|was)[ \t]+(?:missing|absent|not[ \t]+(?:present|there'
                  r'|found))|AGENTS\.md[\x60*"]{0,2}:?[ \t]+(?:isn%(q)st|wasn%(q)st)[ \t]+(?:present|there|found)'
                  r'|AGENTS\.md[\x60*"]{0,2}:?[ \t]+not[ \t]+found|AGENTS\.md[\x60*"]{0,2}[ \t]+(?:does[ \t]+not|doesn%(q)st'
                  r'|did[ \t]+not|didn%(q)st)[ \t]+exist|\b(?:no|missing|without)[ \t]+(?:an?[ \t]+)?[\x60*"]{0,2}'
                  r'AGENTS\.md[\x60*"]{0,2}(?=[ \t]*(?:[.,;:)]|\n|(?![\s\S]))|[ \t]+(?:file|exists|is[ \t]+present|in)\b)'
                  r'|\b(?:create|add|write)\w*[ \t]+(?:an?[ \t]+|the[ \t]+)?(?:missing[ \t]+)?[\x60*"]{0,2}AGENTS\.md)'
                  % {'q': Q})


def agents_md_missing(drop=frozenset()):
    return free_of(AGENTS_MISSING, r'(?:creat\w*|add\w*|writ\w*|missing|absent)', drop)


BLOCK = (r'(?:\bstops?\b|\bstopping\b|\bprevents?\b|\bblocks?\b|\bshadows?\b|\bsuppress\w*|\boverrid\w*|\bmasks?\b'
         r'|\b(?:isn%(q)st|aren%(q)st|won%(q)st[ \t]+be|wouldn%(q)st[ \t]+be|will[ \t]+not[ \t]+be|would[ \t]+not'
         r'[ \t]+be|is[ \t]+not|are[ \t]+not|not|never)[ \t]+(?:\S+[ \t]+)?(?:read|loaded|picked[ \t]+up|used)\b'
         r'|\bno[ \t]+longer[ \t]+(?:read|loaded)\b|\bignored\b|\bskipped\b)' % {'q': Q})


def parent_blocks_agents(drop=frozenset()):
    denied = (r'(?![^\n]*\b(?:does(?:n%st|[ \t]+not)|won%st|will[ \t]+not|never|can%st|cannot|wouldn%st|would[ \t]+not)'
              r'[ \t]+(?:\S+[ \t]+)?(?:stop|prevent|block|shadow|suppress|override|mask|affect))' % (Q, Q, Q, Q))
    return line({**framing(drop), 'denied': denied, 'parent': has(PARENT), 'agents': has(r'AGENTS\.md'),
                 'claim': claim(r'CLAUDE\.md', BLOCK, drop)}, drop)


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
    return either(block(r'"allow"[ \t]*:[ \t]*\[[^\]]*?"' + rule, drop), recommended(ALLOW_VERB, rule, ALLOW, drop))


# f19-declarative-list (issue F15): any recommendation to make the principles a skill, inflected or nominal, or a
# claim that they are a procedure.
CL = r'(?:[^\n.;!?]|[.;!?](?=\S))'  # a character inside one sentence (a colon doesn't end it)
SKILL_VERB = (r'\b(?:add|creat|mak|turn|convert|mov|wrap|extract|packag|writ|promot|split|consider|refactor|rewrit'
              r'|restructur|reshap|put|break)\w*')
SKILL_CLAIM = (r'(?:' + SKILL_VERB + CL + r'{0,60}?principles' + CL + r'{0,60}?\bskills?\b'
               r'|' + SKILL_VERB + CL + r'{0,40}?\bskills?\b' + CL + r'{0,60}?principles'
               r'|\bskills?\b' + CL + r'{0,30}?\b(?:for|from|of|with|covering)\b' + CL + r'{0,40}?principles'
               r'|principles[\x60*"]{0,2}[ \t]+skills?\b'
               r'|\b(?:as|into)[ \t]+(?:a|an|its[ \t]+own)[ \t]+(?:\S+[ \t]+)?skill\b'
               r'|\ba[ \t]+skill[ \t]+(?:would|could|will|can|might|should)\b'
               r'|\b(?:needs?|deserves?|warrants?|should[ \t]+(?:be|become|have)|belongs?[ \t]+in|benefit\w*[ \t]+from)'
               r'[ \t]+(?:a[ \t]+|an[ \t]+|its[ \t]+own[ \t]+)?(?:(?!(?:no|not)\b)\S+[ \t]+)?(?:skill|slash[ \t]+command)\b'
               r'|principles' + CL + r'{0,60}?\b(?:is|are|reads?[ \t]+(?:like|as)|looks?[ \t]+like|counts?[ \t]+as'
               r'|works?[ \t]+as)[ \t]+(?:a[ \t]+|an[ \t]+)?(?:\S+[ \t]+)?procedur\w*'
               r'|procedur\w*[ \t]+(?:in|at|from)[ \t]+\x60?(?:docs/)?principles'
               r'|\.claude/(?:skills|commands)/[\w-]*principl|(?:^|[ \t\x60(])/principles\b)')
SKILL_NEGATED = (r'(?:skills?|procedur\w*|commands?|add\w*|creat\w*|mak\w*|turn\w*|convert\w*|mov\w*|wrap\w*'
                 r'|extract\w*|packag\w*|writ\w*|promot\w*|split\w*|consider\w*|needs?|deserves?|warrants?)\b')


def principles_skill(drop=frozenset()):
    return free_of(SKILL_CLAIM, SKILL_NEGATED, drop, '' if 'principles' in drop else has('principles'))


DOC_SCRIPT = ('Script-graded{flags}. The parts, and the controls each must pass and fail, are in '
              '`tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py '
              '--write`. A line never counts when it is a `Source:` citation line{line_rules}.')
LINE_RULES = (' or says the change was left out of the plan ("I left it out of the plan", "not recommended", '
              '"declined"). The finding\'s parts must sit in one clause of one sentence that no negation, "rather '
              'than" or "instead of" governs ("Don\'t add X", "No command needs one, including X"); a clause ends at '
              '`.` `;` `!` `?` before a space, at "and", "but", "then", "so", "while" or "whereas" (unless a '
              'backticked name follows, as in a list) or at a spaced dash. The sentence must not be a question '
              '("why not", or `?` before a space) or hypothetical or optional ("would do it", "could", "might", "you '
              'could … if you want", "If the repo had …", a sentence that opens with "If", "optional"), and must not '
              'say the fix is already in place. A hypothetical or question in another sentence of the line doesn\'t '
              'count against it')
FENCE = ('A fenced block counts when it opens the report or its intro line (the last non-blank line before the fence) '
         'isn\'t negated, hypothetical or declined.')

GRADERS = {
    'f14-enforcement': [
        ('finding-ask-merge', ask_rule, (r'gh[ \t]+pr[ \t]+merge',), 'i', '',
         'CLAUDE.md says never to merge to main without a human approving the pull request (`gh pr merge`), but '
         '`.claude/settings.json` has no `ask` or `deny` rule, so the gate is prose only.\n\nPASS when the report '
         'adds an ask rule for the command: a fenced JSON `"ask": [...]` array holding `"Bash(gh pr merge`, or a '
         'sentence with "ask" (or `permissions.ask`) and `Bash(gh pr merge` where a recommending word (add, put, '
         'move, use, set, create, include, list, register, gate, require, should, recommend, or Claudit\'s "Change"; '
         'not the "gate" in "human-gate", and not "add nothing") shares a clause with the rule or with "one", "it" '
         'or "them", as in "No ask rule covers `Bash(gh pr merge:*)`; add one." ' + FENCE),
        ('finding-ask-deploy', ask_rule, (r'(?:\./)?bin/deploy',), 'i', '',
         'CLAUDE.md says never to deploy to production without a human go-ahead, and `bin/deploy` has no `ask` '
         'rule.\n\nPASS when the report adds an ask rule for `Bash(bin/deploy` (or `./bin/deploy`), in a fenced '
         '`"ask"` array or a recommending sentence, as for `finding-ask-merge`.'),
        ('finding-ask-release', ask_rule, (r'(?:\./)?bin/release',), 'i', '',
         'CLAUDE.md says a release needs a human go-ahead before `bin/release` runs, and nothing asks.\n\nPASS when '
         'the report adds an ask rule for `Bash(bin/release` (or `./bin/release`), in a fenced `"ask"` array or a '
         'recommending sentence, as for `finding-ask-merge`.'),
        ('finding-branch-protection', branch_protection, (), 'i', '',
         'An ask rule only prompts in Claude Code; the gate on main that holds for everyone is branch protection on '
         'the host.\n\nPASS when one clause names branch protection (also "protected branch", "branch rules", '
         '"ruleset" or "required reviews") with what it does as the gate: gate, enforce, the real/only/actual '
         'gate or control, server-side, bypass, backstop, guarantee, block/prevent/stop … merges, require … '
         'approval/reviews/status checks; or "branch protection, which is <the gate>" with no negation in the '
         'relative clause. "Rather than branch protection" or "only matters for humans" doesn\'t count.'),
        ('finding-commit-hook', commit_hook, (), 'i', '',
         'CLAUDE.md says "You must run `bin/check` before every commit", and no hook runs it.\n\nPASS when the '
         'report adds a hook that runs `bin/check`: a fenced JSON `"PreToolUse"` or `"Stop"` block, then '
         '`bin/check` in it or in a script it names before the next heading or column-0 numbered item; or a '
         'sentence naming `bin/check` where add, create, install, wire, use, set up, register, configure, enforce '
         'or "Change" shares a clause with a hook word. Or the report gives the reason for not adding one: a line '
         'about `bin/check` or commits that says no hook is being added ("I didn\'t add a hook", "no hook is '
         'needed", "skip the hook", "instead of a hook", "a hook isn\'t worth it") and then gives a reason with '
         'because, since, as or given. A problem statement ("No hook runs `bin/check`: commits can skip it") is '
         'neither. Any hook that runs the check counts, as the issue asks for "a hook". ' + FENCE),
    ],
    'f15-context-economy': [
        ('finding-always-loaded-table', always_loaded_table, (), 'i', '',
         '`CLAUDE.md` is 10 lines but about 610 words, because its lines are long, and it imports '
         '`@docs/architecture.md` (about 415 words), so about 1,000 words load every session.\n\nPASS when the '
         'report has a Markdown table whose header names words or tokens, with a row naming `CLAUDE.md` and a row '
         'naming `architecture.md`, each holding a number. The numbers themselves are not checked.'),
        ('finding-visible-skill', visible_skill, (), 'i', '',
         '`.claude/skills/schema-rules/SKILL.md` is read only by the `migrator` subagent (by path), but it is '
         'model-invocable, so its description loads in every session.\n\nPASS when the report hides it: a sentence '
         'naming `schema-rules` where set, add, put, mark, use, give, turn on, enable or "Change" shares a clause '
         'with `disable-model-invocation` (not set to false); a fenced frontmatter snippet with `name: '
         'schema-rules` and `disable-model-invocation: true`; or a sentence naming `schema-rules` where move, '
         'inline, fold, merge, put or copy shares a clause with the `migrator` subagent. `user-invocable: false` '
         'keeps the description loaded and does not count. ' + FENCE),
        ('finding-duplicates-grouped', duplicates_grouped, (), 'i', '',
         'The rule "Never edit files under `migrations/` by hand; create a new one with `bin/migrate new <name>`." '
         'is word for word in `CLAUDE.md`, `docs/contributing.md` and `.claude/agents/migrator.md`, and '
         'paraphrased in the `schema-rules` skill and `docs/architecture.md`.\n\nPASS when a line names the '
         'duplication (duplicate, repeat, copy, word for word, verbatim, identical, restate, same rule, "3 '
         'files") and, from that line on (up to 900 characters, not past a heading), the report names the '
         'migrations rule, `CLAUDE.md`, `contributing.md` and `migrator.md`, with no negation governing a '
         'duplication word in that stretch. The first line carries the usual guards.'),
    ],
    'f16-stale-facts': [
        ('finding-stale-folder', stale, (r'carriers/',), 'i', '',
         '`CLAUDE.md` says `src/labelmaker/carriers/` holds one module per carrier; the folder does not exist.\n\n'
         'PASS when one clause names `carriers/` and says it is missing (doesn\'t exist, no longer exists, '
         'nonexistent, missing, absent, stale, outdated, out of date, wrong, incorrect, false, gone, no such, not '
         'present/found/there, not in the repo/tree), or the sentence names it and says "none of them exists".'),
        ('finding-stale-file', stale, (r'rates\.toml',), 'i', '',
         '`CLAUDE.md` says carrier rates load from `config/rates.toml`; the file does not exist (rates are '
         'constants in `label.py`).\n\nPASS when the report says `rates.toml` is missing, as for '
         '`finding-stale-folder`.'),
        ('finding-stale-dependency', stale, (r'reportlab',), 'i', '',
         '`CLAUDE.md` says labels render through `reportlab`, pinned in `pyproject.toml`; the project has no '
         'dependencies.\n\nPASS when the report says `reportlab` is missing or not a (declared, listed, '
         'installed) dependency, as for `finding-stale-folder`.'),
        ('structure-alignment-below-a', lambda drop=frozenset(): ALIGNMENT_BELOW_A, (), '', '',
         'Alignment is not A while `CLAUDE.md` states false facts (issue #192).\n\nScript-graded (case-sensitive): '
         'a grade `**Alignment: B**` to `**Alignment: F**`. A report without grades fails.'),
    ],
    'f17-scope': [
        ('finding-parent-noted', parent_noted, (), 'i', '',
         'The repo sits in a folder with its own `CLAUDE.md` and `AGENTS.md`, which load with it but are not the '
         'repo\'s.\n\nPASS when one clause mentions the files above (parent, above, enclosing, ancestor, outside '
         'the repo, containing folder, `../`, home folder, higher up) and names `CLAUDE.md` or `AGENTS.md`.'),
        ('finding-symlink-real-path', symlink_real_path, (), 'i', '',
         'The repo\'s `CLAUDE.md` is a symlink to its `AGENTS.md`.\n\nPASS when one clause names `CLAUDE.md` and '
         'the link (symlink, symbolic link, links to, points to/at, `->`, an arrow, resolves to, alias) and the '
         'sentence names `AGENTS.md`. A proposal to make one (make, turn, convert, replace, change, create, '
         'should, `ln -s` before the link word) does not count: it says the file isn\'t a link already.'),
        ('no-invented-agents-md-missing', agents_md_missing, (), 'i', 'not_contains',
         'The repo has an `AGENTS.md` (the real file behind `CLAUDE.md`).\n\nMust not match: a line that says '
         '`AGENTS.md` is missing, absent, not present/there/found or isn\'t present/there/found, doesn\'t exist, '
         '"`AGENTS.md`: not found", "no/missing/without `AGENTS.md`" at the end of a clause or before file/exists/'
         'is present/in, or creates, adds or writes an `AGENTS.md`. A negated clause (a negation, up to two words, '
         'then create, add, write, missing or absent, to the end of the clause) is skipped, so "no need to create '
         'an AGENTS.md" passes while a later claim on the same line still fails; "why not" is never a negation.'),
        ('finding-parent-blocks-agents', parent_blocks_agents, (), 'i', '',
         'Claude Code reads `AGENTS.md` directly only when no `CLAUDE.md` loads, and a `CLAUDE.md` in a parent '
         'folder counts, so for anyone who has this parent the repo\'s `AGENTS.md` isn\'t read on its own (issue '
         '#192 F13).\n\nPASS when one clause names `CLAUDE.md` and the effect (stops, prevents, blocks, shadows, '
         'suppresses, overrides, masks, isn\'t / won\'t be / never read, loaded or used, no longer read, ignored, '
         'skipped) and the sentence names the parent (as in `finding-parent-noted`) and `AGENTS.md`, unless it '
         'says the parent does not (won\'t, never, can\'t) stop, prevent, block or affect it.'),
        ('no-invented-parent-findings', parent_findings, (), 'i', 'not_contains',
         'Only in-repo files are graded. The parent\'s `CLAUDE.md` and `AGENTS.md` name `bin/legacy-build`, '
         'which exists nowhere.\n\nMust not match: a line naming `legacy-build` with a fix word (fix, update, '
         'remove, delete, replace, correct, change, rewrite, drop) that no negation directly governs, or naming '
         'it as missing (as in `finding-stale-folder`, "gone" included) without a scope note (out of scope, outside '
         'the repo, not graded, not part of, excluded, not audited, above the repo).'),
    ],
    'f18-check-commands': [
        ('finding-check-allowlist', check_allowlist, (), 'i', '',
         'The check is defined only in `package.json` (`"check": "bun run lint && bun run typecheck && bun '
         'test"`) and CI (`bun run check`); `CLAUDE.md` says only "use bun run", and there is no settings '
         'file.\n\nPASS when the report allowlists the check: a fenced JSON `"allow": [...]` array holding '
         '`"Bash(bun run check`, or a sentence with allow (allowlist, pre-approve, permissions) and `Bash(bun run '
         'check` where a recommending word shares a clause with the rule or with "one", "it" or "them", as for '
         '`finding-ask-merge`. `Bash(bun run:*)` alone does not name the check and does not count. ' + FENCE),
    ],
    'f19-declarative-list': [
        ('no-invented-principles-skill', principles_skill, (), 'i', 'not_contains',
         '`docs/principles.md` is a numbered list of standing principles with no imperative verbs or sequence '
         'words. It is not a procedure, so no skill is needed (issue #192 F15, a false-defect grader like F4).\n\n'
         'Must not match, on a line naming the principles: a verb in any form (add, create, make, turn, convert, '
         'move, wrap, extract, package, write, promote, split, consider, refactor, rewrite, restructure, reshape, '
         'put, break) and "skill" in one sentence with the principles; "skill for/from/of/with … principles"; '
         '"a `principles` skill"; "as/into a skill"; "a skill would/could/will/can/might/should"; needs, deserves, '
         'warrants, should be, belongs in or benefits from a skill or slash command; the principles called a '
         'procedure (is, are, reads like/as, looks like, counts as, works as … procedure) or "procedure in '
         '`docs/principles`"; or a `.claude/skills/` or `.claude/commands/` path, or a `/principles` command, for '
         'them. A negated clause ("not a procedure", "no skill is needed", "don\'t turn it into a skill") is '
         'skipped; "why not" is never a negation. "Skills are for procedures" doesn\'t count.'),
    ],
}


def built(case):
    """(name, pattern, flags, match, doc) for each #192 grader of a case."""
    out = []
    for name, build, args, flags, match, doc in GRADERS[case]:
        pattern = build(*args)
        rules = '' if match or name.startswith('structure-') or name == 'finding-always-loaded-table' else LINE_RULES
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
        '- Turn on a ruleset for `main` that requires review before a merge.',
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

def fenced(intro, body):
    return '%s\n```json\n%s\n```' % (intro, body)


ASK_BLOCK = '{"permissions": {"ask": ["Bash(%s:*)"]}}'
ALLOW_BLOCK = '{"permissions": {"allow": ["Bash(bun run check)"]}}'
HOOK_BLOCK = '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "bin/check"}]}]}}'


def ask_attacks(cmd):
    rule = '`Bash(%s:*)`' % cmd
    return ([
        '- No ask rule covers %s; add one.' % rule,  # review L5: problem, then fix
        # Smoke a9fd63c (plain): a hypothetical in the next sentence doesn't hide the recommendation.
        '- **Permissions:** add `ask` or `deny` rules for `Bash(bin/deploy production*)`, `Bash(bin/release*)`, '
        '`Bash(gh pr merge*)` and `Bash(git push*)`. Use `deny` if the agent should never run these, and `ask` if you '
        'want to approve them case by case.',
        fenced('Change: add to `.claude/settings.json`:', ASK_BLOCK % cmd),
        '```json\n%s\n```' % (ASK_BLOCK % cmd),
    ], [
        # Direct negation of the line form (review M1).
        '- Don\'t add %s to the ask list.' % rule,
        '- Never put %s in ask.' % rule,
        # A negation earlier in the sentence.
        '- No command needs an ask rule, including %s.' % rule,
        '- None of the gates should get an ask rule, including %s.' % rule,
        # Hypothetical or optional (review M2).
        '- A `deny` or `ask` rule for %s would do it; I didn\'t add it to the plan.' % rule,
        '- If you want the gate enforced, you could add an ask rule for %s.' % rule,
        '- Optionally, add %s to `permissions.ask`.' % rule,
        # Declined in the plan.
        '- I left %s out of the plan; add it to ask yourself.' % rule,
        '- Add %s to ask: not recommended here.' % rule,
        # The block form, with each framing on its intro line.
        fenced('Don\'t add this to `.claude/settings.json`:', ASK_BLOCK % cmd),
        fenced('If you want, you could add:', ASK_BLOCK % cmd),
        fenced('I left this out of the plan:', ASK_BLOCK % cmd),
        # Mutation check for the rule part: a pronoun with no rule on the line.
        '- Add an ask rule for it.',
    ])


ATTACKS = {
    'finding-ask-merge': ask_attacks('gh pr merge'),
    'finding-ask-deploy': ask_attacks('bin/deploy'),
    'finding-ask-release': ask_attacks('bin/release'),
    'finding-branch-protection': ([
        '- Branch protection on `main` enforces review for everyone.',
    ], [
        '- Branch protection enforces review; I left it out of the plan.',
        '- Branch protection that enforces reviews isn\'t needed.',
        '- Don\'t rely on branch protection to enforce reviews.',
        '- Never treat branch protection as the real gate.',
        '- No gate is needed here, including branch protection that enforces review.',
        '- Branch protection could enforce reviews if you want.',
        '- If the repo had branch protection, it would be the real gate.',
        '- Branch protection would be the real gate; I left it out of the plan.',
        # Review L3: inverted claims.
        '- Branch protection only matters for humans; the ask rule is the real gate.',
        '- Rely on the ask rule rather than branch protection, which only slows you down.',
        '- Ask rules don\'t replace branch protection, which is not the real gate.',
    ]),
    'finding-commit-hook': ([
        '- Skip the hook for `bin/check`, because CI already runs it on every pull request.',
    ], [
        '- Adding a PreToolUse hook that runs `bin/check` would help.',
        # Review M3: a problem statement is not a reason for leaving a hook out.
        '- No hook runs `bin/check`: commits can skip it.',
        '- Problem: no hook runs `bin/check`; a commit can skip it.',
        '- There is no hook enforcing `bin/check`, which means the rule is prose only.',
        '- No hook for the commit rule: CI runs `bin/check` on every pull request.',
        # The hook line form, negated, hypothetical and declined.
        '- Don\'t add a PreToolUse hook that runs `bin/check`.',
        '- Never install a pre-commit hook for `bin/check`.',
        '- Nothing here needs a hook, including one that runs `bin/check`.',
        '- You could add a PreToolUse hook for `bin/check` if you want, but it is not in the plan.',  # review M2
        '- If commits mattered more, a Stop hook running `bin/check` would help.',
        '- Add a Stop hook that runs `bin/check`: I left it out of the plan.',
        # The block form.
        fenced('Don\'t add this hook:', HOOK_BLOCK),
        fenced('You could add this if you want:', HOOK_BLOCK),
        fenced('Declined, so not in the plan:', HOOK_BLOCK),
    ]),
    'finding-visible-skill': ([
        '- Mark `schema-rules` with `disable-model-invocation: true`.',
    ], [
        '   Source: set `disable-model-invocation: true` on `schema-rules`',
        '- Should you set `disable-model-invocation: true` on `schema-rules`?',
        '- `schema-rules` already has `disable-model-invocation: true` set.',
        '- Don\'t set `disable-model-invocation` on `schema-rules`.',
        '- No skill needs `disable-model-invocation`, including `schema-rules`.',
        '- You could set `disable-model-invocation: true` on `schema-rules` if you want.',
        '- Setting `disable-model-invocation: true` on `schema-rules` is optional.',
        '- Set `disable-model-invocation: true` on `schema-rules`: not in the plan.',
        '- `schema-rules` uses `disable-model-invocation`.',
        fenced('Don\'t change the frontmatter to:', 'name: schema-rules\ndisable-model-invocation: true'),
        fenced('If you want, you could use:', 'name: schema-rules\ndisable-model-invocation: true'),
        '- Never move `schema-rules` into the migrator subagent.',
        '- You could move `schema-rules` into the migrator subagent.',
    ]),
    'finding-duplicates-grouped': ([], [
        '   Source: the migrations rule is duplicated in `CLAUDE.md`, `docs/contributing.md`, `migrator.md`',
        '- Is the migrations rule duplicated in `CLAUDE.md`, `docs/contributing.md` and `migrator.md`?',
        '- No rule is repeated, including the migrations rule in `CLAUDE.md`, `docs/contributing.md` and '
        '`migrator.md`.',
        '- If the migrations rule were copied into `CLAUDE.md`, `docs/contributing.md` and `migrator.md`, it '
        'would drift.',
        '- The migrations rule is duplicated in `CLAUDE.md`, `docs/contributing.md` and `migrator.md`; I left it '
        'out of the plan.',
    ]),
    'finding-stale-folder': ([
        '- Missing from the repo: `src/labelmaker/carriers/`.',
    ], [
        # Review M5.
        '- `src/labelmaker/carriers/` exists and nothing in it is stale.',
        '- No paths in CLAUDE.md are stale, including `carriers/`.',
        '- `src/labelmaker/carriers/` would be stale if someone deleted it.',
        '- `src/labelmaker/carriers/` might be missing.',
        '- `src/labelmaker/carriers/` is stale, but I left it out of the plan.',
    ]),
    'finding-stale-file': ([
        '- `config/rates.toml` is gone.',
    ], [
        '- `config/rates.toml` is missing, but I left it out of the plan.',
        '- None of `config/rates.toml`, `carriers/` or `reportlab` is wrong.',  # review M5
        '- `config/rates.toml` doesn\'t look stale.',
        '- `config/rates.toml` could be missing.',
    ]),
    'finding-stale-dependency': ([], [
        '- `reportlab` is not a declared dependency; not in the plan.',
        '- `reportlab` is declared in `pyproject.toml`; no dependency is missing.',  # review M5
        '- Never call `reportlab` missing: it is in `pyproject.toml`.',
        '- If `reportlab` were missing, labels would fail.',
    ]),
    'finding-parent-noted': ([], [
        '- The parent folder\'s `CLAUDE.md` loads too; I left it out of the plan.',
        '- Nothing loads from the parent folder\'s `CLAUDE.md`.',
        '- If there were a `CLAUDE.md` above the repo, it would load.',
        '- The parent `CLAUDE.md` could matter, but I left it out of the plan.',
    ]),
    'finding-symlink-real-path': ([], [
        '- `CLAUDE.md` is a symlink to `AGENTS.md`; I left that out of the plan.',
        '- Make `CLAUDE.md` a symlink to `AGENTS.md`.',  # review L2
        '- `CLAUDE.md` should link to `AGENTS.md` so they never drift.',  # review L2
        '- Never treat `CLAUDE.md` as a symlink to `AGENTS.md`.',
        '- If `CLAUDE.md` were a symlink to `AGENTS.md`, nothing would drift.',
    ]),
    'no-invented-agents-md-missing': ([], [
        '- `AGENTS.md` isn\'t present.',  # review L1
        '- `AGENTS.md`: not found.',  # review L1
        '- `AGENTS.md` isn\'t there.',  # review L1
    ]),
    'finding-parent-blocks-agents': ([], [
        '- The parent `CLAUDE.md` is ignored, and it can\'t stop `AGENTS.md` loading.',
        '- If the parent had a `CLAUDE.md`, it would stop `AGENTS.md` being read.',  # review M2
        '- The parent `CLAUDE.md` never stops `AGENTS.md` loading.',
        '- The parent `CLAUDE.md` might stop `AGENTS.md` being read.',
        '- The parent `CLAUDE.md` stops `AGENTS.md` being read; I left it out of the plan.',
    ]),
    'no-invented-parent-findings': ([], [
        '- `bin/legacy-build` is gone.',  # review L4
    ]),
    'finding-check-allowlist': ([
        '- No allow rule covers `Bash(bun run check)`; add one.',
        fenced('Change: create `.claude/settings.json`:', ALLOW_BLOCK),
    ], [
        '- Adding `Bash(bun run check)` to allow would help.',
        '- Add `Bash(bun run check)` to allow; it is already allowed.',
        '- Don\'t add `Bash(bun run check)` to `permissions.allow`.',  # review M1
        '- Never add `Bash(bun run check)` to the allow list.',  # review M1
        '- No command should be allowlisted, including `Bash(bun run check)`.',
        '- You could add `Bash(bun run check)` to allow if you like, but I left it out.',  # review M2
        '- Allowing `Bash(bun run check)` would help.',
        '- Add `Bash(bun run check)` to allow: declined by the project.',
        fenced('Don\'t create this:', ALLOW_BLOCK),
        fenced('If you want, you could add:', ALLOW_BLOCK),
        '- Add an allow rule for it.',
    ]),
    # F15 both ways (review M4).
    'no-invented-principles-skill': ([
        '   Source: [Skills](https://code.claude.com/docs/en/skills): turn the principles into a skill',
        '- `docs/release.md` needs a skill.',
        '- Keep `docs/principles.md` as is; skills are for procedures.',
        '- `docs/principles.md` reads as rules, unlike the release procedure in `docs/release.md`.',
        '- No skill is needed for the principles.',
        '- The principles aren\'t a procedure, so leave them in `docs/principles.md`.',
    ], [
        '- Consider creating a skill from the principles.',
        '- Consider making the principles a skill.',
        '- `docs/principles.md` could be packaged as a skill.',
        '- The principles in `docs/principles.md` would work well as a skill.',
        '- A `principles` skill would load only when needed.',
        '- `docs/principles.md` is always loaded; a skill would cut that.',
        '- Convert to a skill: `docs/principles.md`.',
        '- Moving `docs/principles.md` into `.claude/skills/principles/SKILL.md` saves context.',
        '- Writing the principles up as a skill would help.',
    ]),
}
for _name, (_passing, _failing) in ATTACKS.items():
    CONTROLS[_name][0].extend(_passing)
    CONTROLS[_name][1].extend(_failing)

# Each named part a builder can drop: the control it must flip is in CONTROLS. structure-alignment-below-a has none.
LINE_PARTS = ('source', 'question', 'hypothetical', 'declined', 'claim')
MUTATIONS = {
    'finding-ask-merge': LINE_PARTS + ('already', 'neg-after', 'rule', 'intro'),
    'finding-ask-deploy': LINE_PARTS + ('already', 'rule', 'intro'),
    'finding-ask-release': LINE_PARTS + ('already', 'rule', 'intro'),
    'finding-branch-protection': LINE_PARTS + ('already', 'neg-after', 'which'),
    'finding-commit-hook': LINE_PARTS + ('already', 'neg-after', 'reason-shape', 'intro'),
    'finding-always-loaded-table': ('units', 'claude-row', 'import-row'),
    'finding-visible-skill': LINE_PARTS + ('already', 'not-false', 'intro'),
    'finding-duplicates-grouped': ('source', 'question', 'hypothetical', 'declined', 'neg', 'contributing',
                                   'migrator'),
    'finding-stale-folder': LINE_PARTS,
    'finding-stale-file': LINE_PARTS,
    'finding-stale-dependency': LINE_PARTS,
    'finding-parent-noted': LINE_PARTS,
    'finding-symlink-real-path': LINE_PARTS + ('proposal',),
    'no-invented-agents-md-missing': ('source', 'skip-negated'),
    'finding-parent-blocks-agents': LINE_PARTS + ('denied',),
    'no-invented-parent-findings': ('source', 'skip-negated', 'scope'),
    'finding-check-allowlist': LINE_PARTS + ('already', 'rule', 'intro'),
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
