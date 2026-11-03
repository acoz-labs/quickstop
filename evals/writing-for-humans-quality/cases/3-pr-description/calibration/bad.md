## Changes to webhooks/sender.py

This PR updates the webhook sender. In this description I will walk through each part of the diff in order so that reviewers can follow along.

`deliver()` now loops up to `MAX_ATTEMPTS` times. `_backoff()` computes the delay using `BASE_DELAY_SECONDS` and `random.uniform`. `RETRYABLE_STATUS` contains 429, 500, 502, 503 and 504. The `else` branch of the try statement runs when no exception was raised, which is standard Python behaviour. `time.sleep` pauses the current thread for the given number of seconds.

An exponential backoff is a strategy where the wait between attempts doubles each time. Jitter is a small random variation added to the wait. HTTP status codes in the 500 range indicate server errors, and 429 means too many requests.

`tests/test_sender.py` adds five tests. `deliver()` now loops up to `MAX_ATTEMPTS` times.

Let me know if anything is unclear.
