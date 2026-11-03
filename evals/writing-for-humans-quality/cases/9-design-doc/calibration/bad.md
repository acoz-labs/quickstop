# Photo upload redesign

This document was written from the notes in the notes folder. I read problem.md first, then the meeting notes, then options.md, then the security review and the two CSV files. It follows the design doc template and covers each section in turn.

## Summary

This doc describes the photo upload redesign.

## Problem

A gateway is a server that sits in front of an API and forwards requests to it. A timeout is the maximum time a request may take before it is cut off. Object storage is a service for storing files such as photos. `problem.md` says 6.0% of submits fail with a gateway timeout. client-versions.csv lists four app versions.

## Proposal

Option C from options.md. `security-review.md` lists five conditions. The app uploads photos using signed URLs.

## Alternatives considered

Options A and B, see options.md.

## Rollout

App 4.12, mid-January. device-os.csv shows the iOS split.

## Open questions

There's a question about old clients from the meeting.

## Conclusion

To conclude, this doc describes the photo upload redesign. Let me know if you have any questions or feedback before the review.
