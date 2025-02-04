from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import os 
from dotenv import load_dotenv

load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_email(to_email, home_value, offer_price):
    msg = EmailMessage()
    msg["Subject"] = "Cash Offer for Your Home"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(f"Hello, I am interested in purchasing your home for ${offer_price}. Please let me know if you're interested!")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

app = Flask(__name__)

# Function to fetch properties (Scrapes Realtor.com as an example)
def fetch_properties(county, max_price, max_size):
    search_url = f"https://www.realtor.com/realestateandhomes-search/{county}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    properties = []

    for listing in soup.find_all("div", class_="property-card"):
        try:
            price = listing.find("span", class_="price").text.replace("$", "").replace(",", "")
            address = listing.find("span", class_="address").text
            size = listing.find("span", class_="sqft").text.replace("sq ft", "").replace(",", "").strip()
            
            if int(price) <= int(max_price) and int(size) <= int(max_size):
                properties.append({"address": address, "price": price, "size": size})
        except:
            continue

    return properties

# Function to get homeowner info from county records
def get_owner_info(address):
    county_search_url = f"https://www.example-county.gov/property-search?query={address.replace(' ', '+')}"
    response = requests.get(county_search_url)

    soup = BeautifulSoup(response.text, "html.parser")
    try:
        owner_name = soup.find("div", class_="owner-name").text
        return owner_name
    except:
        return "Unknown Owner"

# Function to send automated email offers
# def send_email(to_email, home_value, offer_price):
#     msg = EmailMessage()
#     msg["Subject"] = "Cash Offer for Your Home"
#     msg["From"] = "youremail@gmail.com"
#     msg["To"] = to_email
#     msg.set_content(f"Hello, I am interested in purchasing your home for ${offer_price}. Please let me know if you're interested!")

#     with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
#         server.login("youremail@gmail.com", "yourpassword")
#         server.send_message(msg)

def send_email(to_email, home_value, offer_price):
    print(f"\n=== Email Preview ===\nTo: {to_email}\nSubject: Cash Offer for Your Home")
    print(f"Body: Hello, I am interested in purchasing your home for ${offer_price}. Please let me know if you're interested!\n")


# @app.route("/", methods=["GET", "POST"])
# def home():
#     if request.method == "POST":
#         home_value = request.form.get("home_value")
#         home_size = request.form.get("home_size")
#         area = request.form.get("area")

#         properties = fetch_properties(area, home_value, home_size)

#         for prop in properties:
#             owner_name = get_owner_info(prop["address"])
#             prop["owner"] = owner_name

#             # Example email sending (replace with real email lookup)
#             email = "homeowner@example.com"
#             offer_price = int(prop["price"]) * 0.6
#             send_email(email, prop["price"], offer_price)

#         return render_template("results.html", properties=properties)

#     return render_template("index.html")
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        home_value = request.form.get("home_value")
        home_size = request.form.get("home_size")
        area = request.form.get("area")

        properties = fetch_properties(area, home_value, home_size)

        # Debugging - Print results to terminal before rendering
        print("Scraped Properties:", properties)

        return render_template("results.html", properties=properties)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
