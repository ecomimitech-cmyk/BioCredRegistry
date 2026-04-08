"""
BioCred Pipeline — End-to-End Test
Runs the full pipeline: CV → parse → engagements → classify → map
Validates determinism, vector sums, and coordinate invariants.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cv_parser import parse_cv
from engagement_extractor import (
    extract_engagements, extract_credentials, extract_evidence_units
)
from classifier import (
    classify_engagement, classify_evidence_unit, expand_to_yearly,
    merge_yearly_vectors, build_profile, build_payload,
    load_keyword_ontology
)
from pentagon_mapper import (
    get_pentagon_vertices, map_simplex_to_xy,
    map_trajectory, verify_invariants
)
from context_matcher import match_contexts, calculate_intensity

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


SAMPLE_CV = str(Path(__file__).parent / "sample_cv.txt")

print("=" * 60)
print("BioCred Pipeline — End-to-End Tests")
print("=" * 60)

# ── Step 1: Config files exist ──
print("\n[1] Config Files")
config_dir = Path(__file__).parent.parent / "config"
for name in ["axis_ontology_v1.json", "context_ontology_v1.json",
             "render_config_registry_v1.json", "keyword_ontology_v1.json"]:
    test(f"{name} exists", (config_dir / name).exists())

axis_data = json.loads(
    (config_dir / "axis_ontology_v1.json").read_text()
)
test("5 axes defined",
     len(axis_data["axes"]) == 5)
test("Axis IDs correct",
     [a["id"] for a in axis_data["axes"]] == ["KR","LOC","SHS","FAP","RP"])

# ── Step 2: CV Parser ──
print("\n[2] CV Parser")
parsed = parse_cv(SAMPLE_CV)
test("Parse returns dict", isinstance(parsed, dict))
test("Has sections", "sections" in parsed)
test("Found employment section",
     "employment" in parsed["sections"])
test("Found education section",
     "education" in parsed["sections"])
test("Found certifications",
     "certifications" in parsed["sections"])
test("Found publications",
     "publications" in parsed["sections"])
test("Found skills",
     "skills" in parsed["sections"])
test("Raw text not empty",
     len(parsed.get("raw_text", "")) > 100)

# ── Step 3: Engagement Extractor ──
print("\n[3] Engagement Extractor")
engagements = extract_engagements(parsed)
test("Engagements extracted",
     len(engagements) > 0)
test("At least 2 engagements",
     len(engagements) >= 2)

if engagements:
    first = engagements[0]
    test("Has role field", "role" in first)
    test("Has start_year", first.get("start_year") is not None)
    test("Has end_year", first.get("end_year") is not None)
    test("Has description", len(first.get("description", "")) > 0)

credentials = extract_credentials(parsed)
test("Credentials extracted",
     len(credentials) > 0)
test("At least 2 credentials",
     len(credentials) >= 2)

# ── Step 4: Classification Engine ──
print("\n[4] Classification Engine")
ontology = load_keyword_ontology()
test("Ontology has 5 axes", len(ontology) == 5)
test("Ontology axes match",
     set(ontology.keys()) == {"KR", "LOC", "SHS", "FAP", "RP"})

if engagements:
    classified = classify_engagement(engagements[0], ontology)
    test("Classification returns weights",
         "domain_weights" in classified)

    weights = classified["domain_weights"]
    weight_sum = sum(weights.values())
    test(f"Weights sum to 1.0 (got {weight_sum:.4f})",
         abs(weight_sum - 1.0) < 0.01)

    test("All 5 axes in weights",
         set(weights.keys()) == {"KR", "LOC", "SHS", "FAP", "RP"})

    test("Total matches > 0",
         classified["total_matches"] > 0)

# ── Step 5: Temporal Expansion ──
print("\n[5] Temporal Expansion")
if engagements:
    yearly = expand_to_yearly(classified)
    test("Yearly expansion produced entries",
         len(yearly) > 0)

    if yearly:
        test("Each entry has year",
             all("year" in y for y in yearly))
        test("Each entry has 5-element vector",
             all(len(y["vector"]) == 5 for y in yearly))
        test("Vectors sum to 1.0",
             all(abs(sum(y["vector"]) - 1.0) < 0.01 for y in yearly))

# ── Step 6: Determinism Test ──
print("\n[6] Determinism")
if engagements:
    c1 = classify_engagement(engagements[0], ontology)
    c2 = classify_engagement(engagements[0], ontology)
    test("Same input → same weights",
         c1["domain_weights"] == c2["domain_weights"])
    test("Same input → same counts",
         c1["axis_counts"] == c2["axis_counts"])

# ── Step 7: Full Profile Build ──
print("\n[7] Full Profile Build")
eng_data = {
    "source": "sample_cv.txt",
    "engagements": engagements,
    "credentials": credentials,
}
profile = build_profile(eng_data, "Jane M. Doe")
test("Profile has trajectory",
     len(profile["trajectory"]) > 0)
test("Profile has credentials",
     len(profile["credentials"]) > 0)
test("Profile version is 1.0",
     profile["profile_version"] == "1.0")

for t in profile["trajectory"]:
    s = round(sum(t["vector"]), 4)
    if abs(s - 1.0) > 0.01:
        test(f"Year {t['year']} vector sum = {s}", False)
        break
else:
    test("All trajectory vectors sum to 1.0", True)

# ── Step 8: Pentagon Mapper ──
print("\n[8] Pentagon Mapper")
vertices = get_pentagon_vertices()
test("5 vertices generated", len(vertices) == 5)

equal_weights = {"KR": 0.2, "LOC": 0.2, "SHS": 0.2, "FAP": 0.2, "RP": 0.2}
cx, cy = map_simplex_to_xy(equal_weights, vertices)
test(f"Equal weights → center ({cx:.3f}, {cy:.3f})",
     abs(cx) < 0.01 and abs(cy) < 0.01)

kr_heavy = {"KR": 0.8, "LOC": 0.05, "SHS": 0.05, "FAP": 0.05, "RP": 0.05}
kx, ky = map_simplex_to_xy(kr_heavy, vertices)
test("KR-heavy maps toward KR vertex",
     ky < -0.3)

mapped = map_trajectory(profile["trajectory"], vertices)
test("Trajectory mapped to 2D",
     len(mapped) == len(profile["trajectory"]))

invariants = verify_invariants(mapped, vertices)
test("All points inside pentagon bounds",
     invariants["all_inside"])

# ── Step 9: Evidence Unit Extraction ──
print("\n[9] Evidence Unit Extraction")
evidence_units = extract_evidence_units(parsed)
test("Evidence units extracted",
     len(evidence_units) > 0)
test("More units than engagements (bullet-level)",
     len(evidence_units) > len(engagements))
if evidence_units:
    first_unit = evidence_units[0]
    test("Unit has id", "id" in first_unit)
    test("Unit has text", len(first_unit.get("text", "")) > 0)
    test("Unit has time range", "time" in first_unit)
    test("Unit has parent_role", "parent_role" in first_unit)
    test("Unit has is_credential flag", "is_credential" in first_unit)

    cred_units = [u for u in evidence_units if u.get("is_credential")]
    test("Credential units included",
         len(cred_units) > 0)

# ── Step 10: Evidence Unit Classification ──
print("\n[10] Evidence Unit Classification")
if evidence_units:
    classified_unit = classify_evidence_unit(evidence_units[0], ontology)
    test("Classified unit has domain_weights",
         "domain_weights" in classified_unit)
    test("Classified unit has intensity_weight",
         "intensity_weight" in classified_unit)
    test("Classified unit has contexts",
         "contexts" in classified_unit)

    uw = classified_unit["domain_weights"]
    unit_sum = sum(uw.values())
    test(f"Unit weights sum to 1.0 (got {unit_sum:.4f})",
         abs(unit_sum - 1.0) < 0.01)
    test("All 5 axes in unit weights",
         set(uw.keys()) == {"KR", "LOC", "SHS", "FAP", "RP"})

    test("intensity_weight is float",
         isinstance(classified_unit["intensity_weight"], float))
    test("intensity_weight in valid range",
         0.1 <= classified_unit["intensity_weight"] <= 1.5)

    test("contexts is dict",
         isinstance(classified_unit["contexts"], dict))

# ── Step 11: Context Matcher ──
print("\n[11] Context Matcher")
ctx_ceqa = match_contexts("Prepared CEQA biological resources sections")
test("CEQA detected as environmental_review",
     "regulatory_interactions" in ctx_ceqa)

ctx_wetland = match_contexts("wetland delineation and stream assessment")
test("Wetland detected as hydrologic_systems",
     "working_environments" in ctx_wetland)

ctx_survey = match_contexts("Conducted protocol surveys for species")
test("Survey detected as species_interaction_mode",
     "species_interaction_modes" in ctx_survey)

ctx_gis = match_contexts("GIS mapping and data analysis")
test("GIS detected as methods_tools",
     "methods_tools" in ctx_gis)

ctx_empty = match_contexts("general office duties")
test("No false positives on generic text",
     len(ctx_empty) == 0)

# ── Step 12: Intensity Calculator ──
print("\n[12] Intensity Calculator")
inten_long = calculate_intensity(2010, 2026, "Senior Lead Biologist")
test("Long + senior role → high intensity",
     inten_long >= 1.0)

inten_short = calculate_intensity(2023, 2024, "Field Assistant")
test("Short + junior role → lower intensity",
     inten_short < inten_long)

inten_cred = calculate_intensity(2015, 2015, "degree", is_credential=True)
test("Credential → reduced intensity",
     inten_cred < 0.8)

inten_none = calculate_intensity(None, None, "")
test("Missing years → default 0.5",
     inten_none == 0.5)

inten_det1 = calculate_intensity(2018, 2026, "Lead Biologist")
inten_det2 = calculate_intensity(2018, 2026, "Lead Biologist")
test("Intensity is deterministic",
     inten_det1 == inten_det2)

# ── Step 13: Full Payload Build (Alexander format) ──
print("\n[13] Payload Build (profile_payload_v1)")
payload = build_payload(evidence_units, "Jane M. Doe", "sample_cv.txt")
test("Payload has profile_version",
     payload.get("profile_version") == "1.0")
test("Payload has biologist_id",
     len(payload.get("biologist_id", "")) > 0)
test("Payload has display block",
     "name" in payload.get("display", {}))
test("Payload has evidence_units",
     len(payload.get("evidence_units", [])) > 0)
test("Payload source_documents set",
     "sample_cv.txt" in payload["display"].get("source_documents", []))

for eu in payload["evidence_units"]:
    ws = sum(eu["domain_weights"].values())
    if abs(ws - 1.0) > 0.01:
        test(f"Evidence unit '{eu['id']}' weights sum = {ws}", False)
        break
else:
    test("All evidence unit weights sum to 1.0", True)

has_intensity = all(
    "intensity_weight" in eu for eu in payload["evidence_units"]
)
test("All units have intensity_weight", has_intensity)

has_contexts = all(
    "contexts" in eu for eu in payload["evidence_units"]
)
test("All units have contexts field", has_contexts)

# ── Step 14: Determinism (full payload) ──
print("\n[14] Payload Determinism")
payload2 = build_payload(evidence_units, "Jane M. Doe", "sample_cv.txt")
test("Same input → same biologist_id",
     payload["biologist_id"] == payload2["biologist_id"])
test("Same input → same unit count",
     len(payload["evidence_units"]) == len(payload2["evidence_units"]))

units_match = all(
    u1["domain_weights"] == u2["domain_weights"]
    for u1, u2 in zip(payload["evidence_units"], payload2["evidence_units"])
)
test("Same input → identical unit weights", units_match)

# ── Results ──
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
print("=" * 60)

sys.exit(1 if FAIL > 0 else 0)
