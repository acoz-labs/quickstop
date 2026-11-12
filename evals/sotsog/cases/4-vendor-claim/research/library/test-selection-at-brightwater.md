# What test selection actually saved us at Brightwater

Source: https://brightwater-games.example.org/eng/test-selection-results
Author: Nadia Kowalczyk, build engineer, Brightwater Games
Published: 2026-05-21

Our full test suite takes 2 hours 10 minutes. We trialled predictive test
selection for three months and measured it against the full suite on every
change. Median CI time fell by 41%, not 90%. It missed 7 of 212 real failures,
which the nightly full run then caught, a day late. For a suite our size it
was worth it; we'd not bother below about 30 minutes.
