#!/usr/bin/env python3
"""Group conventional-commit subjects into Keep a Changelog sections."""
import sys

SECTIONS = {"feat": "Added", "fix": "Fixed"}
ORDER = ["Added", "Fixed", "Changed"]


def classify(subject):
    kind = subject.split(":", 1)[0].split("(", 1)[0].strip().lower()
    return SECTIONS.get(kind, "Changed")


def describe(subject):
    return subject.split(":", 1)[1].strip() if ":" in subject else subject.strip()


def format_entry(subjects):
    groups = {name: [] for name in ORDER}
    for subject in subjects:
        if subject.strip():
            groups[classify(subject)].append(describe(subject))
    out = []
    for name in ORDER:
        if groups[name]:
            out.append(f"### {name}")
            out.extend(f"- {item}" for item in groups[name])
            out.append("")
    return "\n".join(out).rstrip() + "\n" if out else ""


if __name__ == "__main__":
    sys.stdout.write(format_entry(sys.stdin.read().splitlines()))
