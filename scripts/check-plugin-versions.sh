#!/usr/bin/env bash
# Compatibility entrypoint; supply an explicit known base for payload changes.
set -euo pipefail
cd "$(dirname "$0")/.."
exec bin/check-marketplace --base "${1:-origin/main}"
