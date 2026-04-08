"""
BioCred Pipeline — Unit tests for Classifier and Context Matcher.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier import (
    load_keyword_ontology, count_axis_matches, normalize_weights,
    classify_engagement, classify_evidence_unit, validate_evidence_unit,
    expand_to_yearly, merge_yearly_vectors, extract_tags, build_profile,
    build_payload,
)
from context_matcher import match_contexts, calculate_intensity, CONTEXT_DETECTION

PASS = 0
FAIL = 0


def test(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


print("=" * 60)
print("BioCred — Classifier & Context Matcher Unit Tests")
print("=" * 60)

ontology = load_keyword_ontology()

# ── Ontology loading ──
print("\n[Classifier] Ontology loading")
test("Returns dict with 5 axes", len(ontology) == 5 and isinstance(ontology, dict))
test("Each axis has at least 10 keywords",
     all(len(kw) >= 10 for kw in ontology.values()))
all_kws = []
for kws in ontology.values():
    all_kws.extend(k.lower() for k in kws)
test("No keyword appears in multiple axes", len(all_kws) == len(set(all_kws)))

# ── count_axis_matches ──
print("\n[Classifier] count_axis_matches")
gov_text = "conducted regulatory compliance permit review"
gov_counts = count_axis_matches(gov_text, ontology)
test("GOV dominant for regulatory/permit text",
     gov_counts.get("RP", 0) >= max(gov_counts.values()))
kg_text = "research publish statistical analysis methodology"
kg_counts = count_axis_matches(kg_text, ontology)
test("KG dominant for research/statistical text",
     kg_counts.get("KR", 0) >= max(kg_counts.values()))
oc_text = "lead manage supervise coordinate team"
oc_counts = count_axis_matches(oc_text, ontology)
test("OC dominant for lead/manage text",
     oc_counts.get("LOC", 0) >= max(oc_counts.values()))
br_text = "species identification handling capture translocation"
br_counts = count_axis_matches(br_text, ontology)
test("BR dominant for species/handling text",
     br_counts.get("SHS", 0) >= max(br_counts.values()))
abp_text = "fieldwork survey monitoring habitat assessment wetland"
abp_counts = count_axis_matches(abp_text, ontology)
test("ABP dominant for fieldwork/survey text",
     abp_counts.get("FAP", 0) >= max(abp_counts.values()))
test("Empty string → all zeros", sum(count_axis_matches("", ontology).values()) == 0)
hcp = count_axis_matches("habitat conservation plan", ontology)
test("Multi-word 'habitat conservation plan' counted", hcp.get("RP", 0) > 0)
env_rev = count_axis_matches("environmental review", ontology)
test("'environmental review' counted correctly", env_rev.get("RP", 0) > 0)

# ── normalize_weights ──
print("\n[Classifier] normalize_weights")
zeros = {"KR": 0, "LOC": 0, "SHS": 0, "FAP": 0, "RP": 0}
nz = normalize_weights(zeros)
test("All zeros → equal distribution (0.2 each)", all(v == 0.2 for v in nz.values()))
single = {"KR": 5, "LOC": 0, "SHS": 0, "FAP": 0, "RP": 0}
ns = normalize_weights(single)
test("Single axis non-zero → that axis = 1.0", ns.get("KR") == 1.0)
mixed = {"KR": 1, "LOC": 2, "SHS": 1, "FAP": 1, "RP": 1}
nm = normalize_weights(mixed)
test("Sum always equals 1.0 (±0.01)", abs(sum(nm.values()) - 1.0) <= 0.01)

# ── classify_engagement ──
print("\n[Classifier] classify_engagement")
eng = {"role": "Biologist", "organization": "CDFW", "description": "field surveys",
       "start_year": 2018, "end_year": 2020}
cl = classify_engagement(eng, ontology)
test("Returns dict with role, domain_weights, axis_counts, total_matches",
     all(k in cl for k in ["role", "domain_weights", "axis_counts", "total_matches"]))
test("Weights sum to 1.0", abs(sum(cl["domain_weights"].values()) - 1.0) <= 0.01)
test("All 5 axes present in weights", len(cl["domain_weights"]) == 5)

# ── classify_evidence_unit ──
print("\n[Classifier] classify_evidence_unit")
unit = {"id": "u1", "source": "cv", "time": {"start_year": 2019, "end_year": 2020},
        "text": "Conducted wetland surveys"}
ceu = classify_evidence_unit(unit, ontology)
test("Returns dict with domain_weights, intensity_weight, contexts",
     all(k in ceu for k in ["domain_weights", "intensity_weight", "contexts"]))
test("Weights sum to 1.0", abs(sum(ceu["domain_weights"].values()) - 1.0) <= 0.01)
test("intensity_weight is float", isinstance(ceu["intensity_weight"], (int, float)))

# ── validate_evidence_unit ──
print("\n[Classifier] validate_evidence_unit")
valid = {"id": "x", "source": "cv", "time": {}, "text": "foo"}
test("Valid unit returns True", validate_evidence_unit(valid))
test("Missing 'id' returns False",
     not validate_evidence_unit({"source": "cv", "time": {}, "text": "x"}))
test("Missing 'text' returns False",
     not validate_evidence_unit({"id": "x", "source": "cv", "time": {}}))
test("Empty dict returns False", not validate_evidence_unit({}))

# ── expand_to_yearly ──
print("\n[Classifier] expand_to_yearly")
cl_eng = {"start_year": 2018, "end_year": 2020, "role": "Bio",
          "domain_weights": {"KR": 0.2, "LOC": 0.2, "SHS": 0.2, "FAP": 0.2, "RP": 0.2}}
yearly = expand_to_yearly(cl_eng)
test("2018-2020 engagement → 3 yearly entries", len(yearly) == 3)
test("Each entry has year and 5-element vector",
     all("year" in e and len(e.get("vector", [])) == 5 for e in yearly))
test("Vectors sum to 1.0", all(abs(sum(e["vector"]) - 1.0) <= 0.01 for e in yearly))
test("Missing years → empty list", expand_to_yearly({"role": "x"}) == [])

# ── merge_yearly_vectors ──
print("\n[Classifier] merge_yearly_vectors")
overlap = [{"year": 2020, "vector": [0.2] * 5}, {"year": 2020, "vector": [0.2] * 5}]
merged = merge_yearly_vectors(overlap)
test("Two overlapping 2020 entries → merged and normalized",
     len(merged) == 1 and abs(sum(merged[0]["vector"]) - 1.0) <= 0.01)
single_entry = [{"year": 2020, "vector": [0.2] * 5}]
test("Single entry → unchanged", merge_yearly_vectors(single_entry) == single_entry)
test("Empty list → empty result", merge_yearly_vectors([]) == [])

# ── build_payload ──
print("\n[Classifier] build_payload")
units = [{"id": "u1", "source": "cv", "time": {"start_year": 2019, "end_year": 2020},
          "text": "Wetland delineation"}]
payload = build_payload(units, "Jane Doe")
test("Returns profile_version 1.0", payload.get("profile_version") == "1.0")
test("Has biologist_id", "biologist_id" in payload)
test("Has evidence_units list", "evidence_units" in payload and isinstance(payload["evidence_units"], list))
eu = payload["evidence_units"][0]
test("evidence_units have domain_weights, intensity_weight, contexts",
     all(k in eu for k in ["domain_weights", "intensity_weight", "contexts"]))

# ── Context: Regulatory detection ──
print("\n[Context] Regulatory detection")
r1 = match_contexts("CEQA environmental review")
test("CEQA environmental review → environmental_review_coordination",
     "environmental_review_coordination" in r1.get("regulatory_interactions", []))
r2 = match_contexts("coordinated with CDFW and USFWS")
test("CDFW USFWS → wildlife_agency_coordination",
     "wildlife_agency_coordination" in r2.get("regulatory_interactions", []))
r3 = match_contexts("section 7 formal consultation")
test("section 7 formal consultation → interagency_consultation",
     "interagency_consultation" in r3.get("regulatory_interactions", []))
r4 = match_contexts("clean water act compliance")
test("clean water act → water_boards_coordination",
     "water_boards_coordination" in r4.get("regulatory_interactions", []))
r5 = match_contexts("army corps section 404 permit")
test("army corps section 404 → flood_control_coordination",
     "flood_control_coordination" in r5.get("regulatory_interactions", []))

# ── Context: Working environments ──
print("\n[Context] Working environments")
w1 = match_contexts("wetland delineation and riparian survey")
test("wetland riparian → hydrologic_systems",
     "hydrologic_systems" in w1.get("working_environments", []))
w2 = match_contexts("desert chaparral habitat")
test("desert chaparral → terrestrial_natural_systems",
     "terrestrial_natural_systems" in w2.get("working_environments", []))
w3 = match_contexts("coastal estuary monitoring")
test("coastal estuary → coastal_marine_systems",
     "coastal_marine_systems" in w3.get("working_environments", []))
w4 = match_contexts("highway construction site")
test("highway construction → managed_engineered_landscapes",
     "managed_engineered_landscapes" in w4.get("working_environments", []))

# ── Context: Species interaction modes ──
print("\n[Context] Species interaction modes")
s1 = match_contexts("captured and handled listed species")
test("capture AND handling detected",
     "capture" in s1.get("species_interaction_modes", []) and
     "handling" in s1.get("species_interaction_modes", []))
s2 = match_contexts("translocation of desert tortoise")
test("translocation → relocation", "relocation" in s2.get("species_interaction_modes", []))
s3 = match_contexts("pre-construction clearance surveys")
test("clearance → oversight", "oversight" in s3.get("species_interaction_modes", []))
s4 = match_contexts("point count bird survey")
test("point count → survey", "survey" in s4.get("species_interaction_modes", []))
s5 = match_contexts("long-term population monitoring")
test("population monitoring → monitoring", "monitoring" in s5.get("species_interaction_modes", []))

# ── Context: Project types ──
print("\n[Context] Project types")
p1 = match_contexts("habitat restoration revegetation")
test("restoration revegetation → restoration_implementation",
     "restoration_implementation" in p1.get("project_types", []))
p2 = match_contexts("mitigation compliance monitoring")
test("mitigation compliance → mitigation_compliance",
     "mitigation_compliance" in p2.get("project_types", []))
p3 = match_contexts("thesis research grant NSF")
test("thesis research grant NSF → research_program",
     "research_program" in p3.get("project_types", []))

# ── Context: Methods/tools ──
print("\n[Context] Methods/tools")
m1 = match_contexts("ArcGIS spatial analysis")
test("ArcGIS → gis", "gis" in m1.get("methods_tools", []))
m2 = match_contexts("R programming statistical modeling")
test("R statistical → statistics_modeling", "statistics_modeling" in m2.get("methods_tools", []))
m3 = match_contexts("laboratory genetics DNA PCR")
test("lab genetics DNA → lab_methods", "lab_methods" in m3.get("methods_tools", []))
m4 = match_contexts("camera trap telemetry")
test("camera trap telemetry → field_instrumentation",
     "field_instrumentation" in m4.get("methods_tools", []))
m5 = match_contexts("drafted technical report biological assessment")
test("drafted technical report → report_writing", "report_writing" in m5.get("methods_tools", []))

# ── Context: Edge cases ──
print("\n[Context] Edge cases")
test("Empty string → empty dict", match_contexts("") == {})
test("General office duties filing → empty dict",
     match_contexts("general office duties filing") == {})
multi = match_contexts("CEQA wetland survey restoration ArcGIS")
test("Text with multiple categories → all detected",
     len(multi) >= 2)
r_a, r_b = match_contexts("section 7 consultation"), match_contexts("section 7 consultation")
test("Same text twice → deterministic", r_a == r_b)

# ── Intensity calculator ──
print("\n[Context] Intensity calculator")
i1 = calculate_intensity(2000, 2026, "lead biologist", False)
test("Long career + lead → high (>= 1.0)", i1 >= 1.0)
i2 = calculate_intensity(2024, 2025, "assistant", False)
test("Short career + assistant → lower", i2 < i1)
i3 = calculate_intensity(2010, 2020, "biologist", True)
test("Credential → reduced", i3 <= 1.0)
test("None years → 0.5", calculate_intensity(None, None, "", False) == 0.5)
i4a, i4b = calculate_intensity(2015, 2020, "lead", False), calculate_intensity(2015, 2020, "lead", False)
test("Deterministic: same input → same output", i4a == i4b)
i5 = calculate_intensity(2010, 2020, "supervisor", False)
test("Supervisor triggers bonus", i5 >= 0.9)
i6 = calculate_intensity(2010, 2020, "chief scientist", False)
test("Chief triggers leader bonus", i6 >= 0.9)
test("Capped at 1.5 max", calculate_intensity(1990, 2030, "chief director", False) <= 1.5)

# ── CONTEXT_DETECTION export ──
print("\n[Context] CONTEXT_DETECTION")
test("CONTEXT_DETECTION is dict", isinstance(CONTEXT_DETECTION, dict))
test("CONTEXT_DETECTION has regulatory_interactions", "regulatory_interactions" in CONTEXT_DETECTION)

# ── extract_tags ──
print("\n[Classifier] extract_tags")
classified = [{"axis_counts": {"KR": 5, "LOC": 1, "SHS": 0, "FAP": 0, "RP": 0}},
              {"axis_counts": {"KR": 0, "LOC": 0, "SHS": 3, "FAP": 1, "RP": 0}}]
tags = extract_tags(classified)
test("extract_tags returns list", isinstance(tags, list))
test("extract_tags includes dominant axes", "KR" in tags and "SHS" in tags)

# ── Results ──
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print("=" * 60)

sys.exit(1 if FAIL else 0)
