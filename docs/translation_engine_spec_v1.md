# BioCred Translation Engine Spec v1.0
## Deterministic mapping: Phase-1 Evidence → Phase-2 Axis Weights + Density Inputs

> Source: Alexander Funk, March 1 2026

## 0) Purpose

Translate verified evidence records into `evidence_units` suitable for the renderer:

- `domain_weights` on the 5 locked axes: KG/OC/BR/ABP/GOV (sum=1)
- `intensity_weight` (scalar)
- `contexts` (tags / context weights)
- `time` range (start/end)
- traceability fields (`source`, `evidence_id`, `translation_version`)

**Non-goal:** scoring, ranking, readiness classification.

## 1) Inputs and Outputs

### 1.1 Input (from Phase-1 DB)

Minimum fields per record:

- `experience_evidence.evidence_id`
- `domain_category` ∈ {Field, Regulatory, AcademicTechnical, SpeciesDepth, LeadershipResponsibility}
- `activity_type` (string/enum)
- `species_or_system` (string / optional)
- `habitat_context` (string / optional)
- `project_type` (string / optional)
- `role_level` ∈ {participant, contributor, lead, oversight, PI}
- `years_applied` OR (start_date, end_date)
- `evidence_source` (string/url)
- `is_verified` (bool) and/or `verification_state`

Optional but recommended:
- `credential_records` (degrees/certs/permits) linked to profile
- `documentation_url`
- `verification_status` (verified / partial / pending / rejected)

### 1.2 Output (profile_payload v1.0 evidence_units[])

```json
{
  "id": "ev_<evidence_id>_<idx>",
  "source": "phase1_db",
  "source_ref": { "evidence_id": "...", "credential_id": "..." },
  "time": { "start_year": 2021, "end_year": 2024 },
  "text": "short normalized description",
  "domain_weights": { "KG": 0.2, "OC": 0.1, "BR": 0.25, "ABP": 0.25, "GOV": 0.2 },
  "intensity_weight": 0.92,
  "contexts": {
    "regulatory_interactions": ["wildlife_agency_coordination"],
    "working_environments": ["hydrologic_systems"],
    "species_interaction_modes": ["survey"],
    "project_types": ["infrastructure"],
    "methods_tools": ["gis", "report_writing"]
  },
  "translation_version": "TE_v1.0"
}
```

## 2) Canonical Axes (Locked)

- **KG** = Knowledge Generation (research, publications, methods, analysis)
- **OC** = Organizational Coordination (leadership, integration, mentoring, project mgmt)
- **BR** = Biological Resolution (species/ecology judgement, species-specific protocols, determinations)
- **ABP** = Applied Biological Practice (field implementation, monitoring, restoration, surveys, delineations)
- **GOV** = Governance (permitting, CEQA/NEPA, compliance frameworks, agency coordination, policy)

Compliance Implementation is not a 6th axis; it is a label-anchor/context that increases GOV/ABP mix.

## 3) Deterministic Mapping Rules

### 3.1 Base Axis Weights by Phase-1 Domain Category

Start with base vector `B(domain_category)`:

| Domain | KG | OC | BR | ABP | GOV |
|--------|-----|-----|-----|------|------|
| Field Experience | 0.05 | 0.10 | 0.15 | 0.60 | 0.10 |
| Regulatory Experience | 0.10 | 0.15 | 0.05 | 0.10 | 0.60 |
| Academic/Technical | 0.65 | 0.10 | 0.10 | 0.10 | 0.05 |
| Species Depth | 0.05 | 0.05 | 0.65 | 0.20 | 0.05 |
| Leadership/Responsibility | 0.05 | 0.65 | 0.05 | 0.10 | 0.15 |

### 3.2 Activity-Type Modifiers (Deterministic)

Apply modifier vector `M(activity_type)` — add then renormalize.

| Activity Type | Modifiers |
|---------------|-----------|
| CEQA/NEPA writing, permit drafting, compliance reporting | +GOV 0.20, +KG 0.05, -ABP 0.10, -BR 0.05 |
| Agency coordination / consultation / meetings | +GOV 0.15, +OC 0.15, -ABP 0.10, -KG 0.10 |
| Field survey / monitoring | +ABP 0.20, +BR 0.05, -GOV 0.10, -KG 0.15 |
| Species handling / capture / relocation | +BR 0.20, +ABP 0.10, -KG 0.10, -GOV 0.20 |
| GIS / statistics / modeling / lab methods | +KG 0.25, -ABP 0.10, -GOV 0.10, -BR 0.05 |
| Project management / mentoring / QA/QC | +OC 0.25, +GOV 0.10, -ABP 0.15, -KG 0.10 |

Unknown activity types = no modifier (log unknown).

### 3.3 Role-Level Modifiers

| Role | Adjustment |
|------|------------|
| participant | +0.00 (no change) |
| contributor | +OC 0.03, +GOV 0.02 |
| lead | +OC 0.08, +GOV 0.05 |
| oversight | +OC 0.10, +GOV 0.10 |
| PI | +OC 0.10, +KG 0.10 |

Increases taken proportionally from the two highest non-target axes.

### 3.4 Species Interaction Modes → Context tags + BR/ABP tweak

- observation/survey/monitoring: +ABP 0.05, +BR 0.02
- capture/handling/relocation: +BR 0.10, +ABP 0.05
- oversight: +GOV 0.05, +BR 0.05

### 3.5 Regulatory Interaction Diversity → Context tags + GOV/OC tweak

If evidence mentions agencies (CDFW/USFWS/USACE/NOAA/Water Boards/etc.):
- Add `regulatory_interactions[]` tags
- +GOV 0.05, +OC 0.03

### 3.6 Methods/Tools → Context tags + KG/ABP tweak

- Statistics, modeling, lab, GIS → +KG 0.05
- Field instrumentation, restoration equipment → +ABP 0.05

### 3.7 Time Handling (Deterministic)

- If only `years_applied`: `start_year = end_year - years_applied + 1`
- If flagged "ongoing": `end_year = current_year`
- If start/end dates exist, use those years.

## 4) Intensity Weight

`intensity = duration_factor × verification_factor × role_factor × specificity_factor`

### 4.1 duration_factor (0.35 – 1.00)

| Duration | Factor |
|----------|--------|
| 0–3 months | 0.35 |
| 3–12 months | 0.55 |
| 1–3 years | 0.75 |
| 3–7 years | 0.90 |
| 7+ years | 1.00 |

### 4.2 verification_factor (0.30 – 1.00)

| Status | Factor |
|--------|--------|
| verified | 1.00 |
| partial | 0.70 |
| pending | 0.50 |
| rejected | 0.00 (excluded) |
| self-reported | 0.40 |

### 4.3 role_factor (0.70 – 1.05)

| Role | Factor |
|------|--------|
| participant | 0.70 |
| contributor | 0.85 |
| lead | 1.00 |
| oversight | 1.03 |
| PI | 1.05 |

### 4.4 specificity_factor (0.75 – 1.10)

- +0.05 if `species_or_system` present
- +0.05 if `project_type` present
- +0.05 if `methods_tools` non-empty
- +0.05 if `regulatory_interactions` non-empty
- Cap at 1.10, floor at 0.75

Clamp final intensity to **[0.10, 1.30]**.

## 5) Multi-Unit Rule

Split when one record spans multiple distinct contexts:
- evidence lists ≥2 `project_types`
- evidence lists ≥2 species interaction modes
- evidence combines "field survey" + "regulatory reporting"

Each split unit gets:
- Same time range
- Same base domain weights
- Context-specific modifiers per split slice
- **Intensity divided by n** (mass conservation)

## 6) Normalization and Safety

1. Clamp any negative axis values to 0
2. Renormalize to sum=1
3. If all zeros → fallback to base vector `B(domain_category)`
4. Log every fallback

## 7) Determinism Requirements

- Fixed modifier dictionaries (no ML)
- Stable sort order (`evidence_id` ascending)
- Stable rounding: 4 decimals
- `translation_version` string in every evidence_unit

## 8) Unit Tests (Acceptance)

- Simplex validity: weights in [0,1], sum=1
- Modifier determinism: same input twice → identical output JSON
- Split mass conservation: sum(intensity of splits) == original (±1e-6)
- Verification exclusion: rejected evidence → 0 units
- Unknown activity_type: valid output, modifier not applied, unknown logged

## 9) Render Payload Cache (Recommended)

Store per profile:
- `render_payload_json`
- `render_payload_hash`
- `translation_version`
- `generated_at`
