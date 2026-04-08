"""
BioCred Pipeline — Unit tests for CV Parser and Engagement Extractor.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cv_parser import (
    parse_cv, extract_text, clean_text, extract_header_info,
    find_section_boundaries, split_into_sections, PAGE_ARTIFACT_PATTERNS,
)
from engagement_extractor import (
    extract_year_range, extract_role_and_org, clean_bullet,
    parse_engagement_block, extract_engagements, extract_credentials,
    extract_evidence_units,
)

PASS = 0
FAIL = 0

TESTS_DIR = Path(__file__).parent
SAMPLE_CV = str(TESTS_DIR / "sample_cv.txt")
SAMPLE_MINIMAL = TESTS_DIR / "sample_cv_minimal.txt"
SAMPLE_COMPLEX = TESTS_DIR / "sample_cv_complex.txt"


def test(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


print("=" * 60)
print("BioCred — Parser & Extractor Unit Tests")
print("=" * 60)

# ── Parser: parse_cv structure ──
print("\n[Parser] parse_cv structure")
parsed = parse_cv(SAMPLE_CV)
expected_keys = {"source_file", "header", "sections_found", "sections",
                 "raw_text", "total_characters", "total_lines"}
test("parse_cv returns dict with expected keys",
     isinstance(parsed, dict) and expected_keys.issubset(parsed.keys()))

# ── Parser: Header extraction ──
print("\n[Parser] Header extraction")
test("Name detected from sample CV",
     len(parsed["header"].get("name", "")) > 3)

# ── Parser: Section detection ──
print("\n[Parser] Section detection")
standard = {"employment", "education", "certifications", "publications", "skills"}
test("All 5 standard sections found",
     standard.issubset(set(parsed["sections_found"])))

# ── Parser: Combined headers ──
print("\n[Parser] Combined headers")
combined_text = "Education and Certifications"
boundaries = find_section_boundaries(combined_text + "\n\nSome content")
test("Education and Certifications maps to correct section",
     any(b["section"] == "education" for b in boundaries))

# ── Parser: Artifact removal ──
print("\n[Parser] Artifact removal")
with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
    f.write(b"JANE DOE\npage 1 of 2\nExperience\nWorked at CDFW.\n")
    f.flush()
    p = parse_cv(f.name)
    Path(f.name).unlink()
test("Page numbers stripped", "page 1" not in p.get("raw_text", ""))
test("Content preserved", "Worked at CDFW" in p.get("raw_text", ""))

# ── Parser: Clean text ──
print("\n[Parser] Clean text")
dirty = "Header\npage 2 of 3\n- 5 -\nContent here"
cleaned = clean_text(dirty)
test("No artifact patterns in cleaned output",
     not any(p.match(line) for p in PAGE_ARTIFACT_PATTERNS
             for line in cleaned.split("\n") if line.strip()))

# ── Parser: Section boundaries ──
print("\n[Parser] Section boundaries")
empty_text = "Employment\n\n\n\nEducation\nContent"
sects = split_into_sections(empty_text)
test("Empty/short lines skipped in section boundaries",
     "education" in sects and len(sects["education"]) > 0)

long_line = "A" * 85
test("Long lines (>80 chars) not treated as section headers",
     len(find_section_boundaries(long_line)) == 0)

period_line = "This is a long sentence that ends with a period and has more than forty characters."
test("Lines ending with period + >40 chars not treated as section headers",
     len(find_section_boundaries(period_line)) == 0)

bullet_line = "- Conducted surveys in the field"
test("Bullet-prefixed lines not treated as section headers",
     len(find_section_boundaries(bullet_line)) == 0)

# ── Parser: Unsupported file type ──
print("\n[Parser] Unsupported file type")
with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
    f.write(b"dummy")
    f.flush()
    try:
        extract_text(f.name)
        raised = False
    except ValueError:
        raised = True
    Path(f.name).unlink()
test("Unsupported file type raises ValueError", raised)

# ── Parser: Minimal CV fallback ──
print("\n[Parser] Minimal CV fallback")
if SAMPLE_MINIMAL.exists():
    p_min = parse_cv(str(SAMPLE_MINIMAL))
    test("Fallback to unclassified section",
         "unclassified" in p_min["sections_found"])

# ── Parser: Complex CV combined header ──
print("\n[Parser] Complex CV combined header")
if SAMPLE_COMPLEX.exists():
    p_complex = parse_cv(str(SAMPLE_COMPLEX))
    test("Combined header detected",
         "education" in p_complex["sections_found"] or
         "certifications" in p_complex["sections_found"])

# ── Extractor: extract_year_range ──
print("\n[Extractor] extract_year_range")
test("2018–Present → (2018, 2026)", extract_year_range("2018–Present") == (2018, 2026))
test("2014-2018 → (2014, 2018)", extract_year_range("2014-2018") == (2014, 2018))
test("2020 → (2020, 2020)", extract_year_range("2020") == (2020, 2020))
test("January 2018 – December 2020 → (2018, 2020)",
     extract_year_range("January 2018 – December 2020") == (2018, 2020))
test("Spring 2015 – Fall 2017 → (2015, 2017)",
     extract_year_range("Spring 2015 – Fall 2017") == (2015, 2017))
test("Empty string → (None, None)", extract_year_range("") == (None, None))
test("2018–Ongoing → (2018, 2026)", extract_year_range("2018–Ongoing") == (2018, 2026))

# ── Extractor: extract_role_and_org ──
print("\n[Extractor] extract_role_and_org")
role1, org1 = extract_role_and_org("Environmental Scientist | CDFW | 2018–Present")
test("Role contains Environmental Scientist", "Environmental Scientist" in role1)
test("Org contains CDFW", "CDFW" in org1)
role2, org2 = extract_role_and_org("Research Assistant at Stanford University")
test("Org contains Stanford", "Stanford" in org2)

# ── Extractor: clean_bullet ──
print("\n[Extractor] clean_bullet")
test("- Conducted surveys → Conducted surveys",
     clean_bullet("- Conducted surveys") == "Conducted surveys")
test("• Managed team → Managed team", clean_bullet("• Managed team") == "Managed team")
test("1. Led field work → Led field work", clean_bullet("1. Led field work") == "Led field work")
test("a) Prepared reports → Prepared reports",
     clean_bullet("a) Prepared reports") == "Prepared reports")

# ── Extractor: extract_engagements ──
print("\n[Extractor] extract_engagements")
engs = extract_engagements(parsed)
test("At least 2 engagements", len(engs) >= 2)
test("Engagement has role/start_year/end_year/description/bullets",
     engs and all(k in engs[0] for k in ["role", "start_year", "end_year", "description", "bullets"]))
test("Engagements have bullets list length > 0",
     all(len(e.get("bullets", [])) > 0 for e in engs))

# ── Extractor: parse_engagement_block ──
print("\n[Extractor] parse_engagement_block")
block = "Scientist | Org | 2018-2020\n- Bullet one\n- Bullet two"
eng_block = parse_engagement_block(block)
test("parse_engagement_block preserves individual bullets",
     eng_block and len(eng_block.get("bullets", [])) >= 2)

# ── Extractor: extract_credentials ──
print("\n[Extractor] extract_credentials")
creds = extract_credentials(parsed)
test("At least 2 credentials", len(creds) >= 2)
test("Credential has type/title/date_awarded",
     all(all(k in c for k in ["type", "title", "date_awarded"]) for c in creds))

# ── Extractor: Credential type detection ──
print("\n[Extractor] Credential type detection")
mock_certs = {"sections": {"certifications": "Professional License in Biology, 2020\n"
                                             "Wetland Permit and Authorization, 2019"}}
mock_creds = extract_credentials(mock_certs)
test("License type for lines containing license",
     any(c.get("type") == "license" for c in mock_creds))
test("Permit type for lines containing permit",
     any(c.get("type") == "permit" for c in mock_creds))

# ── Extractor: extract_evidence_units ──
print("\n[Extractor] extract_evidence_units")
units = extract_evidence_units(parsed)
test("More units than engagements", len(units) > len(engs))
cred_units = [u for u in units if u.get("is_credential")]
test("Evidence units from credentials have is_credential=True", len(cred_units) > 0)
ids = [u["id"] for u in units]
test("Evidence unit IDs are unique", len(ids) == len(set(ids)))
required = {"id", "source", "time", "text", "parent_role"}
test("Each evidence unit has required fields",
     all(required.issubset(u.keys()) for u in units))

# ── Results ──
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print("=" * 60)

sys.exit(1 if FAIL > 0 else 0)
