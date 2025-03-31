import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# URL for the IPL points table
POINTS_TABLE_URL = "https://www.iplt20.com/points-table/men"

# Directory to save the points table
OUTPUT_DIR = "points_table"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def scrape_points_table():
    """Scrapes the IPL points table from the official website"""
    print("Initializing Chrome and loading page...")
    
    # Setup Chrome driver
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Uncomment to run in headless mode
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Load the page
        driver.get(POINTS_TABLE_URL)
        
        # Wait for table to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.ih-td-tab tbody tr"))
        )
        
        # Parse the page with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find the table
        table = soup.select_one("table.ih-td-tab")
        if not table:
            print("Table not found on the page")
            return None
            
        # Extract headers
        header_row = table.select_one("thead tr")
        if not header_row:
            header_row = table.select_one("tr")  # Fallback if no thead
            
        headers = [header.text.strip() for header in header_row.find_all(["th", "td"])]
        
        # Extract rows
        rows = []
        for row in table.select("tbody tr"):
            cols = row.find_all("td")
            if len(cols) >= len(headers):
                row_data = [col.text.strip() for col in cols[:len(headers)]]
                rows.append(row_data)
        
        # If no rows found but table structure exists, this might be pre-season
        if not rows and table:
            print("No data rows found - IPL season might not have started yet")
            return None
            
        # Create dataframe
        df = pd.DataFrame(rows, columns=headers)
        print(f"Successfully scraped IPL points table with {len(rows)} team entries")
        return df
        
    except Exception as e:
        print(f"Error scraping points table: {e}")
        return None
    finally:
        driver.quit()

def save_points_table(df):
    """Saves the points table to a CSV file"""
    if df is None or df.empty:
        print("No data to save")
        return
        
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(OUTPUT_DIR, f"ipl_points_table_{today}.csv")
    
    try:
        df.to_csv(filename, index=False)
        print(f"Saved points table to: {filename}")
    except Exception as e:
        print(f"Error saving data: {e}")

def main():
    """Main function"""
    print("IPL POINTS TABLE SCRAPER")
    print("-----------------------")
    
    # Scrape the data
    points_table = scrape_points_table()
    
    # Display the data
    if points_table is not None and not points_table.empty:
        print("\nCurrent IPL Points Table:")
        print(points_table)
        
        # Save the data
        save_points_table(points_table)
    else:
        print("Failed to retrieve the points table")
    
    print("\nDone!")

if __name__ == "__main__":
    main()