"""Convert a closed v6 D0 record into the bounded leaf plan ``pipeline_load`` accepts.

v6 Debate is a leaf fan-out: after ``pipeline_mark_decomposition_complete`` sets
``d0_closed``, the session loads its D0 component tree (plan schema 3, altitude
tree) while the session card is in Debate. fizzy creates the aggregate root in
``Decomposed`` and one Task Card per leaf in ``Specifying``, and freezes the leaf
set as ``debate_leaf_inventory`` for the Pre-Gauntlet barrier.

Input: ``<spec_dir>/decomposition/d0.json`` plus the manifest it names (its
``d0`` block holds components, responsibilities, CUT edges and interface
records). The conversion is deterministic and fails closed when the D0 record
and its manifest disagree (hash drift, leaf set drift, missing definition doc).

The shape mirrors fizzy-pipeline-mcp ``_validate_plan`` / ``_validate_altitude_plan``
/ ``load_plan``; fizzy's validator stays the authority (``pipeline_validate_plan``).

Usage::

    uv run python skills/adversarial-spec/scripts/d0_to_load_plan.py \\
        <project>/.adversarial-spec/specs/<slug>/decomposition/d0.json \\
        --out <project>/.adversarial-spec/specs/<slug>/decomposition/leaf-load-plan.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PLAN_SCHEMA_VERSION = 3  # fizzy V4_PLAN_SCHEMA_VERSION: the altitude-tree plan schema.

# Mirrors fizzy ALTITUDE_OBLIGATIONS: binding keys must equal the node's obligations.
ALTITUDE_OBLIGATIONS: dict[str, tuple[str, ...]] = {
    "component": ("component_verification",),
    "subsystem": ("component_verification", "subsystem_verification"),
    "system": ("component_verification", "subsystem_verification", "system_verification"),
}

RE_TASK_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")  # fizzy RE_TASK_ID
RE_ARCH_REF = re.compile(r"\.architecture/[A-Za-z0-9_./-]+?\.md")
ARCH_FALLBACK = ".architecture/primer.md"

# Load-time policy shared by every bounded leaf. The authoritative per-leaf test
# suite does not exist yet: it is bound at A/B closure (pipeline_record_ab_closure)
# while the card is in Specifying.
DEFAULT_TEST_TARGET = "tests/"
DEFAULT_VERIFY_COMMAND = "uv run pytest tests/ -q"
LEAF_SCOPE_NOTE = (
    "A-phase (obligations + failing tests) happens in Specifying; this description "
    "is the D0-level scope, not the spec."
)


class ConversionError(Exception):
    """The D0 record cannot be converted into a faithful bounded leaf plan."""


def _sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, what: str) -> dict[str, Any]:
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConversionError(f"{what} unreadable: {path}: {exc}") from exc
    if not isinstance(blob, dict):
        raise ConversionError(f"{what} must be a JSON object: {path}")
    return blob


def _project_root(d0_path: Path, manifest_rel: str) -> Path:
    """First ancestor of the D0 record under which ``manifest_rel`` resolves."""
    for candidate in d0_path.resolve().parents:
        if (candidate / manifest_rel).is_file():
            return candidate
    raise ConversionError(
        f"manifest_path {manifest_rel!r} does not resolve under any ancestor of {d0_path}"
    )


def load_d0(d0_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    """Return ``(d0_record, manifest, project_root)`` after hash/identity checks."""
    record = _load_json(d0_path, "D0 record")
    manifest_rel = record.get("manifest_path")
    if not isinstance(manifest_rel, str) or not manifest_rel.strip():
        raise ConversionError("D0 record has no manifest_path")
    root = _project_root(d0_path, manifest_rel)
    manifest_path = root / manifest_rel

    declared = str(record.get("manifest_sha256") or "").removeprefix("sha256:")
    actual = _sha256_hex(manifest_path)
    if declared != actual:
        raise ConversionError(
            f"manifest hash drift: d0.json declares sha256:{declared or '<none>'}, "
            f"{manifest_rel} is sha256:{actual}. Re-close D0 before loading."
        )
    manifest = _load_json(manifest_path, "manifest")
    if manifest.get("session_id") != record.get("session_id"):
        raise ConversionError(
            f"session mismatch: d0.json {record.get('session_id')!r} vs "
            f"manifest {manifest.get('session_id')!r}"
        )
    if not isinstance(manifest.get("d0"), dict):
        raise ConversionError(f"{manifest_rel} has no d0 block")
    return record, manifest, root


def _architecture_refs(evidence: list[str], project_root: Path) -> list[str]:
    """Existing ``.architecture/*.md`` files cited by D0 evidence, first-seen order."""
    if not (project_root / ".architecture").is_dir():
        return []
    refs: list[str] = []
    for text in evidence:
        for ref in RE_ARCH_REF.findall(text):
            if ref not in refs and (project_root / ref).is_file():
                refs.append(ref)
    if not refs and (project_root / ARCH_FALLBACK).is_file():
        refs.append(ARCH_FALLBACK)
    return refs


RE_SECTION_HEADING = re.compile(r"^## (\d+)\. (.+?)\s*$")


def load_context_map(map_path: Path, project_root: Path, leaf_ids: list[str]) -> dict[str, str]:
    """Per-leaf "read before specifying" sentences from an operator-approved map.

    fizzy's specify handout makes the agent read ``task.description`` (not the
    definition artifact), so reading that must happen goes into the description.
    Map shape: ``{"doc": "<project-relative .md>", "leaves": {"L1": [8, 7], ...}}``
    with ``##``-level section numbers. Fails closed on an unknown doc, a missing or
    unknown leaf, or a section number the doc does not have.
    """
    blob = _load_json(map_path, "context map")
    doc_rel = blob.get("doc")
    if not isinstance(doc_rel, str) or not (project_root / doc_rel).is_file():
        raise ConversionError(f"context map doc {doc_rel!r} is not a file under {project_root}")
    titles: dict[int, str] = {}
    for line in (project_root / doc_rel).read_text(encoding="utf-8").splitlines():
        if match := RE_SECTION_HEADING.match(line):
            titles[int(match.group(1))] = match.group(2)
    leaves = blob.get("leaves")
    if not isinstance(leaves, dict) or sorted(leaves) != sorted(leaf_ids):
        raise ConversionError(
            f"context map must cover exactly the D0 leaves {sorted(leaf_ids)}; "
            f"got {sorted(leaves) if isinstance(leaves, dict) else leaves!r}"
        )
    reading: dict[str, str] = {}
    for leaf_id in leaf_ids:
        sections = leaves[leaf_id]
        missing = [s for s in sections if not isinstance(s, int) or s not in titles]
        if not sections or missing:
            raise ConversionError(
                f"context map leaf {leaf_id}: sections {missing or sections!r} not in {doc_rel}"
            )
        cited = "; ".join(f"§{s} {titles[s]}" for s in sections)
        reading[leaf_id] = f"Read before specifying: {doc_rel} {cited}."
    return reading


def build_plan(
    record: dict[str, Any],
    manifest: dict[str, Any],
    project_root: Path,
    *,
    test_target: str = DEFAULT_TEST_TARGET,
    verify_command: str = DEFAULT_VERIFY_COMMAND,
    context_reading: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the plan-schema-3 bounded leaf plan for one closed D0 record."""
    d0 = manifest["d0"]
    session_id = record["session_id"]
    manifest_rel = record["manifest_path"]
    components = d0.get("components")
    if not isinstance(components, list) or not components:
        raise ConversionError("manifest d0.components must be a non-empty list")

    by_id: dict[str, dict[str, Any]] = {}
    children: dict[str, list[str]] = {}
    for node in components:
        node_id = node.get("node_id")
        if not isinstance(node_id, str) or not RE_TASK_ID.match(node_id):
            raise ConversionError(f"component node_id {node_id!r} is not a legal fizzy task_id")
        if node_id in by_id:
            raise ConversionError(f"duplicate component node_id {node_id!r}")
        if node.get("kind") not in ALTITUDE_OBLIGATIONS:
            raise ConversionError(f"component {node_id} has unknown kind {node.get('kind')!r}")
        by_id[node_id] = node
        children.setdefault(node_id, [])
    roots = [n["node_id"] for n in components if n.get("parent_id") is None]
    if roots != [record.get("root_node")]:
        raise ConversionError(f"root mismatch: d0.json root_node {record.get('root_node')!r}, tree roots {roots}")
    for node in components:
        parent = node.get("parent_id")
        if parent is not None:
            if parent not in by_id:
                raise ConversionError(f"component {node['node_id']} parent {parent!r} not in tree")
            children[parent].append(node["node_id"])
    tree_leaves = sorted(nid for nid, kids in children.items() if not kids)
    declared_leaves = sorted(record.get("leaf_ids") or [])
    if tree_leaves != declared_leaves:
        raise ConversionError(
            f"leaf drift: d0.json leaf_ids {declared_leaves} != manifest tree leaves {tree_leaves}"
        )

    spec_rel = manifest.get("spec_path") or manifest.get("requirements_summary_path")
    if not isinstance(spec_rel, str) or not (project_root / spec_rel).is_file():
        raise ConversionError(
            f"definition document {spec_rel!r} (manifest spec_path or "
            "requirements_summary_path) is not a file under the project root"
        )
    spec_hash = _sha256_hex(project_root / spec_rel)[:12]
    manifest_hash = _sha256_hex(project_root / manifest_rel)[:12]

    rows = {r["responsibility_id"]: r for r in d0.get("responsibility_rows") or []}
    allocation: dict[str, list[str]] = {}
    for item in d0.get("allocation") or []:
        allocation.setdefault(item["node_id"], []).append(item["responsibility_id"])
    edge_evidence = {e["edge_id"]: e for e in d0.get("responsibility_edges") or []}
    interfaces = d0.get("interface_records") or []

    def binding(altitude: str) -> dict[str, Any]:
        return {
            kind: {
                "plan_artifact": manifest_rel,
                "plan_hash": manifest_hash,
                "artifact": manifest_rel,
                "kind": "verification",
            }
            for kind in ALTITUDE_OBLIGATIONS[altitude]
        }

    tasks: list[dict[str, Any]] = []
    for node in components:
        node_id = node["node_id"]
        altitude = node["kind"]
        parent = node.get("parent_id")
        kids = children[node_id]
        realizes = list(node.get("realizes_refs") or [])
        touching = [i for i in interfaces if node_id in (i["producer_node"], i["consumer_node"])]
        resp_ids = allocation.get(node_id, [])

        evidence: list[str] = []
        for rid in resp_ids:
            evidence.extend(rows.get(rid, {}).get("evidence_refs") or [])
        for iface in touching:
            evidence.append(str(edge_evidence.get(iface["edge_id"], {}).get("evidence", "")))

        if kids:
            description = (
                f"{node['title']}. D0 aggregate {altitude} node {node_id} of session "
                f"{session_id}; decomposes into {', '.join(kids)}. Contracts: {manifest_rel} "
                f"d0.interface_records. Container only: work happens on the leaves."
            )
            acceptance = [
                "every child leaf is Synthesized or carries a legal DEFERRED/NO_GO leaf exception",
                "every D0 CUT edge is SEAM_CLOSED or carries a recorded seam deferral before the "
                "Pre-Gauntlet barrier",
            ]
        else:
            resp_text = "; ".join(
                f"{rid}: {rows.get(rid, {}).get('output', '').strip().rstrip('.')}" for rid in resp_ids
            ) or "none allocated"
            iface_text = "; ".join(
                f"{i['edge_id']} {i['producer_node']}->{i['consumer_node']} "
                f"(owner {i['owner']}, {i['contract_test_id']})"
                for i in touching
            ) or "none"
            description = (
                f"{node['title']}. D0 leaf {node_id} of {record['root_node']} (session "
                f"{session_id}). Responsibilities: {resp_text}. CUT-edge interfaces: "
                f"{iface_text}. Contracts: {manifest_rel} d0.interface_records. {LEAF_SCOPE_NOTE}"
            )
            if context_reading:
                description += f" {context_reading[node_id]}"
            acceptance = [
                "A/B closure recorded: obligations and failing tests in keyed bijection, "
                "3 clean red runs, both oracle controls",
            ] + [
                f"{i['contract_test_id']} ({i['edge_id']} {i['producer_node']}->"
                f"{i['consumer_node']}, {i['interface_type']}) bound and passing at C conformance"
                for i in touching
            ]

        task: dict[str, Any] = {
            "task_id": node_id,
            "title": node["title"],
            "description": description,
            "wave": 0,
            "effort": "M",
            "strategy": "test-first",
            "acceptance_criteria": acceptance,
            "architecture_refs": _architecture_refs(evidence, project_root),
            "behavior_change": True,
            "verification_mode": "automated-integration",
            "verification_scope": "targeted",
            "tested_by": "llm",
            "test_targets": [test_target],
            "verify_commands": [verify_command],
            "depends_on": [],
            "altitude": altitude,
            "parent": parent,
            "parent_task_id": parent,
            "decomposes_into": kids,
            "spec_refs": {"definition_artifact": spec_rel, "definition_hash": spec_hash},
            "verification_binding": binding(altitude),
        }
        if altitude == "system":
            task["system_spec_path"] = spec_rel
            task["conops_refs"] = realizes
            task["user_story_refs"] = realizes
        else:
            if altitude == "subsystem":
                task["subsystem_spec_path"] = spec_rel
            task["realizes_refs"] = realizes
        tasks.append(task)

    return {
        "plan_schema_version": PLAN_SCHEMA_VERSION,
        "session_id": session_id,
        "title": by_id[record["root_node"]]["title"],
        "tasks": tasks,
    }


def leaf_task_ids(plan: dict[str, Any]) -> list[str]:
    """Executable leaves exactly as fizzy computes them: tasks nobody names as parent."""
    parents = {t.get("parent") for t in plan["tasks"] if t.get("parent")}
    return sorted(t["task_id"] for t in plan["tasks"] if t["task_id"] not in parents)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("d0_json", type=Path, help="<spec_dir>/decomposition/d0.json")
    parser.add_argument("--out", type=Path, help="write the plan here (default: stdout)")
    parser.add_argument("--test-target", default=DEFAULT_TEST_TARGET)
    parser.add_argument("--verify-command", default=DEFAULT_VERIFY_COMMAND)
    parser.add_argument(
        "--context-map", type=Path,
        help='JSON {"doc": <project-relative .md>, "leaves": {"L1": [8, 7], ...}}: '
        "per-leaf sections appended to each leaf description as required reading",
    )
    args = parser.parse_args(argv)

    try:
        record, manifest, root = load_d0(args.d0_json)
        context_reading = (
            load_context_map(args.context_map, root, list(record.get("leaf_ids") or []))
            if args.context_map else None
        )
        plan = build_plan(
            record, manifest, root,
            test_target=args.test_target, verify_command=args.verify_command,
            context_reading=context_reading,
        )
    except ConversionError as exc:
        print(f"d0_to_load_plan: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
    if args.out is None:
        sys.stdout.write(text)
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(json.dumps({
        "plan_path": str(args.out.resolve()),
        "session_id": plan["session_id"],
        "project_root": str(root),
        "task_count": len(plan["tasks"]),
        "leaf_task_ids": leaf_task_ids(plan),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
