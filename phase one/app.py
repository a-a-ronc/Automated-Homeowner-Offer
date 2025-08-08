from flask import Flask, render_template, request, Response
import sqlite3
import csv
import io

app = Flask(__name__)
DB_FILE = "contacts.db"

# --- Helper function ---
def query_parcels(county, state, max_value=None, min_sqft=None, max_sqft=None, year_min=None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = "SELECT * FROM parcels WHERE county=? AND state=?"
    params = [county, state]

    if max_value is not None:
        query += " AND (assessed_value <= ? OR taxable_value <= ?)"
        params.extend([max_value, max_value])
    if min_sqft is not None:
        query += " AND IFNULL(building_sqft,0) >= ?"
        params.append(min_sqft)
    if max_sqft is not None:
        query += " AND IFNULL(building_sqft,0) <= ?"
        params.append(max_sqft)
    if year_min is not None:
        query += " AND IFNULL(year_built,0) >= ?"
        params.append(year_min)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template("index.html")

    county = request.form.get("county")
    state = request.form.get("state")
    max_value = request.form.get("max_value")
    min_sqft = request.form.get("min_sqft")
    max_sqft = request.form.get("max_sqft")
    year_min = request.form.get("year_min")

    max_value = float(max_value) if max_value else None
    min_sqft = float(min_sqft) if min_sqft else None
    max_sqft = float(max_sqft) if max_sqft else None
    year_min = int(year_min) if year_min else None

    properties = query_parcels(county, state, max_value, min_sqft, max_sqft, year_min)
    return render_template("results.html", properties=properties, form_data=request.form)

@app.route("/export", methods=["GET"])
def export():
    county = request.args.get("county")
    state = request.args.get("state", "MI")
    max_value = request.args.get("max_value")
    min_sqft = request.args.get("min_sqft")
    max_sqft = request.args.get("max_sqft")
    year_min = request.args.get("year_min")

    max_value = float(max_value) if max_value else None
    min_sqft = float(min_sqft) if min_sqft else None
    max_sqft = float(max_sqft) if max_sqft else None
    year_min = int(year_min) if year_min else None

    rows = query_parcels(county, state, max_value, min_sqft, max_sqft, year_min)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "owner_name","mailing_address1","mailing_city","mailing_state","mailing_zip",
        "situs_address","city","state","zip_code","parcel_id",
        "building_sqft","assessed_value","taxable_value","year_built"
    ])
    for r in rows:
        writer.writerow([
            r.get("owner_name"), r.get("mailing_address1"), r.get("mailing_city"), r.get("mailing_state"), r.get("mailing_zip"),
            r.get("situs_address"), r.get("city"), r.get("state"), r.get("zip_code"), r.get("parcel_id"),
            r.get("building_sqft"), r.get("assessed_value"), r.get("taxable_value"), r.get("year_built")
        ])
    csv_data = buf.getvalue()
    buf.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=parcels_export.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)
