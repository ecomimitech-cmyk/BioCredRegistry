"""
BioCred Pipeline — Step 2C: Pentagon Mapper
Maps domain_weights (5-float simplex) to 2D coordinates
using barycentric projection onto a regular pentagon.
Includes true point-in-polygon containment and trajectory metrics.
Deterministic: same weights always produce same (x, y).

Domain names per BPP_v1.0:
  KR  = Knowledge & Research       (top, 90°)
  LOC = Leadership & Operational Coordination (upper-left, 162°)
  SHS = Species & Habitat Specialization (lower-left, 234°)
  FAP = Field & Applied Practice   (lower-right, 306°)
  RP  = Regulation & Policy        (upper-right, 18°)
"""

import math
import json
from pathlib import Path


AXIS_ORDER = ["KR", "SHS", "FAP", "RP", "LOC"]

DOMAIN_LABELS = {
    "KR":  {"name": "Knowledge & Research",               "descriptor": "Research • Methods • Synthesis"},
    "LOC": {"name": "Leadership & Operational Coordination", "descriptor": "Leadership • Coordination • Integration"},
    "SHS": {"name": "Species & Habitat Specialization",   "descriptor": "Species • Habitat • Ecology"},
    "FAP": {"name": "Field & Applied Practice",           "descriptor": "Field Work • Lab Work • Implementation"},
    "RP":  {"name": "Regulation & Policy",                "descriptor": "Regulation • Compliance • Policy"},
}

PENTAGON_ORIENTATION = {
    "KR":  90,
    "SHS": 18,
    "FAP": -54,
    "RP":  -126,
    "LOC": 162,
}


def get_pentagon_vertices(
    center_x: float = 0.0,
    center_y: float = 0.0,
    radius: float = 1.0,
    rotation_degrees: float = -90,
) -> list:
    """Generate 5 vertices of a regular pentagon.
    Default rotation places KR at the top (90°)."""
    rotation_rad = math.radians(rotation_degrees)
    vertices = []
    for i in range(5):
        angle = rotation_rad + (2 * math.pi * i / 5)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        vertices.append((round(x, 6), round(y, 6)))
    return vertices


def map_simplex_to_xy(
    domain_weights: dict,
    vertices: list = None,
) -> tuple:
    """Barycentric mapping: weighted sum of pentagon vertices."""
    if vertices is None:
        vertices = get_pentagon_vertices()

    weights = [domain_weights.get(axis, 0.0) for axis in AXIS_ORDER]

    total = sum(weights)
    if total > 0:
        weights = [w / total for w in weights]
    else:
        weights = [0.2] * 5

    x = sum(w * v[0] for w, v in zip(weights, vertices))
    y = sum(w * v[1] for w, v in zip(weights, vertices))

    return round(x, 6), round(y, 6)


def _on_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    """Check if (px,py) lies on segment (x1,y1)-(x2,y2)."""
    if abs((y2 - y1) * (px - x1) - (py - y1) * (x2 - x1)) > 1e-9:
        return False
    return min(x1, x2) - 1e-9 <= px <= max(x1, x2) + 1e-9 and \
           min(y1, y2) - 1e-9 <= py <= max(y1, y2) + 1e-9


def point_in_polygon(px: float, py: float, polygon: list) -> bool:
    """Ray-casting algorithm for true point-in-polygon test.
    Handles points on vertices and edges (returns True)."""
    n = len(polygon)
    for v in polygon:
        if abs(px - v[0]) < 1e-9 and abs(py - v[1]) < 1e-9:
            return True
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if _on_segment(px, py, xi, yi, xj, yj):
            return True
        j = i
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if yi != yj and ((yi > py) != (yj > py)) and \
           (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def distance_from_center(x: float, y: float) -> float:
    """Euclidean distance from origin (pentagon center)."""
    return round(math.sqrt(x * x + y * y), 6)


def trajectory_displacement(mapped: list) -> float:
    """Total displacement across trajectory points."""
    if len(mapped) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(mapped)):
        dx = mapped[i]["x"] - mapped[i - 1]["x"]
        dy = mapped[i]["y"] - mapped[i - 1]["y"]
        total += math.sqrt(dx * dx + dy * dy)
    return round(total, 6)


def trajectory_centroid(mapped: list) -> tuple:
    """Geometric center of all trajectory points."""
    if not mapped:
        return 0.0, 0.0
    cx = sum(p["x"] for p in mapped) / len(mapped)
    cy = sum(p["y"] for p in mapped) / len(mapped)
    return round(cx, 6), round(cy, 6)


def dominant_axis(mapped_point: dict) -> str:
    """Return the axis with highest weight for a mapped point."""
    weights = mapped_point.get("weights", {})
    if not weights:
        return ""
    return max(weights, key=weights.get)


def map_trajectory(trajectory: list, vertices: list = None) -> list:
    if vertices is None:
        vertices = get_pentagon_vertices()

    mapped = []
    for entry in trajectory:
        vector = entry["vector"]
        weights = {
            axis: vector[i]
            for i, axis in enumerate(AXIS_ORDER)
        }
        x, y = map_simplex_to_xy(weights, vertices)
        mapped.append({
            "year": entry["year"],
            "x": x,
            "y": y,
            "weights": weights,
            "distance_from_center": distance_from_center(x, y),
            "dominant_axis": dominant_axis({"weights": weights}),
        })

    return mapped


def verify_invariants(mapped_points: list, vertices: list) -> dict:
    """Verify all mapped points lie inside the convex hull."""
    inside = 0
    outside = 0
    for pt in mapped_points:
        if point_in_polygon(pt["x"], pt["y"], vertices):
            inside += 1
        else:
            x_on_edge = any(
                abs(pt["x"] - v[0]) < 1e-6 and abs(pt["y"] - v[1]) < 1e-6
                for v in vertices
            )
            if x_on_edge:
                inside += 1
            else:
                outside += 1

    return {
        "total_points": len(mapped_points),
        "inside_bounds": inside,
        "outside_bounds": outside,
        "all_inside": outside == 0,
        "centroid": trajectory_centroid(mapped_points),
        "total_displacement": trajectory_displacement(mapped_points),
    }


def process(profile_path: str, output_path: str = None):
    profile = json.loads(Path(profile_path).read_text())
    trajectory = profile.get("trajectory", [])

    vertices = get_pentagon_vertices()
    mapped = map_trajectory(trajectory, vertices)

    invariants = verify_invariants(mapped, vertices)

    result = {
        "person": profile.get("person", ""),
        "domain_order": AXIS_ORDER,
        "vertices": {
            axis: vertices[i]
            for i, axis in enumerate(AXIS_ORDER)
        },
        "mapped_trajectory": mapped,
        "invariants": invariants,
    }

    out = output_path or "mapped_profile.json"
    Path(out).write_text(
        json.dumps(result, indent=2, ensure_ascii=False)
    )

    print(f"Mapped {len(mapped)} points")
    print(f"Invariants: {invariants}")
    print(f"Output: {out}")

    return result
