# Questions We Ask the Human

Every workflow stage tends to end by asking something: open questions from an investigation, a design gate, a review's "needs your attention," a decision that can't be made without input. These are the highest-stakes prose an agent writes. A review comment nobody can parse wastes a colleague's minute; **a question nobody can parse blocks the work until they ask what it means**, and they have to spend that round trip before they can even start thinking about the answer.

The context-independence rule in the `writing-for-humans` output style is the floor. This file is how it gets applied to asking.

## The shape

Every question has four parts, in this order.

### 1. The ask, as a question, in one sentence

A real question with a question mark, stated so it can be answered without reading anything else. Not a topic label, not a noun phrase, not a statement of what you found.

- Wrong: "Route scoping."
- Wrong: "What 'who changed what is recoverable' means."
- Right: "When a seed donation has no quantity unit, should the inventory import skip that entry or reject the whole file?"

Bold it. It's what gets read first and often all that's needed.

### 2. Why it's a question at all

Two or three sentences of the situation, in plain words. What's true today, and what about it is unresolved. No identifiers as subjects, no coined shorthand, no ticket ids.

This is where the reader gets enough footing to have an opinion. It's the part most often skipped, because the writer already has the footing and forgets it was ever acquired.

### 3. The options and what each costs

A short list. Each option says what it means in practice and what it gives up. If you have a recommendation, say it and say why.

An option nobody would pick isn't an option, it's padding. Two real ones beat four where two are strawmen.

### 4. The evidence, out of the way

`file:line`, ticket ids, quoted criteria, precedent: all of it goes in a `<details>` block or a trailing parenthetical at the end. It's there to check, and it never sits in a sentence someone has to read to understand the ask.

## Worked example

**Before**, using an independently invented seed-library system:

> Unit ambiguity. `DonationFile.ts:41` accepts blank `quantityUnit`, while `ShelfCount.ts:92` requires it. A file can mix packets and loose seeds. Should we skip the row or fail the file?

The statement is precise and cited, but it makes the reader decode implementation details before understanding the decision or its consequences.

**After:**

> **When a seed donation has no quantity unit, should the inventory import skip that entry or reject the whole file?**
>
> The library imports a file of donated seeds. Quantities may count individual seeds or packets, so a number without its unit cannot be added reliably to the shelf inventory. The file reader accepts these incomplete entries, but the inventory requires a unit.
>
> - **Skip incomplete entries and report them.** Valid donations become available immediately, but someone must correct and import the skipped entries later.
> - **Reject the whole file and report the incomplete entries.** Nothing is imported until the file is corrected, so valid donations wait too; the file remains one import to track.
>
> I recommend skipping incomplete entries with a clear report so valid donations can be listed without guessing the missing units.
>
> <details><summary>Evidence</summary>
> `DonationFile.ts:41` accepts a blank quantity unit. `ShelfCount.ts:92` requires one. These file names and facts belong only to this fictional example.
> </details>

Same facts, same citations, no lookups needed to understand the ask.

## Rules

- **Ask sharp questions, not a survey.** Three that change the shape of the work beat ten that prove you read everything.
- **A question whose answer changes nothing doesn't get asked.** If you'd proceed the same way either way, decide it yourself and say what you decided.
- **Never ask someone to hold two things in their head at once** to answer one question. If the question needs a comparison, put the comparison in the question.
- **Quote, don't point.** An acceptance criterion, a ticket line, a documented rule: paste the words. "AC 3" is a lookup; the sentence itself is an answer someone can react to.
- **One question per question.** Two asks bundled into a paragraph get one answer covering whichever was noticed.
- **Say what you'd do.** A recommendation can be overruled in a word. An open-ended question makes the reader redo structuring you already did and threw away.

## The cold-reader check

For a consequential or persistently unclear question, consider the optional cold reader (see `cold-reader.md`). Within existing delegation authorization, one fresh-context subagent sees the questions and reports what it understood. Check its interpretation against the draft and revise genuine ambiguities. This does not create a new approval gate or require a call for every question.

The instrument is the same one a good review process uses on code: a reader who lacks context sees what a context-laden one can't. This points it at our own writing.
