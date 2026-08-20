/* BioCred — shared Supabase client + auth/profile bootstrap (M2 intake) */
(function (global) {
  "use strict";

  var cfg = global.BIOCRED_CONFIG || {};
  if (!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY) {
    console.error("BIOCRED_CONFIG missing. Copy frontend/config.example.js → config.js");
  }

  var supabase = global.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true
    }
  });

  function requireConfig() {
    if (!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY || cfg.SUPABASE_ANON_KEY.indexOf("YOUR_") === 0) {
      throw new Error("Configure frontend/config.js with SUPABASE_URL and SUPABASE_ANON_KEY");
    }
  }

  async function getSession() {
    requireConfig();
    var res = await supabase.auth.getSession();
    if (res.error) throw res.error;
    return res.data.session;
  }

  async function requireSession(loginHref) {
    var session = await getSession();
    if (!session) {
      var next = encodeURIComponent(location.pathname.split("/").pop() || "upload_documents_v1.html");
      location.href = (loginHref || "login_v1.html") + "?next=" + next;
      return null;
    }
    return session;
  }

  async function ensureBiologistRole() {
    var { error } = await supabase.rpc("ensure_biologist_role");
    if (error) throw error;
  }

  async function getOwnProfile() {
    var session = await getSession();
    if (!session) return null;
    var { data, error } = await supabase
      .from("biologist_profile")
      .select("*")
      .eq("auth_user_id", session.user.id)
      .maybeSingle();
    if (error) throw error;
    return data;
  }

  function makeRegistryId() {
    var n = Math.floor(Math.random() * 9000) + 1000;
    return "DR" + n;
  }

  async function createDraftProfile(fields) {
    await ensureBiologistRole();
    var session = await getSession();
    if (!session) throw new Error("Not signed in");

    var payload = {
      registry_id: fields.registry_id || makeRegistryId(),
      full_name: fields.full_name,
      professional_title: fields.professional_title || null,
      organization: fields.organization || null,
      state: fields.state || null,
      city: fields.city || null,
      geographic_region: fields.geographic_region || null,
      years_experience: fields.years_experience != null && fields.years_experience !== ""
        ? Number(fields.years_experience)
        : null,
      primary_discipline: fields.primary_discipline || null,
      bio_summary: fields.bio_summary || null,
      visibility_status: "draft",
      verification_status: "submitted",
      auth_user_id: session.user.id,
      terms_accepted_at: fields.terms_accepted ? new Date().toISOString() : null
    };

    var { data, error } = await supabase
      .from("biologist_profile")
      .insert(payload)
      .select("*")
      .single();
    if (error) throw error;
    return data;
  }

  async function updateDraftProfile(profileId, fields) {
    var patch = {};
    [
      "full_name",
      "professional_title",
      "organization",
      "state",
      "city",
      "geographic_region",
      "primary_discipline",
      "bio_summary"
    ].forEach(function (k) {
      if (fields[k] !== undefined) patch[k] = fields[k] || null;
    });
    if (fields.years_experience !== undefined) {
      patch.years_experience =
        fields.years_experience === "" || fields.years_experience == null
          ? null
          : Number(fields.years_experience);
    }
    if (fields.terms_accepted) {
      patch.terms_accepted_at = new Date().toISOString();
    }

    var { data, error } = await supabase
      .from("biologist_profile")
      .update(patch)
      .eq("id", profileId)
      .select("*")
      .single();
    if (error) throw error;
    return data;
  }

  async function signUp(email, password) {
    requireConfig();
    var { data, error } = await supabase.auth.signUp({ email: email, password: password });
    if (error) throw error;
    if (data.session) {
      await ensureBiologistRole();
    }
    return data;
  }

  async function signIn(email, password) {
    requireConfig();
    var { data, error } = await supabase.auth.signInWithPassword({
      email: email,
      password: password
    });
    if (error) throw error;
    await ensureBiologistRole();
    return data;
  }

  async function signOut() {
    var { error } = await supabase.auth.signOut();
    if (error) throw error;
  }

  global.BioCred = {
    supabase: supabase,
    getSession: getSession,
    requireSession: requireSession,
    ensureBiologistRole: ensureBiologistRole,
    getOwnProfile: getOwnProfile,
    createDraftProfile: createDraftProfile,
    updateDraftProfile: updateDraftProfile,
    signUp: signUp,
    signIn: signIn,
    signOut: signOut
  };
})(window);
