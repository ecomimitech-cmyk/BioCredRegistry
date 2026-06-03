# BioCred Registry — TODO

## Phase 1 — Data Foundation (Complete)
- [x] Core data model (3 tables + audit log, 8 ENUMs)
- [x] Verification workflow (6-state machine)
- [x] Category definitions (5 domains)
- [x] Profile wireframe (7 sections)
- [x] 5 archetype example profiles (demo names — no real persons)
- [x] 79 validation tests — all passing
- [x] HTML preview for client review (phase1_preview.html)
- [x] translation_version column in experience_evidence
- [x] Badge: "Documentation Verified" (not just "Verified")
- [x] All profiles labeled "DEMO DATA / AI-generated identity"

## Phase 2A — Config Files (Complete)
- [x] axis_ontology_v1.json (KG, OC, BR, ABP, GOV)
- [x] context_ontology_v1.json (regulatory, environments, species modes)
- [x] render_config_registry_v1.json (canvas, density, color)
- [x] keyword_ontology_v1.json (classification keywords per axis)

## Phase 2B-TE — Translation Engine (Complete)
- [x] Translation Engine v1.0 (Alexander's TE Spec exactly)
- [x] Base vectors per Phase-1 domain (Sec 3.1)
- [x] Activity-type modifiers (Sec 3.2)
- [x] Role-level modifiers with proportional subtraction (Sec 3.3)
- [x] Species/regulatory/methods context tweaks (Sec 3.4-3.6)
- [x] 4-factor intensity formula (Sec 4)
- [x] Multi-unit split with mass conservation (Sec 5)
- [x] 105 acceptance tests — all passing

## Phase 2B — CV Translation Pipeline (Complete)
- [x] CV Parser (PDF/DOCX/TXT → parsed sections)
- [x] Engagement Extractor (sections → engagement records)
- [x] Credential Extractor (education/certs → credential records)
- [x] Functional Classification Engine (keyword → axis weights)
- [x] Temporal Expansion (engagements → yearly vectors)
- [x] Profile Builder (full pipeline → biocred_profile.json)
- [x] Evidence Unit Extractor (bullet-level granularity)
- [x] Context Matcher (regulatory, environments, species modes, methods)
- [x] Intensity Weight Calculator (duration + role scope proxies)
- [x] Evidence Unit Classifier (per-bullet domain_weights + contexts)
- [x] Payload Builder (profile_payload_v1.json — Alexander's format)
- [x] 80 end-to-end tests — all passing
- [x] 40 parser & extractor unit tests (test_parser_extractor.py)
- [x] 73 classifier & context_matcher unit tests (test_classifier_context.py)
- [x] 44 extreme career & neutrality tests (test_careers.py) — Alexander Funk validation
- [x] Sample CVs for edge case testing (minimal, complex, government biologist)

## Phase 2C — Mapping Engine (Complete)
- [x] Pentagon vertex generator
- [x] Barycentric simplex-to-XY mapper
- [x] Trajectory mapper
- [x] Coordinate invariant verification

## Supabase Setup (Complete)
- [x] RLS policies per table (biologist_profile, credential_record, experience_evidence, audit_log)
- [x] user_roles table + app_role ENUM (biologist, reviewer, admin)
- [x] render_payload_cache table for pre-computed profile JSON
- [x] can_submit_for_review() gating function
- [x] Storage bucket specs (credentials_docs, evidence_docs)

## Phase 2D — Density Engine (Complete — in renderer)
- [x] KDE grid generation (Gaussian kernel)
- [x] Density normalization
- [x] Contour boundary extraction (convex hull)

## Phase 2E — Renderer (Complete)
- [x] Pentagon substrate rendering (Canvas 2D)
- [x] Density field visualization (5-level color gradient)
- [x] Axis labels and rays (dual labels: short + full)
- [x] Participation boundary contour (dashed convex hull)
- [x] Evidence point markers (intensity-scaled)
- [x] Supabase fetch integration (BioCred.renderProfile)
- [x] 19 Profile Insights generator tests — all passing
- [x] Visual tuning pass v1 (KDE smoothing, label clamping, low-density threshold, point de-noise)
- [x] Visual tuning pass v2 (robust pentagon style, richer gradients, clickable point highlight)
- [x] Visual tuning pass v3 (readable labels with halo, less curved density field, gradient rebalance)

## Spec Reference Docs (Alexander Funk, Mar 2026)
- [x] onboarding_workflow_v1.md — Roles, steps, Supabase design, pilot plan
- [x] profile_page_spec_v1.md — 5-second rule, sections, Webflow implementation
- [x] landing_page_spec_v1.md — Hero, problem/solution, tone rules, tech stack

## Block 1 — Foundation lock (May 2026, complete this slice)
Per Alexander's May 2 review and May 4 confirmation. Status labels follow
his preferred wording.

- [x] Lock canonical AXIS_ORDER across Python, JS, payloads, labels, tests
      ("core foundation built", `docs/axis_contract_v1.md`,
      `pipeline/tests/test_axis_contract.py`, 28/28).
- [x] Fix the silent LOC ↔ SHS ↔ FAP ↔ RP swap in
      `pentagon_mapper.map_trajectory()` (regression-tested).
- [x] Add black centroid dot to the experience map, with directional
      dashed line from centre when the centroid is off-centre. Tested in
      headless Chrome via `renderer/test_centroid_visual.js`.
- [x] Draft production migration checklist
      (`docs/production_migration_checklist_v1.md`, awaiting sign-off).
- [x] Draft Supabase Storage policy plan
      (`docs/storage_policy_plan_v1.md`, awaiting sign-off).
- [x] Apply the four "Block 1 schema gaps" called out by Alexander
      (`database/migrations/2026_06_block1_evidence_status_and_public_views.sql`:
      `public.profile_render_v1`, evidence `verification_status`, audit triggers,
      verified-record edit lock). Staging steps: `docs/staging_deploy_block1_v1.md`.

## Block 2 — Vertical slice (Requires live integration)

Acceptance: one biologist → upload → reviewer approve → audit row →
public profile renders from live data, end-to-end on staging.

- [ ] Provision staging + production Supabase projects.
- [ ] Apply schema + RLS + storage policies on staging.
- [ ] Edge Function `generate_signed_url` (reviewer download path).
- [ ] Edge Function `regenerate_render_payload` (post-verify trigger).
- [ ] Wire `frontend/upload_documents_v1.html` to Supabase Auth + private storage.
- [ ] Wire `frontend/agency_review_v1.html` (rename → `biocred_review_v1.html`)
      to live submission queue + signed URLs + audit writes.
- [ ] Wire `frontend/public_profile_v1.html` to `public.profile_render_v1`.
- [ ] Run §8 storage smoke tests and §6 vertical slice acceptance from
      `production_migration_checklist_v1.md`.

## Block 3 — Public profile polish (Requires production hardening)

- [ ] Public-safe Postgres views (`public.profile_public_v1`,
      `public.credential_public_v1`, `public.evidence_public_v1`,
      `public.profile_render_v1`).
- [ ] Webflow landing page (per `landing_page_spec_v1.md`).
- [ ] Webflow profile page template (per `profile_page_spec_v1.md`).
- [ ] Anisotropic smoothing (density engine refinement).
- [ ] Grayscale readability test.
- [ ] 5-second recognition test.
- [ ] No-score / no-rank visual audit.
- [ ] Rename "Agency Review Portal" → "BioCred Review Portal" everywhere
      (`production_migration_checklist_v1.md` §8).
