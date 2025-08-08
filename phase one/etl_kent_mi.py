"""
ETL for Kent County, MI parcels (public open data)
"""
import argparse
import requests
import sqlite3
import time
from schema_parcels import ensure_db

FEATURESERVER = "https://gis.kentcountymi.gov/agisprod/rest/services/Open_Data_Kent_Co_Parcels/FeatureServer/1/query"
FIELDS = ["PNUM","PROPERTYADDRESS","PROPADDRESSCITY","PROPADDRESSSTATE_ZIPCODE","PROPERTYCLASS","OBJECTID"]

def fetch_page(result_offset=0, result_record_count=2000):
    params = {
        "where": "1=1",
        "outFields": ",".join(FIELDS),
        "f": "json",
        "returnGeometry": "false",
        "resultOffset": result_offset,
        "resultRecordCount": result_record_count,
        "orderByFields": "OBJECTID ASC"
    }
    resp = requests.get(FEATURESERVER, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()

def normalize_feature(f):
    attrs = f.get("attributes", {})
    state_zip = (attrs.get("PROPADDRESSSTATE_ZIPCODE") or "").strip()
    st, zp = None, None
    if state_zip:
        s = state_zip.replace(" ", "")
        st, zp = s[:2], s[2:]
    return {
        "county": "Kent",
        "state": "MI",
        "parcel_id": attrs.get("PNUM"),
        "situs_address": attrs.get("PROPERTYADDRESS"),
        "city": attrs.get("PROPADDRESSCITY"),
        "zip_code": zp,
        "property_class": attrs.get("PROPERTYCLASS"),
        "owner_name": None,
        "mailing_address1": None,
        "mailing_city": None,
        "mailing_state": None,
        "mailing_zip": None,
        "land_sqft": None,
        "building_sqft": None,
        "assessed_value": None,
        "taxable_value": None,
        "year_built": None,
        "source": "Kent FeatureServer 1",
        "source_updated_at": None
    }

def upsert_rows(db, rows):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    for r in rows:
        cur.execute("""
            SELECT id FROM parcels WHERE county=? AND state=? AND parcel_id=?
        """, (r["county"], r["state"], r["parcel_id"]))
        if cur.fetchone():
            cur.execute("""
                UPDATE parcels
                SET situs_address=?, city=?, zip_code=?, property_class=?, source=?, source_updated_at=?
                WHERE county=? AND state=? AND parcel_id=?
            """, (r["situs_address"], r["city"], r["zip_code"], r["property_class"], r["source"], r["source_updated_at"],
                  r["county"], r["state"], r["parcel_id"]))
        else:
            cur.execute("""
                INSERT INTO parcels (county,state,parcel_id,situs_address,city,zip_code,property_class,owner_name,
                    mailing_address1,mailing_city,mailing_state,mailing_zip,land_sqft,building_sqft,assessed_value,
                    taxable_value,year_built,source,source_updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (r["county"], r["state"], r["parcel_id"], r["situs_address"], r["city"], r["zip_code"], r["property_class"],
                  r["owner_name"], r["mailing_address1"], r["mailing_city"], r["mailing_state"], r["mailing_zip"],
                  r["land_sqft"], r["building_sqft"], r["assessed_value"], r["taxable_value"], r["year_built"],
                  r["source"], r["source_updated_at"]))
    conn.commit()
    conn.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="contacts.db")
    ap.add_argument("--pagesize", type=int, default=2000)
    ap.add_argument("--max_pages", type=int, default=999)
    args = ap.parse_args()

    ensure_db(args.db)

    result_offset = 0
    total_inserted = 0
    for _ in range(args.max_pages):
        data = fetch_page(result_offset=result_offset, result_record_count=args.pagesize)
        feats = data.get("features", [])
        if not feats:
            break
        rows = [normalize_feature(f) for f in feats]
        upsert_rows(args.db, rows)
        total_inserted += len(rows)
        result_offset += args.pagesize
        time.sleep(0.5)
    print(f"✅ Kent ETL complete. Upserted {total_inserted} records.")

if __name__ == "__main__":
    main()
