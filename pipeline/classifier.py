"""
BioCred Pipeline — Steps 4-7: Classification Engine
Maps text to axis weights using the keyword ontology.
Supports both engagement-level (legacy) and evidence-unit-level classification.
Assigns context_weights and intensity_weight per evidence unit.
Deterministic: same input always produces identical output.
No AI, no randomness, no judgment.
"""

import json
import re
from pathlib import Path

from context_matcher import match_contexts, calculate_intensity

CONFIG_DIR = Path(__file__).parent / "config"
AXIS_ORDER = ["KR", "LOC", "SHS", "FAP", "RP"]


def load_keyword_ontology() -> dict:
    path = CONFIG_DIR / "keyword_ontology_v1.json"
    data = json.loads(path.read_text())
    return data["axes"]


def tokenize(text: str) -> list:
    return re.findall(r"[a-z][a-z/\-]+", text.lower())


def count_axis_matches(text: str, ontology: dict) -> dict:
    """Count keyword matches per axis. Handles multi-word terms
    (e.g. 'habitat conservation plan') via substring search for
    terms with spaces, regex word boundary for single words."""
    text_lower = text.lower()
    counts = {axis: 0 for axis in ontology}

    for axis, keywords in ontology.items():
        for keyword in keywords:
            kw_lower = keyword.lower()
            if " " in kw_lower:
                counts[axis] += text_lower.count(kw_lower)
            else:
                pattern = re.compile(r"\b" + re.escape(kw_lower) + r"\b")
                counts[axis] += len(pattern.findall(text_lower))

    return counts


def normalize_weights(counts: dict) -> dict:
    total = sum(counts.values())
    if total == 0:
        n = len(counts)
        return {axis: round(1.0 / n, 4) for axis in counts}

    return {
        axis: round(count / total, 4)
        for axis, count in counts.items()
    }


def classify_engagement(engagement: dict, ontology: dict) -> dict:
    text = " ".join([
        engagement.get("role", ""),
        engagement.get("organization", ""),
        engagement.get("description", ""),
    ])

    counts = count_axis_matches(text, ontology)
    weights = normalize_weights(counts)

    return {
        "role": engagement.get("role", ""),
        "start_year": engagement.get("start_year"),
        "end_year": engagement.get("end_year"),
        "axis_counts": counts,
        "domain_weights": weights,
        "total_matches": sum(counts.values()),
    }


def validate_evidence_unit(unit: dict) -> bool:
    """Check that an evidence unit has required fields."""
    required = ["id", "source", "time", "text"]
    return all(k in unit for k in required)


def classify_evidence_unit(unit: dict, ontology: dict) -> dict:
    """Classify a single evidence unit (bullet-level granularity).
    Returns unit enriched with domain_weights, intensity_weight, contexts."""
    if not validate_evidence_unit(unit):
        return {
            "id": unit.get("id", "invalid"),
            "source": "cv",
            "time": {},
            "text": "",
            "domain_weights": {a: 0.2 for a in AXIS_ORDER},
            "intensity_weight": 0.5,
            "contexts": {},
            "validation_error": "missing required fields",
        }

    full_text = " ".join([
        unit.get("parent_role", ""),
        unit.get("parent_org", ""),
        unit.get("text", ""),
    ])

    counts = count_axis_matches(full_text, ontology)
    weights = normalize_weights(counts)

    time = unit.get("time", {})
    intensity = calculate_intensity(
        time.get("start_year"),
        time.get("end_year"),
        unit.get("parent_role", ""),
        unit.get("is_credential", False),
    )

    contexts = match_contexts(unit.get("text", ""))

    return {
        "id": unit.get("id", ""),
        "source": unit.get("source", "cv"),
        "time": time,
        "text": unit.get("text", ""),
        "domain_weights": weights,
        "intensity_weight": intensity,
        "contexts": contexts,
    }


def expand_to_yearly(classified: dict) -> list:
    """Step 5: Convert engagement into yearly slices."""
    start = classified.get("start_year")
    end = classified.get("end_year")

    if not start or not end:
        return []

    yearly = []
    for year in range(start, end + 1):
        yearly.append({
            "year": year,
            "vector": [
                classified["domain_weights"].get("KR", 0),
                classified["domain_weights"].get("LOC", 0),
                classified["domain_weights"].get("SHS", 0),
                classified["domain_weights"].get("FAP", 0),
                classified["domain_weights"].get("RP", 0),
            ],
            "source_role": classified["role"],
        })

    return yearly


def build_profile(engagements_data: dict, person_name: str = "") -> dict:
    """Steps 4-7: Full classification pipeline."""
    ontology = load_keyword_ontology()
    engagements = engagements_data.get("engagements", [])
    credentials = engagements_data.get("credentials", [])

    all_yearly = []
    classified_engagements = []

    for eng in engagements:
        classified = classify_engagement(eng, ontology)
        classified_engagements.append(classified)
        yearly = expand_to_yearly(classified)
        all_yearly.extend(yearly)

    trajectory = merge_yearly_vectors(all_yearly)

    return {
        "profile_version": "1.0",
        "person": person_name or engagements_data.get("source", ""),
        "trajectory": trajectory,
        "credentials": credentials,
        "classified_engagements": classified_engagements,
        "tags": extract_tags(classified_engagements),
    }


def merge_yearly_vectors(yearly_entries: list) -> list:
    """Merge concurrent roles by stacking then normalizing."""
    by_year = {}
    for entry in yearly_entries:
        y = entry["year"]
        if y not in by_year:
            by_year[y] = []
        by_year[y].append(entry["vector"])

    trajectory = []
    for year in sorted(by_year.keys()):
        vectors = by_year[year]
        n = len(vectors)
        merged = [0.0] * 5
        for v in vectors:
            for i in range(5):
                merged[i] += v[i]

        total = sum(merged)
        if total > 0:
            merged = [round(m / total, 4) for m in merged]
        else:
            merged = [0.2] * 5

        trajectory.append({
            "year": year,
            "vector": merged,
        })

    return trajectory


def extract_tags(classified: list) -> list:
    tags = set()
    for eng in classified:
        counts = eng.get("axis_counts", {})
        dominant = max(counts, key=counts.get) if counts else None
        if dominant and counts[dominant] > 0:
            tags.add(dominant)
    return sorted(tags)


def build_payload(evidence_units: list, person_name: str = "",
                  source_file: str = "") -> dict:
    """Build profile_payload_v1.json — Alexander's required format.
    Evidence-unit level granularity with contexts and intensity."""
    ontology = load_keyword_ontology()

    classified_units = [
        classify_evidence_unit(unit, ontology) for unit in evidence_units
    ]

    biologist_id = re.sub(
        r"[^A-Z_]", "",
        person_name.upper().replace(" ", "_").replace(".", ""),
    )

    return {
        "profile_version": "1.0",
        "biologist_id": biologist_id or "UNKNOWN",
        "display": {
            "name": person_name,
            "descriptor": "",
            "profile_derived_date": "",
            "source_documents": [source_file] if source_file else [],
        },
        "evidence_units": classified_units,
    }


def process(engagements_path: str, output_path: str = None,
            person_name: str = ""):
    data = json.loads(Path(engagements_path).read_text())
    profile = build_profile(data, person_name)

    out = output_path or "biocred_profile.json"
    Path(out).write_text(
        json.dumps(profile, indent=2, ensure_ascii=False)
    )

    print(f"Profile: {profile['person']}")
    print(f"Trajectory: {len(profile['trajectory'])} years")
    print(f"Credentials: {len(profile['credentials'])}")
    print(f"Tags: {profile['tags']}")
    print(f"Output: {out}")

    vector_sums = [
        round(sum(t["vector"]), 4)
        for t in profile["trajectory"]
    ]
    all_valid = all(abs(s - 1.0) < 0.01 for s in vector_sums)
    print(f"Vector sums = 1.0: {'PASS' if all_valid else 'FAIL'}")

    return profile
