---
type: regex
pattern: '(?=[\s\S]*?\*\*Correctness: D\*\*)(?=[\s\S]*?\*\*Alignment: A\*\*)(?=[\s\S]*?\*\*Coverage: A\*\*)'
weight: 1
---
The grade letters are the scan's: Correctness D, Alignment A, Coverage A (Claudit 4.2, issue #184 requirements 3 and 4).

Script-graded (case-sensitive): grade lines `**Correctness: X**`, `**Alignment: X**` and `**Coverage: X**` with these letters, anywhere in the report.
