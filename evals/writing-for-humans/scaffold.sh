#!/usr/bin/env bash
# Build one eval workspace: run with cwd = the empty workspace. Commits the base
# fixture on main, then adds the branch fixture on a feature branch, so the
# audit has a branch diff to read. Writes only to the workspace.
set -euo pipefail

suite=$(cd "$(dirname "$0")" && pwd -P)
if [ -n "$(find "$suite/fixture" -type l -print -quit)" ]; then
  echo "scaffold: fixture contains symlinks" >&2
  exit 65
fi

# Operator git configuration (hooks, signing, templates) must not leak in.
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME="Eval Fixture" GIT_AUTHOR_EMAIL=fixture@example.invalid
export GIT_COMMITTER_NAME="Eval Fixture" GIT_COMMITTER_EMAIL=fixture@example.invalid
commit() {
  git add -A
  GIT_AUTHOR_DATE=$1 GIT_COMMITTER_DATE=$1 git -c commit.gpgsign=false commit -q --no-verify -m "$2"
}

git -c init.defaultBranch=main init -q
cp -R "$suite/fixture/base/." .
commit 2026-01-01T00:00:00Z "Add tidecache"
git switch -q -c ttl-decision
cp -R "$suite/fixture/branch/." .
commit 2026-01-02T00:00:00Z "Lower the cache TTL and record the decision"
