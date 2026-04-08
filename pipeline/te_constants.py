"""
BioCred Translation Engine — Constants & Lookup Tables
Alexander Funk's TE Spec v1.0, Sections 3-4.
All modifier dictionaries are FIXED — no ML, no inference.

Domain names per BPP_v1.0:
  KR  = Knowledge & Research
  LOC = Leadership & Operational Coordination
  SHS = Species & Habitat Specialization
  FAP = Field & Applied Practice
  RP  = Regulation & Policy
"""

TRANSLATION_VERSION = "TE_v1.0"
AXIS_ORDER = ["KR", "LOC", "SHS", "FAP", "RP"]

# ─── Section 3.1: Base Vectors by Phase-1 Domain ───

BASE_VECTORS = {
    "field_experience":       {"KR": 0.05, "LOC": 0.10, "SHS": 0.15, "FAP": 0.60, "RP": 0.10},
    "regulatory_experience":  {"KR": 0.10, "LOC": 0.15, "SHS": 0.05, "FAP": 0.10, "RP": 0.60},
    "academic_technical":     {"KR": 0.65, "LOC": 0.10, "SHS": 0.10, "FAP": 0.10, "RP": 0.05},
    "species_depth":          {"KR": 0.05, "LOC": 0.05, "SHS": 0.65, "FAP": 0.20, "RP": 0.05},
    "leadership_scope":       {"KR": 0.05, "LOC": 0.65, "SHS": 0.05, "FAP": 0.10, "RP": 0.15},
}

# ─── Section 3.2: Activity-Type Modifier Patterns ───

ACTIVITY_PATTERNS = [
    {
        "patterns": [
            r"ceqa", r"nepa", r"permit\s*draft", r"compliance\s*report",
            r"environmental\s*review", r"biological\s*assessment",
        ],
        "modifier": {"KR": 0.05, "LOC": 0.0, "SHS": -0.05, "FAP": -0.10, "RP": 0.20},
    },
    {
        "patterns": [
            r"agency\s*coordination", r"consultation", r"interagency",
            r"meetings", r"liaison",
        ],
        "modifier": {"KR": -0.10, "LOC": 0.15, "SHS": 0.0, "FAP": -0.10, "RP": 0.15},
    },
    {
        "patterns": [
            r"field\s*survey", r"monitoring", r"biological\s*monitor",
            r"construction\s*monitoring", r"habitat\s*assessment",
            r"delineation", r"inventory",
        ],
        "modifier": {"KR": -0.15, "LOC": 0.0, "SHS": 0.05, "FAP": 0.20, "RP": -0.10},
    },
    {
        "patterns": [
            r"species\s*handling", r"capture", r"relocation",
            r"translocation", r"mark.recapture", r"banding",
            r"mist\s*net", r"trapping",
        ],
        "modifier": {"KR": -0.10, "LOC": 0.0, "SHS": 0.20, "FAP": 0.10, "RP": -0.20},
    },
    {
        "patterns": [
            r"\bgis\b", r"statistic", r"modeling", r"laboratory",
            r"lab\s*method", r"\bpcr\b", r"genetic", r"microscopy",
            r"remote\s*sensing",
        ],
        "modifier": {"KR": 0.25, "LOC": 0.0, "SHS": -0.05, "FAP": -0.10, "RP": -0.10},
    },
    {
        "patterns": [
            r"project\s*manage", r"mentor", r"qa.?qc",
            r"team\s*lead", r"crew\s*supervis", r"training",
        ],
        "modifier": {"KR": -0.10, "LOC": 0.25, "SHS": 0.0, "FAP": -0.15, "RP": 0.10},
    },
]

# ─── Section 3.3: Role-Level Modifiers ───

ROLE_MODIFIERS = {
    "participant":             {"LOC": 0.00, "RP": 0.00, "KR": 0.00},
    "contributor":             {"LOC": 0.03, "RP": 0.02, "KR": 0.00},
    "lead":                    {"LOC": 0.08, "RP": 0.05, "KR": 0.00},
    "oversight":               {"LOC": 0.10, "RP": 0.10, "KR": 0.00},
    "principal_investigator":  {"LOC": 0.10, "RP": 0.00, "KR": 0.10},
}

# ─── Section 3.4: Species Interaction Mode Modifiers ───

SPECIES_MODE_MODIFIERS = {
    "observation":  {"FAP": 0.05, "SHS": 0.02},
    "survey":       {"FAP": 0.05, "SHS": 0.02},
    "monitoring":   {"FAP": 0.05, "SHS": 0.02},
    "capture":      {"SHS": 0.10, "FAP": 0.05},
    "handling":     {"SHS": 0.10, "FAP": 0.05},
    "relocation":   {"SHS": 0.10, "FAP": 0.05},
    "oversight":    {"RP": 0.05, "SHS": 0.05},
}

# ─── Section 4.1: Duration Factor ───

DURATION_BRACKETS = [
    (0.25, 0.35),
    (1.0,  0.55),
    (3.0,  0.75),
    (7.0,  0.90),
]
DURATION_MAX = 1.00

# ─── Section 4.2: Verification Factor ───

VERIFICATION_FACTORS = {
    "verified":            1.00,
    "partial":             0.70,
    "pending":             0.50,
    "pending_review":      0.50,
    "under_verification":  0.50,
    "submitted":           0.50,
    "rejected":            0.00,
    "self_reported":       0.40,
}

# ─── Section 4.3: Role Intensity Factor ───

ROLE_INTENSITY_FACTORS = {
    "participant":            0.70,
    "contributor":            0.85,
    "lead":                   1.00,
    "oversight":              1.03,
    "principal_investigator": 1.05,
}
