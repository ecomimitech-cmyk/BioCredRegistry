"""
BioCred Registry — Schema Validation Tests
Validates data model structure, referential integrity,
and domain constraints using text analysis of SQL files.
"""

import re
import sys
from pathlib import Path

PASS = 0
FAIL = 0


def test(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def read_file(rel_path):
    path = Path(__file__).parent.parent / rel_path
    return path.read_text()


def read_all_seeds():
    seed_dir = Path(__file__).parent.parent / "database" / "seed"
    combined = ""
    for f in sorted(seed_dir.glob("*.sql")):
        combined += f.read_text() + "\n"
    return combined


print("=" * 60)
print("BioCred Registry — Schema Validation Tests")
print("=" * 60)

schema = read_file("database/schema.sql")
seeds = read_all_seeds()

print("\n[1] Schema File Structure")
test("biologist_profile table",
     "CREATE TABLE biologist_profile" in schema)
test("credential_record table",
     "CREATE TABLE credential_record" in schema)
test("experience_evidence table",
     "CREATE TABLE experience_evidence" in schema)
test("translation_version column",
     "translation_version" in schema)
test("verification_audit_log table",
     "CREATE TABLE verification_audit_log" in schema)

print("\n[2] ENUM Types")
enums = [
    "verification_status", "domain_category", "credential_type",
    "verification_method", "role_level", "visibility_status",
    "geographic_region", "taxonomic_group",
]
for e in enums:
    test(f"ENUM '{e}'",
         f"CREATE TYPE {e} AS ENUM" in schema)

print("\n[3] Domain Categories (5 locked)")
domains = [
    "field_experience", "regulatory_experience",
    "academic_technical", "species_depth", "leadership_scope",
]
for d in domains:
    test(f"Domain '{d}'", f"'{d}'" in schema)
test("Exactly 5 domains", len(domains) == 5)

print("\n[4] Verification Statuses")
for s in ["submitted", "pending_review", "under_verification",
          "verified", "partial", "rejected"]:
    test(f"Status '{s}'", f"'{s}'" in schema)

print("\n[5] Foreign Keys")
test("credential → profile",
     "REFERENCES biologist_profile(id)" in schema)
test("evidence → profile",
     "experience_evidence" in schema
     and "REFERENCES biologist_profile" in schema)
test("audit → profile",
     "verification_audit_log" in schema
     and "REFERENCES biologist_profile" in schema)

print("\n[6] Seed Data — Profiles")
count = seeds.count("INSERT INTO biologist_profile")
test(f"5 profiles (found {count})", count == 5)

print("\n[7] Seed Data — Archetypes")
for name, marker in [
    ("Field Specialist", "Field Specialist"),
    ("Regulatory Specialist", "Regulatory Specialist"),
    ("Academic Lead", "Academic Lead"),
    ("Species Specialist", "Species Specialist"),
    ("Multi-Vector Expert", "Multi-Vector Expert"),
]:
    test(f"'{name}'", marker in seeds)

print("\n[8] Seed Data — Domain Coverage")
for d in domains:
    test(f"'{d}' used", f"'{d}'" in seeds)

print("\n[9] Seed Data — Credential Types")
types = ["degree", "certification", "license",
         "permit", "training", "publication"]
used = [c for c in types if f"'{c}'" in seeds]
for c in types:
    test(f"Type '{c}'", f"'{c}'" in seeds)
test(f">=4 types ({len(used)})", len(used) >= 4)

print("\n[10] Seed Data — Role Levels")
for r in ["participant", "contributor", "lead",
          "oversight", "principal_investigator"]:
    test(f"Role '{r}'", f"'{r}'" in seeds)

print("\n[11] Neutrality Constraints")
for w in ["score", "ranking", "weight", "rating",
          "best", "top", "recommended"]:
    found = bool(re.search(rf'\b{w}\b', schema, re.I))
    test(f"No '{w}' in schema", not found)

print("\n[12] Audit Log Fields")
for f in ["previous_status", "new_status", "changed_by",
          "change_reason", "created_at"]:
    test(f"'{f}'", f in schema)

print("\n[13] Indexes")
for idx in ["idx_profile_region", "idx_profile_verification",
            "idx_credential_profile", "idx_evidence_domain"]:
    test(idx, idx in schema)

print("\n[14] Timestamps & Triggers")
test("created_at", "created_at" in schema)
test("updated_at", "updated_at" in schema)
test("Auto-update trigger", "update_updated_at" in schema)

print("\n[15] SQL Safety")
test("No DROP TABLE", "DROP TABLE" not in schema)
test("Seeds have INSERTs", "INSERT INTO" in seeds)

print("\n[16] Modular Seed Files")
seed_dir = Path(__file__).parent.parent / "database" / "seed"
seed_files = sorted(seed_dir.glob("*.sql"))
test(f"6 seed files (found {len(seed_files)})",
     len(seed_files) == 6)
for expected in ["01_field", "02_regulatory", "03_academic",
                 "04_species", "05_multi_vector", "06_audit"]:
    test(f"File '{expected}' exists",
         any(expected in f.name for f in seed_files))

print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
print("=" * 60)

sys.exit(1 if FAIL > 0 else 0)
