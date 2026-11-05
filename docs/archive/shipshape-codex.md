# Archived Shipshape Codex package

Shipshape's Codex package (`plugins/codex/shipshape`) was removed on 2026-11-05 by [issue 202](https://github.com/acoz-labs/quickstop/issues/202), when Quickstop became a Claude Code-only marketplace. It was never released: its acceptance was blocked because no Codex host was available to test it in.

The package remains at [f4900063106e04f36e0360eb152c61941ef32f9b](https://github.com/acoz-labs/quickstop/tree/f4900063106e04f36e0360eb152c61941ef32f9b/plugins/codex/shipshape), tagged `archive/shipshape-codex-2026-11-05`, together with its acceptance procedure (`docs/acceptance/shipshape.md`) and tests (`tests/test_shipshape.py`). Recover it from the tag if a future task justifies it and the package can be tested in its tool.

The same issue removed Quickstop's Codex and Pi adapters (the Codex and Pi indexes, the Pi package list and their validators), since no plugin for either tool could be tested. The tagged commit still has them. The last `main` commit with them is [9fbd2ece931c18efec62ff4d8ed02813d4932a89](https://github.com/acoz-labs/quickstop/tree/9fbd2ece931c18efec62ff4d8ed02813d4932a89), which removed the Shipshape package; the next commit, `a02398d6193cf29ba0888485e564f7fdb666eb4b`, removed the adapters.

The Shipshape workflow guide in `workflows/shipshape/` is unaffected: it is process documentation, not the package.
