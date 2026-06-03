# BioCred Registry

A neutral, evidence-based professional registry for biological credentials.

## Overview

BioCred Registry documents biological credentials and field experience
in a structured, transparent way. It presents verified information
without ranking, scoring, or implying hierarchy.

## Project Structure

```
biocred-registry/
├── database/               # Phase 1: Data foundation
│   ├── schema.sql          # PostgreSQL schema (4 tables, 8 ENUMs)
│   ├── supabase_rls.sql    # RLS policies, roles, auth functions
│   └── seed/               # 5 archetype example profiles
├── docs/                   # Phase 1: Documentation
│   ├── data-model.md
│   ├── verification-workflow.md
│   ├── category-definitions.md
│   ├── profile-wireframe.md
│   ├── onboarding_workflow_v1.md   # Alexander Funk, Mar 2026
│   ├── profile_page_spec_v1.md     # Alexander Funk, Mar 2026
│   └── landing_page_spec_v1.md     # Alexander Funk, Mar 2026
├── pipeline/               # Phase 2: CV → BioCred translation
│   ├── config/             # Ontology and render specs
│   │   ├── axis_ontology_v1.json
│   │   ├── context_ontology_v1.json
│   │   ├── render_config_registry_v1.json
│   │   └── keyword_ontology_v1.json
│   ├── cv_parser.py        # Step 2: PDF/DOCX/TXT → sections
│   ├── engagement_extractor.py  # Step 3: Sections → engagements + evidence units
│   ├── classifier.py       # Steps 4-7: Classify → profile JSON + payload
│   ├── context_matcher.py  # Context detection + intensity_weight
│   ├── translation_engine.py  # TE Spec v1.0: Phase-1 DB → axis weights
│   ├── te_constants.py    # Base vectors, modifiers, intensity tables
│   ├── pentagon_mapper.py  # Step 2C: Weights → 2D coordinates
│   ├── profile_insights.py # Profile Insights Generator (4–6 neutral bullets)
│   └── tests/
│       ├── test_pipeline.py         # 80 end-to-end tests
│       ├── test_parser_extractor.py # 40 parser & extractor unit tests
│       ├── test_classifier_context.py # 73 classifier & context_matcher unit tests
│       ├── test_careers.py          # 44 extreme career & neutrality tests
│       ├── test_translation_engine.py # 105 TE Spec v1.0 acceptance tests
│       ├── test_profile_insights.py # 19 insights generator tests
│       ├── test_axis_contract.py    # 28 cross-language axis-contract guard tests
│       ├── sample_cv.txt
│       ├── sample_cv_minimal.txt   # Edge case: unclassified fallback
│       ├── sample_cv_complex.txt   # Edge cases: combined headers, dates, bullets
│       └── sample_cv_government.txt # Government biologist archetype
├── renderer/               # Phase 2E: Vanilla JS pentagon renderer
│   ├── biocred-geometry.js # Geometry & KDE utilities + centroid()
│   ├── biocred-renderer.js # Canvas renderer (Webflow-embeddable) with black centroid dot
│   ├── test_renderer.html  # Interactive test with 3 archetypes (KR/LOC/SHS/FAP/RP)
│   ├── test_centroid_visual.js # Headless-Chrome pixel-sampling test (7 assertions)
│   └── capture_archetypes.js   # One-shot screenshot generator for review
├── mockups/                # Visual references (read-only)
├── tests/                  # Phase 1 validation tests
├── phase1_preview.html     # Client-facing Phase 1 preview
└── README.md / TODO.md / CHANGELOG.md / ARCHITECTURE.md
```

## Five Axes (Phase 2 — Locked)

| ID  | Axis                                 | Sublabels                                  |
|-----|--------------------------------------|--------------------------------------------|
| KR  | Knowledge & Research                 | Research · Methods · Synthesis             |
| LOC | Leadership & Operational Coordination| Leadership · Coordination · Integration    |
| SHS | Species & Habitat Specialization     | Species · Habitat · Ecology                |
| FAP | Field & Applied Practice             | Field Work · Lab Work · Implementation     |
| RP  | Regulation & Policy                  | Regulation · Compliance · Policy           |

The canonical (logical) order is `KR, LOC, SHS, FAP, RP`. The visual
(geometric) order on the pentagon is `KR, SHS, FAP, RP, LOC` clockwise
from the top vertex. These two orders must never be interchanged. See
`docs/axis_contract_v1.md` for the locked contract and the bridge rule
that prevents index swaps between Python and JavaScript.

## Pipeline: CV → BioCred Profile

```
CV File → Parser → Evidence Units → Classifier → Yearly Vectors → Pentagon Map
                                       ↓                 ↓
                              profile_payload_v1    biocred_profile.json
```

Deterministic: same CV always produces identical output.
No AI evaluation, no scoring, no ranking — translation only.

## Running Tests

```bash
python3 tests/test_schema.py                       # Phase 1: 79 tests
python3 pipeline/tests/test_pipeline.py            # Phase 2: 80 end-to-end tests
python3 pipeline/tests/test_parser_extractor.py    # Parser & extractor: 40 unit tests
python3 pipeline/tests/test_classifier_context.py  # Classifier & context: 73 unit tests
python3 pipeline/tests/test_careers.py             # Extreme career archetypes: 44 tests
python3 pipeline/tests/test_translation_engine.py  # TE Spec v1.0 acceptance: 105 tests
python3 pipeline/tests/test_profile_insights.py    # Profile insights: 19 tests
python3 pipeline/tests/test_axis_contract.py       # Axis contract guard: 28 tests
node     renderer/test_centroid_visual.js          # Centroid visual: 7 tests (headless Chrome)
```

**Total: 475 tests, 0 failures.**

## Status (per Alexander Funk's status language)

- Phase 1: Data Foundation — **Core foundation built** (79 tests).
- Phase 2A-C: Pipeline — **Core foundation built** (237 tests).
- Translation Engine v1.0 — **Core foundation built** (105 tests).
- Profile Insights Generator — **Core foundation built** (19 tests).
- Supabase RLS Policies — **Prototype complete; requires live integration.**
- Pentagon Renderer (vanilla JS) — **Core foundation built**, with
  black centroid dot and locked axis contract (28 + 7 tests).
- Block 1 — Foundation lock — **Complete this slice** (May 2026).
- Block 2 — Live vertical slice — **Requires live integration**.
- Block 3 — Public profile wiring — **Requires production hardening**.

## Latest Update — May 2026 (Block 1 slice, 3h)

- Locked axis contract end-to-end. Single source of truth in
  `pipeline/te_constants.py` and mirrored in
  `renderer/biocred-geometry.js`; full doc in
  `docs/axis_contract_v1.md`. Cross-language guard test asserts
  Python ≈ JS within 1e-6 over five axis-mix fixtures.
- Fixed a silent index-swap bug in
  `pentagon_mapper.map_trajectory()` that was rotating LOC, SHS,
  FAP, RP weights onto the wrong vertices. Tests had been
  passing because every misrouting still produced a point inside
  the pentagon.
- Added the black centroid dot (with directional dashed line from
  centre when off-centre) to the renderer; validated by sampling
  canvas pixels in headless Chrome for the Field, Regulatory and
  Academic archetypes.
- Drafted `docs/production_migration_checklist_v1.md` and
  `docs/storage_policy_plan_v1.md` so the Block 2 wiring work can
  start the moment funding picks up.
