# The hidden cost of skipping tests

Source: https://blog.example.com/ken-oyelaran/hidden-cost-of-skipping-tests
Author: Ken Oyelaran, independent consultant on testing practice
Published: 2026-08-28

When a selector skips a test that would have failed, the break is found
hours later, by the nightly run or a user, after more changes have landed on
top of it. The person who caused it has moved on, and finding the culprit
takes longer than the CI time saved. For short suites, run everything; the
cheapest test run is the one that tells you straight away.
