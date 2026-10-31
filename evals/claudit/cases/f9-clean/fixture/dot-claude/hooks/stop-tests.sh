#!/usr/bin/env bash
# Stop hook: keep the turn going while the tests fail; let it end once already continuing.
set -u
input=$(cat)
case "$input" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! out=$(npm test --silent 2>&1); then
  printf 'npm test is failing; fix it before finishing.\n%s\n' "$(printf '%s\n' "$out" | tail -n 20)" >&2
  exit 2
fi
