#!/usr/bin/env python3
"""
Framingham Risk Score Calculator — 10-Year Cardiovascular Disease Risk.

Implements the sex-specific point-based model from:
  D'Agostino RB Sr, Vasan RS, Pencina MJ, et al.
  "General Cardiovascular Risk Profile for Use in Primary Care."
  Circulation. 2008;111(6):751-756.

Valid for ages 30-74. Uses lipids, blood pressure (treated vs untreated),
smoking status, and diabetes status.

Stdlib only — no third-party dependencies.
"""

# ---------------------------------------------------------------------------
# Point tables — MALE
# ---------------------------------------------------------------------------

MALE_AGE_POINTS = [
    (30, 35, -1),  # 30-34
    (35, 40,  0),  # 35-39
    (40, 45,  1),  # 40-44
    (45, 50,  2),  # 45-49
    (50, 55,  3),  # 50-54
    (55, 60,  4),  # 55-59
    (60, 65,  5),  # 60-64
    (65, 70,  6),  # 65-69
    (70, 75,  7),  # 70-74
]

# (age_low, age_high): [(tc_low, tc_high, points), ...]
# tc_high of None means >= tc_low
MALE_TC_POINTS = {
    (30, 39): [(0, 160, 0), (160, 200, 4), (200, 240, 7), (240, 280, 9), (280, None, 11)],
    (40, 49): [(0, 160, 0), (160, 200, 3), (200, 240, 5), (240, 280, 6), (280, None,  8)],
    (50, 59): [(0, 160, 0), (160, 200, 2), (200, 240, 3), (240, 280, 4), (280, None,  5)],
    (60, 69): [(0, 160, 0), (160, 200, 1), (200, 240, 1), (240, 280, 2), (280, None,  3)],
    (70, 79): [(0, 160, 0), (160, 200, 0), (200, 240, 0), (240, 280, 1), (280, None,  1)],
}

MALE_SMOKING_POINTS = {
    (30, 39): 2,
    (40, 49): 2,
    (50, 59): 1,
    (60, 69): 1,
    (70, 79): 1,
}

# 10-year risk lookup: total_points -> risk_percent
MALE_RISK_LOOKUP = {
    -1: 1,   # "<1%" stored as 1
     0: 1,
     1: 1,
     2: 2,
     3: 2,
     4: 3,
     5: 4,
     6: 5,
     7: 7,
     8: 9,
     9: 11,
    10: 14,
    11: 17,
    12: 22,
    13: 27,
    14: 33,
    15: 40,
    16: 47,
}

# ---------------------------------------------------------------------------
# Point tables — FEMALE
# ---------------------------------------------------------------------------

FEMALE_AGE_POINTS = [
    (30, 35, -9),  # 30-34
    (35, 40, -4),  # 35-39
    (40, 45,  0),  # 40-44
    (45, 50,  3),  # 45-49
    (50, 55,  6),  # 50-54
    (55, 60,  7),  # 55-59
    (60, 65,  8),  # 60-64
    (65, 70,  8),  # 65-69
    (70, 75,  8),  # 70-74
]

FEMALE_TC_POINTS = {
    (30, 39): [(0, 160, 0), (160, 200, 4), (200, 240, 8), (240, 280, 11), (280, None, 13)],
    (40, 49): [(0, 160, 0), (160, 200, 3), (200, 240, 6), (240, 280,  8), (280, None, 10)],
    (50, 59): [(0, 160, 0), (160, 200, 2), (200, 240, 4), (240, 280,  5), (280, None,  7)],
    (60, 69): [(0, 160, 0), (160, 200, 1), (200, 240, 2), (240, 280,  3), (280, None,  4)],
    (70, 79): [(0, 160, 0), (160, 200, 1), (200, 240, 1), (240, 280,  2), (280, None,  2)],
}

FEMALE_SMOKING_POINTS = {
    (30, 39): 2,
    (40, 49): 2,
    (50, 59): 2,
    (60, 69): 1,
    (70, 79): 1,
}

FEMALE_RISK_LOOKUP = {
    -9: 1,   # "<1%"
    -8: 1,
    -7: 1,
    -6: 1,
    -5: 1,
    -4: 1,
    -3: 1,
    -2: 1,
    -1: 2,
     0: 2,
     1: 2,
     2: 3,
     3: 3,
     4: 4,
     5: 5,
     6: 6,
     7: 7,
     8: 9,
     9: 11,
    10: 13,
    11: 15,
    12: 18,
    13: 20,
    14: 24,
    15: 27,
}

# ---------------------------------------------------------------------------
# Shared tables
# ---------------------------------------------------------------------------

HDL_POINTS = [
    (60, None, -2),   # >= 60
    (50, 60,   -1),   # 50-59
    (40, 50,    0),   # 40-49
    (0,  40,    2),   # < 40
]

# Systolic BP points — untreated / treated
BP_UNTREATED = [
    (0,   120, 0),
    (120, 130, 1),
    (130, 140, 2),
    (140, 160, 3),
    (160, None, 4),
]

BP_TREATED = [
    (0,   120, 0),
    (120, 130, 3),
    (130, 140, 4),
    (140, 160, 5),
    (160, None, 6),
]

DIABETES_POINTS = {"male": 3, "female": 4}


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

def calculate_points(age, sex, total_cholesterol, hdl_cholesterol,
                     systolic_bp, bp_treated, smoker, diabetic):
    """Compute the Framingham Risk Score point total.

    Parameters
    ----------
    age : int
        Patient age (30-74).
    sex : str
        "male" or "female" (case-insensitive).
    total_cholesterol : float
        Total cholesterol in mg/dL.
    hdl_cholesterol : float
        HDL cholesterol in mg/dL.
    systolic_bp : float
        Systolic blood pressure in mmHg.
    bp_treated : bool
        Whether the patient is on BP medication.
    smoker : bool
        Current smoker status.
    diabetic : bool
        Diabetes status.

    Returns
    -------
    int
        Total Framingham points.
    """
    sex = sex.lower().strip()
    if sex not in ("male", "female"):
        raise ValueError(f"sex must be 'male' or 'female', got '{sex}'")
    if age < 30 or age > 74:
        raise ValueError(f"age must be 30-74, got {age}")

    # Select sex-specific tables
    if sex == "male":
        age_table = MALE_AGE_POINTS
        tc_table = MALE_TC_POINTS
        smoking_table = MALE_SMOKING_POINTS
    else:
        age_table = FEMALE_AGE_POINTS
        tc_table = FEMALE_TC_POINTS
        smoking_table = FEMALE_SMOKING_POINTS

    # Age points
    age_pts = _lookup_range(age, age_table)

    # Total cholesterol points (age-group dependent)
    ag = _age_group_key(age)
    tc_pts = _lookup_range(total_cholesterol, tc_table[ag])

    # HDL points
    hdl_pts = _lookup_range(hdl_cholesterol, HDL_POINTS)

    # Systolic BP points
    bp_table = BP_TREATED if bp_treated else BP_UNTREATED
    bp_pts = _lookup_range(systolic_bp, bp_table)

    # Smoking points (age-group dependent, only if smoker)
    smoke_pts = _lookup_age_group(age, smoking_table) if smoker else 0

    # Diabetes points
    diab_pts = DIABETES_POINTS[sex] if diabetic else 0

    total = age_pts + tc_pts + hdl_pts + bp_pts + smoke_pts + diab_pts
    return total


def points_to_risk(total_points, sex):
    """Convert a point total to a 10-year CVD risk percentage.

    Returns an integer percentage. Points below the table minimum return 1%;
    points above the table maximum return 56% (male) or 30% (female).
    """
    sex = sex.lower().strip()
    if sex == "male":
        lookup = MALE_RISK_LOOKUP
        floor_risk = 1
        ceil_risk = 56
        min_pts = min(lookup)
        max_pts = max(lookup)
    else:
        lookup = FEMALE_RISK_LOOKUP
        floor_risk = 1
        ceil_risk = 30
        min_pts = min(lookup)
        max_pts = max(lookup)

    if total_points < min_pts:
        return floor_risk
    if total_points > max_pts:
        return ceil_risk
    return lookup[total_points]


def risk_category(risk_percent):
    """Classify risk percentage into Low / Intermediate / High.

    Low:          < 10%
    Intermediate: 10-20%
    High:         > 20%
    """
    if risk_percent < 10:
        return "Low"
    elif risk_percent <= 20:
        return "Intermediate"
    else:
        return "High"


def calculate_framingham(age, sex, total_cholesterol, hdl_cholesterol,
                         systolic_bp, bp_treated, smoker, diabetic):
    """Full Framingham Risk Score calculation.

    Returns a dict with:
        total_points    — int, raw point score
        risk_percent    — int, estimated 10-year CVD risk (%)
        risk_category   — str, "Low" / "Intermediate" / "High"
        breakdown       — dict, individual point contributions
    """
    sex_norm = sex.lower().strip()

    # Compute individual contributions for the breakdown
    if sex_norm == "male":
        age_table = MALE_AGE_POINTS
        tc_table = MALE_TC_POINTS
        smoking_table = MALE_SMOKING_POINTS
    else:
        age_table = FEMALE_AGE_POINTS
        tc_table = FEMALE_TC_POINTS
        smoking_table = FEMALE_SMOKING_POINTS

    age_pts = _lookup_range(age, age_table)
    ag = _age_group_key(age)
    tc_pts = _lookup_range(total_cholesterol, tc_table[ag])
    hdl_pts = _lookup_range(hdl_cholesterol, HDL_POINTS)
    bp_table = BP_TREATED if bp_treated else BP_UNTREATED
    bp_pts = _lookup_range(systolic_bp, bp_table)
    smoke_pts = _lookup_age_group(age, smoking_table) if smoker else 0
    diab_pts = DIABETES_POINTS[sex_norm] if diabetic else 0

    total = age_pts + tc_pts + hdl_pts + bp_pts + smoke_pts + diab_pts
    risk_pct = points_to_risk(total, sex_norm)
    cat = risk_category(risk_pct)

    return {
        "total_points": total,
        "risk_percent": risk_pct,
        "risk_category": cat,
        "breakdown": {
            "age_points": age_pts,
            "cholesterol_points": tc_pts,
            "hdl_points": hdl_pts,
            "blood_pressure_points": bp_pts,
            "smoking_points": smoke_pts,
            "diabetes_points": diab_pts,
        },
    }


# ---------------------------------------------------------------------------
# CSV batch processing
# ---------------------------------------------------------------------------

def assess_row(row):
    """Score a single CSV row dict.

    Expected keys (case-insensitive, flexible):
        age, sex, total_cholesterol (or tc), hdl_cholesterol (or hdl),
        systolic_bp (or sbp), bp_treated (or on_bp_meds), smoker,
        diabetic (or diabetes)
    """
    def _get(*names, default=None, required=False):
        for n in names:
            for k, v in row.items():
                if k.lower().strip() == n.lower():
                    return v
        if required:
            raise ValueError(f"Missing required field (tried: {names})")
        return default

    age = int(float(_get("age", required=True)))
    sex = str(_get("sex", required=True))
    tc = float(_get("total_cholesterol", "tc", required=True))
    hdl = float(_get("hdl_cholesterol", "hdl", required=True))
    sbp = float(_get("systolic_bp", "sbp", required=True))

    bp_raw = _get("bp_treated", "on_bp_meds", "bp_medication", default="0")
    bp_treated = str(bp_raw).strip().lower() in ("1", "true", "yes", "y")

    smoke_raw = _get("smoker", "smoking", "current_smoker", default="0")
    smoker = str(smoke_raw).strip().lower() in ("1", "true", "yes", "y")

    diab_raw = _get("diabetic", "diabetes", default="0")
    diabetic = str(diab_raw).strip().lower() in ("1", "true", "yes", "y")

    return calculate_framingham(age, sex, tc, hdl, sbp, bp_treated, smoker, diabetic)


def process_csv(input_path, output_path):
    """Read a CSV of patient records, score each, write results."""
    import csv as _csv

    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = _csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    results = []
    for row in rows:
        try:
            res = assess_row(row)
            merged = {**row}
            merged["total_points"] = str(res["total_points"])
            merged["risk_percent"] = str(res["risk_percent"])
            merged["risk_category"] = res["risk_category"]
        except Exception as e:
            merged = {**row}
            merged["total_points"] = "ERROR"
            merged["risk_percent"] = "ERROR"
            merged["risk_category"] = str(e)
        results.append(merged)

    out_fields = list(fieldnames)
    for extra in ("total_points", "risk_percent", "risk_category"):
        if extra not in out_fields:
            out_fields.append(extra)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(results)

    return results
