/**
 * Load a public profile render payload by human-readable registry_id.
 * Requires Supabase anon key + profile_render_v1 view (Block 1 migration).
 */
async function fetchProfileRenderByRegistryId(supabase, registryId) {
  const { data, error } = await supabase
    .from("profile_render_v1")
    .select("registry_id, render_payload_json, translation_version, generated_at")
    .eq("registry_id", registryId)
    .maybeSingle();

  if (error) throw error;
  if (!data) return null;
  return data.render_payload_json;
}

/**
 * Parse ?id=FC2401 from the page URL and render into #biocred-chart.
 */
async function renderPublicProfileFromUrl(supabase, chartElementId) {
  const registryId =
    new URLSearchParams(window.location.search).get("id") || "FC2401";
  const payload = await fetchProfileRenderByRegistryId(supabase, registryId);
  if (!payload) {
    console.warn("No public render payload for registry_id:", registryId);
    return;
  }
  BioCred.renderFromPayload(chartElementId, payload);
}
