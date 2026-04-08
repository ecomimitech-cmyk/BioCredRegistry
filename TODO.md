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

## Pending
- [ ] Webflow landing page (per landing_page_spec_v1.md)
- [ ] Webflow profile page template (per profile_page_spec_v1.md)
- [ ] Supabase project setup (create project, run schema + RLS)
- [ ] Onboarding flow frontend (account creation, draft profile, evidence submission)
- [ ] Anisotropic smoothing (density engine refinement)
- [ ] Grayscale readability test
- [ ] 5-second recognition test
- [ ] No score/rank visual elements check
