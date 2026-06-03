-- Demo render payloads for public.profile_render_v1 smoke tests (FC2401 field specialist)
-- NOT ACTUAL PERSON — matches 01_field_specialist.sql profile id

INSERT INTO render_payload_cache (
    profile_id,
    render_payload_json,
    render_payload_hash,
    translation_version
) VALUES (
    'a1000000-0000-0000-0000-000000000001',
    '{
      "profile_id": "FC2401",
      "translation_engine_version": "TE_v1.0",
      "render_version": "BPP_v1.0",
      "theme_mode": "light",
      "profile_meta": {
        "display_name": "Demo Profile A (Field Specialist)",
        "professional_title": "Senior Field Biologist",
        "organization": "Westland Environmental Services",
        "state": "California",
        "documented_practice_span": { "start_year": 2012, "end_year": 2026 },
        "verified_experience_records": 7,
        "verified_credential_records": 3
      },
      "evidence_units": [
        { "domain_weights": { "KR": 0.05, "LOC": 0.10, "SHS": 0.15, "FAP": 0.60, "RP": 0.10 }, "intensity_weight": 1.0 },
        { "domain_weights": { "KR": 0.05, "LOC": 0.08, "SHS": 0.35, "FAP": 0.45, "RP": 0.07 }, "intensity_weight": 0.9 }
      ]
    }'::jsonb,
    'demo_fc2401_v1',
    'TE_v1.0'
) ON CONFLICT (profile_id, translation_version) DO UPDATE
SET render_payload_json = EXCLUDED.render_payload_json,
    render_payload_hash = EXCLUDED.render_payload_hash,
    generated_at = now();
