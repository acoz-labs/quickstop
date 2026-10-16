# Shipshape for Codex — candidate 0.1.0

Optional shared role instructions and offline Python standard-library helpers.
The Quickstop Shipshape guide remains canonical; guide-only adoption is valid.
This candidate is publicly discoverable in the catalog, but is not accepted,
published or installable through the accepted native indexes. First release waits for
full integrated acceptance of the assigned issue. Native install/runtime and
independent lifecycle acceptance remain pending.

Install one pinned version into separate author/reviewer environments, rather
than copying it into every consumer repository. Record package digest, guide
commit, harness/tool revisions and config digest for each run. No autoadoption
or automatic upgrade. Existing `.sdlc/config.json` remains the local contract;
preserve stronger rules and explicit stopping points. Installation supplies no
credentials, sandbox, reviewer, service, webhook, or execution authority.

Routes: `shipshape` shapes and checks scope; `shipshape-implement` implements and
corrects; `shipshape-review` independently executes review and hands off
acceptance/closeout. Read [runtime obligations](references/runtime.md) and the
[operator protocol](references/operator.md). Resolve resources relative to the
installed SKILL.md directory. The helper is `scripts/shipshape.py` relative to
this README, and requires Python 3.11 stdlib. Never depend on a source checkout.
Run the contained offline synthetic exercise with `python3 examples/run.py` from
this directory (also requires Git). It creates and removes only temporary fixture
state. See the operator protocol for trusted observations and `--handoff-root`;
the exercise does not establish native loading or independent acceptance.

Native lifecycle is version-sensitive. Before installation, inspect the current
Codex host's plugin management help and supported Agent Plugins manifest loading.
Use that host's native local candidate loading procedure in an isolated profile;
record exact commands and installed-cache digest. No universal install command
is asserted here. If the host lacks native loading, stop with a capability gap.
After an accepted marketplace release, select only its immutable accepted pin.
Start a fresh session and verify all three skills and installed helper paths.

Disable through the host's supported plugin management surface; end existing
sessions and verify absence in a fresh session. Uninstall through that same
version's native removal procedure, preserving private run records separately.
Do not delete arbitrary caches or personal configuration. Recovery reinstalls a
previous accepted pin and verifies its installed digest in a fresh session.
This is an initial candidate with no previous accepted Shipshape package.
Disable/uninstall/recovery have not been exercised by static package checks.
