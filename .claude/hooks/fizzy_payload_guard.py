#!/usr/bin/env python3
"""PreToolUse gate for fizzy MCP payload discipline.

Canonical source: Brainquarters/.claude/hooks/fizzy_payload_guard.py
Propagate via the existing hook-propagation flow (same as bash_command_check.py).

Gates unbounded/wasteful Fizzy MCP calls in main context, forcing scoped params
or subagent delegation. Hard-blocks (decision:block) like bash_command_check.py,
with a process-failure-report override.

Rules (see 2026-06-11-mcp-usage-audit-r7-handoff.md section 5):
  G1 get_card_checklists without checklist_name/round_instance_id/states  -> DENY
  G2 get_board_summary (no filter)                                        -> DENY
     get_list_cards / get_card_comments without limit                     -> DENY
  G3 pipeline_dispatch_single_agent_debate spec_content > 2000 chars      -> DENY
  G4 pipeline_advance_debate_round duplicate-args resend                  -> WARN (no-op best-effort)
  G5 narrative arg (findings_summary/domain_context/evidence) > 1500      -> WARN
  G6 bookkeeping tool without caller == "bookkeeper"                      -> DENY

Override (DENY->ALLOW): requires BOTH metadata.intent (or env
FIZZY_GUARD_OVERRIDE) >= 50 chars AND metadata.process_failure_path pointing at
a file that exists, is >= 200 bytes, and was modified within the last 600s.
"""
import datetime
import json
import os
import sys
import time

# G1: unbounded reads gated unless a scoping filter is present.
UNBOUNDED = {"mcp__fizzy__get_card_checklists", "mcp__fizzy__get_board_summary"}
# G2: growth-shaped reads that must carry a limit.
NEEDS_LIMIT = {
    "mcp__fizzy__get_list_cards": "limit",
    "mcp__fizzy__get_card_comments": "limit",
}
# G6: bookkeeping tools delegated to the haiku bookkeeper subagent.
BOOKKEEPING = {
    "mcp__fizzy__pipeline_attest_steps",
    "mcp__fizzy__pipeline_advance_debate_round",
    "mcp__fizzy__pipeline_patch_state",
    "mcp__fizzy__add_comment",
}
NARRATIVE_ARGS = ("findings_summary", "domain_context", "evidence")
MAX_NARRATIVE = 1500
MAX_INLINE_SPEC = 2000
PF_MIN_BYTES = 200
PF_MAX_AGE_S = 600


def deny(msg):
    print(json.dumps({"decision": "block", "reason": msg}))
    sys.exit(0)


def warn(msg):
    print(f"fizzy-guard: {msg}", file=sys.stderr)


def override_valid(meta):
    """DENY->ALLOW only with intent >=50 chars AND a fresh process-failure note."""
    intent = (meta.get("intent") or os.environ.get("FIZZY_GUARD_OVERRIDE") or "")
    pf = meta.get("process_failure_path") or ""
    if len(intent) < 50 or not pf:
        return None
    try:
        st = os.stat(pf)
    except OSError:
        return None
    if st.st_size < PF_MIN_BYTES or (time.time() - st.st_mtime) > PF_MAX_AGE_S:
        return None  # recycled or stub note: DENY stands
    return intent, pf


def log_override(tool, intent, pf):
    try:
        with open(".adversarial-spec/session-state.json") as fh:
            sid = json.load(fh)["active_session_id"]
        ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(f".adversarial-spec/sessions/{sid}.decisions.log", "a") as f:
            f.write(f"{ts} [guard-override] {tool} — {intent[:100]} — note: {pf}\n")
    except Exception as e:  # noqa: BLE001 - ledger failure must not block the override
        warn(f"override ledger write failed ({e}) — override still honored, REPORT THIS")


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = payload.get("tool_name", "")
    args = payload.get("tool_input", {}) or {}
    meta = args.get("metadata") or {}

    # G4 (best-effort WARN): a PreToolUse hook is stateless and fires per-call with
    # no memory of prior failed calls, so true duplicate-args detection across tool
    # uses is impractical here. Implemented as a no-op to avoid over-engineering;
    # the deduplication belongs in the MCP server (which holds round state).

    # Override short-circuits every DENY below.
    ov = override_valid(meta)
    if ov:
        log_override(tool, *ov)
        warn(f"override accepted: {ov[0][:80]}")
        sys.exit(0)

    # G1
    if tool in UNBOUNDED and not any(
        args.get(k) for k in ("checklist_name", "round_instance_id", "states")
    ):
        deny(
            "Unbounded Fizzy read (returns full card history — every round's checklist). "
            "Use scoped params, take IDs from the advance-round failure detail, or delegate "
            "to a haiku subagent. Override: metadata.intent (>=50 chars) AND "
            "metadata.process_failure_path (fresh note, >=200 bytes)."
        )

    # G2
    if tool in NEEDS_LIMIT and not args.get(NEEDS_LIMIT[tool]):
        deny(
            f"{tool} without {NEEDS_LIMIT[tool]} — growth-shaped payload. Scope it or delegate. "
            "Override: intent + process_failure_path."
        )

    # G6
    if tool in BOOKKEEPING and args.get("caller") != "bookkeeper":
        deny(
            "Bookkeeping is delegated (G6) — launch the haiku bookkeeper subagent with the "
            "summary strings; it passes caller='bookkeeper'. Override: intent + "
            "process_failure_path (a written process-failure report is mandatory)."
        )

    # G3
    if (
        tool == "mcp__fizzy__pipeline_dispatch_single_agent_debate"
        and len(args.get("spec_content") or "") > MAX_INLINE_SPEC
    ):
        deny("Inline spec_content > 2KB. Use spec_path — the file is the source of truth.")

    # G5 (WARN)
    for k in NARRATIVE_ARGS:
        v = args.get(k)
        if isinstance(v, str) and len(v) > MAX_NARRATIVE:
            warn(f"{k} is {len(v)} chars — prefer a *_path arg or trim; this rides every retry.")

    sys.exit(0)


if __name__ == "__main__":
    main()
