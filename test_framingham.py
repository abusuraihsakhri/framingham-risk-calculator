"""Regression coverage for Framingham 2008 general CVD (lipid-based)."""
import csv
import io
import json
import math
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from framingham import (calculate_framingham,calculate_points,calculate_continuous_risk,
                        points_to_risk,assess_row,process_csv,risk_category)
from cli import main


class ClinicalModels(unittest.TestCase):
    def test_published_female_example(self):
        # D'Agostino et al., Glob Heart 2013, Table 5: 12 points = 8.6%.
        r=calculate_framingham(61,"female",230,47,124,False,False,False)
        self.assertEqual(r["total_points"],12)
        self.assertEqual(r["point_risk_percent"],8.6)
        self.assertEqual(r["breakdown"]["age_points"],9)
        self.assertEqual(r["breakdown"]["cholesterol_points"],3)
        self.assertEqual(r["breakdown"]["blood_pressure_points"],0)
        self.assertAlmostEqual(r["risk_percent"],8.4,places=1)

    def test_male_score(self):
        r=calculate_framingham(55,"male",220,45,135,False,True,False)
        self.assertEqual(r["total_points"],17)
        self.assertEqual(r["point_risk_percent"],29.4)
        self.assertEqual(r["breakdown"]["smoking_points"],4)

    def test_continuous_coefficients_male(self):
        lp=(3.06117*math.log(55)+1.12370*math.log(220)-0.93263*math.log(45)
            +1.93303*math.log(135)+0.65451-23.9802)
        expected=100*(1-0.88936**math.exp(lp))
        self.assertAlmostEqual(calculate_continuous_risk(55,"male",220,45,135,False,True,False),expected,places=9)

    def test_continuous_coefficients_female(self):
        lp=(2.32888*math.log(61)+1.20904*math.log(230)-0.70833*math.log(47)
            +2.82263*math.log(124)+0.52873+0.69154-26.1931)
        expected=100*(1-0.95012**math.exp(lp))
        self.assertAlmostEqual(calculate_continuous_risk(61,"female",230,47,124,True,True,True),expected,places=9)

    def test_bp_thresholds(self):
        for sex,treated,thresholds in (("male",False,[(119,-2),(120,0),(130,1),(140,2),(160,3)]),
                                       ("male",True,[(119,0),(120,2),(130,3),(140,4),(160,5)]),
                                       ("female",False,[(119,-3),(120,0),(130,1),(140,2),(150,4),(160,5)]),
                                       ("female",True,[(119,-1),(120,2),(130,3),(140,5),(150,6),(160,7)])):
            for sbp,points in thresholds:
                with self.subTest(sex=sex,treated=treated,sbp=sbp):
                    r=calculate_framingham(50,sex,200,50,sbp,treated,False,False)
                    self.assertEqual(r["breakdown"]["blood_pressure_points"],points)

    def test_hdl_and_cholesterol_thresholds(self):
        for hdl,points in [(34,2),(35,1),(44.9,1),(45,0),(50,-1),(60,-2)]:
            r=calculate_framingham(50,"female",200,hdl,130,False,False,False)
            self.assertEqual(r["breakdown"]["hdl_points"],points)
        for tc,points in [(159.9,0),(160,1),(200,2),(240,3),(280,4)]:
            r=calculate_framingham(50,"male",tc,50,130,False,False,False)
            self.assertEqual(r["breakdown"]["cholesterol_points"],points)

    def test_censored_chart_values(self):
        self.assertIsNone(points_to_risk(-3,"male"))
        self.assertEqual(points_to_risk(-2,"male"),1.1)
        self.assertIsNone(points_to_risk(18,"male"))
        self.assertEqual(points_to_risk(20,"female"),28.5)
        self.assertIsNone(points_to_risk(21,"female"))

    def test_validation(self):
        base=[50,"male",200,50,130,False,False,False]
        for age in [29,75,50.5,True,float("nan"),float("inf")]:
            with self.subTest(age=age),self.assertRaises(ValueError):
                calculate_points(*([age]+base[1:]))
        for j in [2,3,4]:
            for bad in [0,-1,float("nan"),float("inf"),True]:
                bad_input=base.copy();bad_input[j]=bad
                with self.assertRaises(ValueError): calculate_points(*bad_input)
        for j in [5,6,7]:
            bad_input=base.copy();bad_input[j]="0"
            with self.assertRaises(ValueError): calculate_points(*bad_input)
        with self.assertRaises(ValueError): calculate_points(50,"other",200,50,130,False,False,False)

    def test_risk_categories_are_descriptive(self):
        self.assertEqual(risk_category(9.9),"Low")
        self.assertEqual(risk_category(10),"Intermediate")
        self.assertEqual(risk_category(20),"Intermediate")
        self.assertEqual(risk_category(20.1),"High")

    def test_csv_flags(self):
        row={"age":"50","sex":"male","tc":"200","hdl":"50","sbp":"130","smoker":"YES"}
        self.assertEqual(assess_row(row)["breakdown"]["smoking_points"],4)
        row["smoker"]="maybe"
        with self.assertRaises(ValueError): assess_row(row)
        row["smoker"]="0";row["age"]="50.5"
        with self.assertRaises(ValueError): assess_row(row)

    def test_batch_malformed_row(self):
        with tempfile.TemporaryDirectory() as folder:
            src=os.path.join(folder,"src.csv");dst=os.path.join(folder,"dst.csv")
            with open(src,"w",newline="") as f:
                w=csv.writer(f);w.writerow(["age","sex","tc","hdl","sbp","smoker"])
                w.writerow([61,"female",230,47,124,0]);w.writerow([50,"male",200,50,130,"maybe"])
            rows=process_csv(src,dst)
            self.assertEqual(rows[0]["total_points"],12)
            self.assertEqual(rows[1]["risk_category"],"ERROR")
            self.assertIn("smoker",rows[1]["risk_error"])
            with open(dst,newline="") as f: self.assertEqual(len(list(csv.DictReader(f))),2)

    def test_duplicate_csv_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            src=os.path.join(folder,"src.csv")
            with open(src,"w") as f:f.write("age,AGE,sex,tc,hdl,sbp\n50,50,male,200,50,130\n")
            with self.assertRaises(ValueError): process_csv(src,os.path.join(folder,"out.csv"))

    def test_cli_json(self):
        out=io.StringIO()
        with redirect_stdout(out):
            status=main(["single","--age","61","--sex","female","--tc","230","--hdl","47","--sbp","124","--json"])
        self.assertEqual(status,0)
        self.assertEqual(json.loads(out.getvalue())["total_points"],12)


if __name__=="__main__":
    unittest.main()
