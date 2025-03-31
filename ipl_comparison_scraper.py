from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import json
import datetime
import requests
from colorama import init, Fore, Style

# Initialize colorama
init()

# Define URLs
TEAM_COMPARISON_URL = "https://www.iplt20.com/comparison/teams"
PLAYER_COMPARISON_URL = "https://www.iplt20.com/comparison/players"

# Define team codes to team names mapping
TEAM_CODES = {
    "CSK": "Chennai Super Kings",
    "DC": "Delhi Capitals",
    "GT": "Gujarat Titans",
    "KKR": "Kolkata Knight Riders",
    "LSG": "Lucknow Super Giants",
    "MI": "Mumbai Indians",
    "PBKS": "Punjab Kings",
    "RR": "Rajasthan Royals",
    "RCB": "Royal Challengers Bengaluru",
    "SRH": "Sunrisers Hyderabad"
}

# Define output directories
COMPARISON_DATA_FOLDER = 'comparison_data'
TEAM_COMPARISON_FOLDER = os.path.join(COMPARISON_DATA_FOLDER, 'team_comparison')
PLAYER_COMPARISON_FOLDER = os.path.join(COMPARISON_DATA_FOLDER, 'player_comparison')

# Debug files folder
DEBUG_FILES_FOLDER = 'debug_files'

# Create folders if they don't exist
for folder in [COMPARISON_DATA_FOLDER, TEAM_COMPARISON_FOLDER, PLAYER_COMPARISON_FOLDER, DEBUG_FILES_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"{Fore.GREEN}Created folder: {folder}{Style.RESET_ALL}")

def setup_driver():
    """
    Set up and return a Selenium WebDriver instance with improved error handling
    """
    print(f"{Fore.CYAN}Setting up Chrome WebDriver...{Style.RESET_ALL}")
    
    chrome_options = Options()
    # Remove headless mode to make browser visible
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--log-level=3')  # Reduce logging
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    try:
        # First try with ChromeDriverManager
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"{Fore.GREEN}Chrome WebDriver setup successful with ChromeDriverManager{Style.RESET_ALL}")
            return driver
        except Exception as e:
            print(f"{Fore.YELLOW}ChromeDriverManager setup failed: {str(e)}. Trying alternative methods...{Style.RESET_ALL}")
        
        # Try with default Chrome path
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print(f"{Fore.GREEN}Chrome WebDriver setup successful with default path{Style.RESET_ALL}")
            return driver
        except Exception as e:
            print(f"{Fore.YELLOW}Default Chrome WebDriver setup failed: {str(e)}. Trying with Edge...{Style.RESET_ALL}")
        
        # Try with Edge WebDriver as fallback
        try:
            from selenium.webdriver.edge.service import Service as EdgeService
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            
            edge_options = webdriver.EdgeOptions()
            for arg in chrome_options.arguments:
                if '--headless' not in arg:  # Keep visible mode for Edge too
                    edge_options.add_argument(arg)
            
            edge_service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=edge_service, options=edge_options)
            print(f"{Fore.GREEN}Edge WebDriver setup successful as fallback{Style.RESET_ALL}")
            return driver
        except Exception as e:
            print(f"{Fore.YELLOW}Edge WebDriver setup failed: {str(e)}{Style.RESET_ALL}")
        
        print(f"{Fore.RED}All WebDriver setup methods failed{Style.RESET_ALL}")
        return None
            
    except Exception as e:
        print(f"{Fore.RED}Error setting up WebDriver: {str(e)}{Style.RESET_ALL}")
        return None

def scroll_to_element(driver, element):
    """
    Scroll to make an element visible
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)  # Small pause after scrolling
    except Exception as e:
        print(f"{Fore.YELLOW}Error scrolling to element: {str(e)}{Style.RESET_ALL}")

def scroll_down_page(driver, scroll_amount=300):
    """
    Scroll down the page by a specific amount of pixels
    """
    try:
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(0.5)  # Small pause after scrolling
    except Exception as e:
        print(f"{Fore.YELLOW}Error scrolling down page: {str(e)}{Style.RESET_ALL}")

def scroll_to_bottom(driver):
    """
    Scroll to the bottom of the page
    """
    try:
        # First scroll quickly to the bottom to trigger any lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # Then scroll back up a bit to ensure everything is visible
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.9);")
        time.sleep(0.5)
        
        # Then scroll through the page in steps to ensure all dynamic content loads
        current_height = 0
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        while current_height < new_height:
            current_height = new_height
            driver.execute_script(f"window.scrollTo(0, {current_height * 0.7});")
            time.sleep(0.5)
            driver.execute_script(f"window.scrollTo(0, {current_height});")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
        print(f"{Fore.GREEN}Scrolled to bottom of page{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}Error scrolling to bottom: {str(e)}{Style.RESET_ALL}")

def save_page_source(driver, filename_prefix):
    """
    Save the current page source to a file for debugging
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(DEBUG_FILES_FOLDER, f"{filename_prefix}_{timestamp}.html")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    
    print(f"{Fore.GREEN}Saved page source to {filename}{Style.RESET_ALL}")
    return filename

def select_teams_for_comparison(driver, team1_code, team2_code):
    """
    Select two teams for comparison
    """
    try:
        print(f"{Fore.CYAN}Selecting teams for comparison: {team1_code} vs {team2_code}{Style.RESET_ALL}")
        
        # Navigate to teams comparison page
        driver.get(TEAM_COMPARISON_URL)
        time.sleep(3)  # Wait for page to load
        
        # Save initial page for debugging
        save_page_source(driver, "teams_comparison_page_initial")
        
        # Step 1: Click on the first "Click to Add Team" button
        try:
            first_add_team = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".ih-tcomp-tsel-left"))
            )
            first_add_team.click()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}Error clicking first team selector: {str(e)}{Style.RESET_ALL}")
            
            # Try alternative selector
            try:
                first_add_team = driver.find_element(By.XPATH, "//div[contains(@class, 'ih-tcomp-tsel-left')]")
                first_add_team.click()
                time.sleep(1)
            except Exception as e2:
                print(f"{Fore.RED}Error with alternative first team selector: {str(e2)}{Style.RESET_ALL}")
                return False
        
        # Step 2: Find and select the first team
        teams_list = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ih-td-filter-list li"))
        )
        
        first_team_found = False
        for team in teams_list:
            if TEAM_CODES.get(team1_code, "") in team.text:
                scroll_to_element(driver, team)
                team.click()
                first_team_found = True
                print(f"{Fore.GREEN}Selected first team: {team.text}{Style.RESET_ALL}")
                time.sleep(1)
                break
        
        if not first_team_found:
            print(f"{Fore.RED}Could not find first team: {team1_code}{Style.RESET_ALL}")
            return False
        
        # Step 3: Click on the second "Click to Add Team" button
        try:
            second_add_team = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".ih-tcomp-tsel-right"))
            )
            second_add_team.click()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}Error clicking second team selector: {str(e)}{Style.RESET_ALL}")
            
            # Try alternative selector
            try:
                second_add_team = driver.find_element(By.XPATH, "//div[contains(@class, 'ih-tcomp-tsel-right')]")
                second_add_team.click()
                time.sleep(1)
            except Exception as e2:
                print(f"{Fore.RED}Error with alternative second team selector: {str(e2)}{Style.RESET_ALL}")
                return False
        
        # Step 4: Find and select the second team
        teams_list = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ih-td-filter-list li"))
        )
        
        second_team_found = False
        for team in teams_list:
            if TEAM_CODES.get(team2_code, "") in team.text:
                scroll_to_element(driver, team)
                team.click()
                second_team_found = True
                print(f"{Fore.GREEN}Selected second team: {team.text}{Style.RESET_ALL}")
                time.sleep(2)  # Wait longer for comparison to load
                break
        
        if not second_team_found:
            print(f"{Fore.RED}Could not find second team: {team2_code}{Style.RESET_ALL}")
            return False
        
        # Step 5: Wait for comparison data to load and scroll through it
        print(f"{Fore.CYAN}Waiting for comparison data to load...{Style.RESET_ALL}")
        time.sleep(3)
        
        # Scroll through the page to ensure all data is loaded
        scroll_down_page(driver, 300)  # Initial scroll to see first part of comparison data
        time.sleep(1)
        
        scroll_to_bottom(driver)  # Then scroll to the bottom to load everything
        
        # Save the comparison page after scrolling
        save_page_source(driver, f"team_comparison_{team1_code}_vs_{team2_code}_after_scroll")
        
        return True
    
    except Exception as e:
        print(f"{Fore.RED}Error selecting teams for comparison: {str(e)}{Style.RESET_ALL}")
        save_page_source(driver, f"error_team_comparison_{team1_code}_vs_{team2_code}")
        return False

def select_players_for_comparison(driver, player1_name, player2_name):
    """
    Select two players for comparison
    """
    try:
        print(f"{Fore.CYAN}Selecting players for comparison: {player1_name} vs {player2_name}{Style.RESET_ALL}")
        
        # Navigate to players comparison page
        driver.get(PLAYER_COMPARISON_URL)
        time.sleep(3)  # Wait for page to load
        
        # Save initial page for debugging
        save_page_source(driver, "players_comparison_page_initial")
        
        # Step 1: Click on the first "Click to Add Player" button
        try:
            first_add_player = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".ih-tcomp-tsel-left"))
            )
            first_add_player.click()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}Error clicking first player selector: {str(e)}{Style.RESET_ALL}")
            
            # Try alternative selector
            try:
                first_add_player = driver.find_element(By.XPATH, "//div[contains(@class, 'ih-tcomp-tsel-left')]")
                first_add_player.click()
                time.sleep(1)
            except Exception as e2:
                print(f"{Fore.RED}Error with alternative first player selector: {str(e2)}{Style.RESET_ALL}")
                return False
        
        # Step 2: Search for the first player
        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.ih-pl-srch"))
            )
            search_input.clear()
            search_input.send_keys(player1_name)
            time.sleep(2)  # Wait for search results
            
            # Click on the matching player
            player_elements = driver.find_elements(By.CSS_SELECTOR, ".ih-td-filter-list li")
            
            first_player_found = False
            for player in player_elements:
                if player1_name.lower() in player.text.lower():
                    scroll_to_element(driver, player)
                    player.click()
                    first_player_found = True
                    print(f"{Fore.GREEN}Selected first player: {player.text}{Style.RESET_ALL}")
                    time.sleep(1)
                    break
            
            if not first_player_found:
                print(f"{Fore.RED}Could not find first player: {player1_name} in search results{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}Error searching for first player: {str(e)}{Style.RESET_ALL}")
            return False
        
        # Step 3: Click on the second "Click to Add Player" button
        try:
            second_add_player = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".ih-tcomp-tsel-right"))
            )
            second_add_player.click()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}Error clicking second player selector: {str(e)}{Style.RESET_ALL}")
            
            # Try alternative selector
            try:
                second_add_player = driver.find_element(By.XPATH, "//div[contains(@class, 'ih-tcomp-tsel-right')]")
                second_add_player.click()
                time.sleep(1)
            except Exception as e2:
                print(f"{Fore.RED}Error with alternative second player selector: {str(e2)}{Style.RESET_ALL}")
                return False
        
        # Step 4: Search for the second player
        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.ih-pl-srch"))
            )
            search_input.clear()
            search_input.send_keys(player2_name)
            time.sleep(2)  # Wait for search results
            
            # Click on the matching player
            player_elements = driver.find_elements(By.CSS_SELECTOR, ".ih-td-filter-list li")
            
            second_player_found = False
            for player in player_elements:
                if player2_name.lower() in player.text.lower():
                    scroll_to_element(driver, player)
                    player.click()
                    second_player_found = True
                    print(f"{Fore.GREEN}Selected second player: {player.text}{Style.RESET_ALL}")
                    time.sleep(2)  # Wait longer for comparison to load
                    break
            
            if not second_player_found:
                print(f"{Fore.RED}Could not find second player: {player2_name} in search results{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}Error searching for second player: {str(e)}{Style.RESET_ALL}")
            return False
        
        # Step 5: Wait for comparison data to load and scroll through it
        print(f"{Fore.CYAN}Waiting for comparison data to load...{Style.RESET_ALL}")
        time.sleep(3)
        
        # Scroll through the page to ensure all data is loaded
        scroll_down_page(driver, 300)  # Initial scroll to see first part of comparison data
        time.sleep(1)
        
        scroll_to_bottom(driver)  # Then scroll to the bottom to load everything
        
        # Save the comparison page after scrolling
        save_page_source(driver, f"player_comparison_{player1_name.replace(' ', '_')}_vs_{player2_name.replace(' ', '_')}_after_scroll")
        
        return True
    
    except Exception as e:
        print(f"{Fore.RED}Error selecting players for comparison: {str(e)}{Style.RESET_ALL}")
        save_page_source(driver, f"error_player_comparison_{player1_name.replace(' ', '_')}_vs_{player2_name.replace(' ', '_')}")
        return False

def extract_comparison_data(driver, entity_type="team"):
    """
    Extract comparison data from the current page
    """
    # Wait a moment to ensure page is fully loaded after scrolling
    time.sleep(2)
    
    # 1. Try to identify the comparison table and headers
    try:
        comparison_table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ih-comparison-table"))
        )
        
        # Get table headers
        headers = []
        header_elements = comparison_table.find_elements(By.CSS_SELECTOR, "th")
        for header in header_elements:
            headers.append(header.text.strip())
        
        if len(headers) < 3:
            print(f"{Fore.YELLOW}Headers not found or incomplete, using default headers{Style.RESET_ALL}")
            headers = ["Metric", "Entity 1", "Entity 2"]
        
        # 2. Extract all rows
        comparison_data = []
        rows = comparison_table.find_elements(By.CSS_SELECTOR, "tbody tr")
        
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            if len(cells) >= 3:
                row_data = {
                    headers[0]: cells[0].text.strip(),
                    headers[1]: cells[1].text.strip(),
                    headers[2]: cells[2].text.strip()
                }
                comparison_data.append(row_data)
        
        print(f"{Fore.GREEN}Extracted {len(comparison_data)} comparison metrics{Style.RESET_ALL}")
        return comparison_data
        
    except Exception as e:
        print(f"{Fore.RED}Error extracting comparison data from page: {str(e)}{Style.RESET_ALL}")
        
        # Try alternative approach with BeautifulSoup
        try:
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the comparison table
            table = soup.select_one('.ih-comparison-table')
            if not table:
                print(f"{Fore.RED}No comparison table found in HTML{Style.RESET_ALL}")
                return []
            
            # Get headers
            headers = []
            for th in table.select('th'):
                headers.append(th.text.strip())
            
            if len(headers) < 3:
                print(f"{Fore.YELLOW}Not enough headers found in table, using default headers{Style.RESET_ALL}")
                headers = ["Metric", "Entity 1", "Entity 2"]
            
            # Extract rows
            comparison_data = []
            for tr in table.select('tbody tr'):
                cells = tr.select('td')
                if len(cells) >= 3:
                    row_data = {
                        headers[0]: cells[0].text.strip(),
                        headers[1]: cells[1].text.strip(),
                        headers[2]: cells[2].text.strip()
                    }
                    comparison_data.append(row_data)
            
            print(f"{Fore.GREEN}Extracted {len(comparison_data)} comparison metrics with BeautifulSoup{Style.RESET_ALL}")
            return comparison_data
            
        except Exception as bs_error:
            print(f"{Fore.RED}Error extracting with BeautifulSoup: {str(bs_error)}{Style.RESET_ALL}")
            return []

def scrape_team_comparison(driver, team1_code, team2_code):
    """
    Scrape comparison data for a specific team pair
    """
    try:
        print(f"{Fore.CYAN}Scraping comparison for {team1_code} vs {team2_code}{Style.RESET_ALL}")
        
        # Step 1: Select teams for comparison
        teams_selected = select_teams_for_comparison(driver, team1_code, team2_code)
        
        if not teams_selected:
            print(f"{Fore.RED}Failed to select teams for comparison{Style.RESET_ALL}")
            return None
        
        # Step 2: Extract comparison data
        comparison_data = extract_comparison_data(driver, "team")
        
        if not comparison_data:
            print(f"{Fore.RED}No comparison data found for {team1_code} vs {team2_code}{Style.RESET_ALL}")
            return None
        
        # Step 3: Prepare result
        team1_name = TEAM_CODES.get(team1_code, team1_code)
        team2_name = TEAM_CODES.get(team2_code, team2_code)
        
        result = {
            "team1": team1_name,
            "team2": team2_name,
            "team1_code": team1_code,
            "team2_code": team2_code,
            "timestamp": datetime.datetime.now().isoformat(),
            "comparison_data": comparison_data
        }
        
        # Step 4: Save as JSON and CSV
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        filename = f"team_comparison_{team1_code}_vs_{team2_code}_{timestamp}"
        
        json_filepath = os.path.join(TEAM_COMPARISON_FOLDER, f"{filename}.json")
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        print(f"{Fore.GREEN}Saved team comparison to {json_filepath}{Style.RESET_ALL}")
        
        # Save as CSV
        df = pd.DataFrame(comparison_data)
        csv_filepath = os.path.join(TEAM_COMPARISON_FOLDER, f"{filename}.csv")
        df.to_csv(csv_filepath, index=False)
        print(f"{Fore.GREEN}Saved team comparison CSV to {csv_filepath}{Style.RESET_ALL}")
        
        return result
        
    except Exception as e:
        print(f"{Fore.RED}Error in team comparison process: {str(e)}{Style.RESET_ALL}")
        return None

def scrape_player_comparison(driver, player1_name, player2_name):
    """
    Scrape comparison data for a specific player pair
    """
    try:
        print(f"{Fore.CYAN}Scraping comparison for {player1_name} vs {player2_name}{Style.RESET_ALL}")
        
        # Step 1: Select players for comparison
        players_selected = select_players_for_comparison(driver, player1_name, player2_name)
        
        if not players_selected:
            print(f"{Fore.RED}Failed to select players for comparison{Style.RESET_ALL}")
            return None
        
        # Step 2: Extract comparison data
        comparison_data = extract_comparison_data(driver, "player")
        
        if not comparison_data:
            print(f"{Fore.RED}No comparison data found for {player1_name} vs {player2_name}{Style.RESET_ALL}")
            return None
        
        # Step 3: Prepare result
        result = {
            "player1": player1_name,
            "player2": player2_name,
            "timestamp": datetime.datetime.now().isoformat(),
            "comparison_data": comparison_data
        }
        
        # Step 4: Save as JSON and CSV
        safe_player1 = player1_name.replace(' ', '_').replace('/', '_')
        safe_player2 = player2_name.replace(' ', '_').replace('/', '_')
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        
        filename = f"player_comparison_{safe_player1}_vs_{safe_player2}_{timestamp}"
        
        json_filepath = os.path.join(PLAYER_COMPARISON_FOLDER, f"{filename}.json")
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        print(f"{Fore.GREEN}Saved player comparison to {json_filepath}{Style.RESET_ALL}")
        
        # Save as CSV
        df = pd.DataFrame(comparison_data)
        csv_filepath = os.path.join(PLAYER_COMPARISON_FOLDER, f"{filename}.csv")
        df.to_csv(csv_filepath, index=False)
        print(f"{Fore.GREEN}Saved player comparison CSV to {csv_filepath}{Style.RESET_ALL}")
        
        return result
        
    except Exception as e:
        print(f"{Fore.RED}Error in player comparison process: {str(e)}{Style.RESET_ALL}")
        return None

def main():
    """
    Main function to run the IPL comparison scraper
    """
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}     IPL COMPARISON SCRAPER          {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    
    start_time = datetime.datetime.now()
    print(f"Scraping started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup driver
    driver = setup_driver()
    
    if driver is None:
        print(f"{Fore.RED}Failed to set up WebDriver. Exiting.{Style.RESET_ALL}")
        return
    
    try:
        # List of team pairs to compare
        team_comparison_pairs = [
            ("CSK", "MI"),   # Chennai Super Kings vs Mumbai Indians
            ("RCB", "KKR"),  # Royal Challengers Bengaluru vs Kolkata Knight Riders
            ("SRH", "RR")    # Sunrisers Hyderabad vs Rajasthan Royals
        ]
        
        # List of player pairs to compare
        player_comparison_pairs = [
            ("MS Dhoni", "Virat Kohli"),
            ("Rohit Sharma", "KL Rahul"),
            ("Jasprit Bumrah", "Kagiso Rabada")
        ]
        
        # Scrape team comparisons
        team_comparisons = []
        for team1_code, team2_code in team_comparison_pairs:
            result = scrape_team_comparison(driver, team1_code, team2_code)
            if result:
                team_comparisons.append(result)
                
            # Reset the driver state
            driver.delete_all_cookies()
            time.sleep(1)
        
        # Scrape player comparisons
        player_comparisons = []
        for player1_name, player2_name in player_comparison_pairs:
            result = scrape_player_comparison(driver, player1_name, player2_name)
            if result:
                player_comparisons.append(result)
                
            # Reset the driver state
            driver.delete_all_cookies()
            time.sleep(1)
        
        # Create overall summary
        summary = {
            "timestamp": datetime.datetime.now().isoformat(),
            "team_comparisons_count": len(team_comparisons),
            "player_comparisons_count": len(player_comparisons),
            "team_comparison_pairs": [f"{pair[0]} vs {pair[1]}" for pair in team_comparison_pairs],
            "player_comparison_pairs": [f"{pair[0]} vs {pair[1]}" for pair in player_comparison_pairs]
        }
        
        # Save summary
        summary_filepath = os.path.join(COMPARISON_DATA_FOLDER, f"comparison_scraping_summary_{datetime.datetime.now().strftime('%Y%m%d')}.json")
        with open(summary_filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4)
        
        print(f"{Fore.GREEN}Saved scraping summary to {summary_filepath}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error in main process: {str(e)}{Style.RESET_ALL}")
    
    finally:
        # Close the driver
        if driver:
            driver.quit()
            print(f"{Fore.CYAN}Closed WebDriver{Style.RESET_ALL}")
    
    end_time = datetime.datetime.now()
    print(f"\n{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"Scraping finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time taken: {end_time - start_time}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")

if __name__ == "__main__":
    main()