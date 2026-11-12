# Comparing with what we have

## Pull out the principles

A principle is a mechanism you could check for in a repo: "every pull request deploys a preview", not "fast feedback matters". Split a bundled idea into its principles; each gets its own row.

## Find how we do it today

Read the files that would hold each principle: the contributing guide, the README, scripts, CI configuration, templates, earlier decisions, incident notes. Cite the file and what it does. When you rely on the user's description instead of a file, say so in the row ("per the user").

## Rate the fit

Use exactly one rating per principle:

| Rating | Meaning |
|---|---|
| already have | we do this, in substance, today |
| partly | we do some of it, or informally |
| gap | we don't, and it would help |
| conflicts | it would break something we rely on |
| doesn't apply | it solves a problem we don't have |

Then list what the idea would remove or weaken. A conflict with something the user relies on (a funder's or customer's condition, an audit, a legal duty, a promise to users) usually decides the outcome on its own; say what it is and where it's written down.

## Example

An idea: "short-lived feature branches with automatic preview deployments", compared with a small web shop's repo.

| Principle | How they do it | How we do it | Fit |
|---|---|---|---|
| Branches live under a day | team rule, flagged in standup | most branches merge in two to three days (`CONTRIBUTING.md`) | partly |
| A preview deployment per branch | CI deploys each branch to its own URL | no previews; reviewers run it locally | gap |
| Previews deleted on merge | CI cleans up on merge | doesn't arise | doesn't apply |
| Product owner approves the preview | required before merge | product owner reviews after release (per the user) | conflicts |

The last row conflicts because the shop's product owner works one day a week; requiring their approval before merge would stall every branch.
