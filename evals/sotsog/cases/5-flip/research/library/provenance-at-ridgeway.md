# Adding build provenance to an internal service: Ridgeway's notes

Source: https://ridgeway-energy.example.org/tech/provenance-notes
Author: Felix Braun, release engineer, Ridgeway Energy
Published: 2026-08-14

We added signing and provenance to a service with two internal consumers. The
first setup took three days; since then, keeping it working has cost about a
day a quarter, mostly when the CI provider or signing tool changes. Our
security team now verifies every deploy against the provenance, which is what
justified the work: they made it a deploy requirement.
