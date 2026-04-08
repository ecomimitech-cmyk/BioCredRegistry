"""
Tests for BioCred Profile Insights Generator.
Verifies neutral language, bullet count bounds, and rule-based output.
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from pipeline.profile_insights import generate_insights, _mean_weights, _sorted_axes


class TestMeanWeights(unittest.TestCase):
    def test_empty_units(self):
        m = _mean_weights([])
        for a in ["KR", "LOC", "SHS", "FAP", "RP"]:
            self.assertAlmostEqual(m[a], 0.2, places=2)

    def test_single_unit(self):
        u = [{"domain_weights": {"KR": 0.6, "LOC": 0.1, "SHS": 0.1, "FAP": 0.1, "RP": 0.1}}]
        self.assertAlmostEqual(_mean_weights(u)["KR"], 0.6, places=2)

    def test_two_units_average(self):
        units = [
            {"domain_weights": {"KR": 0.8, "LOC": 0.05, "SHS": 0.05, "FAP": 0.05, "RP": 0.05}},
            {"domain_weights": {"KR": 0.2, "LOC": 0.2, "SHS": 0.2, "FAP": 0.2, "RP": 0.2}},
        ]
        self.assertAlmostEqual(_mean_weights(units)["KR"], 0.5, places=2)

    def test_sorted_axes(self):
        m = {"KR": 0.1, "LOC": 0.5, "SHS": 0.05, "FAP": 0.3, "RP": 0.05}
        r = _sorted_axes(m)
        self.assertEqual(r[0], "LOC")
        self.assertEqual(r[1], "FAP")


FIELD = {"evidence_units": [
    {"domain_weights": {"KR": 0.04, "LOC": 0.08, "SHS": 0.16, "FAP": 0.62, "RP": 0.10},
     "intensity_weight": 0.85,
     "contexts": {"species_interaction_modes": ["survey", "monitoring"]}},
    {"domain_weights": {"KR": 0.03, "LOC": 0.07, "SHS": 0.22, "FAP": 0.55, "RP": 0.13},
     "intensity_weight": 0.72,
     "contexts": {"species_interaction_modes": ["capture", "handling"]}},
    {"domain_weights": {"KR": 0.06, "LOC": 0.12, "SHS": 0.14, "FAP": 0.58, "RP": 0.10},
     "intensity_weight": 0.65,
     "contexts": {"working_environments": ["hydrologic_systems"]}},
    {"domain_weights": {"KR": 0.05, "LOC": 0.09, "SHS": 0.18, "FAP": 0.56, "RP": 0.12},
     "intensity_weight": 0.90,
     "contexts": {"species_interaction_modes": ["survey"],
                  "regulatory_interactions": ["wildlife_agency_coordination"]}},
]}

REG = {"evidence_units": [
    {"domain_weights": {"KR": 0.12, "LOC": 0.18, "SHS": 0.04, "FAP": 0.08, "RP": 0.58},
     "intensity_weight": 0.90,
     "contexts": {"regulatory_interactions": ["environmental_review_coordination"]}},
    {"domain_weights": {"KR": 0.08, "LOC": 0.22, "SHS": 0.05, "FAP": 0.10, "RP": 0.55},
     "intensity_weight": 0.80,
     "contexts": {"regulatory_interactions": ["interagency_consultation",
                  "water_boards_coordination", "wildlife_agency_coordination"]}},
    {"domain_weights": {"KR": 0.15, "LOC": 0.14, "SHS": 0.06, "FAP": 0.12, "RP": 0.53},
     "intensity_weight": 0.70,
     "contexts": {"regulatory_interactions": ["flood_control_coordination"]}},
]}

UNIFORM = {"evidence_units": [
    {"domain_weights": {"KR": 0.2, "LOC": 0.2, "SHS": 0.2, "FAP": 0.2, "RP": 0.2},
     "intensity_weight": 0.5, "contexts": {}},
    {"domain_weights": {"KR": 0.2, "LOC": 0.2, "SHS": 0.2, "FAP": 0.2, "RP": 0.2},
     "intensity_weight": 0.5, "contexts": {}},
]}

EMPTY = {"evidence_units": []}


class TestGenerateInsights(unittest.TestCase):
    def test_returns_list(self):
        self.assertIsInstance(generate_insights(FIELD), list)

    def test_bullet_count_bounds(self):
        r = generate_insights(FIELD)
        self.assertGreaterEqual(len(r), 1)
        self.assertLessEqual(len(r), 6)

    def test_field_mentions_abp(self):
        self.assertIn("Field & Applied Practice", " ".join(generate_insights(FIELD)))

    def test_field_significant(self):
        self.assertIn("significantly concentrated", generate_insights(FIELD)[0])

    def test_reg_mentions_gov(self):
        self.assertIn("Regulation & Policy", " ".join(generate_insights(REG)))

    def test_reg_breadth(self):
        c = " ".join(generate_insights(REG)).lower()
        self.assertIn("regulatory interaction", c)

    def test_empty_fallback(self):
        r = generate_insights(EMPTY)
        self.assertEqual(len(r), 1)
        self.assertIn("Insufficient", r[0])

    def test_uniform_distributed(self):
        self.assertIn("distributed", generate_insights(UNIFORM)[0].lower())

    def test_species_in_field(self):
        self.assertIn("species interaction", " ".join(generate_insights(FIELD)).lower())

    def test_environment_diversity(self):
        c = " ".join(generate_insights(FIELD)).lower()
        self.assertTrue("hydrologic" in c or "environment" in c or "system" in c)


class TestNeutralLanguage(unittest.TestCase):
    FORBIDDEN = ["strong", "weak", "high", "low", "better",
                 "advanced", "best", "worst", "score", "rank"]

    def test_no_forbidden_words(self):
        payloads = [
            FIELD, REG,
            {"evidence_units": [
                {"domain_weights": {"KR": 0.6, "LOC": 0.1, "SHS": 0.1, "FAP": 0.12, "RP": 0.08},
                 "intensity_weight": 0.8,
                 "contexts": {"methods_tools": ["statistics_modeling"]}}]},
        ]
        for p in payloads:
            for bullet in generate_insights(p):
                for f in self.FORBIDDEN:
                    self.assertNotIn(f, bullet.lower().split(),
                                     f"'{f}' in: {bullet}")


class TestEdgeCases(unittest.TestCase):
    def test_no_contexts(self):
        p = {"evidence_units": [
            {"domain_weights": {"KR": 0.2, "LOC": 0.2, "SHS": 0.2, "FAP": 0.2, "RP": 0.2},
             "intensity_weight": 0.5, "contexts": {}}]}
        self.assertGreaterEqual(len(generate_insights(p)), 1)

    def test_rich_contexts(self):
        p = {"evidence_units": [
            {"domain_weights": {"KR": 0.5, "LOC": 0.1, "SHS": 0.15, "FAP": 0.15, "RP": 0.1},
             "intensity_weight": 0.8,
             "contexts": {
                 "species_interaction_modes": ["survey", "capture", "handling", "monitoring"],
                 "regulatory_interactions": ["wildlife_agency_coordination",
                     "environmental_review_coordination", "water_boards_coordination",
                     "interagency_consultation"],
                 "working_environments": ["hydrologic_systems",
                     "terrestrial_natural_systems", "coastal_marine_systems"]}}]}
        r = generate_insights(p)
        self.assertGreaterEqual(len(r), 4)
        self.assertLessEqual(len(r), 6)

    def test_missing_weights(self):
        p = {"evidence_units": [{"intensity_weight": 0.5, "contexts": {}}]}
        self.assertGreaterEqual(len(generate_insights(p)), 1)

    def test_sparse_gaps(self):
        p = {"evidence_units": [
            {"domain_weights": {"KR": 0.9, "LOC": 0.025, "SHS": 0.025, "FAP": 0.025, "RP": 0.025},
             "intensity_weight": 0.8, "contexts": {}}]}
        self.assertIn("sparse", " ".join(generate_insights(p)).lower())


if __name__ == "__main__":
    unittest.main()
