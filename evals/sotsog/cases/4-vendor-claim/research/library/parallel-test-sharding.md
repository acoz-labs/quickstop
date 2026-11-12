# Speed up CI by sharding, not skipping

Source: https://ci-handbook.example.org/guides/sharding
Author: CI Handbook contributors (community-written guide)
Published: 2026-06-30

Split the test suite across several machines and run the parts at once. Every
test still runs on every change, so nothing is missed, and wall-clock time
falls roughly with the number of shards. Caching dependencies between runs
often saves another minute or two. Costs more machine time, not less.
