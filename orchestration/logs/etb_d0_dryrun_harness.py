"""ETB D0 bounded-load dry run: fizzy validator + load_plan in-process, no board.

Run from the fizzy-pipeline-mcp venv so the real validator is imported:

    uv run --project ~/PycharmProjects/fizzy-pipeline-mcp python \
        orchestration/logs/etb_d0_dryrun_harness.py orchestration/logs/etb-d0-plan-dryrun.json

The session card is an in-memory copy of ETB card 21605's pipeline state (v6,
subsystem, d0_closed, Debate, 28 historical session-card rounds, no
debate_leaf_inventory). Every client call lands in ``MemoryBoard``; nothing
reaches a Fizzy server. ``_plan_project_root`` is pinned to the ETB checkout to
model the plan living under ETB's ``.adversarial-spec/specs/<slug>/`` (its
architecture refs and bindings resolve there); ETB itself is only read.
"""

from __future__ import annotations

import asyncio
import copy
import json
import sys
from pathlib import Path
from typing import Any

from fizzy_pipeline_mcp import pipeline as p
from fizzy_pipeline_mcp.client import FizzyClientError

ETB = Path("/home/jason/PycharmProjects/ETB")
SESSION_ID = "adv-spec-202609220555-selective-reversal-state-machine"
BOARD = "03fw5h5ymdktifuhsjf47c32r"
LANES = {"Debate", "Specifying", "Synthesized", "Decomposed"}


class MemoryBoard:
    """Just enough of FizzyClient for validate_plan/load_plan/begin/lane-state."""

    def __init__(self) -> None:
        self.cards: dict[str, dict[str, Any]] = {
            "21605": {
                "number": 21605,
                "title": "selective reversal state machine",
                "column": {"name": "Debate"},
                "metadata_version": 40,
                "tags": [],
                "pipeline_metadata": {
                    "card_type": "session",
                    "session_id": SESSION_ID,
                    "pipeline_version": 6,
                    "session_altitude": "subsystem",
                    "d0_closed": True,
                    "extensions": {"debate": {"last_completed_round": 28, "state": "completed"}},
                },
            }
        }
        self.steps: dict[str, list[dict[str, Any]]] = {}
        self.next_number = 30000

    async def list_board_cards(self, board_id=None, **_):
        return [copy.deepcopy(c) for c in self.cards.values()]

    async def get_card(self, number, board_id=None, **_):
        return copy.deepcopy(self.cards[str(number)])

    async def find_card_by_session_id(self, session_id, board_id=None, **_):
        for c in self.cards.values():
            meta = c["pipeline_metadata"]
            if meta.get("card_type") == "session" and meta.get("session_id") == session_id:
                return copy.deepcopy(c)
        return None

    async def patch_card_metadata(self, number, patch, expected_version=None, board_id=None, **_):
        card = self.cards[str(number)]
        card["pipeline_metadata"].update(copy.deepcopy(patch))
        card["metadata_version"] += 1
        return copy.deepcopy(card)

    async def create_card_with_metadata(self, *, title, column_name, pipeline_metadata, board_id=None, **_):
        assert column_name in LANES, column_name
        self.next_number += 1
        card = {
            "number": self.next_number, "title": title, "column": {"name": column_name},
            "metadata_version": 1, "tags": [], "pipeline_metadata": copy.deepcopy(pipeline_metadata),
        }
        self.cards[str(self.next_number)] = card
        return copy.deepcopy(card)

    async def create_step(self, number, step, board_id=None, **_):
        self.steps.setdefault(str(number), []).append(step)
        return {"id": f"s{len(self.steps[str(number)])}", **step}

    async def get_card_steps(self, number, board_id=None, **_):
        return list(self.steps.get(str(number), []))

    async def get_column_id(self, name, board_id=None):
        return f"col-{name}"

    async def get_board_members(self, *_, **__):
        return []

    async def create_card_link(self, *_, **__):
        return {}

    async def set_assignees(self, *_, **__):
        return {}

    async def add_comment(self, *_, **__):
        return {}

    async def add_checklist_item_info(self, *_, **__):  # pragma: no cover - not expected
        raise AssertionError("unexpected checklist write")


async def main(plan_path: Path) -> int:
    p._plan_project_root = lambda _real: ETB  # plan modeled as living in ETB's spec dir
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    board = MemoryBoard()
    out: dict[str, Any] = {}

    # (a) lane state before any load
    lane = await p.get_lane_state(board, pipeline="session", board_id=BOARD, session_id=SESSION_ID)
    out["lane_state_before_load"] = {
        "session_next_action": lane.get("session_next_action"),
        "kind": lane.get("attention", {}).get("session_context", {}).get("kind"),
    }

    # (b) whole-spec round refused
    try:
        await p.begin_debate_round(board, session_id=SESSION_ID, card_id="21605",
                                   round_number=29, models=["codex"], board_id=BOARD)
        out["begin_debate_round"] = "NOT REFUSED"
    except FizzyClientError as exc:
        out["begin_debate_round"] = {"code": exc.code, "message": exc.message}

    # validator (pipeline_validate_plan's in-process implementation)
    result = await p.validate_plan(board, plan_path=str(plan_path.resolve()),
                                   session_id=SESSION_ID, board_id=BOARD)
    out["validate_plan"] = {k: result[k] for k in ("valid", "issues", "warnings", "plan_task_count",
                                                   "session_pipeline_version")}
    out["leaf_task_ids"] = sorted(p._v4_leaf_task_ids(plan["tasks"]))
    out["binding_lifts_ok"] = sorted(t["task_id"] for t in plan["tasks"]
                                     if p._derive_v4_node_lift(t, ETB))

    # (c) load into the in-memory board
    loaded = await p.load_plan(board, plan_path=str(plan_path.resolve()),
                               session_id=SESSION_ID, board_id=BOARD)
    tasks = [c for c in board.cards.values() if c["pipeline_metadata"].get("card_type") == "task"]
    out["load_plan_ok"] = loaded.get("ok")
    out["cards_by_lane"] = {}
    for c in sorted(tasks, key=lambda c: c["pipeline_metadata"]["task_id"]):
        out["cards_by_lane"].setdefault(c["column"]["name"], []).append(c["pipeline_metadata"]["task_id"])
    inv = board.cards["21605"]["pipeline_metadata"].get("debate_leaf_inventory") or {}
    out["debate_leaf_inventory_task_ids"] = inv.get("task_ids")

    lane = await p.get_lane_state(board, pipeline="session", board_id=BOARD, session_id=SESSION_ID)
    out["lane_state_after_load"] = {
        "session_next_action": lane.get("session_next_action"),
        "kind": lane.get("attention", {}).get("session_context", {}).get("kind"),
    }
    print(json.dumps(out, indent=2))
    ok = (
        result["valid"] and not result["issues"]
        and out["leaf_task_ids"] == [f"L{i}" for i in range(1, 9)]
        and out["cards_by_lane"].get("Specifying") == out["leaf_task_ids"]
        and out["debate_leaf_inventory_task_ids"] == out["leaf_task_ids"]
    )
    print("DRY RUN:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(Path(sys.argv[1]))))
