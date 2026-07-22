# W0-11 Component Mini-Spec

Title: MW-006 LocalCapabilityVerifier + trusted-time watermark

local_capabilities.py: offline signature/version/freshness verification of cached capability attestations; persisted monotonic authority-time watermark; max(local clock, watermark) expiry; every capability-state maps to exactly one deterministic token; release-signature validation.

Acceptance criteria:
- wall-clock rollback cannot extend authorization, incl. across restarts
- DF-2 skew + missing-release cases green
- TC-3.3 local deferred-for-live-preflight distinguished from remote tokens

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-11.
Implementation status: greenfield — no local capability verifier exists
