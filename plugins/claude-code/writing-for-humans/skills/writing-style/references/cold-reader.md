# The Cold Reader

This is a check, not a review. One fresh-context subagent reads what is about to be shown to a human, with none of the context the current session has, and reports what it understood. If it cannot say what is being asked, that is evidence the draft may need more context, not proof that a human would misunderstand.

This exists because **the writer is the worst possible judge of whether their writing is context-independent.** By the time a question gets drafted, the agent has traced the code, read the ticket, and named things in its own shorthand. Every referential shortcut reads as obvious from inside that context. A fresh reader can expose those shortcuts.

## When to run it

Consider it for a consequential or persistently unclear question that hands a human something to read and act on: open questions from an investigation, questions posed alongside a design artifact, risks that need a decision, and “needs your attention” items in a review.

Scope it to the parts meant to be answered, not the whole artifact. Proof sections still follow every writing rule, but a misunderstanding there does not block an answer, so they do not need this particular check.

Skip it when there is nothing to ask. A clean artifact with no open questions has nothing for the cold reader to fail.

Use it only when delegation is already authorized and a fresh-context reader is available. It is optional, never a required call for every reply or question. If unavailable, check the draft directly and say no independent reader was used when reporting verification.

## Dispatch

Use one subagent with no tools beyond reading what you provide. Give it **only the text** and say so explicitly: no repository path, ticket link, or session summary. Withholding context is the mechanism. Adding context to be helpful destroys the check.

Ask it 4 things:

1. **In your own words, what is being asked?** One sentence per question.
2. **What would you need to look up** to answer it? Name each file, ticket, acronym, or term you could not resolve from the text.
3. **Do you know what changes** depending on the answer?
4. **Which sentences did you have to read twice?**

Have it return `{questions: [{restated, lookups_needed: [], stakes_clear: bool, reread: []}]}`.

## Acting on it

- **Restated incorrectly or vaguely.** Check the restatement against the draft. Correct a genuine ambiguity; the reader can also be mistaken.
- **Any `lookups_needed`.** Replace the missing context with plain words and move the citation to `<details>`.
- **`stakes_clear: false`.** Add what turns on the answer.
- **Anything in `reread`.** Rewrite the sentence rather than defending it.

A cold reader that restates every question correctly, needs no lookups, knows the stakes, and rereads nothing is the pass condition. Use at most one reader call for the draft, then revise directly. Report unresolved ambiguity rather than launching an open-ended loop.

## What it is not

It does not judge whether the question is worth asking, whether a finding is right, or whether the prose is stylish. It answers one question: **would this be understandable to someone who was not here?** Keep the job narrow, or it starts reviewing content it has no context to review.

