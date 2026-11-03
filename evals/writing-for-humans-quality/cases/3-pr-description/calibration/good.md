## Retry failed webhook deliveries

Webhook deliveries that fail on a timeout, a 429 or a 5xx response are now retried, up to five attempts over about 30 seconds, instead of being dropped after the first failure. Before merging, can someone confirm whether our receivers deduplicate repeated deliveries by event id? If they don't, a retry after a slow delivery that actually succeeded would send the same event twice, for example a second payment-received email.

### What changes

- Waits between attempts grow from about 2 seconds to about 16, with some random jitter so receivers that recover don't get hit all at once.
- Other 4xx responses, such as a 404, are still not retried, because sending again won't help.
- Each request now carries the attempt number in an `X-Delivery-Attempt` header, alongside the existing `X-Event-Id`, so receivers can spot a repeat.
- A delivery that runs out of attempts is logged as an error rather than a warning.

### Why

Today one transient failure loses the event permanently, and nothing resends it.

### Tests

New tests cover a 5xx followed by success, giving up after five attempts, no retry on 404, a retried timeout and the attempt header. They pass locally.
