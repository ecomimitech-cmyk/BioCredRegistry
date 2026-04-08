# BioCred Profile Page Design Spec v1.0

**Source:** Alexander Funk, March 2 2026

---

## Core Rule

**A reviewer must answer "fit?" in ~5 seconds.**

The profile page is designed for rapid assessment: glance → scan → drill-down.

---

## Three Layers

| Layer | Purpose |
|-------|---------|
| **Immediate read (glance)** | Trust + overview in seconds |
| **Confirming details (scan)** | Validate fit for specific role |
| **Evidence traceability (drill-down)** | Full audit path for each claim |

---

## Sections (Top to Bottom)

### 1.1 Identity + Trust Header

**Always above the fold.**

- Name
- Credential line
- Title
- Region
- Verification label: **"Documentation Verified"**
- Profile derived date
- Evidence count
- Last verification timestamp

---

### 1.2 BioCred Experience Profile Visual

**Above the fold.**

- **Canonical pentagon density map**
- Dual axis labels
- Boundary contour
- **No center marker**

**Subtitle:** *"This visualization shows where verified experience has accumulated..."*

---

### 1.3 Profile Insights

- **4–6 bullets max**
- Content types:
  - Primary concentration
  - Secondary distribution
  - Regulatory interaction breadth
  - Species interaction modes
  - Project environment diversity
  - Notable gaps

**Language rules:**

| Use | Avoid |
|-----|-------|
| significant | strong |
| concentrated | weak |
| distributed | high/low |
| limited | better |
| recurrent | advanced |
| sparse | — |

---

### 1.4 Quick Filters (Optional v1)

- Verified-only toggle
- Filter chips: species handling, CEQA-NEPA, aquatic, restoration, monitoring
- Date range slider

---

### 1.5 Credential History Table

| Column | Description |
|--------|-------------|
| Type | Credential category |
| Title | Name of credential |
| Issuer | Issuing organization |
| Year | Year obtained |
| Status | Verification status |
| Doc reference | Link to supporting document |

---

### 1.6 Experience Evidence Summary

- Grouped by **Phase-1 domains**
- Bullet lists showing:
  - Time range
  - Role level
  - Project type
  - Verification icon

---

### 1.7 Evidence Explorer (Drill-Down)

- Each record **expands** to show:
  - Text description
  - Supporting doc link (reviewers only)
  - Verification method + date
  - Audit log pointer

---

### 1.8 Neutrality Disclaimer Footer

- Standard footer clarifying BioCred's role
- No rankings, no scores, no endorsements

---

## Content Priority Rules

| Priority | Rule |
|----------|------|
| **A** | Chart + insights above the fold |
| **B** | Trust indicators before details |
| **C** | Evidence always 1-click away |

---

## Webflow Implementation

- **Profile URL** contains `registry_id`
- **JS fetches** from Supabase
- **Caching recommended:** `render_payload_json`, hash, `translation_version`

---

## Approval Checklist

- [ ] 5-second understanding possible
- [ ] Clean verification feel
- [ ] Neutral insights (no evaluative language)
- [ ] Clear evidence path (1-click drill-down)
- [ ] Agency trust maintained
