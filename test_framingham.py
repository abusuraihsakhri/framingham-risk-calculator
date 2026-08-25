#!/usr/bin/env python3
"""
Tests for the Framingham Risk Score Calculator.

Covers:
  - Individual point components (age, cholesterol, HDL, BP, smoking, diabetes)
  - Full score calculation for male and female patients
  - Risk category classification
  - Edge cases (boundary ages, extreme values)
  - Input validation
  - CSV batch processing
"""
import csv
import json
import os
import tempfile
import unittest

from framingham import (
    calculate_framingham,
    calculate_points,
    points_to_risk,
    risk_category,
    assess_row,
    process_csv,
    _lookup_range,
    _age_group_key,
)


# ======================================================================
# Baseline: age=35 male gives 0 age pts; tc=150 gives 0; hdl=45 gives 0;
# sbp=110 untreated gives 0; non-smoker gives 0; non-diabetic gives 0.
# Total baseline = 0 for male.  For female age=40 gives 0, baseline = -1
# (hdl=45 -> 0 pts, but let's use hdl=45 which is in 40-49 -> 0 pts).
# ======================================================================

# Male baseline: age=35, tc=150, hdl=45, sbp=110, no smoke, no diabetes -> 0
M_BASE = dict(age=35, sex="male", total_cholesterol=150, hdl_cholesterol=45,
              systolic_bp=110, bp_treated=False, smoker=False, diabetic=False)

# Female baseline: age=40, tc=150, hdl=45, sbp=110, no smoke, no diabetes -> 0
F_BASE = dict(age=40, sex="female", total_cholesterol=150, hdl_cholesterol=45,
              systolic_bp=110, bp_treated=False, smoker=False, diabetic=False)


# ======================================================================
# Helper lookups
# ======================================================================

class TestLookupRange(unittest.TestCase):
    """Test the generic range-lookup helper."""

    def test_exact_lower_bound(self):
        table = [(0, 120, 0), (120, 130, 1), (130, 140, 2)]
        self.assertEqual(_lookup_range(120, table), 1)

    def test_mid_range(self):
        table = [(0, 120, 0), (120, 130, 1), (130, 140, 2)]
        self.assertEqual(_lookup_range(135, table), 2)

    def test_upper_open_ended(self):
        table = [(0, 120, 0), (120, 130, 1), (160, None, 4)]
        self.assertEqual(_lookup_range(200, table), 4)

    def test_below_all_ranges(self):
        table = [(120, 130, 1), (130, 140, 2)]
        # Falls through to last entry as fallback
        self.assertEqual(_lookup_range(50, table), 2)


class TestAgeGroupKey(unittest.TestCase):

    def test_youngest(self):
        self.assertEqual(_age_group_key(30), (30, 39))
        self.assertEqual(_age_group_key(39), (30, 39))

    def test_middle(self):
        self.assertEqual(_age_group_key(50), (50, 59))
        self.assertEqual(_age_group_key(59), (50, 59))

    def test_oldest(self):
        self.assertEqual(_age_group_key(70), (70, 79))
        self.assertEqual(_age_group_key(74), (70, 79))


# ======================================================================
# Risk category
# ======================================================================

class TestRiskCategory(unittest.TestCase):

    def test_low(self):
        self.assertEqual(risk_category(1), "Low")
        self.assertEqual(risk_category(9), "Low")

    def test_intermediate(self):
        self.assertEqual(risk_category(10), "Intermediate")
        self.assertEqual(risk_category(15), "Intermediate")
        self.assertEqual(risk_category(20), "Intermediate")

    def test_high(self):
        self.assertEqual(risk_category(21), "High")
        self.assertEqual(risk_category(56), "High")


# ======================================================================
# Points-to-risk lookup
# ======================================================================

class TestPointsToRisk(unittest.TestCase):

    def test_male_minimum(self):
        self.assertEqual(points_to_risk(-1, "male"), 1)

    def test_male_zero(self):
        self.assertEqual(points_to_risk(0, "male"), 1)

    def test_male_mid(self):
        self.assertEqual(points_to_risk(8, "male"), 9)
        self.assertEqual(points_to_risk(10, "male"), 14)

    def test_male_max_entry(self):
        self.assertEqual(points_to_risk(16, "male"), 47)

    def test_male_above_max(self):
        self.assertEqual(points_to_risk(17, "male"), 56)
        self.assertEqual(points_to_risk(20, "male"), 56)

    def test_female_minimum(self):
        self.assertEqual(points_to_risk(-9, "female"), 1)

    def test_female_mid(self):
        self.assertEqual(points_to_risk(0, "female"), 2)
        self.assertEqual(points_to_risk(8, "female"), 9)

    def test_female_max_entry(self):
        self.assertEqual(points_to_risk(15, "female"), 27)

    def test_female_above_max(self):
        self.assertEqual(points_to_risk(16, "female"), 30)
        self.assertEqual(points_to_risk(20, "female"), 30)


# ======================================================================
# MALE point calculations — individual components
# Each test uses the baseline (total=0) and varies ONE component.
# ======================================================================

class TestMaleAgePoints(unittest.TestCase):
    """Age points for male. Baseline uses tc=150, hdl=45, sbp=110, etc."""

    def test_age_30_34(self):
        # age=-1, rest=0 -> -1
        self.assertEqual(calculate_points(30, "male", 150, 45, 110, False, False, False), -1)
        self.assertEqual(calculate_points(34, "male", 150, 45, 110, False, False, False), -1)

    def test_age_35_39(self):
        # age=0, rest=0 -> 0
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, False, False, False), 0)
        self.assertEqual(calculate_points(39, "male", 150, 45, 110, False, False, False), 0)

    def test_age_40_44(self):
        self.assertEqual(calculate_points(42, "male", 150, 45, 110, False, False, False), 1)

    def test_age_50_54(self):
        self.assertEqual(calculate_points(52, "male", 150, 45, 110, False, False, False), 3)

    def test_age_60_64(self):
        self.assertEqual(calculate_points(62, "male", 150, 45, 110, False, False, False), 5)

    def test_age_70_74(self):
        self.assertEqual(calculate_points(72, "male", 150, 45, 110, False, False, False), 7)


class TestMaleCholesterolPoints(unittest.TestCase):
    """Total cholesterol points vary by age group. Use age=35 (age_pts=0)."""

    def test_low_tc(self):
        # age=35, tc=150 -> 0 (tc) + 0 (age) = 0
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, False, False, False), 0)

    def test_young_moderate_tc(self):
        # age=35 (<40 bracket), tc=170 -> 4 tc pts
        self.assertEqual(calculate_points(35, "male", 170, 45, 110, False, False, False), 4)

    def test_young_high_tc(self):
        # age=35 (<40 bracket), tc=250 -> 9 tc pts
        self.assertEqual(calculate_points(35, "male", 250, 45, 110, False, False, False), 9)

    def test_young_very_high_tc(self):
        # age=35 (<40 bracket), tc=290 -> 11 tc pts
        self.assertEqual(calculate_points(35, "male", 290, 45, 110, False, False, False), 11)

    def test_middle_age_moderate_tc(self):
        # age=45 (40-49 bracket), tc=210 -> 2 (age) + 5 (tc) = 7
        self.assertEqual(calculate_points(45, "male", 210, 45, 110, False, False, False), 7)

    def test_older_low_tc(self):
        # age=65 (60-69 bracket), tc=150 -> 6 (age) + 0 (tc) = 6
        self.assertEqual(calculate_points(65, "male", 150, 45, 110, False, False, False), 6)

    def test_oldest_high_tc(self):
        # age=72 (70-79 bracket), tc=290 -> 7 (age) + 1 (tc >=280 in 70-79) = 8
        self.assertEqual(calculate_points(72, "male", 290, 45, 110, False, False, False), 8)


class TestMaleHDLPoints(unittest.TestCase):
    """HDL points. Use age=35 (age_pts=0), tc=150 (tc_pts=0), sbp=110 (bp=0)."""

    def test_high_hdl(self):
        # hdl=65 -> -2 pts -> total = -2
        self.assertEqual(calculate_points(35, "male", 150, 65, 110, False, False, False), -2)

    def test_medium_high_hdl(self):
        # hdl=55 -> -1 pts -> total = -1
        self.assertEqual(calculate_points(35, "male", 150, 55, 110, False, False, False), -1)

    def test_normal_hdl(self):
        # hdl=45 -> 0 pts -> total = 0
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, False, False, False), 0)

    def test_borderline_hdl_40(self):
        # hdl=40 -> 0 pts (40-49 range) -> total = 0
        self.assertEqual(calculate_points(35, "male", 150, 40, 110, False, False, False), 0)

    def test_low_hdl(self):
        # hdl=35 -> 2 pts -> total = 2
        self.assertEqual(calculate_points(35, "male", 150, 35, 110, False, False, False), 2)


class TestMaleBPPoints(unittest.TestCase):
    """BP points. Use age=35, tc=150, hdl=45 (all give 0)."""

    def test_low_bp_untreated(self):
        # sbp=110 untreated -> 0 bp pts -> total = 0
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, False, False, False), 0)

    def test_normal_bp_untreated(self):
        # sbp=125 untreated -> 1 bp pt -> total = 1
        self.assertEqual(calculate_points(35, "male", 150, 45, 125, False, False, False), 1)

    def test_elevated_bp_untreated(self):
        # sbp=145 untreated -> 3 bp pts -> total = 3
        self.assertEqual(calculate_points(35, "male", 150, 45, 145, False, False, False), 3)

    def test_high_bp_untreated(self):
        # sbp=165 untreated -> 4 bp pts -> total = 4
        self.assertEqual(calculate_points(35, "male", 150, 45, 165, False, False, False), 4)

    def test_low_bp_treated(self):
        # sbp=110 treated -> 0 bp pts -> total = 0
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, True, False, False), 0)

    def test_normal_bp_treated(self):
        # sbp=125 treated -> 3 bp pts -> total = 3
        self.assertEqual(calculate_points(35, "male", 150, 45, 125, True, False, False), 3)

    def test_elevated_bp_treated(self):
        # sbp=145 treated -> 5 bp pts -> total = 5
        self.assertEqual(calculate_points(35, "male", 150, 45, 145, True, False, False), 5)

    def test_high_bp_treated(self):
        # sbp=165 treated -> 6 bp pts -> total = 6
        self.assertEqual(calculate_points(35, "male", 150, 45, 165, True, False, False), 6)


class TestMaleSmokingPoints(unittest.TestCase):
    """Smoking points. Use age=35, tc=150, hdl=45, sbp=110 (all give 0)."""

    def test_young_smoker(self):
        # age=35 (<40), smoker -> 2 smoke pts -> total = 2
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, False, True, False), 2)

    def test_middle_age_smoker(self):
        # age=55 (55-59), smoker -> 1 smoke pt + 4 age = 5
        self.assertEqual(calculate_points(55, "male", 150, 45, 110, False, True, False), 5)

    def test_older_smoker(self):
        # age=65 (60-69), smoker -> 1 smoke pt + 6 age = 7
        self.assertEqual(calculate_points(65, "male", 150, 45, 110, False, True, False), 7)

    def test_nonsmoker(self):
        # age=55, non-smoker -> 0 smoke + 4 age = 4
        self.assertEqual(calculate_points(55, "male", 150, 45, 110, False, False, False), 4)


class TestMaleDiabetesPoints(unittest.TestCase):
    """Diabetes points (+3 for male). Use age=35, tc=150, hdl=45, sbp=110."""

    def test_diabetic(self):
        # 3 diabetes pts -> total = 3
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, False, False, True), 3)

    def test_nondiabetic(self):
        # 0 diabetes pts -> total = 0
        self.assertEqual(calculate_points(35, "male", 150, 45, 110, False, False, False), 0)


# ======================================================================
# FEMALE point calculations
# Female baseline: age=40 (0 pts), tc=150 (0), hdl=45 (0), sbp=110 (0)
# ======================================================================

class TestFemaleAgePoints(unittest.TestCase):

    def test_age_30_34(self):
        # age=-9, rest=0 -> -9
        self.assertEqual(calculate_points(32, "female", 150, 45, 110, False, False, False), -9)

    def test_age_35_39(self):
        # age=-4, rest=0 -> -4
        self.assertEqual(calculate_points(37, "female", 150, 45, 110, False, False, False), -4)

    def test_age_40_44(self):
        # age=0, rest=0 -> 0
        self.assertEqual(calculate_points(42, "female", 150, 45, 110, False, False, False), 0)

    def test_age_50_54(self):
        # age=6, rest=0 -> 6
        self.assertEqual(calculate_points(52, "female", 150, 45, 110, False, False, False), 6)

    def test_age_60_64(self):
        # age=8, rest=0 -> 8
        self.assertEqual(calculate_points(62, "female", 150, 45, 110, False, False, False), 8)

    def test_age_70_74(self):
        # age=8, rest=0 -> 8
        self.assertEqual(calculate_points(72, "female", 150, 45, 110, False, False, False), 8)


class TestFemaleCholesterolPoints(unittest.TestCase):
    """Female TC points. Use age=40 (age_pts=0)."""

    def test_young_high_tc(self):
        # age=35 (<40 bracket), tc=250 -> -4 (age) + 11 (tc 240-279) = 7
        self.assertEqual(calculate_points(35, "female", 250, 45, 110, False, False, False), 7)

    def test_middle_tc(self):
        # age=45 (40-49 bracket), tc=210 -> 3 (age) + 6 (tc) = 9
        self.assertEqual(calculate_points(45, "female", 210, 45, 110, False, False, False), 9)

    def test_older_low_tc(self):
        # age=65 (60-69 bracket), tc=150 -> 8 (age) + 0 (tc) = 8
        self.assertEqual(calculate_points(65, "female", 150, 45, 110, False, False, False), 8)


class TestFemaleSmokingPoints(unittest.TestCase):
    """Female smoking points. Use tc=150, hdl=45, sbp=110."""

    def test_young_female_smoker(self):
        # age=35 (<40), smoker -> -4 (age) + 2 (smoke) = -2
        self.assertEqual(calculate_points(35, "female", 150, 45, 110, False, True, False), -2)

    def test_50s_female_smoker(self):
        # age=55 (50-59), smoker -> 7 (age) + 2 (smoke) = 9
        self.assertEqual(calculate_points(55, "female", 150, 45, 110, False, True, False), 9)

    def test_older_female_smoker(self):
        # age=65 (60-69), smoker -> 8 (age) + 1 (smoke) = 9
        self.assertEqual(calculate_points(65, "female", 150, 45, 110, False, True, False), 9)


class TestFemaleDiabetesPoints(unittest.TestCase):
    """Female diabetes (+4). Use age=40, tc=150, hdl=45, sbp=110."""

    def test_female_diabetic(self):
        # 0 (age) + 4 (diabetes) = 4
        self.assertEqual(calculate_points(40, "female", 150, 45, 110, False, False, True), 4)

    def test_female_nondiabetic(self):
        # 0 (age) + 0 = 0
        self.assertEqual(calculate_points(40, "female", 150, 45, 110, False, False, False), 0)


# ======================================================================
# Full calculate_framingham() integration tests
# ======================================================================

class TestFullCalculationMale(unittest.TestCase):

    def test_low_risk_male(self):
        """Young male, good numbers, no risk factors."""
        r = calculate_framingham(
            age=35, sex="male", total_cholesterol=150, hdl_cholesterol=65,
            systolic_bp=110, bp_treated=False, smoker=False, diabetic=False,
        )
        # age=0, tc=0, hdl=-2, bp=0, smoke=0, diab=0 -> total=-2
        self.assertEqual(r["total_points"], -2)
        self.assertEqual(r["risk_percent"], 1)
        self.assertEqual(r["risk_category"], "Low")

    def test_intermediate_risk_male(self):
        """Middle-aged male with some risk factors."""
        r = calculate_framingham(
            age=55, sex="male", total_cholesterol=220, hdl_cholesterol=45,
            systolic_bp=135, bp_treated=False, smoker=True, diabetic=False,
        )
        # age=4, tc=3, hdl=0, bp=2, smoke=1, diab=0 -> total=10
        self.assertEqual(r["total_points"], 10)
        self.assertEqual(r["risk_percent"], 14)
        self.assertEqual(r["risk_category"], "Intermediate")

    def test_high_risk_male(self):
        """Older male with multiple risk factors."""
        r = calculate_framingham(
            age=65, sex="male", total_cholesterol=260, hdl_cholesterol=35,
            systolic_bp=155, bp_treated=True, smoker=True, diabetic=True,
        )
        # age=6, tc=2, hdl=2, bp=5, smoke=1, diab=3 -> total=19
        self.assertEqual(r["total_points"], 19)
        self.assertEqual(r["risk_percent"], 56)
        self.assertEqual(r["risk_category"], "High")

    def test_breakdown_structure(self):
        r = calculate_framingham(
            age=50, sex="male", total_cholesterol=200, hdl_cholesterol=50,
            systolic_bp=130, bp_treated=False, smoker=False, diabetic=False,
        )
        b = r["breakdown"]
        self.assertIn("age_points", b)
        self.assertIn("cholesterol_points", b)
        self.assertIn("hdl_points", b)
        self.assertIn("blood_pressure_points", b)
        self.assertIn("smoking_points", b)
        self.assertIn("diabetes_points", b)
        # Sum of breakdown == total
        self.assertEqual(sum(b.values()), r["total_points"])


class TestFullCalculationFemale(unittest.TestCase):

    def test_low_risk_female(self):
        """Young female, good numbers."""
        r = calculate_framingham(
            age=35, sex="female", total_cholesterol=150, hdl_cholesterol=65,
            systolic_bp=110, bp_treated=False, smoker=False, diabetic=False,
        )
        # age=-4, tc=0, hdl=-2, bp=0, smoke=0, diab=0 -> total=-6
        self.assertEqual(r["total_points"], -6)
        self.assertEqual(r["risk_percent"], 1)
        self.assertEqual(r["risk_category"], "Low")

    def test_intermediate_risk_female(self):
        """Middle-aged female with risk factors."""
        r = calculate_framingham(
            age=55, sex="female", total_cholesterol=240, hdl_cholesterol=45,
            systolic_bp=145, bp_treated=True, smoker=True, diabetic=False,
        )
        # age=7, tc=5, hdl=0, bp=5, smoke=2, diab=0 -> total=19
        self.assertEqual(r["total_points"], 19)
        self.assertEqual(r["risk_percent"], 30)
        self.assertEqual(r["risk_category"], "High")

    def test_high_risk_female(self):
        """Older female with many risk factors."""
        r = calculate_framingham(
            age=68, sex="female", total_cholesterol=280, hdl_cholesterol=38,
            systolic_bp=160, bp_treated=True, smoker=True, diabetic=True,
        )
        # age=8, tc=4, hdl=2, bp=6, smoke=1, diab=4 -> total=25
        self.assertEqual(r["total_points"], 25)
        self.assertEqual(r["risk_percent"], 30)
        self.assertEqual(r["risk_category"], "High")

    def test_female_with_hdl_protection(self):
        """Female with high HDL should get negative HDL points."""
        r = calculate_framingham(
            age=50, sex="female", total_cholesterol=150, hdl_cholesterol=70,
            systolic_bp=110, bp_treated=False, smoker=False, diabetic=False,
        )
        # age=6, tc=0, hdl=-2, bp=0, smoke=0, diab=0 -> total=4
        self.assertEqual(r["total_points"], 4)
        self.assertEqual(r["risk_percent"], 4)
        self.assertEqual(r["risk_category"], "Low")


# ======================================================================
# Input validation
# ======================================================================

class TestInputValidation(unittest.TestCase):

    def test_invalid_sex(self):
        with self.assertRaises(ValueError):
            calculate_points(50, "other", 200, 50, 130, False, False, False)

    def test_age_too_young(self):
        with self.assertRaises(ValueError):
            calculate_points(25, "male", 200, 50, 130, False, False, False)

    def test_age_too_old(self):
        with self.assertRaises(ValueError):
            calculate_points(80, "male", 200, 50, 130, False, False, False)

    def test_boundary_age_30(self):
        # Should not raise
        calculate_points(30, "male", 200, 50, 130, False, False, False)

    def test_boundary_age_74(self):
        # Should not raise
        calculate_points(74, "male", 200, 50, 130, False, False, False)

    def test_sex_case_insensitive(self):
        r1 = calculate_points(50, "MALE", 200, 50, 130, False, False, False)
        r2 = calculate_points(50, "Male", 200, 50, 130, False, False, False)
        r3 = calculate_points(50, "male", 200, 50, 130, False, False, False)
        self.assertEqual(r1, r2)
        self.assertEqual(r2, r3)


# ======================================================================
# assess_row (CSV row processing)
# ======================================================================

class TestAssessRow(unittest.TestCase):

    def test_standard_row(self):
        row = {
            "age": "55", "sex": "male", "total_cholesterol": "210",
            "hdl_cholesterol": "50", "systolic_bp": "140",
            "bp_treated": "0", "smoker": "1", "diabetic": "0",
        }
        r = assess_row(row)
        self.assertIn("total_points", r)
        self.assertIn("risk_percent", r)
        self.assertIn("risk_category", r)

    def test_alternate_column_names(self):
        row = {
            "age": "50", "sex": "female", "tc": "200",
            "hdl": "55", "sbp": "125",
            "on_bp_meds": "true", "smoking": "yes", "diabetes": "no",
        }
        r = assess_row(row)
        self.assertIsInstance(r["total_points"], int)
        self.assertIsInstance(r["risk_percent"], int)

    def test_missing_required_field(self):
        row = {"age": "50", "sex": "male"}
        with self.assertRaises(ValueError):
            assess_row(row)

    def test_boolean_like_values(self):
        """Various truthy string representations."""
        for truthy in ("1", "true", "yes", "y", "True", "YES"):
            row = {
                "age": "50", "sex": "male", "tc": "200",
                "hdl": "50", "sbp": "130",
                "bp_treated": truthy, "smoker": "0", "diabetic": "0",
            }
            r = assess_row(row)
            # bp_treated=True for SBP 130 -> 4 bp points
            self.assertEqual(r["breakdown"]["blood_pressure_points"], 4)


# ======================================================================
# CSV batch processing
# ======================================================================

class TestProcessCSV(unittest.TestCase):

    def _write_csv(self, rows, fieldnames):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False,
                                        newline="", encoding="utf-8")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        f.close()
        return f.name

    def test_batch_processing(self):
        fieldnames = ["age", "sex", "tc", "hdl", "sbp", "bp_treated", "smoker", "diabetic"]
        rows = [
            {"age": "45", "sex": "male", "tc": "200", "hdl": "50", "sbp": "130",
             "bp_treated": "0", "smoker": "0", "diabetic": "0"},
            {"age": "60", "sex": "female", "tc": "250", "hdl": "40", "sbp": "150",
             "bp_treated": "1", "smoker": "1", "diabetic": "1"},
        ]
        in_path = self._write_csv(rows, fieldnames)
        out_path = in_path.replace(".csv", "_out.csv")
        try:
            results = process_csv(in_path, out_path)
            self.assertEqual(len(results), 2)
            self.assertIn("total_points", results[0])
            self.assertIn("risk_percent", results[0])
            self.assertIn("risk_category", results[0])

            # Verify output file
            with open(out_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                out_rows = list(reader)
            self.assertEqual(len(out_rows), 2)
            self.assertIn("total_points", out_rows[0])
        finally:
            os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

    def test_batch_with_error_row(self):
        """A row missing required fields should produce ERROR, not crash."""
        fieldnames = ["age", "sex", "tc", "hdl", "sbp"]
        rows = [
            {"age": "45", "sex": "male", "tc": "200", "hdl": "50", "sbp": "130"},
            {"age": "60", "sex": "female"},  # missing fields
        ]
        in_path = self._write_csv(rows, fieldnames)
        out_path = in_path.replace(".csv", "_out.csv")
        try:
            results = process_csv(in_path, out_path)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[1]["total_points"], "ERROR")
        finally:
            os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)


# ======================================================================
# CLI integration
# ======================================================================

class TestCLI(unittest.TestCase):

    def test_single_default_output(self):
        from cli import main
        ret = main(["single", "--age", "50", "--sex", "male",
                     "--tc", "200", "--hdl", "50", "--sbp", "130"])
        self.assertEqual(ret, 0)

    def test_single_json_output(self):
        from cli import main
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["single", "--age", "50", "--sex", "male",
                         "--tc", "200", "--hdl", "50", "--sbp", "130",
                         "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("total_points", data)
        self.assertIn("risk_percent", data)
        self.assertIn("risk_category", data)

    def test_single_with_flags(self):
        from cli import main
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["single", "--age", "55", "--sex", "male",
                         "--tc", "210", "--hdl", "50", "--sbp", "140",
                         "--bp-treated", "--smoker", "--diabetic", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        # age=4, tc=3(50-59,200-239), hdl=-1, bp=5(140-159 treated), smoke=1, diab=3 -> 15
        self.assertEqual(data["total_points"], 15)
        self.assertEqual(data["risk_percent"], 40)
        self.assertEqual(data["risk_category"], "High")

    def test_no_command(self):
        from cli import main
        ret = main([])
        self.assertEqual(ret, 1)

    def test_batch_command(self):
        from cli import main
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False,
                                        newline="", encoding="utf-8")
        writer = csv.DictWriter(f, fieldnames=["age", "sex", "tc", "hdl", "sbp"])
        writer.writeheader()
        writer.writerow({"age": "50", "sex": "male", "tc": "200", "hdl": "50", "sbp": "130"})
        f.close()
        out_path = f.name.replace(".csv", "_out.csv")
        try:
            ret = main(["batch", "-i", f.name, "-o", out_path])
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.exists(out_path))
        finally:
            os.unlink(f.name)
            if os.path.exists(out_path):
                os.unlink(out_path)


# ======================================================================
# Specific known-value regression tests
# ======================================================================

class TestKnownValues(unittest.TestCase):
    """Regression tests for specific patient profiles with known scores."""

    def test_male_low_risk_profile(self):
        """40yo male, TC 180, HDL 55, SBP 125, no treatment, non-smoker, no diabetes."""
        r = calculate_framingham(40, "male", 180, 55, 125, False, False, False)
        # age=1, tc=3(40-49,160-199), hdl=-1, bp=1, smoke=0, diab=0 -> 4
        self.assertEqual(r["total_points"], 4)
        self.assertEqual(r["risk_percent"], 3)
        self.assertEqual(r["risk_category"], "Low")

    def test_male_high_risk_profile(self):
        """70yo male, TC 280, HDL 35, SBP 165, treated, smoker, diabetic."""
        r = calculate_framingham(70, "male", 280, 35, 165, True, True, True)
        # age=7, tc=1(70-79,>=280), hdl=2, bp=6, smoke=1, diab=3 -> 20
        self.assertEqual(r["total_points"], 20)
        self.assertEqual(r["risk_percent"], 56)
        self.assertEqual(r["risk_category"], "High")

    def test_female_low_risk_profile(self):
        """40yo female, TC 170, HDL 60, SBP 115, non-smoker, no diabetes."""
        r = calculate_framingham(40, "female", 170, 60, 115, False, False, False)
        # age=0, tc=3(40-49,160-199), hdl=-2, bp=0, smoke=0, diab=0 -> 1
        self.assertEqual(r["total_points"], 1)
        self.assertEqual(r["risk_percent"], 2)
        self.assertEqual(r["risk_category"], "Low")

    def test_female_high_risk_profile(self):
        """68yo female, TC 270, HDL 38, SBP 155, treated, smoker, diabetic."""
        r = calculate_framingham(68, "female", 270, 38, 155, True, True, True)
        # age=8, tc=3(60-69,240-279), hdl=2, bp=5, smoke=1, diab=4 -> 23
        self.assertEqual(r["total_points"], 23)
        self.assertEqual(r["risk_percent"], 30)
        self.assertEqual(r["risk_category"], "High")

    def test_male_borderline_intermediate(self):
        """Exactly 14% risk -> Intermediate category."""
        r = calculate_framingham(55, "male", 220, 45, 135, False, True, False)
        # age=4, tc=3, hdl=0, bp=2, smoke=1, diab=0 -> 10
        self.assertEqual(r["total_points"], 10)
        self.assertEqual(r["risk_percent"], 14)
        self.assertEqual(r["risk_category"], "Intermediate")


if __name__ == "__main__":
    unittest.main()
