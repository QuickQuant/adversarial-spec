# W0-6 Component Mini-Spec

Title: MW-003 HashChainedJournal

journal.py: logical append (each event hashes predecessor), chain verification, event-head projection, external-anchor record emission for authority-side anchoring.

Acceptance criteria:
- chain break detected at unit level
- anchored-head verification round-trips

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-6.
Implementation status: greenfield — provenance_journal.py:77-362 is TMR-specific; generic substrate absent
