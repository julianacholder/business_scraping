import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# Define the base URL
BASE_URL = "https://business.ycea-pa.org"

# Headers to mimic a real browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# Function to scrape businesses from the main list
def scrape_businesses(max_pages=10):  # Add a max_pages parameter with a default value
    businesses = []
    page_num = 1

    while page_num <= max_pages:  # Add a maximum page limit as a safety measure
        url = f"{BASE_URL}/list/ql/business-personal-professional-services-1401?page={page_num}"
        print(f"🔍 Scraping page {page_num}...")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)  # Add timeout
            if response.status_code != 200:
                print(f"⚠ Received status code {response.status_code}. Stopping.")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            company_cards = soup.find_all("div", class_="gz-results-card-body")
            
            # Improved stopping condition
            if not company_cards:
                print("✅ No more businesses found. Stopping scraper.")
                break
                
            # Check if we've reached a pagination indicator suggesting we're at the end
            pagination = soup.find("ul", class_="pagination")
            if pagination and "next" not in pagination.text.lower():
                print("✅ Reached the last page. Stopping scraper.")
                break
                
            # Add a progress counter
            print(f"Found {len(company_cards)} businesses on this page")

            for card in company_cards:
                try:
                    # Extract business name and detail page link
                    name_tag = card.find_previous_sibling("h5", class_="gz-card-title")
                    name = name_tag.text.strip() if name_tag else None
                    detail_link_tag = name_tag.find("a") if name_tag else None
                    detail_link = BASE_URL + detail_link_tag["href"] if detail_link_tag else None

                    # Extract address
                    address_tag = card.find("li", class_="gz-card-address")
                    address = address_tag.text.strip() if address_tag else None

                    # Extract phone number
                    phone_tag = card.find("li", class_="gz-card-phone")
                    phone = phone_tag.text.strip() if phone_tag else None

                    # Extract Google Maps link for address
                    maps_link_tag = address_tag.find("a") if address_tag else None
                    maps_link = maps_link_tag["href"] if maps_link_tag else None

                    # Extract email, category, and website from business detail page
                    email, category, website = scrape_business_details(detail_link) if detail_link else (None, None, None)

                    businesses.append({
                        "Name": name,
                        "Address": address,
                        "Phone": phone,
                        "Google Maps Link": maps_link,
                        "Category": category,
                        "Email": email,
                        "Website": website,
                        "Detail Page": detail_link
                    })

                except Exception as e:
                    print(f"⚠ Error scraping a company: {e}")

            # Save intermediate results every few pages
            if page_num % 5 == 0:
                temp_df = pd.DataFrame(businesses)
                temp_df.to_csv(f"ycea_businesses_temp_page_{page_num}.csv", index=False)
                print(f"✅ Intermediate data saved with {len(temp_df)} entries.")

            page_num += 1  # Move to the next page
            time.sleep(2)  # Delay to avoid getting blocked
            
        except Exception as e:
            print(f"⚠ Error scraping page {page_num}: {e}")
            # If we encounter an error, try one more time before moving on
            try:
                print(f"Retrying page {page_num}...")
                time.sleep(5)  # Wait longer before retry
                continue
            except:
                break

    return businesses

# Function to scrape email, category, and website from the business detail page
def scrape_business_details(detail_url):
    try:
        response = requests.get(detail_url, headers=HEADERS, timeout=30)  # Add timeout
        if response.status_code != 200:
            print(f"⚠ Received status code {response.status_code} for {detail_url}")
            return None, None, None
            
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract category
        category_tag = soup.find("span", class_="gz-cat")
        category = category_tag.text.strip() if category_tag else None

        # Extract website link
        website_tag = soup.find("a", class_="card-link")
        website = website_tag["href"].strip() if website_tag and "href" in website_tag.attrs else None

        # Extract email (if directly visible)
        email_tag = soup.find("a", href=re.compile(r"mailto:"))
        if email_tag:
            return email_tag["href"].replace("mailto:", "").strip(), category, website

        # If no email found, return the "Send Email" form link
        send_email_button = soup.find("a", text=re.compile(r"Send Email", re.IGNORECASE))
        if send_email_button and "href" in send_email_button.attrs:
            return BASE_URL + send_email_button["href"], category, website

    except Exception as e:
        print(f"⚠ Error fetching details from {detail_url}: {e}")

    return None, category, website

# MAIN EXECUTION
if __name__ == "__main__":
    # Set the maximum number of pages to scrape
    MAX_PAGES = 2 # Adjust this value as needed
    
    print(f"Starting scraper with a maximum of {MAX_PAGES} pages...")
    all_businesses = scrape_businesses(max_pages=MAX_PAGES)

    # Save data to CSV
    df = pd.DataFrame(all_businesses)
    df.to_csv("ycea_business_directory.csv", index=False)
    print(f"✅ Data saved to 'ycea_business_directory.csv' with {len(df)} entries.")