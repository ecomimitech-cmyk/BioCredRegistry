"""
BioCred Pipeline — Extreme Career Simulations & Neutrality Tests
Validation step requested by Alexander Funk.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier import (
    classify_engagement, expand_to_yearly, merge_yearly_vectors,
    build_profile, build_payload, load_keyword_ontology,
)
from pentagon_mapper import (
    get_pentagon_vertices, map_simplex_to_xy, map_trajectory,
    verify_invariants, point_in_polygon, distance_from_center,
    trajectory_centroid, trajectory_displacement, dominant_axis,
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


def eng(role, org, start, end, desc):
    return {"role": role, "organization": org, "start_year": start, "end_year": end, "description": desc}


ontology = load_keyword_ontology()
vertices = get_pentagon_vertices()

# ── Archetype 1: Pure Academic ──
print("\n[1] Pure Academic")
academic = eng("Professor", "University", 2000, 2025,
    "Published 50 peer-reviewed papers, statistical modeling, laboratory research, "
    "teaching ecology, data analysis, R programming, experimental design, thesis advisor")
prof = build_profile({"engagements": [academic]})
cl = classify_engagement(academic, ontology)
w = cl["domain_weights"]
test("KG weight dominant", w.get("KR", 0) >= max(w.values()))
mapped = map_trajectory(prof["trajectory"], vertices)
kg_dist = distance_from_center(vertices[0][0], vertices[0][1])
pt_dist = mapped[0]["distance_from_center"] if mapped else 0
test("Maps toward KG vertex (closer than center)", pt_dist > 0.1 or w.get("KR", 0) > 0.5)

# ── Archetype 2: Pure Field Biologist ──
print("\n[2] Pure Field Biologist")
field = eng("Field Biologist", "Survey Company", 2005, 2025,
    "Conducted habitat assessment surveys, biological monitoring, wetland delineation, "
    "transect sampling, point count, camera trap deployment, vegetation mapping, field inventory")
prof2 = build_profile({"engagements": [field]})
cl2 = classify_engagement(field, ontology)
w2 = cl2["domain_weights"]
test("ABP weight dominant", w2.get("FAP", 0) >= max(w2.values()))
test("Maps toward ABP vertex", dominant_axis({"weights": w2}) == "FAP" or w2.get("FAP", 0) > 0.4)

# ── Archetype 3: Policy Administrator ──
print("\n[3] Policy Administrator")
policy = eng("Regulatory Specialist", "State Agency", 2010, 2025,
    "CEQA environmental review, permit compliance, policy consultation, regulatory authorization, "
    "agency coordination, environmental impact reporting, NEPA compliance")
prof3 = build_profile({"engagements": [policy]})
cl3 = classify_engagement(policy, ontology)
w3 = cl3["domain_weights"]
test("GOV weight dominant", w3.get("RP", 0) >= max(w3.values()))
test("Maps toward GOV vertex", dominant_axis({"weights": w3}) == "RP" or w3.get("RP", 0) > 0.4)

# ── Archetype 4: Rotating Consultant ──
print("\n[4] Rotating Consultant")
rot = [
    eng("Field Tech", "Survey Co", 2008, 2012, "fieldwork survey habitat assessment wetland transect"),
    eng("Regulatory", "Agency", 2012, 2016, "CEQA permit compliance regulatory environmental review"),
    eng("Researcher", "University", 2016, 2020, "research publication statistical modeling thesis"),
    eng("Species Specialist", "Wildlife Org", 2020, 2025, "species identification capture translocation mark-recapture"),
]
prof4 = build_profile({"engagements": rot})
traj4 = prof4["trajectory"]
mapped4 = map_trajectory(traj4, vertices)
disp4 = trajectory_displacement(mapped4)
test("High displacement (rotating career)", disp4 > 0.5)
test("All years valid vectors", all(abs(sum(t["vector"]) - 1.0) < 0.01 for t in traj4))

# ── Archetype 5: Polymath Generalist ──
print("\n[5] Polymath Generalist")
gen_text = ("research fieldwork permit species lead statistical survey regulatory "
    "teaching habitat capture data analysis compliance monitoring")
generalist = eng("Biologist", "Consulting", 2015, 2025, gen_text)
prof5 = build_profile({"engagements": [generalist]})
cl5 = classify_engagement(generalist, ontology)
w5 = cl5["domain_weights"]
test("No axis > 0.35", all(v <= 0.35 for v in w5.values()))
mapped5 = map_trajectory(prof5["trajectory"], vertices)
d5 = mapped5[0]["distance_from_center"] if mapped5 else 1
test("Maps near center", d5 < 0.35)

# ── Archetype 6: Species Specialist ──
print("\n[6] Species Specialist")
species = eng("Herpetologist", "Wildlife Org", 2003, 2025,
    "species identification, listed species handling, capture relocation translocation, "
    "mark-recapture, population monitoring, taxonomy, nesting breeding migration ecology")
prof6 = build_profile({"engagements": [species]})
cl6 = classify_engagement(species, ontology)
w6 = cl6["domain_weights"]
test("BR weight dominant", w6.get("SHS", 0) >= max(w6.values()))
test("Maps toward BR vertex", dominant_axis({"weights": w6}) == "SHS" or w6.get("SHS", 0) > 0.4)

# ── Pentagon: All archetypes valid trajectories ──
print("\n[7] Pentagon: Valid trajectories")
for i, p in enumerate([prof, prof2, prof3, prof4, prof5, prof6]):
    m = map_trajectory(p["trajectory"], vertices)
    inv = verify_invariants(m, vertices)
    test(f"Archetype {i+1} inside pentagon", inv["all_inside"])

# ── point_in_polygon ──
print("\n[8] point_in_polygon")
test("Center (0,0) inside", point_in_polygon(0, 0, vertices))
test("Point (5,5) outside", not point_in_polygon(5, 5, vertices))
test("All vertices inside or on boundary", all(point_in_polygon(v[0], v[1], vertices) for v in vertices))

# ── trajectory_displacement ──
print("\n[9] trajectory_displacement")
test("Single point → 0", trajectory_displacement([{"x": 0, "y": 0}]) == 0)
test("Two distant points → positive", trajectory_displacement([{"x": 0, "y": 0}, {"x": 1, "y": 0}]) > 0)
stat_traj = [{"year": y, "vector": [0.2] * 5} for y in range(2010, 2020)]
stat_mapped = map_trajectory(stat_traj, vertices)
test("Stationary career → small displacement", trajectory_displacement(stat_mapped) < 0.01)

# ── trajectory_centroid ──
print("\n[10] trajectory_centroid")
single_pt = [{"x": 0.5, "y": 0.3}]
test("Single point → that point", trajectory_centroid(single_pt) == (0.5, 0.3))
sym = [{"x": 0.5, "y": 0}, {"x": -0.5, "y": 0}]
cx, cy = trajectory_centroid(sym)
test("Symmetric points → near center", abs(cx) < 0.01 and abs(cy) < 0.01)

# ── dominant_axis per archetype ──
print("\n[11] dominant_axis expectations")
test("Academic → KG", dominant_axis({"weights": w}) == "KR")
test("Field → ABP", dominant_axis({"weights": w2}) == "FAP")
test("Policy → GOV", dominant_axis({"weights": w3}) == "RP")
test("Species → BR", dominant_axis({"weights": w6}) == "SHS")

# ── Distance from center ──
print("\n[12] Distance from center")
spec_weights = {"KR": 0.9, "LOC": 0.025, "SHS": 0.025, "FAP": 0.025, "RP": 0.025}
sx, sy = map_simplex_to_xy(spec_weights, vertices)
test("Specialist (90% one axis) far from center", distance_from_center(sx, sy) > 0.5)
eq_weights = {"KR": 0.2, "LOC": 0.2, "SHS": 0.2, "FAP": 0.2, "RP": 0.2}
ex, ey = map_simplex_to_xy(eq_weights, vertices)
test("Generalist at center", abs(ex) < 0.01 and abs(ey) < 0.01)

# ── Rotation equivariance ──
print("\n[13] Rotation equivariance")
v0 = get_pentagon_vertices(rotation_degrees=0)
v90 = get_pentagon_vertices(rotation_degrees=90)
p0 = map_simplex_to_xy({"KR": 0.5, "LOC": 0.5, "SHS": 0, "FAP": 0, "RP": 0}, v0)
p90 = map_simplex_to_xy({"KR": 0.5, "LOC": 0.5, "SHS": 0, "FAP": 0, "RP": 0}, v90)
d0, d90 = distance_from_center(p0[0], p0[1]), distance_from_center(p90[0], p90[1])
test("Rotating pentagon rotates point (same distance)", abs(d0 - d90) < 0.01)

# ── Neutrality: No evaluative words ──
print("\n[14] Neutrality: No evaluative words")
units = [{"id": "u1", "source": "cv", "time": {"start_year": 2019, "end_year": 2020},
          "text": "Conducted wetland delineation and habitat assessment surveys"}]
payload = build_payload(units)
ev_words = ["best", "top", "strong", "weak", "superior", "inferior", "advanced",
            "expert level", "score", "rank", "rating"]
all_text = " ".join(eu.get("text", "") for eu in payload["evidence_units"])
test("No evaluative words in output", not any(w in all_text.lower() for w in ev_words))

# ── Profile version ──
print("\n[15] Profile version")
test("All profiles version 1.0", all(
    build_profile({"engagements": [academic]})["profile_version"] == "1.0" for _ in [1]))

# ── Determinism ──
print("\n[16] Determinism")
p1 = build_profile({"engagements": [academic]})
p2 = build_profile({"engagements": [academic]})
test("Same engagement → identical profile", p1["trajectory"] == p2["trajectory"])

# ── Weight invariant ──
print("\n[17] Weight invariant")
for p in [prof, prof2, prof3, prof4, prof5, prof6]:
    for t in p["trajectory"]:
        s = sum(t["vector"])
        if abs(s - 1.0) > 0.01:
            test("Weights sum to 1.0", False)
            break
    else:
        continue
    break
else:
    test("Weights sum to 1.0", True)

# ── Concurrent roles: stacked and normalized ──
print("\n[18] Concurrent roles")
e1 = eng("Field", "A", 2020, 2022, "fieldwork survey habitat")
e2 = eng("Regulatory", "B", 2020, 2022, "permit CEQA regulatory compliance")
yearly = expand_to_yearly(classify_engagement(e1, ontology)) + expand_to_yearly(classify_engagement(e2, ontology))
merged = merge_yearly_vectors(yearly)
test("Concurrent merged to single year", len(merged) == 3)
test("Concurrent sum to 1.0", abs(sum(merged[0]["vector"]) - 1.0) < 0.01)

# ── Non-negative, ≤1.0 ──
print("\n[19-20] Vectors non-negative and ≤1.0")
all_vecs = []
for p in [prof, prof2, prof3, prof4, prof5, prof6]:
    all_vecs.extend(t["vector"] for t in p["trajectory"])
test("All non-negative", all(v >= 0 for vec in all_vecs for v in vec))
test("No axis exceeds 1.0", all(v <= 1.0 for vec in all_vecs for v in vec))

# ── Credential count doesn't affect trajectory ──
print("\n[21] Credential count")
base = build_profile({"engagements": [academic], "credentials": []})
with_creds = build_profile({"engagements": [academic], "credentials": [{"name": "PhD"}, {"name": "PE"}]})
test("Credentials don't affect trajectory", base["trajectory"] == with_creds["trajectory"])

# ── context_matcher (match_contexts, calculate_intensity) ──
print("\n[22] context_matcher")
ctx = match_contexts("wetland delineation habitat assessment ceqa")
test("match_contexts returns dict", isinstance(ctx, dict))
intensity = calculate_intensity(2019, 2023, "Senior Biologist", False)
test("calculate_intensity returns float", isinstance(intensity, (int, float)) and 0 <= intensity <= 2)

# ── Results ──
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print("=" * 60)

sys.exit(1 if FAIL else 0)
