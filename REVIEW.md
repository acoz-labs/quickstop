# Review

How a reviewer judges a PR here. Read the issue first, and the change's
`docs/changes/<issue>-<slug>/plan.md` when it has one. Repository facts live
in `docs/repository.md`.

## Passes

Make each pass over the whole diff.

### Bugs

Wrong behaviour, failure paths the change can hit, edge cases, and data or
state the change could lose or corrupt.

### Security

Secrets in code, logs or fixtures; untrusted input reaching commands, queries
or output; permissions or access widened. A new allow rule is
exact; probe appended arguments under `dontAsk`.

### Security (risky changes)

In addition to Security, required when the change touches any of:

- secrets or their handling;
- authentication or permissions;
- release, deploy or CI scripts; dependency or install scripts;
- money: payments, billing, prices, invoices, refunds, payouts;
- personal information: customer or user records, names, emails,
  addresses, payment details, and anything that logs, exports or shares
  them;
- deleting or migrating stored data;
- anything that sends messages to real people (email, texts,
  notifications);
- anything that makes a service, file or endpoint publicly reachable, or
  changes who can reach it.

Post it as its own section of the review, naming the category that
triggered it and what was checked. A high finding blocks merge. When none
applies, the review says "Security (risky changes): not triggered", in one
line.

### Tests

Each behaviour the change adds or fixes has a test that would fail without
it. For an eval or grader change, the reviewer says CLEAR FOR GATE
(not approve) before the paid gate, so the gate runs on a reviewed tree, and
verifies the trace from recorded output without rerunning paid runs. On a bug fix, a change to a pre-existing test that the fix makes pass is
a high finding unless the PR explains why.

### Docs and release

Durable docs match what ships; the version, changelog or release notes the
repository's process expects are in the PR. Publish the
`bin/sdlc-evidence` receipt before approving; otherwise `bin/sdlc audit`
fails for that merge for good.

### Compliance

The PR does what the issue and `plan.md` say, all of it and nothing else.
A departure from the plan updates `plan.md` in the same PR.

## Severity

- **High**: wrong behaviour, data loss, a security hole, or an acceptance
  criterion not met. Blocks merge.
- **Medium**: a real defect or gap with a workaround or a narrow trigger, or
  missing proof for a claim. Fixed in this PR unless the reviewer agrees to
  a follow-up issue.
- **Low**: worth fixing, harmless if not. Doesn't block.

Report at most 5 lows per review and give the rest as a count.

## Escapes

A fix for something an earlier merged change should have caught is an
escape, and so is a revert of a merged change. Whoever files its issue or
PR applies the `escape` label and names the original PR:
`Escape from #<n>`. The reviewer checks for both on such a PR and asks for
whichever is missing.

## Do not report

- Style a formatter or linter in `bin/ci` already enforces.
- Preferences with no effect on behaviour, safety or clarity.
- Pre-existing problems the diff doesn't touch; file an issue instead.
- Automated review-bot noise already triaged.
