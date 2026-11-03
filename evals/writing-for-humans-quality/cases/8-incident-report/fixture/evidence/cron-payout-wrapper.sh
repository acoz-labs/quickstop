#!/usr/bin/env bash
# Nightly payout wrapper, run from cron on batch-02:
#   0 2 * * * /opt/payouts/bin/cron-payout-wrapper.sh
# Waits for the ledger close marker for yesterday before starting the batch,
# so merchants whose partitions close late are still paid tonight.
set -euo pipefail

day="$(date -u -d yesterday +%F)"
marker="/var/run/ledger/close-${day}.done"
deadline=$(( $(date +%s) + 3 * 3600 ))

while [[ ! -f "$marker" ]]; do
  if (( $(date +%s) > deadline )); then
    echo "ledger close for ${day} not done after 3h; running batch anyway" >&2
    break
  fi
  sleep 60
done

exec /opt/payouts/bin/payout-batch --business-date "$day"
