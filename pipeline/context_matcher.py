"""
BioCred Pipeline — Context Matcher
Maps evidence unit text to context categories from context_ontology_v1.json.
Calculates intensity_weight from documented proxies (duration, role scope).
Deterministic: same input always produces identical output.
No AI, no judgment — keyword detection only.
"""

import re

CONTEXT_DETECTION = {
    "regulatory_interactions": {
        "wildlife_agency_coordination": [
            "cdfw", "usfws", "fish and wildlife", "wildlife agency",
            "noaa fisheries", "nmfs", "fish & wildlife",
            "wildlife service", "wildlife department",
        ],
        "water_boards_coordination": [
            "water board", "water quality", "clean water act", "swrcb",
            "rwqcb", "npdes", "stormwater", "storm water permit",
        ],
        "flood_control_coordination": [
            "flood control", "fema", "usace", "army corps",
            "corps of engineers", "floodplain",
        ],
        "land_management_coordination": [
            "blm", "usfs", "forest service", "land management",
            "conservation easement", "land trust", "nps",
            "national park", "bureau of land",
        ],
        "infrastructure_permitting_coordination": [
            "caltrans", "department of transportation", "dot ",
            "infrastructure permit", "right-of-way", "row permit",
        ],
        "environmental_review_coordination": [
            "ceqa", "nepa", "environmental review",
            "environmental impact", "eis", "eir",
            "mitigated negative declaration", "mnd",
            "initial study", "categorical exemption",
            "environmental assessment",
        ],
        "interagency_consultation": [
            "interagency", "section 7", "section 10",
            "biological opinion", "formal consultation",
            "informal consultation", "conference opinion",
            "jeopardy", "critical habitat designation",
        ],
    },
    "working_environments": {
        "hydrologic_systems": [
            "wetland", "stream", "river", "watershed", "riparian",
            "lake", "pond", "aquatic", "creek", "marsh",
            "vernal pool", "floodplain", "drainage", "canal",
            "reservoir", "spring", "seep", "swamp", "bog",
        ],
        "terrestrial_natural_systems": [
            "forest", "grassland", "desert", "chaparral", "woodland",
            "scrub", "prairie", "savanna", "upland", "meadow",
            "alpine", "tundra", "dune", "canyon", "foothill",
        ],
        "coastal_marine_systems": [
            "coastal", "marine", "ocean", "estuary", "beach",
            "tidal", "intertidal", "kelp", "lagoon", "bay",
            "reef", "offshore", "nearshore", "shoreline",
        ],
        "managed_engineered_landscapes": [
            "construction", "development", "highway", "road",
            "pipeline", "utility", "solar", "wind farm",
            "mitigation site", "levee", "dam", "reservoir",
            "transmission line", "substation", "landfill",
        ],
        "transitional_ecotonal_systems": [
            "ecotone", "edge habitat", "buffer zone", "transition",
            "urban-wildland interface", "wildlife corridor",
        ],
    },
    "species_interaction_modes": {
        "observation": [
            "observed", "visual survey", "sighting",
            "visual encounter", "incidental observation",
        ],
        "survey": [
            "survey", "surveying", "surveyed", "census",
            "point count", "transect survey", "protocol survey",
            "presence/absence", "inventory",
        ],
        "monitoring": [
            "monitoring", "monitored", "long-term monitoring",
            "annual monitoring", "population monitoring",
            "nest monitoring", "telemetry monitoring",
        ],
        "capture": [
            "capture", "captured", "trap", "trapping",
            "mist net", "pit trap", "funnel trap",
            "mark-recapture", "live trap",
        ],
        "handling": [
            "handling", "handled", "restrain", "processing",
            "banding", "tagging", "blood sampling", "venipuncture",
        ],
        "relocation": [
            "relocation", "relocated", "translocation",
            "translocated", "salvage", "exclusion",
        ],
        "oversight": [
            "oversight", "compliance check", "site inspection",
            "clearance", "pre-construction clearance",
            "construction monitoring", "biological monitor",
        ],
    },
    "project_types": {
        "infrastructure": [
            "infrastructure", "construction project", "highway",
            "bridge", "pipeline project", "utility project",
            "housing development", "transportation",
            "road widening", "interchange",
        ],
        "restoration_implementation": [
            "restoration", "revegetation", "habitat enhancement",
            "mitigation bank", "habitat creation",
            "stream restoration", "wetland creation",
        ],
        "mitigation_compliance": [
            "mitigation", "compliance", "compensatory",
            "permit condition", "avoidance", "minimization",
            "conservation measure", "biological opinion compliance",
        ],
        "monitoring_program": [
            "monitoring program", "baseline survey",
            "annual monitoring", "long-term study",
            "population study", "status survey",
        ],
        "research_program": [
            "research", "study", "experiment", "thesis",
            "dissertation", "grant", "nsf", "academic research",
            "peer-reviewed", "publication",
        ],
        "environmental_review_support": [
            "environmental review", "biological assessment",
            "ceqa", "nepa", "technical report",
            "environmental document", "biological evaluation",
        ],
    },
    "methods_tools": {
        "gis": [
            "gis", "arcgis", "qgis", "spatial analysis",
            "geospatial", "remote sensing", "lidar",
            "aerial imagery", "gps mapping",
        ],
        "statistics_modeling": [
            "statistical", "statistics", "modeling",
            "r programming", "anova", "regression",
            "data analysis", "python", "spss", "sas",
            "population modeling", "occupancy modeling",
        ],
        "lab_methods": [
            "laboratory", "lab ", "genetics", "dna", "pcr",
            "specimen", "microscopy", "histology",
            "tissue sample", "blood sample",
        ],
        "field_instrumentation": [
            "telemetry", "camera trap", "data logger",
            "gps unit", "radio collar", "pit tag",
            "acoustic monitor", "weather station",
            "trail camera", "bat detector",
        ],
        "report_writing": [
            "report", "document preparation", "authored",
            "prepared", "drafted", "technical report",
            "biological assessment", "management plan",
        ],
        "database_management": [
            "database", "data management", "data entry",
            "spreadsheet", "cnddb", "access database",
            "data collection", "field data",
        ],
    },
}

LEADER_KEYWORDS = [
    "lead", "senior", "principal", "director", "chief",
    "head", "supervisor",
]
MANAGER_KEYWORDS = [
    "manage", "supervise", "coordinate", "oversee",
    "administer", "facilitate",
]


def match_contexts(text: str) -> dict:
    """Match evidence unit text against context categories.
    Returns dict of matched context category IDs."""
    text_lower = text.lower()
    matched = {}

    for category, terms in CONTEXT_DETECTION.items():
        hits = []
        for term_id, keywords in terms.items():
            for kw in keywords:
                if kw in text_lower:
                    hits.append(term_id)
                    break
        if hits:
            matched[category] = sorted(set(hits))

    return matched


def calculate_intensity(
    start_year: int,
    end_year: int,
    role_text: str = "",
    is_credential: bool = False,
) -> float:
    """Deterministic intensity_weight from documented proxies.
    Duration + role scope. No judgment — only data-derived."""
    if start_year is None or end_year is None:
        return 0.5

    duration = max(1, end_year - start_year)
    base = 0.5
    duration_bonus = min(0.4, duration * 0.05)

    if is_credential:
        return round(max(0.3, base + duration_bonus * 0.5 - 0.1), 1)

    role_lower = role_text.lower()
    scope_bonus = 0.0
    if any(w in role_lower for w in LEADER_KEYWORDS):
        scope_bonus = 0.2
    elif any(w in role_lower for w in MANAGER_KEYWORDS):
        scope_bonus = 0.1

    return round(min(1.5, base + duration_bonus + scope_bonus), 1)
