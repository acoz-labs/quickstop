# Your CI is running 90% too many tests

Source: https://prescient-ci.example.com/blog/ci-90-percent-faster
Author: Victor Ashdown, founder and CEO, Prescient CI
Published: 2026-10-08

Every push, your CI runs every test, even though most of them can't possibly
be affected by the change. That's wasted time, wasted money and wasted focus.

At Prescient we built **Prescient Select**, which uses AI to predict which
tests a change can affect and runs only those. The principles behind it:

1. **Map tests to code.** Learn from past runs which tests exercise which
   files.
2. **Predict per change.** For each push, score every test's chance of
   failing and run only the likely ones.
3. **Run the full suite later.** A nightly full run catches anything the
   prediction missed.
4. **Fail fast.** Run the most likely failures first, so developers hear
   about breakage in seconds.

Teams using Prescient Select cut CI time by up to 90%. "It changed how we
work," says the CTO of one of our customers. Developers get feedback in
minutes instead of hours, and cloud bills drop with every push.

Prescient Select works with every major CI service and installs in five
minutes. Start a free 14-day trial today.
