"""Graders for the sotsog eval: script graders, which cost nothing, and the prompts and schemas for the judges.

Frozen with the suite. The runner (`bin/sotsog-eval`) finds the decision document, calls the judges and keeps
the records; everything that decides a verdict is here, so the same code grades both arms and the calibration.
"""
import json
from pathlib import Path
import re
import statistics

SUITE = Path(__file__).resolve().parent
OUTCOMES = ('adopt', 'adapt', 'not now', 'no')
GO = ('adopt', 'adapt')
ITEMS = ('decided', 'why', 'next')
GAPS = ('who_gains', 'baseline')
FIT_RATINGS = ('already have', 'partly', 'gap', 'conflicts', "doesn't apply")
SKEPTICAL_LABELS = {
    'who gains': ('who gains',),
    'measured against': ('measured against',),
    "what's missing": ("what's missing", 'what is missing'),
    'whose conditions': ('whose conditions',),
    'independent support': ('independent support',),
}
TABLE_HEADER = ['principle', 'how they do it', 'how we do it', 'fit']
# Labels that state a decision are searched across the whole document first; summary-type labels, whose first
# sentence is often prose that happens to start with an outcome word, only when no decision label gives a verdict.
PRIMARY_LABELS = ('decision', 'recommendation', 'verdict')
FALLBACK_LABELS = ('conclusion', 'tl;dr', 'tldr', 'bottom line', 'summary', 'short answer')
DECISION_LABELS = PRIMARY_LABELS + FALLBACK_LABELS
# Lead-ins skipped before a verdict, tried in order and repeatedly: "My recommendation is to", "I'd recommend",
# "We'll", "<Name> should". A subject that starts with a negative or a hedge ("nobody should adopt", "maybe we
# should adopt") is never skipped, so the verdict stays unread.
SUBJECT = (r"(?!(?:no|nobody|no one|none|neither|never|maybe|perhaps|possibly|probably|might|could|unclear|"
           r"unsure|if|whether)\b)(?:[\w'.-]+ ){0,3}?")
LEAD_INS = (
    r"(?:my|our|the) (?:recommendation|decision|verdict|answer) is(?: to| that we| that)?",
    r"(?:i|we)(?: would|'d| will|'ll)? (?:recommend|suggest|propose)(?: that we| that| we)?",
    r"recommend(?:ed)?",
    r"(?:we|i)(?: should| will|'ll| would|'d| can| must)?",
    SUBJECT + r"[\w'.-]+ should",
    r"yes",
    r"to",
)
# A negated modal after a subject ("We won't adopt", "The team shouldn't adopt") reads as "not ...".
NEGATED = re.compile(SUBJECT + r"(?:[\w'.-]+ )?(?:should not|shouldn't|will not|won't|would not|wouldn't|"
                     r"do not|don't|does not|doesn't|cannot|can't)\s+")
# Verdict phrases, matched as whole words at the start of the verdict, longest first, so "not now" is never
# read as "no" and "adopt in part" never as "adopt".
VERDICT_PHRASES = {
    'adopt in part': 'adapt', 'partially adopt': 'adapt', 'adopt partially': 'adapt', 'adopt, partially': 'adapt',
    'adopt with changes': 'adapt', 'adapt': 'adapt', 'adapting': 'adapt',
    'not now': 'not now', 'not yet': 'not now', 'not at this time': 'not now', 'not right now': 'not now',
    'hold off': 'not now', 'wait': 'not now', 'defer': 'not now', 'deferring': 'not now', 'postpone': 'not now',
    'later': 'not now',
    'do not adopt': 'no', "don't adopt": 'no', 'not adopt': 'no', 'not adopting': 'no', 'not adopted': 'no',
    'reject': 'no', 'decline': 'no', 'no': 'no',
    'adopt': 'adopt', 'adopting': 'adopt', 'adopted': 'adopt',
}
DATE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
LIST_ITEM = re.compile(r'^(\s*)(?:[-*+]|\d+[.)])\s+')
TEMPLATE_H1 = re.compile(r'^#\s+(?P<idea>.+?):\s+(?P<outcome>adopt|adapt|not now|no)\s+for\s+(?P<target>\S.*?)\s*$', re.I)


def normalize(text):
    """Lower case, straight quotes and dashes, single spaces: how labels and phrases are compared."""
    text = text.replace('’', "'").replace('‘', "'").replace('—', '-').replace('–', '-')
    return re.sub(r'\s+', ' ', text).strip().lower()


def plain(text):
    """Text without Markdown emphasis or code markers."""
    return re.sub(r'[*_`]', '', text)


def lines_of(document):
    return document.replace('\r\n', '\n').split('\n')


def fenced_free(document):
    """The document's lines with fenced code blocks blanked, so examples inside code never count."""
    out, fenced = [], False
    for line in lines_of(document):
        if line.strip().startswith('```'):
            fenced = not fenced
            out.append('')
        else:
            out.append('' if fenced else line)
    return out


def headings(lines):
    return [(i, len(m.group(1)), plain(m.group(2)).strip()) for i, line in enumerate(lines)
            if (m := HEADING.match(line))]


def section(lines, starts_with, level=2):
    """The lines under the first heading at `level` whose text starts with `starts_with`, up to the next heading
    at that level or above; None when there's no such heading."""
    marks = headings(lines)
    for n, (i, lvl, text) in enumerate(marks):
        if lvl == level and normalize(text).startswith(normalize(starts_with)):
            end = next((j for j, l2, _ in marks[n + 1:] if l2 <= level), len(lines))
            return lines[i + 1:end]
    return None


# Outcome.

def verdict_outcome(text):
    """The outcome a verdict text states at its start, or None. Lead-ins and markers are skipped first."""
    rest = normalize(plain(text))
    while True:
        rest = rest.lstrip(' :.-,;!()[]"\'')
        negated = NEGATED.match(rest)
        if negated and not rest.startswith(('do not adopt', "don't adopt")):
            rest = 'not ' + rest[negated.end():]
            continue
        for lead in LEAD_INS:
            match = re.match(rf"(?:{lead})(?![\w'])", rest)
            if match and match.end():
                rest = rest[match.end():]
                break
        else:
            break
    for phrase in sorted(VERDICT_PHRASES, key=len, reverse=True):
        if re.match(rf'{re.escape(phrase)}(?![\w\'])', rest):
            return VERDICT_PHRASES[phrase]
    return None


def decision_label(line, labels=DECISION_LABELS):
    """(label, text after it) when the line labels a decision: a heading, a bold label, or a plain line whose
    label is followed by a colon or dash ("Decision: adopt"). Body text such as "Decision makers..." isn't one."""
    is_heading = HEADING.match(line) is not None
    body = HEADING.sub(r'\2', line) if is_heading else LIST_ITEM.sub('', line)
    bold = re.match(r'^\s*(\*\*|__)', body) is not None
    text = normalize(plain(body))
    for label in labels:
        if not re.match(rf'{re.escape(label)}(?![\w])', text):
            continue
        rest = text[len(label):]
        if is_heading or bold or re.match(r'\s*[:-]', rest):
            return label, rest
    return None, ''


def first_sentence(paragraph):
    text = ' '.join(line.strip() for line in paragraph)
    match = re.match(r'(.+?[.!?])(\s|$)', text)
    return match.group(1) if match else text


def label_verdict(lines, labels):
    """(outcome, where, text) from the first label in `labels` that gives a verdict, or None. A label's verdict is
    on its own line or, failing that, the first sentence of the next paragraph."""
    for i, line in enumerate(lines):
        label, rest = decision_label(line, labels)
        if not label:
            continue
        found = verdict_outcome(rest)
        if found:
            return found, 'label', line.strip()
        paragraph, j = [], i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        while j < len(lines) and lines[j].strip() and not HEADING.match(lines[j]):
            paragraph.append(LIST_ITEM.sub('', lines[j]))
            j += 1
        sentence = first_sentence(paragraph)
        found = verdict_outcome(sentence)
        if found:
            return found, 'next paragraph', sentence
    return None


def outcome(document):
    """(outcome or None, where it was read, the text read). Same reader for both arms.

    In order, the first verdict found wins: the template's H1 decision line; any Decision, Recommendation or
    Verdict label in the document; a verdict right after the colon of any other H1; then any Conclusion,
    Summary, TL;DR, Bottom line or Short answer label. A label with no verdict doesn't stop the search."""
    lines = fenced_free(document)
    h1 = next((line for line in lines if re.match(r'^#\s', line)), None)
    if h1 and (m := TEMPLATE_H1.match(plain(h1).strip())):
        return normalize(m.group('outcome')), 'h1', h1.strip()
    found = label_verdict(lines, PRIMARY_LABELS)
    if found:
        return found
    if h1 and ':' in h1 and not decision_label(h1)[0]:
        verdict = verdict_outcome(h1.split(':', 1)[1])
        if verdict:
            return verdict, 'h1 verdict', h1.strip()
    found = label_verdict(lines, FALLBACK_LABELS)
    if found:
        return found
    first_label = next((line.strip() for line in lines if decision_label(line)[0]), '')
    return None, 'none', first_label


# Structure.

def table_rows(lines):
    """Rows of the first table whose header is the template's comparison header, or None."""
    for i, line in enumerate(lines):
        if not line.strip().startswith('|'):
            continue
        cells = [normalize(plain(c)) for c in line.strip().strip('|').split('|')]
        if cells != TABLE_HEADER:
            continue
        rows = []
        for row in lines[i + 2:]:
            if not row.strip().startswith('|'):
                break
            rows.append([plain(c).strip() for c in row.strip().strip('|').split('|')])
        if i + 1 < len(lines) and re.match(r'^\s*\|?\s*:?-{3,}', lines[i + 1]):
            return rows
    return None


def list_groups(section_lines):
    """Top-level list items of a section, each with its continuation and nested lines."""
    groups = []
    for line in section_lines:
        m = LIST_ITEM.match(line)
        if m and not m.group(1):
            groups.append([line])
        elif groups and line.strip():
            groups[-1].append(line)
    return groups


def structure(document):
    """The six template checks; passes when all hold."""
    lines = fenced_free(document)
    found, _, _ = outcome(document)
    h1 = next((line for line in lines if re.match(r'^#\s', line)), '')
    checks = {}
    rows = table_rows(lines)
    checks['comparison table'] = bool(rows) and all(
        len(r) == 4 and any(normalize(r[3]).startswith(f) for f in FIT_RATINGS) for r in rows)
    checks['decision line'] = bool(TEMPLATE_H1.match(plain(h1).strip()))
    revisit = section(lines, 'Revisit when')
    checks['revisit when'] = revisit is not None and any(line.strip() for line in revisit)
    evidence = section(lines, 'What the evidence shows')
    text = normalize(plain('\n'.join(evidence or [])))
    checks['skeptical read'] = evidence is not None and all(
        any(form in text for form in forms) for forms in SKEPTICAL_LABELS.values())
    has_brief = section(lines, 'Implementation brief') is not None
    checks['brief iff go'] = checks['decision line'] and has_brief == (found in GO)
    sources = section(lines, 'Sources')
    groups = list_groups(sources or [])
    checks['sources with dates'] = bool(groups) and all(DATE.search(' '.join(g)) for g in groups)
    return {'passed': all(checks.values()), 'checks': checks}


# Depth, script half.

def library_titles(case_dir):
    titles = {}
    for path in sorted((Path(case_dir) / 'research/library').glob('*.md')):
        first = path.read_text().split('\n', 1)[0]
        titles[path.name] = re.sub(r'^#\s+', '', first).strip()
    return titles


def cited(document, name, title):
    text = normalize(document)
    stem = name[:-3] if name.endswith('.md') else name
    return (re.search(rf'(?<![\w-]){re.escape(stem)}(?![\w-])', text) is not None
            or normalize(title) in text)


def depth_script(document, case):
    """Which library files the document cites, by file name or exact title, and whether the counts are met."""
    titles = library_titles(case['dir'])
    found = {name: case['library'][name] for name, title in titles.items() if cited(document, name, title)}
    roles = set(found.values())
    return {'passed': bool(found) and 'critique' in roles and 'competitor' in roles, 'cited': found}


# Judges: prompts and schemas. Each judge sees only what its prompt builder passes.

def judge_prompt_text(kind, suite=SUITE):
    return (Path(suite) / 'judges' / f'{kind}.md').read_text()


def schema(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


TEXT = {'type': 'string'}
VERDICT = schema({'verdict': {'type': 'string', 'enum': ['PASS', 'FAIL']}, 'reason': TEXT})
SCHEMAS = {
    'reader': schema({item: TEXT for item in ITEMS}),
    'compare': schema({item: VERDICT for item in ITEMS}),
    'brief': schema({'verdict': {'type': 'string', 'enum': ['YES', 'NO']}, 'reasons': TEXT}),
    'open-questions': schema({'questions': {'type': 'array', 'items': TEXT}}),
    'depth': schema({'sources': {'type': 'array', 'items': schema(
        {'file': TEXT, 'described': {'type': 'boolean'}, 'reason': TEXT})}}),
    'gaps': schema({gap: VERDICT for gap in GAPS}),
}


def document_prompt(document):
    return f'<document>\n{document}\n</document>'


def compare_prompt(key, notes):
    items = {item: key['items'][item] for item in ITEMS}
    return '\n'.join(['<answer_key>', json.dumps(items, indent=2), '</answer_key>',
                      '<notes>', json.dumps(notes, indent=2), '</notes>'])


def depth_prompt(document, case, cited_files):
    parts = [document_prompt(document)]
    for name, role in sorted(cited_files.items()):
        if role in ('critique', 'competitor'):
            text = (Path(case['dir']) / 'research/library' / name).read_text()
            parts.append(f'<source file="{name}" role="{role}">\n{text}\n</source>')
    return '\n'.join(parts)


def gaps_prompt(document, key):
    return '\n'.join([document_prompt(document), '<gaps>', json.dumps(key['gaps'], indent=2), '</gaps>'])


def judges_needed(key, found_outcome, depth):
    """The judges one document gets, in order. Reader and comparator always; the rest only where scored."""
    kinds = ['reader', 'compare']
    if key['go']:
        kinds.append('brief')
    if found_outcome in ('no', 'not now'):
        kinds.append('open-questions')
    if depth['passed']:
        kinds.append('depth')
    if 'gaps' in key:
        kinds.append('gaps')
    return kinds


def script_grades(document, case):
    found, where, text = outcome(document)
    return {'structure': structure(document),
            'outcome': {'value': found, 'read_from': where, 'text': text, 'passed': found in case['key']['expected']},
            'depth_script': depth_script(document, case)}


def final_grades(case, script, judged):
    """Every grader's verdict for one document. A judge that didn't grade leaves its grader as None (ungraded)."""
    key = case['key']
    grades = {'structure': script['structure']['passed'], 'outcome': script['outcome']['passed'],
              'outcome_value': script['outcome']['value']}
    compare = judged.get('compare')
    grades['cold_read'] = ({item: compare[item]['verdict'] == 'PASS' for item in ITEMS} if compare else None)
    if key['go']:
        brief = judged.get('brief')
        grades['brief'] = None if brief is None else brief['verdict'] == 'YES'
    if script['outcome']['value'] in ('no', 'not now'):
        questions = judged.get('open-questions')
        grades['open_questions'] = None if questions is None else len(questions['questions'])
    if not script['depth_script']['passed']:
        grades['depth'] = False
    else:
        depth = judged.get('depth')
        if depth is None:
            grades['depth'] = None
        else:
            described = {s['file'] for s in depth['sources'] if s['described']}
            roles = {script['depth_script']['cited'].get(f) for f in described}
            grades['depth'] = 'critique' in roles and 'competitor' in roles
    if 'gaps' in key:
        gaps = judged.get('gaps')
        grades['gaps'] = None if gaps is None else {gap: gaps[gap]['verdict'] == 'PASS' for gap in GAPS}
    return grades


# Cases.

def load_cases(suite=SUITE):
    cases = {}
    for directory in sorted((Path(suite) / 'cases').iterdir()):
        if not directory.is_dir():
            continue
        meta = json.loads((directory / 'case.json').read_text())
        cases[directory.name] = dict(meta, name=directory.name, dir=directory,
                                     prompt=(directory / 'prompt.md').read_text(),
                                     key=json.loads((directory / 'key.json').read_text()))
    return cases


# Calibration expectations.

def calibration_rows(case, sample, expected, grades, script, judges):
    """One row per expected verdict: ok when the grade matches. Script-only runs skip judge rows."""
    rows = []

    def row(grader, want, got):
        rows.append({'case': case['name'], 'sample': sample, 'grader': grader, 'expected': want, 'got': got,
                     'ok': got == want})

    row('structure', expected['structure'], grades['structure'])
    row('outcome', expected['outcome'], grades['outcome'])
    row('depth (script half)', expected['depth_script'], script['depth_script']['passed'])
    if not judges:
        return rows
    for item, want in (expected.get('cold_read') or {}).items():
        row(f'cold read {item}', want, None if grades['cold_read'] is None else grades['cold_read'][item])
    if 'brief' in expected:
        row('brief', expected['brief'], grades.get('brief'))
    if 'open_questions' in expected:
        count = grades.get('open_questions')
        bound = expected['open_questions']
        ok = count is not None and count <= bound.get('max', count) and count >= bound.get('min', count)
        rows.append({'case': case['name'], 'sample': sample, 'grader': 'open questions', 'expected': bound,
                     'got': count, 'ok': ok})
    row('depth', expected['depth'], grades['depth'])
    for gap, want in (expected.get('gaps') or {}).items():
        row(f'gap {gap}', want, None if grades.get('gaps') is None else grades['gaps'][gap])
    return rows


def median(values):
    return statistics.median(values) if values else None
