"""Check a saved report for required sections."""
import re

REQUIRED = ('Intent', 'Grades', 'Top changes')


def missing_sections(text):
    """Required section names that have no heading in text."""
    headings = {m.group(1).strip() for m in re.finditer(r'^#+\s+(.+)$', text, re.M)}
    return [name for name in REQUIRED if name not in headings]
