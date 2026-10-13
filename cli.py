#!/usr/bin/env python3
"""Command-line interface for Framingham 2008 general CVD risk."""
import argparse
import json
import sys
from framingham import calculate_framingham,process_csv


def build_parser():
    parser=argparse.ArgumentParser(prog="framingham",description="Framingham 2008 10-year general CVD (lipid model)")
    subs=parser.add_subparsers(dest="cmd")
    single=subs.add_parser("single",help="Assess a CVD-free adult aged 30-74")
    single.add_argument("--age",required=True,type=int)
    single.add_argument("--sex",required=True,choices=["male","female"])
    single.add_argument("--tc",required=True,type=float,help="Total cholesterol mg/dL")
    single.add_argument("--hdl",required=True,type=float,help="HDL cholesterol mg/dL")
    single.add_argument("--sbp",required=True,type=float,help="Systolic BP mmHg")
    single.add_argument("--bp-treated",action="store_true")
    single.add_argument("--smoker",action="store_true")
    single.add_argument("--diabetic",action="store_true")
    single.add_argument("--json",action="store_true")
    batch=subs.add_parser("batch",help="Process CSV rows")
    batch.add_argument("-i","--input",required=True)
    batch.add_argument("-o","--output",default="results.csv")
    return parser


def main(argv=None):
    parser=build_parser()
    args=parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return 1
    try:
        if args.cmd=="batch":
            rows=process_csv(args.input,args.output)
            invalid=sum(bool(x["risk_error"]) for x in rows)
            print(f"Processed {len(rows)} records ({invalid} invalid) -> {args.output}")
            return 0 if not invalid else 1
        result=calculate_framingham(args.age,args.sex,args.tc,args.hdl,args.sbp,
                                   args.bp_treated,args.smoker,args.diabetic)
    except (ValueError,OSError,OverflowError) as exc:
        print(f"Error: {exc}",file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result,indent=2))
    else:
        print("Framingham 2008 General CVD (10-year, lipid model)")
        print(f"  Continuous risk: {result['risk_percent']:.1f}%")
        print(f"  Point score: {result['total_points']} (tabulated {result['point_risk_label']})")
        print(f"  Descriptive risk category: {result['risk_category']}")
        for key,value in result["breakdown"].items():
            print(f"  {key.replace('_',' '):<25} {value:+d}")
        print("Educational and research use; not a standalone clinical decision rule.")
    return 0


if __name__=="__main__":
    sys.exit(main())
