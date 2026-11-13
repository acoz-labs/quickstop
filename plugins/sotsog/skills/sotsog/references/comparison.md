# Comparing with what we have

## Pull out the principles

A principle is a mechanism you could check for in a repo: "every pull request deploys a preview", not "fast feedback matters". Split a bundled idea into its principles; each gets its own row.

## Find how we do it today

Read the files that would hold each principle: the contributing guide, the README, scripts, CI configuration, templates, earlier decisions, incident notes. Cite the file and what it does. When you rely on the user's description instead of a file, say so in the row ("per the user").

## Question our side

Read our side as skeptically as the source:

- **Does it work, or does it only exist?** A config file or a doc that says we do it shows only that it exists. Evidence that it works is a test that exercises it, a log or CI run showing it ran, a result, or a past incident it caught (or failed to catch).
- **Docs against reality.** Where the docs describe a process, check the code or logs that should carry it out. A documented step that no script runs is on paper only.
- **Measured against what.** Say whether we know ours works or assume it.
- **Known weak spots.** Look in the repo's history, incident notes and issues for recent failures, workarounds and complaints about the area.
- **Whose conditions.** Ours may have been built for an older scale, team or setup; say if that no longer holds.
- **The user's own claims.** List what you couldn't check. When the user says something works, ask briefly how they know, and record the answer.

## Rate the fit

Use exactly one rating per principle:

| Rating | Meaning |
|---|---|
| already have | we do this today, and there's evidence that it works (name it) |
| on paper only | it's written down or configured, but nothing shows it works |
| partly | we do some of it, or informally |
| gap | we don't, and it would help |
| conflicts | it would break something we rely on |
| doesn't apply | it solves a problem we don't have |

Then list what the idea would remove or weaken. A conflict with something the user relies on (a funder's or customer's condition, an audit, a legal duty, a promise to users) usually decides the outcome on its own; say what it is and where it's written down.

## Example

An idea: "short-lived feature branches with automatic preview deployments", compared with a small web shop's repo.

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Branches live under a day | team rule, flagged in standup | `CONTRIBUTING.md` asks for merges within a day, but most branches last month merged after two to three days (git log) | on paper only |
| Every branch runs the tests | CI on each push | CI runs the suite on every push and blocks merge on failure; it blocked two merges last month (CI history) | already have |
| A preview deployment per branch | CI deploys each branch to its own URL | no previews; reviewers run it locally | gap |
| Previews deleted on merge | CI cleans up on merge | doesn't arise | doesn't apply |
| Product owner approves the preview | required before merge | product owner reviews after release (per the user) | conflicts |

The first row is on paper only because the rule is written down but the history shows it isn't followed. The last row conflicts because the shop's product owner works one day a week; requiring their approval before merge would stall every branch.
