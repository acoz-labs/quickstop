"""Tally votes of the form 'voter,choice'."""
from collections import Counter


def parse_line(line):
    voter, _, choice = line.partition(",")
    voter, choice = voter.strip(), choice.strip()
    if not voter or not choice:
        raise ValueError(f"malformed vote: {line!r}")
    return voter, choice


def tally(lines):
    """Count one vote per voter; a later vote replaces an earlier one."""
    latest = {}
    for line in lines:
        if line.strip():
            voter, choice = parse_line(line)
            latest[voter] = choice
    return Counter(latest.values())


def winner(counts):
    """Return the choice with most votes; ties break alphabetically."""
    if not counts:
        return None
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
