# Sign your releases and publish how they were built

Source: https://blog.example.org/ines-carvalho/sign-your-releases
Author: Inês Carvalho, maintainer of Wrenfold, an open-source image library downloaded about 2 million times a month
Published: 2026-07-01

Last year someone uploaded a tampered copy of Wrenfold to a mirror. Our users
had no way to tell it from the real thing. Since then, every release is signed
and comes with a record of how it was built. What we do:

1. **Sign every release artifact** with keyless signing: the CI job signs with
   a short-lived certificate tied to our repository, and the signature goes into
   a public transparency log. No long-lived key to lose.
2. **Publish build provenance:** a signed statement of which commit, which
   workflow and which build environment produced each file.
3. **Build only in CI,** from a tagged commit, never on a maintainer's laptop.
4. **Tell users how to verify,** with one command in the install docs.

Setting it up took about two days. Since then, two large companies that
depend on Wrenfold told us they can now approve new versions without a manual
review, and three downstream packagers verify our signatures automatically.
