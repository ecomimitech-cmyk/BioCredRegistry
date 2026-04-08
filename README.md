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
│       ├── sample_cv.txt
│       ├── sample_cv_minimal.txt   # Edge case: unclassified fallback
│       ├── sample_cv_complex.txt   # Edge cases: combined headers, dates, bullets
│       └── sample_cv_government.txt # Government biologist archetype
├── renderer/               # Phase 2E: Vanilla JS pentagon renderer
│   ├── biocred-geometry.js # Geometry & KDE utilities
│   ├── biocred-renderer.js # Canvas renderer (Webflow-embeddable)
│   └── test_renderer.html  # Interactive test with 3 archetypes
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
python3 tests/test_schema.py                    # Phase 1: 79 tests
python3 pipeline/tests/test_pipeline.py          # Phase 2: 80 end-to-end tests
python3 pipeline/tests/test_parser_extractor.py  # Parser & extractor: 40 unit tests
python3 pipeline/tests/test_classifier_context.py  # Classifier & context_matcher: 73 unit tests
python3 pipeline/tests/test_careers.py            # Extreme career archetypes & neutrality: 44 tests
python3 pipeline/tests/test_translation_engine.py  # TE Spec v1.0 acceptance: 105 tests
python3 pipeline/tests/test_profile_insights.py   # Profile insights generator: 19 tests
```

**Total: 440 tests, 0 failures**

## Status

- Phase 1: Data Foundation — Complete (79 tests)
- Phase 2A-C: Pipeline — Complete (237 tests)
- Translation Engine v1.0 — Complete (105 tests)
- Profile Insights Generator — Complete (19 tests)
- Supabase RLS Policies — Complete
- Pentagon Renderer (vanilla JS) — Complete
- Webflow Integration — Pending (landing page + profile page)

## Latest Update

- Renderer visual tuning pass applied in `renderer/biocred-renderer.js`:
  - smoother KDE blending with low-density suppression
  - label placement clamped to canvas bounds to avoid text clipping
  - reduced point-marker noise for a cleaner chart look
  - stronger pentagon visual structure and richer green tonal gradient
  - click interaction on evidence points with highlight feedback
  - larger label typography with white halo for readability over density
  - reduced density curvature artifacts with rebalanced KDE blend
