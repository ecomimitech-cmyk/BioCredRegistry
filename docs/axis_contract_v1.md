# BioCred — Axis Contract v1.0

**Status:** Locked. Single source of truth for axis identifiers, axis order,
visual placement, and pentagon vertex assignment across Python, JavaScript,
JSON payloads, render-cache rows, tests, and labels.

This document exists because Block 1 of Alexander's review (May 2026) called
out that "axis order across Python, JS, payloads, labels and tests" had to
be locked to one definition before any production wiring. It also fixes a
real bug in `pipeline/pentagon_mapper.map_trajectory()` that quietly swapped
LOC / SHS / FAP / RP weights when expanding yearly vectors into 2D points.

If you are about to add a new axis, rename one, or change vertex placement,
edit this document **first**, then propagate.

---

## 1. Axis identifiers (BPP_v1.0, locked)

| ID  | Name                                       | Sublabels                                | Domain bucket            |
|-----|--------------------------------------------|------------------------------------------|--------------------------|
| KR  | Knowledge & Research                       | Research • Methods • Synthesis           | academic_technical       |
| LOC | Leadership & Operational Coordination      | Leadership • Coordination • Integration  | leadership_scope         |
| SHS | Species & Habitat Specialization           | Species • Habitat • Ecology              | species_depth            |
| FAP | Field & Applied Practice                   | Field Work • Lab Work • Implementation   | field_experience         |
| RP  | Regulation & Policy                        | Regulation • Compliance • Policy         | regulatory_experience    |

Legacy identifiers `KG / OC / BR / ABP / GOV` are deprecated and must not
appear in new code or payloads. They were renamed in v0.7.0 (March 2026).

---

## 2. Two orders, two purposes

The codebase keeps **two** explicit orderings. They are different on purpose
and must never be confused.

### 2.1 Logical / canonical order — `AXIS_ORDER`

```
AXIS_ORDER = ["KR", "LOC", "SHS", "FAP", "RP"]
```

Purpose: indexing into any list-shaped data structure that has one slot per
axis. Anywhere a `list` / `Array` represents axes, the layout is this order.

Used by:

- `classifier.expand_to_yearly()` — `vector` is laid out in `AXIS_ORDER`.
- `classifier.merge_yearly_vectors()` — preserves `AXIS_ORDER` slots.
- `translation_engine.clamp_and_renormalize()` — iterates `AXIS_ORDER`.
- `profile_insights._mean_weights()` — iterates `AXIS_ORDER`.
- All Python tests (`test_translation_engine.py`, `test_pipeline.py`, etc.).
- The JS renderer when iterating to compute the simplex sum.

Defined once in `pipeline/te_constants.py` and re-exported through
`pipeline.te_constants.AXIS_ORDER`. JavaScript copies the same list in
`renderer/biocred-geometry.js`. The cross-language test in
`pipeline/tests/test_axis_contract.py` verifies they stay in lockstep.

### 2.2 Visual / geometric order — `PENTAGON_VISUAL_ORDER`

```
PENTAGON_VISUAL_ORDER = ["KR", "SHS", "FAP", "RP", "LOC"]
```

Purpose: walking the pentagon clockwise from the top vertex. Used **only**
for geometry: vertex generation, polygon construction, point-in-polygon,
axis ray drawing, label placement.

Used by:

- `pentagon_mapper.get_pentagon_vertices()` — returns vertices in this order.
- `pentagon_mapper.vertex_for_axis(axis, verts)` — looks up by axis name.
- `renderer/biocred-renderer.js drawLabels()` — label index uses this order.
- `renderer/biocred-geometry.js pentagonVertices()` — same convention.

Never used to index into a vector that came from data. If a function is
about to read `vector[i]`, it must declare which order it expects.

### 2.3 Pentagon orientation (math degrees)

Standard math convention (sin positive = up). Canvas code flips y for the
final pixel coordinate.

```
PENTAGON_ORIENTATION = {
  "KR":  90,    # top
  "SHS": 18,    # upper-right
  "FAP": -54,   # lower-right
  "RP":  -126,  # lower-left
  "LOC": 162,   # upper-left
}
```

These are derived: starting at -90° canvas rotation and stepping +72° in
visual order yields exactly these per-axis angles. They are kept explicit so
the angle of any axis can be queried without rederiving it.

---

## 3. The bridge rule

This is the rule that prevents the bug we just fixed.

> Any function that reads or writes axis weights as a `dict / object`
> (keys = axis ids) is order-agnostic and safe.
>
> Any function that reads or writes axis weights as a `list / Array`
> (positions = axes) **must** declare which order it uses, and **must**
> use `AXIS_ORDER` unless the docstring says otherwise.
>
> Any function that maps a list-form weight into pentagon space **must
> not** zip the list with `vertices`. It must rebuild a dict by name and
> then look up vertices via `vertex_for_axis()` (Python) or
> `vertexForAxis()` (JS).

The bug we fixed in `map_trajectory()` was exactly this: it zipped a
list-form vector laid out in canonical order with a vertex list laid out
in visual order, silently routing LOC weight onto the SHS vertex, etc.

---

## 4. Where each constant lives

| Constant                  | Python                              | JavaScript                                  |
|---------------------------|-------------------------------------|---------------------------------------------|
| `AXIS_ORDER`              | `pipeline/te_constants.py`          | `renderer/biocred-geometry.js`              |
| `PENTAGON_VISUAL_ORDER`   | `pipeline/te_constants.py`          | `renderer/biocred-geometry.js`              |
| `PENTAGON_ORIENTATION`    | `pipeline/te_constants.py`          | `renderer/biocred-geometry.js`              |
| Axis names / descriptors  | `pipeline/pentagon_mapper.DOMAIN_LABELS` | `renderer/biocred-renderer.js AXIS_LABELS` |

Other Python modules (`classifier.py`, `profile_insights.py`,
`translation_engine.py`, `pentagon_mapper.py`) **import** `AXIS_ORDER`
from `te_constants` and never redefine it. The cross-language test asserts
this.

---

## 5. Payload contract

Render payloads (`render_payload_cache.render_payload_json`) and translation
payloads (`translate_profile()` output) are **always** axis-keyed dicts:

```json
{
  "evidence_units": [
    {
      "id": "ev_1_0",
      "domain_weights": { "KR": 0.04, "LOC": 0.08, "SHS": 0.16, "FAP": 0.62, "RP": 0.10 },
      "intensity_weight": 0.85,
      "contexts": { "...": "..." }
    }
  ]
}
```

Never a list. The renderer accepts only this shape. Webflow embeds rely
on this contract, so changing it is a breaking change.

The yearly trajectory inside a `biocred_profile.json` is the one place a
list form appears (`{"year": 2024, "vector": [KR, LOC, SHS, FAP, RP]}`),
and it is laid out in `AXIS_ORDER`.

---

## 6. Adding or renaming an axis

Edit in this order:

1. Update the table in §1 of this file.
2. Update `AXIS_ORDER`, `PENTAGON_VISUAL_ORDER`, `PENTAGON_ORIENTATION` in
   `pipeline/te_constants.py`.
3. Mirror in `renderer/biocred-geometry.js`.
4. Update `pipeline/pentagon_mapper.DOMAIN_LABELS` and
   `renderer/biocred-renderer.js AXIS_LABELS`.
5. Update `pipeline/config/axis_ontology_v1.json` and
   `pipeline/config/keyword_ontology_v1.json`.
6. Update `pipeline/te_constants.BASE_VECTORS` and any modifier table.
7. Run `python3 pipeline/tests/test_axis_contract.py` and the full pipeline
   test suite. They will fail loudly if the bridge rule is violated.

---

## 7. Verification

The cross-language guard test at
`pipeline/tests/test_axis_contract.py` asserts:

- Python and JS both expose the same `AXIS_ORDER`.
- Python and JS both expose the same `PENTAGON_VISUAL_ORDER`.
- Python and JS both expose the same `PENTAGON_ORIENTATION`.
- Same axis-keyed weights produce equivalent (x, y) under both
  `pentagon_mapper.map_simplex_to_xy()` (Python) and
  `BioCredGeo.barycentricXY()` (JS).
- The previously buggy `map_trajectory()` path now matches a direct
  `map_simplex_to_xy(weights)` call — i.e. the LOC/SHS/FAP/RP swap is gone.

Run with:

```
python3 pipeline/tests/test_axis_contract.py
```

The Node leg of the test runs automatically if `node` is on PATH; if not,
the Python side still validates structural parity by reading
`renderer/biocred-geometry.js` as text.

---

## 8. Changelog of this contract

- **v1.0 — May 2026.** Initial lock. Splits `AXIS_ORDER` (logical) and
  `PENTAGON_VISUAL_ORDER` (geometric). Fixes silent index swap in
  `map_trajectory()`. Adds Python ↔ JS guard test. Renames legacy
  `KG/OC/BR/ABP/GOV` payload demos to BPP_v1.0 ids in
  `renderer/test_renderer.html`.
