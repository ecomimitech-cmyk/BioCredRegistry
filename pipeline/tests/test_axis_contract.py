"""
BioCred Axis Contract — Cross-Language Guard Test

Locks the contract described in docs/axis_contract_v1.md. Run after any
change that touches AXIS_ORDER, PENTAGON_VISUAL_ORDER, PENTAGON_ORIENTATION,
pentagon_mapper.py, or renderer/biocred-geometry.js. Failures here mean
the Python side and the JS side have drifted, or that the trajectory
mapper has regressed back to the visual/logical index swap that we fixed.

Tests are pure-Python by default. If `node` is on PATH the script also
runs the JS leg and compares numeric output.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pipeline.te_constants import (  # noqa: E402
    AXIS_ORDER, PENTAGON_VISUAL_ORDER, PENTAGON_ORIENTATION,
)
from pipeline.pentagon_mapper import (  # noqa: E402
    get_pentagon_vertices, map_simplex_to_xy, map_trajectory,
)


passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        suffix = f" — {detail}" if detail else ""
        print(f"  FAIL: {name}{suffix}")
        failed += 1


print("=" * 60)
print("BioCred Axis Contract — Cross-Language Guard Test")
print("=" * 60)


# ─── 1. Python self-consistency ────────────────────────────────────
print("\n[1] Python constants")

test("AXIS_ORDER is a list of 5 ids",
     isinstance(AXIS_ORDER, list) and len(AXIS_ORDER) == 5)
test("AXIS_ORDER == ['KR','LOC','SHS','FAP','RP']",
     AXIS_ORDER == ["KR", "LOC", "SHS", "FAP", "RP"])
test("PENTAGON_VISUAL_ORDER == ['KR','SHS','FAP','RP','LOC']",
     PENTAGON_VISUAL_ORDER == ["KR", "SHS", "FAP", "RP", "LOC"])
test("Both orders have the same axis set",
     set(AXIS_ORDER) == set(PENTAGON_VISUAL_ORDER))
test("PENTAGON_ORIENTATION covers all 5 axes",
     set(PENTAGON_ORIENTATION.keys()) == set(AXIS_ORDER))
expected_orient = {"KR": 90, "SHS": 18, "FAP": -54, "RP": -126, "LOC": 162}
test("PENTAGON_ORIENTATION values locked",
     PENTAGON_ORIENTATION == expected_orient,
     detail=f"got {PENTAGON_ORIENTATION}")


# ─── 2. Geometric placement (KR at top etc.) ──────────────────────
print("\n[2] Geometric placement (canvas y-down)")

verts = get_pentagon_vertices(0.0, 0.0, 1.0, -90)
test("5 vertices generated", len(verts) == 5)
# vertices come in PENTAGON_VISUAL_ORDER, so verts[0] == KR top
kr_x, kr_y = verts[PENTAGON_VISUAL_ORDER.index("KR")]
test("KR vertex sits at top (y < -0.95)",
     abs(kr_x) < 1e-6 and kr_y < -0.95)
loc_x, loc_y = verts[PENTAGON_VISUAL_ORDER.index("LOC")]
test("LOC vertex sits upper-left (x < -0.5, y < 0)",
     loc_x < -0.5 and loc_y < 0)
fap_x, fap_y = verts[PENTAGON_VISUAL_ORDER.index("FAP")]
test("FAP vertex sits lower-right (x > 0.5, y > 0)",
     fap_x > 0.5 and fap_y > 0)


# ─── 3. Order-agnostic mapping ────────────────────────────────────
print("\n[3] Order-agnostic mapping (dict input)")

# Same weights, two key orderings. Must produce the exact same (x, y).
w_logical = {"KR": 0.05, "LOC": 0.10, "SHS": 0.15, "FAP": 0.60, "RP": 0.10}
w_shuffled = {"FAP": 0.60, "RP": 0.10, "KR": 0.05, "SHS": 0.15, "LOC": 0.10}
xy_a = map_simplex_to_xy(w_logical, verts)
xy_b = map_simplex_to_xy(w_shuffled, verts)
test("Dict iteration order does not change (x, y)",
     xy_a == xy_b,
     detail=f"a={xy_a} b={xy_b}")

# Equal weights map to (0, 0)
xy_eq = map_simplex_to_xy({a: 0.2 for a in AXIS_ORDER}, verts)
test("Equal weights map to center",
     abs(xy_eq[0]) < 1e-6 and abs(xy_eq[1]) < 1e-6,
     detail=f"got {xy_eq}")

# KR-heavy biases toward the top vertex
xy_kr = map_simplex_to_xy(
    {"KR": 0.8, "LOC": 0.05, "SHS": 0.05, "FAP": 0.05, "RP": 0.05},
    verts,
)
test("KR-heavy biases toward top (y << 0)",
     xy_kr[1] < -0.6,
     detail=f"got y={xy_kr[1]}")

# RP-heavy biases toward the lower-left vertex
xy_rp = map_simplex_to_xy(
    {"KR": 0.05, "LOC": 0.05, "SHS": 0.05, "FAP": 0.05, "RP": 0.8},
    verts,
)
test("RP-heavy biases lower-left (x < 0, y > 0)",
     xy_rp[0] < -0.3 and xy_rp[1] > 0.3,
     detail=f"got {xy_rp}")


# ─── 4. map_trajectory bug regression test ────────────────────────
print("\n[4] map_trajectory regression (no LOC/SHS/FAP/RP swap)")

# Build a vector in canonical AXIS_ORDER. Heavy LOC.
heavy_loc_vector = [0.05, 0.80, 0.05, 0.05, 0.05]
trajectory = [{"year": 2024, "vector": heavy_loc_vector}]
mapped = map_trajectory(trajectory, verts)
test("map_trajectory returns one mapped point", len(mapped) == 1)
m = mapped[0]

# Reconstruct the dict the renderer would receive
reconstructed = {axis: heavy_loc_vector[i] for i, axis in enumerate(AXIS_ORDER)}
xy_direct = map_simplex_to_xy(reconstructed, verts)
test("map_trajectory matches direct map_simplex_to_xy",
     (round(m["x"], 6), round(m["y"], 6))
     == (round(xy_direct[0], 6), round(xy_direct[1], 6)),
     detail=f"trajectory={(m['x'], m['y'])} direct={xy_direct}")

# LOC vertex is upper-left. So a LOC-heavy point must land upper-left.
test("Heavy LOC lands upper-left (x < -0.4, y < 0)",
     m["x"] < -0.4 and m["y"] < 0,
     detail=f"got x={m['x']} y={m['y']}")

# Dominant axis is reported correctly (was scrambled before the fix)
test("Heavy LOC dominant_axis == LOC",
     m["dominant_axis"] == "LOC",
     detail=f"got {m['dominant_axis']}")


# ─── 5. JS file structural parity ─────────────────────────────────
print("\n[5] JS file structural parity")

js_path = (
    Path(__file__).resolve().parents[2]
    / "renderer"
    / "biocred-geometry.js"
)
js_src = js_path.read_text()


def _parse_js_array(name: str) -> list:
    m = re.search(rf"var\s+{name}\s*=\s*\[([^\]]*)\]\s*;", js_src)
    if not m:
        return []
    body = m.group(1)
    return [
        s.strip().strip('"').strip("'")
        for s in body.split(",")
        if s.strip()
    ]


def _parse_js_orientation() -> dict:
    m = re.search(
        r"PENTAGON_ORIENTATION\s*=\s*\{([^}]*)\}",
        js_src,
        re.DOTALL,
    )
    if not m:
        return {}
    body = m.group(1)
    pairs = re.findall(r"([A-Z]+)\s*:\s*(-?\d+)", body)
    return {k: int(v) for k, v in pairs}


js_axis_order = _parse_js_array("AXIS_ORDER")
js_visual_order = _parse_js_array("PENTAGON_VISUAL_ORDER")
js_orientation = _parse_js_orientation()

test("JS AXIS_ORDER matches Python", js_axis_order == AXIS_ORDER,
     detail=f"js={js_axis_order} py={AXIS_ORDER}")
test("JS PENTAGON_VISUAL_ORDER matches Python",
     js_visual_order == PENTAGON_VISUAL_ORDER,
     detail=f"js={js_visual_order} py={PENTAGON_VISUAL_ORDER}")
test("JS PENTAGON_ORIENTATION matches Python",
     js_orientation == PENTAGON_ORIENTATION,
     detail=f"js={js_orientation} py={PENTAGON_ORIENTATION}")


# ─── 6. Optional Node runtime parity ──────────────────────────────
print("\n[6] Node runtime parity (optional)")

node = shutil.which("node")
if not node:
    print("  SKIP: node not on PATH; structural parity already validated.")
else:
    fixtures = [
        {"KR": 0.05, "LOC": 0.10, "SHS": 0.15, "FAP": 0.60, "RP": 0.10},
        {"KR": 0.80, "LOC": 0.05, "SHS": 0.05, "FAP": 0.05, "RP": 0.05},
        {"KR": 0.05, "LOC": 0.80, "SHS": 0.05, "FAP": 0.05, "RP": 0.05},
        {"KR": 0.05, "LOC": 0.05, "SHS": 0.05, "FAP": 0.05, "RP": 0.80},
        {a: 0.2 for a in AXIS_ORDER},
    ]

    py_xy = []
    for w in fixtures:
        x, y = map_simplex_to_xy(w, verts)
        py_xy.append((x, y))

    geometry_path = js_path.resolve().as_posix()
    fixtures_payload = json.dumps(fixtures)

    runner = f"""
        const Geo = require({json.dumps(geometry_path)});
        const verts = Geo.pentagonVertices(0, 0, 1, -90);
        const fixtures = {fixtures_payload};
        const out = fixtures.map(w => Geo.barycentricXY(w, verts));
        process.stdout.write(JSON.stringify(out));
    """

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False
    ) as fh:
        fh.write(runner)
        runner_path = fh.name

    try:
        proc = subprocess.run(
            [node, runner_path],
            capture_output=True, text=True, timeout=10,
        )
        ok = proc.returncode == 0
        test("Node runner exits cleanly", ok,
             detail=proc.stderr.strip()[:200])
        if ok:
            js_xy = json.loads(proc.stdout)
            test("Same number of points", len(js_xy) == len(py_xy))
            for i, (py_pt, js_pt) in enumerate(zip(py_xy, js_xy)):
                px, py = py_pt
                jx, jy = js_pt["x"], js_pt["y"]
                close = (
                    abs(px - jx) < 1e-6
                    and abs(py - jy) < 1e-6
                )
                test(
                    f"Fixture {i}: Python ≈ JS within 1e-6",
                    close,
                    detail=f"py=({px},{py}) js=({jx},{jy})",
                )
    finally:
        try:
            os.unlink(runner_path)
        except OSError:
            pass


# ─── Summary ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
