#!/usr/bin/env python3
"""Non-mutating semantic analysis for Phase 7 dependency plans.

Fizzy validates that a dependency graph is structurally loadable.  This module
checks the planning meaning that is intentionally richer than Fizzy's wire
contract: why an edge exists, whether a promised contract fanout is actually
runnable, scope closure, and safety-predecessor order.

The input remains a normal ``fizzy-plan.json``. Semantic metadata can live in
an adjacent sidecar or under an optional top-level ``dependency_semantics``
object for an unloaded draft. ``depends_on`` remains the only dependency field
sent to Fizzy. The report is read-only and is designed to be reviewed before
``pipeline_validate_plan`` / ``pipeline_load``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

REPORT_SCHEMA_VERSION = 2
# Bump when a new rule class lands; loaders enforce a minimum floor so a green
# report from an analyzer that predates the evidence rules cannot pass.
ANALYZER_VERSION = 2
EDGE_KINDS = frozenset(
    {"interface_ready", "integration_ready", "safety_ready", "data_ready"}
)
RECEIPT_REQUIRED_FIELDS = (
    "receipt_id",
    "spine",
    "class",
    "producer_task",
    "location_accessor",
    "pass_condition",
)
OBLIGATION_REQUIRED_FIELDS = (
    "obligation_id",
    "root_goal",
    "discharge_test",
    "route_prose",
    "downstream_owner_phase",
)


def _issue(code: str, **detail: Any) -> dict[str, Any]:
    return {"code": code, **detail}


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        return None
    return value


def _wave(task: dict[str, Any]) -> int | None:
    """Return a comparable wave when the task provides one."""
    value = task.get("wave")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _topological_profile(
    task_ids: list[str], dependencies: dict[str, set[str]]
) -> tuple[list[str], dict[str, int], list[str]]:
    """Return topological order, earliest-ready layers, and cyclic nodes."""
    dependents: dict[str, set[str]] = defaultdict(set)
    remaining = {task_id: len(dependencies[task_id]) for task_id in task_ids}
    for dependent, prerequisites in dependencies.items():
        for prerequisite in prerequisites:
            dependents[prerequisite].add(dependent)

    ready = deque(sorted(task_id for task_id in task_ids if remaining[task_id] == 0))
    order: list[str] = []
    layers: dict[str, int] = {}
    while ready:
        task_id = ready.popleft()
        order.append(task_id)
        prerequisites = dependencies[task_id]
        layers[task_id] = (
            max((layers[prerequisite] for prerequisite in prerequisites), default=-1) + 1
        )
        for dependent in sorted(dependents[task_id]):
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                ready.append(dependent)

    cyclic = sorted(task_id for task_id, count in remaining.items() if count > 0)
    return order, layers, cyclic


def analyze_plan(
    plan: dict[str, Any],
    *,
    semantic_metadata: dict[str, Any] | None = None,
    decomposition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze a plan's dependency semantics without changing the plan.

    Missing semantic metadata is allowed only for a plan with no dependency
    edges.  Once a task has ``depends_on``, every edge needs a ledger entry with
    an explicit readiness kind, reason, and source reference.
    """
    issues: list[dict[str, Any]] = []
    raw_tasks = plan.get("tasks")
    if not isinstance(raw_tasks, list):
        return {
            "report_schema_version": REPORT_SCHEMA_VERSION,
            "valid": False,
            "issues": [_issue("INVALID_TASKS", detail="plan.tasks must be a list")],
            "summary": {},
        }

    tasks: dict[str, dict[str, Any]] = {}
    task_order: list[str] = []
    for index, task in enumerate(raw_tasks):
        if not isinstance(task, dict):
            issues.append(_issue("INVALID_TASK", index=index))
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            issues.append(_issue("INVALID_TASK_ID", index=index))
            continue
        if task_id in tasks:
            issues.append(_issue("DUPLICATE_TASK_ID", task_id=task_id))
            continue
        tasks[task_id] = task
        task_order.append(task_id)

    dependencies: dict[str, set[str]] = {task_id: set() for task_id in task_order}
    edges: set[tuple[str, str]] = set()
    for task_id in task_order:
        raw_dependencies = tasks[task_id].get("depends_on", [])
        parsed = _string_list(raw_dependencies)
        if parsed is None:
            issues.append(_issue("INVALID_DEPENDS_ON", task_id=task_id))
            continue
        for prerequisite in parsed:
            if prerequisite not in tasks:
                issues.append(
                    _issue(
                        "UNKNOWN_PREREQUISITE",
                        dependent=task_id,
                        prerequisite=prerequisite,
                    )
                )
                continue
            dependencies[task_id].add(prerequisite)
            edges.add((task_id, prerequisite))

    semantics = (
        semantic_metadata
        if semantic_metadata is not None
        else plan.get("dependency_semantics", {})
    )
    if not isinstance(semantics, dict):
        issues.append(_issue("INVALID_DEPENDENCY_SEMANTICS"))
        semantics = {}

    ledger = semantics.get("edge_ledger", [])
    if not isinstance(ledger, list):
        issues.append(_issue("INVALID_EDGE_LEDGER"))
        ledger = []
    ledger_edges: set[tuple[str, str]] = set()
    data_ready_entries: list[dict[str, Any]] = []
    for index, entry in enumerate(ledger):
        if not isinstance(entry, dict):
            issues.append(_issue("INVALID_EDGE_LEDGER_ENTRY", index=index))
            continue
        dependent = entry.get("dependent")
        prerequisite = entry.get("prerequisite")
        kind = entry.get("kind")
        reason = entry.get("reason")
        source_ref = entry.get("source_ref")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (dependent, prerequisite, kind, reason, source_ref)
        ):
            issues.append(_issue("INCOMPLETE_EDGE_LEDGER_ENTRY", index=index))
            continue
        edge = (dependent, prerequisite)
        if kind not in EDGE_KINDS:
            issues.append(_issue("INVALID_EDGE_KIND", index=index, kind=kind))
        if kind == "data_ready":
            data_ready_entries.append(entry)
        if edge in ledger_edges:
            issues.append(
                _issue(
                    "DUPLICATE_EDGE_LEDGER_ENTRY",
                    dependent=dependent,
                    prerequisite=prerequisite,
                )
            )
        ledger_edges.add(edge)
        if edge not in edges:
            issues.append(
                _issue(
                    "LEDGER_EDGE_NOT_IN_PLAN",
                    dependent=dependent,
                    prerequisite=prerequisite,
                )
            )

    for dependent, prerequisite in sorted(edges - ledger_edges):
        issues.append(
            _issue(
                "UNEXPLAINED_DEPENDENCY",
                dependent=dependent,
                prerequisite=prerequisite,
            )
        )

    order, layers, cyclic = _topological_profile(task_order, dependencies)
    if cyclic:
        issues.append(_issue("DEPENDENCY_CYCLE", task_ids=cyclic))

    ancestors_cache: dict[str, set[str]] = {}

    def ancestors(task_id: str) -> set[str]:
        if task_id in ancestors_cache:
            return ancestors_cache[task_id]
        visited: set[str] = set()
        pending = list(dependencies.get(task_id, set()))
        while pending:
            prerequisite = pending.pop()
            if prerequisite in visited:
                continue
            visited.add(prerequisite)
            pending.extend(dependencies.get(prerequisite, set()))
        ancestors_cache[task_id] = visited
        return visited

    readiness: dict[str, dict[str, Any]] = {}
    for task_id in task_order:
        readiness[task_id] = {
            "direct_dependencies": sorted(dependencies[task_id]),
            "transitive_dependencies": sorted(ancestors(task_id)),
            "ready_layer": layers.get(task_id),
        }

    fanout_report: list[dict[str, Any]] = []
    fanout_contracts = semantics.get("fanout_contracts", [])
    if not isinstance(fanout_contracts, list):
        issues.append(_issue("INVALID_FANOUT_CONTRACTS"))
        fanout_contracts = []
    for contract_index, contract in enumerate(fanout_contracts):
        if not isinstance(contract, dict):
            issues.append(_issue("INVALID_FANOUT_CONTRACT", index=contract_index))
            continue
        gate_task_id = contract.get("gate_task_id")
        streams = contract.get("workstreams")
        if gate_task_id not in tasks or not isinstance(streams, list) or not streams:
            issues.append(_issue("INCOMPLETE_FANOUT_CONTRACT", index=contract_index))
            continue

        gate_ancestors = ancestors(gate_task_id) | {gate_task_id}
        stream_report: list[dict[str, Any]] = []
        foreign_by_stream: dict[str, set[str]] = {}
        for stream_index, stream in enumerate(streams):
            if not isinstance(stream, dict):
                issues.append(
                    _issue(
                        "INVALID_FANOUT_WORKSTREAM",
                        contract_index=contract_index,
                        stream_index=stream_index,
                    )
                )
                continue
            name = stream.get("name")
            first_task_id = stream.get("first_runnable_task")
            artifacts = _string_list(stream.get("required_artifacts"))
            if (
                not isinstance(name, str)
                or not name.strip()
                or first_task_id not in tasks
                or artifacts is None
                or not artifacts
            ):
                issues.append(
                    _issue(
                        "INCOMPLETE_FANOUT_WORKSTREAM",
                        contract_index=contract_index,
                        stream_index=stream_index,
                    )
                )
                continue
            if tasks[first_task_id].get("workstream") != name:
                issues.append(
                    _issue(
                        "FANOUT_WORKSTREAM_MISMATCH",
                        workstream=name,
                        task_id=first_task_id,
                    )
                )
            direct = dependencies[first_task_id]
            if gate_task_id not in ancestors(first_task_id):
                issues.append(
                    _issue(
                        "FANOUT_GATE_NOT_REQUIRED",
                        gate_task_id=gate_task_id,
                        workstream=name,
                        task_id=first_task_id,
                    )
                )
            foreign = direct - gate_ancestors
            foreign_by_stream[name] = foreign
            stream_report.append(
                {
                    "workstream": name,
                    "first_runnable_task": first_task_id,
                    "required_artifacts": artifacts,
                    "direct_dependencies": sorted(direct),
                    "additional_dependencies": sorted(foreign),
                    "ready_after_gate": not foreign and gate_task_id in ancestors(first_task_id),
                }
            )

        if len(foreign_by_stream) > 1:
            shared = set.intersection(*foreign_by_stream.values())
            gate_wave = _wave(tasks[gate_task_id])
            for prerequisite in sorted(shared):
                prerequisite_wave = _wave(tasks[prerequisite])
                is_later = (
                    gate_wave is not None
                    and prerequisite_wave is not None
                    and prerequisite_wave > gate_wave
                )
                if is_later or gate_wave is None or prerequisite_wave is None:
                    issues.append(
                        _issue(
                            "FANOUT_SHARED_LATER_DEPENDENCY",
                            gate_task_id=gate_task_id,
                            prerequisite=prerequisite,
                            workstreams=sorted(foreign_by_stream),
                        )
                    )
        fanout_report.append(
            {
                "gate_task_id": gate_task_id,
                "workstreams": stream_report,
                "ready_after_gate_count": sum(
                    stream["ready_after_gate"] for stream in stream_report
                ),
                "workstream_count": len(stream_report),
            }
        )

    scope_report: list[dict[str, Any]] = []
    scope_summary: dict[str, list[str]] = {
        "active": [],
        "deferred": [],
        "excluded": [],
    }
    scope_closure = semantics.get("scope_closure")
    if not isinstance(scope_closure, dict):
        issues.append(_issue("MISSING_SCOPE_CLOSURE"))
    else:
        parsed_scopes: dict[str, list[str]] = {}
        for key in ("active", "deferred", "excluded"):
            values = _string_list(scope_closure.get(key))
            if values is None:
                issues.append(_issue("INCOMPLETE_SCOPE_CLOSURE", field=key))
                values = []
            parsed_scopes[key] = values
        active_scope = set(parsed_scopes["active"])
        deferred_scope = set(parsed_scopes["deferred"])
        excluded_scope = set(parsed_scopes["excluded"])
        scope_summary = {
            "active": sorted(active_scope),
            "deferred": sorted(deferred_scope),
            "excluded": sorted(excluded_scope),
        }
        if active_scope & deferred_scope or active_scope & excluded_scope:
            issues.append(_issue("SCOPE_CLASSIFICATION_CONFLICT"))
        raw_exceptions = scope_closure.get("operator_approved_exceptions", [])
        if not isinstance(raw_exceptions, list):
            issues.append(_issue("INVALID_SCOPE_EXCEPTIONS"))
            raw_exceptions = []
        exceptions: set[tuple[str, str, str]] = set()
        for index, exception in enumerate(raw_exceptions):
            if not isinstance(exception, dict):
                issues.append(_issue("INVALID_SCOPE_EXCEPTION", index=index))
                continue
            values = (
                exception.get("active_task_id"),
                exception.get("deferred_task_id"),
                exception.get("scope"),
                exception.get("approved_by"),
                exception.get("reason"),
            )
            if not all(isinstance(value, str) and value.strip() for value in values):
                issues.append(_issue("INCOMPLETE_SCOPE_EXCEPTION", index=index))
                continue
            exceptions.add((values[0], values[1], values[2]))

        task_scopes: dict[str, set[str]] = {}
        for task_id in task_order:
            raw_scope_refs = tasks[task_id].get("scope_refs", [])
            scope_refs = _string_list(raw_scope_refs)
            if scope_refs is None:
                issues.append(_issue("INVALID_SCOPE_REFS", task_id=task_id))
                scope_refs = []
            task_scopes[task_id] = set(scope_refs)
            if task_scopes[task_id] & deferred_scope and task_scopes[task_id] & active_scope:
                issues.append(_issue("TASK_SCOPE_CONFLICT", task_id=task_id))

        active_tasks = [
            task_id
            for task_id in task_order
            if tasks[task_id].get("active_path") is True
            or bool(task_scopes[task_id] & active_scope)
        ]
        for active_task_id in active_tasks:
            for prerequisite in ancestors(active_task_id):
                for scope in sorted(
                    task_scopes[prerequisite] & (deferred_scope | excluded_scope)
                ):
                    if (active_task_id, prerequisite, scope) in exceptions:
                        continue
                    code = (
                        "ACTIVE_SCOPE_DEPENDS_ON_DEFERRED"
                        if scope in deferred_scope
                        else "ACTIVE_SCOPE_DEPENDS_ON_EXCLUDED"
                    )
                    issues.append(
                        _issue(
                            code,
                            active_task_id=active_task_id,
                            deferred_task_id=prerequisite,
                            scope=scope,
                        )
                    )
                    scope_report.append(
                        {
                            "active_task_id": active_task_id,
                            "deferred_task_id": prerequisite,
                            "scope": scope,
                        }
                    )

    safety_implementers: dict[str, set[str]] = defaultdict(set)
    safety_consumers: dict[str, set[str]] = defaultdict(set)
    for task_id in task_order:
        implements = _string_list(tasks[task_id].get("safety_implements", []))
        consumes = _string_list(tasks[task_id].get("safety_consumes", []))
        if implements is None:
            issues.append(_issue("INVALID_SAFETY_IMPLEMENTATION_REFS", task_id=task_id))
            implements = []
        if consumes is None:
            issues.append(_issue("INVALID_SAFETY_CONSUMER_REFS", task_id=task_id))
            consumes = []
        for invariant in implements:
            safety_implementers[invariant].add(task_id)
        for invariant in consumes:
            safety_consumers[invariant].add(task_id)

    safety_report: list[dict[str, Any]] = []
    for invariant, consumers in sorted(safety_consumers.items()):
        implementers = safety_implementers.get(invariant, set())
        for consumer in sorted(consumers):
            if consumer in implementers:
                issues.append(
                    _issue(
                        "SAFETY_SELF_IMPLEMENTATION",
                        invariant=invariant,
                        task_id=consumer,
                    )
                )
                continue
            if not implementers:
                issues.append(
                    _issue(
                        "MISSING_SAFETY_IMPLEMENTER",
                        invariant=invariant,
                        consumer=consumer,
                    )
                )
                continue
            if not any(implementer in ancestors(consumer) for implementer in implementers):
                issues.append(
                    _issue(
                        "SAFETY_CONSUMER_BEFORE_IMPLEMENTER",
                        invariant=invariant,
                        consumer=consumer,
                        implementers=sorted(implementers),
                    )
                )
                safety_report.append(
                    {
                        "invariant": invariant,
                        "consumer": consumer,
                        "implementers": sorted(implementers),
                    }
                )

    # ---- Evidence receipts + acceptance-obligation closure (H2) ----
    receipts: dict[str, dict[str, Any]] = {}
    raw_receipts = semantics.get("evidence_receipts", [])
    if not isinstance(raw_receipts, list):
        issues.append(_issue("INVALID_EVIDENCE_RECEIPTS"))
        raw_receipts = []
    for index, receipt in enumerate(raw_receipts):
        if not isinstance(receipt, dict):
            issues.append(_issue("INVALID_EVIDENCE_RECEIPT", index=index))
            continue
        if not all(
            isinstance(receipt.get(field), str) and receipt[field].strip()
            for field in RECEIPT_REQUIRED_FIELDS
        ):
            issues.append(_issue("INCOMPLETE_EVIDENCE_RECEIPT", index=index))
            continue
        receipt_id = receipt["receipt_id"]
        if receipt_id in receipts:
            issues.append(_issue("DUPLICATE_RECEIPT_ID", receipt_id=receipt_id))
            continue
        binding = receipt.get("binding")
        if not (
            isinstance(binding, dict)
            and isinstance(binding.get("hash_or_freshness"), str)
            and binding["hash_or_freshness"].strip()
        ):
            issues.append(_issue("RECEIPT_UNBOUND", receipt_id=receipt_id))
        if _string_list(receipt.get("consumers")) is None:
            issues.append(_issue("INVALID_RECEIPT_CONSUMERS", receipt_id=receipt_id))
            continue
        if receipt["producer_task"] not in tasks:
            issues.append(
                _issue(
                    "RECEIPT_PRODUCER_UNKNOWN",
                    receipt_id=receipt_id,
                    producer_task=receipt["producer_task"],
                )
            )
            continue
        receipts[receipt_id] = receipt

    consumers_with_edge: dict[str, set[str]] = defaultdict(set)
    for entry in data_ready_entries:
        dependent = entry["dependent"]
        prerequisite = entry["prerequisite"]
        receipt_id = entry.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.strip():
            issues.append(
                _issue(
                    "DATA_READY_EDGE_MISSING_RECEIPT",
                    dependent=dependent,
                    prerequisite=prerequisite,
                )
            )
            continue
        receipt = receipts.get(receipt_id)
        if receipt is None:
            issues.append(
                _issue(
                    "DATA_READY_EDGE_UNKNOWN_RECEIPT",
                    dependent=dependent,
                    receipt_id=receipt_id,
                )
            )
            continue
        consumers_with_edge[receipt_id].add(dependent)
        producer = receipt["producer_task"]
        if producer != prerequisite and producer not in ancestors(prerequisite):
            issues.append(
                _issue(
                    "RECEIPT_PRODUCER_NOT_UPSTREAM",
                    receipt_id=receipt_id,
                    producer_task=producer,
                    prerequisite=prerequisite,
                )
            )

    for receipt_id, receipt in receipts.items():
        listed = set(receipt.get("consumers", []))
        for consumer in sorted(listed):
            if consumer not in tasks:
                issues.append(
                    _issue(
                        "RECEIPT_CONSUMER_UNKNOWN",
                        receipt_id=receipt_id,
                        consumer=consumer,
                    )
                )
                continue
            if (
                consumer not in consumers_with_edge.get(receipt_id, set())
                or receipt["producer_task"] not in ancestors(consumer)
            ):
                issues.append(
                    _issue(
                        "RECEIPT_CONSUMER_UNREACHABLE",
                        receipt_id=receipt_id,
                        consumer=consumer,
                    )
                )
        for consumer in sorted(consumers_with_edge.get(receipt_id, set()) - listed):
            issues.append(
                _issue(
                    "RECEIPT_CONSUMER_NOT_LISTED",
                    receipt_id=receipt_id,
                    consumer=consumer,
                )
            )

    live_spine_owners: set[str] = set()
    obligations: dict[str, dict[str, Any]] = {}
    if decomposition is not None:
        raw_obligations = decomposition.get("acceptance_obligations", [])
        if not isinstance(raw_obligations, list):
            issues.append(_issue("INVALID_ACCEPTANCE_OBLIGATIONS"))
            raw_obligations = []
        for index, obligation in enumerate(raw_obligations):
            if not isinstance(obligation, dict) or not all(
                isinstance(obligation.get(field), str) and obligation[field].strip()
                for field in OBLIGATION_REQUIRED_FIELDS
            ):
                issues.append(_issue("INCOMPLETE_ACCEPTANCE_OBLIGATION", index=index))
                continue
            classes = _string_list(obligation.get("missing_evidence_classes"))
            if classes is None or not classes:
                issues.append(
                    _issue(
                        "OBLIGATION_MISSING_EVIDENCE_CLASSES",
                        obligation_id=obligation["obligation_id"],
                    )
                )
                continue
            obligations[obligation["obligation_id"]] = obligation
        # Trigger rule: an acceptance-only ruling (acceptance_oracle present)
        # cannot stand without at least one preserved obligation record.
        if decomposition.get("acceptance_oracle") is not None and not obligations:
            issues.append(_issue("MISSING_ACCEPTANCE_OBLIGATION"))

        raw_closures = semantics.get("acceptance_obligation_closures", [])
        if not isinstance(raw_closures, list):
            issues.append(_issue("INVALID_OBLIGATION_CLOSURES"))
            raw_closures = []
        closures: dict[str, list[str]] = {}
        for index, closure in enumerate(raw_closures):
            if (
                not isinstance(closure, dict)
                or not isinstance(closure.get("obligation_id"), str)
                or _string_list(closure.get("receipt_ids")) is None
            ):
                issues.append(_issue("INVALID_OBLIGATION_CLOSURE", index=index))
                continue
            closures[closure["obligation_id"]] = closure["receipt_ids"]

        for obligation_id, obligation in sorted(obligations.items()):
            receipt_ids = closures.get(obligation_id)
            if receipt_ids is None:
                issues.append(
                    _issue("OBLIGATION_NOT_CLOSED", obligation_id=obligation_id)
                )
                continue
            closed_classes: set[str] = set()
            for receipt_id in receipt_ids:
                receipt = receipts.get(receipt_id)
                if receipt is None:
                    issues.append(
                        _issue(
                            "OBLIGATION_CLOSURE_UNKNOWN_RECEIPT",
                            obligation_id=obligation_id,
                            receipt_id=receipt_id,
                        )
                    )
                    continue
                closed_classes.add(receipt["class"])
                live_spine_owners.add(receipt["producer_task"])
            for required_class in obligation["missing_evidence_classes"]:
                if required_class not in closed_classes:
                    issues.append(
                        _issue(
                            "OBLIGATION_MISSING_EVIDENCE_CLASS",
                            obligation_id=obligation_id,
                            evidence_class=required_class,
                        )
                    )

    # Declared waves may not contradict the derived dependency order.
    for dependent, prerequisite in sorted(edges):
        dependent_wave = _wave(tasks[dependent])
        prerequisite_wave = _wave(tasks[prerequisite])
        if (
            dependent_wave is not None
            and prerequisite_wave is not None
            and dependent_wave < prerequisite_wave
        ):
            issues.append(
                _issue(
                    "WAVE_ORDER_CONTRADICTION",
                    dependent=dependent,
                    prerequisite=prerequisite,
                    dependent_wave=dependent_wave,
                    prerequisite_wave=prerequisite_wave,
                )
            )

    critical_path: list[str] = []
    if not cyclic and order:
        predecessor: dict[str, str | None] = {}
        for task_id in order:
            task_dependencies = sorted(dependencies[task_id])
            predecessor[task_id] = max(
                task_dependencies, key=lambda item: layers[item], default=None
            )
        tail = max(order, key=lambda item: (layers[item], item))
        while tail is not None:
            critical_path.append(tail)
            tail = predecessor[tail]
        critical_path.reverse()

    layer_widths: dict[int, int] = defaultdict(int)
    for layer in layers.values():
        layer_widths[layer] += 1
    covered_edges = len(edges & ledger_edges)
    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "analyzer_version": ANALYZER_VERSION,
        "valid": not issues,
        "issues": issues,
        "live_spine_owners": sorted(live_spine_owners),
        "evidence_receipts": sorted(receipts),
        "summary": {
            "task_count": len(task_order),
            "edge_count": len(edges),
            "edge_ledger_coverage": {
                "covered_edges": covered_edges,
                "total_edges": len(edges),
                "complete": covered_edges == len(edges),
            },
            "critical_path": critical_path,
            "critical_path_length": len(critical_path),
            "max_immediate_concurrency": max(layer_widths.values(), default=0),
            "ready_now": sorted(
                task_id for task_id in task_order if not dependencies[task_id]
            ),
        },
        "task_readiness": readiness,
        "fanout": fanout_report,
        "scope_closure": scope_summary,
        "scope_violations": scope_report,
        "safety_violations": safety_report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report Phase 7 dependency semantics without changing a plan."
    )
    parser.add_argument("--plan", required=True, type=Path, help="Path to fizzy-plan.json")
    parser.add_argument(
        "--semantics",
        type=Path,
        help="Optional dependency-semantics.json sidecar for an emitted plan",
    )
    parser.add_argument(
        "--decomposition",
        type=Path,
        help="Optional d0-decomposition.json; enables acceptance-obligation closure checks",
    )
    parser.add_argument(
        "--emit-report",
        type=Path,
        help="Write a hash-bound semantic report for pipeline_load verification",
    )
    args = parser.parse_args(argv)
    plan_bytes: bytes | None = None
    semantics_bytes: bytes | None = None
    try:
        plan_bytes = args.plan.read_bytes()
        data = json.loads(plan_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("plan root must be a JSON object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {
            "report_schema_version": REPORT_SCHEMA_VERSION,
            "valid": False,
            "issues": [_issue("PLAN_READ_ERROR", detail=str(exc))],
            "summary": {},
        }
    else:
        semantic_metadata: dict[str, Any] | None = None
        decomposition: dict[str, Any] | None = None
        read_error: dict[str, Any] | None = None
        if args.semantics is not None:
            try:
                semantics_bytes = args.semantics.read_bytes()
                semantic_document = json.loads(semantics_bytes.decode("utf-8"))
                if not isinstance(semantic_document, dict):
                    raise ValueError("semantic sidecar root must be a JSON object")
                semantic_metadata = semantic_document.get(
                    "dependency_semantics", semantic_document
                )
                if not isinstance(semantic_metadata, dict):
                    raise ValueError("dependency_semantics must be a JSON object")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                read_error = _issue("SEMANTICS_READ_ERROR", detail=str(exc))
        if read_error is None and args.decomposition is not None:
            try:
                decomposition_document = json.loads(
                    args.decomposition.read_text(encoding="utf-8")
                )
                if not isinstance(decomposition_document, dict):
                    raise ValueError("decomposition root must be a JSON object")
                decomposition = decomposition_document.get(
                    "decomposition", decomposition_document
                )
                if not isinstance(decomposition, dict):
                    raise ValueError("decomposition must be a JSON object")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                read_error = _issue("DECOMPOSITION_READ_ERROR", detail=str(exc))
        if read_error is not None:
            report = {
                "report_schema_version": REPORT_SCHEMA_VERSION,
                "valid": False,
                "issues": [read_error],
                "summary": {},
            }
        else:
            report = analyze_plan(
                data,
                semantic_metadata=semantic_metadata,
                decomposition=decomposition,
            )
    ledger_path_for_report: str | None = None
    if args.emit_report is not None and semantics_bytes is not None and args.semantics is not None:
        # pipeline_load resolves the report's ledger from the fizzy-plan.json
        # directory and deliberately rejects absolute or escaping paths.  Make
        # the emitted credential portable even when this CLI received absolute
        # input paths (the usual invocation from a worker's project root).
        plan_root = args.plan.resolve().parent
        try:
            ledger_path_for_report = args.semantics.resolve().relative_to(plan_root).as_posix()
        except ValueError:
            report = dict(report)
            report["valid"] = False
            report["issues"] = [
                *list(report.get("issues") or []),
                _issue(
                    "SEMANTIC_REPORT_LEDGER_OUTSIDE_PLAN_ROOT",
                    detail=(
                        "--semantics must be inside the fizzy-plan.json directory "
                        "when --emit-report is used"
                    ),
                ),
            ]

    if args.emit_report is not None:
        bound = dict(report)
        bound["analyzer_version"] = ANALYZER_VERSION
        bound["verdict"] = "green" if report["valid"] else "red"
        if plan_bytes is not None:
            bound["plan_path"] = str(args.plan)
            bound["plan_sha256"] = hashlib.sha256(plan_bytes).hexdigest()
        if semantics_bytes is not None and ledger_path_for_report is not None:
            bound["ledger_path"] = ledger_path_for_report
            bound["ledger_sha256"] = hashlib.sha256(semantics_bytes).hexdigest()
        args.emit_report.write_text(
            json.dumps(bound, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
