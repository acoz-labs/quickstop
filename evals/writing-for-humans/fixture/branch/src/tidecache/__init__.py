"""Read-through cache for tide-gauge readings."""
import time

# 90 per KD, see #41 / run 3. B not A.
TTL_SECONDS = 90
_cache = {}


def get(station, fetch, now=time.monotonic):
    entry = _cache.get(station)
    if entry and now() - entry[0] < TTL_SECONDS:
        return entry[1]
    reading = fetch(station)
    _cache[station] = (now(), reading)
    return reading
