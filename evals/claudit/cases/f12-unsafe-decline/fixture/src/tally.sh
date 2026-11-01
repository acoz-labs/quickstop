#!/usr/bin/env bash
# Print the number of words in a file.
set -euo pipefail
wc -w < "$1" | tr -d " "
