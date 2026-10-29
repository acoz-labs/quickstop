#!/usr/bin/env bash
# Build one eval workspace: bash scaffold.sh <fixture-dir>, run with cwd = the
# empty workspace. Writes only to the workspace and $HOME.
set -euo pipefail

if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
  echo "usage: bash scaffold.sh <fixture-dir>" >&2
  exit 64
fi
fixture=$(cd "$1" && pwd -P)
suite=$(cd "$(dirname "$0")" && pwd -P)
workspace=$(pwd -P)

# Fixtures store dotfiles as dot-* and agent instruction files as *.fixture so
# the suite itself never carries live Claude Code configuration.
map_segment() {
  local segment=$1
  case "$segment" in
    dot-*) segment=".${segment#dot-}" ;;
  esac
  case "$segment" in
    ?*.fixture) segment="${segment%.fixture}" ;;
  esac
  printf '%s' "$segment"
}

map_path() {
  local part out= parts
  IFS=/ read -r -a parts <<< "$1"
  for part in "${parts[@]}"; do
    out="${out:+$out/}$(map_segment "$part")"
  done
  printf '%s' "$out"
}

if [ -n "$(find "$fixture" -type l -print -quit)" ]; then
  echo "scaffold: fixture contains symlinks: $fixture" >&2
  exit 65
fi

while IFS= read -r -d '' path; do
  relative=${path#"$fixture"/}
  target="$workspace/$(map_path "$relative")"
  if [ -d "$path" ]; then
    mkdir -p "$target"
  else
    mkdir -p "$(dirname "$target")"
    cp -p "$path" "$target"
  fi
done < <(find "$fixture" -mindepth 1 -print0)

# Operator git configuration (hooks, signing, templates) must not leak in.
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
git -c init.defaultBranch=main init -q
git config user.name "Eval Fixture"
git config user.email "fixture@example.invalid"
git add -A
GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
  git -c commit.gpgsign=false commit -q --allow-empty --no-verify -m "Fixture"

if [ -d "$suite/seed-home" ]; then
  cp -R "$suite/seed-home/." "$HOME/"
fi

cache="$HOME/.cache/claudit"
if [ -f "$cache/.seed-root" ]; then
  new_root=$(cd "$cache" && pwd -P)
  python3 - "$(cat "$cache/.seed-root")" "$new_root" <<'PY'
import json
from pathlib import Path
import sys

old, new = sys.argv[1].rstrip('/'), sys.argv[2]


def move(value):
    if isinstance(value, str) and (value == old or value.startswith(old + '/')):
        return new + value[len(old):]
    if isinstance(value, list):
        return [move(item) for item in value]
    if isinstance(value, dict):
        return {key: move(item) for key, item in value.items()}
    return value


for path in sorted((Path(new) / 'v2').rglob('*.json')):
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        continue
    moved = move(record)
    if moved != record:
        path.write_text(json.dumps(moved, indent=2, ensure_ascii=False) + '\n')
PY
  rm -f "$cache/.seed-root"
fi
