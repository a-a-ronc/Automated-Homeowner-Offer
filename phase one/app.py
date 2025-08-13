from flask import Flask, render_template, request, Response, session, redirect, url_for, flash, jsonify
import sqlite3
import csv
import io
import hashlib
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import re
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
DB_FILE = os.path.join(os.path.dirname(__file__), "contacts.db")

# Email configuration - set these in Replit Secrets
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

def init_users_table():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            county TEXT,
            state TEXT,
            max_value REAL,
            offer_percentage REAL DEFAULT 60,
            test_mode BOOLEAN DEFAULT FALSE,
            test_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS campaign_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            parcel_id TEXT,
            owner_name TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            mailing_address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            property_address TEXT,
            assessed_value REAL,
            email_sent BOOLEAN DEFAULT FALSE,
            letter_generated BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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

def find_email_address(first_name, last_name, address, city, state, test_mode=False):
    """Attempt to find email address using various methods"""
    # This is a simplified version - in production you'd use services like:
    # - Hunter.io API
    # - Clearbit API
    # - People search APIs

    if test_mode:
        # In test mode, generate predictable test emails
        if first_name and last_name:
            return f"test.{first_name.lower()}.{last_name.lower()}@example.com"
        return None

    # For demo purposes, we'll simulate finding some emails
    common_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']

    if first_name and last_name:
        # Try common email patterns
        patterns = [
            f"{first_name.lower()}.{last_name.lower()}",
            f"{first_name.lower()}{last_name.lower()}",
            f"{first_name[0].lower()}{last_name.lower()}",
            f"{first_name.lower()}{last_name[0].lower()}"
        ]

        # Simulate 30% success rate for demo
        import random
        if random.random() < 0.3:
            pattern = random.choice(patterns)
            domain = random.choice(common_domains)
            return f"{pattern}@{domain}"

    return None

def parse_owner_name(owner_name):
    """Extract first and last name from owner name"""
    if not owner_name:
        return None, None

    # Remove common suffixes and prefixes
    cleaned = re.sub(r'\b(LLC|INC|CORP|TRUST|ESTATE|ET AL|ETAL)\b', '', owner_name.upper())
    cleaned = re.sub(r'[,&].*', '', cleaned)  # Remove everything after comma or &

    parts = cleaned.strip().split()
    if len(parts) >= 2:
        return parts[0].title(), parts[-1].title()
    elif len(parts) == 1:
        return parts[0].title(), ""

    return None, None

def generate_ai_letter(first_name, last_name, property_address, assessed_value, offer_percentage):
    """Generate AI-powered letter content"""
    offer_amount = int(assessed_value * (offer_percentage / 100)) if assessed_value else "competitive cash"

    letter_template = f"""
{datetime.now().strftime('%B %d, %Y')}

Dear {first_name} {last_name},

I hope this letter finds you well. My name is [YOUR NAME], and I am a local real estate investor who specializes in purchasing homes for cash.

I am writing to you today because I am interested in purchasing your property located at {property_address}. I understand that selling a home can be a significant decision, and I want to make the process as simple and stress-free as possible for you.

Here's what I can offer:

• Cash purchase - no financing contingencies
• Quick closing (as fast as 7-14 days)
• No real estate agent commissions or fees
• Purchase the property in its current condition - no need for repairs or improvements
• Flexible closing date to accommodate your timeline

Based on my analysis of your property and current market conditions, I would like to offer ${offer_amount:,} for your home. This is a cash offer with no financing contingencies, meaning we can close quickly and with certainty.

I understand this may be an unexpected offer, but I have found that many homeowners appreciate having this option available to them, especially when they need to sell quickly or want to avoid the traditional real estate process.

If you're interested in learning more about this opportunity, please feel free to contact me at [YOUR PHONE] or [YOUR EMAIL]. I would be happy to answer any questions you may have and discuss the details further.

Even if you're not ready to sell now, please keep my information for future reference. I am always looking for properties in the area and would be interested in hearing from you whenever you might be ready to sell.

Thank you for your time and consideration.

Sincerely,

[YOUR NAME]
[YOUR COMPANY]
[YOUR PHONE]
[YOUR EMAIL]

P.S. This is a no-obligation offer. I understand that selling your home is a big decision, and I respect whatever choice you make.
"""

    return letter_template.strip()

@app.route("/", methods=["GET"])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        flash("Please enter both username and password")
        return render_template("login.html")

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # Check if user exists
    cur.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    
    print(f"Debug: Looking for user '{username}'")
    print(f"Debug: User found: {user is not None}")
    
    if user:
        stored_hash = user[1]
        provided_hash = hash_password(password)
        print(f"Debug: Password hashes match: {stored_hash == provided_hash}")
        
        if stored_hash == provided_hash:
            session['user_id'] = user[0]
            session['username'] = username
            conn.close()
            return redirect(url_for('index'))
    
    conn.close()
    flash("Invalid username or password")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not username or not password:
        flash("Please enter username and password")
        return render_template("register.html")

    if password != confirm_password:
        flash("Passwords do not match")
        return render_template("register.html")

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        password_hash = hash_password(password)
        print(f"Debug: Registering user '{username}' with hash: {password_hash}")
        
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                   (username, password_hash))
        conn.commit()
        
        print(f"Debug: User '{username}' registered successfully")
        flash("Registration successful! Please log in.")
        return redirect(url_for('login'))
    except sqlite3.IntegrityError as e:
        print(f"Debug: Registration failed for '{username}': {e}")
        flash("Username already exists")
        return render_template("register.html")
    except Exception as e:
        print(f"Debug: Unexpected error during registration: {e}")
        flash("Registration failed. Please try again.")
        return render_template("register.html")
    finally:
        conn.close()

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/search", methods=["GET", "POST"])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == "GET":
        return render_template("search.html")

    county = request.form.get("county")
    state = request.form.get("state", "MI")
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

@app.route("/create_campaign", methods=["POST"])
def create_campaign():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    data = request.get_json()
    county = data.get("county")
    state = data.get("state", "MI")
    max_value = data.get("max_value")
    offer_percentage = data.get("offer_percentage", 60)
    campaign_name = data.get("campaign_name", f"{county} Campaign")
    test_mode = data.get("test_mode", False)
    test_email = data.get("test_email", "")

    # Create campaign
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO campaigns (user_id, name, county, state, max_value, offer_percentage, test_mode, test_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session['user_id'], campaign_name, county, state, max_value, offer_percentage, test_mode, test_email))

    campaign_id = cur.lastrowid

    # Get properties
    properties = query_parcels(county, state, max_value)

    # Process each property
    contacts_added = 0
    for prop in properties:
        if not prop.get('owner_name'):
            continue

        first_name, last_name = parse_owner_name(prop['owner_name'])
        if not first_name:
            continue

        # Try to find email
        email = find_email_address(
            first_name, last_name, 
            prop.get('situs_address', ''),
            prop.get('city', ''),
            prop.get('state', ''),
            test_mode=test_mode
        )

        # Add to campaign contacts
        cur.execute("""
            INSERT INTO campaign_contacts 
            (campaign_id, parcel_id, owner_name, first_name, last_name, email, 
             mailing_address, city, state, zip_code, property_address, assessed_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_id, prop.get('parcel_id'), prop.get('owner_name'),
            first_name, last_name, email,
            prop.get('mailing_address1', ''), prop.get('mailing_city', ''),
            prop.get('mailing_state', ''), prop.get('mailing_zip', ''),
            prop.get('situs_address', ''), prop.get('assessed_value')
        ))
        contacts_added += 1

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'campaign_id': campaign_id,
        'contacts_added': contacts_added,
        'test_mode': test_mode
    })

@app.route("/campaigns")
def campaigns():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT c.*, 
               COUNT(cc.id) as total_contacts,
               COUNT(CASE WHEN cc.email IS NOT NULL THEN 1 END) as with_email,
               COUNT(CASE WHEN cc.email_sent = 1 THEN 1 END) as emails_sent
        FROM campaigns c
        LEFT JOIN campaign_contacts cc ON c.id = cc.campaign_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """, (session['user_id'],))

    campaigns_data = cur.fetchall()
    conn.close()

    return render_template("campaigns.html", campaigns=campaigns_data)

@app.route("/campaign/<int:campaign_id>")
def campaign_detail(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get campaign info
    cur.execute("SELECT * FROM campaigns WHERE id = ? AND user_id = ?", 
                (campaign_id, session['user_id']))
    campaign = cur.fetchone()

    if not campaign:
        flash("Campaign not found")
        return redirect(url_for('campaigns'))

    # Get contacts
    cur.execute("""
        SELECT * FROM campaign_contacts 
        WHERE campaign_id = ? 
        ORDER BY email IS NOT NULL DESC, last_name
    """, (campaign_id,))
    contacts = cur.fetchall()

    conn.close()

    return render_template("campaign_detail.html", campaign=campaign, contacts=contacts)

@app.route("/send_emails/<int:campaign_id>", methods=["POST"])
def send_emails(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Get campaign info
    cur.execute("SELECT test_mode, test_email FROM campaigns WHERE id = ?", (campaign_id,))
    campaign_info = cur.fetchone()
    test_mode = campaign_info[0] if campaign_info else False
    test_email = campaign_info[1] if campaign_info else ""

    if test_mode:
        if not test_email:
            return jsonify({'success': False, 'error': 'Test email not provided'})

        # In test mode, send one sample email to the test address
        cur.execute("""
            SELECT cc.*, c.offer_percentage 
            FROM campaign_contacts cc
            JOIN campaigns c ON cc.campaign_id = c.id
            WHERE cc.campaign_id = ? AND cc.email IS NOT NULL
            LIMIT 1
        """, (campaign_id,))
        contact = cur.fetchone()

        if not contact:
            return jsonify({'success': False, 'error': 'No contacts with emails found'})

        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            # Create test email
            msg = MIMEMultipart()
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = test_email
            msg['Subject'] = f"TEST EMAIL - Cash Offer for Property at {contact[10]}"

            # Email body with test notice
            body = f"""
*** THIS IS A TEST EMAIL - NOT SENT TO ACTUAL PROPERTY OWNER ***

This is how your email would look when sent to: {contact[4]} {contact[5]}
Original email would go to: {contact[6]}

---

Dear {contact[4]} {contact[5]},

I hope this email finds you well. I am a local real estate investor, and I'm interested in purchasing your property at {contact[10]} for cash.

I can offer you a quick, hassle-free sale with:
• Cash purchase - no financing contingencies
• Quick closing (7-14 days)
• No real estate agent fees
• Buy as-is condition

Based on current market conditions, I can offer ${contact[12] * (contact[13]/100):,.0f} cash for your property.

If you're interested in learning more, please reply to this email or call me.

Best regards,
[Your Name]
[Your Phone]

---
*** END TEST EMAIL ***
            """.strip()

            msg.attach(MIMEText(body, 'plain'))
            server.send_message(msg)
            server.quit()

            return jsonify({'success': True, 'emails_sent': 1, 'test_mode': True, 'message': f'Test email sent to {test_email}'})

        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to send test email: {str(e)}'})
        finally:
            conn.close()

    else:
        # Production mode - send actual emails
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            return jsonify({'success': False, 'error': 'Email credentials not configured'})

        # Get campaign and contacts with emails
        cur.execute("""
            SELECT cc.*, c.offer_percentage 
            FROM campaign_contacts cc
            JOIN campaigns c ON cc.campaign_id = c.id
            WHERE cc.campaign_id = ? AND cc.email IS NOT NULL AND cc.email_sent = 0
        """, (campaign_id,))

        contacts = cur.fetchall()

        emails_sent = 0
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            for contact in contacts:
                try:
                    # Create email
                    msg = MIMEMultipart()
                    msg['From'] = EMAIL_ADDRESS
                    msg['To'] = contact[6]  # email
                    msg['Subject'] = f"Cash Offer for Your Property at {contact[10]}"  # property_address

                    # Email body
                    body = f"""
Dear {contact[4]} {contact[5]},

I hope this email finds you well. I am a local real estate investor, and I'm interested in purchasing your property at {contact[10]} for cash.

I can offer you a quick, hassle-free sale with:
• Cash purchase - no financing contingencies
• Quick closing (7-14 days)
• No real estate agent fees
• Buy as-is condition

Based on current market conditions, I can offer ${contact[12] * (contact[13]/100):,.0f} cash for your property.

If you're interested in learning more, please reply to this email or call me.

Best regards,
[Your Name]
[Your Phone]
                    """.strip()

                    msg.attach(MIMEText(body, 'plain'))

                    server.send_message(msg)

                    # Mark as sent
                    cur.execute("UPDATE campaign_contacts SET email_sent = 1 WHERE id = ?", (contact[0],))
                    emails_sent += 1

                    time.sleep(1)  # Rate limiting

                except Exception as e:
                    print(f"Failed to send email to {contact[6]}: {e}")

            server.quit()
            conn.commit()

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        finally:
            conn.close()

        return jsonify({'success': True, 'emails_sent': emails_sent, 'test_mode': False})

@app.route("/generate_letters/<int:campaign_id>")
def generate_letters(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get campaign and contacts without emails
    cur.execute("""
        SELECT cc.*, c.offer_percentage 
        FROM campaign_contacts cc
        JOIN campaigns c ON cc.campaign_id = c.id
        WHERE cc.campaign_id = ? AND (cc.email IS NULL OR cc.email = '')
    """, (campaign_id,))

    contacts = cur.fetchall()

    letters = []
    for contact in contacts:
        letter_content = generate_ai_letter(
            contact['first_name'],
            contact['last_name'],
            contact['property_address'],
            contact['assessed_value'],
            contact['offer_percentage']
        )

        letters.append({
            'contact': dict(contact),
            'letter': letter_content
        })

        # Mark letter as generated
        cur.execute("UPDATE campaign_contacts SET letter_generated = 1 WHERE id = ?", (contact['id'],))

    conn.commit()
    conn.close()

    return render_template("letters.html", letters=letters, campaign_id=campaign_id)

@app.route("/export/<int:campaign_id>")
def export_campaign(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT first_name, last_name, email, mailing_address, city, state, zip_code,
               property_address, assessed_value, email_sent, letter_generated
        FROM campaign_contacts 
        WHERE campaign_id = ?
    """, (campaign_id,))

    rows = cur.fetchall()
    conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "First Name", "Last Name", "Email", "Mailing Address", "City", "State", "Zip",
        "Property Address", "Assessed Value", "Email Sent", "Letter Generated"
    ])

    for row in rows:
        writer.writerow(row)

    csv_data = buf.getvalue()
    buf.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_export.csv"}
    )

def init_database():
    """Initialize all database tables"""
    init_users_table()

if __name__ == "__main__":
    init_database()
    app.run(host="0.0.0.0", port=5000, debug=True)