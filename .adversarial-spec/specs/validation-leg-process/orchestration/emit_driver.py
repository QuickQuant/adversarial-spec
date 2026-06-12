#!/usr/bin/env python3
"""Emit schema-3 validation-leg execution artifacts from execution-plan.md.

This driver is intentionally local-only. It reads the approved execution plan,
builds the altitude tree, calls mini_spec_emission.emit_fizzy_plan(), replaces
the helper's placeholder artifacts with substantive per-node docs, refreshes
hashes, and writes the coverage report plus fizzy-plan.json.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SESSION_ID = "adv-spec-202606110339-validation-leg-process"
SLUG = "validation-leg-process"

REPO_ROOT = Path(__file__).resolve().parents[4]
SPEC_ROOT = REPO_ROOT / ".adversarial-spec" / "specs" / SLUG
PLAN_PATH = SPEC_ROOT / "execution-plan.md"
COVERAGE_PATH = SPEC_ROOT / "verification-coverage.json"
FIZZY_PLAN_PATH = SPEC_ROOT / "fizzy-plan.json"
REPORT_PATH = SPEC_ROOT / "orchestration" / "emission-report.md"
EMITTER_PATH = REPO_ROOT / "skills" / "adversarial-spec" / "scripts" / "mini_spec_emission.py"

EXPECTED_IDS = [
    "SYS",
    "SS-1",
    "C-1.1",
    "C-1.2",
    "C-1.3",
    "C-1.4",
    "SS-2",
    "C-2.1",
    "C-2.2",
    "C-2.3",
    "SS-3",
    "C-3.1",
    "C-3.2",
    "C-3.3",
    "SS-4",
    "C-4.1",
    "C-4.2",
    "C-4.3",
    "C-4.4",
    "C-4.5",
    "C-4.6",
    "SS-5",
    "C-5.1",
    "C-5.2",
    "C-5.3",
]

EXPECTED_CHILDREN = {
    "SYS": ["SS-1", "SS-2", "SS-3", "SS-4", "SS-5"],
    "SS-1": ["C-1.1", "C-1.2", "C-1.3", "C-1.4"],
    "SS-2": ["C-2.1", "C-2.2", "C-2.3"],
    "SS-3": ["C-3.1", "C-3.2", "C-3.3"],
    "SS-4": ["C-4.1", "C-4.2", "C-4.3", "C-4.4", "C-4.5", "C-4.6"],
    "SS-5": ["C-5.1", "C-5.2", "C-5.3"],
}

EXPECTED_MODE_COUNTS = {
    "automated-unit": 16,
    "automated-integration": 6,
    "artifact-sync": 1,
    "static-check": 1,
    "manual-ux": 1,
}

EXPECTED_NON_BEHAVIOR = {"C-4.6", "SS-5", "C-5.1", "C-5.2", "C-5.3"}
EXEMPT_MODES = {"artifact-sync", "static-check", "manual-ux"}
ARCH_INV_A = [f"INV-A{i}" for i in range(1, 8)]
VALID_IMPLEMENTATION_STATUSES = {"greenfield", "partial", "already-built"}
RE_TASK_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


@dataclass
class PlanNode:
    task_id: str
    title: str
    altitude: str
    parent: str | None
    children: list[str] = field(default_factory=list)
    realizes_refs: list[str] = field(default_factory=list)
    conops_refs: list[str] = field(default_factory=list)
    user_story_refs: list[str] = field(default_factory=list)
    implementation_status: str = ""
    behavior_change: bool = True
    verification_mode: str = ""
    verification_scope: str = ""
    strategy: str = "test-first"
    architecture_refs: list[str] = field(default_factory=list)
    concern_refs: list[str] = field(default_factory=list)
    invariant_refs: list[str] = field(default_factory=list)
    surface_scope: list[str] = field(default_factory=list)
    test_refs: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    verify_commands: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    exemption_reason: str | None = None
    depends_on: list[str] = field(default_factory=list)

    @property
    def description(self) -> str:
        noun = self.altitude
        title = words(self.title)
        return f"The {noun} shall satisfy the approved {title} acceptance criteria."

    @property
    def requirement_rationale(self) -> str:
        refs = self.realizes_refs or self.user_story_refs or self.conops_refs
        ref_text = ", ".join(refs) if refs else "the approved parent scope"
        return f"The {self.altitude} shall preserve validation-leg intent for {ref_text}."


def main() -> int:
    emitter = load_emitter()
    markdown = PLAN_PATH.read_text(encoding="utf-8")
    nodes = parse_execution_plan(markdown)
    validation_errors = validate_parsed_nodes(nodes)
    if validation_errors:
        write_report(
            coverage=None,
            self_check={"valid": False, "issues": validation_errors},
            lint_results=[],
            judgment_calls=[],
            open_questions=["Parsing failed; see self_check/issues block."],
        )
        raise SystemExit("\n".join(validation_errors))

    component_ids = [tid for tid, node in nodes.items() if node.altitude == "component"]
    for node in nodes.values():
        if node.depends_on == ["(all)"]:
            node.depends_on = [tid for tid in component_ids if tid != node.task_id]

    coverage, coverage_notes = build_coverage(nodes)
    write_json_atomic(COVERAGE_PATH, coverage)

    tree = build_tree(nodes)
    plan = emitter.emit_fizzy_plan(
        tree,
        session_id=SESSION_ID,
        slug=SLUG,
        with_artifact_manifest=False,
        artifact_root=REPO_ROOT,
    )
    enrich_plan(plan, nodes, emitter)
    write_node_artifacts(plan, nodes)
    refresh_hashes(plan)
    normalize_task_ids_for_fizzy(plan)

    self_check = emitter.self_check_plan(plan)
    live_contract_issues = validate_live_contract_shim(plan)
    if live_contract_issues:
        self_check = {
            "valid": False,
            "issues": [
                *self_check.get("issues", []),
                *live_contract_issues,
            ],
        }
    lint_results = run_requirement_lint(plan, emitter)
    lint_failures = [r for r in lint_results if not r["ok"]]
    if lint_failures:
        self_check = {
            "valid": False,
            "issues": [
                *self_check.get("issues", []),
                {"code": "REQUIREMENT_LINT_FAILED", "detail": lint_failures},
            ],
        }

    write_json_atomic(FIZZY_PLAN_PATH, plan)
    write_report(
        coverage=coverage,
        self_check=self_check,
        lint_results=lint_results,
        judgment_calls=[
            *coverage_notes,
            "Subsystem and system nodes without explicit verify_commands use the plan-declared full-suite scope.",
            "Final plan task ids are normalized to fizzy dash-form ids; artifact paths retain execution-plan dotted ids.",
            "Top-level verify_commands mirror the per-node execution-plan commands for automated nodes.",
            "Exempt doc/dogfood nodes keep their exemption_reason and use inspection/demonstration evidence in verification artifacts.",
            "Requirement IDs for dotted component ids use C-R<major><minor> so they satisfy ^[A-Z]+-R?\\d+$ and stay unique.",
        ],
        open_questions=[],
    )

    print(json.dumps({"coverage": str(COVERAGE_PATH), "plan": str(FIZZY_PLAN_PATH), "self_check": self_check}, indent=2))
    return 0 if self_check.get("valid") else 1


def load_emitter() -> Any:
    spec = importlib.util.spec_from_file_location("mini_spec_emission", EMITTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import emitter from {EMITTER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mini_spec_emission"] = module
    spec.loader.exec_module(module)
    return module


def parse_execution_plan(markdown: str) -> dict[str, PlanNode]:
    heading = re.compile(
        r"^(?P<marks>#{3,4})\s+(?P<task_id>SYS|SS-\d+|C-\d+\.\d+)\s+(?:\u2014\s*)?(?P<title>.+?)\s*$",
        re.MULTILINE,
    )
    matches = list(heading.finditer(markdown))
    nodes: dict[str, PlanNode] = {}
    for idx, match in enumerate(matches):
        task_id = match.group("task_id")
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        body = markdown[start:end]
        raw_title = match.group("title").strip()
        title = re.sub(r"\s+\([^)]*\)$", "", raw_title).strip()
        node = parse_node_body(task_id, title, body)
        nodes[task_id] = node
    return nodes


def parse_node_body(task_id: str, title: str, body: str) -> PlanNode:
    altitude = ""
    parent: str | None = None
    children: list[str] = []
    realizes_refs: list[str] = []
    conops_refs: list[str] = []
    user_story_refs: list[str] = []
    implementation_status = ""
    behavior_change = True
    verification_mode = ""
    verification_scope = ""
    strategy = "test-first"
    architecture_refs: list[str] = []
    concern_refs: list[str] = []
    invariant_refs: list[str] = []
    surface_scope: list[str] = []
    test_refs: list[str] = []
    test_files: list[str] = []
    verify_commands: list[str] = []
    exemption_reason: str | None = None
    depends_on: list[str] = []

    for raw_line in body.splitlines():
        line = raw_line.strip()
        clean = strip_md(line)
        if clean.startswith("- altitude:"):
            altitude = segment(clean, "altitude")
            parent_text = segment(clean, "parent")
            if parent_text and parent_text != "null":
                parent = parent_text
            children = bracket_items(clean, "decomposes_into")
            realizes_refs = us_ids(segment(clean, "realizes"))
            dep_text = segment(clean, "depends_on")
            if dep_text == "(all)":
                depends_on = ["(all)"]
            elif dep_text:
                depends_on = task_refs(dep_text)
                if not depends_on:
                    depends_on = ["(unparsed)"]
        elif "conops_refs / user_story_refs:" in clean:
            refs = us_ids(clean)
            conops_refs = refs
            user_story_refs = refs
        elif clean.startswith("- impl_status:"):
            implementation_status = implementation_status_token(clean)
        if "behavior_change:" in clean:
            behavior_change = segment(clean, "behavior_change").lower() == "true"
            verification_mode = segment(clean, "verification_mode")
            verification_scope = segment(clean, "scope")
            strategy = segment(clean, "strategy") or strategy
        elif clean.startswith("- architecture_refs:"):
            architecture_refs = backtick_items(line) or split_items(clean.removeprefix("- architecture_refs:"))
        elif "concern_refs:" in clean:
            concern_refs = split_items(segment(clean, "concern_refs"))
            invariant_refs = invariant_items(segment(clean, "invariant_refs"))
            surface_scope = split_items(segment(clean, "surface_scope"))
        elif "test_refs:" in clean:
            test_refs = tc_ids(segment(clean, "test_refs"))
            backtick_items(line)
            commands = files_after_label(line, "verify_commands")
            if "test_files:" in clean:
                test_files = files_after_label(line, "test_files")
            if commands:
                verify_commands = commands
        if "exemption_reason:" in line:
            m = re.search(r"exemption_reason:\*\*\s*\"([^\"]+)\"", line)
            if not m:
                m = re.search(r"exemption_reason:\s*\"([^\"]+)\"", strip_md(line))
            if m:
                exemption_reason = m.group(1)

    acceptance_criteria = parse_acceptance(body)
    if not verify_commands:
        verify_commands = default_verify_commands(verification_mode, verification_scope)

    return PlanNode(
        task_id=task_id,
        title=title,
        altitude=altitude,
        parent=parent,
        children=children,
        realizes_refs=realizes_refs,
        conops_refs=conops_refs,
        user_story_refs=user_story_refs,
        implementation_status=implementation_status,
        behavior_change=behavior_change,
        verification_mode=verification_mode,
        verification_scope=verification_scope,
        strategy=strategy,
        architecture_refs=architecture_refs,
        concern_refs=concern_refs,
        invariant_refs=invariant_refs,
        surface_scope=surface_scope,
        test_refs=test_refs,
        test_files=test_files,
        verify_commands=verify_commands,
        acceptance_criteria=acceptance_criteria,
        exemption_reason=exemption_reason,
        depends_on=depends_on,
    )


def parse_acceptance(body: str) -> list[str]:
    lines = body.splitlines()
    collected: list[str] = []
    collecting = False
    for raw_line in lines:
        line = raw_line.rstrip()
        clean = strip_md(line.strip())
        same_line = re.search(r"\bacceptance:\s*(.+)$", clean)
        if same_line and "acceptance_criteria" not in clean:
            collected.append(same_line.group(1).strip())
            continue
        if clean.startswith("- acceptance_criteria:"):
            collecting = True
            continue
        if not collecting:
            continue
        stripped = clean.strip()
        if stripped.startswith("- [ ]"):
            collected.append(stripped.removeprefix("- [ ]").strip())
        elif stripped.startswith("- ") and collected:
            break
        elif stripped and collected and not stripped.startswith("####"):
            collected[-1] = f"{collected[-1]} {stripped}"
    return collected or ["Approved execution-plan acceptance criteria are satisfied."]


def validate_parsed_nodes(nodes: dict[str, PlanNode]) -> list[str]:
    errors: list[str] = []
    ids = list(nodes)
    if ids != EXPECTED_IDS:
        errors.append(f"NODE_ORDER_DRIFT expected {EXPECTED_IDS}, parsed {ids}")
    for task_id, expected_children in EXPECTED_CHILDREN.items():
        actual = nodes.get(task_id).children if task_id in nodes else []
        if actual != expected_children:
            errors.append(f"TREE_DRIFT {task_id}: expected {expected_children}, parsed {actual}")
    for task_id in EXPECTED_IDS:
        node = nodes.get(task_id)
        if node is None:
            continue
        for field_name in ("altitude", "verification_mode", "verification_scope", "strategy"):
            if not getattr(node, field_name):
                errors.append(f"MISSING_FIELD {task_id}.{field_name}")
        if node.implementation_status not in VALID_IMPLEMENTATION_STATUSES:
            errors.append(f"BAD_IMPLEMENTATION_STATUS {task_id}: {node.implementation_status!r}")
        if node.verification_mode in EXEMPT_MODES and not node.exemption_reason:
            errors.append(f"MISSING_EXEMPTION_REASON {task_id}")
        if "(unparsed)" in node.depends_on:
            errors.append(f"DEPENDS_ON_UNPARSEABLE {task_id}")
    false_behavior = {tid for tid, node in nodes.items() if not node.behavior_change}
    if false_behavior != EXPECTED_NON_BEHAVIOR:
        errors.append(f"BEHAVIOR_COUNT_DRIFT expected false {sorted(EXPECTED_NON_BEHAVIOR)}, parsed {sorted(false_behavior)}")
    return errors


def build_coverage(nodes: dict[str, PlanNode]) -> tuple[dict[str, Any], list[str]]:
    counts: dict[str, int] = {}
    unmapped_behavior: list[str] = []
    unmapped_non_behavior: list[str] = []
    for node in nodes.values():
        mode = node.verification_mode
        if mode:
            counts[mode] = counts.get(mode, 0) + 1
        elif node.behavior_change:
            unmapped_behavior.append(node.task_id)
        else:
            unmapped_non_behavior.append(node.task_id)

    behavior_count = sum(1 for n in nodes.values() if n.behavior_change)
    notes: list[str] = []
    if counts != EXPECTED_MODE_COUNTS:
        notes.append(f"Mode-count discrepancy: parsed {counts}, expected {EXPECTED_MODE_COUNTS}. Parsed values used.")
    else:
        notes.append("Coverage derivation matched orchestrator expected mode counts.")
    if behavior_count != 20:
        notes.append(f"Behavior-count discrepancy: parsed {behavior_count}, expected 20. Parsed value used.")
    else:
        notes.append("Behavior derivation matched expected 20 behavior-changing nodes.")

    exempt_tasks = [
        {"task_id": n.task_id, "mode": n.verification_mode, "reason": n.exemption_reason}
        for n in nodes.values()
        if n.verification_mode in EXEMPT_MODES
    ]

    return (
        {
            "report_schema_version": 1,
            "total_tasks": len(nodes),
            "behavior_changing_count": behavior_count,
            "non_behavior_changing_count": len(nodes) - behavior_count,
            "counts_by_mode": counts,
            "exempt_tasks": exempt_tasks,
            "unmapped_behavior_tasks": unmapped_behavior,
            "unmapped_non_behavior_tasks": unmapped_non_behavior,
            "validation_errors": [],
        },
        notes,
    )


TESTED_BY_LLM_MODES = {
    "automated-unit", "automated-integration", "automated-contract",
    "automated-component", "static-check", "artifact-sync", "test-producer",
}


def build_tree(nodes: dict[str, PlanNode]) -> dict[str, Any]:
    def build(task_id: str) -> dict[str, Any]:
        node = nodes[task_id]
        payload: dict[str, Any] = {
            "task_id": node.task_id,
            "title": node.title,
            "description": node.description,
            "effort": "M" if node.altitude == "component" else "L",
            "strategy": node.strategy,
            "acceptance_criteria": node.acceptance_criteria,
            "architecture_refs": node.architecture_refs,
            "behavior_change": node.behavior_change,
            "verification_mode": node.verification_mode,
            "verification_scope": node.verification_scope,
            "implementation_status": node.implementation_status,
            "rationale": node.requirement_rationale,
            "owner": "adversarial-spec implementation agent",
        }
        if node.task_id == "SYS":
            payload["conops_refs"] = node.conops_refs
            payload["user_story_refs"] = node.user_story_refs
        else:
            payload["realizes_refs"] = node.realizes_refs
        if node.depends_on:
            payload["depends_on"] = node.depends_on
        if node.children:
            payload["children"] = [build(child) for child in node.children]
        return payload

    return {"system": build("SYS")}


def enrich_plan(plan: dict[str, Any], nodes: dict[str, PlanNode], emitter: Any) -> None:
    for task in plan["tasks"]:
        node = nodes[task["task_id"]]
        task["description"] = node.description
        task["acceptance_criteria"] = node.acceptance_criteria
        task["implementation_status"] = node.implementation_status
        task["concern_refs"] = node.concern_refs
        task["invariant_refs"] = node.invariant_refs
        task["surface_scope"] = node.surface_scope
        task["test_refs"] = node.test_refs
        task["test_files"] = node.test_files
        task["verification_mode"] = node.verification_mode
        task["verification_scope"] = node.verification_scope
        task["behavior_change"] = node.behavior_change
        # load_plan requires tested_by (validate_plan does NOT check it — served
        # validate/load asymmetry 2026-06-11; the emitter does not pass it
        # through, so stamp here). Mapping per add_tested_by.py documented
        # decision: agent-verifiable modes -> "llm"; manual-ux dogfood ->
        # "both" (gate must accept AND Jason accepts intent, US-10/TC-4.1).
        task["tested_by"] = (
            "llm" if node.verification_mode in TESTED_BY_LLM_MODES
            else "both" if node.verification_mode == "manual-ux" else "user"
        )
        if node.verify_commands:
            task["verify_commands"] = list(node.verify_commands)
        if node.exemption_reason:
            task["exemption_reason"] = node.exemption_reason
        req_id = requirement_id(node.task_id)
        if not emitter.REQUIREMENT_ID_RE.match(req_id):
            raise RuntimeError(f"bad requirement id for {node.task_id}: {req_id}")
        method = verification_method(node.verification_mode)
        task["requirement_metadata"] = {
            "requirement_id": req_id,
            "rationale": node.requirement_rationale,
            "traced_from": node.parent,
            "owner": "adversarial-spec implementation agent",
            "verification_method": method,
            "verification_level": node.altitude,
        }
        for binding in task["verification_binding"].values():
            binding["artifact"] = verification_artifact(node)
            binding["verify_commands"] = node.verify_commands
            binding["test_refs"] = node.test_refs
            binding["verification_mode"] = node.verification_mode
            binding["verification_scope"] = node.verification_scope
            if node.exemption_reason:
                binding["exemption_reason"] = node.exemption_reason


def write_node_artifacts(plan: dict[str, Any], nodes: dict[str, PlanNode]) -> None:
    for task in plan["tasks"]:
        node = nodes[task["task_id"]]
        write_text_atomic(REPO_ROOT / task["spec_refs"]["definition_artifact"], spec_doc(node, task))
        for kind, binding in task["verification_binding"].items():
            write_text_atomic(REPO_ROOT / binding["plan_artifact"], verification_doc(node, task, kind, binding))


def refresh_hashes(plan: dict[str, Any]) -> None:
    for task in plan["tasks"]:
        definition = REPO_ROOT / task["spec_refs"]["definition_artifact"]
        task["spec_refs"]["definition_hash"] = sha12(definition)
        for binding in task["verification_binding"].values():
            artifact = REPO_ROOT / binding["plan_artifact"]
            binding["plan_hash"] = sha12(artifact)


def run_requirement_lint(plan: dict[str, Any], emitter: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for task in plan["tasks"]:
        statements = {
            "description": task["description"],
            "rationale": task["requirement_metadata"]["rationale"],
        }
        for field_name, statement in statements.items():
            result = emitter.lint_requirement_text(statement)
            results.append(
                {
                    "task_id": task["task_id"],
                    "field": field_name,
                    "ok": result["ok"],
                    "tier": result["tier"],
                    "violations": result["violations"],
                }
            )
    return results


def normalize_task_ids_for_fizzy(plan: dict[str, Any]) -> None:
    mapping = {
        task["task_id"]: task["task_id"].replace(".", "-")
        for task in plan["tasks"]
        if "." in task["task_id"]
    }
    if not mapping:
        return

    def fix(value: Any) -> Any:
        return mapping.get(value, value)

    for task in plan["tasks"]:
        task["task_id"] = fix(task["task_id"])
        if task.get("parent"):
            task["parent"] = fix(task["parent"])
        for key in ("decomposes_into", "depends_on"):
            if isinstance(task.get(key), list):
                task[key] = [fix(item) for item in task[key]]
        metadata = task.get("requirement_metadata") or {}
        if metadata.get("traced_from"):
            metadata["traced_from"] = fix(metadata["traced_from"])


def validate_live_contract_shim(plan: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for task in plan.get("tasks", []):
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not RE_TASK_ID.match(task_id):
            issues.append({"code": "TASK_ID_CONTRACT_FAILED", "task_id": task_id, "field": "task_id"})

        status = task.get("implementation_status")
        if status not in VALID_IMPLEMENTATION_STATUSES:
            issues.append({"code": "MATURITY_FLOOR_VIOLATION", "task_id": task_id, "field": "implementation_status"})

        commands = task.get("verify_commands")
        needs_commands = task.get("behavior_change") is True and str(task.get("verification_mode", "")).startswith("automated")
        if needs_commands and not commands:
            issues.append({"code": "missing_required_verify_commands", "task_id": task_id, "field": "verify_commands"})
        for command in commands or []:
            if not isinstance(command, str) or not command.strip() or len(command) > 512:
                issues.append({"code": "invalid_verify_command_format", "task_id": task_id, "field": "verify_commands"})
                break

        definition = ((task.get("spec_refs") or {}).get("definition_artifact"))
        if definition and not (REPO_ROOT / definition).is_file():
            issues.append({"code": "MISSING_SPEC_ARTIFACT", "task_id": task_id, "field": "spec_refs.definition_artifact"})
        for kind, binding in (task.get("verification_binding") or {}).items():
            artifact = binding.get("plan_artifact")
            if artifact and not (REPO_ROOT / artifact).is_file():
                issues.append({"code": "MISSING_VERIFICATION_ARTIFACT", "task_id": task_id, "field": kind})
    return issues


def spec_doc(node: PlanNode, task: dict[str, Any]) -> str:
    refs = node.realizes_refs or node.user_story_refs
    lines = [
        f"# {node.task_id} {node.altitude.title()} Mini-Spec",
        "",
        f"Title: {node.title}",
        f"Altitude: {node.altitude}",
        f"Parent: {node.parent or 'null'}",
        f"Children: {', '.join(node.children) if node.children else 'none'}",
        f"Realizes refs: {', '.join(refs) if refs else 'root owner'}",
        f"Requirement ID: {task['requirement_metadata']['requirement_id']}",
        "",
        "## Requirement Statement",
        "",
        node.description,
        "",
        "## Scope",
        "",
        f"- Implementation status: {ascii_clean(node.implementation_status) or 'not specified'}",
        f"- Behavior change: {str(node.behavior_change).lower()}",
        f"- Verification mode: {node.verification_mode}",
        f"- Verification scope: {node.verification_scope}",
        f"- Strategy: {node.strategy}",
        f"- Surface scope: {', '.join(node.surface_scope) if node.surface_scope else 'not specified'}",
        "",
        "## Traceability",
        "",
        f"- Architecture refs: {', '.join(node.architecture_refs) if node.architecture_refs else 'not specified'}",
        f"- Concern refs: {', '.join(node.concern_refs) if node.concern_refs else 'not specified'}",
        f"- Invariant refs: {', '.join(node.invariant_refs) if node.invariant_refs else 'not specified'}",
        f"- Test refs: {', '.join(node.test_refs) if node.test_refs else 'not specified'}",
    ]
    if node.exemption_reason:
        lines.append(f"- Exemption reason: {ascii_clean(node.exemption_reason)}")
    lines.extend(["", "## Acceptance Criteria", ""])
    lines.extend(f"- {ascii_clean(item)}" for item in node.acceptance_criteria)
    lines.extend(["", "## Verification Summary", "", verification_summary(node), ""])
    return "\n".join(lines)


def verification_doc(node: PlanNode, task: dict[str, Any], kind: str, binding: dict[str, Any]) -> str:
    commands = node.verify_commands
    command_lines = [f"- `{cmd}`" for cmd in commands] if commands else ["- No automated command is declared for this exempt node."]
    evidence = evidence_statement(node, kind)
    lines = [
        f"# {node.task_id} {kind.replace('_', ' ').title()}",
        "",
        f"Verification kind: {binding['kind']}",
        f"Altitude obligation: {node.altitude}",
        f"Verification mode: {node.verification_mode}",
        f"Verification scope: {node.verification_scope}",
        "",
        "## What Runs",
        "",
        *command_lines,
        "",
        "## Evidence Required",
        "",
        evidence,
        "",
        "## Mapped Tests",
        "",
        f"- Test refs: {', '.join(node.test_refs) if node.test_refs else 'not specified'}",
        f"- Test files: {', '.join(node.test_files) if node.test_files else verification_artifact(node)}",
        "",
        "## Acceptance Criteria Covered",
        "",
        *(f"- {ascii_clean(item)}" for item in node.acceptance_criteria),
        "",
        "## Traceability",
        "",
        f"- Architecture refs: {', '.join(node.architecture_refs) if node.architecture_refs else 'not specified'}",
        f"- Concern refs: {', '.join(node.concern_refs) if node.concern_refs else 'not specified'}",
        f"- Invariant refs: {', '.join(node.invariant_refs) if node.invariant_refs else 'not specified'}",
        "",
    ]
    return "\n".join(lines)


def verification_summary(node: PlanNode) -> str:
    if node.verification_mode.startswith("automated"):
        return "Automated evidence is the declared pytest command passing with mapped TC coverage."
    if node.verification_mode == "static-check":
        return "Inspection/static evidence is the declared grep or pytest static check passing."
    if node.verification_mode == "artifact-sync":
        return "Artifact evidence is the documented Phase 7 section plus dogfood TC-0.1 cold-read proof."
    if node.verification_mode == "manual-ux":
        return "Manual evidence is Jason's dogfood acceptance for TC-4.1."
    return "Verification evidence follows the declared mode and mapped tests."


def evidence_statement(node: PlanNode, kind: str) -> str:
    base = verification_summary(node)
    if kind == "subsystem_verification":
        return f"{base} Child nodes must be integrated and the subsystem acceptance criterion must be satisfied."
    if kind == "system_verification":
        return f"{base} The full validation-leg close path must pass on the dogfood session without a system_validation plan binding."
    return base


def write_report(
    *,
    coverage: dict[str, Any] | None,
    self_check: dict[str, Any],
    lint_results: list[dict[str, Any]],
    judgment_calls: list[str],
    open_questions: list[str],
) -> None:
    lint_failures = [r for r in lint_results if not r.get("ok")]
    coverage_block = json.dumps(coverage, indent=2, ensure_ascii=False) if coverage is not None else "not emitted"
    self_check_block = json.dumps(self_check, indent=2, ensure_ascii=False)
    lint_block = json.dumps(
        {
            "checked": len(lint_results),
            "failures": lint_failures,
            "all_ok": not lint_failures,
        },
        indent=2,
        ensure_ascii=False,
    )
    lines = [
        "# Emission Report: validation-leg-process",
        "",
        "## Produced",
        "",
        f"- `{COVERAGE_PATH.relative_to(REPO_ROOT)}`",
        f"- `{FIZZY_PLAN_PATH.relative_to(REPO_ROOT)}`",
        "- Per-node mini-spec and verification artifacts under `.adversarial-spec/specs/validation-leg-process/<task_id>/`",
        f"- `{Path(__file__).relative_to(REPO_ROOT)}`",
        "",
        "## Coverage JSON",
        "",
        "```json",
        coverage_block,
        "```",
        "",
        "## self_check_plan raw output",
        "",
        "```json",
        self_check_block,
        "```",
        "",
        "## Requirement lint",
        "",
        "```json",
        lint_block,
        "```",
        "",
        "## Judgment Calls",
        "",
    ]
    lines.extend(f"- {ascii_clean(item)}" for item in judgment_calls)
    lines.extend(["", "## OPEN QUESTIONS", ""])
    if open_questions:
        lines.extend(f"- {ascii_clean(item)}" for item in open_questions)
    else:
        lines.append("- None.")
    lines.append("")
    write_text_atomic(REPORT_PATH, "\n".join(lines))


def segment(text: str, label: str) -> str:
    pattern = re.compile(rf"{re.escape(label)}:\s*(.*?)(?=\s+\u00b7\s+[^:\u00b7]+:|$)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def implementation_status_token(line: str) -> str:
    value = strip_md(line).removeprefix("- impl_status:").strip()
    match = re.match(r"^(greenfield|partial|already-built)\b", value)
    return match.group(1) if match else value


def bracket_items(text: str, label: str) -> list[str]:
    match = re.search(rf"{re.escape(label)}:\s*\[([^\]]*)\]", text)
    return split_items(match.group(1)) if match else []


def split_items(text: str) -> list[str]:
    text = strip_md(text).strip()
    if not text:
        return []
    parts = re.split(r"\s*,\s*", text)
    return [p.strip(" `.;") for p in parts if p.strip(" `.;")]


def backtick_items(text: str) -> list[str]:
    return re.findall(r"`([^`]+)`", text)


def files_after_label(line: str, label: str) -> list[str]:
    if f"{label}:" not in line:
        return []
    tail = line.split(f"{label}:", 1)[1]
    return backtick_items(tail)


def task_refs(text: str) -> list[str]:
    return re.findall(r"\b(?:SS-\d+|C-\d+\.\d+|SYS)\b", text)


def us_ids(text: str) -> list[str]:
    return unique(re.findall(r"\bUS-\d+\b", text))


def tc_ids(text: str) -> list[str]:
    return unique(re.findall(r"\bTC-[A-Z0-9.-]+", text))


def invariant_items(text: str) -> list[str]:
    refs: list[str] = []
    if "INV-A1..A7" in text or "(and all)" in text:
        refs.extend(ARCH_INV_A)
    refs.extend(re.findall(r"\bINV-A\d+\b|\bINV-\d+\b", text))
    return unique(refs)


def default_verify_commands(mode: str, scope: str) -> list[str]:
    if mode == "automated-unit":
        return ["uv run pytest scripts/tests/test_validation_emission.py -q"]
    if mode == "automated-integration":
        return ["uv run pytest scripts/tests/test_validation_emission.py -q"]
    if mode == "static-check":
        return ["uv run pytest scripts/tests/test_validation_emission.py -k doc_error_codes -q"]
    if mode in {"artifact-sync", "manual-ux"}:
        return []
    if scope in {"targeted", "full-suite"}:
        return ["uv run pytest scripts/tests/test_validation_emission.py -q"]
    return []


def verification_artifact(node: PlanNode) -> str:
    if node.test_files:
        return node.test_files[0]
    if node.verification_mode == "artifact-sync":
        return "skills/adversarial-spec/phases/07-execution.md"
    if node.verification_mode == "static-check":
        return "skills/adversarial-spec/phases/08-implementation.md"
    if node.verification_mode == "manual-ux":
        return ".adversarial-spec/specs/validation-leg-process/dogfood-validation.md"
    return "scripts/tests/test_validation_emission.py"


def verification_method(mode: str) -> str:
    if mode.startswith("automated"):
        return "test"
    if mode == "manual-ux":
        return "demonstration"
    return "inspection"


def requirement_id(task_id: str) -> str:
    if task_id == "SYS":
        return "SYS-1"
    if re.fullmatch(r"SS-\d+", task_id):
        return task_id
    match = re.fullmatch(r"C-(\d+)\.(\d+)", task_id)
    if match:
        return f"C-R{match.group(1)}{match.group(2).zfill(2)}"
    raise ValueError(f"unsupported task id: {task_id}")


def words(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("-", " ")).strip()


def strip_md(value: str) -> str:
    return value.replace("**", "").replace("`", "")


def ascii_clean(value: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2011": "-",
        "\u2192": "->",
        "\u2260": "!=",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2713": "PASS",
        "\u00b7": "-",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return value.encode("ascii", "replace").decode("ascii")


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    write_text_atomic(path, text)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
