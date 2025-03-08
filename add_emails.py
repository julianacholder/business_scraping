import pandas as pd
import time
import re
import urllib.parse
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Set user agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

# Initialize Selenium WebDriver
def initialize_driver():
    chrome_options = Options()
    # Comment this out if you want to see the browser
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Disable images to speed up loading
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    # Disable JavaScript for faster loading (only if necessary)
    # chrome_options.add_argument("--disable-javascript")
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # Set a shorter page load timeout
    driver.set_page_load_timeout(20)  # Reduced from 30 to 20 seconds
    
    return driver

# Safe way to navigate to a URL with timeout handling
def safe_get(driver, url, timeout=20):
    """Navigate to URL with timeout handling."""
    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True
    except TimeoutException:
        print(f"Timeout when loading {url}")
        return False
    except WebDriverException as e:
        print(f"WebDriver error for {url}: {str(e)[:100]}")
        return False
    except Exception as e:
        print(f"Error loading {url}: {str(e)[:100]}")
        return False

# Function to extract email from a webpage
def extract_email_from_page(driver, url):
    """Extract email from the current page."""
    try:
        # Get all text from page
        page_source = driver.page_source
        
        # Look for email patterns in the page source
        email_pattern = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
        email_matches = email_pattern.findall(page_source)
        
        if email_matches:
            # Filter out common false positives
            filtered_emails = [email for email in email_matches 
                            if not any(domain in email.lower() for domain in [
                                'example.com', 'yourdomain.com', 'domain.com', 
                                'email@', 'user@', 'name@', 'someone@'
                            ])]
            if filtered_emails:
                return filtered_emails[0]
        
        return None
    except Exception as e:
        print(f"Error extracting email from page: {e}")
        return None

# Function to check common contact pages
def check_contact_pages(driver, base_url):
    """Check common contact page paths for emails."""
    # Common paths where contact information might be found
    contact_paths = [
        '/contact', '/contact-us', '/about/contact', '/about-us/contact',
        '/contactus', '/about', '/about-us', '/connect', '/get-in-touch',
        '/support', '/help', '/reach-us'
    ]
    
    try:
        # Get domain from base_url
        parsed_url = urlparse(base_url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Already checked the main page, start with contact pages
        for path in contact_paths:
            contact_url = f"{base_domain}{path}"
            try:
                print(f"Checking contact page: {contact_url}")
                if safe_get(driver, contact_url, timeout=15):
                    # Extract email from this contact page
                    email = extract_email_from_page(driver, contact_url)
                    if email:
                        return email
                else:
                    print(f"Skipping {contact_url} due to loading issues")
                    continue
            except Exception as e:
                print(f"Error on {contact_url}: {e}")
                continue
        
        return None
    except Exception as e:
        print(f"Error in check_contact_pages: {e}")
        return None

# Function to look for "mailto:" links
def find_mailto_links(driver):
    """Find mailto links in the page."""
    try:
        # Look for mailto links
        mailto_links = driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
        
        if mailto_links:
            for link in mailto_links:
                href = link.get_attribute('href')
                if href:
                    # Extract email from mailto link
                    email_match = re.search(r'mailto:([\w.+-]+@[\w-]+\.[\w.-]+)', href)
                    if email_match:
                        return email_match.group(1)
        
        return None
    except Exception as e:
        print(f"Error finding mailto links: {e}")
        return None

# Function to extract email from company website
def extract_company_email(driver, website_url):
    """Extract email from company website by checking multiple pages."""
    if not website_url or not isinstance(website_url, str):
        return "No website URL provided"
    
    # Clean up URL
    website_url = website_url.strip()
    if not website_url.startswith('http'):
        website_url = 'http://' + website_url
    
    try:
        # First, try the main page
        print(f"Checking main website: {website_url}")
        if not safe_get(driver, website_url, timeout=20):
            # Try with www. if the original URL doesn't have it
            if 'www.' not in website_url:
                parsed = urlparse(website_url)
                www_url = f"{parsed.scheme}://www.{parsed.netloc}{parsed.path}"
                print(f"Trying with www prefix: {www_url}")
                if not safe_get(driver, www_url, timeout=15):
                    return "Website timeout or error"
        
        # Look for mailto links first (these are most reliable)
        email = find_mailto_links(driver)
        if email:
            return email
        
        # Extract email from main page
        email = extract_email_from_page(driver, website_url)
        if email:
            return email
        
        # If no email found on main page, check common contact pages
        email = check_contact_pages(driver, website_url)
        if email:
            return email
        
        # If we still haven't found an email, try to find and click a "Contact" link
        try:
            # Find links that might lead to contact pages
            contact_links = driver.find_elements(
                By.XPATH, 
                "//a[contains(translate(text(), 'CONTACT', 'contact'), 'contact') or contains(@href, 'contact')]"
            )
            
            if contact_links:
                # Try the first few contact links
                for link in contact_links[:2]:  # Reduced from 3 to 2 to speed up
                    try:
                        contact_url = link.get_attribute('href')
                        if contact_url:
                            if safe_get(driver, contact_url, timeout=15):
                                # Look for mailto links first
                                email = find_mailto_links(driver)
                                if email:
                                    return email
                                    
                                # Extract email from contact page
                                email = extract_email_from_page(driver, contact_url)
                                if email:
                                    return email
                    except Exception as e:
                        print(f"Error following contact link: {e}")
                        continue
        except Exception as e:
            print(f"Error finding contact links: {e}")
        
        return "No email found on website"
        
    except TimeoutException:
        return "Website timeout"
    except Exception as e:
        return f"Error: {str(e)[:100]}"  # Truncate long error messages

# Function to restart the browser
def restart_browser(driver):
    """Restart the browser if it's having issues."""
    try:
        if driver:
            driver.quit()
    except:
        pass
    
    print("Restarting browser...")
    return initialize_driver()

# Main function to update the existing Email column in the CSV
def update_emails_from_websites(csv_path, output_path=None, start_from=0):
    driver = None
    try:
        # Initialize WebDriver
        driver = initialize_driver()
        print("Browser initialized successfully")
        
        # Load the existing CSV
        df = pd.read_csv(csv_path)
        print(f"Loaded CSV with {len(df)} entries")
        
        # Set output path
        if not output_path:
            output_path = csv_path.replace('.csv', '_updated_emails.csv')
        
        # Process each row that has a website URL
        # Get rows with websites
        to_process = df[df['Website'].notna()].copy()
        total_to_process = len(to_process)
        
        print(f"Need to process {total_to_process} entries with website URLs")
        print(f"Starting from index {start_from}")
        
        if total_to_process == 0:
            print("No entries to process. Make sure 'Website' column exists.")
            return
        
        browser_restart_count = 0
        consecutive_errors = 0
        
        # Skip to the starting point
        processed = 0
        for index, row in to_process.iloc[start_from:].iterrows():
            website = row['Website']
            if isinstance(website, str) and website.strip():
                print(f"\nProcessing {start_from + processed + 1} of {total_to_process}: {row['Name']}")
                print(f"Website URL: {website}")
                
                try:
                    # Extract email from company website
                    email = extract_company_email(driver, website)
                    
                    # Update the Email column directly
                    df.at[index, 'Email'] = email
                    
                    # Reset error counter on success
                    consecutive_errors = 0
                    
                except Exception as e:
                    print(f"Error processing {website}: {e}")
                    df.at[index, 'Email'] = f"Error processing: {str(e)[:50]}"
                    consecutive_errors += 1
                
                # Restart browser if too many consecutive errors
                if consecutive_errors >= 3:
                    print(f"Too many consecutive errors ({consecutive_errors}). Restarting browser...")
                    driver = restart_browser(driver)
                    consecutive_errors = 0
                    browser_restart_count += 1
                
                # Restart browser every 20 websites to prevent memory issues
                if (processed + 1) % 20 == 0:
                    print("Routine browser restart to prevent memory issues")
                    driver = restart_browser(driver)
                    browser_restart_count += 1
                
                # Save progress every 3 entries
                processed += 1
                if processed % 3 == 0 or processed + start_from == total_to_process:
                    current_progress = start_from + processed
                    print(f"Progress: {current_progress}/{total_to_process} ({current_progress/total_to_process*100:.1f}%)")
                    df.to_csv(output_path, index=False)
                    print(f"Progress saved to {output_path}")
                
                # Add a delay between websites
                time.sleep(2)  # Reduced from 3 to 2 seconds
        
        # Final save
        df.to_csv(output_path, index=False)
        print(f"✅ All done! Data saved to {output_path}")
        print(f"Browser was restarted {browser_restart_count} times")
        
    except Exception as e:
        print(f"Error in main function: {e}")
        # Save progress even if there's an error
        if 'df' in locals() and 'output_path' in locals():
            df.to_csv(output_path, index=False)
            print(f"Progress saved to {output_path} after error")
        
        # Print information for resuming
        if 'processed' in locals() and 'start_from' in locals():
            resume_from = start_from + processed
            print(f"To resume, run script with start_from={resume_from}")
    finally:
        # Always close the driver
        if driver:
            try:
                driver.quit()
                print("Browser closed")
            except:
                pass

# Run the script
if __name__ == "__main__":
    csv_file = "ycea_business_directory.csv"  # Update with your CSV file name
    
    # If you need to resume from a specific point, uncomment and edit the line below
    # update_emails_from_websites(csv_file, start_from=20)
    
    # Otherwise, start from the beginning
    update_emails_from_websites(csv_file)