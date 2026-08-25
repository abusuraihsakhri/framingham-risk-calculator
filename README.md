# Framingham Risk Score Calculator

A Python implementation of the Framingham 10-Year Cardiovascular Disease (CVD) Risk Score, based on the sex-specific point-based model published in:

> D'Agostino RB Sr, Vasan RS, Pencina MJ, et al.
> "General Cardiovascular Risk Profile for Use in Primary Care."
> *Circulation*. 2008;111(6):751-756.

## What It Does

Estimates a patient's 10-year risk of cardiovascular disease (coronary death, myocardial infarction, coronary insufficiency, angina, ischemic stroke, hemorrhagic stroke, heart failure, peripheral artery disease) using these factors:

| Factor | Values |
|--------|--------|
| Age | 30-74 years |
| Sex | Male / Female |
| Total Cholesterol | mg/dL |
| HDL Cholesterol | mg/dL |
| Systolic Blood Pressure | mmHg |
| BP Treatment | On medication or not |
| Smoking Status | Current smoker or not |
| Diabetes | Yes or no |

Risk categories:
- **Low**: < 10%
- **Intermediate**: 10-20%
- **High**: > 20%

## Requirements

Python 3.8+ (stdlib only — no third-party packages).

## Usage

### Single Patient (CLI)

```bash
python cli.py single --age 55 --sex male --tc 210 --hdl 50 \
                     --sbp 140 --bp-treated --smoker --diabetic
```

Output:
```
Framingham 10-Year CVD Risk Assessment
==========================================
  Total Points:    16
  10-Year Risk:    47%
  Risk Category:   High
  Breakdown:
    Age Points..................... +5
    Cholesterol Points............ +3
    Hdl Points.................... -1
    Blood Pressure Points......... +5
    Smoking Points................ +1
    Diabetes Points............... +3
```

Add `--json` for machine-readable output.

### Batch CSV Processing

```bash
python cli.py batch --input patients.csv --output results.csv
```

The input CSV must have these columns: `age`, `sex`, `total_cholesterol` (or `tc`), `hdl_cholesterol` (or `hdl`), `systolic_bp` (or `sbp`). Optional columns: `bp_treated`, `smoker`, `diabetic` (accept `1`/`true`/`yes`).

The output CSV appends `total_points`, `risk_percent`, and `risk_category` columns.

### Python API

```python
from framingham import calculate_framingham

result = calculate_framingham(
    age=55, sex="male", total_cholesterol=210, hdl_cholesterol=50,
    systolic_bp=140, bp_treated=True, smoker=True, diabetic=True,
)
print(result["risk_percent"])   # 47
print(result["risk_category"])  # "High"
print(result["breakdown"])      # individual point contributions
```

## Running Tests

```bash
python -m pytest test_framingham.py -v
```

## Limitations

- Valid only for ages 30-74.
- Based on the 2008 general CVD model (not the older CHD-only model).
- Does not account for family history, CRP, coronary calcium score, or other modifiers.
- Not a substitute for clinical judgment.

## License

MIT
