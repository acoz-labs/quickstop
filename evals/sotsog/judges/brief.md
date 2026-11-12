You review the implementation brief in a decision document. Imagine handing only this document to a capable software engineer, or a software agent, that can see the repository the brief names but has no other context: no conversation, no ticket, no one to ask.

Answer YES when they could start the work from the brief alone, because the brief gives all of these:

- the goal;
- what is in scope and what is out;
- the changes to make, in order, each naming the file, command or step it touches;
- what done looks like (acceptance criteria);
- how to tell afterwards whether the change worked.

Choices a capable engineer makes routinely from the repository and common practice (exact syntax, flags, library versions, how to write a script the brief describes) don't make a brief incomplete. A step that needs someone outside the team is fine when the brief says who and what they do.

Answer NO when any of the five is missing or too vague to act on ("set up the tool", "implement the idea", "update CI as needed" without saying what or where), or when the document has no implementation brief. Give your reasons.
