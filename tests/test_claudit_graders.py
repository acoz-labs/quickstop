"""The Claudit 5 eval graders (#207): built from each case's scan, with passing and failing controls and a mutation
check, in Python and, when node is installed, in node.

Passing controls render each case's scan as a report six ways (phrasings adapted from recorded 4.3.1 reports:
labelled problem and fix lines, bold leads, an inline fix, a fence whose body isn't indented, wrapped lines, no
Source line). Every grader of the case must pass all six. Failing controls change one thing each and name the grader
that must fail: a dropped item, a wrong line, a missing fix token, an item moved under "Not reported", a token only
in a negated note, an invented second item at an expected citation, an item with no citation, advice under the
table, advice in the footer, a wrong count, a missing footer line, a missing respected or scope line.
"""
import json
from pathlib import Path
import re
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claudit_graders as cg  # noqa: E402

ce = cg.ce
BUILT = None


def built():
    global BUILT
    if BUILT is None:
        BUILT = cg.built()
    return BUILT


def split_fix(fix):
    """(lead, JSON block, text after it, script) for a scan fix: settings JSON and scripts go in fenced blocks."""
    prefix = 'Add to .claude/settings.json: '
    if not fix.startswith(prefix):
        return fix, None, '', ''
    data, end = json.JSONDecoder().raw_decode(fix, len(prefix))
    rest = fix[end:]
    script = ''
    if rest.startswith(' and create') and ':\n' in rest:
        rest, script = rest.split(':\n', 1)
        rest += ':'
    return 'Add to `.claude/settings.json`', json.dumps(data), rest.strip().lstrip('.').strip(), script


def item(n, finding, variant):
    cite = '`%s:%d`' % (finding['path'], finding['line'])
    lead, block, after, script = split_fix(finding['fix'])
    language = 'json'
    source = finding.get('source')
    src = '[%s](%s)' % (source['heading'], source['url']) if source else ''
    problem = finding['problem']
    if variant == 0:  # the skill's shape
        lines = ['%d. %s %s' % (n, cite, problem), '   Fix: %s%s' % (lead, ':' if block else '')]
    elif variant == 1:  # a bold lead, labelled lines (4.3.1's Problem/Change shape)
        lines = ['%d. %s **%s**' % (n, cite, finding['kind']), '   Problem: %s' % problem,
                 '   Change: %s%s' % (lead, ':' if block else '')]
    elif variant == 2:  # one line, the fix inline
        lines = ['%d. %s %s Fix: %s%s%s' % (n, cite, problem, lead, ' `%s`' % block if block else '',
                                             ' ' + after if after else '')]
        block = after = None
    elif variant == 3:  # a fence whose body isn't indented
        lines = ['%d. %s %s' % (n, cite, problem), '   Fix: %s:' % lead if block else '   Fix: %s' % lead]
    elif variant == 4:  # wrapped lines
        words, wrapped, current = problem.split(' '), [], ''
        for word in words:
            if len(current) + len(word) > 60 and current:
                wrapped.append(current)
                current = word
            else:
                current = (current + ' ' + word).strip()
        wrapped.append(current)
        lines = ['%d. %s %s' % (n, cite, wrapped[0])] + ['   ' + w for w in wrapped[1:]] + ['   Fix: ' + lead]
    else:  # labelled, no Source line
        lines = ['%d. %s' % (n, cite), '   Problem: %s' % problem, '   Fix: %s' % lead]
        src = ''
    if block:
        indent = '' if variant == 3 else '   '
        lines += ['   ```' + language, indent + block, indent + '```']
    if after:
        lines.append('   ' + after)
    if script and variant != 2:
        lines += ['   ```bash'] + [('   ' + line) if line else '' for line in script.rstrip('\n').split('\n')] + ['   ```']
    elif script:
        lines[-1] += ' then create `.claude/hooks/stop-check.sh`, which runs the check and ends with `exit 2` on a failure.'
    if src and variant != 2:
        lines.append('   Source: ' + src)
    return '\n'.join(lines)


def render(scan, variant=0, findings=None, not_reported=None, after_table='', footer=None, summary=None):
    findings = scan['findings'] if findings is None else findings
    parts = ['# Claudit: fixture', '', summary or scan['summary'], '']
    parts += [item(n, f, variant) for n, f in enumerate(findings, 1)]
    bullets = [r['text'] for r in scan['respected']] + (not_reported or [])
    if bullets:
        parts += ['', '## Not reported', ''] + ['- ' + b for b in bullets]
    parts += ['', '## Always loaded', '', scan['context']['table']]
    if after_table:
        parts += ['', after_table]
    parts += ['', '---'] + (scan['footer'] if footer is None else footer)
    return '\n'.join(parts) + '\n'


def failing_controls(case, scan, graders):
    """[(label, text, grader that must fail)] for one case."""
    names = [g[0] for g in graders]
    out = []
    finding_names = [n for n in names if n.startswith('finding-') and not n.startswith(('finding-respected',
                                                                                         'finding-scope'))]
    for index, (finding, name) in enumerate(zip(scan['findings'], finding_names)):
        rest = scan['findings'][:index] + scan['findings'][index + 1:]
        out.append(('dropped %s' % name, render(scan, findings=rest), name))
        out.append(('dropped %s' % name, render(scan, findings=rest), 'no-invented-findings'))
        moved = dict(finding, line=finding['line'] + 1)
        out.append(('wrong line %s' % name, render(scan, findings=rest[:index] + [moved] + rest[index:]), name))
        out.append(('wrong line %s' % name, render(scan, findings=rest[:index] + [moved] + rest[index:]),
                    'no-invented-findings'))
        for token in ce.finding_tokens(finding):
            bare = dict(finding, problem='See the line.', fix='Fix it.', id=finding['id'] + ':x')
            out.append(('no token %s %s' % (name, token), render(scan, findings=rest[:index] + [bare] + rest[index:]),
                        name))
        note = '`%s:%d`: not needed here (%s)' % (finding['path'], finding['line'], finding['fix'][:120].replace('\n', ' '))
        out.append(('moved to Not reported %s' % name, render(scan, findings=rest, not_reported=[note]), name))
        negated = '`%s:%d`: don\'t add %s; see `%s:%d`.' % (finding['path'], finding['line'], finding['fix'][:80].replace(
            '\n', ' '), finding['path'], finding['line'])
        out.append(('negated note %s' % name, render(scan, findings=rest, not_reported=[negated]), name))
    for finding in scan['findings']:
        bare = dict(finding, problem='See the line.', fix='Fix it.', id=finding['id'] + ':x')
        others = [f for f in scan['findings'] if f is not finding]
        out.append(('no token', render(scan, findings=others + [bare]), 'no-invented-findings'))
        out.append(('the same item twice', render(scan, findings=scan['findings'] + [finding]),
                    'no-invented-findings'))
    if scan['findings']:
        first = scan['findings'][0]
        invented = dict(first, id='invented', problem='Also add a skill for this file.', fix='Create a skill.')
        out.append(('invented item at an expected citation',
                    render(scan, findings=scan['findings'] + [invented], summary='%d findings.' % (
                        len(scan['findings']) + 1)), 'no-invented-findings'))
    uncited = {'id': 'x', 'kind': 'x', 'path': '', 'line': 0, 'problem': 'Add a skill for the release docs.',
               'fix': 'Create `.claude/skills/release/SKILL.md`.'}
    text = render(scan, findings=scan['findings'] + [uncited]).replace('`:0` ', '')
    out.append(('an item with no citation', text, 'no-invented-findings'))
    out.append(('advice under the table', render(scan, after_table='Consider a skill for `docs/release.md`.'),
                'no-invented-prose'))
    out.append(('advice in the footer', render(scan, footer=scan['footer'] + ['Tip: add a skill for the docs.']),
                'no-invented-prose'))
    out.append(('a wrong count', render(scan, summary='%d findings.' % (len(scan['findings']) + 2)),
                'structure-summary'))
    out.append(('no /doctor prompt-audit line', render(scan, footer=[l for l in scan['footer'] if '/doctor' not in l]),
                'structure-footer'))
    for name in names:
        if name.startswith('finding-respected-'):
            bare = dict(scan, respected=[])
            out.append(('no respected line', render(bare), name))
        if name.startswith('finding-scope-'):
            line = scan['scope']['lines'][int(name.rsplit('-', 1)[1]) - 1]
            out.append(('no scope line', render(scan, footer=[l for l in scan['footer'] if l != line]), name))
    return out


def literal(token):
    """Text a token regex matches: the first alternative, unescaped."""
    first = token.split('|')[0]
    return re.sub(r'\[(.)[^\]]*\]', r'\1', re.sub(r'\\(.)', r'\1', first))


class Graders(unittest.TestCase):
    def test_committed_graders_match_the_scan(self):
        for case, (_, graders) in built().items():
            with self.subTest(case):
                folder = cg.CASES / case / 'graders'
                self.assertEqual(sorted(p.stem for p in folder.glob('*.md')), sorted(g[0] for g in graders),
                                 'rebuild with python3 tests/claudit_graders.py --write')
                for name, pattern, function, doc in graders:
                    self.assertEqual((folder / (name + '.md')).read_text(), cg.grader_text(pattern, function, doc),
                                     '%s: rebuild with --write' % name)
                    self.assertEqual(cg.read_grader(folder / (name + '.md'))['pattern'], pattern)

    def test_every_case_has_its_planted_items(self):
        """Each case's findings, pinned by hand from the fixture, not from the scan: kind, file, line and the exact rules
        a fix suggests. A scan change that moves any of them fails here, not only in the rebuilt graders."""
        unittest_call = 'Bash(python3 -m unittest discover -s tests)'
        expected = {
            'f1-agent-run': [('allowlist', 'CLAUDE.md', 3, ['Bash(bin/ci)']), ('stop-hook', 'CLAUDE.md', 3, [])],
            'f2-plugin-repo': [('allowlist', 'CLAUDE.md', 6, [unittest_call]), ('stale-ref', 'CLAUDE.md', 10, [])],
            'f3-misconfigured': [('oversized', 'CLAUDE.md', 1, [])],
            'f5-bare': [('allowlist', 'go.mod', 1, ['Bash(go test ./...)'])],
            'f6-agents-md': [('allowlist', 'AGENTS.md', 3, ['Bash(bin/check)']), ('stop-hook', 'AGENTS.md', 3, [])],
            'f10-stale-decline': [('allowlist', 'CLAUDE.md', 5, ['Bash(bin/check-notes)']),
                                  ('stop-hook', 'CLAUDE.md', 5, [])],
            'f12-unsafe-decline': [('allowlist', 'CLAUDE.md', 7, ['Bash(bin/test)'])],
            'f14-enforcement': [('stop-hook', 'CLAUDE.md', 13, []),
                                ('gate-ask', 'CLAUDE.md', 14, ['Bash(gh pr merge *)', 'Bash(bin/deploy *)',
                                                               'Bash(bin/release *)'])],
            # bin/check is allowed, so the steps it runs need no rules: no allowlist finding on f15.
            'f15-context-economy': [('visible-skill', '.claude/skills/schema-rules/SKILL.md', 3, []),
                                    ('stop-hook', 'CLAUDE.md', 5, []), ('duplicate', 'CLAUDE.md', 6, [])],
            'f16-stale-facts': [('stale-ref', 'CLAUDE.md', 8, []), ('stale-ref', 'CLAUDE.md', 9, []),
                                ('stale-dep', 'CLAUDE.md', 10, []), ('allowlist', 'CLAUDE.md', 14, [unittest_call])],
            # Nothing names a command, so the rules are package.json's own scripts, run the way CLAUDE.md says (bun run).
            'f18-check-commands': [('allowlist', 'package.json', 9, ['Bash(bun run test)', 'Bash(bun run lint)',
                                                                     'Bash(bun run check)', 'Bash(bun run typecheck)'])],
        }
        respected = {'f8-documented-decline': ['stop-hook'], 'f11-valid-decline': ['stop-hook'],
                     'f13-no-reason-decline': ['stop-hook']}
        for case, (scan, _) in built().items():
            with self.subTest(case):
                got = [(f['kind'], f['path'], f['line'], re.findall(r'"(Bash\([^"]*\))"', f['fix']))
                       for f in scan['findings']]
                self.assertEqual(got, expected.get(case, []))
                self.assertEqual([r['id'] for r in scan['respected']], respected.get(case, []))
        self.assertEqual(len(built()['f17-scope'][0]['scope']['lines']), 3)

    def checks(self):
        """[(label, pattern, text, expected)] for every case."""
        out = []
        for case, (scan, graders) in built().items():
            patterns = {name: pattern for name, pattern, _, _ in graders}
            for variant in range(6):
                text = render(scan, variant)
                out += [('%s variant %d %s' % (case, variant, name), pattern, text, True)
                        for name, pattern in patterns.items()]
            for label, text, name in failing_controls(case, scan, graders):
                out.append(('%s %s %s' % (case, label, name), patterns[name], text, False))
        return out

    def test_controls_in_python(self):
        for label, pattern, text, expected in self.checks():
            self.assertEqual(cg.verdict(pattern, text), expected, label + '\n' + text)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_controls_in_node(self):
        checks = self.checks()
        got = cg.js_verdicts([[pattern, text] for _, pattern, text, _ in checks])
        for (label, _, text, expected), verdict in zip(checks, got):
            self.assertEqual(verdict, expected, label)

    def test_every_part_is_load_bearing(self):
        """Dropping any part of `no-invented-findings` or a `finding-*` token lets a failing control pass."""
        for case, (scan, graders) in built().items():
            controls = [(text, name) for _, text, name in failing_controls(case, scan, graders)]
            parts = ce.findings_parts(scan['findings'])
            for index in range(len(parts)):
                weaker = ''.join(parts[:index] + parts[index + 1:])
                with self.subTest(case=case, part=index):
                    self.assertTrue(any(cg.verdict(weaker, text) for text, name in controls
                                        if name == 'no-invented-findings'),
                                    'part %d of no-invented-findings is not load-bearing: %s' % (index, parts[index]))
            for finding in scan['findings']:
                tokens = ce.finding_tokens(finding)
                for token in tokens:
                    rest = [t for t in tokens if t != token]
                    item = ce.ITEM_START + r'[ \t]*' + ce.cited(finding['path'], finding['line'])
                    weaker = ''.join(r'(?=[\s\S]*%s%s*?(?:%s))' % (item, ce.IN_ITEM, t) for t in rest) or item
                    # The item keeps every other token, so only the dropped one is missing.
                    bare = dict(finding, problem='See the line: %s.' % ', '.join(literal(t) for t in rest),
                                fix='Fix it.', id=finding['id'] + ':x')
                    others = [f for f in scan['findings'] if f is not finding]
                    text = render(scan, findings=others + [bare])
                    with self.subTest(case=case, token=token):
                        self.assertTrue(cg.verdict(weaker, text), 'without %s the grader still needs it' % token)
                        self.assertFalse(cg.verdict(ce.finding_pattern(finding), text))

    def test_real_report_checks(self):
        """grade_report, the headless check of real repositories, on the same controls."""
        scan = built()['f15-context-economy'][0]
        good = render(scan)
        self.assertEqual(set(ce.grade_report(good, scan).values()), {True}, ce.grade_report(good, scan))
        dropped = render(scan, findings=scan['findings'][1:])
        self.assertFalse(ce.grade_report(dropped, scan)['scan_accounted'])
        first = scan['findings'][0]
        reason = '`%s:%d`: the subagent rules say to keep it (`docs/contributing.md:3`).' % (first['path'], first['line'])
        explained = render(scan, findings=scan['findings'][1:], not_reported=[reason],
                           summary='%d findings.' % (len(scan['findings']) - 1))
        self.assertEqual(set(ce.grade_report(explained, scan).values()), {True}, ce.grade_report(explained, scan))
        unexplained = explained.replace(' (`docs/contributing.md:3`)', '')
        self.assertFalse(ce.grade_report(unexplained, scan)['drops_cite_the_repository'])
        invented = render(scan, findings=scan['findings'] + [dict(first, line=99)])
        self.assertFalse(ce.grade_report(invented, scan)['items_from_scan'])
        self.assertFalse(ce.grade_report(render(scan, after_table='Also add a skill.'), scan)['template'])
        respected = built()['f8-documented-decline'][0]
        self.assertTrue(ce.grade_report(render(respected), respected)['respected_listed'])
        self.assertFalse(ce.grade_report(render(dict(respected, respected=[])), respected)['respected_listed'])


if __name__ == '__main__':
    unittest.main()
