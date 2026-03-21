"""Regression tests for adversary registries and template definitions."""

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from adversaries import (
    ADVERSARIES,
    ADVERSARY_PREFIXES,
    ADVERSARY_TEMPLATES,
    AdversaryTemplate,
    resolve_adversary_name,
)


def test_adversary_template_copies_and_freezes_fixed_fields():
    """Template inputs must not remain externally mutable after construction."""
    focus_areas = ["Existing code reuse"]
    scope_guidelines = {"domain:cli-tool": "Prefer builtins."}

    template = AdversaryTemplate(
        name="minimalist",
        prefix="MINI",
        tone="Be practical.",
        focus_areas=focus_areas,
        valid_dismissal="Show the simpler path fails.",
        invalid_dismissal="Appeal to fashion.",
        rule="Prove complexity is needed.",
        scope_guidelines=scope_guidelines,
    )

    focus_areas.append("Future-proofing")
    scope_guidelines["domain:library"] = "This should not appear."

    assert template.focus_areas == ("Existing code reuse",)
    assert dict(template.scope_guidelines) == {"domain:cli-tool": "Prefer builtins."}

    with pytest.raises(TypeError):
        template.scope_guidelines["domain:library"] = "Mutate in place"

    with pytest.raises(FrozenInstanceError):
        template.focus_areas = ("new",)


def test_resolve_adversary_name_maps_legacy_names_to_minimalist():
    """Legacy roster names should resolve to the merged canonical adversary."""
    assert resolve_adversary_name("lazy_developer") == "minimalist"
    assert resolve_adversary_name("prior_art_scout") == "minimalist"
    assert resolve_adversary_name("architect") == "architect"


def test_adversary_registry_replaces_legacy_names_with_new_roster():
    """Canonical gauntlet registry should expose merged and new adversaries only."""
    assert "minimalist" in ADVERSARIES
    assert "traffic_engineer" in ADVERSARIES
    assert "lazy_developer" not in ADVERSARIES
    assert "prior_art_scout" not in ADVERSARIES


def test_adversary_templates_capture_new_roster_and_focus_splits():
    """Template registry should include new adversaries and sharpened focus areas."""
    assert "minimalist" in ADVERSARY_TEMPLATES
    assert "traffic_engineer" in ADVERSARY_TEMPLATES

    burned = ADVERSARY_TEMPLATES["burned_oncall"].focus_areas
    peda = ADVERSARY_TEMPLATES["pedantic_nitpicker"].focus_areas
    assh = ADVERSARY_TEMPLATES["asshole_loner"].focus_areas

    assert any("recovery" in area.lower() for area in burned)
    assert any("nullability" in area.lower() or "precision" in area.lower() for area in peda)
    assert any("state machine" in area.lower() or "invariant" in area.lower() for area in assh)


def test_adversary_prefixes_keep_historical_aliases_and_new_prefixes():
    """Historical concern IDs must keep resolving after the roster swap."""
    assert ADVERSARY_PREFIXES["minimalist"] == "MINI"
    assert ADVERSARY_PREFIXES["traffic_engineer"] == "TRAF"
    assert ADVERSARY_PREFIXES["lazy_developer"] == "LAZY"
    assert ADVERSARY_PREFIXES["prior_art_scout"] == "PREV"
