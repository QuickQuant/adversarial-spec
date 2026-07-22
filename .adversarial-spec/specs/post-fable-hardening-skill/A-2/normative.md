# A-2 Component Mini-Spec

Title: Hook-plane dispatcher + conformance fixtures

One slice-owned dispatcher per event type in .claude/hooks/ (hook-local codec, NO skill imports); declarative versioned registration; duplicate/third-party handler detection at bootstrap; typed ALLOW/DENY/DIAGNOSTIC verdicts; blocking mode for preventive gates; shared conformance fixtures against both hook-local and skill validators; consolidate the three drifting role resolvers (CON-005).

Acceptance criteria:
- duplicate handler detected + cross-surface fixture agreement (TC-2.4)
- internal failure becomes DENY for safety dispatchers
- async/exit-1/raise/malformed classifier cases never skip later blockers

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task A-2.
Implementation status: partial — hook plane exists (fizzy_payload_guard.py:86-147; three role resolvers dispatch_check.py:18-83, pipeline_continue.py:21-67, pipeline_idle_retry.py:24-70); dispatcher layer is new
