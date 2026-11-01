#!/usr/bin/env bash
# Sort files in a folder into YYYY-MM subfolders.
set -euo pipefail
for f in "${1:-.}"/*; do
  [ -f "$f" ] || continue
  d=$(date -r "$f" +%Y-%m)
  mkdir -p "${1:-.}/$d" && mv "$f" "${1:-.}/$d/"
done
