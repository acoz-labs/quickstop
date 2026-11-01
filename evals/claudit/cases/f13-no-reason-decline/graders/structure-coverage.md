---
type: regex
pattern: '\bcoverage\b[^\n]{0,160}\bconfidence\b|\bconfidence\b[^\n]{0,160}\bcoverage\b'
flags: i
weight: 1
---
The report gives the Coverage grade with a confidence on the same line. A 4.0 target; Claudit 3.2.3 is expected to fail.
