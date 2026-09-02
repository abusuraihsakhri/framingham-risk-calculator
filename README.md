# Framingham Risk Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Framingham Risk Score Calculator — 10-Year Cardiovascular Disease Risk.

Implements the sex-specific point-based model from:
  D'Agostino RB Sr, Vasan RS, Pencina MJ, et al.
  "General Cardiovascular Risk Profile for Use in Primary Care."
  Circulation. 2008;111(6):751-756.

Valid for ages 30-74. Uses lipids, blood pressure (treated vs untreated),
smoking status, and diabetes status.

Stdlib only — no third-party dependencies.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`calculate_points()`**: Compute the Framingham Risk Score point total.

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
- **`points_to_risk()`**: Convert a point total to a 10-year CVD risk percentage.

Returns an integer percentage. Points below the table minimum return 1%;
points above the table maximum return 56% (male) or 30% (female).
- **`risk_category()`**: Classify risk percentage into Low / Intermediate / High.

Low:          < 10%
Intermediate: 10-20%
High:         > 20%
- **`calculate_framingham()`**: Full Framingham Risk Score calculation.

Returns a dict with:
    total_points    — int, raw point score
    risk_percent    — int, estimated 10-year CVD risk (%)
    risk_category   — str, "Low" / "Intermediate" / "High"
    breakdown       — dict, individual point contributions
- **`assess_row()`**: Score a single CSV row dict.

Expected keys (case-insensitive, flexible):
    age, sex, total_cholesterol (or tc), hdl_cholesterol (or hdl),
    systolic_bp (or sbp), bp_treated (or on_bp_meds), smoker,
    diabetic (or diabetes)

---

## 📐 Mathematical Formulation & Logic

```text
  return (30, 39)
  return (40, 49)
  return (50, 59)
  return (60, 69)
  return (70, 79)
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --age <value> --sex <value> --tc <value> --hdl <value>
```

### Parameter Reference
- `--age`: Specifies input measurement or parameter value.
- `--sex`: Specifies input measurement or parameter value.
- `--tc`: Specifies input measurement or parameter value.
- `--hdl`: Specifies input measurement or parameter value.
- `--sbp`: Specifies input measurement or parameter value.
- `--bp-treated`: Specifies input measurement or parameter value.
- `--smoker`: Specifies input measurement or parameter value.
- `--diabetic`: Specifies input measurement or parameter value.
- `--input`: Specifies input measurement or parameter value.
- `--output`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `age` | Parameter / observation metric | Required |
| `sex` | Parameter / observation metric | Required |
| `tc` | Parameter / observation metric | Required |
| `hdl` | Parameter / observation metric | Required |
| `sbp` | Parameter / observation metric | Required |
| `bp_treated` | Parameter / observation metric | Required |
| `smoker` | Parameter / observation metric | Required |
| `diabetic` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t framingham-risk-calculator .
docker run -p 8000:8000 framingham-risk-calculator
```
