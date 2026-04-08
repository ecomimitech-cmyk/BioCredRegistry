/**
 * BioCred Profile Page — Demo bootstrap
 * Depends on: biocred-geometry.js, biocred-renderer.js
 */

var DEMO_PAYLOAD = {
  profile_id: "BC-ALEX-001",
  translation_engine_version: "TE_v1.0",
  render_version: "BPP_v1.0",
  theme_mode: "light",
  profile_meta: {
    display_name: "Alexander Funk",
    professional_title: "Environmental Scientist",
    organization: "California Department of Fish & Wildlife",
    state: "California",
    documented_practice_span: { start_year: 2010, end_year: 2024 },
    verified_experience_records: 63,
    verified_credential_records: 12
  },
  evidence_units: [
    // FAP-heavy cluster (field surveys, 14 years of fieldwork)
    { domain_weights: { KR: 0.05, SHS: 0.35, FAP: 0.60, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.2 },
    { domain_weights: { KR: 0.05, SHS: 0.30, FAP: 0.65, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.1 },
    { domain_weights: { KR: 0.05, SHS: 0.25, FAP: 0.70, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.0 },
    { domain_weights: { KR: 0.00, SHS: 0.30, FAP: 0.70, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.9 },
    { domain_weights: { KR: 0.05, SHS: 0.35, FAP: 0.60, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.0 },
    { domain_weights: { KR: 0.10, SHS: 0.20, FAP: 0.70, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.1 },
    { domain_weights: { KR: 0.00, SHS: 0.40, FAP: 0.55, RP: 0.05, LOC: 0.00 }, intensity_weight: 0.95 },
    { domain_weights: { KR: 0.05, SHS: 0.25, FAP: 0.65, RP: 0.05, LOC: 0.00 }, intensity_weight: 1.05 },
    { domain_weights: { KR: 0.00, SHS: 0.35, FAP: 0.65, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.85 },
    { domain_weights: { KR: 0.10, SHS: 0.30, FAP: 0.60, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.15 },
    { domain_weights: { KR: 0.00, SHS: 0.20, FAP: 0.75, RP: 0.00, LOC: 0.05 }, intensity_weight: 0.8 },
    { domain_weights: { KR: 0.05, SHS: 0.45, FAP: 0.50, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.0 },
    // SHS cluster (species handling, ecology, monitoring)
    { domain_weights: { KR: 0.30, SHS: 0.70, FAP: 0.00, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.1 },
    { domain_weights: { KR: 0.00, SHS: 0.70, FAP: 0.30, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.0 },
    { domain_weights: { KR: 0.00, SHS: 0.65, FAP: 0.35, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.9 },
    { domain_weights: { KR: 0.10, SHS: 0.75, FAP: 0.15, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.05 },
    { domain_weights: { KR: 0.05, SHS: 0.80, FAP: 0.15, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.95 },
    { domain_weights: { KR: 0.15, SHS: 0.60, FAP: 0.25, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.85 },
    { domain_weights: { KR: 0.20, SHS: 0.55, FAP: 0.20, RP: 0.05, LOC: 0.00 }, intensity_weight: 0.75 },
    { domain_weights: { KR: 0.00, SHS: 0.60, FAP: 0.30, RP: 0.10, LOC: 0.00 }, intensity_weight: 0.70 },
    // FAP-SHS bridge
    { domain_weights: { KR: 0.00, SHS: 0.50, FAP: 0.50, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.1 },
    { domain_weights: { KR: 0.05, SHS: 0.45, FAP: 0.50, RP: 0.00, LOC: 0.00 }, intensity_weight: 1.0 },
    { domain_weights: { KR: 0.10, SHS: 0.40, FAP: 0.45, RP: 0.05, LOC: 0.00 }, intensity_weight: 0.9 },
    { domain_weights: { KR: 0.00, SHS: 0.55, FAP: 0.45, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.95 },
    { domain_weights: { KR: 0.05, SHS: 0.50, FAP: 0.40, RP: 0.05, LOC: 0.00 }, intensity_weight: 0.85 },
    // KR cluster (methods, analysis, research)
    { domain_weights: { KR: 0.65, SHS: 0.35, FAP: 0.00, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.8 },
    { domain_weights: { KR: 0.60, SHS: 0.40, FAP: 0.00, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.7 },
    { domain_weights: { KR: 0.70, SHS: 0.20, FAP: 0.10, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.65 },
    { domain_weights: { KR: 0.55, SHS: 0.30, FAP: 0.15, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.75 },
    { domain_weights: { KR: 0.50, SHS: 0.35, FAP: 0.10, RP: 0.05, LOC: 0.00 }, intensity_weight: 0.6 },
    // KR-SHS bridge (education, species research)
    { domain_weights: { KR: 0.45, SHS: 0.50, FAP: 0.05, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.7 },
    { domain_weights: { KR: 0.40, SHS: 0.55, FAP: 0.05, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.65 },
    // RP scattered (regulatory exposure)
    { domain_weights: { KR: 0.00, SHS: 0.35, FAP: 0.05, RP: 0.60, LOC: 0.00 }, intensity_weight: 0.6 },
    { domain_weights: { KR: 0.05, SHS: 0.20, FAP: 0.10, RP: 0.55, LOC: 0.10 }, intensity_weight: 0.5 },
    { domain_weights: { KR: 0.10, SHS: 0.15, FAP: 0.00, RP: 0.65, LOC: 0.10 }, intensity_weight: 0.45 },
    { domain_weights: { KR: 0.00, SHS: 0.25, FAP: 0.15, RP: 0.50, LOC: 0.10 }, intensity_weight: 0.55 },
    // LOC scattered (coordination, team lead)
    { domain_weights: { KR: 0.00, SHS: 0.00, FAP: 0.35, RP: 0.00, LOC: 0.65 }, intensity_weight: 0.5 },
    { domain_weights: { KR: 0.00, SHS: 0.10, FAP: 0.25, RP: 0.05, LOC: 0.60 }, intensity_weight: 0.45 },
    { domain_weights: { KR: 0.05, SHS: 0.00, FAP: 0.30, RP: 0.10, LOC: 0.55 }, intensity_weight: 0.4 },
    // Education units (spread towards KR)
    { domain_weights: { KR: 0.80, SHS: 0.15, FAP: 0.05, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.5 },
    { domain_weights: { KR: 0.75, SHS: 0.20, FAP: 0.05, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.45 },
    { domain_weights: { KR: 0.85, SHS: 0.10, FAP: 0.05, RP: 0.00, LOC: 0.00 }, intensity_weight: 0.4 }
  ]
};

var AXIS_TYPE_LABELS = {
  KR:  "Research & Methods Specialist",
  LOC: "Leadership & Coordination Specialist",
  SHS: "Species & Habitat Specialist",
  FAP: "Field & Applied Practice Specialist",
  RP:  "Regulatory & Policy Specialist"
};

function populateMeta(payload) {
  var meta = payload.profile_meta || {};
  var span = meta.documented_practice_span || {};

  var nameEl = document.querySelector(".identity-block .name");
  if (nameEl && meta.display_name) nameEl.textContent = meta.display_name;

  var roleEl = document.querySelector(".identity-block .role-line");
  if (roleEl) {
    var parts = [meta.professional_title, meta.organization, meta.state].filter(Boolean);
    roleEl.innerHTML = parts.map(function(p, i) {
      return i === 0 ? "<span>" + p + "</span>" : p;
    }).join(" \u00b7 ");
  }

  var el = function(id) { return document.getElementById(id); };
  if (el("metric-span") && span.start_year && span.end_year)
    el("metric-span").textContent = span.start_year + " \u2013 " + span.end_year;
  if (el("metric-evidence") && meta.verified_experience_records !== undefined)
    el("metric-evidence").textContent = meta.verified_experience_records;
  if (el("metric-creds") && meta.verified_credential_records !== undefined)
    el("metric-creds").textContent = meta.verified_credential_records;
  if (el("metric-te"))
    el("metric-te").textContent = payload.translation_engine_version || "TE_v1.0";

  var units = payload.evidence_units || [];
  var totals = { KR: 0, LOC: 0, SHS: 0, FAP: 0, RP: 0 };
  units.forEach(function(u) {
    var w = u.domain_weights || {};
    Object.keys(totals).forEach(function(ax) { totals[ax] += (w[ax] || 0) * (u.intensity_weight || 1); });
  });
  var dominant = Object.keys(totals).reduce(function(a, b) { return totals[a] > totals[b] ? a : b; });
  var second = Object.keys(totals).filter(function(k) { return k !== dominant; })
                 .reduce(function(a, b) { return totals[a] > totals[b] ? a : b; });
  var typeEl = el("profile-type");
  if (typeEl) typeEl.textContent = AXIS_TYPE_LABELS[dominant] + " \u00b7 " + second + "-oriented";
}

function renderMiniMap() {
  var Geo = window.BioCredGeo;
  var canvas = document.getElementById("biocred-minimap");
  var dpr = window.devicePixelRatio || 1;
  var size = 120;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + "px";
  canvas.style.height = size + "px";

  var ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, size, size);

  var cx = size / 2, cy = size / 2;
  var r = size * 0.38;
  var verts = Geo.pentagonVertices(cx, cy, r, -90);

  ctx.beginPath();
  ctx.moveTo(verts[0].x, verts[0].y);
  for (var i = 1; i < 5; i++) ctx.lineTo(verts[i].x, verts[i].y);
  ctx.closePath();
  ctx.strokeStyle = "#c8d8c8";
  ctx.lineWidth = 1;
  ctx.stroke();

  var units = DEMO_PAYLOAD.evidence_units;
  var sumX = 0, sumY = 0, totalW = 0;
  for (var u = 0; u < units.length; u++) {
    var pt = Geo.barycentricXY(units[u].domain_weights, verts);
    var w = units[u].intensity_weight || 1;
    sumX += pt.x * w; sumY += pt.y * w; totalW += w;
  }
  ctx.beginPath();
  ctx.arc(sumX / totalW, sumY / totalW, 7, 0, 2 * Math.PI);
  ctx.fillStyle = "#1a2e1a";
  ctx.fill();
}

function toggleTheme() {
  document.body.classList.toggle("dark");
  var btn = document.querySelector(".theme-toggle");
  btn.textContent = document.body.classList.contains("dark") ? "\u263e Dark" : "\u2600 Light";
}

window.addEventListener("load", function() {
  populateMeta(DEMO_PAYLOAD);
  BioCred.renderFromPayload("biocred-chart", DEMO_PAYLOAD);
  renderMiniMap();
});
