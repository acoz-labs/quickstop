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
JOIN = (r'[ \t]+and[ \t]+(?![\x60*"]|Bash\()|[ \t]+(?:but|then|so|while|whereas)[ \t]+'
        r'|[ \t]+[—–-][ \t]+')
CEND = r'[.;!?](?=[ \t*_)"\x60]|\n|(?![\s\S]))|' + JOIN
IMPER = (r'(?:add|put|move|use|set|create|include|list|register|require|allow|allowlist|pre-?approve|approve'
         r'|install|wire|configure|enable|mark|give|turn|enforce|gate|inline|fold|merge|copy|fix|remove|delete'
         r'|update|replace|drop|record|document|make|change|protect)')
CSTART = r';[ \t]+|:[ \t]+(?=(?:\*\*)?%s\b)|' % IMPER + JOIN
# A character inside one sentence: . ! ? end it only before a space or the end (not inside a file name).
SENT = r'(?:[^\n.!?]|[.!?](?=[^\s*_)"\x60]))'
SOURCE = r'(?![ \t]*(?:[-*>][ \t]+)?(?:\*\*|_)?Sources?\b)'
QUESTION = r'(?!%s*?(?:\bwhy[ \t]+not\b|\?(?=[ \t*_"\x60)]|\n|(?![\s\S]))))' % SENT
# Hypothetical or optional framing: "would do it", "you could", "if you want", "If the parent had".
HYPO_P = (r'(?:[.;:!?][ \t]+if\b|\bif[ \t]+(?:you|we|they|needed|wanted|desired|preferred|so|there[ \t]+(?:were|was)|it[ \t]+(?:were|had))\b'
          r'|\bif\b[^\n]{0,40}?\bhad\b|\bunless\b|\bwhether\b|\b(?:could|might)\b|\bwould[ \t]+(?:\S+[ \t]+)?(?:do|work'
          r'|help|fix|cover|be|suffice|stop|catch|gate|hold|need|go)\b|\boptional(?:ly)?\b|\bnice[ -]to[ -]have\b)')
# A line or sentence that opens with "If" is a hypothetical too.
HYPOTHETICAL = r'(?![ \t]*(?:[-*+>]|[0-9]+[.)])?[ \t]*(?:\*\*|_)?if\b)(?!%s*?%s)' % (SENT, HYPO_P)
# Declined from the plan: "I didn't add it to the plan", "left it out", "not recommended".
DECLINED_P = (r'(?:\b(?:not|n%st)[ \t]+(?:\S+[ \t]+){0,4}?(?:in|into|to|part[ \t]+of|on)[ \t]+(?:the|my|this)[ \t]+plan\b'
              r'|\bleft[ \t]+(?:\S+[ \t]+){0,2}?out\b|\bout[ \t]+of[ \t]+(?:the[ \t]+)?plan\b|\bnot[ \t]+(?:planned'
              r'|recommended|recommending|proposing|included)\b|\bdeclin\w*)' % Q)
DECLINED = r'(?![^\n]*%s)' % DECLINED_P
# A sentence that rejects the change or reports someone else's advice: "this repo doesn't need it", "that is wrong
# here", "Hold off on …", "Some teams add …", "A previous audit said …", "I expected X to be stale", and colon intros
# such as "Not needed:" or "Don't do this:".
REJECT_P = (r'(?:\b(?:doesn%(q)st|does[ \t]+not|don%(q)st|do[ \t]+not)[ \t]+need[ \t]+(?:it|this|that|one|them)\b'
            r'|\b(?:it|this|that)(?:[ \t]+(?:is|was)|%(q)ss)[ \t]+(?:wrong|unnecessary|overkill|fine|not[ \t]+needed)\b'
            r'|\bhold[ \t]+off\b|\b(?:some|other)[ \t]+(?:teams|projects|repos)\b|\ba[ \t]+previous\b'
            r'|\b(?:expected|assumed|thought|suspected|feared)\b[^\n.!?]{0,60}?\bto[ \t]+be\b'
            r'|\b(?:not|no|none|nothing)[ \t]+(?:\S+[ \t]+)?(?:needed|necessary|required|recommended|to[ \t]+add'
            r'|to[ \t]+do|worth[ \t]+it)\W*:|\b(?:don%(q)st|do[ \t]+not|never|avoid)[ \t]+(?:\S+[ \t]+){0,2}?(?:this'
            r'|these|that|the[ \t]+following)\W*:)' % {'q': Q})
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
    return head + r'(?:[^\n]*?[.!?][*_\x60)"]*[ \t]+)?' + rest + r'[^\n]*'


def framing(drop):
    """The guards every finding line carries."""
    return {'source': SOURCE, 'question': QUESTION, 'hypothetical': HYPOTHETICAL, 'declined': DECLINED,
            'rejected': r'(?!%s*?%s)' % (SENT, REJECT_P)}


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


# Review round 4, O3: "branch protection" (or "protected branch", "ruleset") and main, merge or review in one
# sentence, in any phrasing. A statement of the gap ("`main` has no branch protection, so anyone can merge") counts;
# a sentence that advises against it, says it isn't needed or is already in place doesn't.
BRANCH = r'(?:\bbranch[ \t-]+protections?\b|\bprotected[ \t]+branch(?:es)?\b|\brulesets?\b)'
BRANCH_WITH = r'(?:\bmain\b|\bmerg\w*|\breview\w*)'
AGAINST = (r'(?:\b(?:don%(q)st|do[ \t]+not|never|avoid|skip|no[ \t]+need[ \t]+to)[ \t]+(?:\S+[ \t]+){0,2}?(?:enabl'
           r'|add|us|set|turn|configur|requir|need|bother|rel[yi]|treat|enforc|protect|worr)\w*'
           r'|\b(?:doesn%(q)st|don%(q)st|do(?:es)?[ \t]+not|needn%(q)st)[ \t]+(?:really[ \t]+)?need\b|\bno[ \t]+need\b'
           r'|\b(?:rather[ \t]+than|instead[ \t]+of)[ \t]+(?:\S+[ \t]+){0,2}?%(branch)s|\bunnecessar\w*|\boverkill\b'
           r'|\bnot[ \t]+(?:needed|necessary|required|worth)\b'
           r'|\bno\b(?:[ \t]+\S+){0,3}?[ \t]+(?:is|are)[ \t]+(?:needed|necessary|required)\b'
           r'|\bmatters?[ \t]+(?:only[ \t]+)?for[ \t]+humans\b'
           r'|\b(?:remov|disabl|drop|turn[ \t]+off|relax|loosen)\w*[ \t]+(?:\S+[ \t]+){0,2}?%(branch)s'
           r'|%(branch)s(?:(?!%(cend)s)[^\n]){0,60}?\b(?:won%(q)st|wouldn%(q)st|doesn%(q)st|does[ \t]+not|can%(q)st'
           r'|cannot|isn%(q)st)[ \t]+(?:\S+[ \t]+)?(?:help|matter|work|apply|stop|block|prevent|cover|catch)\b)'
           % {'q': Q, 'branch': BRANCH, 'cend': CEND})


def branch_protection(drop=frozenset()):
    return line({**framing(drop), 'already': already(BRANCH), 'neg-after': neg_after(BRANCH),
                 'against': r'(?!%s*?%s)' % (SENT, AGAINST), 'with': has(BRANCH_WITH), 'claim': has(BRANCH)}, drop)


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
    header = BOL + r'[ \t]*\|%s[^\n]*\|[ \t]*\n[ \t]*\|?[ \t]*:?-+[^\n]*' % (
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
           r'(?:declared|listed|installed)\b|\b(?:declares|lists|has)[ \t]+no[ \t]+dependenc\w*|\bdependencies[ \t]*=[ \t]*\[\]'
           r'|\b(?:none|neither)\b[^\n]{0,30}\bexists?\b)' % {'q': Q})
SPAN = r'\x60[^\x60\n]*\x60'
PROOF = r'\x60(?:pyproject\.toml|CLAUDE\.md|package\.json|requirements[\w.-]*|setup\.cfg)\x60'
NONE_EXIST = (r'\b(?:none|neither)[ \t]+of[ \t]+(?:them|these|those|the[ \t]+three)[ \t]+(?:exists?|is[ \t]+(?:present'
              r'|real|there))\b')


def stale(key, drop=frozenset()):
    """The key and a missing word in one clause, with no other backticked name between them; or a later clause, or
    the next sentence, that refers back without naming anything but the file that proves it."""
    if 'claim' in drop:
        same = has(key) + has(MISSING)
    else:
        lead = r'(?:(?!%s|%s)[^\n])*?' % (NEGB, CEND)  # up to the first part
        run = r'(?:(?!%s|%s|%s)[^\n])*?' % (NEGB, CEND, SPAN)  # between the parts: no other backticked name
        same = (r'(?=(?:%s*?(?:%s))?(?:%s%s[\x60*"]*%s%s|%s%s%s(?:\x60[^\x60\n]*?)?%s))'
                % (SENT, CSTART, lead, key, run, MISSING, lead, MISSING, run, key))
    back = r'(?:%s|(?!%s|%s|\x60)[^\n])*?' % (PROOF, NEGB, CEND)  # a later clause up to the cue
    later = r'(?=%s*?%s%s*?(?:%s)%s%s)' % (SENT, key, SENT, CSTART, back, MISSING)
    next_sentence = (r'(?=%s*?%s%s*?[.!?][ \t]+(?:\*\*)?(?:that|this|the|it|those|these)\b(?:(?!%s|%s|\x60)[^\n]){0,40}?%s)'
                     % (SENT, key, SENT, NEGB, CEND, MISSING))
    refer = '(?!)' if 'refer' in drop else either(later, next_sentence)
    return line({**framing(drop), 'key': has(key), 'claim': either(same, has(NONE_EXIST), refer)}, drop)


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
                  r'|\black(?:s|ing)?[ \t]+(?:an?[ \t]+|any[ \t]+)?[\x60*"]{0,2}AGENTS\.md'
                  r'|\b(?:create|add|write)\w*[ \t]+(?:an?[ \t]+|the[ \t]+)?(?:missing[ \t]+)?[\x60*"]{0,2}AGENTS\.md)'
                  % {'q': Q})


def agents_md_missing(drop=frozenset()):
    return free_of(AGENTS_MISSING, r'(?:creat\w*|add\w*|writ\w*|missing|absent)', drop)


# Review round 4, O2: one paragraph or list item names the parent CLAUDE.md and says the repo's AGENTS.md is not
# read or loaded, in either order. A line break stays inside the unit unless a blank line, a list marker, a table row
# or a heading follows, so each table row is its own unit.
UNIT_MARK = r'[ \t]*(?:[-*+][ \t]|[0-9]+[.)][ \t]|\||#{1,6}[ \t])'
UNIT_NL = r'\n(?![ \t]*\n|%s)' % UNIT_MARK
# Where a unit starts: the text start, a line after a blank line, or a list, table or heading line. Only these are
# tried, so a long paragraph isn't rescanned from each of its lines.
UNIT_START = r'(?:^|\n(?=%s)|\n[ \t]*\n(?:[ \t]*\n)*)' % UNIT_MARK
# The parent, as in PARENT, but "above" only as a place ("the `CLAUDE.md` above", "above the repo"), not "as noted
# above".
PARENT_DIR = (r'(?:\bparent\b|\benclosing\b|\bancestor\w*|\boutside[ \t]+(?:the[ \t]+|this[ \t]+)?(?:repo\w*|project'
              r'|checkout)|\bcontaining[ \t]+(?:folder|directory)|\.\./|\bhome[ \t]+(?:folder|directory)|~/'
              r'|\bup[ \t]+the[ \t]+tree|\bhigher[ \t]+up\b|[\x60*"]{1,2}[ \t]+above\b|\babove[ \t]+(?:the'
              r'|this|your)[ \t]+(?:repo\w*|project|checkout|folder|directory|tree)\b|\b(?:folder|directory|one)'
              r'[ \t]+above\b)')
UNREAD = (r'(?:\b(?:not|never|no[ \t]+longer|isn%(q)st|aren%(q)st|wasn%(q)st|won%(q)st[ \t]+be|wouldn%(q)st[ \t]+be'
          r'|can%(q)st[ \t]+be|doesn%(q)st[ \t]+get)[ \t]+(?:\S+[ \t]+)?(?:read|loaded|picked[ \t]+up|used|seen)\b'
          r'|\b(?:never|doesn%(q)st|does[ \t]+not|won%(q)st|will[ \t]+not|can%(q)st|cannot|no[ \t]+longer|don%(q)st'
          r'|do[ \t]+not)[ \t]+(?:\S+[ \t]+)?(?:reads?|loads?|picks?[ \t]+up|uses?|sees?|looks?[ \t]+at|opens?)\b'
          r'|\b(?:stops?|stopping|prevents?|blocks?|shadow\w*|suppress\w*|overrid\w*|overrode|masks?|masked|hides?'
          r'|hidden|ignored|skipped|unread)\b|\binstead[ \t]+of\b|\bonly[ \t]+when[ \t]+no\b)' % {'q': Q})
# A sentence about a parent AGENTS.md ("the parent `AGENTS.md` isn't read") is not about the repo's.
PARENT_AGENTS = (r'(?:\.\./|~/|\b(?:parent|ancestor|enclosing|workspace|outer|home)\w*(?:%s?s)?[ \t]+(?:(?:folder'
                 r'|directory)(?:%ss)?[ \t]+)?)[\x60*"]{0,2}AGENTS\.md' % (Q, Q))


def parent_blocks_agents(drop=frozenset()):
    unit_nl = r'\n' if 'unit' in drop else UNIT_NL
    uchar = r'(?:[^\n]|%s){0,4000}?' % unit_nl
    named = r'(?:%s%s*?CLAUDE\.md|CLAUDE\.md%s*?%s)' % (PARENT_DIR, SENT, SENT, PARENT_DIR)
    parent = '' if 'parent' in drop else r'(?=%s%s)' % (uchar, named)
    said = line({**framing(drop), 'repo-agents': r'(?!%s*?%s)' % (SENT, PARENT_AGENTS),
                 'claim': claim(r'AGENTS\.md', UNREAD, drop)}, drop)
    return (BOL if 'unit' in drop else UNIT_START) + parent + r'(?:%s%s)?' % (uchar, unit_nl) + said[len(BOL):]


FIX = r'\b(?:fix|update|remove|delete|replace|correct|change|rewrite|drop|point|repoint|rename|redirect)\w*\b'
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
ALLOW_VERB = (r'(?:\b(?:add|adding|put|create|include|use|using|set|Change|allowlist|pre-?approve|approve)\b'
              r'|\ballow\b(?![\x60"\x27.]))')


def check_allowlist(drop=frozenset()):
    rule = r'Bash\([ \t]*bun[ \t]+run[ \t]+check\b'
    return either(block(r'"allow"[ \t]*:[ \t]*\[[^\]]*?"' + rule, drop), recommended(ALLOW_VERB, rule, ALLOW, drop))


# f19-declarative-list (issue F15), review round 4, O1: a false defect only when a numbered item of the report's
# changes proposes a skill for the principles. Items under a set-aside heading ("Also worth knowing", "Declined",
# "Optional", "Not recommended", ...), items whose title is optional or a decline, bullets and prose never count, and
# a clause with negation or decline wording ("a skill would add nothing", "a skill would be overkill") never counts.
HEADING = r'(?:#{1,6}[ \t]|\*\*[^\n*]+\*\*:?[ \t]*(?=\n|(?![\s\S])))'  # a Markdown heading or a line of bold text
SET_ASIDE = (r'(?:\balso[ \t]+worth\b|\bdeclin\w*|\bnot[ \t]+(?:recommended|planned|changing|doing|worth)\b'
             r'|\boptional\w*|\bskip\w*|\bleft[ \t]+out\b|\bout[ \t]+of[ \t]+(?:scope|the[ \t]+plan)\b'
             r'|\balready[ \t]+good\b|\bwhat%ss[ \t]+(?:good|fine|working)\b|\bno[ \t]+changes?\b|\bconsidered\b'
             r'|\bnice[ -]to[ -]have\b)' % Q)
# An item's title (to its first sentence end or the end of its bold text) that makes it optional or a decline.
TITLE_OFF = (r'(?:\b%s\b|\boptional\w*|\bnice[ -]to[ -]have\b|\bonly[ \t]+if\b|\bif[ \t]+(?:you|needed|wanted|it)\b'
             r'|\bmaybe\b|\bkeep\b|\bleave\b|\balso[ \t]+worth\b|\bdeclin\w*)' % NEG)
TITLE = r'(?:\*\*)?(?:[^\n.!?*]|[.!?](?=\S))*?'
# A line break inside a list item: the next non-blank line is indented and isn't the next numbered item.
ITEM_NL = r'\n(?=(?:[ \t]*\n)*(?: {2,}|\t)(?![ \t]*[0-9]+[.)][ \t])\S)'
HEAD_NL = r'\n(?![ \t]*%s)' % HEADING  # inside a numbered heading's section
BOUND = (r'[.!?;](?=[ \t*_)"\x60]|\n|(?![\s\S]))|[ \t]+(?:so|because|since|but|then|while|whereas|which|though'
         r'|although)[ \t]+')
SKILL = r'(?:\bskills?\b|\bslash[ \t]+commands?\b|\.claude/(?:skills|commands)/|\bSKILL\.md\b|(?:^|[ \t\x60(])/principles\b)'
REFUSE = (r'(?:%s|\b(?:overkill|unnecessar\w*|unneeded|needless\w*|pointless|redundant|prematur\w*|declin\w*|wrong'
          r'|keep|leave|fine|already)\b|\b(?:poor|bad)[ \t]+fit\b'
          r'|\bskills[ \t]+(?:are|suit|fit|work|belong|hold|cover|should)\b)' % NEGB)


def principles_skill(drop=frozenset()):
    """A not_contains pattern for a numbered item that proposes a skill for the principles."""
    def item(marker, nl):
        ichar = r'(?:[^\n]|%s)' % nl
        cchar = ichar if 'clause' in drop else r'(?:(?!%s|\n)%s)' % (BOUND, ichar)
        bound = nl if 'clause' in drop else r'(?:%s|%s)' % (BOUND, nl)
        proposes = (('' if 'source' in drop else SOURCE) + ('' if 'refuse' in drop else r'(?!%s*?%s)' % (cchar, REFUSE))
                    + ('' if 'question' in drop else r'(?!%s*?\?(?=[ \t*_"\x60)]|\n|(?![\s\S])))' % cchar)
                    + r'%s*?%s' % (cchar, SKILL))
        return (marker + ('' if 'title' in drop else r'(?!%s%s)' % (TITLE, TITLE_OFF))
                + ('' if 'principles' in drop else r'(?=%s*?principles)' % ichar)
                + r'(?=(?:%s*?%s)?%s)' % (ichar, bound, proposes))
    # The item's section: the text start or a heading that isn't set aside, then text up to the item that crosses no
    # other heading. The section start doesn't consume the line break, so a numbered heading can be the item itself.
    aside = r'[ \t]*%s[^\n]*%s' % (HEADING, SET_ASIDE)
    first, later = ('', '') if 'section' in drop else (r'(?!%s)' % aside, r'(?!\n%s)' % aside)
    rest = r'(?:(?!\n[ \t]*%s)[\s\S])*?' % HEADING
    section = r'(?:^%s%s|(?=\n[ \t]*%s)%s(?:[\s\S]%s)?)' % (first, rest, HEADING, later, rest)
    return section + r'(?:^|\n)[ \t]{0,3}' + either(
        item(r'(?:\*\*)?[0-9]+[.)](?:\*\*)?[ \t]+', ITEM_NL), item(r'#{1,6}[ \t]+[0-9]+[.)]?[ \t]+', HEAD_NL))


DOC_SCRIPT = ('Script-graded{flags}. The parts, and the controls each must pass and fail, are in '
              '`tests/test_claudit_fixture_graders.py`; rebuild with `python3 tests/test_claudit_fixture_graders.py '
              '--write`. A line never counts when it is a `Source:` citation line{line_rules}.')
DECLINED_RULE = (' or says the change was left out of the plan ("I left it out of the plan", "not recommended", '
                 '"declined"). ')
CLAUSE_RULE = ('The finding\'s parts must sit in one clause of one sentence that no negation, "rather than" or '
               '"instead of" governs ("Don\'t add X", "No command needs one, including X"); a clause ends at `.` `;` '
               '`!` `?` before a space, at "but", "then", "so", "while" or "whereas", at "and" (unless a backticked '
               'name follows, as in a list), at a spaced dash, or at a colon before an imperative ("…, but nothing '
               'enforces it: add X"). ')
SENTENCE_RULE = ('The sentence must not be a question ("why not", or `?` before a space) or hypothetical or optional '
                 '("would do it", "could", "might", "you could … if you want", "If the repo had …", a sentence that '
                 'opens with "If", "optional"), and must not say the fix is already in place or reject the change or '
                 'report someone else\'s advice ("this repo doesn\'t need it", "that is wrong here", "Hold off on …", '
                 '"Some teams …", "A previous audit …", "I expected … to be …", "Not needed:", "Don\'t do this:"). A '
                 'hypothetical or question in another sentence of the line doesn\'t count against it')
LINE_RULES = DECLINED_RULE + CLAUSE_RULE + SENTENCE_RULE
# Review round 4: graders matched by structure and co-occurrence rather than by one clause.
STRUCTURAL = {'finding-branch-protection', 'finding-parent-blocks-agents'}
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
         'the host.\n\nPASS when one sentence names branch protection (also "protected branch" or "ruleset") and '
         '`main`, a merge or a review, in any phrasing; a statement of the gap ("`main` has no branch protection, so '
         'anyone can merge") counts. The sentence must not advise against it ("don\'t enable/rely on …", "doesn\'t '
         'need", "no need", "rather than / instead of branch protection", "remove/disable … branch protection", '
         '"unnecessary", "overkill", "not needed", "No … is needed", "matters only for humans", or "branch '
         'protection won\'t/doesn\'t help/apply/stop …" in its own clause), and must not say branch protection isn\'t '
         'needed or is already in place (review round 4, O3).'),
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
         'present/found/there, not in the repo/tree), with no other backticked name between them. A later clause '
         'of the sentence, or the next sentence, may carry the missing word when it refers back and names nothing '
         'else ("…, but that folder does not exist", "…, but there is no such folder", "That file doesn\'t '
         'exist"), except the file that proves it ("…, but `pyproject.toml` declares no dependencies"). Or the '
         'sentence names it and says "none of them exists".'),
        ('finding-stale-file', stale, (r'rates\.toml',), 'i', '',
         '`CLAUDE.md` says carrier rates load from `config/rates.toml`; the file does not exist (rates are '
         'constants in `label.py`).\n\nPASS when the report says `rates.toml` is missing, as for '
         '`finding-stale-folder`.'),
        ('finding-stale-dependency', stale, (r'reportlab',), 'i', '',
         '`CLAUDE.md` says labels render through `reportlab`, pinned in `pyproject.toml`; the project has no '
         'dependencies.\n\nPASS when the report says `reportlab` is missing or not a (declared, listed, '
         'installed) dependency, or that `pyproject.toml` declares no dependencies, as for `finding-stale-folder`.'),
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
         'is present/in, "lacks an `AGENTS.md`", or creates, adds or writes an `AGENTS.md`. A negated clause (a negation, up to two words, '
         'then create, add, write, missing or absent, to the end of the clause) is skipped, so "no need to create '
         'an AGENTS.md" passes while a later claim on the same line still fails; "why not" is never a negation.'),
        ('finding-parent-blocks-agents', parent_blocks_agents, (), 'i', '',
         'Claude Code reads `AGENTS.md` directly only when no `CLAUDE.md` loads, and a `CLAUDE.md` in a parent '
         'folder counts, so for anyone who has this parent the repo\'s `AGENTS.md` isn\'t read on its own (issue '
         '#192 F13).\n\nPASS when one paragraph or list item (a table row is its own item) names the parent '
         '`CLAUDE.md` (a sentence with `CLAUDE.md` and the parent: parent, enclosing, ancestor, outside the repo, '
         'containing folder, `../`, `~/`, home folder, higher up, "the `CLAUDE.md` above", "above the repo", not "as '
         'noted above") and says the repo\'s `AGENTS.md` is not read or loaded, in either order: one clause with '
         '`AGENTS.md` and not / never / no longer / isn\'t / won\'t be read, loaded, picked up or used, "Claude Code '
         'never reads / won\'t read / doesn\'t load / never looks at", stops, prevents, blocks, shadows, suppresses, '
         'overrides, masks, hides, ignored, skipped, unread, "instead of" or "only when no", with no negation before '
         'them in the clause (review round 4, O2). Both must be within the first 4,000 characters of the paragraph or list item. A sentence about a parent `AGENTS.md` (`../AGENTS.md`, "the parent '
         '`AGENTS.md`") doesn\'t count.'),
        ('no-invented-parent-findings', parent_findings, (), 'i', 'not_contains',
         'Only in-repo files are graded. The parent\'s `CLAUDE.md` and `AGENTS.md` name `bin/legacy-build`, '
         'which exists nowhere.\n\nMust not match: a line naming `legacy-build` with a fix word (fix, update, '
         'remove, delete, replace, correct, change, rewrite, drop, point, rename, redirect) that no negation '
         'directly governs, or naming '
         'it as missing (as in `finding-stale-folder`, "gone" included) without a scope note (out of scope, outside '
         'the repo, not graded, not part of, excluded, not audited, above the repo).'),
    ],
    'f18-check-commands': [
        ('finding-check-allowlist', check_allowlist, (), 'i', '',
         'The check is defined only in `package.json` (`"check": "bun run lint && bun run typecheck && bun '
         'test"`) and CI (`bun run check`); `CLAUDE.md` says only "use bun run", and there is no settings '
         'file.\n\nPASS when the report allowlists the check: a fenced JSON `"allow": [...]` array holding '
         '`"Bash(bun run check`, or a sentence with allow (allowlist, pre-approve, permissions) and `Bash(bun run '
         'check` where a recommending word (add, put, create, include, use, set, "Change", allowlist, pre-approve, '
         'approve, or "allow" itself, not the key in `permissions.allow`) shares a clause with the rule or with "one", "it" or "them", as for '
         '`finding-ask-merge`. `Bash(bun run:*)` alone does not name the check and does not count. ' + FENCE),
    ],
    'f19-declarative-list': [
        ('no-invented-principles-skill', principles_skill, (), 'i', 'not_contains',
         '`docs/principles.md` is a numbered list of standing principles with no imperative verbs or sequence '
         'words. It is not a procedure, so no skill is needed (issue #192 F15, a false-defect grader like F4).\n\n'
         'Must not match: a numbered item of the report\'s changes (`1.`, `**1.**` or a numbered heading such as `## '
         '2. Context`) that names the principles and proposes a skill (skill, slash command, a `.claude/skills/` or '
         '`.claude/commands/` path, `SKILL.md`, a `/principles` command) in a clause with no negation or decline '
         'wording (no, not, never, nothing, n\'t, avoid, skip, rather than, instead of, overkill, unnecessary, '
         'pointless, redundant, premature, declined, wrong, poor/bad fit, keep, leave, fine, already, "skills '
         'are/suit/fit … for") and that isn\'t a question. A clause ends at `.` `;` `!` `?` before a space, a line '
         'break, or so, because, since, but, then, while, whereas, which, though, although. An item\'s text is its '
         'first line and the indented lines under it (a numbered heading\'s runs to the next heading). Never counted: '
         'bullets and prose; items under a heading or bold line that sets them aside (Also worth knowing, Declined, '
         'Not recommended/planned, Optional, Skipped, Left out, Out of scope, Already good, What\'s good/fine, No '
         'changes, Considered, Nice to have); items whose title (to its first sentence end or the end of its bold '
         'text) is optional or a decline (optional, nice to have, only if, if you/needed, maybe, keep, leave, a '
         'negation, also worth, declined); and a `Source:` line (review round 4, O1).'),
    ],
}


def built(case):
    """(name, pattern, flags, match, doc) for each #192 grader of a case."""
    out = []
    for name, build, args, flags, match, doc in GRADERS[case]:
        pattern = build(*args)
        rules = ('' if match or name.startswith('structure-') or name == 'finding-always-loaded-table'
                 else DECLINED_RULE + SENTENCE_RULE if name in STRUCTURAL else LINE_RULES)
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
}
for _name, (_passing, _failing) in ATTACKS.items():
    CONTROLS[_name][0].extend(_passing)
    CONTROLS[_name][1].extend(_failing)

# Review round 2: the false-negative pass. For every positive grader, realistic ways a correct report phrases the
# finding, taken from the smoke and #184 gate reports where they exist: the fact first, then "but"/"and" the missing
# word; problem, then fix across a colon or semicolon; a bare imperative; a table row; a bullet with a code span; a fix
# in a fenced block with an intro line. Then the round 2 attacks.
def ask_true(cmd):
    rule = '`Bash(%s:*)`' % cmd
    return [
        '- `%s` needs a human, but nothing enforces it: add %s to `permissions.ask`.' % (cmd, rule),  # review N2
        '- The gate is prose only; add %s to the ask list.' % rule,
        '- Add %s to `permissions.ask`.' % rule,
        '| `%s` | prose only | add %s to ask |' % (cmd, rule),
        '- Ask before %s: put it in `permissions.ask`.' % rule,
        fenced('   Change: add an ask rule to `.claude/settings.json`:', ASK_BLOCK % cmd),
        '   Problem: CLAUDE.md requires a human before `%s`, and no ask rule covers it. Change: add %s to ask.' % (
            cmd, rule),
    ]


def ask_false(cmd):
    rule = '`Bash(%s:*)`' % cmd
    return [
        '- Some teams add %s to ask, but this repo doesn\'t need it.' % rule,  # review N6
        '- Hold off on adding %s to ask.' % rule,  # review N6
        '- A previous audit said to add %s to ask; that is wrong here.' % rule,  # review N6
        '- Not needed: add %s to ask.' % rule,
        '- Don\'t do this: add %s to ask.' % rule,
        '- Nothing enforces the gate; no need to add %s to ask.' % rule,
    ]


ROUND2 = {
    'finding-ask-merge': (ask_true('gh pr merge'), ask_false('gh pr merge')),
    'finding-ask-deploy': (ask_true('bin/deploy'), ask_false('bin/deploy')),
    'finding-ask-release': (ask_true('bin/release'), ask_false('bin/release')),
    'finding-commit-hook': ([
        '- The rule is prose only, so nothing runs `bin/check` before a commit: add a PreToolUse hook on '
        '`git commit` that runs it.',
        '- Add a PreToolUse hook that runs `bin/check` before `git commit`.',
        '- **Pre-commit hook:** add a `PreToolUse` hook on `Bash(git commit*)` that runs `bin/check` and blocks the '
        'commit (exit code 2) if it fails.',  # smoke (plain)
        '| must run `bin/check` | prose only | add a PreToolUse hook that runs `bin/check` |',
        plan_item(1, 'Enforce the check with a Stop hook', 'Problem: `CLAUDE.md:13` says "You must run `bin/check` '
                  'before every commit", but `.claude/settings.json` has no hooks.\nChange: add to '
                  '`.claude/settings.json`:\n```json\n{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": '
                  '"\\"$CLAUDE_PROJECT_DIR\\"/.claude/hooks/stop-check.sh"}]}]}}\n```\nand create '
                  '`.claude/hooks/stop-check.sh`, which runs `bin/check`.'),  # smoke (Claudit)
        '- I didn\'t add a hook for `bin/check`, because CI runs it on every push.',
    ], [
        '- Some teams wire a pre-commit hook to run `bin/check`, but this repo doesn\'t need it.',
        '- Not needed: add a PreToolUse hook that runs `bin/check`.',
    ]),
    'finding-always-loaded-table': ([
        '| File | Words |\n|---|---|\n| `CLAUDE.md` (10 lines) | ~610 |\n| `@docs/architecture.md` | ~415 |\n'
        '| Total | ~1,025 |',
        '| Always loaded | Lines | Est. tokens |\n|---|---:|---:|\n| CLAUDE.md | 10 | 820 |\n| docs/architecture.md '
        '| 31 | 560 |',
        '| Source | Tokens |\n| --- | --- |\n| `CLAUDE.md` | 800 |\n| `docs/architecture.md` (via `@`) | 550 |',
        '  | File | Words |\n  |---|---|\n  | `CLAUDE.md` | 610 |\n  | `docs/architecture.md` | 415 |',
        '| What loads | Words | Note |\n|:--|--:|:--|\n| `CLAUDE.md` | 610 | long lines |\n| '
        '`docs/architecture.md` | 415 | imported |',
        '| Component | Type | Est. resident tokens |\n|---|---|---|\n| `CLAUDE.md` | memory | ~800 |\n| '
        '`docs/architecture.md` | import | ~550 |',  # the /doctor table shape from the smoke
    ], []),
    'finding-visible-skill': ([
        '- `schema-rules` is read only by the migrator subagent, but its description loads every session: set '
        '`disable-model-invocation: true`.',
        '- Set `disable-model-invocation: true` in `.claude/skills/schema-rules/SKILL.md`.',
        '| `schema-rules` | read only by `migrator` | add `disable-model-invocation: true` |',
        fenced('Change: add to the `schema-rules` frontmatter:', 'name: schema-rules\ndescription: Naming rules.\n'
               'disable-model-invocation: true'),
        '- Move the rules in `schema-rules` into `.claude/agents/migrator.md` and delete the skill.',
        '- Only the subagent reads `schema-rules`; mark it with `disable-model-invocation: true`.',
    ], [
        '- Some teams set `disable-model-invocation: true` on skills like `schema-rules`, but this repo doesn\'t '
        'need it.',
    ]),
    'finding-duplicates-grouped': ([
        '- The migrations rule appears word for word in `CLAUDE.md`, `docs/contributing.md` and '
        '`.claude/agents/migrator.md`, and two more files paraphrase it.',
        '### Duplicated rule\n\n| File | Line |\n|---|---|\n| `CLAUDE.md` | 4 |\n| `docs/contributing.md` | 10 |\n'
        '| `.claude/agents/migrator.md` | 9 |\n\nThe migrations rule is the same in all three.',
        '- "Never edit files under `migrations/` by hand" is repeated in `CLAUDE.md:4`, `docs/contributing.md:10` and '
        '`migrator.md:9`; keep it in one place.',
        '1. **Remove the duplicated migrations rule** (Alignment, effort S)\n   Problem: `CLAUDE.md`, '
        '`docs/contributing.md` and `.claude/agents/migrator.md` copy the same sentence.',
        '- Same rule, 3 files: `CLAUDE.md`, `docs/contributing.md`, `migrator.md` (migrations).',
        '- The migrations rule is copied verbatim into `CLAUDE.md`, `docs/contributing.md` and `migrator.md`: keep '
        'one copy and point to it.',
    ], []),
    'finding-stale-folder': [[
        '- `CLAUDE.md` says modules live in `src/labelmaker/carriers/`, but that folder does not exist.',  # review N1
        '- `CLAUDE.md:8` points to `src/labelmaker/carriers/`, but there is no such folder.',  # review N1
        '- CLAUDE.md describes `src/labelmaker/carriers/` and the folder is missing.',  # review N1
        '- **Stale path.** `src/labelmaker/carriers/` is listed in CLAUDE.md but doesn\'t exist in the repo.',  # N1
        '   Problem: CLAUDE.md line 8 says `src/labelmaker/carriers/` holds one module per carrier. That folder '
        'doesn\'t exist, so the instruction sends Claude to nothing.',  # #184 gate shape
        '| `src/labelmaker/carriers/` | CLAUDE.md:8 | missing |',
        '- Remove the stale `src/labelmaker/carriers/` line from CLAUDE.md.',
        fenced('Change: `src/labelmaker/carriers/` doesn\'t exist; delete the line:', '- `src/labelmaker/carriers/` '
               'holds one module per carrier.').replace('```json', '```diff'),
    ], [
        '- I expected `carriers/` to be stale; it is fine.',  # review N6
        '- `src/labelmaker/carriers/` exists, but `config/rates.toml` is missing.',
        '- `src/labelmaker/carriers/` is listed in CLAUDE.md. That folder is not missing.',
    ]],
    'finding-stale-file': [[
        '- CLAUDE.md says rates load from `config/rates.toml`, but that file doesn\'t exist.',
        '- `config/rates.toml` is named in CLAUDE.md and isn\'t in the repo; rates are constants in `label.py`.',
        '- **Correctness: C** (confidence: high). `CLAUDE.md` points at `config/rates.toml`, which doesn\'t exist.',
        '| `config/rates.toml` | not found |',
        '- Fix the stale reference to `config/rates.toml`: rates live in `label.py`.',
        '   Problem: CLAUDE.md line 9 says rates load from `config/rates.toml`. That file doesn\'t exist.',
    ], [
        '- `config/rates.toml` is named in CLAUDE.md, but `carriers/` is the one that\'s missing.',
        '- I expected `config/rates.toml` to be missing; it is fine.',
    ]],
    'finding-stale-dependency': [[
        '- `reportlab` is mentioned but not listed in `pyproject.toml`.',  # review N1
        '- CLAUDE.md says labels render through `reportlab`, but `pyproject.toml` declares no dependencies.',
        '- `reportlab` is not a dependency: `pyproject.toml` has `dependencies = []`.',
        '| `reportlab` | dependency | not declared |',
        '- Remove the stale `reportlab` line; nothing imports it.',
        '   Problem: CLAUDE.md line 10 names `reportlab`. It isn\'t declared in `pyproject.toml`, so the fact is false.',
    ], [
        '- `reportlab` is declared, but `config/rates.toml` is missing.',
        '- I assumed `reportlab` would turn out to be missing; it is fine.',
    ]],
    'finding-parent-noted': ([
        '- The folder above this repo has its own `CLAUDE.md` and `AGENTS.md`; they load too but aren\'t graded.',
        '| `../CLAUDE.md` (workspace) | memory | parent dir | ~50 |',  # smoke (/doctor)
        '- Skipped: `../CLAUDE.md`, an ancestor-directory file outside the working directory.',  # smoke (audit)
        '- Note: a parent `CLAUDE.md` loads in every session started here.',
        '- `CLAUDE.md` and `AGENTS.md` in the parent folder load with this repo, but only in-repo files are graded.',
        '- Files above the repo (`../CLAUDE.md`, `../AGENTS.md`) are out of scope.',
    ], [
        '- Some teams keep a `CLAUDE.md` in the parent folder, but this repo doesn\'t need it.',
    ]),
    'finding-symlink-real-path': ([
        '- `CLAUDE.md` is a symlink to `AGENTS.md`, so Claude Code and other agents read the same file.',  # smoke
        '- Scope: `AGENTS.md`, plus `CLAUDE.md`, a symlink to it, so there is one file.',  # smoke (audit)
        '| `CLAUDE.md` | symlink → `AGENTS.md` |',
        '- `CLAUDE.md -> AGENTS.md`: one file, nothing to sync.',
        '- `CLAUDE.md` points to `AGENTS.md` (a symlink), and that is the file graded.',
        '- `CLAUDE.md` links to `AGENTS.md`; I graded `AGENTS.md`.',
    ], [
        '- Some teams keep `CLAUDE.md` as a symlink to `AGENTS.md`, but this repo doesn\'t need it.',
    ]),
    'finding-check-allowlist': ([
        '- Allow `Bash(bun run check)` in `.claude/settings.json` so the check runs without a prompt.',  # review N3
        plan_item(1, 'Pre-approve the check commands', 'Problem: `.claude/settings.json` doesn\'t exist, so no '
                  '`permissions.allow` rule covers `bun run check` and every run prompts.\nChange: create '
                  '`.claude/settings.json`:\n```json\n{"permissions": {"allow": ["Bash(bun run check)"]}}\n```'),
        '- The check is only in `package.json` and CI, so every run prompts: add `Bash(bun run check)` to '
        '`permissions.allow`.',
        '| `bun run check` | CI and package.json | allow `Bash(bun run check)` |',
        '- Pre-approve `Bash(bun run check)`.',
        '- Nothing pre-approves the check; add `Bash(bun run check:*)` to the allow list.',
    ], [
        '- Some teams allow `Bash(bun run check)`, but this repo doesn\'t need it.',
        '- Not needed: add `Bash(bun run check)` to allow.',
    ]),
    'no-invented-agents-md-missing': ([], ['- The repo lacks an `AGENTS.md`.']),  # review N5
    'no-invented-parent-findings': ([], ['- Point `bin/legacy-build` at the new script.']),  # review N5
}
for _name, (_passing, _failing) in ROUND2.items():
    CONTROLS[_name][0].extend(_passing)
    CONTROLS[_name][1].extend(_failing)

# Review round 4: O1 to O3 rebuilt as structural rules. Each grader's controls hold every reviewer example from rounds
# 1 to 3 that touches it (now graded by the new rule), the false-negative pass (correct phrasings in the shapes the
# recorded reports use), and the attacker pass.
SKILLS_SOURCE = '   Source: [Put team procedures in skills](https://code.claude.com/docs/en/best-practices)'


def claudit_top(*items, also=()):
    """A Claudit-shaped report: numbered Top changes, then Also worth knowing bullets."""
    text = '## Top changes\n\n%d changes are worth making.\n\n' % len(items) + '\n\n'.join(items)
    if also:
        text += '\n\n## Also worth knowing\n\n' + '\n'.join('- ' + note for note in also)
    return text + '\n\n---\nClaudit 4.2.0'


def skill_item(n, title, *body):
    return '%d. **%s** (Alignment, effort S)\n%s\n%s' % (n, title, '\n'.join('   ' + b for b in body), SKILLS_SOURCE)


STOP_HOOK_ITEM = skill_item(1, 'Enforce the tests with a Stop hook', 'Problem: nothing runs `go test` before Claude '
                            'finishes.', 'Change: add a Stop hook.')
# Proposals to make the principles a skill: review M4, N5 and L-b, and round 1's own.
SKILL_PROPOSALS = [
    'Consider creating a skill from the principles.',  # M4
    'Consider making the principles a skill.',  # M4
    '`docs/principles.md` could be packaged as a skill.',  # M4
    'The principles in `docs/principles.md` would work well as a skill.',  # M4
    'A `principles` skill would load only when needed.',  # M4
    '`docs/principles.md` is always loaded; a skill would cut that.',  # M4
    'Convert to a skill: `docs/principles.md`.',  # M4
    '`docs/principles.md` would be a good fit for a skill.',  # N5
    'Turning the principles into a slash command would help.',  # L-b
    'A skill for the principles would help.',  # round 3
    'Turn `docs/principles.md` into a skill.',
    'Moving `docs/principles.md` into `.claude/skills/principles/SKILL.md` saves context.',
    'Writing the principles up as a skill would help.',
    '`docs/principles.md` deserves its own skill.',
]
# Correct statements about the principles: review M4, O1 and L-f, and round 1's own. None proposes a skill.
SKILL_DECLINES = [
    'Keep `docs/principles.md` as is; skills are for procedures.',  # M4
    '`docs/principles.md` reads as rules, unlike the release procedure in `docs/release.md`.',  # M4
    '`docs/principles.md` is a declarative list; a skill would add nothing.',  # O1
    'The principles are fine as text; a skill would be overkill.',  # O1
    'The numbered steps in `docs/principles.md` form a procedure.',  # L-f: a claim, not a skill proposal
    '`docs/principles.md` is a list of principles, not a procedure, so it needs no skill.',
    'No procedure needs a skill: `docs/principles.md` holds standing principles.',
    'Don\'t turn `docs/principles.md` into a skill.',
    'No skill is needed for the principles.',
    'Why not make `docs/principles.md` a skill?',
    'Is a skill for the principles worth it?',
    'Rather than a skill, keep the principles in `docs/principles.md`.',
    'The principles aren\'t a procedure, so a skill is the wrong fit.',
    'Skills suit procedures; the principles are a list.',
    'The principles aren\'t a procedure, so leave them in `docs/principles.md`.',
]
PLAIN_HOOK_ITEM = '**What to improve, in priority order**\n\n1. **Enforce the test rule with a hook.** Add a Stop hook.\n\n2. '
ROUND4 = {
    'finding-branch-protection': ([
        '- Enable branch protection on `main` so merges require a review.',  # O3
        '- Also enable branch protection on `main` so merges require an approving review; the ask rule only covers '
        'Claude Code.',  # O3
        '- Turn on branch protection for `main` to require pull request reviews.',  # O3
        # Smoke a9fd63c (plain), the one recorded report that names branch protection.
        '- **Branch protection:** require PR approval on `main` in GitHub. CI already runs on PRs, so also make `ci / '
        'check` a required status check. This is the only control that holds regardless of what the agent does.',
        '- **Branch protection:** require PR approval on `main` in GitHub.',
        '- Branch protection on `main` is the real gate: an ask rule only prompts inside Claude Code.',
        '- Ask rules only prompt inside Claude Code, and branch protection on `main` is the real gate.',
        '- The merge rule is prose only: turn on branch protection that requires an approving review.',
        '- Protect `main`: branch protection is the only control that holds for every client.',
        '| merge to main | branch protection | the real gate, enforced server-side |',
        '- Enable a ruleset on `main`; it enforces review for anyone who pushes.',
        '- Require reviews with a protected branch; nothing else enforces the merge rule outside Claude Code.',
        '- Turn on a ruleset for `main` that requires review before a merge.',
        '- Branch protection on `main` enforces review for everyone.',
        '- `main` has no branch protection, so anyone can merge without review.',
        '- Add a ruleset on `main` that requires one approving review.',
        '- Make `main` a protected branch with required reviews.',
        '- Nothing on GitHub stops a merge: enable branch protection on `main`.',
        plan_item(3, 'Protect main on GitHub', 'Problem: the ask rule only prompts in Claude Code; anyone else can '
                  'merge.\nChange: in GitHub, add a branch protection rule for `main` that requires one approving '
                  'review.'),
    ], [
        # Review L3: inverted claims.
        '- Branch protection only matters for humans; the ask rule is the real gate.',
        '- Rely on the ask rule rather than branch protection, which only slows you down.',
        # No main, merge or review: the O3 rule needs one (round 1's passing control, now failing).
        '- Ask rules don\'t replace branch protection, which is the gate that holds for everyone.',
        '- Ask rules don\'t replace branch protection, which is not the real gate.',
        '- Branch protection exists on GitHub.',
        '- Never treat branch protection as the real gate.',
        '- Require review before merging to `main`.',
        # Each guard, with main, merge or review in the sentence.
        '- No branch protection is needed on `main`.',
        '- No branch protection is needed to gate merges.',
        '- `main` doesn\'t need branch protection.',
        '- Don\'t enable branch protection on `main`.',
        '- Don\'t rely on branch protection to enforce reviews.',
        '- No gate is needed here, including branch protection that enforces review.',
        '- Rely on the ask rule for merges rather than branch protection.',
        '- Branch protection only matters for humans; merges by Claude go through the ask rule.',
        '- Remove branch protection from `main`.',
        '- Branch protection won\'t help with merges that Claude Code makes.',
        '- Branch protection on `main` isn\'t needed.',
        '- Branch protection that enforces reviews isn\'t needed.',
        '- Branch protection on `main` is already enabled.',
        '- Is branch protection on `main` enabled?',
        '- If you want, enable branch protection on `main`.',
        '- Branch protection could enforce reviews on `main` if you want.',
        '- Branch protection on `main`: I left it out of the plan.',
        '- Branch protection enforces review; I left it out of the plan.',
        '- Some teams turn on branch protection to enforce reviews, but this repo doesn\'t need it.',
        '- Not needed: branch protection that enforces review.',
        '- A previous audit said to enable branch protection on `main`.',  # N6 shape
        '- Hold off on branch protection for `main`.',  # N6 shape
        '   Source: [About protected branches](https://docs.github.com) require reviews before merging to main',
    ]),
    'finding-parent-blocks-agents': ([
        '- The parent `CLAUDE.md` loads, so `AGENTS.md` is not read directly.',  # O2
        '- `../CLAUDE.md` is loaded, so Claude Code won\'t read `AGENTS.md` directly.',  # O2
        '- Anyone who has the parent `CLAUDE.md` gets it instead of the repo\'s `AGENTS.md`.',  # L-e
        '- Because the parent folder has a `CLAUDE.md`, Claude Code never reads `AGENTS.md` on its own.',  # N4
        '- The parent folder\'s `CLAUDE.md` stops the repo\'s `AGENTS.md` being read directly.',
        '- The parent folder\'s `CLAUDE.md` stops the repo\'s `AGENTS.md` being read directly for anyone who has '
        'that parent.',
        '- Because `../CLAUDE.md` loads, `AGENTS.md` won\'t be read on its own; the symlink is what loads it.',
        '- For anyone with this parent, `../CLAUDE.md` loads and `AGENTS.md` is not read on its own; the symlink is '
        'what loads it.',
        '| `../CLAUDE.md` | parent | blocks the direct read of `AGENTS.md` |',
        '- Note: a `CLAUDE.md` above the repo means Claude Code won\'t read `AGENTS.md` directly.',
        '- The parent `CLAUDE.md` shadows `AGENTS.md`: Claude Code reads `AGENTS.md` only when no `CLAUDE.md` loads.',
        # Either order, across sentences and lines of one paragraph or list item.
        '- `AGENTS.md` is not loaded on its own. The cause is `../CLAUDE.md`: a `CLAUDE.md` in any parent folder '
        'counts.',
        'There is a `CLAUDE.md` in the parent folder.\nBecause one loads, Claude Code doesn\'t load `AGENTS.md` '
        'directly here.',
        plan_item(1, 'Note the parent file', 'Problem: `../CLAUDE.md` loads for anyone who has this parent.\nWhy: '
                  'Claude Code reads `AGENTS.md` only when no `CLAUDE.md` loads, so the repo\'s `AGENTS.md` is not '
                  'read directly.'),
        '- `AGENTS.md` is ignored while the parent `CLAUDE.md` loads.',
        '- With `~/CLAUDE.md` present, `AGENTS.md` isn\'t loaded directly.',
        '- Claude Code picks up the `CLAUDE.md` above and so never looks at `AGENTS.md` itself.',
    ], [
        '- If the parent had a `CLAUDE.md`, it would stop `AGENTS.md` being read.',  # M2
        '- I expected the parent `CLAUDE.md` to block `AGENTS.md`; it is fine.',  # N6 shape
        '- The parent `CLAUDE.md` does not stop `AGENTS.md` loading.',
        '- Does the parent `CLAUDE.md` stop `AGENTS.md` being read?',
        '   Source: [AGENTS.md](https://code.claude.com/docs/en/memory) a parent CLAUDE.md stops it being read',
        '- The parent `CLAUDE.md` and the repo\'s `AGENTS.md` both load.',
        '- The parent `CLAUDE.md` is ignored, and it can\'t stop `AGENTS.md` loading.',
        '- The parent `CLAUDE.md` never stops `AGENTS.md` loading.',
        '- The parent `CLAUDE.md` might stop `AGENTS.md` being read.',
        '- The parent `CLAUDE.md` stops `AGENTS.md` being read; I left it out of the plan.',
        '- The parent `CLAUDE.md` loads, but the parent `AGENTS.md` is not read.',
        '- The parent `CLAUDE.md` is not read, but `AGENTS.md` is.',
        '- `AGENTS.md` isn\'t ignored: the parent `CLAUDE.md` loads alongside it.',
        '- As noted above, `CLAUDE.md` loads, so `AGENTS.md` is not read directly.',
        # One unit each: separate paragraphs, list items and table rows don't combine.
        'The parent folder has a `CLAUDE.md`.\n\nSeparately, `AGENTS.md` is not read by Codex here.',
        '- The parent `CLAUDE.md` loads.\n- `AGENTS.md` is not read directly.',
        # Smoke a9fd63c (doctor-combined): the recorded table rows.
        '| `../CLAUDE.md` (workspace) | memory | parent dir | n/a | n/a | ~50 | keep |\n| `AGENTS.md` | memory '
        '(duplicate of `CLAUDE.md`) | project | n/a | n/a | not loaded by Claude Code | see note |',
    ]),
    'no-invented-principles-skill': (
        # A bullet, prose or an Also worth knowing note never counts.
        ['- ' + text for text in SKILL_PROPOSALS] + [claudit_top(STOP_HOOK_ITEM, also=[text]) for text in SKILL_PROPOSALS]
        # A numbered item that declines, or says no skill is needed, never counts.
        + [claudit_top(STOP_HOOK_ITEM, skill_item(2, 'Principles', text)) for text in SKILL_DECLINES]
        + ['1. ' + text for text in SKILL_DECLINES] + [
            # Smoke a9fd63c (plain f14 and f17): optional extras, as a numbered heading and as a numbered item.
            '## 1. Rules are prose only\n- Add a Stop hook.\n\n## 4. Optional extras (lower value at this size)\n- A '
            '`/principles` skill that walks through the list.',
            '1. **Enforce the tests.** Add a Stop hook.\n\n6. **Optional extras, only if they\'d be used:**\n   - A '
            '`/principles` slash command or skill that wraps the list.',
            '## Declined by the project\n\n1. **Skills** (`docs/decisions.md:3`): turn `docs/principles.md` into a skill.',
            '\n## Also worth knowing\n\n1. Turn `docs/principles.md` into a skill.',
            '## Top changes\n1. **Hooks** Add a Stop hook.\n## Also worth knowing\n1. Turn `docs/principles.md` into a '
            'skill.',
            claudit_top(STOP_HOOK_ITEM, skill_item(2, 'Keep the principles as they are', 'A skill would load them on '
                                                   'demand, but they are short.')),
            # The #184 gate's release-skill item: a skill for another file, with the principles named elsewhere.
            claudit_top(STOP_HOOK_ITEM, skill_item(2, 'Add a release skill', 'Problem: `docs/release.md` has 5 numbered '
                                                   'steps, but `.claude/skills/` doesn\'t exist.', 'Change: create '
                                                   '`.claude/skills/release/SKILL.md`.')),
            claudit_top(skill_item(1, 'Principles', 'Problem: none.'), skill_item(2, 'Add a release skill', 'Change: '
                                                                                  'create `.claude/skills/release/SKILL.md`.')),
            # The only skill word is in the Source: line.
            claudit_top(STOP_HOOK_ITEM, skill_item(2, 'Shorten the principles', 'Problem: `docs/principles.md` is '
                                                   'imported every session.', 'Change: trim the list to five lines.')),
        ],
        # The same proposals as a numbered item, in Claudit's and plain's shapes.
        [claudit_top(STOP_HOOK_ITEM, skill_item(2, 'Load the principles on demand', 'Problem: `docs/principles.md` is '
                                                'imported into every session.', 'Change: ' + text))
         for text in SKILL_PROPOSALS] + [PLAIN_HOOK_ITEM + text for text in SKILL_PROPOSALS] + [
            # The #184 gate's recorded release-skill item, with the principles in place of the release doc.
            claudit_top(skill_item(1, 'Add a skill for docs/principles.md', 'Problem: `docs/principles.md` has 7 '
                                   'numbered principles, but no skill exists and nothing loaded links to it. Claude '
                                   'only follows it if it happens to find the doc.', 'Why: The principles are a '
                                   'repeatable procedure, and a skill makes it discoverable and invocable.', 'Change: '
                                   'Create `.claude/skills/principles/SKILL.md` with `name` and `description` '
                                   'frontmatter. It should follow the list in `docs/principles.md`, keep that doc as '
                                   'the source and link to it.')),
            claudit_top(STOP_HOOK_ITEM, skill_item(2, 'Move the principles out of every session', 'Problem: `CLAUDE.md` '
                                                   'imports `@docs/principles.md`, so all 7 principles load every '
                                                   'session.', 'Change: create `.claude/skills/principles/SKILL.md`:',
                                                   '```markdown', '---', 'name: principles', 'description: Design '
                                                   'principles for the library.', '---', '```')),
            '## 1. Rules are prose only\n- Add a Stop hook.\n\n## 2. Context\n- Turn `docs/principles.md` into a skill so '
            'it loads only when needed.',
            '- Add a Stop hook.\n## 2. Context\n- Turn `docs/principles.md` into a skill.',
            '**What to improve**\n\n1. **Make the principles a skill.** It would keep them out of every session.',
            '**1.** Make the principles a skill.',
            claudit_top(skill_item(1, 'Load the principles on demand', 'Problem: the principles load every session, but '
                                   'no skill holds them.', 'Change: make `docs/principles.md` a skill.')),
            claudit_top(skill_item(1, 'Load the principles on demand', 'Change: move the principles into a skill so they '
                                   'don\'t load every session.')),
        ]),
}
CONTROLS.update(ROUND4)


# Each named part a builder can drop: the control it must flip is in CONTROLS. structure-alignment-below-a has none.
LINE_PARTS = ('source', 'question', 'hypothetical', 'declined', 'rejected', 'claim')
MUTATIONS = {
    'finding-ask-merge': LINE_PARTS + ('already', 'neg-after', 'rule', 'intro'),
    'finding-ask-deploy': LINE_PARTS + ('already', 'rule', 'intro'),
    'finding-ask-release': LINE_PARTS + ('already', 'rule', 'intro'),
    'finding-branch-protection': LINE_PARTS + ('already', 'neg-after', 'against', 'with'),
    'finding-commit-hook': LINE_PARTS + ('already', 'neg-after', 'reason-shape', 'intro'),
    'finding-always-loaded-table': ('units', 'claude-row', 'import-row'),
    'finding-visible-skill': LINE_PARTS + ('already', 'not-false', 'intro'),
    'finding-duplicates-grouped': ('source', 'question', 'hypothetical', 'declined', 'neg', 'contributing',
                                   'migrator'),
    'finding-stale-folder': LINE_PARTS + ('refer',),
    'finding-stale-file': LINE_PARTS,
    'finding-stale-dependency': LINE_PARTS,
    'finding-parent-noted': LINE_PARTS,
    'finding-symlink-real-path': LINE_PARTS + ('proposal',),
    'no-invented-agents-md-missing': ('source', 'skip-negated'),
    'finding-parent-blocks-agents': LINE_PARTS + ('parent', 'unit', 'repo-agents'),
    'no-invented-parent-findings': ('source', 'skip-negated', 'scope'),
    'finding-check-allowlist': LINE_PARTS + ('already', 'rule', 'intro'),
    'no-invented-principles-skill': ('source', 'refuse', 'question', 'title', 'principles', 'clause', 'section'),
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
