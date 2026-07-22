# W0-5 Component Mini-Spec

Title: Safe-path resolver + filesystem capability probes

Per-component dir_fd walk with O_NOFOLLOW + fstat device/mount validation (normative); ..-, absolute-, cross-session targets fail closed; bootstrap lock-capability probe proving cross-process shared/exclusive semantics; filesystem-capability-unsupported named failure.

Acceptance criteria:
- intermediate-symlink substitution blocked (TC-1.5)
- induced submount rejected (DF-8)
- unsupported filesystem is a named capability failure, never silent

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-5.
Implementation status: greenfield — no descriptor-relative walker in repo; spec notes final-component checks insufficient
