/**
 * BioCred Experience Profile Renderer v1.0
 * Vanilla JS — embeddable via <script> tag in Webflow.
 * Depends on biocred-geometry.js (load first).
 *
 * Usage:
 *   <div id="biocred-profile" data-registry-id="BCR-001"></div>
 *   <script src="biocred-geometry.js"></script>
 *   <script src="biocred-renderer.js"></script>
 *   <script>BioCred.renderProfile('biocred-profile');</script>
 *
 * Or with pre-loaded payload:
 *   BioCred.renderFromPayload('biocred-profile', payloadJSON);
 */
(function (root) {
  "use strict";

  var Geo = root.BioCredGeo;
  var AXIS_ORDER = Geo.AXIS_ORDER;

  var AXIS_LABELS = {
    KR:  { full: "Knowledge & Research",                  short: "KR",  descriptor: "Research • Methods • Synthesis" },
    LOC: { full: "Leadership & Operational Coordination", short: "LOC", descriptor: "Leadership • Coordination • Integration" },
    SHS: { full: "Species & Habitat Specialization",      short: "SHS", descriptor: "Species • Habitat • Ecology" },
    FAP: { full: "Field & Applied Practice",              short: "FAP", descriptor: "Field Work • Lab Work • Implementation" },
    RP:  { full: "Regulation & Policy",                   short: "RP",  descriptor: "Regulation • Compliance • Policy" }
  };

  var P = {
    bg:           "#FFFFFF",
    pentagon:     "#EEF5EF",
    pentagonLine: "#AFC3B1",
    gridLine:     "rgba(120,170,130,0.26)",
    axisRay:      "rgba(70,120,80,0.22)",
    labelText:    "#1a3a1a",
    labelSub:     "#4a7a4a",
    density:      [
      "#0E2F22",
      "#174A33",
      "#1F6A46",
      "#2F8A58",
      "#53AA70",
      "#8DD6A0",
      "#D9F6DF"
    ],
    contour:      "rgba(63,143,87,0.45)",
    point:        "rgba(220,250,225,0.62)",
    pointStroke:  "rgba(50,110,60,0.30)",
    pointActive:  "#F3FFF5",
    pointActiveStroke: "#2E7A48"
  };

  /* ── Drawing functions ── */

  function drawPentagonBase(ctx, verts) {
    ctx.beginPath();
    ctx.moveTo(verts[0].x, verts[0].y);
    for (var i = 1; i < 5; i++) ctx.lineTo(verts[i].x, verts[i].y);
    ctx.closePath();
    ctx.shadowColor = "rgba(50,95,60,0.10)";
    ctx.shadowBlur = 10;
    ctx.shadowOffsetY = 2;
    ctx.fillStyle = P.pentagon;
    ctx.fill();
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;
    ctx.shadowOffsetY = 0;
    ctx.strokeStyle = P.pentagonLine;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  function drawGridRings(ctx, cx, cy, radius) {
    [0.33, 0.66].forEach(function (frac) {
      var inner = Geo.pentagonVertices(cx, cy, radius * frac, -90);
      ctx.beginPath();
      ctx.moveTo(inner[0].x, inner[0].y);
      for (var i = 1; i < 5; i++) ctx.lineTo(inner[i].x, inner[i].y);
      ctx.closePath();
      ctx.strokeStyle = P.gridLine;
      ctx.lineWidth = 0.8;
      ctx.stroke();
    });
  }

  function drawAxisRays(ctx, cx, cy, verts) {
    ctx.strokeStyle = P.axisRay;
    ctx.lineWidth = 0.8;
    for (var i = 0; i < 5; i++) {
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(verts[i].x, verts[i].y);
      ctx.stroke();
    }
  }

  function drawLabels(ctx, verts, radius, width) {
    var off = radius * 0.28, margin = 22;
    var sx = 0, sy = 0;
    for (var k = 0; k < 5; k++) { sx += verts[k].x; sy += verts[k].y; }
    var cx = sx / 5, cy = sy / 5;
    var font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    function txt(t, x, y, f, c) {
      ctx.font = f + " " + font;
      ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.lineWidth = 3;
      ctx.strokeText(t, x, y);
      ctx.fillStyle = c;
      ctx.fillText(t, x, y);
    }
    for (var i = 0; i < 5; i++) {
      var v = verts[i], dx = v.x - cx, dy = v.y - cy, d = Math.sqrt(dx * dx + dy * dy);
      var lx = v.x + (dx / d) * off, ly = v.y + (dy / d) * off;
      var info = AXIS_LABELS[AXIS_ORDER[i]];
      ctx.textAlign = "center";
      ctx.font = "bold 15px " + font; var w0 = ctx.measureText(info.short).width;
      ctx.font = "11px " + font; var w1 = ctx.measureText(info.full).width;
      ctx.font = "10px " + font; var w2 = ctx.measureText(info.descriptor).width;
      var halfW = Math.max(w0, w1, w2) * 0.5 + 4;
      lx = Math.max(margin + halfW, Math.min(width - margin - halfW, lx));
      var top = (dy < -d * 0.3), bottom = (dy > d * 0.3);
      ctx.textBaseline = top ? "bottom" : (bottom ? "top" : "middle");
      var y0 = top ? ly - 28 : (bottom ? ly : ly - 14);
      var y1 = top ? ly - 14 : (bottom ? ly + 16 : ly + 2);
      var y2 = top ? ly : (bottom ? ly + 30 : ly + 16);
      txt(info.short, lx, y0, "bold 15px", P.labelText);
      txt(info.full, lx, y1, "11px", P.labelSub);
      txt(info.descriptor, lx, y2, "10px", "rgba(74,106,74,0.6)");
    }
  }

  function drawDensity(ctx, points, verts, cx, cy, radius) {
    if (points.length === 0) return;

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(verts[0].x, verts[0].y);
    for (var i = 1; i < 5; i++) ctx.lineTo(verts[i].x, verts[i].y);
    ctx.closePath();
    ctx.clip();

    var gridSize = 240;
    var bw = radius * 0.15;
    var bw2 = bw * bw;
    var gamma = 0.62;
    var span = radius * 2.4;
    var step = span / gridSize;
    var ox = cx - radius * 1.2;
    var oy = cy - radius * 1.2;

    var grid = [], maxVal = 0;
    for (var gy = 0; gy < gridSize; gy++) {
      grid[gy] = [];
      for (var gx = 0; gx < gridSize; gx++) {
        var px = ox + gx * step;
        var py = oy + gy * step;
        if (!Geo.pointInPentagon(px, py, verts)) { grid[gy][gx] = 0; continue; }
        var d = 0;
        for (var p = 0; p < points.length; p++) {
          var dx = px - points[p].x, dy = py - points[p].y;
          d += points[p].intensity * Math.exp(-(dx * dx + dy * dy) / (2 * bw2));
        }
        grid[gy][gx] = d;
        if (d > maxVal) maxVal = d;
      }
    }

    if (maxVal <= 0) { ctx.restore(); return; }

    for (var gy2 = 0; gy2 < gridSize; gy2++) {
      for (var gx2 = 0; gx2 < gridSize; gx2++) {
        var val = grid[gy2][gx2];
        if (val <= 0) continue;
        var t = Math.min(1, val / maxVal);
        var bright = Math.pow(t, gamma);
        var dxC = (ox + gx2 * step) - cx;
        var dyC = (oy + gy2 * step) - cy;
        var dCenter = Math.sqrt(dxC * dxC + dyC * dyC) / radius;
        var centerBase = Math.max(0, 1 - dCenter) * 0.18;
        bright = Math.min(1, bright * 0.82 + centerBase);
        if (bright < 0.05) continue;

        var ci = bright * (P.density.length - 1);
        var lo = Math.floor(ci);
        var hi = Math.min(lo + 1, P.density.length - 1);
        var frac = ci - lo;
        var c0 = P.density[lo].replace("#", "");
        var c1 = P.density[hi].replace("#", "");
        var r0 = parseInt(c0.slice(0, 2), 16), g0 = parseInt(c0.slice(2, 4), 16), b0 = parseInt(c0.slice(4, 6), 16);
        var r1 = parseInt(c1.slice(0, 2), 16), g1 = parseInt(c1.slice(2, 4), 16), b1 = parseInt(c1.slice(4, 6), 16);
        var r = Math.round(r0 + (r1 - r0) * frac);
        var g = Math.round(g0 + (g1 - g0) * frac);
        var b = Math.round(b0 + (b1 - b0) * frac);
        var a = 0.18 + bright * 0.72;
        ctx.fillStyle = "rgba(" + r + "," + g + "," + b + "," + a.toFixed(3) + ")";
        ctx.fillRect(ox + gx2 * step, oy + gy2 * step, step + 0.5, step + 0.5);
      }
    }

    ctx.restore();
  }

  function drawPoints(ctx, points, selectedIdx) {
    var step = Math.max(1, Math.floor(points.length / 24));
    for (var i = 0; i < points.length; i += step) {
      var pt = points[i];
      var active = (selectedIdx === i);
      var r = (active ? 3.1 : 1.6) + pt.intensity * (active ? 1.2 : 0.7);
      if (active) {
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, r + 5, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(141,214,160,0.24)";
        ctx.fill();
      }
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = active ? P.pointActive : P.point;
      ctx.fill();
      ctx.strokeStyle = active ? P.pointActiveStroke : P.pointStroke;
      ctx.lineWidth = active ? 1.3 : 0.45;
      ctx.stroke();
    }
  }

  function drawContour(ctx, points) {
    if (points.length < 3) return;
    var hull = Geo.convexHull(points);
    if (hull.length < 3) return;
    ctx.beginPath();
    ctx.moveTo(hull[0].x, hull[0].y);
    for (var i = 1; i < hull.length; i++) ctx.lineTo(hull[i].x, hull[i].y);
    ctx.closePath();
    ctx.strokeStyle = P.contour;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  /* ── Main render ── */

  function render(container, payload) {
    if (typeof container === "string") container = document.getElementById(container);
    if (!container) { console.error("[BioCred] Container not found"); return; }

    var units = payload.evidence_units || [];
    if (units.length === 0) {
      container.innerHTML = '<p style="color:#64748B;font-family:sans-serif;' +
        'text-align:center;padding:40px;">No evidence data available.</p>';
      return;
    }

    var dpr = window.devicePixelRatio || 1;
    var width = container.offsetWidth || 560;
    var height = Math.max(480, Math.min(width * 0.85, 600));

    var canvas = document.createElement("canvas");
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    container.innerHTML = "";
    container.appendChild(canvas);

    var ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.fillStyle = P.bg;
    ctx.fillRect(0, 0, width, height);

    var cx = width / 2, cy = height * 0.49;
    var radius = Math.min(width, height) * 0.30;
    var verts = Geo.pentagonVertices(cx, cy, radius, -90);

    var points = units.map(function (u) {
      var w = u.domain_weights || {};
      var pt = Geo.barycentricXY(w, verts);
      return { x: pt.x, y: pt.y, intensity: u.intensity_weight || 0.5, weights: w };
    });

    var selectedIdx = null;

    function paint() {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = P.bg;
      ctx.fillRect(0, 0, width, height);
      drawPentagonBase(ctx, verts);
      drawGridRings(ctx, cx, cy, radius);
      drawAxisRays(ctx, cx, cy, verts);
      drawDensity(ctx, points, verts, cx, cy, radius);
      drawContour(ctx, points);
      drawPoints(ctx, points, selectedIdx);
      drawLabels(ctx, verts, radius, width);
    }

    paint();

    canvas.addEventListener("click", function (ev) {
      var rect = canvas.getBoundingClientRect();
      var mx = ev.clientX - rect.left;
      var my = ev.clientY - rect.top;
      var best = -1;
      var bestDist = 16;
      for (var i = 0; i < points.length; i++) {
        var dx = points[i].x - mx;
        var dy = points[i].y - my;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < bestDist) {
          bestDist = d;
          best = i;
        }
      }
      selectedIdx = (best === -1 ? null : best);
      paint();
    });
  }

  /* ── Public API ── */

  root.BioCred = {
    renderFromPayload: function (id, payload) { render(id, payload); },

    renderProfile: function (id, supabaseUrl, supabaseKey) {
      var el = document.getElementById(id);
      if (!el) { console.error("[BioCred] Container not found: " + id); return; }
      var rid = el.getAttribute("data-registry-id");
      if (!rid) { console.error("[BioCred] Missing data-registry-id"); return; }

      el.innerHTML = '<p style="color:#94A3B8;font-family:sans-serif;' +
        'text-align:center;padding:40px;">Loading profile\u2026</p>';

      var url = supabaseUrl + "/rest/v1/render_payload_cache?" +
        "select=render_payload_json&profile_id=eq." +
        encodeURIComponent(rid) + "&order=generated_at.desc&limit=1";

      fetch(url, {
        headers: { "apikey": supabaseKey, "Authorization": "Bearer " + supabaseKey }
      })
      .then(function (r) { return r.json(); })
      .then(function (rows) {
        if (!rows || !rows.length) {
          el.innerHTML = '<p style="color:#94A3B8;font-family:sans-serif;' +
            'text-align:center;padding:40px;">Profile not found.</p>';
          return;
        }
        render(el, rows[0].render_payload_json);
      })
      .catch(function (err) {
        console.error("[BioCred] Fetch error:", err);
        el.innerHTML = '<p style="color:#EF4444;font-family:sans-serif;' +
          'text-align:center;padding:40px;">Error loading profile.</p>';
      });
    },

    AXIS_ORDER: AXIS_ORDER,
    AXIS_LABELS: AXIS_LABELS,
    version: "1.0.0"
  };

})(typeof window !== "undefined" ? window : this);
