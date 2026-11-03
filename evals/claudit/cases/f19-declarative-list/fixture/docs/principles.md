# Design principles

1. The public API is stable within a major version.
2. Errors are values; the library never panics on input text.
3. The standard library is the only dependency.
4. Counting is deterministic: the same text gives the same counts on every platform.
5. Markdown syntax is not counted as words; link text is, link targets are not.
6. Reading time is an estimate in whole minutes, rounded up, at 230 words per minute.
7. Every exported function has an example in its test file.
