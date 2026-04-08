"""
BioCred Translation Engine v1.0
Deterministic mapping: Phase-1 DB records → Phase-2 axis weights + density inputs.
Implements Alexander Funk's TE Spec v1.0 exactly.
No scoring, no ranking, no AI — translation only.
"""

import datetime
import re

from pipeline.context_matcher import match_contexts
from pipeline.te_constants import (
    TRANSLATION_VERSION, AXIS_ORDER, BASE_VECTORS,
    ACTIVITY_PATTERNS, ROLE_MODIFIERS, SPECIES_MODE_MODIFIERS,
    DURATION_BRACKETS, DURATION_MAX,
    VERIFICATION_FACTORS, ROLE_INTENSITY_FACTORS,
)

CURRENT_YEAR = datetime.date.today().year
_unknown_activity_log = []


def get_unknown_log():
    return list(_unknown_activity_log)


def clear_unknown_log():
    _unknown_activity_log.clear()


def base_vector(domain_category: str) -> dict:
    return dict(BASE_VECTORS.get(domain_category, BASE_VECTORS["field_experience"]))


def clamp_and_renormalize(weights: dict) -> dict:
    w = {ax: max(0, weights.get(ax, 0)) for ax in AXIS_ORDER}
    total = sum(w.values())
    if total == 0:
        return {ax: 0.2 for ax in AXIS_ORDER}
    return {ax: round(w[ax] / total, 4) for ax in AXIS_ORDER}


def _match_activity(text: str) -> dict | None:
    text_lower = text.lower()
    for entry in ACTIVITY_PATTERNS:
        for pat in entry["patterns"]:
            if re.search(pat, text_lower):
                return dict(entry["modifier"])
    return None


def apply_activity_modifier(weights: dict, activity_type: str) -> dict:
    if not activity_type:
        return weights
    mod = _match_activity(activity_type)
    if mod is None:
        _unknown_activity_log.append(activity_type)
        return weights
    w = {ax: weights.get(ax, 0) + mod.get(ax, 0) for ax in AXIS_ORDER}
    return clamp_and_renormalize(w)


def apply_role_modifier(weights: dict, role_level: str) -> dict:
    mod = ROLE_MODIFIERS.get(role_level, ROLE_MODIFIERS["participant"])
    total_increase = sum(v for v in mod.values() if v > 0)
    if total_increase == 0:
        return weights

    target_axes = {ax for ax, v in mod.items() if v > 0}
    non_targets = [(ax, weights[ax]) for ax in AXIS_ORDER if ax not in target_axes]
    non_targets.sort(key=lambda x: -x[1])
    top_two = [nt[0] for nt in non_targets[:2]]
    top_sum = sum(weights[ax] for ax in top_two)

    w = dict(weights)
    for ax, bonus in mod.items():
        if bonus > 0:
            w[ax] = w[ax] + bonus
    if top_sum > 0:
        for ax in top_two:
            share = weights[ax] / top_sum
            w[ax] = w[ax] - total_increase * share
    return clamp_and_renormalize(w)


def apply_species_mode_tweaks(weights: dict, contexts: dict) -> dict:
    modes = contexts.get("species_interaction_modes", [])
    if not modes:
        return weights
    w = dict(weights)
    for mode in modes:
        mod = SPECIES_MODE_MODIFIERS.get(mode, {})
        for ax, delta in mod.items():
            w[ax] = w.get(ax, 0) + delta
    return clamp_and_renormalize(w)


def apply_regulatory_tweaks(weights: dict, contexts: dict) -> dict:
    if not contexts.get("regulatory_interactions"):
        return weights
    w = dict(weights)
    w["RP"] = w.get("RP", 0) + 0.05
    w["LOC"] = w.get("LOC", 0) + 0.03
    return clamp_and_renormalize(w)


def apply_methods_tweaks(weights: dict, contexts: dict) -> dict:
    tools = contexts.get("methods_tools", [])
    if not tools:
        return weights
    w = dict(weights)
    technical = {"gis", "statistics_modeling", "lab_methods"}
    field_tools = {"field_instrumentation"}
    if any(t in technical for t in tools):
        w["KR"] = w.get("KR", 0) + 0.05
    if any(t in field_tools for t in tools):
        w["FAP"] = w.get("FAP", 0) + 0.05
    return clamp_and_renormalize(w)


# ─── Section 4: Intensity ───

def duration_factor(years: float) -> float:
    if years is None or years <= 0:
        return 0.35
    for threshold, factor in DURATION_BRACKETS:
        if years <= threshold:
            return factor
    return DURATION_MAX


def verification_factor(status: str) -> float:
    return VERIFICATION_FACTORS.get(status, 0.50)


def role_intensity_factor(role: str) -> float:
    return ROLE_INTENSITY_FACTORS.get(role, 0.70)


def specificity_factor(contexts: dict, record: dict) -> float:
    score = 0.75
    if record.get("species_or_system"):
        score += 0.05
    if record.get("project_type"):
        score += 0.05
    if contexts.get("methods_tools"):
        score += 0.05
    if contexts.get("regulatory_interactions"):
        score += 0.05
    return min(1.10, max(0.75, score))


def compute_intensity(record: dict, contexts: dict) -> float:
    years = record.get("years_applied", 1) or 1
    v_status = record.get("verification_status", "pending")
    role = record.get("role_level", "participant")
    intensity = (
        duration_factor(years)
        * verification_factor(v_status)
        * role_intensity_factor(role)
        * specificity_factor(contexts, record)
    )
    return round(min(1.30, max(0.10, intensity)), 4)


# ─── Section 3.7: Time ───

def resolve_time(record: dict) -> dict:
    start = record.get("start_year")
    end = record.get("end_year")
    years_applied = record.get("years_applied")

    if start and end:
        return {"start_year": int(start), "end_year": int(end)}
    if years_applied:
        y = int(years_applied)
        e = int(end) if end else CURRENT_YEAR
        return {"start_year": e - y + 1, "end_year": e}
    return {"start_year": CURRENT_YEAR, "end_year": CURRENT_YEAR}


# ─── Section 5: Multi-Unit Split ───

def detect_split_triggers(record: dict, contexts: dict) -> list:
    slices = []
    project_types = contexts.get("project_types", [])
    species_modes = contexts.get("species_interaction_modes", [])
    activity = (record.get("activity_type") or "").lower()
    has_field = any(w in activity for w in ["survey", "monitor", "field"])
    has_reg = any(w in activity for w in ["ceqa", "nepa", "permit", "compliance"])

    if len(project_types) >= 2:
        for pt in project_types:
            ctx_slice = dict(contexts)
            ctx_slice["project_types"] = [pt]
            slices.append(ctx_slice)
    elif len(species_modes) >= 2:
        for sm in species_modes:
            ctx_slice = dict(contexts)
            ctx_slice["species_interaction_modes"] = [sm]
            slices.append(ctx_slice)
    elif has_field and has_reg:
        field_ctx = dict(contexts)
        field_ctx["_activity_override"] = "field survey"
        reg_ctx = dict(contexts)
        reg_ctx["_activity_override"] = "ceqa"
        slices = [field_ctx, reg_ctx]
    return slices


def _build_unit(record, weights, intensity, contexts, idx):
    ev_id = record.get("id", record.get("evidence_id", "unknown"))
    time = resolve_time(record)
    text = record.get("activity_type", "")
    if record.get("species_or_system"):
        text += f" — {record['species_or_system']}"
    clean_ctx = {k: v for k, v in contexts.items()
                 if k != "_activity_override" and v}
    return {
        "id": f"ev_{ev_id}_{idx}",
        "source": "phase1_db",
        "source_ref": {
            "evidence_id": str(ev_id),
            "credential_id": record.get("credential_id"),
        },
        "time": time,
        "text": text,
        "domain_weights": weights,
        "intensity_weight": intensity,
        "contexts": clean_ctx,
        "translation_version": TRANSLATION_VERSION,
    }


def maybe_split(record, weights, intensity, contexts):
    slices = detect_split_triggers(record, contexts)
    if not slices:
        return [_build_unit(record, weights, intensity, contexts, 0)]

    n = len(slices)
    split_intensity = round(intensity / n, 4)
    units = []
    for idx, ctx_slice in enumerate(slices):
        w = dict(weights)
        override = ctx_slice.pop("_activity_override", None)
        if override:
            w = apply_activity_modifier(w, override)
        w = apply_species_mode_tweaks(w, ctx_slice)
        w = apply_regulatory_tweaks(w, ctx_slice)
        w = apply_methods_tweaks(w, ctx_slice)
        units.append(_build_unit(record, w, split_intensity, ctx_slice, idx))
    return units


# ─── Main Entry Points ───

def translate_record(record: dict) -> list:
    """Translate one Phase-1 experience_evidence record into evidence_units."""
    v_status = record.get("verification_status", "pending")
    if verification_factor(v_status) == 0.0:
        return []

    domain = record.get("domain_category", "field_experience")
    activity = record.get("activity_type", "")
    role = record.get("role_level", "participant")

    w = base_vector(domain)
    w = apply_activity_modifier(w, activity)
    w = apply_role_modifier(w, role)

    combined_text = " ".join(filter(None, [
        activity,
        record.get("species_or_system", ""),
        record.get("habitat_context", ""),
        record.get("project_type", ""),
    ]))
    contexts = match_contexts(combined_text)

    w = apply_species_mode_tweaks(w, contexts)
    w = apply_regulatory_tweaks(w, contexts)
    w = apply_methods_tweaks(w, contexts)

    intensity = compute_intensity(record, contexts)
    return maybe_split(record, w, intensity, contexts)


def translate_profile(records: list, profile_info: dict = None) -> dict:
    """Translate all evidence records for one biologist into a payload."""
    sorted_records = sorted(records, key=lambda r: str(r.get("id", "")))
    all_units = []
    for rec in sorted_records:
        all_units.extend(translate_record(rec))

    info = profile_info or {}
    return {
        "profile_version": "1.0",
        "biologist_id": info.get("registry_id", "UNKNOWN"),
        "display": {
            "name": info.get("full_name", ""),
            "descriptor": info.get("professional_title", ""),
            "profile_derived_date": str(datetime.date.today()),
            "source_documents": ["phase1_db"],
        },
        "evidence_units": all_units,
        "translation_version": TRANSLATION_VERSION,
    }
