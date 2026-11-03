## Subagent return: pdf-signing-libs (task t-8812)

Scope: candidates pdfquill, paperforge, inkleaf. Criteria C1 = PAdES/PKCS#7 signing supported, C2 = licence in {MIT, Apache-2.0}.

```json
[
  {"lib": "pdfquill",   "version": "2.4.0", "C1": true,  "C2": true,  "licence": "MIT",        "last_release": "2025-09-02", "evidence": "docs/signing.md#pades; LICENSE"},
  {"lib": "paperforge", "version": "7.1.3", "C1": true,  "C2": false, "licence": "AGPL-3.0",   "last_release": "2026-10-21", "evidence": "README#licensing; src/sign/pkcs7.rs"},
  {"lib": "inkleaf",    "version": "0.19.0","C1": false, "C2": true,  "licence": "Apache-2.0", "last_release": "2026-10-28", "evidence": "issue #311 'signing: not planned'"}
]
```

Notes:
- pdfquill: C1 ok via `Signer.pades()`; 14mo since last release; 37 open issues, 2 labelled security (neither affects signing, per triage labels); maintainer last commented 2026-03.
- paperforge: C1 ok; AGPL-3.0 => network-use clause; org policy LP-4 requires legal review for AGPL; dual licence not offered.
- inkleaf: C1 not supported; maintainers closed signing request as not planned (#311).
- verdict: pdfquill = only C1 && C2. risk: maintenance. alt: paperforge iff legal approves AGPL.
