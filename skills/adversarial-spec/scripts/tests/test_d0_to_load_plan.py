"""d0_to_load_plan: closed v6 D0 record -> bounded leaf plan for pipeline_load."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import d0_to_load_plan as conv
import pytest

SESSION = "adv-spec-202609220000-fixture"
SPEC_DIR = ".adversarial-spec/specs/fixture"


def _project(tmp_path: Path, *, leaf_ids: list[str] | None = None, tamper: bool = False) -> Path:
    """Tiny consuming project: subsystem root R with leaves A and B, one CUT edge A->B."""
    (tmp_path / ".architecture/structured/components").mkdir(parents=True)
    (tmp_path / ".architecture/primer.md").write_text("# primer\n")
    (tmp_path / ".architecture/structured/components/alpha.md").write_text("# alpha\n")
    spec_dir = tmp_path / SPEC_DIR
    (spec_dir / "decomposition").mkdir(parents=True)
    (spec_dir / "requirements-v0.md").write_text("# requirements\n")
    manifest = {
        "session_id": SESSION,
        "session_altitude": "subsystem",
        "spec_path": None,
        "requirements_summary_path": f"{SPEC_DIR}/requirements-v0.md",
        "d0": {
            "components": [
                {"node_id": "R", "parent_id": None, "kind": "subsystem", "is_leaf": False,
                 "title": "Root", "realizes_refs": ["G1", "G2"]},
                {"node_id": "A", "parent_id": "R", "kind": "component", "is_leaf": True,
                 "title": "Alpha", "realizes_refs": ["G1"]},
                {"node_id": "B", "parent_id": "R", "kind": "component", "is_leaf": True,
                 "title": "Beta", "realizes_refs": ["G2"]},
            ],
            "responsibility_rows": [
                {"responsibility_id": "R01", "output": "alpha facts",
                 "evidence_refs": [".architecture/structured/components/alpha.md:1-3", "req §1"]},
                {"responsibility_id": "R02", "output": "beta verdict", "evidence_refs": ["req §2"]},
            ],
            "allocation": [
                {"responsibility_id": "R01", "node_id": "A"},
                {"responsibility_id": "R02", "node_id": "B"},
            ],
            "responsibility_edges": [
                {"edge_id": "E01", "from_node": "A", "to_node": "B", "classification": "CUT",
                 "evidence": "see .architecture/missing.md and alpha"},
            ],
            "interface_records": [
                {"edge_id": "E01", "producer_node": "A", "consumer_node": "B", "owner": "A",
                 "interface_type": "data", "contract_test_id": "TC-FX-E01"},
            ],
        },
    }
    manifest_path = spec_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if tamper:
        manifest_path.write_text(json.dumps({**manifest, "session_altitude": "system"}))
    d0 = {
        "session_id": SESSION,
        "manifest_path": f"{SPEC_DIR}/manifest.json",
        "manifest_sha256": f"sha256:{digest}",
        "root_node": "R",
        "leaf_ids": leaf_ids if leaf_ids is not None else ["A", "B"],
    }
    d0_path = spec_dir / "decomposition" / "d0.json"
    d0_path.write_text(json.dumps(d0))
    return d0_path


def _convert(d0_path: Path) -> dict:
    record, manifest, root = conv.load_d0(d0_path)
    return conv.build_plan(record, manifest, root)


def test_one_specifying_leaf_task_per_d0_leaf_under_the_aggregate_root(tmp_path: Path) -> None:
    plan = _convert(_project(tmp_path))
    tasks = {t["task_id"]: t for t in plan["tasks"]}

    assert plan["plan_schema_version"] == 3
    assert plan["session_id"] == SESSION
    assert conv.leaf_task_ids(plan) == ["A", "B"]
    root = tasks["R"]
    assert root["parent"] is None and root["decomposes_into"] == ["A", "B"]
    assert root["realizes_refs"] == ["G1", "G2"]
    assert root["subsystem_spec_path"] == f"{SPEC_DIR}/requirements-v0.md"
    assert set(root["verification_binding"]) == {"component_verification", "subsystem_verification"}

    alpha = tasks["A"]
    assert alpha["parent"] == "R" and alpha["altitude"] == "component"
    assert set(alpha["verification_binding"]) == {"component_verification"}
    assert "subsystem_spec_path" not in alpha
    assert alpha["realizes_refs"] == ["G1"]
    # Each touching CUT-edge contract test becomes a leaf acceptance criterion.
    assert any("TC-FX-E01" in ac for ac in alpha["acceptance_criteria"])
    assert any("TC-FX-E01" in ac for ac in tasks["B"]["acceptance_criteria"])
    # Evidence-cited architecture docs that exist; missing ones are dropped.
    assert alpha["architecture_refs"] == [".architecture/structured/components/alpha.md"]
    assert tasks["B"]["architecture_refs"] == [".architecture/primer.md"]


def test_manifest_drift_since_d0_closure_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(conv.ConversionError, match="manifest hash drift"):
        conv.load_d0(_project(tmp_path, tamper=True))


def test_leaf_ids_disagreeing_with_the_tree_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(conv.ConversionError, match="leaf drift"):
        _convert(_project(tmp_path, leaf_ids=["A"]))


def _context_map(tmp_path: Path, leaves: dict) -> Path:
    (tmp_path / SPEC_DIR / "draft-v2.md").write_text(
        "# Draft\n\n## 1. Problem\n\ntext\n\n## 2. Snapshot schema\n\n### 2.1 detail\n"
    )
    map_path = tmp_path / "reading-map.json"
    map_path.write_text(json.dumps({"doc": f"{SPEC_DIR}/draft-v2.md", "leaves": leaves}))
    return map_path


def test_context_map_sections_become_required_reading_in_leaf_descriptions(tmp_path: Path) -> None:
    d0_path = _project(tmp_path)
    record, manifest, root = conv.load_d0(d0_path)
    reading = conv.load_context_map(
        _context_map(tmp_path, {"A": [2, 1], "B": [1]}), root, record["leaf_ids"],
    )
    tasks = {t["task_id"]: t for t in conv.build_plan(record, manifest, root, context_reading=reading)["tasks"]}

    assert tasks["A"]["description"].endswith(
        f"Read before specifying: {SPEC_DIR}/draft-v2.md §2 Snapshot schema; §1 Problem."
    )
    assert "Read before specifying" not in tasks["R"]["description"]


@pytest.mark.parametrize("leaves", [{"A": [1]}, {"A": [1], "B": [3]}])
def test_context_map_missing_leaf_or_unknown_section_fails_closed(tmp_path: Path, leaves: dict) -> None:
    d0_path = _project(tmp_path)
    record, _manifest, root = conv.load_d0(d0_path)

    with pytest.raises(conv.ConversionError, match="context map"):
        conv.load_context_map(_context_map(tmp_path, leaves), root, record["leaf_ids"])


def test_cli_output_is_byte_identical_across_runs(tmp_path: Path) -> None:
    d0_path = _project(tmp_path)
    first, second = tmp_path / "p1.json", tmp_path / "p2.json"

    assert conv.main([str(d0_path), "--out", str(first)]) == 0
    assert conv.main([str(d0_path), "--out", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()
