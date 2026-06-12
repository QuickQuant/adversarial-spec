#!/usr/bin/env python3
"""Add the tested_by field load_plan requires (validate_plan does NOT check it —
served validate/load asymmetry observed 2026-06-11, MISSING_OR_INVALID_TESTED_BY x25).

Mapping (documented decision):
  - automated-* and static-check and artifact-sync -> "llm" (agent-verifiable:
    pytest suites, static greps, doc-section cold-read TC-0.1)
  - manual-ux (C-5-3 dogfood) -> "both" (the real fizzy gate must accept AND
    Jason gives intent-level acceptance, US-10/TC-4.1)

Part of the resume chain: emit_driver.py -> fix_task_ids.py -> add_tested_by.py.
"""
import json
import sys
from pathlib import Path

PLAN = Path(__file__).resolve().parent.parent / "fizzy-plan.json"

LLM_MODES = {
    "automated-unit", "automated-integration", "automated-contract",
    "automated-component", "static-check", "artifact-sync", "test-producer",
}


def main() -> int:
    plan = json.loads(PLAN.read_text())
    counts = {"llm": 0, "both": 0, "user": 0, "kept": 0}
    for t in plan["tasks"]:
        if t.get("tested_by") in ("llm", "both", "user"):
            counts["kept"] += 1
            continue
        mode = t.get("verification_mode", "")
        val = "llm" if mode in LLM_MODES else "both" if mode == "manual-ux" else "user"
        t["tested_by"] = val
        counts[val] += 1
    tmp = PLAN.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan, indent=2) + "\n")
    tmp.rename(PLAN)
    print("tested_by set:", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
