#!/usr/bin/env python3
"""Normalize dotted task ids to fizzy's RE_TASK_ID contract (^[A-Za-z0-9_-]{1,32}$).

C-1.1 -> C-1-1 etc. Applied to id-bearing fields ONLY (task_id, parent,
decomposes_into, depends_on, requirement_metadata.traced_from). Paths are NOT
touched: artifact dirs keep their dotted names and the plan's spec_refs /
verification_binding paths keep pointing at them (load re-derives hashes from
file bytes; the path is just a locator). Test refs like TC-3.9 are never ids.

Run after any emit_driver.py re-emission, before pipeline_validate_plan:
    uv run python orchestration/fix_task_ids.py

Context: live pipeline_validate_plan rejected 'C-1.1' (PLAN_INVALID) on
2026-06-11; local self_check_plan has no task_id-charset check (parity gap,
reported to fizzy backlog).
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # specs/validation-leg-process/
PLAN = BASE / "fizzy-plan.json"
COMMENTS = BASE / "orchestration" / "comments-draft.json"


def main() -> int:
    plan = json.loads(PLAN.read_text())
    tasks = plan["tasks"]
    mapping = {
        t["task_id"]: t["task_id"].replace(".", "-")
        for t in tasks
        if "." in t["task_id"]
    }
    if not mapping:
        print("nothing to do: no dotted task ids")
        return 0

    def fix(v):
        return mapping.get(v, v)

    for t in tasks:
        t["task_id"] = fix(t["task_id"])
        if t.get("parent"):
            t["parent"] = fix(t["parent"])
        for key in ("decomposes_into", "depends_on"):
            if isinstance(t.get(key), list):
                t[key] = [fix(x) for x in t[key]]
        rm = t.get("requirement_metadata") or {}
        if rm.get("traced_from"):
            rm["traced_from"] = fix(rm["traced_from"])

    tmp = PLAN.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan, indent=2) + "\n")
    tmp.rename(PLAN)

    if COMMENTS.exists():
        comments = json.loads(COMMENTS.read_text())
        rekeyed = {fix(k): v for k, v in comments.items()}
        ctmp = COMMENTS.with_suffix(".json.tmp")
        ctmp.write_text(json.dumps(rekeyed, indent=2, ensure_ascii=False) + "\n")
        ctmp.rename(COMMENTS)

    print(f"renamed {len(mapping)} ids: " + ", ".join(sorted(mapping.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
