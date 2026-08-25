#!/usr/bin/env python3
"""
Command-line interface for the Framingham Risk Score Calculator.

Usage examples:

  Single patient:
    python cli.py single --age 55 --sex male --tc 210 --hdl 50 \
                         --sbp 140 --bp-treated --smoker --diabetic

  Batch CSV:
    python cli.py batch --input patients.csv --output results.csv
"""
import argparse
import json
import sys

from framingham import calculate_framingham, process_csv


def build_parser():
    p = argparse.ArgumentParser(
        prog="framingham",
        description="Framingham 10-Year Cardiovascular Risk Score Calculator",
    )
    sub = p.add_subparsers(dest="cmd")

    # --- single ---
    s = sub.add_parser("single", help="Calculate risk for a single patient")
    s.add_argument("--age", type=int, required=True, help="Age (30-74)")
    s.add_argument("--sex", required=True, choices=["male", "female"],
                   help="Biological sex")
    s.add_argument("--tc", type=float, required=True,
                   help="Total cholesterol (mg/dL)")
    s.add_argument("--hdl", type=float, required=True,
                   help="HDL cholesterol (mg/dL)")
    s.add_argument("--sbp", type=float, required=True,
                   help="Systolic blood pressure (mmHg)")
    s.add_argument("--bp-treated", action="store_true", default=False,
                   help="Patient is on blood pressure medication")
    s.add_argument("--smoker", action="store_true", default=False,
                   help="Current smoker")
    s.add_argument("--diabetic", action="store_true", default=False,
                   help="Diabetic")
    s.add_argument("--json", action="store_true", default=False,
                   help="Output as JSON")

    # --- batch ---
    b = sub.add_parser("batch", help="Batch-process a CSV file")
    b.add_argument("-i", "--input", required=True, help="Input CSV path")
    b.add_argument("-o", "--output", default="results.csv",
                   help="Output CSV path (default: results.csv)")

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None:
        parser.print_help()
        return 1

    if args.cmd == "single":
        result = calculate_framingham(
            age=args.age,
            sex=args.sex,
            total_cholesterol=args.tc,
            hdl_cholesterol=args.hdl,
            systolic_bp=args.sbp,
            bp_treated=args.bp_treated,
            smoker=args.smoker,
            diabetic=args.diabetic,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Framingham 10-Year CVD Risk Assessment")
            print(f"{'='*42}")
            print(f"  Total Points:    {result['total_points']}")
            print(f"  10-Year Risk:    {result['risk_percent']}%")
            print(f"  Risk Category:   {result['risk_category']}")
            print(f"  Breakdown:")
            for k, v in result["breakdown"].items():
                label = k.replace("_", " ").title()
                print(f"    {label:.<30} {v:+d}")
        return 0

    if args.cmd == "batch":
        results = process_csv(args.input, args.output)
        print(f"Processed {len(results)} records -> {args.output}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
