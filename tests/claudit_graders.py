"""Build the Claudit 5 eval graders (#207) from the scan of each case's scaffolded fixture.

Every grader is a script (regex) grader. The patterns come from bin/claudit-eval, which uses the same definitions to
check real-repository reports, so a fixture and a real repository are graded alike. Rebuild after changing a
fixture, the scan or a pattern:

    python3 tests/claudit_graders.py --write

`tests/test_claudit_graders.py` fails when a committed grader falls behind, and runs each grader's passing and failing
controls in Python and, when node is installed, in node (the engine `claude plugin eval` uses).
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'evals/claudit/cases'
SCAFFOLD_ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
sys.dont_write_bytecode = True  # never leave a cache in the plugin bytes or bin/


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


cl = load('claudit_helper_graders', ROOT / 'plugins/claudit/skills/claudit/scripts/claudit.py')
ce = load('claudit_eval_graders', ROOT / 'bin/claudit-eval')

GRADER = """---
type: regex
pattern: '{pattern}'
weight: 1
---
{doc}

Script-graded and built from the scan of the scaffolded fixture by `tests/claudit_graders.py` (rebuild with
`python3 tests/claudit_graders.py --write`); the pattern is `{function}` in `bin/claudit-eval`, which also checks
real-repository reports.
"""


def scaffold_scan(case, workdir):
    """Scaffold a case as the eval host does (a workspace whose parent folder is the run's home) and scan it."""
    target = Path(workdir) / case / 'cwd'
    target.mkdir(parents=True)
    target = target.resolve()
    subprocess.run(['bash', str(CASES / case / 'scaffold.sh')], cwd=target, check=True, env=SCAFFOLD_ENV,
                   capture_output=True)
    ceiling, cl.Scan.ceiling = cl.Scan.ceiling, str(target.parent)  # nothing above the run's home counts
    try:
        return cl.Scan(str(target), True, 'unknown').run()
    finally:
        cl.Scan.ceiling = ceiling


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')




def case_graders(scan):
    """[(name, pattern, function, doc)] for one case's scan."""
    out = []
    kinds = [f['kind'] for f in scan['findings']]
    for finding in scan['findings']:
        name = 'finding-' + finding['kind']
        if kinds.count(finding['kind']) > 1:
            name += '-' + slug(finding['id'].split(':', 2)[-1])
        out.append((name, ce.finding_pattern(finding), 'finding_pattern',
                    'A numbered item cites `%s:%d` and holds %s: the scan\'s `%s` finding ("%s").' % (
                        finding['path'], finding['line'], ' and '.join('`%s`' % t for t in ce.finding_tokens(finding)),
                        finding['id'], finding['problem'][:200])))
    for entry in scan['respected']:
        out.append(('finding-respected-' + entry['id'], ce.lines_pattern([entry['text']], ce.NOT_REPORTED),
                    'lines_pattern', 'Under "Not reported", the respected decision line: "%s"' % entry['text']))
    for number, line in enumerate(scan['scope']['lines'], 1):
        out.append(('finding-scope-%d' % number, ce.lines_pattern([line], ce.FOOTER_RULE), 'lines_pattern',
                    'After the footer rule, the scope line: "%s"' % line))
    listed = ', '.join('`%s:%d` (%s)' % (f['path'], f['line'], f['kind']) for f in scan['findings']) or 'none'
    out += [
        ('no-invented-findings', ce.findings_pattern(scan['findings']), 'findings_pattern',
         'The numbered items are exactly the scan\'s findings, one to one: %s. An invented item, an item with no '
         'citation or a second item at an expected citation fails.' % listed),
        ('no-invented-prose', ce.template_pattern(), 'template_pattern',
         'The report holds only the template\'s parts (title, count line, numbered items, "Not reported", "Always '
         'loaded", the footer lines). Advice or any other prose outside them fails.'),
        ('structure-summary', ce.summary_pattern(len(scan['findings'])), 'summary_pattern',
         'The line after the title is "%s"' % scan['summary']),
        ('structure-footer', ce.footer_pattern(cl.VERSION), 'footer_pattern',
         'After the footer rule: the not-checked line, the `/doctor prompt-audit` line and "Claudit %s; audited '
         'commit <sha>".' % cl.VERSION),
    ]
    return out


def built():
    """{case: (scan, graders)} for every case in the suite."""
    with tempfile.TemporaryDirectory() as work:
        return {path.parent.name: (scan, case_graders(scan))
                for path in sorted(CASES.glob('*/case.yaml'))
                for scan in [scaffold_scan(path.parent.name, work)]}


def grader_text(pattern, function, doc):
    return GRADER.format(pattern=pattern.replace("'", "''"), function=function, doc=doc)


def write_all():
    for case, (_, graders) in built().items():
        folder = CASES / case / 'graders'
        for old in folder.glob('*.md'):
            old.unlink()
        for name, pattern, function, doc in graders:
            (folder / (name + '.md')).write_text(grader_text(pattern, function, doc))


def read_grader(path):
    head = path.read_text().split('\n---\n', 1)[0].splitlines()[1:]
    fields = {}
    for line in head:
        key, _, value = line.partition(': ')
        if len(value) > 1 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        fields[key] = value
    return fields


def verdict(pattern, text):
    return re.search(pattern, text) is not None


def js_verdicts(checks):
    """[(pattern, text)] -> [passed], with JavaScript's RegExp as `claude plugin eval` runs it."""
    script = ("const checks = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
              "process.stdout.write(JSON.stringify(checks.map(([p, t]) => new RegExp(p).test(t))));")
    out = subprocess.run(['node', '-e', script], input=json.dumps(checks), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


if __name__ == '__main__':
    if sys.argv[1:] != ['--write']:
        sys.exit('usage: python3 tests/claudit_graders.py --write')
    write_all()
