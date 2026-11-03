# Upload failures (from Aiko, platform on-call, 21 Oct)

Inspectors take photos on site, then tap "Submit inspection". The app sends the
whole inspection, photos included, in one request to the API. The API servers
write each photo to object storage before they answer.

The gateway in front of the API cuts any request off at 30 seconds. We can't
change that per route; it's one setting for the whole public gateway and
security wants it kept.

Last 30 days:
- 61,400 inspections submitted
- 3,710 failed with a gateway timeout (6.0%)
- of inspections with more than 40 photos: 2,950 of 7,200 failed (41%)
- of inspections with 40 photos or fewer: 760 of 54,200 failed (1.4%)
- median photos per inspection: 18; p95: 64
- median photo size after the app's compression: 2.1 MB

When a submit fails, the app retries the whole thing from the start, photos
included. Inspectors on weak site connections can retry five or six times.
Support gets about 140 tickets a month about stuck submissions, and some
inspectors re-shoot photos because they think they were lost.

API servers also spend most of their memory buffering photos. We added two
servers in September just for upload load.
