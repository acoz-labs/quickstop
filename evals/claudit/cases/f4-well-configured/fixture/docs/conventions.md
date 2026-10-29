# Conventions

- ESM only, named exports, no default exports.
- No runtime dependencies. Dev tooling uses only Node built-ins.
- Every new transliteration rule gets a test in `test/slug.test.js` showing
  the input and expected slug.
- Commit titles use Conventional Commits (`feat:`, `fix:`, `chore:`).
