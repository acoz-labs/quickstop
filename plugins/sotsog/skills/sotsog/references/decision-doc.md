# The decision document

Use these headings exactly, in this order. Leave out "Implementation brief" on no or not now, and "What we're not taking" on adopt when nothing is left out.

```markdown
# <Idea>: <adopt | adapt | not now | no> for <repo or workflow>

<Sentence 1: the decision.> <Sentence 2: what happens next, or that nothing does.> <Sentence 3: what changes or what's at stake.>

Date, who decided, sources read.

## The idea in brief
2-4 plain sentences; define any term a reader might not know.

## What the evidence shows
Merit verdict and why. The skeptical read, each by its label: **Who gains**, **Measured against**, **What's missing**, **Whose conditions**, **Independent support**. How wide the research went.

## How it compares with what we do
| Principle | How they do it | How we do it | Fit |

## Why this decision
Gains, costs, risks; the strongest case against (skeptic pass); the user's answers that shaped it.

## Revisit when
Concrete triggers. On a go, includes when to roll back.

## Implementation brief
(go only) Goal (one sentence); in scope / out of scope; changes in order, each naming the file or step; acceptance criteria; how to tell it worked (what to measure, when); how to verify and roll back; open risks.

## What we're not taking, and why
(required on no and not now; on adapt, the principles left out) Each principle rated partly or gap that isn't taken: taken now, held for a named trigger, or dropped. Anything worth borrowing, from the idea's side practices or other sources, and whether it's taken now.

## Sources
One list item per source: link or file path and the date read (YYYY-MM-DD); who wrote it and what they gain; shown versus claimed; the conditions it was proven under.
```

The outcome in the title is one of the four words, in lower case. The fit column uses only: already have, partly, gap, conflicts, doesn't apply.

## A go example

```markdown
# Consumer-driven contract tests: adapt for the Fieldnote mobile app

We'll add contract tests for the six API endpoints the mobile app calls, run on every API pull request, but not the shared contract broker the source recommends. The brief below is ready to hand to whoever picks it up. Three of last quarter's five app crashes came from API changes the app wasn't told about.

Date 2026-10-02. Decided by the mobile and API leads. Sources read: the original post and six others.

## The idea in brief
In a contract test, the client (here, the mobile app) writes down exactly which fields it reads from each API response, and the API's test suite checks every change against that record. A "broker" is a shared service that stores the records and tells each side when they break.

## What the evidence shows
Sound with caveats: well established, but the broker adds upkeep that small teams report regretting.
- **Who gains:** the post's author maintains the broker product, offered as paid hosting.
- **Measured against:** a before-and-after at the author's company (integration failures fell from 11 to 2 a quarter); no other baseline.
- **What's missing:** the broker's running cost and setup time.
- **Whose conditions:** 40 services and 12 teams; we have one API and one client.
- **Independent support:** two independent teams report fewer integration breaks; one dropped the broker after a year and kept the contracts in the API repo. A critique argues contract tests only catch shape changes, not behaviour changes.
Seven sources; one conference talk couldn't be reached.

## How it compares with what we do
| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| The client records what it reads | per-client contract files | none | gap |
| The API checks every change against them | in CI | API tests check the API's own examples only | gap |
| A broker shares contracts | hosted broker | one client, one API, same organisation | doesn't apply |

## Why this decision
Gain: the three crash-causing changes would each have failed a contract test. Cost: about three days to write the six contracts, then minutes per API change. Strongest case against: end-to-end tests could catch the same breaks, but ours take 40 minutes and run nightly, a day too late. The leads' answer that the app ships weekly made a same-day signal the priority.

## Revisit when
- A second client (the web app) starts calling the API: reconsider the broker.
- Roll back if contract failures block more than two correct API changes a month.

## Implementation brief
**Goal.** An API change that breaks a field the mobile app reads fails CI before it merges.
**In scope:** contracts for the six endpoints in `app/src/api/`, a contract check in the API's CI. **Out of scope:** a broker, other clients.
1. In the app repo, add `contracts/` with one file per endpoint listing the fields and types the app reads.
2. In the API repo, add `tests/contract/` with a test that loads those files (pinned by commit) and checks each endpoint's response.
3. Run it in the API's CI on every pull request.
4. Document in both READMEs how to change a contract.
**Acceptance:** removing a field the app reads from any of the six responses fails the API's CI.
**How to tell it worked:** count app crashes from API changes per quarter; target zero next quarter.
**Verify and roll back:** delete a field in a test branch and watch CI fail. Roll back by removing the CI step.
**Open risks:** contracts drift if app developers forget to update them.

## What we're not taking, and why
The broker: one client and one API don't need a shared service.

## Sources
- The original post, https://example.com/contract-testing, read 2026-10-01. Broker maintainer; before-and-after shown, "teams love it" claimed. 40 services.
- An independent team's report, https://example.org/contracts-a-year-on, read 2026-10-01. Measured break counts; dropped the broker.
```

## A no-go example

```markdown
# Moving to a monorepo: no for the Fieldnote services

We'll keep the three repositories as they are. Nothing changes now. A monorepo would need a build system rewrite none of the four engineers has time for, to solve a problem (cross-repo changes) that comes up about twice a year.

Date 2026-09-14. Decided by the engineering lead. Sources read: the original talk and five others.

## The idea in brief
A monorepo keeps every project in one repository, so one change can update a library and all its users together. It usually needs a build tool that only rebuilds what changed.

## What the evidence shows
Sound with caveats: it pays off where many projects change together often.
- **Who gains:** the speaker's company sells a monorepo build tool.
- **Measured against:** nothing; "dramatically faster" with no figures.
- **What's missing:** migration cost; teams that went back.
- **Whose conditions:** hundreds of engineers and projects; we have four engineers and three repos.
- **Independent support:** two independent reports favour it at large scale; a critique from a 10-person team describes six months of build tooling work and a return to separate repos.
Six sources.

## How it compares with what we do
| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| One change updates a library and its users | one repository | two pull requests, about twice a year | partly |
| Rebuild only what changed | dedicated build tool | each repo builds in under 3 minutes | doesn't apply |

## Why this decision
Gain: two fewer pull requests twice a year. Cost: weeks of build work and a new tool to learn. Strongest case for it: the shared library may grow. If it does, the triggers below catch it.

## Revisit when
- Cross-repo changes happen more than once a month.
- The team grows past ten engineers.

## What we're not taking, and why
All of it. One change updating a library and its users (partly today) is held for the first trigger above. Nothing is worth borrowing now: pinning the shared library by version already gives us its main safety benefit.

## Sources
- The original talk, https://example.com/monorepo-talk, read 2026-09-13. Speaker's company sells the build tool; claims only.
- A 10-person team's critique, https://example.org/back-to-polyrepo, read 2026-09-13. Measured migration effort.
```
