# The process

[Shipshape](README.md) describes outcomes to achieve, not a fixed sequence of
ceremonies. Steps can overlap or repeat as new information arrives. Use existing
issues, pull requests and documentation to hold the information; do not create
parallel records merely to match this guide.

## Define the useful result

Identify who needs the change, what they should be able to do afterward, and the
constraints that matter. Distinguish confirmed facts from assumptions. Express
completion in observable terms: an example interaction, a corrected result, or
a release that can be checked in its real environment.

Clarify the task boundary. “Investigate,” “prepare a proposal,” “implement,” and
“publish” authorize different actions. Work within the authority already given;
do not ask for approval again just because a routine step is next. Ask when a
missing decision materially affects the outcome or would exceed that authority.
Continue useful unaffected work while a genuine blocker is unresolved.

For a small fix, a few sentences in an existing issue can be enough. For an
uncertain feature, explore the user need and alternatives before committing to
an implementation. Document only what will help someone decide, build or review.

## Choose the amount of planning

Consider uncertainty, reversibility, data exposure, dependencies and the cost of
failure. Use a plan when it helps resolve these, with enough detail to identify
the approach, relevant tradeoffs, checks and recovery path. A plan is optional
unless the project's applicable rules require it.

Split large work into useful increments. Record unanswered questions and the
next action rather than pretending the design is settled. Revise the plan when
facts change; explain material scope changes. Do not quietly weaken acceptance
criteria to make a failing implementation pass.

## Make ownership clear

Identify who can decide scope, implement, review, accept the outcome and release.
These are responsibilities, not required job titles or a mandated team size.
Use the project's existing roles and tools. State which decisions are delegated
and which need someone else's authority.

Independent review requires a reviewer distinct from the author. A second pass
by the same agent, a switched account, or a test run is not independent review.
If an authorized separate reviewer is unavailable, record that limitation. Do
not bypass an existing requirement. In a project that permits self-review, call
it self-review and let the authorized owner determine whether that is sufficient
for the risk.

## Implement and check the behavior

Follow local instructions and existing patterns. Keep unrelated changes out of
the task. Test meaningful outcomes at the appropriate level: a relevant example
or build check for a small edit, behavioral tests for logic, and rendered checks
for user interfaces. Review keyboard use, responsive layouts and failure states
when the interface changes warrant them.

Run the repository's required checks. Record what ran, the candidate it checked,
results and relevant limitations. Preserve enough evidence for a reviewer to
assess the outcome without exposing secrets or personal data. A missing test
result means the result is unknown; it does not establish that testing never
happened.

Fix failures within scope and repeat affected checks. Do not broaden testing
indefinitely after the relevant checks pass unless new changes or unresolved
risks justify it.

## Review and accept the candidate

Review the actual changes against the intended behavior and applicable rules.
Resolve findings, then review the changed candidate. Old approvals and passing
checks do not automatically apply to new bytes.

Acceptance asks whether the result meets the task's criteria. Contributor test
reports are useful evidence but do not by themselves establish independent
acceptance. Use a distinct authorized reviewer or acceptor when local rules or
the risk require one. Retain the actual candidate identity and outcome.

For consequential releases, identify the source commit and immutable artifact
or digest, relevant configuration, the scenarios exercised and any limitations.
If your build system cannot promote the tested artifact, disclose that gap and
establish appropriate verification rather than claiming a different build was
accepted.

## Deliver to the agreed boundary

Choose the actual delivery target. For ordinary documentation, checked and
published files may complete the task. For a library or plugin, verify the
published artifact and instructions. For a service, promote the accepted
artifact and verify its behavior in the destination environment. Merging a pull
request is not proof of deployment.

Before a risky release, establish how to recover and who can act. A code rollback
may not reverse data changes. Use isolated data for destructive tests, and verify
backup or recovery procedures when the risk calls for them. If recovery requires
permissions or capabilities you lack, resolve that before the consequential
action. After an interruption, inspect deployment state and receipts before
retrying so that an uncertain result does not cause a duplicate operation.

Respect an explicit stopping point, such as a preview or approved artifact ready
for release. Otherwise continue through the delivery already authorized. Report
what is implemented, what was checked, what is published or deployed, remaining
limitations, and any concrete next action. Use “done” only for the agreed scope.
