---
type: regex
pattern: '(?:^|\n)#{2,3}[ \t]+(?:The )?Top(?: [0-9]+)? changes[^\n]*(?:(?!\n(?:#{3,4}[ \t]+)?(?:\*\*)?[0-9]+[.)][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*\n(?:#{3,4}[ \t]+)?(?:\*\*)?1[.)][ \t]+(?:\*\*)?Pre-approve[ \t]+the[ \t]+check[ \t]+commands(?:\*\*|[ \t]*(?=\(|\n|(?![\s\S])))(?:(?!\n(?:#{3,4}[ \t]+)?(?:\*\*)?[0-9]+[.)][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*\n(?:#{3,4}[ \t]+)?(?:\*\*)?2[.)][ \t]+(?:\*\*)?Enforce[ \t]+the[ \t]+check[ \t]+with[ \t]+a[ \t]+Stop[ \t]+hook(?:\*\*|[ \t]*(?=\(|\n|(?![\s\S])))(?:(?!\n(?:#{3,4}[ \t]+)?(?:\*\*)?[0-9]+[.)][ \t]|\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S])))[\s\S])*(?=\n#{1,2}[ \t]|\n[-*_]{3,}[ \t]*(?:\n|(?![\s\S]))|\n?(?![\s\S]))'
flags: i
weight: 1
---
The Top changes section holds exactly the plan the scan decides for this fixture (Claudit 4.1, issue #174 requirement 1): 1. Pre-approve the check commands, 2. Enforce the check with a Stop hook.

Script-graded (case-insensitive), built from the scan by `tests/test_claudit_case_graders.py`. Each item is a column-0 line `N. **<title>**` (or `N)`, bold around the number, or a `###`/`####` heading) numbered from 1 in order, with the title word for word; a word with a dot or slash may be backticked. No other column-0 numbered line may appear in the section, which ends at the next `#` or `##` heading, a `---` rule or the end of the report. With no items the first non-blank line says "No changes worth making".
