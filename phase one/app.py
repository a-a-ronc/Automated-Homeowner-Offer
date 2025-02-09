from flask import Flask, render_template, request
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re

# Dictionary mapping (county, state) to Redfin county ID
RED_FIN_COUNTY_IDS = {
    ("Alcona", "MI"): "1820",
    ("Alger", "MI"): "1821",
    ("Allegan", "MI"): "1822",
    ("Alpena", "MI"): "1823",
    ("Antrim", "MI"): "1824",
    ("Arenac", "MI"): "1825",
    ("Baraga", "MI"): "1826",
    ("Barry", "MI"): "1827",
    ("Bay", "MI"): "1828",
    ("Benzie", "MI"): "1829",
    ("Berrien", "MI"): "1830",
    ("Branch", "MI"): "1831",
    ("Calhoun", "MI"): "1832",
    ("Cass", "MI"): "1833",
    ("Charlevoix", "MI"): "1834",
    ("Cheboygan", "MI"): "1835",
    ("Chippewa", "MI"): "1836",
    ("Clare", "MI"): "1837",
    ("Clinton", "MI"): "1838",
    ("Crawford", "MI"): "1839",
    ("Delta", "MI"): "1840",
    ("Dickinson", "MI"): "1841",
    ("Eaton", "MI"): "1842",
    ("Emmet", "MI"): "1843",
    ("Genesee", "MI"): "1844",
    ("Gladwin", "MI"): "1845",
    ("Gogebic", "MI"): "1846",
    ("Grand Traverse", "MI"): "1847",
    ("Gratiot", "MI"): "1848",
    ("Hillsdale", "MI"): "1849",
    ("Houghton", "MI"): "1850",
    ("Huron", "MI"): "1851",
    ("Ingham", "MI"): "1852",
    ("Ionia", "MI"): "1853",
    ("Iosco", "MI"): "1854",
    ("Iron", "MI"): "1855",
    ("Isabella", "MI"): "1856",
    ("Jackson", "MI"): "1857",
    ("Kalamazoo", "MI"): "1858",
    ("Kalkaska", "MI"): "1859",
    ("Kent", "MI"): "1860",
    ("Keweenaw", "MI"): "1861",
    ("Lake", "MI"): "1862",
    ("Lapeer", "MI"): "1863",
    ("Leelanau", "MI"): "1864",
    ("Lenawee", "MI"): "1865",
    ("Livingston", "MI"): "1866",
    ("Luce", "MI"): "1867",
    ("Mackinac", "MI"): "1868",
    ("Macomb", "MI"): "1869",
    ("Manistee", "MI"): "1870",
    ("Marquette", "MI"): "1871",
    ("Mason", "MI"): "1872",
    ("Mecosta", "MI"): "1873",
    ("Menominee", "MI"): "1874",
    ("Midland", "MI"): "1875",
    ("Missaukee", "MI"): "1876",
    ("Monroe", "MI"): "1877",
    ("Montcalm", "MI"): "1878",
    ("Montmorency", "MI"): "1879",
    ("Muskegon", "MI"): "1880",
    ("Newaygo", "MI"): "1881",
    ("Oakland", "MI"): "1882",
    ("Oceana", "MI"): "1883",
    ("Ogemaw", "MI"): "1884",
    ("Ontonagon", "MI"): "1885",
    ("Osceola", "MI"): "1886",
    ("Oscoda", "MI"): "1887",
    ("Otsego", "MI"): "1888",
    ("Ottawa", "MI"): "1889",
    ("Presque Isle", "MI"): "1890",
    ("Roscommon", "MI"): "1891",
    ("Saginaw", "MI"): "1892",
    ("St. Clair", "MI"): "1893",
    ("St. Joseph", "MI"): "1894",
    ("Sanilac", "MI"): "1895",
    ("Schoolcraft", "MI"): "1896",
    ("Shiawassee", "MI"): "1897",
    ("Tuscola", "MI"): "1898",
    ("Van Buren", "MI"): "1899",
    ("Washtenaw", "MI"): "1900",
    ("Wayne", "MI"): "1901",
    ("Wexford", "MI"): "1902"
}


# Load environment variables (for email credentials)
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Initialize Flask app
app = Flask(__name__)

### 🔹 Function to Get Redfin County ID ###
def get_redfin_county_id(county, state):
    """Gets the Redfin county ID from a known dictionary."""
    key = (county, state.upper())  # Normalize input

    if key in RED_FIN_COUNTY_IDS:
        print(f"Using known County ID: {RED_FIN_COUNTY_IDS[key]}")
        return RED_FIN_COUNTY_IDS[key]
    
    print("Error: County ID not found in dictionary. Consider adding it manually.")
    return None


### 🔹 Function to Fetch Properties ###
def fetch_properties_redfin(county, state, max_price, max_sqft="4k-sqft"):
    """Fetch properties from Redfin using county name, state, and search filters."""

    # Get the Redfin County ID from the dictionary
    county_id = get_redfin_county_id(county, state)

    if not county_id:
        print("Error: Could not retrieve county ID.")
        return []

    # Convert user input into a Redfin-friendly format
    formatted_county = county.replace(" ", "-")
    formatted_state = state.upper()
    formatted_max_price = f"{max_price}k"

    # Construct the correct Redfin URL
    search_url = f"https://www.redfin.com/county/{county_id}/{formatted_state}/{formatted_county}/filter/property-type=house,max-price={formatted_max_price},max-sqft={max_sqft}"

    print(f"Scraping Redfin URL: {search_url}")  # Debugging Output

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(search_url)
    time.sleep(5)  # Allow JavaScript to load

    properties = []
    listings = driver.find_elements(By.CLASS_NAME, "bp-Homecard__Content")  # Updated class for property container

    for listing in listings:
        try:
            # Find price using updated class name
            price_text = listing.find_element(By.CLASS_NAME, "bp-Homecard__Price--value").text
            price = int(price_text.replace("$", "").replace(",", ""))  # Convert price to int

            # Find address using updated class
            address = listing.find_element(By.CLASS_NAME, "bp-Homecard__Address").text

            properties.append({"address": address, "price": price})
        except Exception as e:
            print(f"Error extracting property: {e}")
            continue

    driver.quit()
    print("Filtered Properties:", properties)
    return properties



### 🔹 Flask Route to Handle User Input ###
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        home_value = request.form.get("home_value").replace("$", "").replace(",", "")  # Clean price input
        county = request.form.get("county")  # Get county name from user
        state = request.form.get("state")  # Get state from user
        
        properties = fetch_properties_redfin(county, state, home_value)

        print("Final Filtered Properties:", properties)  # Debugging Output

        return render_template("results.html", properties=properties)

    return render_template("index.html")

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)


# def send_email(to_email, home_value, offer_price):
#     msg = EmailMessage()
#     msg["Subject"] = "Cash Offer for Your Home"
#     msg["From"] = EMAIL_ADDRESS
#     msg["To"] = to_email
#     msg.set_content(f"Hello, I am interested in purchasing your home for ${offer_price}. Please let me know if you're interested!")

#     with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
#         server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
#         server.send_message(msg)

# app = Flask(__name__)
