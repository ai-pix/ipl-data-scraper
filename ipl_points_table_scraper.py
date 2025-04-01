import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import datetime
import time
import pytz
import random
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("points_table_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# URL for the IPL points table
POINTS_TABLE_URL = "https://www.iplt20.com/points-table/men"
ALTERNATE_URL = "https://www.cricbuzz.com/cricket-series/5945/indian-premier-league-2025/points-table"

# Directory to save the points table
OUTPUT_DIR = "points_table"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# List of user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/122.0"
]

def setup_webdriver(headless=True):
    """Sets up and returns a configured Chrome WebDriver"""
    chrome_options = Options()
    
    # Choose a random user agent
    user_agent = random.choice(USER_AGENTS)
    
    if headless:
        chrome_options.add_argument("--headless=new")  # New headless mode
    
    # Basic settings for stability
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Additional settings to avoid detection
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Create the WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute CDP commands to prevent detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def scrape_points_table():
    """Scrapes the IPL points table with fallback mechanisms"""
    logger.info("Attempting to scrape IPL points table...")
    
    # Try official site with headless browser
    logger.info("Attempt 1: Using official IPL site with headless browser")
    result = scrape_official_site(headless=True)
    if result is not None:
        return result
    
    # Try official site without headless mode
    logger.info("Attempt 2: Using official IPL site without headless mode")
    result = scrape_official_site(headless=False)
    if result is not None:
        return result
    
    # Try alternative site (Cricbuzz)
    logger.info("Attempt 3: Using alternative site (Cricbuzz)")
    result = scrape_cricbuzz_site()
    if result is not None:
        return result
    
    # Final fallback: Try with requests and BeautifulSoup directly
    logger.info("Attempt 4: Using direct HTTP request")
    result = scrape_with_requests()
    
    return result

def scrape_official_site(headless=True):
    """Scrapes the IPL points table from the official website"""
    driver = None
    try:
        logger.info(f"Initializing Chrome {'headless' if headless else 'with browser window'}")
        driver = setup_webdriver(headless=headless)
        
        # Load the page
        driver.get(POINTS_TABLE_URL)
        
        # Wait a moment and log page title to verify correct loading
        time.sleep(3)
        logger.info(f"Page title: {driver.title}")
        
        # Try to save the page source for debugging if needed
        debug_dir = "debug_files"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        with open(os.path.join(debug_dir, f"ipl_points_table_page_{datetime.datetime.now().strftime('%Y%m%d')}.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        try:
            # Wait for table to load (try multiple selectors)
            selectors = [
                "table.ih-td-tab tbody tr", 
                "table.points-table tbody tr",
                "table.standings-table tbody tr",
                ".points-table-container table"
            ]
            
            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Selector {selector} found!")
                    break
                except TimeoutException:
                    continue
        except TimeoutException:
            logger.warning("Timed out waiting for table to load")
        
        # Parse the page with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Try multiple table selectors
        table_selectors = ["table.ih-td-tab", "table.points-table", ".points-table-container table", "table"]
        table = None
        
        for selector in table_selectors:
            table = soup.select_one(selector)
            if table:
                logger.info(f"Found table with selector: {selector}")
                break
                
        if not table:
            logger.warning("Table not found on the page with any selector")
            return None
            
        # Extract headers
        header_row = table.select_one("thead tr")
        if not header_row:
            header_row = table.select_one("tr")  # Fallback if no thead
            
        headers = [header.text.strip() for header in header_row.find_all(["th", "td"])]
        logger.info(f"Found headers: {headers}")

        # Extract rows
        rows = []
        for row in table.select("tbody tr"):
            cols = row.find_all("td")
            if len(cols) >= len(headers):
                row_data = [col.text.strip() for col in cols[:len(headers)]]
                rows.append(row_data)
        
        # If no rows found but table structure exists, this might be pre-season
        if not rows and table:
            logger.warning("No data rows found - IPL season might not have started yet")
            
            # Create a placeholder table with team names if we can find them
            teams = ["Chennai Super Kings", "Mumbai Indians", "Kolkata Knight Riders", 
                    "Royal Challengers Bengaluru", "Delhi Capitals", "Sunrisers Hyderabad",
                    "Rajasthan Royals", "Punjab Kings", "Gujarat Titans", "Lucknow Super Giants"]
            
            if len(headers) > 0:
                # Fill with zeroes for all other stats
                placeholder_rows = []
                for i, team in enumerate(teams, 1):
                    placeholder_rows.append([i, team] + ["0"] * (len(headers) - 2))
                df = pd.DataFrame(placeholder_rows, columns=headers)
                logger.info("Created placeholder table for pre-season")
                return df
            
            return None
            
        # Create dataframe
        df = pd.DataFrame(rows, columns=headers)
        logger.info(f"Successfully scraped IPL points table with {len(rows)} team entries")
        return df
        
    except Exception as e:
        logger.error(f"Error scraping official site: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    finally:
        if driver:
            driver.quit()

def scrape_cricbuzz_site():
    """Scrapes the IPL points table from Cricbuzz as fallback"""
    driver = None
    try:
        logger.info("Trying alternative site (Cricbuzz)")
        driver = setup_webdriver(headless=True)
        
        # Load the page
        driver.get(ALTERNATE_URL)
        time.sleep(3)
        
        # Try to save the page source for debugging
        debug_dir = "debug_files"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        with open(os.path.join(debug_dir, f"cricbuzz_points_table_{datetime.datetime.now().strftime('%Y%m%d')}.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Look for table
        table = soup.select_one("table.table")
        if not table:
            logger.warning("Table not found on Cricbuzz")
            return None
            
        # Extract headers and rows
        headers = [th.text.strip() for th in table.select("thead th")]
        
        rows = []
        for tr in table.select("tbody tr"):
            row_data = [td.text.strip() for td in tr.select("td")]
            if len(row_data) == len(headers):
                rows.append(row_data)
        
        if not rows:
            logger.warning("No rows found in Cricbuzz table")
            return None
            
        df = pd.DataFrame(rows, columns=headers)
        logger.info(f"Successfully scraped points table from Cricbuzz with {len(rows)} team entries")
        return df
        
    except Exception as e:
        logger.error(f"Error scraping Cricbuzz: {str(e)}")
        return None
    finally:
        if driver:
            driver.quit()

def scrape_with_requests():
    """Attempt to scrape using direct HTTP requests as a last resort"""
    try:
        logger.info("Attempting direct HTTP request")
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        # Try both URLs
        for url in [POINTS_TABLE_URL, ALTERNATE_URL]:
            logger.info(f"Trying URL: {url}")
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                logger.info(f"Successfully retrieved page from {url}")
                
                # Save for debugging
                debug_dir = "debug_files"
                if not os.path.exists(debug_dir):
                    os.makedirs(debug_dir)
                with open(os.path.join(debug_dir, f"direct_request_{datetime.datetime.now().strftime('%Y%m%d')}.html"), "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find any table that might contain the points
                tables = soup.find_all('table')
                logger.info(f"Found {len(tables)} tables on the page")
                
                for i, table in enumerate(tables):
                    try:
                        headers = [th.text.strip() for th in table.select("thead th") or table.select("tr:first-child th") or table.select("tr:first-child td")]
                        if not headers:
                            continue
                            
                        rows = []
                        for tr in table.select("tbody tr") or table.select("tr")[1:]:
                            row_data = [td.text.strip() for td in tr.select("td")]
                            if len(row_data) >= len(headers):
                                rows.append(row_data[:len(headers)])
                        
                        if rows:
                            logger.info(f"Found potential points table (Table #{i+1}) with {len(rows)} rows")
                            df = pd.DataFrame(rows, columns=headers)
                            
                            # Check if this looks like a points table
                            points_related_columns = ['pts', 'point', 'points', 'pld', 'played', 'won', 'lost', 'team', 'teams', 'position', 'nrr']
                            column_match = any(any(point_col in col.lower() for point_col in points_related_columns) for col in df.columns)
                            
                            if column_match:
                                logger.info(f"Table #{i+1} appears to be a points table based on column names")
                                return df
                    except Exception as table_error:
                        logger.warning(f"Error processing table #{i+1}: {table_error}")
                        continue
        
        logger.warning("No suitable table found in direct request")
        return None
        
    except Exception as e:
        logger.error(f"Error with direct request: {str(e)}")
        return None

def save_points_table(dataframe):
    """Save points table to CSV and other formats"""
    if dataframe is None or dataframe.empty:
        logger.error("No data to save!")
        return False
        
    try:
        # Get current date in Indian Standard Time
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.datetime.now(ist)
        date_str = today.strftime("%Y%m%d")
        
        # Save as CSV
        csv_file = os.path.join(OUTPUT_DIR, f"ipl_points_table_{date_str}.csv")
        dataframe.to_csv(csv_file, index=False)
        logger.info(f"Points table saved to CSV: {csv_file}")
        
        # Save as HTML for better visualization
        html_file = os.path.join(OUTPUT_DIR, f"ipl_points_table_{date_str}.html")
        html_content = dataframe.to_html(index=False, classes='table table-striped')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(f"""
                <html>
                <head>
                    <title>IPL Points Table - {today.strftime('%Y-%m-%d')}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .table {{ border-collapse: collapse; width: 100%; }}
                        .table-striped tbody tr:nth-of-type(odd) {{ background-color: rgba(0,0,0,.05); }}
                        .table th, .table td {{ padding: 8px; border: 1px solid #ddd; }}
                        .table th {{ background-color: #4b4b4b; color: white; }}
                        h1, h2 {{ color: #403f3f; }}
                    </style>
                </head>
                <body>
                    <h1>IPL 2025 Points Table</h1>
                    <h2>Updated: {today.strftime('%Y-%m-%d %H:%M:%S')} IST</h2>
                    {html_content}
                    <p>Generated by IPL Points Table Scraper</p>
                </body>
                </html>
            """)
        logger.info(f"Points table saved to HTML: {html_file}")
        
        # Create latest version symlink/copy for easy reference
        latest_csv = os.path.join(OUTPUT_DIR, "ipl_points_table_latest.csv")
        latest_html = os.path.join(OUTPUT_DIR, "ipl_points_table_latest.html")
        
        # Copy instead of symlink for Windows compatibility
        import shutil
        shutil.copy2(csv_file, latest_csv)
        shutil.copy2(html_file, latest_html)
        logger.info("Created latest version copies")
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving points table: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def display_points_table(dataframe):
    """Display points table in console"""
    if dataframe is None or dataframe.empty:
        print("\nNo points table data available!")
        return
        
    # Display in console with formatting
    print("\n" + "="*80)
    print("IPL 2025 POINTS TABLE".center(80))
    print("="*80)
    
    # Format for display (limited width)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)
    print(dataframe)
    print("="*80)
    
    # Calculate and show days since IPL started and days until final
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.datetime.now(ist)
    ipl_start = datetime.datetime(2025, 3, 22, tzinfo=ist)  # IPL 2025 start date
    ipl_final = datetime.datetime(2025, 5, 25, tzinfo=ist)  # IPL 2025 final date
    
    days_since_start = (today - ipl_start).days
    days_until_final = (ipl_final - today).days
    
    if days_since_start < 0:
        print(f"IPL 2025 has not started yet. {abs(days_since_start)} days until IPL begins!\n")
    elif days_until_final < 0:
        print(f"IPL 2025 is complete! The final was held on {ipl_final.strftime('%B %d, %Y')}\n")
    else:
        print(f"IPL 2025 Day {days_since_start+1} | {days_until_final} days remaining until the final\n")

def main():
    """Main function"""
    print("\nIPL POINTS TABLE SCRAPER")
    print("-----------------------")
    
    # Get and save points table
    points_table = scrape_points_table()
    
    if points_table is not None and not points_table.empty:
        # Save to file
        save_points_table(points_table)
        
        # Display in console
        display_points_table(points_table)
        
        print("Done!")
    else:
        print("\nFailed to retrieve the points table")
        print("\nDone!")

if __name__ == "__main__":
    main()