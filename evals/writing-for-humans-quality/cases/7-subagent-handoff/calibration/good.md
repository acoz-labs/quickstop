Only one of the three libraries does both things you need: pdfquill can sign PDFs and is MIT licensed. It hasn't had a release in 14 months, so you need to choose: take pdfquill with that risk, or ask legal to approve paperforge, which signs too but is AGPL. With pdfquill we may have to fork and patch it ourselves; with paperforge we wait on legal, and a no rules it out.

The third candidate, inkleaf, has the right licence (Apache-2.0) but can't sign, and its maintainers have said they don't plan to add signing.

On pdfquill's health: it has 37 open issues, two of them security issues that don't affect signing, and the maintainer was last active in March. Paperforge is actively released (last on 21 October), and our policy sends any AGPL dependency to legal review.
