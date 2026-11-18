/**
 * Directory — search and filter across published profiles.
 * Depends on: supabase-js, config.js
 *
 * Only approved profiles are reachable here, for the same reason they are the
 * only ones reachable on a public profile page: the views and the RLS policies
 * filter them out. Search is a second door onto the same room, so the absence
 * of pending profiles is a property worth testing, not an assumption.
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
  var AXIS_ORDER = ["KR", "LOC", "SHS", "FAP", "RP"];
  // Clockwise from the top, matching the profile map. Geometry only.
  var PENTAGON_VISUAL_ORDER = ["KR", "SHS", "FAP", "RP", "LOC"];

  // Same thresholds the profile page uses for its written insights, so "focused
  // on Regulation & Policy" means the same thing in search as it does on a profile.
  var MODERATE = 0.25;

  var state = {
    rows: [],
    loaded: false,
    q: "",
    region: "",
    discipline: "",
    domain: "",
    minYears: "",
    // A–Z until someone searches or filters. Once they do, "best match" takes over
    // unless they have picked a sort themselves.
    sort: "name",
    sortTouched: false
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function supabaseClient() {
    var cfg = window.BIOCRED_CONFIG || {};
    if (!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY) {
      throw new Error("Configure frontend/config.js with the staging anon key.");
    }
    return window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY, {
      auth: { persistSession: false, autoRefreshToken: false }
    });
  }

  function meanWeights(payload) {
    var totals = { KR: 0, LOC: 0, SHS: 0, FAP: 0, RP: 0 };
    var units = (payload && payload.evidence_units) || [];
    if (!units.length) return totals;
    units.forEach(function (u) {
      var w = u.domain_weights || {};
      AXIS_ORDER.forEach(function (a) { totals[a] += w[a] || 0; });
    });
    AXIS_ORDER.forEach(function (a) { totals[a] = totals[a] / units.length; });
    return totals;
  }

  function rankedDomains(weights) {
    return AXIS_ORDER.slice()
      .sort(function (a, b) { return weights[b] - weights[a]; })
      .filter(function (a) { return weights[a] > 0; });
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text == null ? "" : text;
  }

  function show(id, on) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle("hidden", !on);
  }

  // ── loading ────────────────────────────────────────────────────────────

  async function load() {
    var sb = supabaseClient();

    var profRes = await sb
      .from("profile_public_v1")
      .select("id,registry_id,full_name,professional_title,organization,state,city,primary_discipline,years_experience,verification_status");
    if (profRes.error) throw profRes.error;
    var profiles = profRes.data || [];

    if (!profiles.length) {
      state.rows = [];
      state.loaded = true;
      return;
    }

    var ids = profiles.map(function (p) { return p.id; });

    var evRes = await sb
      .from("evidence_public_v1")
      .select("profile_id,domain_category,activity_type,species_or_system,habitat_context,project_type")
      .in("profile_id", ids);
    if (evRes.error) throw evRes.error;

    var credRes = await sb
      .from("credential_public_v1")
      .select("profile_id,credential_type,title,issuing_authority")
      .in("profile_id", ids);
    if (credRes.error) throw credRes.error;

    var renderRes = await sb
      .from("profile_render_v1")
      .select("registry_id,render_payload_json")
      .in("registry_id", profiles.map(function (p) { return p.registry_id; }));
    if (renderRes.error) throw renderRes.error;

    var evBy = {};
    (evRes.data || []).forEach(function (r) {
      (evBy[r.profile_id] = evBy[r.profile_id] || []).push(r);
    });
    var credBy = {};
    (credRes.data || []).forEach(function (r) {
      (credBy[r.profile_id] = credBy[r.profile_id] || []).push(r);
    });
    var payloadBy = {};
    (renderRes.data || []).forEach(function (r) {
      payloadBy[r.registry_id] = r.render_payload_json;
    });

    state.rows = profiles.map(function (p) {
      var payload = payloadBy[p.registry_id] || null;
      var weights = meanWeights(payload);
      var evidence = evBy[p.id] || [];
      var credentials = credBy[p.id] || [];
      var meta = (payload && payload.profile_meta) || {};

      // One lowercase blob per profile so a free-text search reaches the
      // evidence too — an agency looks for "bats" or "wetland", not for a name.
      var blob = [
        p.full_name, p.professional_title, p.organization,
        p.primary_discipline, p.city, p.state, p.registry_id
      ].concat(evidence.map(function (e) {
        return [e.activity_type, e.species_or_system, e.habitat_context, e.project_type].join(" ");
      })).concat(credentials.map(function (c) {
        return [c.title, c.issuing_authority].join(" ");
      })).join(" ").toLowerCase();

      var identity = [
        p.full_name, p.professional_title, p.organization, p.primary_discipline
      ].join(" ").toLowerCase();

      return {
        profile: p,
        weights: weights,
        ranked: rankedDomains(weights),
        identity: identity,
        blob: blob,
        nCred: meta.verified_credential_records != null ? meta.verified_credential_records : credentials.length,
        nEv: meta.verified_experience_records != null ? meta.verified_experience_records : evidence.length,
        hasPayload: !!payload
      };
    });

    state.loaded = true;
  }

  // ── filtering ──────────────────────────────────────────────────────────

  function matches(row) {
    var p = row.profile;

    if (state.q) {
      var terms = state.q.toLowerCase().split(/\s+/).filter(Boolean);
      for (var i = 0; i < terms.length; i++) {
        if (row.blob.indexOf(terms[i]) === -1) return false;
      }
    }
    if (state.region && p.state !== state.region) return false;
    if (state.discipline && p.primary_discipline !== state.discipline) return false;
    if (state.domain && !(row.weights[state.domain] >= MODERATE)) return false;
    if (state.minYears && !(Number(p.years_experience) >= Number(state.minYears))) return false;
    return true;
  }

  function byName(a, b) {
    return String(a.profile.full_name || "").localeCompare(String(b.profile.full_name || ""));
  }

  function countOccurrences(haystack, needle) {
    var n = 0, i = haystack.indexOf(needle);
    while (i !== -1) { n++; i = haystack.indexOf(needle, i + needle.length); }
    return n;
  }

  // How well a row answers the words that were actually typed. A word found in
  // the person's name, title or organisation counts for more than one found in
  // their records. Nothing here reads the experience map: a domain filter
  // narrows the list but never reorders it.
  function relevance(row) {
    if (!state.q) return 0;
    var terms = state.q.toLowerCase().split(/\s+/).filter(Boolean);
    var score = 0;
    terms.forEach(function (t) {
      score += countOccurrences(row.identity, t) * 3;
      score += countOccurrences(row.blob, t);
    });
    return score;
  }

  function effectiveSort() {
    if (state.sortTouched) return state.sort;
    return (state.q || state.region || state.discipline || state.domain || state.minYears)
      ? (state.q ? "relevance" : "name")
      : "name";
  }

  function sortRows(rows) {
    var s = effectiveSort();
    return rows.slice().sort(function (a, b) {
      if (s === "years") {
        return (Number(b.profile.years_experience) || 0) - (Number(a.profile.years_experience) || 0) || byName(a, b);
      }
      if (s === "evidence") return (b.nEv - a.nEv) || byName(a, b);
      if (s === "relevance") return (relevance(b) - relevance(a)) || byName(a, b);
      return byName(a, b);
    });
  }

  // ── rendering ──────────────────────────────────────────────────────────

  function buildOptions() {
    var regions = {}, disciplines = {};
    state.rows.forEach(function (r) {
      if (r.profile.state) regions[r.profile.state] = true;
      if (r.profile.primary_discipline) disciplines[r.profile.primary_discipline] = true;
    });

    function fill(id, values, label) {
      var sel = document.getElementById(id);
      var keep = sel.value;
      sel.innerHTML = '<option value="">' + label + "</option>" +
        Object.keys(values).sort().map(function (v) {
          return '<option value="' + esc(v) + '">' + esc(v) + "</option>";
        }).join("");
      sel.value = keep;
    }

    fill("f-region", regions, "Any region");
    fill("f-discipline", disciplines, "Any discipline");

    var dom = document.getElementById("f-domain");
    var keepDom = dom.value;
    dom.innerHTML = '<option value="">Any experience domain</option>' +
      AXIS_ORDER.map(function (a) {
        return '<option value="' + a + '">' + esc(AXIS_NAMES[a]) + "</option>";
      }).join("");
    dom.value = keepDom;
  }

  function shapeCaption(weights) {
    var ranked = AXIS_ORDER.slice().sort(function (a, b) { return weights[b] - weights[a]; });
    var top = ranked[0];
    if (!top || !(weights[top] > 0)) return "No experience map yet";
    if (weights[top] >= 0.4) return "Concentrated in " + AXIS_NAMES[top];
    if (weights[top] >= MODERATE) return "Leans toward " + AXIS_NAMES[top];
    return "Spread across the five domains";
  }

  // Longest arm always reaches the frame, so a specialist and a generalist
  // occupy the same outer size. The difference is the silhouette, not a magnitude.
  function shapeGlyph(weights) {
    var max = 0;
    PENTAGON_VISUAL_ORDER.forEach(function (a) {
      if ((weights[a] || 0) > max) max = weights[a] || 0;
    });
    if (max <= 0) return '<span class="chip muted">No experience map yet</span>';

    var cx = 28, cy = 28, radius = 22, floor = 0.18;
    function ring(scale) {
      return PENTAGON_VISUAL_ORDER.map(function (a, i) {
        var t = scale(a);
        var angle = (-90 + i * 72) * Math.PI / 180;
        var x = cx + radius * t * Math.cos(angle);
        var y = cy + radius * t * Math.sin(angle);
        return x.toFixed(2) + "," + y.toFixed(2);
      }).join(" ");
    }
    var frame = ring(function () { return 1; });
    var body = ring(function (a) {
      return floor + (1 - floor) * ((weights[a] || 0) / max);
    });
    var caption = shapeCaption(weights);
    return '<div class="r-shape">' +
      '<svg class="r-glyph" viewBox="0 0 56 56" role="img" aria-label="' + esc(caption) + '. Not a score.">' +
        '<polygon class="glyph-frame" points="' + frame + '"></polygon>' +
        '<polygon class="glyph-body" points="' + body + '"></polygon>' +
      "</svg>" +
      '<span class="r-shape-cap">' + esc(caption) + "</span>" +
    "</div>";
  }

  function card(row) {
    var p = row.profile;
    var loc = [p.city, p.state].filter(Boolean).join(", ");
    var partial = p.verification_status !== "verified";
    return '<a class="result" href="public_profile_v1.html?id=' + encodeURIComponent(p.registry_id) + '">' +
      '<div class="r-head">' +
        '<div>' +
          '<div class="r-name">' + esc(p.full_name || "Unnamed profile") + "</div>" +
          '<div class="r-title">' + esc(p.professional_title || "—") +
            (p.organization ? ' <span class="r-org">· ' + esc(p.organization) + "</span>" : "") +
          "</div>" +
        "</div>" +
        '<span class="r-badge' + (partial ? " partial" : "") + '">' +
          (partial ? "◐ Partially verified" : "✓ Documentation Verified") + "</span>" +
      "</div>" +
      '<div class="r-meta">' +
        (loc ? "<span>📍 " + esc(loc) + "</span>" : "") +
        (p.years_experience != null ? "<span>📅 " + esc(p.years_experience) + " yrs documented</span>" : "") +
        "<span>📄 " + esc(row.nEv) + " experience records</span>" +
        "<span>🎓 " + esc(row.nCred) + " credentials</span>" +
      "</div>" +
      shapeGlyph(row.weights) +
      '<div class="r-id">' + esc(p.registry_id) + "</div>" +
      "</a>";
  }

  function activeFilterCount() {
    return [state.q, state.region, state.discipline, state.domain, state.minYears]
      .filter(function (v) { return !!v; }).length;
  }

  function render() {
    var hits = sortRows(state.rows.filter(matches));

    setText("count-label",
      state.rows.length === 0
        ? "No published profiles yet"
        : hits.length + (hits.length === 1 ? " profile" : " profiles") +
          (hits.length === state.rows.length ? "" : " of " + state.rows.length));

    show("btn-clear", activeFilterCount() > 0);

    var root = document.getElementById("results");

    if (!state.rows.length) {
      root.innerHTML = "";
      show("state-empty-registry", true);
      show("state-no-hits", false);
      return;
    }
    show("state-empty-registry", false);

    if (!hits.length) {
      root.innerHTML = "";
      show("state-no-hits", true);
      return;
    }
    show("state-no-hits", false);

    root.innerHTML = hits.map(card).join("");

    var missing = hits.filter(function (r) { return !r.hasPayload; }).length;
    var note = document.getElementById("payload-note");
    if (missing) {
      note.textContent = missing === 1
        ? "One profile has no experience map yet, so it cannot be matched by domain."
        : missing + " profiles have no experience map yet, so they cannot be matched by domain.";
      note.classList.remove("hidden");
    } else {
      note.classList.add("hidden");
    }
  }

  // ── wiring ─────────────────────────────────────────────────────────────

  function debounce(fn, ms) {
    var t = null;
    return function () {
      clearTimeout(t);
      t = setTimeout(fn, ms);
    };
  }

  function readControls() {
    state.q = document.getElementById("f-q").value.trim();
    state.region = document.getElementById("f-region").value;
    state.discipline = document.getElementById("f-discipline").value;
    state.domain = document.getElementById("f-domain").value;
    state.minYears = document.getElementById("f-years").value;
  }

  // Keep the Sort box honest about what is actually being used.
  function syncSortBox() {
    document.getElementById("f-sort").value = effectiveSort();
  }

  function bind() {
    var onChange = function () { readControls(); syncSortBox(); render(); };
    document.getElementById("f-q").addEventListener("input", debounce(onChange, 160));
    ["f-region", "f-discipline", "f-domain", "f-years"].forEach(function (id) {
      document.getElementById(id).addEventListener("change", onChange);
    });
    document.getElementById("f-sort").addEventListener("change", function () {
      state.sort = document.getElementById("f-sort").value;
      state.sortTouched = true;
      render();
    });
    document.getElementById("btn-clear").addEventListener("click", function () {
      document.getElementById("f-q").value = "";
      ["f-region", "f-discipline", "f-domain", "f-years"].forEach(function (id) {
        document.getElementById(id).value = "";
      });
      state.sortTouched = false;
      state.sort = "name";
      onChange();
    });
    document.getElementById("search-form").addEventListener("submit", function (e) {
      e.preventDefault();
      onChange();
    });
  }

  window.addEventListener("DOMContentLoaded", function () {
    bind();
    show("state-loading", true);
    load().then(function () {
      buildOptions();
      show("state-loading", false);
      show("state-ready", true);
      render();
    }).catch(function (err) {
      console.error(err);
      show("state-loading", false);
      show("state-error", true);
      setText("error-detail", err.message || "Could not load the registry.");
    });
  });
})();
