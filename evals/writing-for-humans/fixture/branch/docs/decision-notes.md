# TTL

Went with B. A regressed p95 on the cold path in run 3 (#41); C needs the shim
we dropped in a8f2c1.

TTL now 90s per KD's call, revisit after LT.

Open: does the purge hook still fire on 304s? If not, stale window is ~TTL+jitter.

Ask: ship behind the flag Mon or wait for LT?
