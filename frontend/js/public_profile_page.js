/**
 * Public profile page — load a registry_id from the public-safe views.
 * Depends on: supabase-js, config.js, biocred-renderer.js
 *
 * Unpublished profiles (pending_review, rejected, draft) are invisible here
 * because the views and the RLS policies both filter them out. The empty
 * state is the proof, not an error.
 */
(function () {
  "use strict";

  var AXIS_NAMES = {
    KR: "Knowledge & Research",
    LOC: "Leadership & Operational Coordination",
    SHS: "Species & Habitat Specialization",
    FAP: "Field & Applied Practice",
    RP: "Regulation & Policy"
  };

  var DOMAIN_LABELS = {
    field_experience: "Field & Applied Practice",
    regulatory_experience: "Regulation & Policy",
    academic_technical: "Knowledge & Research",
    species_depth: "Species & Habitat Specialization",
    leadership_scope: "Leadership & Operational Coordination"
  };

  var DOMAIN_ICONS = {
    field_experience: "🌿",
    regulatory_experience: "📋",
    academic_technical: "📊",
    species_depth: "🦅",
    leadership_scope: "👥"
  };

  var CRED_LABELS = {
    degree: "Degree",
    certification: "Certification",
    license: "License",
    permit: "Permit",
    training: "Training",
    publication: "Publication",
    award: "Award",
    other: "Other"
  };

  // Thresholds for how the written summary describes where documented work sits.
  // The directory uses the same 0.25 line for "leans toward".
  var CONCENTRATION = { significant: 0.4, moderate: 0.25, present: 0.1 };
  var AXIS_ORDER = ["KR", "LOC", "SHS", "FAP", "RP"];

  var state = {
    profile: null,
    credentials: [],
    evidence: [],
    payload: null,
    generatedAt: null,
    translationVersion: null,
    chip: "all"
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function registryIdFromUrl() {
    return (new URLSearchParams(window.location.search).get("id") || "FC2401").trim();
  }

  function fmtDate(iso) {
    if (!iso) return null;
    var d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function supabaseClient() {
    var cfg = window.BIOCRED_CONFIG || {};
    if (!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY || String(cfg.SUPABASE_ANON_KEY).indexOf("YOUR_") === 0) {
      throw new Error("Configure frontend/config.js with the staging anon key.");
    }
    return window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY, {
      auth: { persistSession: false, autoRefreshToken: false }
    });
  }

  function show(id, on) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle("hidden", !on);
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text == null ? "" : text;
  }

  function pill(status) {
    var label = status === "verified" ? "Verified" : status === "partial" ? "Partial" : status;
    var cls = status === "verified" ? "verified" : status === "partial" ? "partial" : "pending";
    return '<span class="pill ' + cls + '">' + (status === "verified" ? "✓ " : status === "partial" ? "◐ " : "") + esc(label) + "</span>";
  }

  function meanWeights(units) {
    var totals = { KR: 0, LOC: 0, SHS: 0, FAP: 0, RP: 0 };
    if (!units.length) return totals;
    units.forEach(function (u) {
      var w = u.domain_weights || {};
      AXIS_ORDER.forEach(function (a) { totals[a] += w[a] || 0; });
    });
    AXIS_ORDER.forEach(function (a) { totals[a] = totals[a] / units.length; });
    return totals;
  }

  function generateInsights(payload, evidence) {
    var units = (payload && payload.evidence_units) || [];
    if (!units.length) return ["No verified experience records are available to summarise yet."];

    // This text only says what is documented. It never says what is missing:
    // the map already shows where evidence sits, and an absence is not a finding.
    var mean = meanWeights(units);
    var ranked = AXIS_ORDER.slice().sort(function (a, b) { return mean[b] - mean[a]; });
    var out = [];

    var top = ranked[0];
    if (mean[top] >= CONCENTRATION.significant) {
      out.push("Documented experience concentrated in " + AXIS_NAMES[top] + ".");
    } else if (mean[top] >= CONCENTRATION.moderate) {
      out.push("Documented experience leans toward " + AXIS_NAMES[top] + ".");
    } else {
      out.push("Documented experience is spread across the five domains.");
    }

    var secondaries = ranked.slice(1).filter(function (a) { return mean[a] >= CONCENTRATION.present; });
    if (secondaries.length && mean[top] >= CONCENTRATION.moderate) {
      if (secondaries.length === 1) {
        out.push("Also documented in " + AXIS_NAMES[secondaries[0]] + ".");
      } else {
        out.push("Also documented in " + secondaries.slice(0, 3).map(function (a) { return AXIS_NAMES[a]; }).join(", ") + ".");
      }
    }

    var habitats = {};
    (evidence || []).forEach(function (e) {
      if (e.habitat_context) habitats[e.habitat_context] = true;
    });
    var habitatList = Object.keys(habitats);
    if (habitatList.length >= 3) {
      out.push("Project environments span " + habitatList.length + " documented habitat contexts.");
    } else if (habitatList.length === 2) {
      out.push("Experience across " + habitatList[0] + " and " + habitatList[1] + ".");
    } else if (habitatList.length === 1) {
      out.push("Project environments concentrated in " + habitatList[0] + ".");
    }

    return out.slice(0, 6);
  }

  function matchesChip(row) {
    var chip = state.chip;
    if (chip === "all") return true;
    if (chip === "verified") return row.verification_status === "verified";
    if (chip.indexOf("domain:") === 0) return row.domain_category === chip.slice(7);
    var q = chip.toLowerCase();
    var blob = [row.activity_type, row.species_or_system, row.habitat_context, row.project_type]
      .join(" ").toLowerCase();
    return blob.indexOf(q) !== -1;
  }

  function renderIdentity() {
    var p = state.profile;
    var meta = (state.payload && state.payload.profile_meta) || {};
    var name = meta.display_name || p.full_name || "Unnamed profile";
    // Only the title the person gave. BioCred does not generate a designation.
    var titleParts = [
      meta.professional_title || p.professional_title
    ].filter(Boolean);
    var loc = [p.city, p.state].filter(Boolean).join(", ");

    document.title = "BioCred — " + name + " · " + p.registry_id;
    setText("breadcrumb", "Public Profile · " + p.registry_id);
    setText("id-name", name);
    setText("id-title", titleParts.join(" · "));

    var nEv = meta.verified_experience_records != null
      ? meta.verified_experience_records
      : state.evidence.length;
    var nCred = meta.verified_credential_records != null
      ? meta.verified_credential_records
      : state.credentials.length;

    var derived = fmtDate(state.generatedAt);
    var locHtml = loc ? "<span>📍 <strong>" + esc(loc) + "</strong></span>" : "";
    var years = p.years_experience != null
      ? "<span>📅 <strong>" + esc(p.years_experience) + "</strong> years documented</span>"
      : "";
    document.getElementById("id-meta").innerHTML =
      locHtml +
      years +
      "<span>📄 <strong>" + esc(nEv) + "</strong> verified experience records</span>" +
      "<span>🎓 <strong>" + esc(nCred) + "</strong> verified credentials</span>" +
      (derived ? "<span>🔄 Profile derived <strong>" + esc(derived) + "</strong></span>" : "");

    var verified = p.verification_status === "verified";
    var badge = document.getElementById("verified-badge");
    badge.textContent = verified ? "Documentation Verified" : "Partially verified";
    badge.className = "verified-badge" + (verified ? "" : " partial-badge");

    document.getElementById("trust-meta").innerHTML =
      "Registry ID: " + esc(p.registry_id) + "<br>" +
      "Translation Engine: " + esc(state.translationVersion || "TE_v1.0");
  }

  function renderInsights() {
    var items = generateInsights(state.payload, state.evidence);
    document.getElementById("insights-list").innerHTML = items.map(function (t) {
      return "<li>" + esc(t) + "</li>";
    }).join("");
  }

  function renderChips() {
    var chips = [
      { id: "all", label: "All records" },
      { id: "verified", label: "Verified only" }
    ];
    var seen = {};
    state.evidence.forEach(function (e) {
      if (e.domain_category && !seen[e.domain_category]) {
        seen[e.domain_category] = true;
        chips.push({
          id: "domain:" + e.domain_category,
          label: DOMAIN_LABELS[e.domain_category] || e.domain_category
        });
      }
    });
    document.getElementById("chips").innerHTML =
      '<span class="chip-label">Filter by:</span>' +
      chips.map(function (c) {
        var active = c.id === state.chip ? " active" : "";
        return '<span class="chip' + active + '" data-chip="' + esc(c.id) + '">' + esc(c.label) + "</span>";
      }).join("");
  }

  function renderCredentials() {
    setText("cred-sub", state.credentials.length + " verified records");
    var body = document.getElementById("cred-body");
    if (!state.credentials.length) {
      body.innerHTML = '<tr><td colspan="5" class="empty-cell">No verified credentials on this profile.</td></tr>';
      return;
    }
    body.innerHTML = state.credentials.map(function (c) {
      return "<tr>" +
        "<td>" + esc(CRED_LABELS[c.credential_type] || c.credential_type) + "</td>" +
        "<td>" + esc(c.title) + "</td>" +
        "<td>" + esc(c.issuing_authority) + "</td>" +
        "<td>" + esc(c.year_issued || "—") + "</td>" +
        "<td>" + pill(c.verification_status) + "</td>" +
        "</tr>";
    }).join("");
  }

  function renderEvidence() {
    var grouped = {};
    var order = [
      "field_experience",
      "species_depth",
      "academic_technical",
      "regulatory_experience",
      "leadership_scope"
    ];
    state.evidence.forEach(function (e) {
      var key = e.domain_category || "field_experience";
      (grouped[key] = grouped[key] || []).push(e);
    });
    order.forEach(function (k) { if (!grouped[k]) return; });
    Object.keys(grouped).forEach(function (k) {
      if (order.indexOf(k) === -1) order.push(k);
    });

    var visibleTotal = 0;
    var html = order.map(function (key) {
      var rows = (grouped[key] || []).filter(matchesChip);
      if (!rows.length) return "";
      visibleTotal += rows.length;
      var items = rows.map(function (e) {
        var meta = [e.years_applied ? e.years_applied + " yrs" : null, e.role_level, e.habitat_context]
          .filter(Boolean).join(" · ");
        return '<div class="ev-item">' +
          '<span class="ev-icon">' + (DOMAIN_ICONS[key] || "•") + "</span>" +
          '<div class="ev-body">' +
            '<div class="ev-title">' + esc(e.activity_type || "Experience record") + "</div>" +
            (meta ? '<div class="ev-meta">' + esc(meta) + "</div>" : "") +
            (e.species_or_system ? '<div class="ev-meta">' + esc(e.species_or_system) + "</div>" : "") +
            '<div class="ev-badges">' + pill(e.verification_status) + "</div>" +
          "</div></div>";
      }).join("");
      return '<div class="domain-group">' +
        '<button type="button" class="domain-toggle">' +
          '<span class="domain-name">' + esc(DOMAIN_LABELS[key] || key) + "</span>" +
          '<span class="domain-count">' + rows.length + " records</span>" +
          '<span class="domain-chevron open">▶</span>' +
        "</button>" +
        '<div class="domain-records open">' + items + "</div>" +
        "</div>";
    }).join("");

    document.getElementById("evidence-root").innerHTML = html ||
      '<p class="empty-cell" style="padding:24px">No experience records match this filter.</p>';
    setText("ev-sub", visibleTotal + " records · grouped by domain");
  }

  function paint() {
    renderIdentity();
    renderInsights();
    renderChips();
    renderCredentials();
    renderEvidence();
  }

  function bind() {
    document.getElementById("chips").addEventListener("click", function (ev) {
      var chip = ev.target.closest("[data-chip]");
      if (!chip) return;
      state.chip = chip.getAttribute("data-chip");
      renderChips();
      renderEvidence();
    });

    document.getElementById("evidence-root").addEventListener("click", function (ev) {
      var btn = ev.target.closest(".domain-toggle");
      if (!btn) return;
      var records = btn.nextElementSibling;
      var chevron = btn.querySelector(".domain-chevron");
      records.classList.toggle("open");
      chevron.classList.toggle("open");
    });

    document.querySelector(".heatmap-btn").addEventListener("click", function () {
      var panel = document.getElementById("heatmap-panel");
      var btn = document.querySelector(".heatmap-btn");
      var visible = panel.classList.toggle("visible");
      btn.textContent = visible ? "✕ Hide Experience Map" : "⬡ View Experience Map";
      if (visible && state.payload && window.BioCred && window.BioCred.renderFromPayload) {
        var chart = document.getElementById("biocred-chart");
        chart.innerHTML = "";
        window.BioCred.renderFromPayload("biocred-chart", state.payload);
      }
    });
  }

  async function load() {
    var id = registryIdFromUrl();
    setText("breadcrumb", "Public Profile · " + id);
    show("state-loading", true);
    show("state-missing", false);
    show("state-ready", false);

    var sb = supabaseClient();

    var profileRes = await sb
      .from("profile_public_v1")
      .select("id,registry_id,full_name,professional_title,organization,state,city,years_experience,primary_discipline,verification_status,updated_at")
      .eq("registry_id", id)
      .maybeSingle();
    if (profileRes.error) throw profileRes.error;

    if (!profileRes.data) {
      setText("missing-id", id);
      show("state-loading", false);
      show("state-missing", true);
      return;
    }

    var profile = profileRes.data;
    var creds = await sb
      .from("credential_public_v1")
      .select("id,profile_id,credential_type,title,issuing_authority,year_issued,verification_status,verification_method,verification_date")
      .eq("profile_id", profile.id)
      .order("year_issued", { ascending: false });
    if (creds.error) throw creds.error;

    var ev = await sb
      .from("evidence_public_v1")
      .select("id,profile_id,domain_category,activity_type,species_or_system,habitat_context,project_type,years_applied,role_level,verification_status")
      .eq("profile_id", profile.id);
    if (ev.error) throw ev.error;

    var render = await sb
      .from("profile_render_v1")
      .select("registry_id,render_payload_json,translation_version,generated_at")
      .eq("registry_id", id)
      .maybeSingle();
    if (render.error) throw render.error;

    state.profile = profile;
    state.credentials = creds.data || [];
    state.evidence = ev.data || [];
    state.payload = render.data ? render.data.render_payload_json : null;
    state.generatedAt = render.data ? render.data.generated_at : null;
    state.translationVersion = render.data ? render.data.translation_version : null;

    paint();
    show("state-loading", false);
    show("state-ready", true);
  }

  window.addEventListener("DOMContentLoaded", function () {
    bind();
    load().catch(function (err) {
      console.error(err);
      setText("missing-id", registryIdFromUrl());
      document.getElementById("missing-detail").textContent =
        err.message || "Could not load this profile.";
      show("state-loading", false);
      show("state-missing", true);
    });
  });
})();
