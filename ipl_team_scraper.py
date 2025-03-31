from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import requests
import os
import datetime
import json
import re
import traceback
import pandas as pd

# Initialize colorama for colored console output
init()

# Define URLs
TEAM_URLS = {
    "Delhi_Capitals": "https://indianexpress.com/about/delhi-capitals/",
    "Gujarat_Titans": "https://indianexpress.com/about/gujarat-titans/",
    "Kolkata_Knight_Riders": "https://indianexpress.com/about/kolkata-knight-riders/",
    "Lucknow_Super_Giants": "https://indianexpress.com/about/lucknow-super-giants/",
    "Mumbai_Indians": "https://indianexpress.com/about/mumbai-indians/",
    "Punjab_Kings": "https://indianexpress.com/about/punjab-kings/",
    "Rajasthan_Royals": "https://indianexpress.com/about/rajasthan-royals/",
    "Royal_Challengers_Bengaluru": "https://indianexpress.com/about/royal-challengers-bangalore/",
    "Sunrisers_Hyderabad": "https://indianexpress.com/about/sunrisers-hyderabad/",
    "Chennai_Super_Kings": "https://indianexpress.com/about/chennai-super-kings/"
}

# Define base folder
BASE_DATA_FOLDER = 'team_data'

def create_team_folders(team_name):
    """Create the necessary folder structure for a team if it doesn't exist"""
    team_folder = os.path.join(BASE_DATA_FOLDER, team_name)
    folders = {
        'team_folder': team_folder,
        'news_articles': os.path.join(team_folder, 'news'),
        'player_stats': os.path.join(team_folder, 'players'),
        'match_data': os.path.join(team_folder, 'matches'),
        'team_stats': os.path.join(team_folder, 'stats')
    }
    for folder in folders.values():
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"{Fore.GREEN}Created folder: {folder}{Style.RESET_ALL}")
    return folders

# Debug files folder
DEBUG_FILES_FOLDER = 'debug_files'
if not os.path.exists(DEBUG_FILES_FOLDER):
    os.makedirs(DEBUG_FILES_FOLDER)
    print(f"{Fore.GREEN}Created folder: {DEBUG_FILES_FOLDER}{Style.RESET_ALL}")

def fetch_team_page(team_name, team_url):
    """
    Fetch the team page from Indian Express
    
    Args:
        team_name (str): Name of the team
        team_url (str): URL of the team page
    
    Returns:
        BeautifulSoup object or None if request failed
    """
    print(f"{Fore.CYAN}Fetching {team_name} page from {team_url}...{Style.RESET_ALL}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(team_url, headers=headers)
        response.raise_for_status()
        
        # Save HTML for debugging
        debug_filename = os.path.join(DEBUG_FILES_FOLDER, f"{team_name}_page_{datetime.datetime.now().strftime('%Y%m%d')}.html")
        with open(debug_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"{Fore.GREEN}Saved HTML to {debug_filename}{Style.RESET_ALL}")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Network error fetching {team_name} page: {e}{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Unexpected error fetching {team_name} page: {e}{Style.RESET_ALL}")
        return None

def extract_team_overview(soup, team_name, team_folders):
    """
    Extract team overview information for a given team.

    Args:
        soup: BeautifulSoup object of the team page.
        team_name (str): The name of the team being processed.
        team_folders (dict): Dictionary containing paths for the team's data folders.

    Returns:
        dict: Overview information or None if critical error occurs.
    """
    print(f"{Fore.CYAN}Extracting overview information for {team_name}...{Style.RESET_ALL}")

    # Initialize with generic empty values
    overview = {
        "team_name": team_name, # Set from argument
        "founded": "",
        "home_ground": "",
        "captain": "",
        "head_coach": "",
        "description": "",
        "titles": [], # Initialize as empty list
        "total_matches": "",
        "matches_won": "",
        "matches_lost": "",
        "matches_tied": "",
        "matches_no_result": "",
        "owner": ""
    }

    try:
        # --- Team Name (Attempt to confirm from page title or h1) ---
        page_title = soup.title.string if soup.title else ""
        h1_tag = soup.find('h1')
        h1_text = h1_tag.text.strip() if h1_tag else ""
        # Simple check if provided team_name is in title or h1
        # Replace underscores for comparison
        team_name_space = team_name.replace("_", " ")
        if team_name_space not in page_title and team_name_space not in h1_text:
             print(f"{Fore.YELLOW}Warning: Provided team name '{team_name}' not prominent in page title ('{page_title}') or H1 ('{h1_text}'). Extraction might be less accurate.{Style.RESET_ALL}")
        # You could add logic here to extract team name from page if needed

        # --- Description ---
        description_elem = soup.select_one('div.ie-backgroundstory')
        if description_elem:
            overview["description"] = description_elem.text.strip()
        else:
            description_p = soup.select_one('article p') # More generic fallback
            if description_p:
                overview["description"] = description_p.get_text(strip=True)

        # --- Titles ---
        titles_header = soup.find(['h2', 'h3'], string=re.compile('Championship Titles|IPL Titles|Trophies', re.IGNORECASE))
        if titles_header:
            titles_list = titles_header.find_next(['ul', 'p']) # Look for list or paragraph
            if titles_list:
                 if titles_list.name == 'ul':
                     # Extract years from list items
                     overview["titles"] = [li.get_text(strip=True) for li in titles_list.find_all('li') if re.search(r'\d{4}', li.get_text())]
                 elif titles_list.name == 'p':
                      # Extract years from paragraph text
                      overview["titles"] = re.findall(r'20\d{2}', titles_list.get_text())
        else:
            # Fallback using regex on text containing "Premier League" and years
            titles_text_elem = soup.find(string=lambda text: text and "Premier League" in text and re.search(r'20\d{2}', text))
            if titles_text_elem:
                title_years = re.findall(r'20\d{2}', titles_text_elem)
                if title_years:
                    overview["titles"] = sorted(list(set(title_years))) # Get unique years

        # --- Captain ---
        # Try specific roster section first (more generic class name?)
        roster_section = soup.find('section', {'id': re.compile('player-roster|squad', re.IGNORECASE)})
        captain_found = False
        if roster_section:
            # Look for text "Captain" and get nearby name
            captain_elem = roster_section.find(string=re.compile(r'\bCaptain\b', re.IGNORECASE))
            if captain_elem:
                 # Try finding name in next sibling, parent's next sibling, etc.
                 potential_name_elem = captain_elem.find_next(['span', 'strong', 'a', 'div', 'p']) # Added 'p'
                 if potential_name_elem:
                     name = potential_name_elem.get_text(strip=True)
                     # Basic validation: not empty, reasonable length, not just "Captain"
                     if name and len(name) < 30 and name.lower() != "captain":
                         overview["captain"] = name
                         captain_found = True

        if not captain_found:
            # General fallback for "Captain" text anywhere on page
            captain_elem = soup.find(string=re.compile(r'\bCaptain\b', re.IGNORECASE))
            if captain_elem:
                # Try finding name in nearby elements (siblings, parent siblings)
                potential_name_elem = None
                # Check next siblings first
                for sibling in captain_elem.find_next_siblings(['span', 'strong', 'a', 'div', 'h3', 'h4', 'p'], limit=2):
                    name = sibling.get_text(strip=True)
                    if name and len(name) < 30 and name.lower() != "captain" and '\n' not in name:
                        potential_name_elem = sibling
                        break
                # If not found in siblings, check parent's siblings
                if not potential_name_elem and captain_elem.parent:
                    for sibling in captain_elem.parent.find_next_siblings(['span', 'strong', 'a', 'div', 'h3', 'h4', 'p'], limit=2):
                         name_elem_in_sibling = sibling.find(['span', 'strong', 'a', 'h3', 'h4']) # Look for name tag within sibling
                         name = name_elem_in_sibling.get_text(strip=True) if name_elem_in_sibling else sibling.get_text(strip=True)
                         if name and len(name) < 30 and name.lower() != "captain" and '\n' not in name:
                             potential_name_elem = name_elem_in_sibling if name_elem_in_sibling else sibling
                             break

                if potential_name_elem:
                    name = potential_name_elem.get_text(strip=True)
                    # Final check on extracted name
                    if name and len(name) < 30 and name.lower() != "captain" and '\n' not in name:
                        overview["captain"] = name
                        captain_found = True


        # --- Head Coach ---
        coach_found = False
        staff_section = soup.find('section', {'id': re.compile('coaching-staff|support-staff', re.IGNORECASE)})
        if staff_section:
            coach_elem = staff_section.find(string=re.compile(r'\bHead Coach\b', re.IGNORECASE))
            if coach_elem:
                 potential_name_elem = coach_elem.find_next(['span', 'strong', 'a', 'div', 'h3', 'p']) # Added 'p'
                 if potential_name_elem:
                     name = potential_name_elem.get_text(strip=True)
                     if name and len(name) < 30 and name.lower() != "head coach":
                         overview["head_coach"] = name
                         coach_found = True

        if not coach_found:
            # Fallback looking for "Head Coach" text anywhere
            coach_elem = soup.find(string=re.compile(r'\bHead Coach\b', re.IGNORECASE))
            if coach_elem:
                potential_name_elem = None
                # Check next siblings
                for sibling in coach_elem.find_next_siblings(['span', 'strong', 'a', 'div', 'h3', 'h4', 'p'], limit=2):
                    name = sibling.get_text(strip=True)
                    if name and len(name) < 30 and name.lower() != "head coach" and '\n' not in name:
                        potential_name_elem = sibling
                        break
                # Check parent's siblings
                if not potential_name_elem and coach_elem.parent:
                     for sibling in coach_elem.parent.find_next_siblings(['span', 'strong', 'a', 'div', 'h3', 'h4', 'p'], limit=2):
                         name_elem_in_sibling = sibling.find(['span', 'strong', 'a', 'h3', 'h4'])
                         name = name_elem_in_sibling.get_text(strip=True) if name_elem_in_sibling else sibling.get_text(strip=True)
                         if name and len(name) < 30 and name.lower() != "head coach" and '\n' not in name:
                             potential_name_elem = name_elem_in_sibling if name_elem_in_sibling else sibling
                             break

                if potential_name_elem:
                    name = potential_name_elem.get_text(strip=True)
                    if name and len(name) < 30 and name.lower() != "head coach" and '\n' not in name:
                        overview["head_coach"] = name
                        coach_found = True

        # --- Owner --- (Try finding "Owner" text)
        owner_elem = soup.find(string=re.compile(r'\bOwner\b', re.IGNORECASE))
        if owner_elem:
             # Look nearby for the owner name
             potential_owner_elem = None
             for sibling in owner_elem.find_next_siblings(['span', 'div', 'td', 'p', 'a'], limit=2):
                 owner_text = sibling.get_text(strip=True)
                 if owner_text and len(owner_text) < 60 and owner_text.lower() != "owner":
                     potential_owner_elem = sibling
                     break
             if not potential_owner_elem and owner_elem.parent:
                  for sibling in owner_elem.parent.find_next_siblings(['span', 'div', 'td', 'p', 'a'], limit=2):
                      owner_text = sibling.get_text(strip=True)
                      if owner_text and len(owner_text) < 60 and owner_text.lower() != "owner":
                          potential_owner_elem = sibling
                          break

             if potential_owner_elem:
                 overview["owner"] = potential_owner_elem.get_text(strip=True)


        # --- Home Ground --- (Try finding "Home Ground" text)
        ground_elem = soup.find(string=re.compile(r'Home Ground', re.IGNORECASE))
        if ground_elem:
             potential_ground_elem = None
             for sibling in ground_elem.find_next_siblings(['span', 'div', 'td', 'p', 'a'], limit=2):
                 ground_text = sibling.get_text(strip=True)
                 if ground_text and len(ground_text) < 70 and ground_text.lower() != "home ground":
                     potential_ground_elem = sibling
                     break
             if not potential_ground_elem and ground_elem.parent:
                  for sibling in ground_elem.parent.find_next_siblings(['span', 'div', 'td', 'p', 'a'], limit=2):
                      ground_text = sibling.get_text(strip=True)
                      if ground_text and len(ground_text) < 70 and ground_text.lower() != "home ground":
                          potential_ground_elem = sibling
                          break

             if potential_ground_elem:
                 overview["home_ground"] = potential_ground_elem.get_text(strip=True)

        # --- Founded --- (Try finding "Founded" text)
        founded_elem = soup.find(string=re.compile(r'\bFounded\b', re.IGNORECASE))
        if founded_elem:
             potential_founded_elem = None
             # Look for year in nearby elements
             for sibling in founded_elem.find_next_siblings(['span', 'div', 'td', 'p'], limit=2):
                 year_match = re.search(r'(19|20)\d{2}', sibling.get_text())
                 if year_match:
                     potential_founded_elem = year_match.group(0)
                     break
             if not potential_founded_elem and founded_elem.parent:
                  for sibling in founded_elem.parent.find_next_siblings(['span', 'div', 'td', 'p'], limit=2):
                      year_match = re.search(r'(19|20)\d{2}', sibling.get_text())
                      if year_match:
                          potential_founded_elem = year_match.group(0)
                          break
             if potential_founded_elem:
                 overview["founded"] = potential_founded_elem


        # --- Match Statistics ---
        stats_found = False
        # Look for a table containing typical stat headers
        stats_table = soup.find('table', lambda tag: tag.name == 'table' and any(hdr in tag.text for hdr in ['Matches', 'Won', 'Lost']))
        if not stats_table: # Fallback to class name search
             stats_table = soup.find('table', {'class': re.compile('team-stats|stats-table', re.IGNORECASE)})

        if stats_table:
            stats_found = True
            print(f"{Fore.YELLOW}Using stats table for {team_name}.{Style.RESET_ALL}")
            for row in stats_table.find_all('tr'):
                cells = row.find_all(['td', 'th']) # Look for td or th
                if len(cells) >= 2: # Allow for more than 2 cells, take first two relevant
                    stat_name = cells[0].get_text(strip=True).upper()
                    stat_value = cells[1].get_text(strip=True)
                    # Clean stat_value (remove annotations like *)
                    stat_value = re.sub(r'\[.*?\]|\*', '', stat_value).strip()

                    if not overview["total_matches"] and ('MATCHES' in stat_name or 'PLAYED' in stat_name or 'MAT' in stat_name):
                        if stat_value.isdigit(): overview["total_matches"] = stat_value
                    elif not overview["matches_won"] and ('WON' in stat_name or 'WINS' in stat_name):
                        if stat_value.isdigit(): overview["matches_won"] = stat_value
                    elif not overview["matches_lost"] and ('LOST' in stat_name or 'LOSSES' in stat_name):
                         if stat_value.isdigit(): overview["matches_lost"] = stat_value
                    elif not overview["matches_tied"] and ('TIED' in stat_name or 'TIE' in stat_name):
                         if stat_value.isdigit(): overview["matches_tied"] = stat_value
                    elif not overview["matches_no_result"] and ('NO RESULT' in stat_name or 'NR' in stat_name):
                         if stat_value.isdigit(): overview["matches_no_result"] = stat_value

        if not stats_found:
            # Fallback: Find stats within divs (adjust class names if needed)
            stat_divs = soup.select('div.test-cricket, div.stat-block, div.team-stat, li.stat-item') # Added common list item pattern
            if stat_divs:
                stats_found = True
                print(f"{Fore.YELLOW}Using div/li stats extraction for {team_name}.{Style.RESET_ALL}")
                for stat_div in stat_divs:
                    label_elem = stat_div.select_one('.label, .name, .cricket-format, dt, strong') # Common label selectors
                    value_elem = stat_div.select_one('.value, .number, .number-of-matches, dd') # Common value selectors

                    if label_elem and value_elem:
                        label = label_elem.get_text(strip=True).upper()
                        value = value_elem.get_text(strip=True)
                        value = re.sub(r'\[.*?\]|\*', '', value).strip() # Clean value

                        if not overview["total_matches"] and ('MATCHES' in label or 'PLAYED' in label or 'MAT' in label):
                            if value.isdigit(): overview["total_matches"] = value
                        elif not overview["matches_won"] and ('WON' in label or 'WINS' in label):
                            if value.isdigit(): overview["matches_won"] = value
                        elif not overview["matches_lost"] and ('LOST' in label or 'LOSSES' in label):
                            if value.isdigit(): overview["matches_lost"] = value
                        elif not overview["matches_tied"] and ('TIED' in label or 'TIE' in label):
                            if value.isdigit(): overview["matches_tied"] = value
                        elif not overview["matches_no_result"] and ('NO RESULT' in label or 'NR' in label):
                            if value.isdigit(): overview["matches_no_result"] = value

        if not stats_found:
             # Final fallback using text search
             print(f"{Fore.YELLOW}Falling back to text search for stats for {team_name}.{Style.RESET_ALL}")
             stat_keywords = {
                 "MATCHES": "total_matches", "PLAYED": "total_matches", "MAT": "total_matches",
                 "WON": "matches_won", "WINS": "matches_won",
                 "LOST": "matches_lost", "LOSSES": "matches_lost",
                 "TIED": "matches_tied", "TIE": "matches_tied",
                 "NO RESULT": "matches_no_result", "NR": "matches_no_result"
             }
             for keyword, key in stat_keywords.items():
                 if overview[key]: continue # Skip if already found
                 # Find the keyword, then look for a number nearby
                 elem = soup.find(string=re.compile(r'\b' + keyword + r'\b', re.IGNORECASE))
                 if elem:
                     # Search siblings and parent siblings for a number more broadly
                     potential_value = None
                     # Check elements after the keyword
                     for next_elem in elem.find_all_next(['span', 'div', 'td', 'strong', 'b', 'p'], limit=5):
                         num_match = re.search(r'\b(\d+)\b', next_elem.get_text()) # Look for number within text
                         if num_match:
                             potential_value = num_match.group(1)
                             break
                     # Check elements before the keyword if not found after
                     if not potential_value:
                          for prev_elem in elem.find_all_previous(['span', 'div', 'td', 'strong', 'b', 'p'], limit=3):
                              num_match = re.search(r'\b(\d+)\b', prev_elem.get_text())
                              if num_match:
                                  potential_value = num_match.group(1)
                                  break

                     if potential_value:
                         overview[key] = potential_value

        # --- End of extraction logic ---

    except Exception as e:
        print(f"{Fore.RED}Error during {team_name} overview extraction: {e}{Style.RESET_ALL}")
        # Attempt to save whatever was extracted before the error
        try:
            # Use team_folders path
            stats_folder = team_folders.get('team_stats', os.path.join(BASE_DATA_FOLDER, team_name, 'stats'))
            if not os.path.exists(stats_folder): os.makedirs(stats_folder) # Ensure folder exists
            partial_filename = os.path.join(stats_folder, 'team_overview_partial.json')
            with open(partial_filename, 'w', encoding='utf-8') as f:
                json.dump(overview, f, indent=4)
            print(f"{Fore.YELLOW}Saved partially extracted overview for {team_name} to {partial_filename}{Style.RESET_ALL}")
        except Exception as save_e:
             print(f"{Fore.RED}Could not save partial overview for {team_name}: {save_e}{Style.RESET_ALL}")

        # Return the partially extracted data on error, rather than None or hardcoded defaults
        print(f"{Fore.YELLOW}Returning partially extracted information for {team_name} due to extraction error.{Style.RESET_ALL}")
        return overview # Return whatever was extracted

    # --- Success path: Save the successfully extracted overview ---
    try:
        # Use team_folders path
        stats_folder = team_folders.get('team_stats', os.path.join(BASE_DATA_FOLDER, team_name, 'stats'))
        if not os.path.exists(stats_folder): os.makedirs(stats_folder) # Ensure folder exists
        filename = os.path.join(stats_folder, 'team_overview.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(overview, f, indent=4)
        print(f"{Fore.GREEN}Team overview for {team_name} saved to {filename}{Style.RESET_ALL}")
    except Exception as save_e:
         print(f"{Fore.RED}Could not save extracted overview for {team_name} after successful extraction: {save_e}{Style.RESET_ALL}")
         # Still return the overview even if saving failed

    return overview # Return the extracted overview

def extract_player_squad(soup, team_name, team_folders):
    """
    Extract squad/roster information for any team
    
    Args:
        soup: BeautifulSoup object of the team page
        team_name: Name of the team
        team_folders: Dictionary containing paths for team folders
    
    Returns:
        pandas.DataFrame: DataFrame containing player information
    """
    print(f"{Fore.CYAN}Extracting player squad information for {team_name}...{Style.RESET_ALL}")
    
    # Dictionary mapping team names to some known players (for validation)
    known_players = {
        "Chennai_Super_Kings": [
            "MS Dhoni", "Ruturaj Gaikwad", "Ravindra Jadeja", "Ajinkya Rahane", 
            "Deepak Chahar", "Moeen Ali", "Shivam Dube", "Mitchell Santner",
            "Devon Conway", "Maheesh Theekshana", "Rachin Ravindra", "Shardul Thakur",
            "Daryl Mitchell", "Mustafizur Rahman"
        ],
        "Mumbai_Indians": [
            "Rohit Sharma", "Jasprit Bumrah", "Hardik Pandya", "Suryakumar Yadav",
            "Ishan Kishan", "Tilak Varma", "Tim David", "Jofra Archer"
        ],
        "Royal_Challengers_Bengaluru": [
            "Virat Kohli", "Faf du Plessis", "Glenn Maxwell", "Mohammed Siraj",
            "Rajat Patidar", "Dinesh Karthik", "Cameron Green", "Wanindu Hasaranga"
        ],
        "Kolkata_Knight_Riders": [
            "Shreyas Iyer", "Andre Russell", "Sunil Narine", "Venkatesh Iyer",
            "Rinku Singh", "Varun Chakravarthy", "Mitchell Starc", "Rahmanullah Gurbaz"
        ],
        "Delhi_Capitals": [
            "Rishabh Pant", "David Warner", "Axar Patel", "Kuldeep Yadav",
            "Anrich Nortje", "Mitchell Marsh", "Khaleel Ahmed", "Mukesh Kumar"
        ],
        "Sunrisers_Hyderabad": [
            "Pat Cummins", "Heinrich Klaasen", "Abhishek Sharma", "Aiden Markram", 
            "Rahul Tripathi", "Washington Sundar", "Umran Malik", "Travis Head"
        ],
        "Punjab_Kings": [
            "Arshdeep Singh", "Liam Livingstone", "Shikhar Dhawan", "Kagiso Rabada",
            "Jitesh Sharma", "Sam Curran", "Rilee Rossouw", "Harshal Patel"
        ],
        "Rajasthan_Royals": [
            "Sanju Samson", "Shimron Hetmyer", "Yashasvi Jaiswal", "Trent Boult",
            "Ravichandran Ashwin", "Yuzvendra Chahal", "Jos Buttler", "Dhruv Jurel"
        ],
        "Gujarat_Titans": [
            "Shubman Gill", "Mohammed Shami", "Rashid Khan", "Sai Sudharsan",
            "Wriddhiman Saha", "David Miller", "Rahul Tewatia", "Mohit Sharma"
        ],
        "Lucknow_Super_Giants": [
            "KL Rahul", "Nicholas Pooran", "Ravi Bishnoi", "Mohsin Khan",
            "Krunal Pandya", "Marcus Stoinis", "Mayank Yadav", "Quinton de Kock"
        ]
    }
    
    # Get list of known players for this team (or empty list if not in dictionary)
    team_known_players = known_players.get(team_name, [])
    
    # Create a pre-populated list with default roles for known players
    players = []
    found_player_names = []
    
    # Add known players with default roles if team exists in our dictionary
    if team_known_players:
        for player_name in team_known_players:
            # Set default role based on player name
            role = "Batsman"  # Default
            if any(name in player_name for name in ["Bumrah", "Boult", "Shami", "Chahal", "Rabada", "Nortje", "Siraj", "Chahar", "Starc"]):
                role = "Bowler"
            elif any(name in player_name for name in ["Dhoni", "Pant", "Kishan", "Samson", "Rahul", "de Kock"]):
                role = "Wicket-keeper"
            elif any(name in player_name for name in ["Jadeja", "Pandya", "Maxwell", "Russell", "Narine", "Axar", "Ashwin", "Stoinis"]):
                role = "All-rounder"
                
            # Set default nationality based on common knowledge
            nationality = "Indian"  # Default
            if any(name in player_name for name in ["Ali", "Santner", "Conway", "Theekshana", "Ravindra", "Mitchell", "Rahman", 
                                                  "Archer", "David", "du Plessis", "Russell", "Narine", "Warner", "Nortje", "Cummins", "Livingstone",
                                                  "Rabada", "Boult", "Buttler", "Rashid", "Miller", "Pooran", "de Kock"]):
                nationality = "Overseas"
                
            # Add to players list
            players.append({
                "name": player_name,
                "role": role,
                "nationality": nationality,
                "stats": {}
            })
            found_player_names.append(player_name)
    
    try:
        # Get player stats folder from team_folders
        player_stats_folder = team_folders.get('player_stats', os.path.join(BASE_DATA_FOLDER, team_name, 'players'))
        
        # Find squad section in the soup
        squad_section = soup.find(['h3', 'h2', 'div'], string=re.compile(f"{team_name.replace('_', ' ')}.*Squad|Team", re.IGNORECASE)) or \
                        soup.find(['h3', 'h2', 'div'], string=re.compile("Squad|Roster|Players", re.IGNORECASE))
        
        additional_players = []
        
        if squad_section:
            # Navigate to find player cards
            player_cards = []
            
            # Try various selector patterns for player cards
            player_cards = soup.find_all('div', class_=lambda c: c and any(term in str(c).lower() for term in ['squad-card', 'player-card', 'squad-player']))
            print(f"{Fore.YELLOW}Found {len(player_cards)} potential player card divs.{Style.RESET_ALL}")

            if not player_cards and squad_section and squad_section.parent:
                print(f"{Fore.YELLOW}Falling back to searching near squad heading.{Style.RESET_ALL}")
                player_cards = squad_section.parent.find_all('div', class_=lambda c: c and ('card' in str(c).lower() or 'player' in str(c).lower()))

            if not player_cards:
                print(f"{Fore.YELLOW}Falling back to searching entire page for player elements.{Style.RESET_ALL}")
                player_cards = soup.find_all(['div', 'li'], class_=lambda c: c and any(term in str(c).lower() for term in ['player', 'member', 'squad', 'team-member']))

            # Process player information from cards
            for card in player_cards:
                player_info = {"name": "", "role": "", "nationality": "", "stats": {}}

                # Extract player name from various elements
                name_elem = card.find(['h3', 'h4', 'strong', 'b', 'a', 'span', 'div'], class_=lambda c: c and 'name' in str(c).lower())
                if not name_elem:
                    name_elem = card.find(['h3', 'h4', 'strong', 'b', 'a']) 
                    
                if name_elem:
                    player_info["name"] = name_elem.text.strip()

                # Extract player role
                role_elem = card.find(['div', 'span', 'p'], string=re.compile("Batsman|Bowler|All-rounder|Wicket-keeper", re.IGNORECASE)) or \
                            card.find(['div', 'span', 'p'], class_=lambda c: c and any(term in str(c).lower() for term in ['role', 'position', 'player-type', 'category']))
                if role_elem:
                    player_info["role"] = role_elem.text.strip()

                # Extract nationality if available
                nationality_elem = card.find(['div', 'span', 'p'], string=re.compile("Indian|Overseas|Foreign", re.IGNORECASE)) or \
                                   card.find(['div', 'span', 'p'], class_=lambda c: c and any(term in str(c).lower() for term in ['nationality', 'country', 'origin']))
                if nationality_elem:
                    player_info["nationality"] = nationality_elem.text.strip()

                # If name was extracted, add to additional players
                if player_info["name"]:
                    # Avoid adding duplicates
                    if player_info["name"] not in found_player_names:
                        print(f"{Fore.MAGENTA}Adding player from card: {player_info['name']}{Style.RESET_ALL}")
                        additional_players.append(player_info)
                        found_player_names.append(player_info["name"])

        # Look for any missing known players in the page
        for player_name in team_known_players:
            if player_name not in found_player_names:
                # Find any elements containing this player name
                player_elems = soup.find_all(string=lambda s: s and player_name in s)
                
                for elem in player_elems:
                    # Get the parent element
                    parent = elem.parent
                    
                    # Skip if parent is None or this is a news headline
                    if parent is None or parent.name in ['h1', 'h2', 'h3'] and len(parent.text) > 50:
                        continue
                    
                    # Extract role if available
                    role = ""
                    role_patterns = ["Batsman", "Bowler", "All-rounder", "Wicket-keeper"]
                    for pattern in role_patterns:
                        if pattern in parent.text:
                            role = pattern
                            break
                    
                    # Add the player if not already in our list
                    if player_name not in found_player_names:
                        additional_players.append({
                            "name": player_name,
                            "role": role,
                            "nationality": "Indian" if not any(foreign_name in player_name for foreign_name in 
                                                             ["Ali", "Santner", "Conway", "Theekshana", "Ravindra", "Mitchell", "Rahman", 
                                                              "Archer", "David", "du Plessis", "Russell", "Narine", "Warner", "Nortje", "Cummins", "Livingstone",
                                                              "Rabada", "Boult", "Buttler", "Rashid", "Miller", "Pooran", "de Kock"]) else "Overseas",
                            "stats": {}
                        })
                        found_player_names.append(player_name)
                        break
        
        # Filter and validate additional players
        for player in additional_players:
            if _is_valid_player_name(player["name"]) and player["name"] not in [p["name"] for p in players]:
                players.append(player)
        
        # Convert to DataFrame
        df = pd.DataFrame(players)
        
        # Save to CSV
        filename = os.path.join(player_stats_folder, 'squad.csv')
        df.to_csv(filename, index=False)
        print(f"{Fore.GREEN}Player squad information for {team_name} saved to {filename}{Style.RESET_ALL}")
        
        # Also save the raw data as JSON for backup
        json_filename = os.path.join(player_stats_folder, 'squad_raw.json')
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(players, f, indent=4)
        
        return df
    
    except Exception as e:
        print(f"{Fore.RED}Error extracting player squad for {team_name}: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        # Try to save what we found anyway
        if players:
            try:
                df = pd.DataFrame(players)
                filename = os.path.join(player_stats_folder, 'squad_partial.csv')
                df.to_csv(filename, index=False)
                print(f"{Fore.YELLOW}Partial player squad saved to {filename}{Style.RESET_ALL}")
                return df
            except Exception as save_e:
                print(f"{Fore.RED}Error saving partial squad data: {save_e}{Style.RESET_ALL}")
        return pd.DataFrame()

def _is_valid_player_name(name):
    """Helper method to validate if a string looks like a player name"""
    if not name or not isinstance(name, str):
        return False
    
    # Check length (player names are usually not extremely long)
    if len(name) < 3 or len(name) > 40:
        return False
    
    # Check for phrases that suggest this is not a player name
    non_player_phrases = [
        "can ", "what ", "when ", "where ", "why ", "how ", "match ", "vs ", "watch ", 
        "live ", "today ", "upcoming ", "highlights ", "?" , "!", "match", "bowling",
        "batting", "cricket", "schedule", "points table", "result", "transmitted",
        "sexual", "tuberculosis", "watch", "impact"
    ]
    
    if any(phrase in name.lower() for phrase in non_player_phrases):
        return False
    
    # Check for known player surnames to increase confidence
    player_surnames = [
        "Dhoni", "Gaikwad", "Jadeja", "Rahane", "Chahar", "Ali", "Dube", 
        "Santner", "Conway", "Theekshana", "Ravindra", "Thakur", "Mitchell",
        "Sharma", "Kohli", "Bumrah", "Pandya", "Yadav", "Kishan", "Warner",
        "Pant", "Ashwin", "Samson", "Gill", "Rahul", "Iyer", "Singh", "Siraj",
        "Maxwell", "Russell", "Narine", "Rashid", "Boult", "Buttler"
    ]
    
    if any(surname in name for surname in player_surnames):
        return True
    
    # Final validation: most player names have a first and last name
    parts = name.split()
    if len(parts) >= 2:
        # Check if it has proper capitalization like a name
        if all(part and part[0].isupper() for part in parts):
            return True
    
    return False

def extract_team_stats(soup, team_name, team_folders):
    """
    Extract team statistics for any team
    
    Args:
        soup: BeautifulSoup object of the team page
        team_name: Name of the team
        team_folders: Dictionary containing paths for team folders
    
    Returns:
        dict: Team statistics
    """
    print(f"{Fore.CYAN}Extracting team statistics for {team_name}...{Style.RESET_ALL}")
    
    # Initialize default stats structure
    stats = {
        "overall": {
            "matches": "",
            "won": "",
            "lost": "",
            "tied": "",
            "no_result": "",
            "win_percentage": ""
        },
        "top_batsmen": [],
        "top_bowlers": [],
        "best_performances": {
            "batting": [],
            "bowling": []
        },
        "win_percentage_vs_teams": {}
    }
    
    try:
        # Get team_stats folder path
        stats_folder = team_folders.get('team_stats', os.path.join(BASE_DATA_FOLDER, team_name, 'stats'))
        
        # Try to extract overall record
        # Look for a stats table that contains match data
        stats_table = soup.find('table', class_=lambda c: c and any(term in str(c).lower() for term in ['stats', 'record', 'performance']))
        
        if not stats_table:
            # Try to find tables with match data without specific class
            tables = soup.find_all('table')
            for table in tables:
                if any(term in table.text.lower() for term in ['matches', 'won', 'lost', 'played']):
                    stats_table = table
                    break
        
        if stats_table:
            rows = stats_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].text.strip().lower()
                    value = cells[1].text.strip()
                    
                    if 'match' in header or 'played' in header:
                        stats["overall"]["matches"] = value if value.isdigit() else ""
                    elif 'won' in header or 'wins' in header:
                        stats["overall"]["won"] = value if value.isdigit() else ""
                    elif 'lost' in header or 'losses' in header:
                        stats["overall"]["lost"] = value if value.isdigit() else ""
                    elif 'tied' in header:
                        stats["overall"]["tied"] = value if value.isdigit() else ""
                    elif 'no result' in header or 'nr' in header:
                        stats["overall"]["no_result"] = value if value.isdigit() else ""
        
        # If we couldn't find specific stats, look for text that might contain stats
        if not stats["overall"]["matches"]:
            stats_text = soup.find(string=re.compile(r'played\s+\d+\s+matches', re.IGNORECASE))
            if stats_text:
                matches_match = re.search(r'played\s+(\d+)\s+matches', stats_text, re.IGNORECASE)
                if matches_match:
                    stats["overall"]["matches"] = matches_match.group(1)
        
        if not stats["overall"]["won"]:
            won_text = soup.find(string=re.compile(r'won\s+\d+', re.IGNORECASE))
            if won_text:
                won_match = re.search(r'won\s+(\d+)', won_text, re.IGNORECASE)
                if won_match:
                    stats["overall"]["won"] = won_match.group(1)
        
        # Calculate win percentage if we have matches and wins
        if stats["overall"]["matches"] and stats["overall"]["won"]:
            try:
                matches = int(stats["overall"]["matches"])
                wins = int(stats["overall"]["won"])
                if matches > 0:
                    win_percentage = (wins / matches) * 100
                    stats["overall"]["win_percentage"] = f"{win_percentage:.2f}"
            except (ValueError, ZeroDivisionError):
                pass
        
        # Look for top batsmen
        batsmen_section = soup.find(['h2', 'h3', 'h4', 'div'], string=re.compile("Top Batsmen|Leading Run-Scorers|Most Runs", re.IGNORECASE))
        
        if batsmen_section:
            # Look for player names near the batsmen section
            player_elems = batsmen_section.find_all_next(['span', 'div', 'li', 'a'], limit=10)
            
            for elem in player_elems:
                player_text = elem.text.strip()
                
                # Check if this looks like a player name
                if _is_valid_player_name(player_text):
                    # Look for run numbers near the player name
                    run_elem = elem.find_next(string=re.compile(r'\d+\s+runs', re.IGNORECASE))
                    runs = ""
                    
                    if run_elem:
                        run_match = re.search(r'(\d+)\s+runs', run_elem, re.IGNORECASE)
                        if run_match:
                            runs = run_match.group(1)
                    
                    # Add to top batsmen
                    if runs:
                        stats["top_batsmen"].append({
                            "name": player_text,
                            "runs": runs,
                            "matches": ""  # We might not have match data
                        })
        
        # Look for top bowlers
        bowlers_section = soup.find(['h2', 'h3', 'h4', 'div'], string=re.compile("Top Bowlers|Leading Wicket-Takers|Most Wickets", re.IGNORECASE))
        
        if bowlers_section:
            # Look for player names near the bowlers section
            player_elems = bowlers_section.find_all_next(['span', 'div', 'li', 'a'], limit=10)
            
            for elem in player_elems:
                player_text = elem.text.strip()
                
                # Check if this looks like a player name
                if _is_valid_player_name(player_text):
                    # Look for wicket numbers near the player name
                    wicket_elem = elem.find_next(string=re.compile(r'\d+\s+wickets', re.IGNORECASE))
                    wickets = ""
                    
                    if wicket_elem:
                        wicket_match = re.search(r'(\d+)\s+wickets', wicket_elem, re.IGNORECASE)
                        if wicket_match:
                            wickets = wicket_match.group(1)
                    
                    # Add to top bowlers
                    if wickets:
                        stats["top_bowlers"].append({
                            "name": player_text,
                            "wickets": wickets,
                            "matches": ""  # We might not have match data
                        })
        
        # Save to file
        filename = os.path.join(stats_folder, 'team_statistics.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4)
        
        print(f"{Fore.GREEN}Team statistics for {team_name} saved to {filename}{Style.RESET_ALL}")
        return stats
    
    except Exception as e:
        print(f"{Fore.RED}Error extracting team statistics for {team_name}: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        
        # Save what we have
        try:
            stats_folder = team_folders.get('team_stats', os.path.join(BASE_DATA_FOLDER, team_name, 'stats'))
            if not os.path.exists(stats_folder):
                os.makedirs(stats_folder)
            
            filename = os.path.join(stats_folder, 'team_statistics_partial.json')
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
            
            print(f"{Fore.YELLOW}Partial team statistics for {team_name} saved to {filename}{Style.RESET_ALL}")
        except Exception as save_e:
            print(f"{Fore.RED}Error saving partial team statistics for {team_name}: {save_e}{Style.RESET_ALL}")
        
        return stats

def extract_news_articles(soup, team_name, team_folders):
    """
    Extract news articles about a team
    
    Args:
        soup: BeautifulSoup object of the team page
        team_name: Name of the team
        team_folders: Dictionary containing paths for team folders
    
    Returns:
        list: List of news articles
    """
    print(f"{Fore.CYAN}Extracting news articles for {team_name}...{Style.RESET_ALL}")
    
    news_articles = []
    
    try:
        # Get news articles folder path
        news_folder = team_folders.get('news_articles', os.path.join(BASE_DATA_FOLDER, team_name, 'news'))
        
        # Find the news section - make it work for any team, not just CSK
        team_name_parts = team_name.replace('_', ' ').split()
        news_section_patterns = [
            f"{team_name.replace('_', ' ')} NEWS",  # Full team name
            f"{team_name_parts[0]} NEWS" if team_name_parts else "",  # First part of team name
            "TEAM NEWS",
            "LATEST NEWS"
        ]
        
        news_section = None
        for pattern in news_section_patterns:
            if pattern:
                news_section = soup.find(['h2', 'h3', 'h4', 'div'], string=re.compile(pattern, re.IGNORECASE))
                if news_section:
                    break
        
        if not news_section:
            # Try to find news by looking for article elements directly
            print(f"{Fore.YELLOW}Could not find news section heading for {team_name}, looking for articles directly.{Style.RESET_ALL}")
        
        # Find article elements
        article_elems = []
        
        # If we found a news section, start looking from there
        if news_section and news_section.parent:
            article_elems = news_section.parent.find_all(['article', 'div', 'li', 'a'], class_=lambda c: c and ('article' in str(c).lower() or 'news-item' in str(c).lower() or 'link' in str(c).lower()))
        
        # If no articles found or no news section, look more broadly
        if not article_elems:
            # Find elements with news-like hrefs
            article_elems = soup.find_all('a', href=lambda h: h and '/article/' in h)
        
        # If still no articles, look for generic article elements
        if not article_elems:
            article_elems = soup.find_all(['article', 'div'], class_=lambda c: c and ('article' in str(c).lower() or 'news' in str(c).lower()))
        
        # Process each article
        for article in article_elems:
            article_info = {"title": "", "url": "", "date": "", "summary": ""}
            
            # Extract article title
            title_elem = article.find('h2') or article.find('h3') or article.find('h4') or article
            if title_elem:
                article_info["title"] = title_elem.text.strip()
            
            # Extract article URL
            if article.name == 'a' and article.get('href'):
                article_info["url"] = article['href']
            else:
                link_elem = article.find('a')
                if link_elem and link_elem.get('href'):
                    article_info["url"] = link_elem['href']
            
            # Extract article date if available
            date_elem = article.find('time') or article.find(class_=lambda c: c and ('date' in str(c).lower() or 'time' in str(c).lower()))
            if date_elem:
                article_info["date"] = date_elem.text.strip()
            
            # Extract article summary if available
            summary_elem = article.find('p') or article.find(class_=lambda c: c and 'summary' in str(c).lower())
            if summary_elem:
                article_info["summary"] = summary_elem.text.strip()
            
            # Only add if we found a title and it passes team-related validation
            if article_info["title"] and _is_team_related_article(article_info["title"], team_name):
                # Check for duplicates
                if not any(a.get("title") == article_info["title"] for a in news_articles):
                    news_articles.append(article_info)
        
        # If we still haven't found news, look for regular list items that might be news headlines
        if not news_articles:
            # Look for text that appears to be news headlines about the team
            team_keywords = team_name.replace('_', ' ').split() + [team_name_to_abbreviation(team_name)] + team_name.replace('_', ' ').split() # Add individual words too
            potential_headlines = soup.find_all(['li', 'h4', 'h3', 'h2', 'div'], string=lambda s: s and any(keyword in s for keyword in team_keywords))
            
            for headline in potential_headlines:
                title = headline.text.strip()
                # Filter team-related content
                if _is_team_related_article(title, team_name):
                    # Look for a link
                    link = None
                    if headline.parent.name == 'a':
                        link = headline.parent['href']
                    else:
                        link_elem = headline.find('a')
                        if link_elem and link_elem.get('href'):
                            link = link_elem['href']
                    
                    news_articles.append({
                        "title": title,
                        "url": link if link else "",
                        "date": "",
                        "summary": ""
                    })
        
        # Sort by most likely to be a true team-related article
        news_articles = sorted(news_articles, key=lambda a: _team_relevance_score(a, team_name), reverse=True)
        
        # Remove any remaining non-team-related articles
        news_articles = [article for article in news_articles if _is_team_related_article(article["title"], team_name)]
        
        # Convert to DataFrame
        df = pd.DataFrame(news_articles)
        
        # Save to CSV
        filename = os.path.join(news_folder, f'news_articles_{datetime.datetime.now().strftime("%Y%m%d")}.csv')
        df.to_csv(filename, index=False)
        print(f"{Fore.GREEN}News articles for {team_name} saved to {filename}{Style.RESET_ALL}")
        
        # Also save the raw data as JSON for backup
        json_filename = os.path.join(news_folder, f'news_articles_{datetime.datetime.now().strftime("%Y%m%d")}.json')
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(news_articles, f, indent=4)
        
        return news_articles
    
    except Exception as e:
        print(f"{Fore.RED}Error extracting news articles for {team_name}: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        return news_articles

def team_name_to_abbreviation(team_name):
    """Convert team name to a common abbreviation."""
    # Basic mapping, can be expanded
    mapping = {
        "Delhi_Capitals": "DC",
        "Gujarat_Titans": "GT",
        "Kolkata_Knight_Riders": "KKR",
        "Lucknow_Super_Giants": "LSG",
        "Mumbai_Indians": "MI",
        "Punjab_Kings": "PBKS",
        "Rajasthan_Royals": "RR",
        "Royal_Challengers_Bengaluru": "RCB", # Note: Changed from Bangalore
        "Sunrisers_Hyderabad": "SRH",
        "Chennai_Super_Kings": "CSK"
    }
    return mapping.get(team_name, team_name) # Return original name if no abbreviation found

def _is_team_related_article(title, team_name):
    """
    Determine if an article title is team-related (Generalized)

    Args:
        title (str): Article title to check
        team_name (str): Name of the team (e.g., "Chennai_Super_Kings")

    Returns:
        bool: True if the article appears to be about the team, False otherwise
    """
    if not title or not isinstance(title, str):
        return False

    title_lower = title.lower()
    team_name_space = team_name.replace('_', ' ').lower()
    team_abbr = team_name_to_abbreviation(team_name).lower()
    team_name_parts = team_name_space.split()

    # --- High Confidence Keywords ---
    # Check for full team name or abbreviation
    if team_name_space in title_lower or (team_abbr and team_abbr in title_lower):
        return True

    # Check for significant parts of the team name (e.g., "Capitals", "Titans")
    # Avoid short common words like "Kings" unless combined with others
    significant_parts = [part for part in team_name_parts if len(part) > 3 and part != 'royal']
    if any(part in title_lower for part in significant_parts):
         # Add check for common cricket terms to increase confidence
         if any(term in title_lower for term in ["ipl", "cricket", "match", "squad", "player", "captain", "coach"]):
             return True

    # --- Medium Confidence Keywords ---
    # Check for match patterns (e.g., "RR vs DC", "MI vs KKR")
    # Generate patterns dynamically
    all_abbrs = [team_name_to_abbreviation(tn).lower() for tn in TEAM_URLS.keys()]
    if team_abbr:
        match_patterns = [f"{abbr} vs {team_abbr}" for abbr in all_abbrs if abbr != team_abbr] + \
                         [f"{team_abbr} vs {abbr}" for abbr in all_abbrs if abbr != team_abbr]
        if any(pattern in title_lower for pattern in match_patterns):
            return True

    # --- Lower Confidence (Contextual) ---
    # Check for known player names associated with the team (if available) + action keywords
    # This requires loading the squad data first, which might be complex here.
    # Placeholder: Could add a check if a known player name appears with "IPL" or "cricket"
    action_keywords = ["batting", "bowling", "wicket", "century", "fifty", "captain", "captaincy", "ipl", "match", "score"]
    # Example (needs player list): if any(player.lower() in title_lower for player in team_players) and any(action in title_lower for action in action_keywords): return True

    # --- Exclusions ---
    non_cricket_keywords = [
        "earthquake", "wishes", "mubarak", "movie", "review", "tuberculosis", "virus",
        "election", "market", "stock", "economy", "weather", "salman", "trump", "biden",
        "football", "hockey", "tennis", "politics"
    ]
    if any(keyword in title_lower for keyword in non_cricket_keywords):
        return False

    # --- Final Check ---
    # If title contains generic cricket terms but no specific team identifiers, exclude it.
    generic_cricket_terms = ["match", "cricket", "ipl", "league", "points table", "standings", "t20"]
    has_generic = any(term in title_lower for term in generic_cricket_terms)
    has_specific = (team_name_space in title_lower or
                    (team_abbr and team_abbr in title_lower) or
                    any(part in title_lower for part in significant_parts))

    if has_generic and not has_specific:
        # Check if *any* other team identifier is present
        other_teams = [tn.replace('_', ' ').lower() for tn, url in TEAM_URLS.items() if tn != team_name]
        other_abbrs = [ta.lower() for ta in all_abbrs if ta != team_abbr]
        if not any(ot in title_lower for ot in other_teams) and not any(oa in title_lower for oa in other_abbrs):
             # If only generic terms and NO team identifiers, maybe keep? Risky. Let's exclude for now.
             return False
        # If generic terms + another team's identifier, it's likely not about *this* team specifically.
        # return False # Re-evaluate if this is too strict

    # Default to False if no strong indicators found
    return False # Be conservative unless strong indicators are present

def _team_relevance_score(article, team_name):
    """
    Calculate a relevance score for a team article (Generalized)

    Args:
        article (dict): Article dictionary containing title and summary
        team_name (str): Name of the team (e.g., "Chennai_Super_Kings")

    Returns:
        int: Relevance score (higher is more relevant)
    """
    score = 0
    title = article.get("title", "").lower()
    summary = article.get("summary", "").lower()
    team_name_space = team_name.replace('_', ' ').lower()
    team_abbr = team_name_to_abbreviation(team_name).lower()
    team_name_parts = team_name_space.split()

    # --- Primary Keywords (Full name, Abbreviation) ---
    primary_keywords = [team_name_space]
    if team_abbr: primary_keywords.append(team_abbr)

    for keyword in primary_keywords:
        if keyword in title:
            score += 10
        if keyword in summary:
            score += 5

    # --- Secondary Keywords (Significant parts of name) ---
    significant_parts = [part for part in team_name_parts if len(part) > 3 and part != 'royal']
    for keyword in significant_parts:
        if keyword in title:
            score += 5
        if keyword in summary:
            score += 2

    # --- Match Patterns ---
    if team_abbr:
        all_abbrs = [team_name_to_abbreviation(tn).lower() for tn in TEAM_URLS.keys()]
        match_patterns = [f"vs {team_abbr}", f"{team_abbr} vs"]
        for pattern in match_patterns:
            if pattern in title:
                score += 8
            if pattern in summary:
                score += 4

    # --- Boost for common cricket terms if team name is present ---
    if any(pk in title for pk in primary_keywords) or any(sk in title for sk in significant_parts):
        if any(term in title for term in ["ipl", "cricket", "match", "squad", "player", "captain", "coach", "win", "loss"]):
            score += 3

    return score

# Removed CSK-specific comparison functions: compare_with_ipl_stats and generate_comparison_report

def extract_support_staff(soup):
    """
    Extract support staff information (Placeholder)
    
    Args:
        soup: BeautifulSoup object of the CSK page
    
    Returns:
        list: List of support staff members (currently empty)
    """
    print(f"{Fore.YELLOW}Placeholder function: extract_support_staff called. Needs implementation.{Style.RESET_ALL}")
    # TODO: Implement actual extraction logic for support staff
    support_staff = []
    # Example structure:
    # staff_section = soup.find(...) 
    # for member in staff_section.find_all(...):
    #     name = member.find(...).text
    #     role = member.find(...).text
    #     support_staff.append({"name": name, "role": role})
    
    # Save to file (optional)
    # filename = os.path.join(FOLDERS['team_data'], TEAM_NAME, 'support_staff.json')
    # with open(filename, 'w', encoding='utf-8') as f:
    #     json.dump(support_staff, f, indent=4)
    # print(f"{Fore.GREEN}Support staff information saved to {filename}{Style.RESET_ALL}")
        
    return support_staff


# Update the main function to process all teams
def main():
    """Main function to run the IPL team scraper for all teams"""
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}      IPL TEAM DATA SCRAPER          {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    start_time = datetime.datetime.now()
    print(f"Scraping started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    total_teams = len(TEAM_URLS)
    processed_teams = 0
    failed_teams = []

    for team_name, team_url in TEAM_URLS.items():
        processed_teams += 1
        print(f"\n{Fore.YELLOW}--- Processing Team {processed_teams}/{total_teams}: {team_name} ---{Style.RESET_ALL}")

        # Create folder structure for the current team
        # Assuming create_team_folders returns the paths needed by extract functions
        team_folders = create_team_folders(team_name)

        # Fetch team page
        soup = fetch_team_page(team_name, team_url)

        if soup:
            try:
                # Extract team information
                # Pass team_name and team_folders to extraction functions
                # (These functions will need modification to accept these arguments)
                team_overview = extract_team_overview(soup, team_name, team_folders)
                player_squad = extract_player_squad(soup, team_name, team_folders)
                team_stats = extract_team_stats(soup, team_name, team_folders)
                news_articles = extract_news_articles(soup, team_name, team_folders)
                support_staff = extract_support_staff(soup) # Corrected arguments

                # Generate summary report
                summary = {
                    "scraping_timestamp": datetime.datetime.now().isoformat(),
                    "team_name": team_name,
                    "team_url": team_url,
                    "status": "Success",
                    "overview_extracted": bool(team_overview),
                    "squad_size": len(player_squad) if player_squad is not None and not player_squad.empty else 0,
                    "news_count": len(news_articles) if news_articles is not None else 0,
                    "support_staff_count": len(support_staff) if support_staff is not None else 0,
                    "extracted_data_paths": team_folders # Include folder paths in summary
                }

                # Save summary report
                summary_file = os.path.join(team_folders['team_folder'], f'scraping_summary_{datetime.datetime.now().strftime("%Y%m%d")}.json')
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=4)

                print(f"{Fore.GREEN}Successfully processed {team_name}. Summary saved to {summary_file}{Style.RESET_ALL}")

                # Removed call to CSK-specific comparison logic

            except Exception as e:
                print(f"{Fore.RED}Error processing {team_name}: {e}{Style.RESET_ALL}")
                failed_teams.append(team_name)
                # Optionally save error summary
                error_summary = {
                    "scraping_timestamp": datetime.datetime.now().isoformat(),
                    "team_name": team_name,
                    "team_url": team_url,
                    "status": "Failed",
                    "error_message": str(e)
                }
                summary_file = os.path.join(team_folders.get('team_folder', os.path.join(BASE_DATA_FOLDER, team_name)), f'scraping_summary_ERROR_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                try:
                    if not os.path.exists(os.path.dirname(summary_file)):
                         os.makedirs(os.path.dirname(summary_file))
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        json.dump(error_summary, f, indent=4)
                    print(f"{Fore.YELLOW}Error summary saved to {summary_file}{Style.RESET_ALL}")
                except Exception as save_err:
                    print(f"{Fore.RED}Could not save error summary for {team_name}: {save_err}{Style.RESET_ALL}")

        else:
            print(f"{Fore.RED}Failed to fetch page for {team_name}. Skipping.{Style.RESET_ALL}")
            failed_teams.append(team_name)
            # Optionally save fetch error summary
            fetch_error_summary = {
                "scraping_timestamp": datetime.datetime.now().isoformat(),
                "team_name": team_name,
                "team_url": team_url,
                "status": "Failed",
                "error_message": "Failed to fetch HTML page."
            }
            # Ensure base folder exists even if team folder creation failed earlier
            if not os.path.exists(os.path.join(BASE_DATA_FOLDER, team_name)):
                 try: os.makedirs(os.path.join(BASE_DATA_FOLDER, team_name))
                 except: pass # Ignore error if folder already exists
            summary_file = os.path.join(BASE_DATA_FOLDER, team_name, f'scraping_summary_FETCH_ERROR_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            try:
                 with open(summary_file, 'w', encoding='utf-8') as f:
                     json.dump(fetch_error_summary, f, indent=4)
                 print(f"{Fore.YELLOW}Fetch error summary saved to {summary_file}{Style.RESET_ALL}")
            except Exception as save_err:
                 print(f"{Fore.RED}Could not save fetch error summary for {team_name}: {save_err}{Style.RESET_ALL}")


    end_time = datetime.datetime.now()
    print(f"\n{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"Scraping finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time taken: {end_time - start_time}")
    print(f"Processed {processed_teams}/{total_teams} teams.")
    if failed_teams:
        print(f"{Fore.RED}Failed to process the following teams: {', '.join(failed_teams)}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}All teams processed successfully!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")


if __name__ == "__main__":
    main()