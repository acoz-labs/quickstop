#!/usr/bin/env python3
"""Minimal lint: syntax check, no tabs, no trailing whitespace, lines <= 100."""
import pathlib
import py_compile
import sys

problems = []
for root in sys.argv[1:]:
    for path in sorted(pathlib.Path(root).rglob("*.py")):
        py_compile.compile(str(path), doraise=True)
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if "\t" in line:
                problems.append(f"{path}:{n}: tab character")
            if line != line.rstrip():
                problems.append(f"{path}:{n}: trailing whitespace")
            if len(line) > 100:
                problems.append(f"{path}:{n}: line longer than 100")
print("\n".join(problems) or "lint: ok")
sys.exit(1 if problems else 0)
