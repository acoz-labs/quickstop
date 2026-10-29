---
name: add-slug-rule
description: Add a transliteration rule to slugsmith with a test. Use when asked to support a new character, letter or symbol in slugs.
---

# Add a transliteration rule

1. Check `src/rules.js`; if the character already has a rule, stop and tell
   the user what it maps to.
2. Add the rule to `RULES` in `src/rules.js`. Keys are single lowercase
   characters.
3. Add a test to `test/slug.test.js` that shows the input title and the
   expected slug.
4. Run `npm test` and `npm run lint`.
5. If the rule changes the slug of any input that previously produced a
   different slug, tell the user it is a breaking change (see the Gotchas in
   CLAUDE.md).
