# tidecache

A small read-through cache for the tide-gauge API. `tidecache.get(station)`
returns the latest reading, fetching it when the cached copy is older than the
configured time-to-live.
