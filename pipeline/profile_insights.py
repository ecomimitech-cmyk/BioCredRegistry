"""
BioCred Profile Insights Generator v1.0

Rule-based text generator for the 4–6 bullet "Profile Insights" section.
Takes a translated payload (from translation_engine.translate_profile)
and produces neutral, descriptive sentences.

Language rules (from Alexander's Profile Page Spec):
  USE:   significant, concentrated, distributed, limited, recurrent, sparse
  AVOID: strong, weak, high/low, better, advanced
"""

from __future__ import annotations
from collections import Counter

AXIS_ORDER = ["KR", "LOC", "SHS", "FAP", "RP"]

AXIS_NAMES = {
    "KR":  "Knowledge & Research",
    "LOC": "Leadership & Operational Coordination",
    "SHS": "Species & Habitat Specialization",
    "FAP": "Field & Applied Practice",
    "RP":  "Regulation & Policy",
}

_CONCENTRATION_THRESHOLDS = {
    "significant": 0.40,
    "moderate":    0.25,
    "limited":     0.10,
}


def _mean_weights(units: list) -> dict:
    if not units:
        return {a: 0.2 for a in AXIS_ORDER}
    totals = {a: 0.0 for a in AXIS_ORDER}
    for u in units:
        w = u.get("domain_weights", {})
        for a in AXIS_ORDER:
            totals[a] += w.get(a, 0)
    n = len(units)
    return {a: round(totals[a] / n, 4) for a in AXIS_ORDER}


def _sorted_axes(mean: dict) -> list:
    return sorted(AXIS_ORDER, key=lambda a: -mean[a])


def _primary_concentration(mean: dict) -> str | None:
    ranked = _sorted_axes(mean)
    top = ranked[0]
    val = mean[top]
    if val >= _CONCENTRATION_THRESHOLDS["significant"]:
        return (
            f"Experience is significantly concentrated in "
            f"{AXIS_NAMES[top]}."
        )
    if val >= _CONCENTRATION_THRESHOLDS["moderate"]:
        return (
            f"Experience shows moderate concentration in "
            f"{AXIS_NAMES[top]}."
        )
    return "Experience is distributed across multiple dimensions with no single concentration."


def _secondary_distribution(mean: dict) -> str | None:
    ranked = _sorted_axes(mean)
    primary_val = mean[ranked[0]]
    secondaries = [
        a for a in ranked[1:]
        if mean[a] >= _CONCENTRATION_THRESHOLDS["limited"]
    ]
    if not secondaries or primary_val < _CONCENTRATION_THRESHOLDS["moderate"]:
        return None
    if len(secondaries) == 1:
        return (
            f"Secondary presence in {AXIS_NAMES[secondaries[0]]}."
        )
    names = [AXIS_NAMES[a] for a in secondaries[:3]]
    return f"Secondary presence distributed across {', '.join(names)}."


def _regulatory_breadth(units: list) -> str | None:
    reg_types: set[str] = set()
    for u in units:
        ctx = u.get("contexts", {})
        for ri in ctx.get("regulatory_interactions", []):
            reg_types.add(ri)
    if not reg_types:
        return None
    if len(reg_types) >= 4:
        return f"Recurrent regulatory interaction across {len(reg_types)} coordination types."
    if len(reg_types) >= 2:
        return f"Regulatory interaction in {len(reg_types)} coordination contexts."
    return "Limited regulatory interaction noted in one coordination context."


def _species_modes(units: list) -> str | None:
    modes: set[str] = set()
    for u in units:
        ctx = u.get("contexts", {})
        for sm in ctx.get("species_interaction_modes", []):
            modes.add(sm)
    if not modes:
        return None
    mode_labels = {
        "observation": "observation",
        "survey": "surveys",
        "monitoring": "monitoring",
        "capture": "capture",
        "handling": "handling",
        "relocation": "relocation",
        "oversight": "oversight",
    }
    named = [mode_labels.get(m, m) for m in sorted(modes)]
    if len(named) >= 4:
        return f"Species interaction across {len(named)} modes including {', '.join(named[:3])}."
    if len(named) >= 2:
        return f"Species interaction includes {' and '.join(named)}."
    return f"Species interaction limited to {named[0]}."


def _environment_diversity(units: list) -> str | None:
    envs: set[str] = set()
    for u in units:
        ctx = u.get("contexts", {})
        for we in ctx.get("working_environments", []):
            envs.add(we)
    if not envs:
        return None
    env_labels = {
        "hydrologic_systems": "hydrologic systems",
        "terrestrial_natural_systems": "terrestrial systems",
        "coastal_marine_systems": "coastal/marine systems",
        "managed_engineered_landscapes": "managed landscapes",
        "transitional_ecotonal_systems": "ecotonal systems",
    }
    named = [env_labels.get(e, e) for e in sorted(envs)]
    if len(named) >= 3:
        return f"Project environments span {len(named)} system types."
    if len(named) == 2:
        return f"Experience across {named[0]} and {named[1]}."
    return f"Project environments concentrated in {named[0]}."


def _notable_gaps(mean: dict) -> str | None:
    sparse = [
        AXIS_NAMES[a] for a in AXIS_ORDER
        if mean[a] < _CONCENTRATION_THRESHOLDS["limited"]
    ]
    if not sparse:
        return None
    if len(sparse) >= 3:
        return "Several dimensions show sparse representation."
    return f"Sparse representation in {' and '.join(sparse)}."


def generate_insights(payload: dict) -> list[str]:
    """Generate 4-6 neutral insight bullets from a translated profile payload."""
    units = payload.get("evidence_units", [])
    if not units:
        return ["Insufficient evidence data to generate profile insights."]

    mean = _mean_weights(units)
    generators = [
        _primary_concentration,
        _secondary_distribution,
        _regulatory_breadth,
        _species_modes,
        _environment_diversity,
        _notable_gaps,
    ]

    insights: list[str] = []
    for gen in generators:
        if len(insights) >= 6:
            break
        if gen in (_primary_concentration, _secondary_distribution, _notable_gaps):
            result = gen(mean)
        else:
            result = gen(units)
        if result:
            insights.append(result)

    return insights if insights else [
        "Experience is distributed across multiple dimensions with no single concentration."
    ]
