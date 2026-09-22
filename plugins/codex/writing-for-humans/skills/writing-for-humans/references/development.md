# Development writing

For a PR, describe observable behavior before and after the change, why the difference matters, and verification that supports the claim. Preserve the repository template. Name material limitations. Distinguish an existing test from a proposed test and from an observed passing run; do not turn supplied test coverage into a future instruction or imply it passed without evidence. Rewrite the description around the final change when its scope changes.

For a commit, describe one coherent change and lasting rationale using repository conventions. Preserve required trailers and attribution exactly. Writing guidance does not authorize amending, rebasing or publishing history.

For a review, explain the verified behavior and consequence at a precise anchor. Separate what is established from a suspected failure and from a preferred remedy. A visible code symbol can supply context, but a location alone cannot explain the problem. Follow existing severity conventions without inventing findings from voice preferences.

For an issue, describe the problem, affected user, intended outcome, bounded scope and observable acceptance. Include available reproduction steps and expected versus actual behavior for a bug. Missing facts remain missing: do not invent owners, dates or reproduction evidence. An update describes what changed, what remains and who needs to act only when known.

Evidence should support an intelligible claim. Put essential caveats in the main explanation. Use collapsible GitHub evidence only when it improves reading; do not assume another destination supports it.
