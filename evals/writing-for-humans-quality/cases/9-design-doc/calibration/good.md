# Direct-to-storage photo uploads

## Summary

The app should send each photo straight to object storage through a short-lived signed URL and submit only the photo references, so submits stop failing at the gateway's 30-second timeout. Reviewers must decide whether apps older than 4.12 are forced to upgrade on 31 January or keep the old submit path. Forcing it retires that path and its servers but cuts off inspectors whose devices can't run 4.12; keeping it means paying to run both.

The mobile team needs the answer before sprint planning on 16 November, because a forced upgrade needs an upgrade prompt in 4.12.

## Problem

Today the app sends a whole inspection, photos included, in one request, and the API writes every photo to storage before replying. The public gateway ends any request at 30 seconds, and security wants that limit kept for every route.

In the last 30 days, 6% of the 61,400 submits failed this way. Size drives it: 41% of inspections with more than 40 photos failed, against 1.4% of smaller ones. A failed submit starts again from the first photo, so inspectors on weak site connections retry five or six times, some re-shoot photos they think were lost, and support handles about 140 tickets a month. Buffering photos also takes most of the API servers' memory; two servers were added in September for upload load alone.

## Proposal

1. The app asks the API for one signed upload URL per photo.
2. It uploads each photo directly to object storage, retrying a single photo when one fails.
3. It submits the inspection with the photo keys only.
4. The API checks every key before accepting the submit.

Security has approved this with five conditions: each URL allows a single PUT to one object and expires in 15 minutes; keys are random and prefixed with the inspection ID; at submit the API confirms each key exists, sits under that inspection's prefix and is under 25 MB; and uploads never claimed by a submit are deleted after 24 hours. No extra pen test is needed.

Storage costs don't change. The API stops handling photo bytes, which removes the reason for the two September servers.

## Alternatives considered

- **A longer gateway timeout.** Security rejected it: the setting is global, and longer timeouts widen slow-request attacks on every route.
- **Chunked uploads through the API.** This fixes the timeout but keeps photo bytes, and the extra servers, on our side, with the most new server code of the three options.

## Rollout

API work (signing endpoint and submit check) takes two sprints and runs alongside three sprints of app work for the upload queue. App 4.12 ships the new path, targeted for the stores in mid-January. The old submit endpoint stays up for older apps until the question below is settled.

## Open questions

**Force the upgrade, or keep the old path?** The review decides, before 16 November.

- Force it: on 31 January the old endpoint switches off and older versions are blocked. Inspectors on iOS 15 (335 people, about 9%) can't install 4.12, because it needs iOS 16 for background uploads, so they stop being able to submit until they get new devices.
- Keep it: everyone keeps working, and the photo-buffering servers stay, at roughly £1,800 a month, with no end date.

Bram (mobile) and Aiko (platform) disagree, which is why it comes to the review.
