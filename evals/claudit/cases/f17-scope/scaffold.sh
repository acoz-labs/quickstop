#!/usr/bin/env bash
# The repo is checked out inside a parent folder (the workspace's parent: the run's home in claude plugin eval)
# that has its own CLAUDE.md and AGENTS.md, and the repo's CLAUDE.md is a symlink to its AGENTS.md. Fixtures
# carry no symlinks or live instruction files, so this script adds both after the shared scaffold.
set -euo pipefail
case_dir=$(cd "$(dirname "$0")" && pwd -P)
bash "$case_dir/../../scaffold.sh" "$case_dir/fixture"
parent=$(cd .. && pwd -P)
for name in CLAUDE.md AGENTS.md; do
  if [ -e "$parent/$name" ] || [ -L "$parent/$name" ]; then
    echo "scaffold: $parent/$name already exists" >&2
    exit 65
  fi
  cp "$case_dir/parent/$name.fixture" "$parent/$name"
done
ln -s AGENTS.md CLAUDE.md
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
git add CLAUDE.md
GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
  git -c commit.gpgsign=false commit -q --amend --no-edit --no-verify
