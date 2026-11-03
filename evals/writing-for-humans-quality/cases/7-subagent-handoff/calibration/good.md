Use pdfquill: it's the only one of the three that can sign PDFs and has an allowed licence (MIT). The open question is whether you're comfortable with its upkeep, since it hasn't had a release in 14 months. If a bug or security problem turns up, we may have to fork and fix it ourselves, because neither alternative meets both of your requirements.

The other two each miss one. Paperforge signs but is AGPL, and inkleaf is Apache-2.0 but can't sign, with no plans to add it.

On pdfquill's health: it has 37 open issues, two of them security issues that don't affect signing, and the maintainer was last active in March. If you'd like me to go ahead, I'll start with its PAdES signing support.
