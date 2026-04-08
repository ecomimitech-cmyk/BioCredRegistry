# BioCred Registry — Profile Page Structure (Wireframe)

## Purpose

Structural layout of a biologist profile page.
No styling, branding, or visual design — only information architecture.

---

## Page Layout

```
╔══════════════════════════════════════════════════════════╗
║  HEADER BAR                                              ║
║  [BioCred Logo]   Search | About | FAQ | Registry        ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ┌───────────────────────────────────────────────┐      ║
║  │  SECTION 1: IDENTITY HEADER                   │      ║
║  │                                               │      ║
║  │  [Photo]   Full Name, Degrees                 │      ║
║  │            Professional Title(s)              │      ║
║  │            Organization (optional)            │      ║
║  │            Registry ID: XX0000                │      ║
║  │            Location: City, State              │      ║
║  │            [Verification Badge]               │      ║
║  │                                               │      ║
║  │  Tags: [Years] [Regulatory] [Species] ...     │      ║
║  └───────────────────────────────────────────────┘      ║
║                                                          ║
║  ┌────────────────────┐  ┌──────────────────────┐       ║
║  │ SECTION 2: DOMAINS  │  │ SECTION 3: SUMMARY   │       ║
║  │                     │  │                      │       ║
║  │ ┌─────────────────┐│  │ Organization          │       ║
║  │ │                 ││  │ • Title 1             │       ║
║  │ │ [BioCred Experience  ││  │ • Title 2             │       ║
║  │ │  Visualization  ││  │                      │       ║
║  │ │ — coming later] ││  │ Years Experience      │       ║
║  │ │                 ││  │ Location              │       ║
║  │ └─────────────────┘│  │                      │       ║
║  │                     │  │ Taxonomic Focus Tags  │       ║
║  │ Domain summaries:   │  │ [Avian] [Reptile]    │       ║
║  │ • Field: scope      │  │                      │       ║
║  │ • Regulatory: scope │  │ [Send Inquiry]       │       ║
║  │ • Academic: scope   │  │ [Share] [Print]      │       ║
║  │ • Species: scope    │  │                      │       ║
║  │ • Leadership: scope │  │ Organization Link     │       ║
║  └────────────────────┘  └──────────────────────┘       ║
║                                                          ║
║  ┌───────────────────────────────────────────────┐      ║
║  │  SECTION 4: CREDENTIAL HISTORY                │      ║
║  │                                               │      ║
║  │  Credential    Authority    Year    Status     │      ║
║  │  ──────────────────────────────────────       │      ║
║  │  M.S. Wildlife  UC Davis    2012   ✓ Verified │      ║
║  │  B.S. Ecology   CSU Long    2009   ✓ Verified │      ║
║  │  CEQA Cert      State Bd    2014   ○ Pending  │      ║
║  │                                               │      ║
║  │  [+ Credential Details & Documents (N)]       │      ║
║  └───────────────────────────────────────────────┘      ║
║                                                          ║
║  ┌───────────────────────────────────────────────┐      ║
║  │  SECTION 5: EXPERIENCE SUMMARY                │      ║
║  │                                               │      ║
║  │  Field Experience                             │      ║
║  │  • 28 CEQA/ESA buffer zone surveys (Lead)     │      ║
║  │  • Biological monitoring, 12+ projects        │      ║
║  │                                               │      ║
║  │  Species Depth                                │      ║
║  │  • 18 protected/sensitive taxa documented     │      ║
║  │                                               │      ║
║  │  (continues for all 5 domains)                │      ║
║  └───────────────────────────────────────────────┘      ║
║                                                          ║
║  ┌───────────────────────────────────────────────┐      ║
║  │  SECTION 6: RECENT PROJECTS                   │      ║
║  │  2023 · CEQA burrowing owl monitoring, CA     │      ║
║  │  2022 · CESA-listed amphibian surveys, CA     │      ║
║  └───────────────────────────────────────────────┘      ║
║                                                          ║
║  ┌───────────────────────────────────────────────┐      ║
║  │  SECTION 7: DOCUMENTATION & DOWNLOADS         │      ║
║  │  [Download CV / PDF Summary]                  │      ║
║  │  Disclaimer: Domains represent documented     │      ║
║  │  experience; no endorsement implied.          │      ║
║  └───────────────────────────────────────────────┘      ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║  FOOTER: About | FAQ | Privacy | Terms | Contact        ║
║  © 2026 BioCred Registry. All rights reserved.          ║
╚══════════════════════════════════════════════════════════╝
```

---

## Verification Badge Display Rules

| Profile Status | Badge Display |
|---------------|---------------|
| verified | ✓ VERIFIED (green shield) |
| partial | ◉ PARTIAL (amber indicator) |
| pending_review | ○ PENDING (gray) |
| under_verification | ○ UNDER REVIEW (gray) |
| submitted | No badge shown |
| rejected | Profile not displayed publicly |

---

## Neutrality Constraints

- No "star ratings" or score displays
- No "top" or "recommended" labels
- No comparative positioning between profiles
- Domain summaries are factual descriptions only
- Disclaimer appears on every profile page
