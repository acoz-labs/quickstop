import sys

from reportcheck import missing_sections

with open(sys.argv[1], encoding='utf-8') as handle:
    gaps = missing_sections(handle.read())
print('\n'.join(gaps))
sys.exit(1 if gaps else 0)
