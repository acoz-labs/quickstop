#!/usr/bin/env bash
# Stop hook: block finishing while the tests fail.
input=$(cat)
case "$input" in
  *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;;
esac
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! out=$(go test ./... 2>&1); then
  printf 'Tests fail; fix them before finishing:\n%s\n' "$out" >&2
  exit 2
fi
exit 0
