import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re  # For extracting email

# Define the base URL for the business directory
BASE_URL = "https://business.ycea-pa.org/list/ql/business-personal-professional-services-1401"

# Set headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# Function to get the total number of pages
def get_total_pages(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the pagination section and extract the last page number
    pagination = soup.find("ul", class_="pagination")
    if pagination:
        pages = pagination.find_all("a")
        page_numbers = [int(page.text) for page in pages if page.text.isdigit()]
        return max(page_numbers) if page_numbers else 1  # Return max page number found
    return 1  # Default to 1 if no pagination is found

# Function to scrape company data from a page
def scrape_companies(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch page: {url}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    company_cards = soup.find_all("div", class_="gz-results-card-body")  # Adjusted based on your HTML

    company_data = []

    for card in company_cards:
        try:
            # Extract name
            name_tag = card.find_previous_sibling("div", class_="card-header")
            name = name_tag.text.strip() if name_tag else None

            # Extract address
            address_tag = card.find("li", class_="gz-card-address")
            address = address_tag.text.strip() if address_tag else None

            # Extract phone number
            phone_tag = card.find("li", class_="gz-card-phone")
            phone = phone_tag.text.strip() if phone_tag else None

            # Extract website
            website_tag = card.find("li", class_="gz-card-website")
            website = website_tag.find("a")["href"].strip() if website_tag and website_tag.find("a") else None

            # Extract category
            category_tag = card.find("div", class_="gz-category")
            category = category_tag.text.strip() if category_tag else None

            # Extract email (search for "mailto:")
            email_tag = card.find("a", href=re.compile(r"mailto:"))
            email = email_tag["href"].replace("mailto:", "").strip() if email_tag else None

            company_data.append({
                "Name": name,
                "Address": address,
                "Phone": phone,
                "Website": website,
                "Category": category,
                "Email": email
            })

        except Exception as e:
            print(f"Error scraping a company: {e}")

    return company_data

# Get total number of pages before scraping
total_pages = get_total_pages(BASE_URL)
print(f"Total Pages Found: {total_pages}")

# Scrape multiple pages with proper stopping condition
all_companies = []
for page_num in range(1, total_pages + 1):
    page_url = f"https://business.ycea-pa.org/list/ql/business-personal-professional-services-1401?page={page_num}"
    print(f"Scraping page {page_num} of {total_pages}...")

    page_data = scrape_companies(page_url)
    if not page_data:
        print("No more companies found. Stopping scraping.")
        break  # Stops early if no data is found on a page

    all_companies.extend(page_data)
    time.sleep(2)  # Delay to prevent getting blocked

# Save results to CSV file
df = pd.DataFrame(all_companies)
df.to_csv("ycea_business_directory.csv", index=False)

print(f"✅ Data saved to 'ycea_business_directory.csv' with {len(df)} entries.")
