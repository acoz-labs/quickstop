# Security notes on signed uploads (Celeste, 29 Oct)

Conditions for approval:
1. One signed URL per object key; PUT only; no list or read.
2. Expiry 15 minutes.
3. Object keys are random, prefixed with the inspection ID.
4. At submit, the API verifies every key exists, sits under that inspection's
   prefix, and is under the 25 MB size cap. Reject the submit otherwise.
5. Unclaimed uploads (no submit within 24 hours) are deleted by a lifecycle rule.

With those, this is fine. No pen test needed beyond the normal release check.
