import sys

from csvsum import column_sum

with open(sys.argv[1], encoding='utf-8') as handle:
    print(column_sum(handle, sys.argv[2]))
