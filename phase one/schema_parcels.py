"""
Creates/updates a `parcels` table in contacts.db
"""
import sqlite3

DB_FILE = "contacts.db"

PARCELS_SCHEMA = """
CREATE TABLE IF NOT EXISTS parcels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    county TEXT,
    state TEXT,
    parcel_id TEXT,
    situs_address TEXT,
    city TEXT,
    zip_code TEXT,
    property_class TEXT,
    owner_name TEXT,
    mailing_address1 TEXT,
    mailing_city TEXT,
    mailing_state TEXT,
    mailing_zip TEXT,
    land_sqft REAL,
    building_sqft REAL,
    assessed_value REAL,
    taxable_value REAL,
    year_built INTEGER,
    source TEXT,
    source_updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_parcels_county_state ON parcels(county, state);
"""

def ensure_db(db_path: str = DB_FILE):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(PARCELS_SCHEMA)
    conn.commit()
    conn.close()
    print(f"✅ parcels table ready in {db_path}")

if __name__ == "__main__":
    ensure_db()
