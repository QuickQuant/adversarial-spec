"""Regression tests for the Phase 7 dependency semantics gate."""

from __future__ import annotations

import json

from dependency_semantics import analyze_plan, main
from mini_spec_emission import emit_fizzy_plan, representative_tree


def edge(dependent: str, prerequisite: str, kind: str = "interface_ready") -> dict:
    return {
        "dependent": dependent,
        "prerequisite": prerequisite,
        "kind": kind,
        "reason": f"{dependent} consumes {prerequisite}'s declared output.",
        "source_ref": "target-architecture.md §7.2",
    }


def task(task_id: str, depends_on: list[str] | None = None, **metadata: object) -> dict:
    return {"task_id": task_id, "depends_on": depends_on or [], **metadata}


def codes(report: dict) -> set[str]:
    return {issue["code"] for issue in report["issues"]}


def test_contract_decoder_is_ready_before_its_later_integration() -> None:
    plan = {
        "tasks": [
            task("W0-contract", wave=0),
            task("M1-store", ["W0-contract"], wave=1),
            task("M1-confidence", ["W0-contract"], wave=1),
            task("M2-SWC-decode", ["W0-contract"], wave=2, workstream="SWC"),
            task(
                "M2-SWC-integrate",
                ["M2-SWC-decode", "M1-store", "M1-confidence"],
                wave=2,
                workstream="SWC",
            ),
        ],
        "dependency_semantics": {
            "edge_ledger": [
                edge("M1-store", "W0-contract"),
                edge("M1-confidence", "W0-contract"),
                edge("M2-SWC-decode", "W0-contract"),
                edge("M2-SWC-integrate", "M2-SWC-decode", "integration_ready"),
                edge("M2-SWC-integrate", "M1-store", "integration_ready"),
                edge("M2-SWC-integrate", "M1-confidence", "integration_ready"),
            ],
            "fanout_contracts": [
                {
                    "gate_task_id": "W0-contract",
                    "workstreams": [
                        {
                            "name": "SWC",
                            "first_runnable_task": "M2-SWC-decode",
                            "required_artifacts": ["TableEventProposal v1"],
                        }
                    ],
                }
            ],
            "scope_closure": {
                "active": [], "deferred": [], "excluded": [],
                "operator_approved_exceptions": [],
            },
        },
    }

    report = analyze_plan(plan)

    assert report["valid"], report["issues"]
    assert report["fanout"][0]["workstreams"][0]["ready_after_gate"] is True
    assert set(report["task_readiness"]["M2-SWC-integrate"]["transitive_dependencies"]) >= {
        "M1-store",
        "M1-confidence",
        "M2-SWC-decode",
    }


def test_parallel_fanout_rejects_shared_later_dependency() -> None:
    adapter_ids = ["SWC", "Bovada", "TP", "P2"]
    tasks = [task("W0-contract", wave=0), task("M1-store", ["W0-contract"], wave=1)]
    ledger = [edge("M1-store", "W0-contract")]
    streams = []
    for adapter in adapter_ids:
        task_id = f"M2-{adapter}-decode"
        tasks.append(task(task_id, ["W0-contract", "M1-store"], wave=2, workstream=adapter))
        ledger.extend([edge(task_id, "W0-contract"), edge(task_id, "M1-store", "integration_ready")])
        streams.append(
            {
                "name": adapter,
                "first_runnable_task": task_id,
                "required_artifacts": ["TableEventProposal v1"],
            }
        )
    plan = {
        "tasks": tasks,
        "dependency_semantics": {
            "edge_ledger": ledger,
            "fanout_contracts": [{"gate_task_id": "W0-contract", "workstreams": streams}],
            "scope_closure": {
                "active": [], "deferred": [], "excluded": [],
                "operator_approved_exceptions": [],
            },
        },
    }

    report = analyze_plan(plan)

    assert report["valid"] is False
    assert "FANOUT_SHARED_LATER_DEPENDENCY" in codes(report)


def test_active_scope_cannot_reach_deferred_site() -> None:
    plan = {
        "tasks": [
            task("M2-SWC", scope_refs=["SWC"], active_path=True),
            task("M6-SWC", ["M2-SWC", "M6-TP"], scope_refs=["SWC"], active_path=True),
            task("M6-TP", scope_refs=["TP"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [edge("M6-SWC", "M2-SWC"), edge("M6-SWC", "M6-TP")],
            "scope_closure": {
                "active": ["SWC", "Bovada"],
                "deferred": ["TP", "P2"],
                "excluded": [],
                "operator_approved_exceptions": [],
            },
        },
    }

    report = analyze_plan(plan)

    assert report["valid"] is False
    assert "ACTIVE_SCOPE_DEPENDS_ON_DEFERRED" in codes(report)


def test_active_scope_cannot_reach_excluded_site() -> None:
    plan = {
        "tasks": [
            task("M6-SWC", ["M6-P2"], scope_refs=["SWC"], active_path=True),
            task("M6-P2", scope_refs=["P2"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [edge("M6-SWC", "M6-P2")],
            "scope_closure": {
                "active": ["SWC"],
                "deferred": [],
                "excluded": ["P2"],
                "operator_approved_exceptions": [],
            },
        },
    }

    report = analyze_plan(plan)

    assert report["valid"] is False
    assert "ACTIVE_SCOPE_DEPENDS_ON_EXCLUDED" in codes(report)


def test_safety_implementer_must_precede_every_consumer() -> None:
    plan = {
        "tasks": [
            task("W0-browser-isolation", safety_implements=["INV-browser-isolation"]),
            task("M2-browser-automation", safety_consumes=["INV-browser-isolation"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [],
            "scope_closure": {
                "active": [], "deferred": [], "excluded": [],
                "operator_approved_exceptions": [],
            },
        },
    }

    report = analyze_plan(plan)

    assert report["valid"] is False
    assert "SAFETY_CONSUMER_BEFORE_IMPLEMENTER" in codes(report)


def test_cli_writes_a_read_only_json_report(tmp_path, capsys) -> None:
    plan_path = tmp_path / "fizzy-plan.json"
    semantics_path = tmp_path / "dependency-semantics.json"
    plan_path.write_text(
        json.dumps({"tasks": [task("W0")]}) + "\n",
        encoding="utf-8",
    )
    semantics_path.write_text(
        json.dumps(
            {
                "edge_ledger": [],
                "scope_closure": {
                    "active": [], "deferred": [], "excluded": [],
                    "operator_approved_exceptions": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["--plan", str(plan_path), "--semantics", str(semantics_path)])

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["valid"] is True
    assert plan_path.read_text(encoding="utf-8").endswith("\n")


def data_ready_edge(dependent: str, prerequisite: str, receipt_id: str | None = None) -> dict:
    entry = edge(dependent, prerequisite, "data_ready")
    if receipt_id is not None:
        entry["receipt_id"] = receipt_id
    return entry


def receipt(
    receipt_id: str,
    spine: str,
    evidence_class: str,
    producer_task: str,
    consumers: list[str],
    *,
    hash_or_freshness: str = "sha256:deadbeef",
) -> dict:
    return {
        "receipt_id": receipt_id,
        "spine": spine,
        "class": evidence_class,
        "producer_task": producer_task,
        "location_accessor": "artifact://receipt",
        "pass_condition": f"{receipt_id} pass condition satisfied",
        "consumers": consumers,
        "binding": {"hash_or_freshness": hash_or_freshness},
    }


def obligation(obligation_id: str, missing_evidence_classes: list[str]) -> dict:
    return {
        "obligation_id": obligation_id,
        "root_goal": f"{obligation_id} root goal",
        "discharge_test": f"{obligation_id} discharge test",
        "route_prose": f"{obligation_id} route prose",
        "downstream_owner_phase": "phase-8",
        "missing_evidence_classes": missing_evidence_classes,
    }


def closure(obligation_id: str, receipt_ids: list[str]) -> dict:
    return {"obligation_id": obligation_id, "receipt_ids": receipt_ids}


def empty_scope_closure() -> dict:
    return {
        "active": [],
        "deferred": [],
        "excluded": [],
        "operator_approved_exceptions": [],
    }


def test_temporal_inversion_consumer_without_data_ready_edge() -> None:
    # Models the gateway T-1 failure: the obligation is closed on paper by a
    # receipt that lists T-1 as a consumer, but T-1 has no data_ready edge
    # naming the receipt at all, so the closure is unreachable in practice.
    plan = {
        "tasks": [
            task("G0"),
            task("T-1"),
        ],
        "dependency_semantics": {
            "edge_ledger": [],
            "evidence_receipts": [receipt("R1", "spine-A", "no_order_readiness", "G0", ["T-1"])],
            "acceptance_obligation_closures": [closure("AO-1", ["R1"])],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(
        plan,
        decomposition={"acceptance_obligations": [obligation("AO-1", ["no_order_readiness"])]},
    )

    assert report["valid"] is False
    assert "RECEIPT_CONSUMER_UNREACHABLE" in codes(report)


def test_data_ready_edge_unknown_receipt() -> None:
    plan = {
        "tasks": [
            task("B"),
            task("A", ["B"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [data_ready_edge("A", "B", receipt_id="R-missing")],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(plan)

    assert report["valid"] is False
    assert "DATA_READY_EDGE_UNKNOWN_RECEIPT" in codes(report)


def test_receipt_producer_not_upstream() -> None:
    plan = {
        "tasks": [
            task("P"),
            task("B"),
            task("A", ["B", "P"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [
                data_ready_edge("A", "B", receipt_id="R1"),
                edge("A", "P", "interface_ready"),
            ],
            "evidence_receipts": [receipt("R1", "spine-A", "no_order_readiness", "P", ["A"])],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(plan)

    assert report["valid"] is False
    assert "RECEIPT_PRODUCER_NOT_UPSTREAM" in codes(report)


def test_unbound_receipt_flagged() -> None:
    plan = {
        "tasks": [task("P")],
        "dependency_semantics": {
            "edge_ledger": [],
            "evidence_receipts": [
                {
                    "receipt_id": "R1",
                    "spine": "spine-A",
                    "class": "no_order_readiness",
                    "producer_task": "P",
                    "location_accessor": "artifact://receipt",
                    "pass_condition": "R1 pass condition satisfied",
                    "consumers": [],
                }
            ],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(plan)

    assert report["valid"] is False
    assert "RECEIPT_UNBOUND" in codes(report)


def test_valid_two_receipt_spine_passes() -> None:
    plan = {
        "tasks": [
            task("G0"),
            task("M4", ["G0"]),
            task("C", ["G0", "M4"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [
                edge("M4", "G0", "interface_ready"),
                data_ready_edge("C", "G0", receipt_id="R-G0"),
                data_ready_edge("C", "M4", receipt_id="R-M4"),
            ],
            "evidence_receipts": [
                receipt("R-G0", "spine-1", "no_order_readiness", "G0", ["C"]),
                receipt("R-M4", "spine-1", "post_order_fill", "M4", ["C"]),
            ],
            "acceptance_obligation_closures": [closure("AO-1", ["R-G0", "R-M4"])],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(
        plan,
        decomposition={
            "acceptance_obligations": [
                obligation("AO-1", ["no_order_readiness", "post_order_fill"])
            ]
        },
    )

    assert report["valid"], report["issues"]
    assert report["live_spine_owners"] == ["G0", "M4"]


def test_synthetic_plan_untouched() -> None:
    plan = {
        "tasks": [
            task("A"),
            task("B", ["A"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [edge("B", "A", "interface_ready")],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(plan)

    assert report["valid"], report["issues"]


def test_missing_evidence_class_rejected() -> None:
    plan = {
        "tasks": [
            task("G0"),
            task("C", ["G0"]),
        ],
        "dependency_semantics": {
            "edge_ledger": [data_ready_edge("C", "G0", receipt_id="R-G0")],
            "evidence_receipts": [receipt("R-G0", "spine-1", "no_order_readiness", "G0", ["C"])],
            "acceptance_obligation_closures": [closure("AO-1", ["R-G0"])],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(
        plan,
        decomposition={"acceptance_obligations": [obligation("AO-1", ["post_order_fill"])]},
    )

    assert report["valid"] is False
    assert "OBLIGATION_MISSING_EVIDENCE_CLASS" in codes(report)


def test_acceptance_only_without_obligation_fails() -> None:
    plan = {
        "tasks": [task("A")],
        "dependency_semantics": {
            "edge_ledger": [],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(plan, decomposition={"acceptance_oracle": {"id": "AO-1"}})

    assert report["valid"] is False
    assert "MISSING_ACCEPTANCE_OBLIGATION" in codes(report)


def test_ordinary_decomposition_without_oracle_clean() -> None:
    plan = {
        "tasks": [task("A")],
        "dependency_semantics": {
            "edge_ledger": [],
            "scope_closure": empty_scope_closure(),
        },
    }

    report = analyze_plan(plan, decomposition={})

    assert report["valid"], report["issues"]


def test_wave_order_contradiction() -> None:
    contradictory_plan = {
        "tasks": [
            task("Later", ["Earlier"], wave=1),
            task("Earlier", wave=2),
        ],
        "dependency_semantics": {
            "edge_ledger": [edge("Later", "Earlier")],
            "scope_closure": empty_scope_closure(),
        },
    }

    contradictory_report = analyze_plan(contradictory_plan)

    assert contradictory_report["valid"] is False
    assert "WAVE_ORDER_CONTRADICTION" in codes(contradictory_report)

    equal_wave_plan = {
        "tasks": [
            task("Later", ["Earlier"], wave=2),
            task("Earlier", wave=2),
        ],
        "dependency_semantics": {
            "edge_ledger": [edge("Later", "Earlier")],
            "scope_closure": empty_scope_closure(),
        },
    }

    equal_wave_report = analyze_plan(equal_wave_plan)

    assert equal_wave_report["valid"], equal_wave_report["issues"]


def test_altitude_emitter_uses_a_sidecar_without_changing_its_wire_payload() -> None:
    plan = emit_fizzy_plan(representative_tree(), session_id="sess")
    report = analyze_plan(
        plan,
        semantic_metadata={
            "edge_ledger": [],
            "fanout_contracts": [],
            "scope_closure": {
                "active": [],
                "deferred": [],
                "excluded": [],
                "operator_approved_exceptions": [],
            },
        },
    )

    assert report["valid"], report["issues"]
    assert "dependency_semantics" not in plan
    assert report["scope_closure"] == {
        "active": [],
        "deferred": [],
        "excluded": [],
    }
