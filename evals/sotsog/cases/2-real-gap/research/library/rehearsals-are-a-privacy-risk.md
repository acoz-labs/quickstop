# Production copies in test are a privacy incident waiting to happen

Source: https://privacy-eng.example.com/blog/stop-copying-production
Author: Ruth Abernathy, privacy engineer and author on data protection
Published: 2026-08-05

"Rehearse your migration on a copy of production" is popular advice, and the
cost is rarely mentioned: every copy of production is another place personal
data can leak from, and most test environments have weaker access controls.
If you must rehearse, use a copy with personal fields replaced, or a synthetic
dataset generated at production size. A static linter and a lock timeout give
most of the protection at none of the risk.
