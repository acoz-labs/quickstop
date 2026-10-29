#!/usr/bin/env bash
# Build one eval workspace: bash scaffold.sh <fixture-dir>, run with cwd = the
# empty workspace. Writes only to the workspace and $HOME.
set -euo pipefail

if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
  echo "usage: bash scaffold.sh <fixture-dir>" >&2
  exit 64
fi
fixture=$(cd "$1" && pwd -P)
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
  local part mapped out= parts
  IFS=/ read -r -a parts <<< "$1"
  for part in "${parts[@]}"; do
    mapped=$(map_segment "$part")
    case "$mapped" in
      '' | . | ..)
        echo "scaffold: fixture path '$1' maps segment '$part' to '$mapped'" >&2
        return 1 ;;
    esac
    out="${out:+$out/}$mapped"
  done
  printf '%s' "$out"
}

if [ -n "$(find "$fixture" -type l -print -quit)" ]; then
  echo "scaffold: fixture contains symlinks: $fixture" >&2
  exit 65
fi

# Map and validate every path before copying anything.
sources=() targets=()
while IFS= read -r -d '' path; do
  mapped=$(map_path "${path#"$fixture"/}") || exit 65
  sources+=("$path")
  targets+=("$workspace/$mapped")
done < <(find "$fixture" -mindepth 1 -print0)

for ((i = 0; i < ${#sources[@]}; i++)); do
  if [ -d "${sources[i]}" ]; then
    mkdir -p "${targets[i]}"
  else
    mkdir -p "$(dirname "${targets[i]}")"
    cp -p "${sources[i]}" "${targets[i]}"
  fi
done

# Operator git configuration (hooks, signing, templates) must not leak in.
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
git -c init.defaultBranch=main init -q
git config user.name "Eval Fixture"
git config user.email "fixture@example.invalid"
git add -A
GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
  git -c commit.gpgsign=false commit -q --allow-empty --no-verify -m "Fixture"
