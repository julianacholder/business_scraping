import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import urllib.parse

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

# Function to extract data from the detail page
def get_business_details(detail_url):
    try:
        response = requests.get(detail_url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch detail page: {detail_url}")
            return None, None, None
        
        detail_soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract category
        category_section = detail_soup.find("div", class_="gz-details-categories")
        category = None
        if category_section:
            cat_span = category_section.find("span", class_="gz-cat")
            if cat_span:
                category = cat_span.text.strip().replace('"', '').replace("::after", "")
        
        # Try to find website if not found on main page
        website = None
        website_link = detail_soup.find("li", class_="gz-card-website")
        if website_link and website_link.find("a"):
            website = website_link.find("a").get("href", "").strip()
        
        # Try to find email through contact form link
        email = None
        email_link = detail_soup.find("a", class_="card-link", id="gz-directory-contact")
        if email_link:
            # Unfortunately, we can't directly get the email from the contact form
            # This would require form submission or JavaScript execution
            # For this example, we'll store the contact form URL instead
            email = "Contact form available"
            
        return category, website, email
    except Exception as e:
        print(f"Error fetching details: {e}")
        return None, None, None

# Function to scrape company data from a page
def scrape_companies(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch page: {url}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    company_cards = soup.find_all("div", class_="gz-card-top")  # Find all company card top sections
    company_data = []
    
    for card in company_cards:
        try:
            # Extract name and detail page URL
            name_tag = card.find("h5", class_="card-title")
            name = None
            detail_url = None
            
            if name_tag and name_tag.find("a"):
                name_link = name_tag.find("a")
                name = name_link.text.strip()
                detail_url = name_link.get("href")
                if detail_url and not detail_url.startswith("http"):
                    detail_url = urllib.parse.urljoin("https://business.ycea-pa.org", detail_url)
            
            # Find the corresponding body section
            body_div = card.find_next_sibling("div", class_="card-body")
            
            address = None
            phone = None
            website = None
            
            if body_div:
                # Extract address
                address_li = body_div.find("li", class_="gz-card-address")
                if address_li:
                    address = address_li.text.strip()
                
                # Extract phone number
                phone_li = body_div.find("li", class_="gz-card-phone")
                if phone_li:
                    phone = phone_li.text.strip()
                
                # Extract website
                website_li = body_div.find("li", class_="gz-card-website")
                if website_li and website_li.find("a"):
                    website = website_li.find("a").get("href", "").strip()
            
            # Get additional details from the detail page
            category = None
            detail_website = None
            email = None
            
            if detail_url:
                print(f"Fetching details for: {name} from {detail_url}")
                category, detail_website, email = get_business_details(detail_url)
                # Use detail page website if main page website is missing
                if not website and detail_website:
                    website = detail_website
                
                # Add a small delay between detail page requests
                time.sleep(1)
            
            company_data.append({
                "Name": name,
                "Address": address,
                "Phone": phone,
                "Website": website,
                "Category": category,
                "Email": email,
                "Detail_URL": detail_url
            })
            
        except Exception as e:
            print(f"Error scraping a company: {e}")
    
    return company_data

# Main function to control the scraping process
def main():
    # Get total number of pages before scraping
    total_pages = get_total_pages(BASE_URL)
    print(f"Total Pages Found: {total_pages}")
    
    # For testing, you might want to limit to fewer pages initially
    pages_to_scrape = min(total_pages, 3)  # Change to total_pages for full scrape
    
    # Scrape multiple pages with proper stopping condition
    all_companies = []
    for page_num in range(1, pages_to_scrape + 1):
        page_url = f"{BASE_URL}?page={page_num}"
        print(f"Scraping page {page_num} of {pages_to_scrape}...")
        page_data = scrape_companies(page_url)
        
        if not page_data:
            print("No more companies found. Stopping scraping.")
            break  # Stops early if no data is found on a page
            
        all_companies.extend(page_data)
        print(f"Collected {len(page_data)} companies from page {page_num}")
        
        # Add delay between pages to be respectful
        time.sleep(3)
    
    # Save results to CSV file
    df = pd.DataFrame(all_companies)
    df.to_csv("ycea_business_directory.csv", index=False)
    print(f"✅ Data saved to 'ycea_business_directory.csv' with {len(df)} entries.")

# Run the scraper
if __name__ == "__main__":
    main()