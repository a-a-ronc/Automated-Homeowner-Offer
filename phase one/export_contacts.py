"""
Filter parcels by criteria and export for mail-merge
"""
import argparse
import sqlite3
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="contacts.db")
    ap.add_argument("--county", required=True)
    ap.add_argument("--state", default="MI")
    ap.add_argument("--max_value", type=float)
    ap.add_argument("--min_sqft", type=float)
    ap.add_argument("--max_sqft", type=float)
    ap.add_argument("--year_min", type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    df = pd.read_sql_query(
        "SELECT * FROM parcels WHERE county=? AND state=?",
        conn, params=[args.county, args.state]
    )
    conn.close()

    if args.max_value:
        df = df[(df["assessed_value"].fillna(df["taxable_value"]) <= args.max_value)]
    if args.min_sqft:
        df = df[df["building_sqft"].fillna(0) >= args.min_sqft]
    if args.max_sqft:
        df = df[df["building_sqft"].fillna(0) <= args.max_sqft]
    if args.year_min:
        df = df[df["year_built"].fillna(0) >= args.year_min]

    df.to_csv(args.out, index=False)
    print(f"✅ Wrote {len(df)} rows to {args.out}")

if __name__ == "__main__":
    main()
