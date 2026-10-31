"""Read-through cache for tide-gauge readings."""
import time

TTL_SECONDS = 300
_cache = {}


def get(station, fetch, now=time.monotonic):
    entry = _cache.get(station)
    if entry and now() - entry[0] < TTL_SECONDS:
        return entry[1]
    reading = fetch(station)
    _cache[station] = (now(), reading)
    return reading
