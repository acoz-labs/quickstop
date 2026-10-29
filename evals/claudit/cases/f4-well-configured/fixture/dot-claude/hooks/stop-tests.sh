#!/usr/bin/env bash
# Stop hook: keep the turn going while the test suite fails.
# Exits 2 with the failure on stderr so Claude sees why it should continue.
# When Claude is already continuing because of this hook (stop_hook_active),
# it lets the turn end to avoid a loop.
set -u
input=$(cat)
if printf '%s' "$input" | node -e '
  let s = "";
  process.stdin.on("data", (d) => (s += d)).on("end", () => {
    process.exit(JSON.parse(s || "{}").stop_hook_active ? 0 : 1);
  });'; then
  exit 0
fi
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! out=$(npm test --silent 2>&1); then
  printf 'npm test is failing; fix it before finishing.\n%s\n' "$(printf '%s\n' "$out" | tail -n 20)" >&2
  exit 2
fi
exit 0
