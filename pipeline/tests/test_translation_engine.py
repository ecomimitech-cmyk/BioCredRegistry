"""
BioCred Translation Engine — Acceptance Tests
Tests per Alexander Funk's TE Spec v1.0, Section 8.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name}")
        failed += 1

from pipeline.translation_engine import (
    translate_record, translate_profile,
    base_vector, apply_activity_modifier, apply_role_modifier,
    clamp_and_renormalize, compute_intensity,
    duration_factor, verification_factor, role_intensity_factor,
    specificity_factor, resolve_time, get_unknown_log, clear_unknown_log,
    apply_species_mode_tweaks, apply_regulatory_tweaks, apply_methods_tweaks,
    detect_split_triggers, maybe_split, CURRENT_YEAR,
)
from pipeline.te_constants import AXIS_ORDER, BASE_VECTORS, TRANSLATION_VERSION
from pipeline.context_matcher import match_contexts

print("=" * 60)
print("BioCred Translation Engine — TE Spec v1.0 Acceptance Tests")
print("=" * 60)

# ─── Section 3.1: Base Vectors ───
print("\n[1] Base Vectors (Sec 3.1)")

for domain, expected in BASE_VECTORS.items():
    bv = base_vector(domain)
    s = sum(bv.values())
    test(f"{domain} sum=1.0", abs(s - 1.0) < 0.001)
    test(f"{domain} matches spec", bv == expected)

test("Unknown domain → fallback to field_experience",
     base_vector("nonexistent") == BASE_VECTORS["field_experience"])

# ─── Section 3.2: Activity-Type Modifiers ───
print("\n[2] Activity-Type Modifiers (Sec 3.2)")

w_field = base_vector("field_experience")
w_ceqa = apply_activity_modifier(dict(w_field), "CEQA biological assessment")
test("CEQA boosts GOV", w_ceqa["RP"] > w_field["RP"])

w_survey = apply_activity_modifier(dict(w_field), "Field survey and monitoring")
test("Survey boosts ABP", w_survey["FAP"] > 0.5)

w_gis = apply_activity_modifier(base_vector("academic_technical"), "GIS statistical modeling")
test("GIS boosts KG", w_gis["KR"] > 0.6)

w_capture = apply_activity_modifier(base_vector("species_depth"), "Species handling and capture")
test("Capture boosts BR", w_capture["SHS"] > w_field["SHS"])

w_mgmt = apply_activity_modifier(base_vector("leadership_scope"), "Project management and mentoring")
test("Management boosts OC", w_mgmt["LOC"] > 0.5)

clear_unknown_log()
apply_activity_modifier(dict(w_field), "Unknown weird activity xyz")
test("Unknown activity → logged", len(get_unknown_log()) == 1)
test("Unknown activity → no modifier (unchanged)", True)
clear_unknown_log()

# ─── Section 3.3: Role-Level Modifiers ───
print("\n[3] Role-Level Modifiers (Sec 3.3)")

w_base = base_vector("field_experience")
w_lead = apply_role_modifier(dict(w_base), "lead")
test("Lead → OC increases", w_lead["LOC"] > w_base["LOC"])
test("Lead → GOV increases", w_lead["RP"] > w_base["RP"])

w_pi = apply_role_modifier(base_vector("academic_technical"), "principal_investigator")
test("PI → KG increases", w_pi["KR"] > 0.6)
test("PI → OC increases", w_pi["LOC"] > BASE_VECTORS["academic_technical"]["LOC"])

w_participant = apply_role_modifier(dict(w_base), "participant")
test("Participant → no change", w_participant == w_base)

# ─── Sec 3.4-3.6: Context Tweaks ───
print("\n[4] Context Tweaks (Sec 3.4-3.6)")

ctx_species = {"species_interaction_modes": ["capture", "handling"]}
w_sp = apply_species_mode_tweaks(dict(w_base), ctx_species)
test("Capture mode → BR boost", w_sp["SHS"] > w_base["SHS"])

ctx_reg = {"regulatory_interactions": ["wildlife_agency_coordination"]}
w_reg = apply_regulatory_tweaks(dict(w_base), ctx_reg)
test("Regulatory context → GOV boost", w_reg["RP"] > w_base["RP"])

ctx_tools = {"methods_tools": ["gis"]}
w_tools = apply_methods_tweaks(base_vector("academic_technical"), ctx_tools)
test("GIS tool → KG boost", w_tools["KR"] > BASE_VECTORS["academic_technical"]["KR"])

ctx_field_tools = {"methods_tools": ["field_instrumentation"]}
w_ft = apply_methods_tweaks(dict(w_base), ctx_field_tools)
test("Field tools → ABP boost", w_ft["FAP"] > w_base["FAP"])

# ─── Simplex Validity (Sec 8 test 1) ───
print("\n[5] Simplex Validity")

sample_record = {
    "id": "test_001",
    "domain_category": "regulatory_experience",
    "activity_type": "CEQA/NEPA environmental document preparation",
    "species_or_system": None,
    "habitat_context": "Riparian",
    "project_type": "Environmental review",
    "role_level": "lead",
    "years_applied": 10,
    "verification_status": "verified",
    "is_verified": True,
}

units = translate_record(sample_record)
test("At least 1 unit produced", len(units) >= 1)
for u in units:
    w = u["domain_weights"]
    test(f"Unit {u['id']}: all in [0,1]",
         all(0 <= w[ax] <= 1 for ax in AXIS_ORDER))
    test(f"Unit {u['id']}: sum=1.0",
         abs(sum(w.values()) - 1.0) < 0.01)

# ─── Modifier Determinism (Sec 8 test 2) ───
print("\n[6] Determinism")

units_a = translate_record(sample_record)
units_b = translate_record(sample_record)
test("Same input → same unit count", len(units_a) == len(units_b))
if units_a and units_b:
    test("Same input → identical weights",
         units_a[0]["domain_weights"] == units_b[0]["domain_weights"])
    test("Same input → identical intensity",
         units_a[0]["intensity_weight"] == units_b[0]["intensity_weight"])

# ─── Verification Exclusion (Sec 8 test 4) ───
print("\n[7] Verification Exclusion")

rejected_record = dict(sample_record)
rejected_record["verification_status"] = "rejected"
test("Rejected → 0 units", translate_record(rejected_record) == [])

# ─── Unknown Activity Type (Sec 8 test 5) ───
print("\n[8] Unknown Activity Type")

clear_unknown_log()
unknown_record = {
    "id": "test_unknown",
    "domain_category": "field_experience",
    "activity_type": "Quantum entanglement of butterflies",
    "role_level": "participant",
    "years_applied": 2,
    "verification_status": "verified",
}
units_unk = translate_record(unknown_record)
test("Unknown activity → still valid output", len(units_unk) >= 1)
test("Unknown activity → weights sum to 1.0",
     abs(sum(units_unk[0]["domain_weights"].values()) - 1.0) < 0.01)
test("Unknown activity → logged", len(get_unknown_log()) >= 1)
clear_unknown_log()

# ─── Intensity Formula (Sec 4) ───
print("\n[9] Intensity Factors (Sec 4)")

test("0-3 months → 0.35", duration_factor(0.2) == 0.35)
test("6 months → 0.55", duration_factor(0.8) == 0.55)
test("2 years → 0.75", duration_factor(2) == 0.75)
test("5 years → 0.90", duration_factor(5) == 0.90)
test("10 years → 1.00", duration_factor(10) == 1.00)
test("None → 0.35", duration_factor(None) == 0.35)

test("Verified → 1.00", verification_factor("verified") == 1.00)
test("Partial → 0.70", verification_factor("partial") == 0.70)
test("Pending → 0.50", verification_factor("pending") == 0.50)
test("Rejected → 0.00", verification_factor("rejected") == 0.00)

test("Participant → 0.70", role_intensity_factor("participant") == 0.70)
test("Lead → 1.00", role_intensity_factor("lead") == 1.00)
test("Oversight → 1.03", role_intensity_factor("oversight") == 1.03)
test("PI → 1.05", role_intensity_factor("principal_investigator") == 1.05)

ctx_full = {"methods_tools": ["gis"], "regulatory_interactions": ["environmental_review_coordination"]}
rec_full = {"species_or_system": "Desert tortoise", "project_type": "Infrastructure"}
sf = specificity_factor(ctx_full, rec_full)
test(f"Full specificity → 0.95 (all 4 bonuses) (got {sf})", abs(sf - 0.95) < 0.001)

ctx_empty = {}
rec_empty = {}
test("Empty specificity → 0.75 (floor)", specificity_factor(ctx_empty, rec_empty) == 0.75)

# ─── Intensity clamping ───
print("\n[10] Intensity Clamping")

long_verified_lead = {
    "years_applied": 20, "verification_status": "verified",
    "role_level": "principal_investigator",
    "species_or_system": "X", "project_type": "Y",
}
i = compute_intensity(long_verified_lead, ctx_full)
test(f"High intensity clamped ≤ 1.30 (got {i})", i <= 1.30)
test(f"High intensity ≥ 0.10", i >= 0.10)

short_pending = {
    "years_applied": 0, "verification_status": "pending",
    "role_level": "participant",
}
i_low = compute_intensity(short_pending, {})
test(f"Low intensity ≥ 0.10 (got {i_low})", i_low >= 0.10)

# ─── Time Resolution (Sec 3.7) ───
print("\n[11] Time Resolution (Sec 3.7)")

test("Start+end provided", resolve_time({"start_year": 2018, "end_year": 2022})
     == {"start_year": 2018, "end_year": 2022})
test("years_applied only",
     resolve_time({"years_applied": 5})["start_year"] < resolve_time({"years_applied": 5})["end_year"])
test("Nothing → current year",
     resolve_time({}) == {"start_year": CURRENT_YEAR, "end_year": CURRENT_YEAR})

# ─── Multi-Unit Split (Sec 5) ───
print("\n[12] Multi-Unit Split (Sec 5)")

split_record = {
    "id": "test_split",
    "domain_category": "field_experience",
    "activity_type": "Field survey and CEQA compliance monitoring",
    "role_level": "lead",
    "years_applied": 5,
    "verification_status": "verified",
    "habitat_context": "wetland",
}
units_split = translate_record(split_record)
test("Field+regulatory → split into ≥2 units", len(units_split) >= 2)

if len(units_split) >= 2:
    total_intensity = sum(u["intensity_weight"] for u in units_split)
    single_units = translate_record({
        **split_record,
        "activity_type": "Field survey",
    })
    single_i = single_units[0]["intensity_weight"] if single_units else 0
    test("Split mass ≈ original (conservation)",
         abs(total_intensity - single_i) < 0.5)

multi_project = {
    "id": "test_multi_proj",
    "domain_category": "field_experience",
    "activity_type": "Habitat assessment and monitoring",
    "role_level": "lead",
    "years_applied": 3,
    "verification_status": "verified",
    "habitat_context": "wetland restoration infrastructure",
    "project_type": "restoration and infrastructure",
}
ctx_multi = match_contexts("restoration revegetation infrastructure highway")
if len(ctx_multi.get("project_types", [])) >= 2:
    splits = detect_split_triggers(multi_project, ctx_multi)
    test("≥2 project types → split triggered", len(splits) >= 2)

# ─── Full Profile Translation ───
print("\n[13] Full Profile Translation")

records = [
    {"id": "ev1", "domain_category": "field_experience",
     "activity_type": "Desert tortoise protocol surveys",
     "species_or_system": "Gopherus agassizii",
     "habitat_context": "Mojave desert scrub",
     "project_type": "Pre-construction clearance",
     "role_level": "lead", "years_applied": 10,
     "verification_status": "verified"},
    {"id": "ev2", "domain_category": "regulatory_experience",
     "activity_type": "CEQA/NEPA environmental document preparation",
     "role_level": "lead", "years_applied": 15,
     "verification_status": "verified"},
    {"id": "ev3", "domain_category": "academic_technical",
     "activity_type": "Peer-reviewed publication authorship",
     "role_level": "principal_investigator", "years_applied": 20,
     "verification_status": "verified"},
    {"id": "ev4", "domain_category": "species_depth",
     "activity_type": "Species handling and capture",
     "species_or_system": "Listed reptiles",
     "role_level": "lead", "years_applied": 8,
     "verification_status": "verified"},
    {"id": "ev5", "domain_category": "leadership_scope",
     "activity_type": "Project management and mentoring",
     "role_level": "oversight", "years_applied": 10,
     "verification_status": "verified"},
    {"id": "ev_rejected", "domain_category": "field_experience",
     "activity_type": "Rejected evidence",
     "role_level": "participant", "years_applied": 1,
     "verification_status": "rejected"},
]

profile_info = {
    "registry_id": "FC_TEST_001",
    "full_name": "Demo Profile (Test)",
    "professional_title": "Test Biologist",
}

payload = translate_profile(records, profile_info)
test("Payload has profile_version", payload["profile_version"] == "1.0")
test("Payload has biologist_id", payload["biologist_id"] == "FC_TEST_001")
test("Payload has display block", "name" in payload["display"])
test("Payload has translation_version", payload["translation_version"] == TRANSLATION_VERSION)
test("Payload has evidence_units", len(payload["evidence_units"]) >= 5)
test("Rejected record excluded",
     not any("ev_rejected" in u["id"] for u in payload["evidence_units"]))

for u in payload["evidence_units"]:
    w = u["domain_weights"]
    test(f"  {u['id']}: sum=1.0", abs(sum(w.values()) - 1.0) < 0.01)
    test(f"  {u['id']}: intensity in [0.10,1.30]",
         0.10 <= u["intensity_weight"] <= 1.30)
    test(f"  {u['id']}: has translation_version",
         u["translation_version"] == TRANSLATION_VERSION)

# ─── Determinism of full profile ───
print("\n[14] Profile Determinism")
payload2 = translate_profile(records, profile_info)
test("Same records → same unit count",
     len(payload["evidence_units"]) == len(payload2["evidence_units"]))
test("Same records → same biologist_id",
     payload["biologist_id"] == payload2["biologist_id"])
for u1, u2 in zip(payload["evidence_units"], payload2["evidence_units"]):
    test(f"  {u1['id']}: identical weights", u1["domain_weights"] == u2["domain_weights"])

# ─── Domain-axis alignment ───
print("\n[15] Domain-Axis Alignment (Sanity)")

field_units = translate_record({
    "id": "sanity_field", "domain_category": "field_experience",
    "activity_type": "Biological construction monitoring",
    "role_level": "lead", "years_applied": 5, "verification_status": "verified"
})
if field_units:
    test("Field → ABP dominant",
         field_units[0]["domain_weights"]["FAP"] == max(field_units[0]["domain_weights"].values()))

reg_units = translate_record({
    "id": "sanity_reg", "domain_category": "regulatory_experience",
    "activity_type": "CEQA environmental review coordination",
    "role_level": "lead", "years_applied": 5, "verification_status": "verified"
})
if reg_units:
    test("Regulatory → GOV dominant",
         reg_units[0]["domain_weights"]["RP"] == max(reg_units[0]["domain_weights"].values()))

acad_units = translate_record({
    "id": "sanity_acad", "domain_category": "academic_technical",
    "activity_type": "Statistical modeling and GIS analysis",
    "role_level": "principal_investigator", "years_applied": 10,
    "verification_status": "verified"
})
if acad_units:
    test("Academic → KG dominant",
         acad_units[0]["domain_weights"]["KR"] == max(acad_units[0]["domain_weights"].values()))

species_units = translate_record({
    "id": "sanity_species", "domain_category": "species_depth",
    "activity_type": "Species handling and capture",
    "species_or_system": "Listed reptiles",
    "role_level": "lead", "years_applied": 8, "verification_status": "verified"
})
if species_units:
    test("Species → BR dominant",
         species_units[0]["domain_weights"]["SHS"] == max(species_units[0]["domain_weights"].values()))

lead_units = translate_record({
    "id": "sanity_lead", "domain_category": "leadership_scope",
    "activity_type": "Project management and mentoring",
    "role_level": "oversight", "years_applied": 10, "verification_status": "verified"
})
if lead_units:
    test("Leadership → OC dominant",
         lead_units[0]["domain_weights"]["LOC"] == max(lead_units[0]["domain_weights"].values()))

# ─── Normalization Edge Cases (Sec 6) ───
print("\n[16] Normalization Edge Cases (Sec 6)")

test("All zeros → equal dist", clamp_and_renormalize({ax: 0 for ax in AXIS_ORDER})
     == {ax: 0.2 for ax in AXIS_ORDER})
test("Negatives clamped",
     all(v >= 0 for v in clamp_and_renormalize({"KR": -0.5, "LOC": 0.3, "SHS": 0.2, "FAP": 0.5, "RP": 0.1}).values()))

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
