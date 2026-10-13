#!/usr/bin/env python3
"""
Framingham Risk Score Calculator — 10-Year Cardiovascular Disease Risk.

Implements the corrected 2008 lipid-based general CVD continuous and point models from:
  D'Agostino RB Sr, Vasan RS, Pencina MJ, et al.
  "General Cardiovascular Risk Profile for Use in Primary Care."
  Circulation. 2008;117(6):743-753.

Valid for ages 30-74. Uses lipids, blood pressure (treated vs untreated),
smoking status, and diabetes status.

Stdlib only — no third-party dependencies.
"""

# Sex-specific tables: D'Agostino et al., Circulation 2008;117:743-753.
# THESE ARE FOR GENERAL CVD, NOT THE OLDER FRAMINGHAM CHD / ATP III SCORES.
import csv
import math

AGE = {
    "male": [0,2,5,6,8,10,11,12,14],
    "female": [0,2,4,5,7,8,9,10,11],
}
TC = {"male": [0,1,2,3,4], "female": [0,1,3,4,5]}
HDL = [(0,35,2),(35,45,1),(45,50,0),(50,60,-1),(60,None,-2)]
BP = {
    "male": {False: [-2,0,1,2,3], True: [0,2,3,4,5]},
    "female": {False: [-3,0,1,2,4,5], True: [-1,2,3,5,6,7]},
}
SMOKE = {"male":4, "female":3}
DIAB = {"male":3, "female":4}
RISK_LOOKUP = {
    "male": {-2:1.1,-1:1.4,**dict(enumerate([1.6,1.9,2.3,2.8,3.3,3.9,4.7,5.6,6.7,7.9,9.4,11.2,13.2,15.6,18.4,21.6,25.3,29.4]))},
    "female": {-1:1.0,**dict(enumerate([1.2,1.5,1.7,2.0,2.4,2.8,3.3,3.9,4.5,5.3,6.3,7.3,8.6,10.0,11.7,13.7,15.9,18.5,21.5,24.8,28.5]))},
}
# Lipid-based continuous Cox model, NOT the BMI-based regression.
COEF = {
    "male": (3.06117,1.12370,-0.93263,1.93303,1.99881,0.65451,0.57367,23.9802,0.88936),
    "female": (2.32888,1.20904,-0.70833,2.76157,2.82263,0.52873,0.69154,26.1931,0.95012),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lookup_range(value, table):
    """Look up points from a list of (low, high, points) tuples.

    `high` is exclusive unless it is None (meaning >= low).
    """
    for low, high, pts in table:
        if high is None:
            if value >= low:
                return pts
        else:
            if low <= value < high:
                return pts
    # Fallback: clamp to last entry
    return table[-1][2]


def _lookup_age_group(age, table):
    """Return points from an age-group keyed dict or list of tuples."""
    if isinstance(table, dict):
        for (lo, hi), pts in table.items():
            if lo <= age <= hi:
                return pts
        # clamp
        last_key = list(table.keys())[-1]
        return table[last_key]
    # list of (lo, hi, pts)
    return _lookup_range(age, table)


def _age_group_key(age):
    """Return the 10-year age-band start (30, 40, 50, 60, 70)."""
    if age < 40:
        return (30, 39)
    elif age < 50:
        return (40, 49)
    elif age < 60:
        return (50, 59)
    elif age < 70:
        return (60, 69)
    else:
        return (70, 79)


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def _validate(age, sex, tc, hdl, sbp, bp_treated, smoker, diabetic):
    if not isinstance(sex,str) or sex.strip().lower() not in COEF:
        raise ValueError("sex must be 'male' or 'female'")
    sex = sex.strip().lower()
    if isinstance(age,bool) or not isinstance(age,(int,float)) or not math.isfinite(age) or not float(age).is_integer() or not 30 <= age <= 74:
        raise ValueError("age must be an integer from 30 to 74")
    for name, value in (("total_cholesterol",tc),("hdl_cholesterol",hdl),("systolic_bp",sbp)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    for name, value in (("bp_treated",bp_treated),("smoker",smoker),("diabetic",diabetic)):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a boolean")
    return sex


def _breakdown(age, sex, tc, hdl, sbp, treated, smoker, diabetic):
    tc_index = 0 if tc<160 else 1 if tc<200 else 2 if tc<240 else 3 if tc<280 else 4
    hdl_points = _lookup_range(hdl, HDL)
    if sex=="male":
        bp_index = 0 if sbp<120 else 1 if sbp<130 else 2 if sbp<140 else 3 if sbp<160 else 4
    else:
        bp_index = 0 if sbp<120 else 1 if sbp<130 else 2 if sbp<140 else 3 if sbp<150 else 4 if sbp<160 else 5
    return {"age_points":AGE[sex][(int(age)-30)//5],
            "cholesterol_points":TC[sex][tc_index],
            "hdl_points":hdl_points,
            "blood_pressure_points":BP[sex][treated][bp_index],
            "smoking_points":SMOKE[sex] if smoker else 0,
            "diabetes_points":DIAB[sex] if diabetic else 0}


def calculate_points(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic):
    sex=_validate(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic)
    return sum(_breakdown(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic).values())


def points_to_risk(total_points,sex):
    """Published point table (%); None means a censored tail (<1 or >30%)."""
    if not isinstance(sex,str) or sex.strip().lower() not in COEF:
        raise ValueError("sex must be 'male' or 'female'")
    if type(total_points) is not int:
        raise ValueError("total_points must be integer")
    return RISK_LOOKUP[sex.strip().lower()].get(total_points)


def risk_category(risk_percent):
    """Descriptive thresholds ONLY; not clinical treatment thresholds."""
    if not isinstance(risk_percent,(int,float)) or not math.isfinite(risk_percent) or not 0 <= risk_percent <= 100:
        raise ValueError("risk_percent must be finite between 0 and 100")
    return "Low" if risk_percent<10 else "Intermediate" if risk_percent<=20 else "High"


def calculate_continuous_risk(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic):
    """Unrounded 2008 lipid-based general CVD risk, in percent."""
    sex=_validate(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic)
    a,tc,hdl,sbu,sbt,sm,d,mean,survival=COEF[sex]
    lp=(a*math.log(age)+tc*math.log(total_cholesterol)+hdl*math.log(hdl_cholesterol)
        +(sbt if bp_treated else sbu)*math.log(systolic_bp)+sm*smoker+d*diabetic-mean)
    return -100*math.expm1(math.log(survival)*math.exp(min(lp,700)))


def calculate_framingham(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic):
    sex=_validate(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic)
    breakdown=_breakdown(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic)
    total=sum(breakdown.values())
    risk=round(calculate_continuous_risk(age,sex,total_cholesterol,hdl_cholesterol,systolic_bp,bp_treated,smoker,diabetic),1)
    point_risk=points_to_risk(total,sex)
    return {"total_points":total, "risk_percent":risk, "risk_category":risk_category(risk),
            "breakdown":breakdown, "point_risk_percent":point_risk,
            "point_risk_label":(f"{point_risk:.1f}%" if point_risk is not None else
                                "<1%" if total<(-1 if sex=="female" else -2) else ">30%"),
            "model":"Framingham 2008 general CVD (lipid-based)"}


# CSV / CLI compatibility
def _flag(value, name):
    value=str(value).strip().lower()
    if value in ("1","true","yes","y"): return True
    if value in ("0","false","no","n",""): return False
    raise ValueError(f"{name} must be yes/no, true/false, or 1/0")


def assess_row(row):
    """Case-insensitive CSV headers; optional flags default to False."""
    if not isinstance(row,dict) or None in row:
        raise ValueError("CSV row has extra columns")
    values={k.strip().lower():v for k,v in row.items()}
    def get(*names,default=None):
        for name in names:
            if name in values: return values[name]
        if default is not None: return default
        raise ValueError(f"Missing required field: {names[0]}")
    age=float(get("age"))
    if not math.isfinite(age) or not age.is_integer():
        raise ValueError("age must be an integer")
    return calculate_framingham(int(age),get("sex"),
        float(get("total_cholesterol","tc")),float(get("hdl_cholesterol","hdl")),
        float(get("systolic_bp","sbp")),
        _flag(get("bp_treated","on_bp_meds","bp_medication",default="0"),"bp_treated"),
        _flag(get("smoker","smoking","current_smoker",default="0"),"smoker"),
        _flag(get("diabetic","diabetes",default="0"),"diabetic"))


def process_csv(input_path,output_path):
    """Score CSV, record row errors, disallow duplicate or reserved output fields."""
    with open(input_path,newline="",encoding="utf-8-sig") as stream:
        reader=csv.DictReader(stream)
        fields=list(reader.fieldnames or [])
        if not fields or any(not k or not k.strip() for k in fields):
            raise ValueError("CSV needs a header")
        normalized=[k.strip().lower() for k in fields]
        if len(set(normalized))!=len(normalized):
            raise ValueError("Duplicate CSV headers are not allowed")
        if any(k in normalized for k in ("total_points","risk_percent","risk_category","risk_error")):
            raise ValueError("CSV input contains reserved output fields")
        rows=list(reader)
    results=[]
    for row in rows:
        result={k:v for k,v in row.items() if k is not None}
        try:
            risk=assess_row(row)
            result.update(total_points=risk["total_points"],risk_percent=risk["risk_percent"],
                          risk_category=risk["risk_category"],risk_error="")
        except (ValueError,TypeError,OverflowError) as exc:
            result.update(total_points="ERROR",risk_percent="ERROR",risk_category="ERROR",risk_error=str(exc))
        results.append(result)
    with open(output_path,"w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields+["total_points","risk_percent","risk_category","risk_error"])
        writer.writeheader()
        writer.writerows(results)
    return results
