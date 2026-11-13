# sotsog

sotsog ("stand on the shoulders of giants") helps you decide whether to adopt an idea from outside: a practice from a blog post, a tool another team uses, a workflow from a paper. Give it the link and ask "should we adopt this?" It researches beyond that one link, reads the sources skeptically, compares the idea with what your repo or workflow already does, asks you what only you can answer, and writes a decision document: adopt, adapt, not now or no.

It's one skill that follows the [Agent Skills specification](https://agentskills.io/specification), so it works in any agent tool that reads skills. Nobody types its name: it triggers on plain requests such as "should we adopt X", "is this worth bringing into our repo", "compare this approach with ours" or "here's a post about how team Y does Z, should we?".

## What you get

- **Research beyond your link:** where the idea came from, independent teams using it, evidence, critiques and failures, and other answers to the same problem.
- **A written skeptical read:** who gains if you adopt it, what it was measured against, what's missing, whose conditions it was proven under, and whether anyone without a stake agrees.
- **An honest comparison:** your own side questioned as hard as the source (does it work, or does it only exist on paper?), and each principle of the idea rated against your actual files as already have, on paper only, partly, gap, conflicts or doesn't apply.
- **Findings and at most five questions,** each with a recommended answer.
- **A decision document** in your repo's decisions folder. On a go, it includes an implementation brief an agent with no other context could start from. On a no, it says why, what would change the answer, and anything still worth borrowing.

The skill stops at the document. It never starts the implementation.

## Install

In Claude Code:

```sh
/plugin marketplace add acoz-labs/quickstop
/plugin install sotsog@quickstop
```

In another agent tool, copy `skills/sotsog/` into the folder that tool reads skills from.

## Limits

- sotsog is a workflow: its results depend on the model and agent tool running it.
- Research is only as wide as the agent's access. Without web access, it asks you to paste or point to sources and says the research is limited to them.
- Fetched pages are treated as data; instructions inside them are ignored and reported.
- The decision document never copies secrets or private data from your repo, but review it before sharing it.
