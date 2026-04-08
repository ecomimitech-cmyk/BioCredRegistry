"""
BioCred Pipeline — Step 3: Engagement Extractor
Converts parsed CV sections into structured engagement records
and granular evidence units (bullet-level).
Handles diverse date formats, role/org extraction, sub-bullets.
"""

import json
import re
from pathlib import Path


MONTH_NAMES = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

SEASON_NAMES = r"(?:spring|summer|fall|autumn|winter)"

YEAR_RANGE_PATTERN = re.compile(
    r"(\d{4})\s*[-–—to]+\s*(\d{4}|[Pp]resent|[Cc]urrent|[Oo]ngoing)"
)

MONTH_YEAR_RANGE = re.compile(
    rf"(?i)({MONTH_NAMES})\s+(\d{{4}})\s*[-–—to]+\s*"
    rf"(?:({MONTH_NAMES})\s+)?(\d{{4}}|[Pp]resent|[Cc]urrent)"
)

SEASON_YEAR_RANGE = re.compile(
    rf"(?i)({SEASON_NAMES})\s+(\d{{4}})\s*[-–—to]+\s*"
    rf"(?:({SEASON_NAMES})\s+)?(\d{{4}}|[Pp]resent|[Cc]urrent)"
)

SINGLE_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

PRESENT_WORDS = {"present", "current", "ongoing"}

ORG_SEPARATORS = re.compile(r"\s*[|·•–—,]\s*")
ORG_PREPOSITIONS = re.compile(
    r"(?i)\b(?:at|with|for)\s+(.+?)(?:\s*[|,]|\s*$)"
)

BULLET_PATTERN = re.compile(r"^\s*[-•▪◦*→‣]\s*")
NUMBERED_BULLET = re.compile(r"^\s*\d+[.)]\s*")
LETTERED_BULLET = re.compile(r"^\s*[a-z][.)]\s*", re.IGNORECASE)


def normalize_end_year(text: str) -> int:
    if text.lower() in PRESENT_WORDS:
        return 2026
    return int(text)


def extract_year_range(text: str) -> tuple:
    month_match = MONTH_YEAR_RANGE.search(text)
    if month_match:
        start = int(month_match.group(2))
        end = normalize_end_year(month_match.group(4))
        return start, end

    season_match = SEASON_YEAR_RANGE.search(text)
    if season_match:
        start = int(season_match.group(2))
        end = normalize_end_year(season_match.group(4))
        return start, end

    match = YEAR_RANGE_PATTERN.search(text)
    if match:
        start = int(match.group(1))
        end = normalize_end_year(match.group(2))
        return start, end

    years = [int(m.group(0)) for m in SINGLE_YEAR_PATTERN.finditer(text)]
    if years:
        return min(years), max(years)

    return None, None


def extract_role_and_org(title_line: str) -> tuple:
    """Extract role and organization from a title line."""
    for prep_match in ORG_PREPOSITIONS.finditer(title_line):
        org = prep_match.group(1).strip()
        role = title_line[:prep_match.start()].strip()
        return role, org

    parts = ORG_SEPARATORS.split(title_line)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 2:
        year_positions = []
        for i, p in enumerate(parts):
            if SINGLE_YEAR_PATTERN.search(p):
                year_positions.append(i)

        non_year = [
            p for i, p in enumerate(parts)
            if i not in year_positions
        ]
        if len(non_year) >= 2:
            return non_year[0], non_year[1]
        elif len(non_year) == 1:
            return non_year[0], ""

    return parts[0] if parts else title_line, ""


def clean_bullet(line: str) -> str:
    """Strip bullet markers from a line."""
    cleaned = BULLET_PATTERN.sub("", line)
    cleaned = NUMBERED_BULLET.sub("", cleaned)
    cleaned = LETTERED_BULLET.sub("", cleaned)
    return cleaned.strip()


def is_sub_bullet(line: str) -> bool:
    """Detect indented sub-bullets (4+ spaces or tab before marker)."""
    return bool(re.match(r"^(\s{4,}|\t)\s*[-•▪◦*]", line))


def parse_engagement_block(block: str) -> dict:
    lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
    if not lines:
        return None

    title_line = lines[0]
    start_year, end_year = extract_year_range(block)
    role, organization = extract_role_and_org(title_line)

    bullets = []
    for line in lines[1:]:
        cleaned = clean_bullet(line)
        if cleaned and not YEAR_RANGE_PATTERN.match(cleaned):
            bullets.append(cleaned)

    return {
        "role": role,
        "organization": organization,
        "start_year": start_year,
        "end_year": end_year,
        "description": " ".join(bullets),
        "bullets": bullets,
    }


def split_employment_into_blocks(text: str) -> list:
    lines = text.split("\n")
    blocks = []
    current_block = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            continue

        has_year = bool(YEAR_RANGE_PATTERN.search(stripped))
        has_month_year = bool(MONTH_YEAR_RANGE.search(stripped))
        has_upper = stripped[0].isupper() if stripped else False

        if (has_year or has_month_year) and has_upper and current_block:
            blocks.append("\n".join(current_block))
            current_block = [stripped]
        else:
            current_block.append(stripped)

    if current_block:
        blocks.append("\n".join(current_block))

    return blocks


def extract_engagements(parsed_cv: dict) -> list:
    sections = parsed_cv.get("sections", {})
    employment_text = sections.get("employment", "")

    if not employment_text:
        for key in ["experience", "work_history", "projects",
                     "unclassified"]:
            if key in sections:
                employment_text = sections[key]
                break

    if not employment_text:
        return []

    blocks = split_employment_into_blocks(employment_text)
    engagements = []

    for block in blocks:
        eng = parse_engagement_block(block)
        if eng and eng["role"]:
            engagements.append(eng)

    return engagements


def extract_credentials(parsed_cv: dict) -> list:
    credentials = []
    sections = parsed_cv.get("sections", {})

    edu_text = sections.get("education", "")
    if edu_text:
        for line in edu_text.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            years = SINGLE_YEAR_PATTERN.findall(line)
            year = int(max(years)) if years else None
            clean_title = re.sub(r"\b(19|20)\d{2}\b", "", line).strip()
            clean_title = clean_title.rstrip(",").strip()
            if clean_title:
                credentials.append({
                    "type": "degree",
                    "title": clean_title,
                    "issuing_body": "",
                    "date_awarded": year,
                })

    cert_text = sections.get("certifications", "")
    if cert_text:
        for line in cert_text.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            years = SINGLE_YEAR_PATTERN.findall(line)
            year = int(max(years)) if years else None

            cert_type = "certification"
            lower = line.lower()
            if "permit" in lower or "authorization" in lower:
                cert_type = "permit"
            elif "license" in lower or "licensed" in lower:
                cert_type = "license"
            elif "training" in lower or "course" in lower:
                cert_type = "training"

            clean_title = re.sub(r"\b(19|20)\d{2}\b", "", line).strip()
            clean_title = clean_bullet(clean_title).rstrip(",").strip()
            if clean_title:
                credentials.append({
                    "type": cert_type,
                    "title": clean_title,
                    "issuing_body": "",
                    "date_awarded": year,
                })

    return credentials


def extract_evidence_units(parsed_cv: dict) -> list:
    """Extract granular evidence units (bullet-level) from parsed CV."""
    engagements = extract_engagements(parsed_cv)
    credentials = extract_credentials(parsed_cv)
    units = []

    for eng in engagements:
        role_slug = re.sub(r"[^a-z0-9]", "_", eng["role"][:25].lower())
        for i, bullet in enumerate(eng.get("bullets", [])):
            units.append({
                "id": f"ev_{role_slug}_{i}",
                "source": "cv",
                "time": {
                    "start_year": eng["start_year"],
                    "end_year": eng["end_year"],
                },
                "text": bullet,
                "parent_role": eng["role"],
                "parent_org": eng["organization"],
                "is_credential": False,
            })

    for i, cred in enumerate(credentials):
        cred_slug = re.sub(r"[^a-z0-9]", "_", cred["type"][:15].lower())
        units.append({
            "id": f"ev_{cred_slug}_{i}",
            "source": "cv",
            "time": {
                "start_year": cred.get("date_awarded"),
                "end_year": cred.get("date_awarded"),
            },
            "text": cred["title"],
            "parent_role": cred["type"],
            "parent_org": cred.get("issuing_body", ""),
            "is_credential": True,
        })

    return units


def process(parsed_cv_path: str, output_path: str = None):
    parsed_cv = json.loads(Path(parsed_cv_path).read_text())
    engagements = extract_engagements(parsed_cv)
    credentials = extract_credentials(parsed_cv)
    evidence_units = extract_evidence_units(parsed_cv)

    result = {
        "source": parsed_cv.get("source_file", ""),
        "engagements": engagements,
        "credentials": credentials,
        "evidence_units": evidence_units,
        "engagement_count": len(engagements),
        "credential_count": len(credentials),
        "evidence_unit_count": len(evidence_units),
    }

    out = output_path or "engagements.json"
    Path(out).write_text(
        json.dumps(result, indent=2, ensure_ascii=False)
    )
    print(f"Extracted {len(engagements)} engagements, "
          f"{len(credentials)} credentials, "
          f"{len(evidence_units)} evidence units → {out}")
    return result
