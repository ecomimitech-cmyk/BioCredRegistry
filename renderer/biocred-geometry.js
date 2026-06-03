/**
 * BioCred Renderer — Geometry & KDE utilities
 * Extracted for modularity. Used by biocred-renderer.js.
 *
 * Axis contract — see docs/axis_contract_v1.md.
 *   AXIS_ORDER  (logical / data layout): KR, LOC, SHS, FAP, RP
 *   PENTAGON_VISUAL_ORDER (clockwise from top, geometry only):
 *                                         KR, SHS, FAP, RP, LOC
 *
 * pentagonVertices() returns vertices in PENTAGON_VISUAL_ORDER so KR
 * is at the top vertex and the polygon walks clockwise. Data lookups
 * (barycentricXY, centroid) iterate by axis name so they are immune
 * to any ordering mismatch on the caller side.
 */
(function (root) {
  "use strict";

  var AXIS_ORDER = ["KR", "LOC", "SHS", "FAP", "RP"];
  var PENTAGON_VISUAL_ORDER = ["KR", "SHS", "FAP", "RP", "LOC"];
  var PENTAGON_ORIENTATION = {
    KR:  90,
    SHS: 18,
    FAP: -54,
    RP:  -126,
    LOC: 162
  };

  function pentagonVertices(cx, cy, radius, rotDeg) {
    var rot = (rotDeg !== undefined ? rotDeg : -90) * Math.PI / 180;
    var verts = [];
    for (var i = 0; i < 5; i++) {
      var angle = rot + (2 * Math.PI * i / 5);
      verts.push({
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle)
      });
    }
    return verts;
  }

  function vertexForAxis(axis, verts) {
    return verts[PENTAGON_VISUAL_ORDER.indexOf(axis)];
  }

  function barycentricXY(weights, verts) {
    var raw = {}, sum = 0;
    for (var i = 0; i < AXIS_ORDER.length; i++) {
      var ax = AXIS_ORDER[i];
      var v = Math.max(0, Number(weights[ax]) || 0);
      raw[ax] = v;
      sum += v;
    }
    var norm = {};
    if (sum > 0) {
      for (var j = 0; j < AXIS_ORDER.length; j++) {
        norm[AXIS_ORDER[j]] = raw[AXIS_ORDER[j]] / sum;
      }
    } else {
      for (var k = 0; k < AXIS_ORDER.length; k++) norm[AXIS_ORDER[k]] = 0.2;
    }
    var x = 0, y = 0;
    for (var m = 0; m < AXIS_ORDER.length; m++) {
      var ax2 = AXIS_ORDER[m];
      var vert = vertexForAxis(ax2, verts);
      x += norm[ax2] * vert.x;
      y += norm[ax2] * vert.y;
    }
    return { x: x, y: y };
  }

  function centroid(points) {
    if (!points || points.length === 0) return null;
    var sx = 0, sy = 0;
    for (var i = 0; i < points.length; i++) {
      sx += points[i].x;
      sy += points[i].y;
    }
    return { x: sx / points.length, y: sy / points.length };
  }

  function pointInPentagon(px, py, verts) {
    var n = verts.length, inside = false;
    for (var i = 0, j = n - 1; i < n; j = i++) {
      var xi = verts[i].x, yi = verts[i].y;
      var xj = verts[j].x, yj = verts[j].y;
      if (((yi > py) !== (yj > py)) &&
          (px < (xj - xi) * (py - yi) / (yj - yi) + xi)) {
        inside = !inside;
      }
    }
    return inside;
  }

  function buildDensityGrid(points, verts, cx, cy, radius, gridSize) {
    var bandwidth = radius * 0.20;
    var bw2 = bandwidth * bandwidth;
    var span = radius * 2.4;
    var step = span / gridSize;
    var startX = cx - radius * 1.2;
    var startY = cy - radius * 1.2;
    var grid = [], maxVal = 0;

    for (var gy = 0; gy < gridSize; gy++) {
      grid[gy] = [];
      for (var gx = 0; gx < gridSize; gx++) {
        var px = startX + gx * step;
        var py = startY + gy * step;
        if (!pointInPentagon(px, py, verts)) { grid[gy][gx] = 0; continue; }
        var density = 0;
        for (var p = 0; p < points.length; p++) {
          var dx = px - points[p].x, dy = py - points[p].y;
          density += points[p].intensity * Math.exp(-(dx * dx + dy * dy) / (2 * bw2));
        }
        grid[gy][gx] = density;
        if (density > maxVal) maxVal = density;
      }
    }
    return { grid: grid, max: maxVal, step: step, startX: startX, startY: startY };
  }

  function convexHull(pts) {
    var sorted = pts.slice().sort(function (a, b) {
      return a.x - b.x || a.y - b.y;
    });
    if (sorted.length <= 2) return sorted;
    function cross(O, A, B) {
      return (A.x - O.x) * (B.y - O.y) - (A.y - O.y) * (B.x - O.x);
    }
    var lower = [];
    for (var i = 0; i < sorted.length; i++) {
      while (lower.length >= 2 &&
             cross(lower[lower.length - 2], lower[lower.length - 1], sorted[i]) <= 0)
        lower.pop();
      lower.push(sorted[i]);
    }
    var upper = [];
    for (var j = sorted.length - 1; j >= 0; j--) {
      while (upper.length >= 2 &&
             cross(upper[upper.length - 2], upper[upper.length - 1], sorted[j]) <= 0)
        upper.pop();
      upper.push(sorted[j]);
    }
    lower.pop();
    upper.pop();
    return lower.concat(upper);
  }

  root.BioCredGeo = {
    AXIS_ORDER: AXIS_ORDER,
    PENTAGON_VISUAL_ORDER: PENTAGON_VISUAL_ORDER,
    PENTAGON_ORIENTATION: PENTAGON_ORIENTATION,
    pentagonVertices: pentagonVertices,
    vertexForAxis: vertexForAxis,
    barycentricXY: barycentricXY,
    centroid: centroid,
    pointInPentagon: pointInPentagon,
    buildDensityGrid: buildDensityGrid,
    convexHull: convexHull
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = root.BioCredGeo;
  }

})(typeof window !== "undefined" ? window : this);
