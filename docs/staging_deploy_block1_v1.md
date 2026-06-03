# BioCred — Staging deploy (Block 1, June 2026)

Run in the **Supabase SQL Editor** (or `psql`) on a **new staging project**.

## Order

1. `database/schema.sql`
2. `database/supabase_rls.sql`
3. `database/migrations/2026_06_block1_evidence_status_and_public_views.sql`
4. Seed files in order:
   - `database/seed/01_field_specialist.sql` … `05_multi_vector_expert.sql`
   - `database/seed/06_audit_log.sql`
   - `database/seed/07_render_payload_demo.sql`

## Smoke tests

```sql
-- registry_id → render payload (Block 1 deliverable)
SELECT registry_id, translation_version, jsonb_typeof(render_payload_json)
FROM public.profile_render_v1
WHERE registry_id = 'FC2401';

-- evidence uses verification_status
SELECT verification_status, count(*)
FROM experience_evidence
GROUP BY 1;

-- audit trigger (as service role / reviewer session)
UPDATE experience_evidence
SET verification_status = 'pending_review'
WHERE profile_id = 'a1000000-0000-0000-0000-000000000001'
LIMIT 1;
SELECT previous_status, new_status, changed_by
FROM verification_audit_log
ORDER BY created_at DESC
LIMIT 3;
```

## Frontend lookup (Webflow / static page)

```javascript
const registryId = new URLSearchParams(location.search).get("id") || "FC2401";
const { data, error } = await supabase
  .from("profile_render_v1")
  .select("render_payload_json, translation_version")
  .eq("registry_id", registryId)
  .maybeSingle();
```

See `frontend/public_profile_supabase_v1.js`.

## Not in Block 1

Storage buckets, signed-URL Edge Functions, upload E2E — Block 2.
