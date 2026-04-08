# BioCred Registry — Changelog

## [0.7.3] - 2026-03-03

### Changed — Label Readability + Density Shape Cleanup
- **renderer/biocred-renderer.js**:
  - increased domain label typography for better readability in the chart card
  - added white text halo (`strokeText`) behind all label lines
  - rebalanced KDE field (`bw`, `gamma`, center-base blend) to reduce curved blob artifacts
  - kept click-to-highlight interaction for evidence markers
  - refactored label drawing to keep renderer modular and under 400 lines

## [0.7.2] - 2026-03-03

### Changed — Chart Professionalization + Point Interaction
- **renderer/biocred-renderer.js**:
  - improved pentagon visual robustness (stronger substrate outline + subtle depth)
  - expanded green tonal range for smoother and richer density gradient rendering
  - adjusted KDE rendering parameters for clearer density contrast and reduced washout
  - added click interaction on evidence markers (selected point highlight)
  - reduced marker noise while preserving spatial cues
  - removed unused subtitle draw function to keep renderer file under 400 lines

## [0.7.1] - 2026-03-03

### Changed — Renderer Visual Tuning
- **renderer/biocred-renderer.js**:
  - tuned KDE blend (`bw`, `gamma`, alpha floor) to reduce overfilled/washed density
  - added label X clamping based on measured text width to prevent left/right clipping
  - restored full domain label strings while keeping labels inside chart bounds
  - reduced marker density and marker contrast for less visual noise

## [0.7.0] - 2026-03-06

### Changed — BPP_v1.0 Domain Rename + Renderer Update
- **Domain names updated** across all files (KG→KR, OC→LOC, BR→SHS, ABP→FAP, GOV→RP) per Alexander's BPP_v1.0 spec
- **pipeline/config/axis_ontology_v1.json**: New domain names, descriptors, and orientation angles per BPP_v1.0
- **pipeline/config/keyword_ontology_v1.json**: All axis keys renamed, expanded keyword lists
- **pipeline/config/render_config_registry_v1.json**: Hex grid config, green-only color scale (bright=more events), light theme
- **pipeline/te_constants.py**: All domain references renamed (BASE_VECTORS, ACTIVITY_PATTERNS, ROLE_MODIFIERS, SPECIES_MODE_MODIFIERS)
- **pipeline/translation_engine.py**: apply_regulatory_tweaks, apply_methods_tweaks updated
- **pipeline/classifier.py**: AXIS_ORDER and yearly vector expansion updated
- **pipeline/profile_insights.py**: AXIS_ORDER and AXIS_NAMES updated
- **pipeline/pentagon_mapper.py**: AXIS_ORDER, DOMAIN_LABELS, PENTAGON_ORIENTATION updated; KR at top
- **renderer/biocred-geometry.js**: AXIS_ORDER updated
- **renderer/biocred-renderer.js**: AXIS_LABELS with new names + descriptors; color palette green-only
- **All tests updated**: 440 tests passing, 0 failures



### Added — Supabase RLS + Renderer + Profile Insights
- **database/supabase_rls.sql**: Complete Supabase RLS policies per Onboarding v1.0
  - `user_roles` table with `app_role` ENUM (biologist, reviewer, admin)
  - Helper functions: `auth_uid()`, `has_role()`, `is_reviewer_or_admin()`
  - Per-table RLS: biologist_profile, credential_record, experience_evidence, audit_log
  - Public read: only verified/partial + active visibility profiles
  - Owner CRUD, reviewer read+update, append-only audit log
  - `render_payload_cache` table for pre-computed profile JSON
  - `can_submit_for_review()` gating function (≥1 identity cred, ≥3 evidence, ≥1 doc)
  - Storage bucket specs for credentials_docs and evidence_docs
- **renderer/biocred-renderer.js**: Vanilla JS pentagon density map renderer
  - Embeddable via `<script>` in Webflow; Canvas 2D with device-pixel-ratio support
  - Pentagon base, grid rings, axis rays, KDE density field, evidence points, convex hull contour
  - Dual axis labels (short + full name) per Alexander's Profile Page Spec
  - `BioCred.renderFromPayload()` for local data, `BioCred.renderProfile()` fetches from Supabase
  - Neutrality subtitle: "Descriptive only — no ranking or scoring is implied."
- **renderer/biocred-geometry.js**: Geometry & KDE utilities extracted for modularity
  - Pentagon vertices, barycentric mapping, point-in-polygon, Gaussian KDE grid, convex hull
- **renderer/test_renderer.html**: Interactive test page with 3 archetype payloads + empty state
- **pipeline/profile_insights.py**: Rule-based Profile Insights Generator v1.0
  - 6 insight generators: primary concentration, secondary distribution,
    regulatory breadth, species modes, environment diversity, notable gaps
  - Enforces Alexander's neutral language rules (no "strong/weak/high/low/better/advanced")
  - 4–6 bullets per profile
- **pipeline/tests/test_profile_insights.py**: 19 tests (neutrality, edge cases, bounds)
- **Total tests**: 440 (79 + 80 + 40 + 73 + 44 + 105 + 19), 0 failures

## [0.5.1] - 2026-03-02

### Added — Alexander Funk Spec Reference Docs
- **docs/onboarding_workflow_v1.md**: Onboarding workflow v1.0
  - Roles (Public, Biologist, Reviewer, Admin)
  - 4-step flow: account → draft profile → evidence (credentials + experience) → submit
  - Tiered verification (Tier 1 quick, Tier 2 progressive)
  - Supabase design: buckets, RLS, audit log
  - Pilot: invite-only 25 profiles, 72-hour SLA
- **docs/profile_page_spec_v1.md**: Profile page design spec v1.0
  - 5-second "fit?" rule; three layers (glance, scan, drill-down)
  - Sections 1.1–1.8: Identity header, pentagon visual, insights, filters, credentials, evidence, explorer, disclaimer
  - Webflow + Supabase implementation notes
- **docs/landing_page_spec_v1.md**: Landing page spec v1.0 for biocredregistry.com
  - Hero, problem/solution, canonical diagram, trust, for whom, early access
  - Tone rules; tech: Webflow + Supabase, vanilla JS renderer

## [0.5.0] - 2026-03-01

### Added — Translation Engine v1.0 (Alexander's TE Spec)
- **translation_engine.py**: Deterministic Phase-1 DB → Phase-2 axis weights
  - Base vectors per domain category (Sec 3.1, exact numbers from spec)
  - Activity-type modifiers with regex pattern matching (Sec 3.2)
  - Role-level modifiers with proportional subtraction (Sec 3.3)
  - Species interaction, regulatory, and methods/tools tweaks (Sec 3.4-3.6)
  - 4-factor intensity formula: duration × verification × role × specificity (Sec 4)
  - Multi-unit split rule with mass conservation (Sec 5)
  - Clamp-and-renormalize safety (Sec 6)
  - Unknown activity logging (Sec 7)
  - translation_version "TE_v1.0" in every output unit
- **te_constants.py**: All lookup tables extracted for maintainability
- **test_translation_engine.py**: 105 acceptance tests per TE Spec Sec 8
- **docs/translation_engine_spec_v1.md**: Full spec reference
- **Total tests**: 421 (79 + 80 + 40 + 73 + 44 + 105), 0 failures

## [0.4.1] - 2026-03-01

### Changed — Alexander's Phase 1 Approval Adjustments
- **schema.sql**: Added nullable `translation_version TEXT` column to
  `experience_evidence` table (Phase 2 pipeline versioning)
- **Seed profiles**: Relabeled all 5 archetypes as "Demo Profile A–E"
  with "DEMO DATA / NOT A REAL PERSON" markers (no real-sounding names)
- **HTML preview**: Badge text changed from "Verified" to "Documentation Verified",
  profile wireframe uses "Demo Profile A" and "[Demo Organization]",
  all profile cards show red "DEMO DATA" tag
- **Renamed**: "Ionic Profile Visualization" → "BioCred Experience Profile"
  across HTML, docs, and architecture (Ionic remains internal terminology)
- **test_schema.py**: Added test for `translation_version` column,
  updated archetype markers for demo profile names
- **Total tests**: 316 (79 + 80 + 40 + 73 + 44), 0 failures

## [0.4.0] - 2026-03-01

### Improved — All Pipeline Modules
- **cv_parser.py**: Combined header detection ("Education and Certifications"),
  PDF artifact removal, header info extraction (name/email/phone/location),
  section patterns for projects/affiliations, sentence-vs-header disambiguation
- **engagement_extractor.py**: Month-year dates ("Jan 2018 – Dec 2020"),
  season-year dates, "Ongoing" support, org extraction with prepositions ("at"),
  numbered/lettered/sub-bullet handling, credential type detection for training
- **classifier.py**: Multi-word keyword matching (bigram/substring),
  evidence unit input validation, AXIS_ORDER constant
- **context_matcher.py**: Expanded keyword lists (~50% more terms per category),
  additional leader/manager keywords
- **pentagon_mapper.py**: True point-in-polygon (ray-casting + edge/vertex),
  distance_from_center, trajectory_displacement, trajectory_centroid,
  dominant_axis, enriched mapped output

### Added — 315 Tests Total (78 + 237)
- test_parser_extractor.py (40 tests)
- test_classifier_context.py (73 tests)
- test_careers.py (44 tests) — Alexander's extreme career simulation
- 3 edge-case sample CVs (minimal, complex, government)

## [0.3.0] - 2026-02-24

### Added — Pipeline Evidence Unit Support
- **Context Matcher** (`pipeline/context_matcher.py`)
  - Keyword-based detection for 5 context categories
  - regulatory_interactions (7 types), working_environments (5),
    species_interaction_modes (7), project_types (6), methods_tools (6)
  - Deterministic intensity_weight from duration + role scope
- **Evidence Unit Extraction** (`engagement_extractor.py`)
  - Splits engagement bullets into individual evidence units
  - Each bullet becomes its own classifiable unit with parent context
  - Credentials included as evidence units
- **Evidence Unit Classification** (`classifier.py`)
  - `classify_evidence_unit()` — per-bullet domain_weights + contexts
  - `build_payload()` — outputs Alexander's profile_payload_v1.json format
  - biologist_id, display block, source_documents in output
- **Tests expanded**: 43 → 80 (context matching, intensity, payload build)

### Improved — Phase 1 HTML Preview
- Profile wireframe now shows populated example (Maria R. Delgado)
  with credential table, domain experience grid, and Send Inquiry button

## [0.2.0] - 2026-02-28

### Added — Phase 2: CV Translation Pipeline
- **Config files** (from Alexander's specs):
  - `axis_ontology_v1.json` — 5 axes (KG, OC, BR, ABP, GOV)
  - `context_ontology_v1.json` — regulatory, environments, species modes
  - `render_config_registry_v1.json` — canvas, density, color settings
  - `keyword_ontology_v1.json` — classification keywords per axis

- **CV Parser** (`pipeline/cv_parser.py`)
  - Supports PDF, DOCX, and TXT input
  - Extracts: employment, education, certifications, publications, skills

- **Engagement Extractor** (`pipeline/engagement_extractor.py`)
  - Parses employment into structured engagement records
  - Extracts credentials from education/certification sections
  - Handles year ranges and concurrent roles

- **Classification Engine** (`pipeline/classifier.py`)
  - Keyword-based axis weight assignment (deterministic)
  - Temporal expansion into yearly vectors
  - Concurrent role stacking with normalization (not averaging)
  - All vectors sum to 1.0

- **Pentagon Mapper** (`pipeline/pentagon_mapper.py`)
  - Barycentric projection onto regular pentagon
  - Equal weights map to center (0, 0)
  - Coordinate invariant verification

- **End-to-end tests** (`pipeline/tests/test_pipeline.py`)
  - 43 tests covering full pipeline
  - Sample CV for testing
  - Determinism, vector sums, coordinate bounds all verified

## [0.1.1] - 2026-02-24

### Added — Phase 1: Client Preview
- `phase1_preview.html` — Self-contained HTML preview of Phase 1 deliverables
  - Database schema diagram (3 tables + audit log)
  - Verification workflow (6-state flow)
  - Category definitions table (5 domains)
  - 5 archetype example profiles with credentials and evidence
  - Profile page wireframe (7 sections)
  - Ready to share with client for review before Supabase deployment

## [0.1.0] - 2026-02-25

### Added — Phase 1: Data Foundation
- Core data model (schema.sql): 4 tables, 8 ENUMs, indexes
- Verification workflow: 6-state machine with audit trail
- Category definitions: 5 domains with Counts As / Does Not Count As
- Profile wireframe: 7-section structural layout
- 5 archetype example profiles with seed data
- 78 validation tests — all passing
