# Three fictional examples

[Back to Shipshape](README.md)

These invented scenarios illustrate adaptation choices. They are not accounts
of customer projects or evidence of successful harness tests.

## A small fix in a solo documentation project

**Situation.** A static guide for a fictional community garden has a broken
navigation link. Its contributor guide already explains previews and the link
checker. The user asks an agent to fix the link and prepare a pull request.

**Adaptation.** No new workflow files are needed. The task is bounded: the link
must reach the existing composting guide, the menu must remain usable, and the
stopping point is an open pull request. The agent edits the link, runs the
documented checks, and inspects the affected navigation in the preview.

**Review and delivery.** There is no second reviewer available during this task.
The project permits self-review for routine prose edits, so the agent records
its self-review and checks without calling them independent acceptance. It
prepares the pull request and stops. The site has not been published.

**What would add friction.** Requiring a discovery document, a new issue system,
an approved implementation plan or deployment access for this task.

**Useful final report.** “The navigation link is corrected in the pull request.
The link checker passed and the preview navigation reaches the guide. Review
was a self-review; the live site is unchanged.”

## An ambiguous feature in a team application

**Situation.** A fictional equipment-lending application has required peer
review and automated checks. A user asks for “better reminders” but has not said
whether the problem is missed returns, message volume or confusing wording.

**Adaptation.** The agent asks which outcome matters before choosing a feature.
The team identifies repeated reminders after an item has already been returned.
An existing issue captures the desired result: a returned item must not generate
a scheduled reminder, while outstanding loans still receive the agreed notice.

The current process already covers testing and peer review. The only useful
documentation addition is a short instruction to record observable completion
criteria in feature issues. No second review system or Shipshape installation
is needed.

**Implementation and verification.** A short plan is useful because scheduling
and return processing can race. The contributor uses the project's isolated
test environment and synthetic loans, checks both event orderings, and confirms
that valid reminders still work. An authorized peer reviews the final candidate.
No real borrowers receive test messages.

**Delivery.** The task authorizes a tested change and pull request, with release
handled by the team's scheduled deployment. The report identifies the reviewed
commit and checks, and says deployment remains pending. Required peer review
is preserved even if the agent could finish sooner without it.

**What would add friction.** Asking the user to approve every routine design
choice after the outcome and scope are clear, or importing unfamiliar role names
and mandatory planning templates.

## A consequential release with data changes

**Situation.** A fictional parcel-tracking service must move delivery history
to a new storage format. Its team authorizes implementation and production
release, but requires separate release acceptance and verified recovery. Its
existing deployment script rebuilds from a moving branch each time.

**Adaptation.** The concrete gap is candidate identity: the tested build may
differ from the deployed build. The team changes the existing pipeline to build
from a fixed commit, retain the artifact and digest, and promote that artifact.
The release record also identifies the migration and relevant configuration.
This is executable delivery work and follows the repository's normal code review.

**Verification.** A plan is warranted. The team rehearses migration on isolated
synthetic data, checks representative history queries and interruption handling,
and measures whether the migration fits the intended release window. It verifies
a recoverable backup and restoration procedure; reverting application code alone
would not restore the old data format. A distinct authorized acceptor reviews
the candidate and recovery evidence.

**Missing capability.** Suppose the restoration rehearsal fails. Acceptance
remains unsuccessful, and production release does not proceed. The team fixes
the procedure or escalates the unresolved constraint with evidence. It does not
call an untested backup “verified” or remove the recovery criterion to ship.

**Delivery.** After the corrected candidate passes acceptance, the authorized
release operator promotes it, verifies production queries, and records artifact
identity, migration result and recovery status. An interrupted deployment is
inspected before retrying. Existing authorization covers these routine release
steps; it does not cover unrelated changes to other services.

**What would add friction.** A mandatory new staging service when an adequate
isolated environment already exists, or another owner approval after every
successful check. What would be insufficient is treating a merged pull request
as proof that the service and its data were safely released.
