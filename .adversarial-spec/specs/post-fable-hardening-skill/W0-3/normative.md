# W0-3 Component Mini-Spec

Title: MW-008 CliBoundary

cli_boundary.py: shared strict argparse (allow_abbrev=False, unknown-arg rejection), one structured result envelope per invocation, exit mapping 0/1/2 with blocking precedence, no env-var gate inputs.

Acceptance criteria:
- abbreviation and unknown args rejected with envelope output
- every invocation emits exactly one result envelope
- --help is a successful help result

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-3.
Implementation status: greenfield — no shared CLI adapter; validation_emission.py:3423 has its own _Parser (stays)
