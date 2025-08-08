"""
ETL for Ottawa County, MI from their Parcel Data Export CSV
"""
import argparse
import sqlite3
import pandas as pd
from schema_parcels import ensure_db

COLMAP = {
    "parcel_id": ["parcel", "parcel number", "pnnum", "pnum", "apn", "parcelid", "parcel_id", "pid"],
    "situs_address": ["situs address", "property address", "address", "site address", "loc addr", "prop addr"],
    "city": ["city", "situs city", "prop city"],
    "state": ["state", "situs state", "prop state"],
    "zip_code": ["zip", "zipcode", "zip code", "situs zip", "prop zip"],
    "owner_name": ["owner", "owner name", "ownernamelong", "ownername", "owner1", "grantee"],
    "mailing_address1": ["mailing address", "owner address", "mail address", "mail_addr", "mailing addr1", "mailing"],
    "mailing_city": ["mailing city", "owner city", "mail city"],
    "mailing_state": ["mailing state", "owner state", "mail state"],
    "mailing_zip": ["mailing zip", "owner zip", "mail zip", "mail zipcode"],
    "assessed_value": ["assessed value", "sev", "state equalized value", "assessed"],
    "taxable_value": ["taxable value", "taxable"],
    "building_sqft": ["building sqft", "improvement sqft", "bldg sqft", "bldgsqft", "impr sq ft"],
    "year_built": ["year built", "yr built", "yearbuilt"],
    "property_class": ["property class", "class", "prop class"],
}

def pick(colnames, candidates):
    s = {c.lower(): c for c in colnames}
    for cand in candidates:
        if cand.lower() in s:
            return s[cand.lower()]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="contacts.db")
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()

    ensure_db(args.db)
    df = pd.read_csv(args.csv)
    cols = list(df.columns)
    mapping = {key: pick(cols, vals) for key, vals in COLMAP.items()}

    rows = []
    for _, row in df.iterrows():
        def v(k):
            col = mapping.get(k)
            return str(row[col]).strip() if col and pd.notna(row[col]) else None
        rows.append({
            "county": "Ottawa",
            "state": "MI",
            "parcel_id": v("parcel_id"),
            "situs_address": v("situs_address"),
            "city": v("city"),
            "zip_code": v("zip_code"),
            "property_class": v("property_class"),
            "owner_name": v("owner_name"),
            "mailing_address1": v("mailing_address1"),
            "mailing_city": v("mailing_city"),
            "mailing_state": v("mailing_state"),
            "mailing_zip": v("mailing_zip"),
            "land_sqft": None,
            "building_sqft": v("building_sqft"),
            "assessed_value": v("assessed_value"),
            "taxable_value": v("taxable_value"),
            "year_built": v("year_built"),
            "source": "Ottawa Parcel Data Export",
            "source_updated_at": None
        })

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    for r in rows:
        cur.execute("""
            INSERT INTO parcels (county,state,parcel_id,situs_address,city,zip_code,property_class,owner_name,
                mailing_address1,mailing_city,mailing_state,mailing_zip,land_sqft,building_sqft,assessed_value,
                taxable_value,year_built,source,source_updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, tuple(r.values()))
    conn.commit()
    conn.close()
    print(f"✅ Ottawa import complete. Inserted {len(rows)} rows.")

if __name__ == "__main__":
    main()
