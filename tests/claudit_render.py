"""A Claudit report written verbatim from a scan, as SKILL.md lays it out, for $0 checks of the scan's wording.

The model writes the real report. This rendering keeps only what the skill tells it to take from the scan word for
word (grades, plan titles, each finding's problem, each fix, the always-loaded table, the scope lines, the footer), so
a frozen grader that fails on it fails because of the scan's wording, not the model's.
"""
import json
import re

GRADE_NAMES = ('correctness', 'alignment', 'coverage')


def split_fix(fix):
    """(text before, a JSON object or fenced block, text after) of a finding's fix."""
    fence = re.search(r'\n?```(\w*)\n(.*?)\n```', fix, re.S)
    if fence:
        return fix[:fence.start()].rstrip(':'), (fence.group(1), fence.group(2)), fix[fence.end():]
    start = fix.find('{')
    if start < 0:
        return fix, None, ''
    try:
        obj, end = json.JSONDecoder().raw_decode(fix[start:])
    except ValueError:
        return fix, None, ''
    return fix[:start].rstrip(' :'), ('json', json.dumps(obj, indent=2)), fix[start + end:].lstrip('. ')


def render(scan, deep=None):
    findings = {f['id']: f for f in scan['findings']}
    lines = ['# Claudit: project', '', '**Intent:** a project. Assumed from the repository; correct me if wrong.', '',
             '## Grades', '']
    for name in GRADE_NAMES:
        grade = scan['grades'][name]
        why = 'Nothing to fix.' if grade['letter'] == 'A' else 'Item%s %s would raise it to A.' % (
            's' if len(grade['items']) > 1 else '', ' and '.join(str(n) for n in grade['items']))
        lines.append('- **%s: %s** (confidence: high). %s' % (name.capitalize(), grade['letter'], why))
    lines += ['', '## Top changes', '', scan['plan']['summary'], '']
    for item in scan['plan']['items']:
        lines.append('%d. **%s** (%s, effort S)' % (item['n'], item['title'], item['grades'][0].capitalize()))
        mine = [findings[i] for i in item['finding_ids'] if i in findings]
        problem = ' '.join(f.get('problem') or f['evidence'] + '.' for f in mine)
        lines += ['   Problem: %s' % problem, '   Why: it serves the intent.']
        for f in mine[:1] if item['kind'] != 'stale' else []:
            before, block, after = split_fix(f['fix'])
            lines.append('   Change: %s:' % before.rstrip('.') if block else '   Change: %s' % before)
            if block:
                lines += ['   ```%s' % block[0]] + ['   ' + l for l in block[1].splitlines()] + ['   ```']
            text, _, script = after.partition(':\n')
            if text.strip():
                lines.append('   ' + text.strip() + (':' if script else ''))
            if script:  # a script the fix creates, such as a Stop hook's
                lines += ['   ```bash'] + ['   ' + l for l in script.rstrip().splitlines()] + ['   ```']
        if item['kind'] == 'stale':
            lines.append('   Change: point each line at what exists, or remove it.')
        source = mine[0]['source'] if mine else {}
        if source.get('url'):
            lines.append('   Source: [%s](%s)' % (source['heading'], source['url']))
        lines.append('')
    if scan['declined']:
        lines += ['## Declined by the project', '']
        for d in scan['declined']:
            lines += ['- **%s** (`%s:%d`): "%s"' % (d['label'], d['path'], d['line'], d['quote']),
                      '  Reason: %s' % ('no reason given.' if d['reason'] == 'no reason given' else '"%s"' % d['reason'])]
            note = d.get('reconsider')
            if note:
                evidence = note['evidence']
                lines.append('  Worth reconsidering: %s. Evidence: %s' % (note['claim'], '[%s](%s)' % (
                    evidence['heading'], evidence['url']) if 'url' in evidence else '`%s:%d`' % (
                    evidence['path'], evidence['line'])))
        lines.append('')
    for item in scan['plan']['items']:
        if item.get('declined'):
            at = lines.index('%d. **%s** (%s, effort S)' % (item['n'], item['title'], item['grades'][0].capitalize()))
            lines.insert(at + 2, '   Declined: %s (`%s:%d`)' % (item['declined']['label'], item['declined']['path'],
                                                                item['declined']['line']))
    lines += ['## Always loaded', '', scan['context']['table'], '', '## Also worth knowing', '']
    lines += ['- %s' % l for l in scan['scope']['lines']] or ['- Nothing else.']
    if deep is not None:
        lines += ['', '## From /doctor prompt-audit', '', '- %s' % deep]
    lines += ['', '---', scan['footer'], 'Claude Code 2.1.317; catalog %s.' % scan['catalog_version']]
    return '\n'.join(lines) + '\n'
