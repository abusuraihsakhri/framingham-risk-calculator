# Framingham 2008 General CVD Risk Calculator

A zero-dependency Python CLI and static web application estimating **10-year risk of first general cardiovascular disease (CVD)** using the **lipid-based Framingham model of D'Agostino et al. (2008)**. The model is intended for adults aged **30–74 without established CVD**.

This is **not** the ATP III hard-coronary-heart-disease score, the 1998 Framingham CHD score, or a contemporary ASCVD/PREVENT calculator.

## Browser application

Open **index.html** in a modern browser. GitHub Pages deployment is configured through **.github/workflows/pages.yml**; a verified live URL will be added after GitHub Pages is enabled and deployment is confirmed.

The static site supports single-person risk calculations and local CSV input/output (2 MB, maximum 5,000 rows). The webpage does not send patient data to a remote service, call external APIs, or store calculations in browser storage. Static hosting providers may log ordinary page requests. Do not include identifiable patient information when sharing exported CSVs.

## Python CLI

Python **3.10+**, standard library only; no installation required.

~~~bash
python cli.py single --age 55 --sex male --tc 220 --hdl 45 --sbp 135 --smoker --json
python cli.py batch --input sample.csv --output results.csv
python -m unittest discover -v
~~~

Use **mg/dL** for total and HDL cholesterol, **mmHg** for systolic blood pressure. Optional flags **--bp-treated**, **--smoker**, **--diabetic** default to false. Running **python cli.py** with no subcommand prints help.

CSV headers: **age,sex,tc,hdl,sbp** (alternatively **total_cholesterol**, **hdl_cholesterol**, **systolic_bp**); optional **bp_treated,smoker,diabetic**, accepted as yes/no, true/false or 1/0. Invalid rows are marked **ERROR** with a **risk_error** explanation. The batch command returns exit code 1 if any row fails.

## Algorithm and interpretation

**calculate_framingham()** returns an individual estimate via the continuous **2008 lipid-based Cox regression** (**risk_percent**, one decimal place). It additionally reports the **separate approximate published point-score model** (**total_points**, **breakdown**, **point_risk_percent**, **point_risk_label**). The point-table value can differ from the continuous estimate due to discretization and may be censored as less than 1% or greater than 30%; the numeric point-table value is then **None**.

The returned **risk_category** convention is low (below 10%), intermediate (10–20%), high (above 20%). **These descriptive categories are not treatment thresholds.** The original derivation cohort may not calibrate to modern, diverse populations; consider current applicable guidance and patient-specific factors when interpreting an estimate.

**Clinical sources**

- D'Agostino RB Sr et al. *General cardiovascular risk profile for use in primary care.* Circulation. 2008;117:743–753. [DOI:10.1161/CIRCULATIONAHA.107.699579](https://doi.org/10.1161/CIRCULATIONAHA.107.699579).
- D'Agostino RB Sr et al. *Cardiovascular disease risk assessment: insights from Framingham.* Glob Heart. 2013;8:11–23. [PMCID:PMC3673738](https://pmc.ncbi.nlm.nih.gov/articles/PMC3673738/).

## Testing and deployment

- Python: **python -m unittest discover -v**
- Browser calculation/CSV: **node --test test_browser.cjs** (Node.js 22 recommended).
- GitHub Actions runs tests for pull requests and pushes to **master**. The Pages workflow builds a static artifact on **master** and deploys it when Pages is enabled with **GitHub Actions** as its publishing source. No Python server or in-browser Python runtime is required.

Compatible with current Chromium, Firefox and Safari using JavaScript and browser File APIs. No third-party dependencies or build step.

**License:** [MIT](LICENSE).

**For research and education only.** This implementation is not independently validated or approved as stand-alone clinical decision support.
