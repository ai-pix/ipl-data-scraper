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

# Import today's match function
from todays_match import fetch_today_matches

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

# Reverse mapping for team names to team codes
TEAM_NAMES_TO_CODES = {v: k for k, v in TEAM_CODES.items()}

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

def get_team_code(team_name):
    """
    Convert team name to team code
    """
    # Try direct mapping
    if team_name in TEAM_NAMES_TO_CODES:
        return TEAM_NAMES_TO_CODES[team_name]
    
    # Try searching in keys
    for code, name in TEAM_CODES.items():
        if team_name.lower() in name.lower():
            return code
    
    # Return the first 3 characters as a fallback
    return team_name[:3].upper()

def select_teams_for_comparison(driver, team1_name, team2_name):
    """
    Select two teams for comparison using proper page selectors from HTML analysis
    """
    team1_code = get_team_code(team1_name)
    team2_code = get_team_code(team2_name)
    
    try:
        print(f"{Fore.CYAN}Selecting teams for comparison: {team1_name} vs {team2_name}{Style.RESET_ALL}")
        
        # Navigate to teams comparison page
        driver.get(TEAM_COMPARISON_URL)
        time.sleep(5)  # Wait longer for page to load
        
        # Save initial page for debugging
        save_page_source(driver, "teams_comparison_page_initial")
        
        # Make sure the Teams tab is active (click it if needed)
        try:
            teams_tab = driver.find_elements(By.CSS_SELECTOR, ".nav-pills li.nav-item")[1]
            teams_tab.click()
            time.sleep(2)
        except Exception as e:
            print(f"{Fore.YELLOW}Teams tab may already be active: {str(e)}{Style.RESET_ALL}")
        
        # Step 1: Click on the first "Click to Add Team" button
        try:
            first_team_btn = driver.find_element(By.ID, "add-team-btn-left")
            first_team_btn.click()
            time.sleep(2)
            print(f"{Fore.GREEN}Clicked on first team button{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error clicking first team button: {str(e)}{Style.RESET_ALL}")
            return False
        
        # Step 2: Find and select the first team from the list using the onclick attribute
        team1_selected = False
        try:
            team_elements = driver.find_elements(By.CSS_SELECTOR, ".team-list-team-one")
            for team in team_elements:
                onclick_attr = team.get_attribute("onclick")
                if onclick_attr and f'"{team1_code}"' in onclick_attr:
                    scroll_to_element(driver, team)
                    team.click()
                    team1_selected = True
                    print(f"{Fore.GREEN}Selected first team: {team1_code}{Style.RESET_ALL}")
                    time.sleep(2)
                    break
            
            if not team1_selected:
                print(f"{Fore.RED}Could not find first team: {team1_code} in the list{Style.RESET_ALL}")
                return False
        except Exception as e:
            print(f"{Fore.RED}Error selecting first team: {str(e)}{Style.RESET_ALL}")
            return False
        
        # Step 3: Click on the second "Click to Add Team" button
        try:
            second_team_btn = driver.find_element(By.ID, "add-team-btn-right")
            second_team_btn.click()
            time.sleep(2)
            print(f"{Fore.GREEN}Clicked on second team button{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error clicking second team button: {str(e)}{Style.RESET_ALL}")
            return False
        
        # Step 4: Find and select the second team
        team2_selected = False
        try:
            team_elements = driver.find_elements(By.CSS_SELECTOR, ".team-list-team-two")
            for team in team_elements:
                onclick_attr = team.get_attribute("onclick")
                if onclick_attr and f'"{team2_code}"' in onclick_attr:
                    scroll_to_element(driver, team)
                    team.click()
                    team2_selected = True
                    print(f"{Fore.GREEN}Selected second team: {team2_code}{Style.RESET_ALL}")
                    time.sleep(3)  # Wait longer for comparison to load
                    break
            
            if not team2_selected:
                print(f"{Fore.RED}Could not find second team: {team2_code} in the list{Style.RESET_ALL}")
                return False
        except Exception as e:
            print(f"{Fore.RED}Error selecting second team: {str(e)}{Style.RESET_ALL}")
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

def extract_comparison_data(driver):
    """
    Extract comparison data from the current page using the correct structure
    for the comparison data found below the team rectangles
    """
    # Wait a moment to ensure page is fully loaded after scrolling
    time.sleep(2)
    
    try:
        # Look for the correct tab content that contains the comparison data
        comparison_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pills-overall"))
        )
        
        # Get all the comparison sections
        sections = comparison_div.find_elements(By.CLASS_NAME, "section2")
        
        if not sections:
            print(f"{Fore.YELLOW}No comparison sections found in the 'OVERALL' tab{Style.RESET_ALL}")
            return ["Metric", "Team 1", "Team 2"], []
        
        comparison_data = []
        
        # Extract the data from each section
        for section in sections:
            try:
                # Find the metric name (in the center p element)
                metric_name_element = section.find_element(By.CLASS_NAME, "section2_text")
                metric_name = metric_name_element.text.strip() if metric_name_element else "Unknown Metric"
                
                # Find the left value (first team)
                left_value_element = section.find_element(By.CLASS_NAME, "section2_progressBarPointleft")
                left_value = left_value_element.text.strip() if left_value_element else "N/A"
                
                # Find the right value (second team)
                right_value_element = section.find_element(By.CLASS_NAME, "section2_progressBarPointright")
                right_value = right_value_element.text.strip() if right_value_element else "N/A"
                
                # Skip empty metrics
                if metric_name and (metric_name != "Unknown Metric"):
                    row_data = {
                        "Metric": metric_name,
                        "Team 1": left_value,
                        "Team 2": right_value
                    }
                    comparison_data.append(row_data)
            except Exception as section_error:
                print(f"{Fore.YELLOW}Error extracting data from section: {str(section_error)}{Style.RESET_ALL}")
                continue
        
        print(f"{Fore.GREEN}Extracted {len(comparison_data)} comparison metrics from sections{Style.RESET_ALL}")
        return ["Metric", "Team 1", "Team 2"], comparison_data
        
    except Exception as e:
        print(f"{Fore.RED}Error extracting comparison data from page: {str(e)}{Style.RESET_ALL}")
        
        # Try alternative approach with BeautifulSoup
        try:
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the comparison tab content
            tab_content = soup.select_one('#pills-overall')
            if not tab_content:
                print(f"{Fore.RED}No OVERALL tab content found in HTML{Style.RESET_ALL}")
                return ["Metric", "Team 1", "Team 2"], []
            
            # Find all sections
            sections = tab_content.select('.section2')
            if not sections:
                print(f"{Fore.RED}No comparison sections found in HTML{Style.RESET_ALL}")
                return ["Metric", "Team 1", "Team 2"], []
            
            comparison_data = []
            
            # Extract data from each section
            for section in sections:
                try:
                    metric_name_element = section.select_one('.section2_text')
                    metric_name = metric_name_element.text.strip() if metric_name_element else "Unknown Metric"
                    
                    left_value_element = section.select_one('.section2_progressBarPointleft')
                    left_value = left_value_element.text.strip() if left_value_element else "N/A"
                    
                    right_value_element = section.select_one('.section2_progressBarPointright')
                    right_value = right_value_element.text.strip() if right_value_element else "N/A"
                    
                    # Skip empty metrics or sections without proper data
                    if metric_name and metric_name != "Unknown Metric" and left_value != "N/A" and right_value != "N/A":
                        row_data = {
                            "Metric": metric_name,
                            "Team 1": left_value,
                            "Team 2": right_value
                        }
                        comparison_data.append(row_data)
                except Exception as section_error:
                    print(f"{Fore.YELLOW}Error extracting data from section in BeautifulSoup: {str(section_error)}{Style.RESET_ALL}")
                    continue
            
            print(f"{Fore.GREEN}Extracted {len(comparison_data)} comparison metrics with BeautifulSoup{Style.RESET_ALL}")
            return ["Metric", "Team 1", "Team 2"], comparison_data
            
        except Exception as bs_error:
            print(f"{Fore.RED}Error extracting with BeautifulSoup: {str(bs_error)}{Style.RESET_ALL}")
            return ["Metric", "Team 1", "Team 2"], []

def scrape_team_comparison(driver, team1_name, team2_name):
    """
    Scrape comparison data for today's match teams
    """
    try:
        print(f"{Fore.CYAN}Scraping comparison for {team1_name} vs {team2_name}{Style.RESET_ALL}")
        
        # Step 1: Select teams for comparison
        teams_selected = select_teams_for_comparison(driver, team1_name, team2_name)
        
        if not teams_selected:
            print(f"{Fore.RED}Failed to select teams for comparison{Style.RESET_ALL}")
            return None
        
        # Step 2: Extract comparison data
        headers, comparison_data = extract_comparison_data(driver)
        
        if not comparison_data:
            print(f"{Fore.RED}No comparison data found for {team1_name} vs {team2_name}{Style.RESET_ALL}")
            return None
        
        # Step 3: Prepare result
        result = {
            "team1": team1_name,
            "team2": team2_name,
            "team1_code": get_team_code(team1_name),
            "team2_code": get_team_code(team2_name),
            "headers": headers,
            "timestamp": datetime.datetime.now().isoformat(),
            "comparison_data": comparison_data
        }
        
        # Step 4: Save as JSON and CSV
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        filename = f"team_comparison_{get_team_code(team1_name)}_vs_{get_team_code(team2_name)}_{timestamp}"
        
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

def get_key_player_names(team_name, limit=3):
    """
    Get key player names for a team - this would typically connect to a player database
    We'll use hardcoded values for demonstration
    """
    key_players = {
        "Mumbai Indians": ["Rohit Sharma", "Hardik Pandya", "Jasprit Bumrah"],
        "Kolkata Knight Riders": ["Shreyas Iyer", "Sunil Narine", "Andre Russell"],
        "Chennai Super Kings": ["MS Dhoni", "Ravindra Jadeja", "Ruturaj Gaikwad"],
        "Royal Challengers Bengaluru": ["Virat Kohli", "Faf du Plessis", "Glenn Maxwell"],
        "Delhi Capitals": ["Rishabh Pant", "Axar Patel", "David Warner"],
        "Rajasthan Royals": ["Sanju Samson", "Jos Buttler", "Yuzvendra Chahal"],
        "Punjab Kings": ["Shikhar Dhawan", "Sam Curran", "Kagiso Rabada"],
        "Sunrisers Hyderabad": ["Aiden Markram", "Heinrich Klaasen", "Bhuvneshwar Kumar"],
        "Gujarat Titans": ["Shubman Gill", "Rashid Khan", "Mohammed Shami"],
        "Lucknow Super Giants": ["KL Rahul", "Nicholas Pooran", "Ravi Bishnoi"]
    }
    
    # Try to find the team in our dictionary
    for team_key in key_players.keys():
        if team_name.lower() in team_key.lower() or team_key.lower() in team_name.lower():
            return key_players[team_key][:limit]
    
    # If we can't find the team, return generic player names
    return [f"Player 1 ({team_name})", f"Player 2 ({team_name})", f"Player 3 ({team_name})"]

def get_todays_match_details():
    """
    Get today's IPL match details using the function from todays_match.py
    """
    try:
        matches = fetch_today_matches()
        if matches and len(matches) > 0:
            match = matches[0]  # Get the first match for today
            return {
                'team1': match['team1'],
                'team2': match['team2'],
                'time': match['time'],
                'venue': match['venue']
            }
        else:
            print(f"{Fore.YELLOW}No IPL matches scheduled for today.{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}Error fetching today's match details: {str(e)}{Style.RESET_ALL}")
        return None

def get_team_comparison_via_api(team1_code, team2_code):
    """
    Try to get team comparison data via direct API call
    This is a fallback method that might work better than browser automation
    """
    try:
        print(f"{Fore.CYAN}Trying to get team comparison data via API for {team1_code} vs {team2_code}...{Style.RESET_ALL}")
        
        url = f"https://www.iplt20.com/comparison/show-team-stats"
        params = {
            'team_one': team1_code,
            'team_two': team2_code
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') and data.get('html'):
                print(f"{Fore.GREEN}Successfully fetched team comparison data via API{Style.RESET_ALL}")
                # Parse the HTML to extract comparison data
                soup = BeautifulSoup(data['html'], 'html.parser')
                table = soup.select_one('.ih-comparison-table')
                
                if not table:
                    print(f"{Fore.YELLOW}No comparison table found in API response{Style.RESET_ALL}")
                    return None
                
                # Get headers
                headers = []
                for th in table.select('th'):
                    headers.append(th.text.strip())
                
                if len(headers) < 3:
                    headers = ["Metric", "Team 1", "Team 2"]
                
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
                
                print(f"{Fore.GREEN}Extracted {len(comparison_data)} comparison metrics from API{Style.RESET_ALL}")
                
                result = {
                    "team1": TEAM_CODES.get(team1_code, team1_code),
                    "team2": TEAM_CODES.get(team2_code, team2_code),
                    "team1_code": team1_code,
                    "team2_code": team2_code,
                    "headers": headers,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "comparison_data": comparison_data
                }
                
                return result
            else:
                print(f"{Fore.YELLOW}API returned status false or no HTML data{Style.RESET_ALL}")
                return None
        else:
            print(f"{Fore.RED}API request failed with status code {response.status_code}{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}Error in API comparison method: {str(e)}{Style.RESET_ALL}")
        return None

def main():
    """
    Main function to run the IPL comparison scraper for today's match
    """
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  TODAY'S IPL MATCH COMPARISON DATA  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    
    start_time = datetime.datetime.now()
    print(f"Scraping started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Get today's match details
    today_match = get_todays_match_details()
    
    if not today_match:
        print(f"{Fore.YELLOW}No match details found for today. Exiting.{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}Today's IPL match: {today_match['team1']} vs {today_match['team2']}{Style.RESET_ALL}")
    print(f"Time: {today_match['time']}")
    print(f"Venue: {today_match['venue']}")
    
    # Get team codes
    team1_code = get_team_code(today_match['team1'])
    team2_code = get_team_code(today_match['team2'])
    
    # First try API method (faster and more reliable)
    team_comparison = get_team_comparison_via_api(team1_code, team2_code)
    
    # If API method failed, try browser automation
    if not team_comparison:
        print(f"{Fore.YELLOW}API method failed. Trying browser automation...{Style.RESET_ALL}")
        
        # Step 2: Setup WebDriver
        driver = setup_driver()
        
        if driver is None:
            print(f"{Fore.RED}Failed to set up WebDriver. Exiting.{Style.RESET_ALL}")
            return
        
        try:
            # Step 3: Scrape team comparison for today's match
            print(f"\n{Fore.CYAN}Scraping team comparison data...{Style.RESET_ALL}")
            team_comparison = scrape_team_comparison(driver, today_match['team1'], today_match['team2'])
            
        except Exception as e:
            print(f"{Fore.RED}Error in scraping process: {str(e)}{Style.RESET_ALL}")
        
        finally:
            # Close the driver if we opened it
            if driver:
                driver.quit()
                print(f"{Fore.CYAN}Closed WebDriver{Style.RESET_ALL}")
    
    # Step 4: Get key players for today's teams
    team1_players = get_key_player_names(today_match['team1'])
    team2_players = get_key_player_names(today_match['team2'])
    
    print(f"\n{Fore.GREEN}Key players for {today_match['team1']}: {', '.join(team1_players)}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Key players for {today_match['team2']}: {', '.join(team2_players)}{Style.RESET_ALL}")
    
    # Create summary report
    summary = {
        "match_date": datetime.datetime.now().strftime('%Y-%m-%d'),
        "team1": today_match['team1'],
        "team2": today_match['team2'],
        "venue": today_match['venue'],
        "time": today_match['time'],
        "team_comparison_available": team_comparison is not None,
        "team1_key_players": team1_players,
        "team2_key_players": team2_players,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Save summary
    timestamp = datetime.datetime.now().strftime('%Y%m%d')
    summary_filepath = os.path.join(COMPARISON_DATA_FOLDER, f"today_match_comparison_summary_{timestamp}.json")
    
    with open(summary_filepath, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)
    
    print(f"\n{Fore.GREEN}Saved match comparison summary to {summary_filepath}{Style.RESET_ALL}")
    
    # If we got team comparison data, save it
    if team_comparison:
        # Save as JSON and CSV
        filename = f"team_comparison_{team1_code}_vs_{team2_code}_{timestamp}"
        
        json_filepath = os.path.join(TEAM_COMPARISON_FOLDER, f"{filename}.json")
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(team_comparison, f, indent=4)
        print(f"{Fore.GREEN}Saved team comparison to {json_filepath}{Style.RESET_ALL}")
        
        # Save as CSV if we have comparison data
        if team_comparison.get("comparison_data"):
            df = pd.DataFrame(team_comparison["comparison_data"])
            csv_filepath = os.path.join(TEAM_COMPARISON_FOLDER, f"{filename}.csv")
            df.to_csv(csv_filepath, index=False)
            print(f"{Fore.GREEN}Saved team comparison CSV to {csv_filepath}{Style.RESET_ALL}")
    
    end_time = datetime.datetime.now()
    print(f"\n{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"Scraping finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time taken: {end_time - start_time}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")

if __name__ == "__main__":
    main()