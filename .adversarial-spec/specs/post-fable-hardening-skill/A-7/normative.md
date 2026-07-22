# A-7 Component Mini-Spec

Title: hardening_bootstrap.py (BOOT-* checks + live preflight)

Bootstrap CLI: BOOT-GATES/HARNESS/RECON/REGISTRY/SPINE blocking + BOOT-ROUTER advisory; hermetic blocking path (no transport instantiation); --live-preflight REMOTE path via MW-007; deferred-state exit mapping by pending regime-sensitive transition; five-minute fresh-clone target; failure output contract.

Acceptance criteria:
- fresh-clone clean run under 5 minutes with named checks (TC-0.0)
- regime branch distinguishes legacy/hardened/corrupt (TC-0.4)
- every blocking check passes under denied socket/DNS (TC-2.3)
- blocking precedence: advisory+blocking => exit 2

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task A-7.
Implementation status: greenfield — hardening_bootstrap.py absent (verified)
