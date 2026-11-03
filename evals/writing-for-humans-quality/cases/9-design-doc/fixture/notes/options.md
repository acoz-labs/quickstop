# Options (Dev's scratch notes)

A. Raise gateway timeout to 120s
   - Smallest change. Rejected by security: one global setting, longer
     timeouts widen slow-request attacks on every route.

B. Chunked upload through the API
   - App sends photos in 1 MB chunks to a new API endpoint, API reassembles.
   - Fixes the timeout. Keeps photo bytes on API servers, so memory problem and
     the two extra servers stay. Most new server code of the three.

C. Signed direct-to-storage uploads  <- preferred
   - Fixes the timeout and the memory problem. Per-photo retry.
   - New: signing endpoint, key check at submit, app upload queue.
   - Storage costs unchanged.

Estimate for C: API work 2 sprints (Dev), app work 3 sprints (Bram's team),
in parallel. Target: 4.12 in the stores mid-January.
