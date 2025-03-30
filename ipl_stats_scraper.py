import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import re
import csv
import os
import json
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init()

# Define folder structure
FOLDERS = {
    'batting_stats': 'batting_stats',
    'bowling_stats': 'bowling_stats',
    'debug_files': 'debug_files',
    'reports': 'reports'
}

def create_folders():
    """Create the necessary folder structure if it doesn't exist"""
    for folder in FOLDERS.values():
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"{Fore.GREEN}Created folder: {folder}{Style.RESET_ALL}")

def extract_stats_from_text(text, stat_type):
    """
    Extract player statistics from text content based on stat type
    
    Args:
        text (str): Text content to extract stats from
        stat_type (str): Type of statistic to extract
    
    Returns:
        pandas.DataFrame: DataFrame containing the extracted stats
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Different extraction patterns based on stat type
    if stat_type == 'most-runs':
        # Pattern for batsmen with runs stats
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+\*?)\s+([\d\.]+)\s+([\d\.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Runs', 'HS', 'Avg', 'SR', '100s', '50s', '4s', '6s']
    elif stat_type == 'most-hundreds':
        # Pattern for players with hundreds
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '100s']
    elif stat_type == 'most-fifties':
        # Pattern for players with fifties
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '50s']
    elif stat_type == 'most-6s':
        # Pattern for players with sixes
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '6s']
    elif stat_type == 'most-4s':
        # Pattern for players with fours
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '4s']
    # Bowling stats patterns
    elif stat_type == 'most-wickets':
        # Pattern for bowlers with wickets
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts']
    elif stat_type == 'most-maidens':
        # Pattern for bowlers with maidens
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Maidens']
    elif stat_type == 'best-bowling-average':
        # Pattern for best bowling average
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d\.]+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts', 'Avg']
    elif stat_type == 'best-bowling-strike-rate':
        # Pattern for best bowling strike rate
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d\.]+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts', 'SR']
    elif stat_type == 'best-economy-rates':
        # Pattern for best economy rates
        pattern = r'(\d+)\s+([A-Za-z\s]+)\s+([A-Za-z\s]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d\.]+)'
        columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Overs', 'Econ']
    else:
        return None
    
    # Find matches
    matches = re.findall(pattern, text)
    
    if not matches:
        return None
    
    # Process matches
    data = []
    for match in matches:
        # Filter out non-player entries (UI elements, headers, etc.)
        player_name = match[1].strip()
        team_name = match[2].strip()
        
        # Skip entries that don't look like player stats
        if (any(keyword in player_name.lower() for keyword in ['batting', 'bowling', 'most', 'runs', 'hundreds', 'fifties', 'sixes', 'fours']) or
            any(keyword in team_name.lower() for keyword in ['batting', 'bowling', 'most', 'runs', 'hundreds', 'fifties', 'sixes', 'fours', 'mat', 'sr'])):
            continue
        
        # For runs: Check if runs is a reasonable number
        if stat_type == 'most-runs' and not (match[5].isdigit() and 10 <= int(match[5]) <= 1000):
            continue
            
        # Create row data
        row = list(match)
        data.append(row)
    
    if not data:
        return None
    
    # Create DataFrame with appropriate number of columns
    df = pd.DataFrame(data, columns=columns[:len(data[0])])
    return df

def manual_cleanup(df, stat_type):
    """
    Manually clean up the DataFrame based on known issues
    
    Args:
        df (pandas.DataFrame): DataFrame to clean
        stat_type (str): Type of statistic
    
    Returns:
        pandas.DataFrame: Cleaned DataFrame
    """
    if df is None:
        return None
    
    # Remove rows where Player contains keywords that indicate it's not a player
    if 'Player' in df.columns:
        df = df[~df['Player'].str.contains('most|batting|bowling|runs|hundreds|fifties|sixes|fours|skip|menu|search', case=False, na=False)]
    
    # Remove rows with zero or very low values for the main stat
    stat_column = None
    if stat_type == 'most-runs':
        stat_column = 'Runs'
    elif stat_type == 'most-hundreds':
        stat_column = '100s'
    elif stat_type == 'most-fifties':
        stat_column = '50s'
    elif stat_type == 'most-6s':
        stat_column = '6s'
    elif stat_type == 'most-4s':
        stat_column = '4s'
    elif stat_type == 'most-wickets':
        stat_column = 'Wkts'
    elif stat_type == 'most-maidens':
        stat_column = 'Maidens'
    
    if stat_column and stat_column in df.columns:
        try:
            df[stat_column] = pd.to_numeric(df[stat_column], errors='coerce')
            # Keep only rows with reasonable values
            if stat_type == 'most-runs':
                df = df[df[stat_column] >= 10]
            else:
                df = df[df[stat_column] > 0]
        except Exception:
            pass
    
    # Reset index after filtering
    df = df.reset_index(drop=True)
    
    # Fix rank numbers
    if 'Rank' in df.columns:
        df['Rank'] = range(1, len(df) + 1)
    
    return df

def scrape_ipl_stats(url, stat_type):
    """
    Scrape IPL statistics from Indian Express website for different stat types
    
    Args:
        url (str): URL of the stats page to scrape
        stat_type (str): Type of statistic being scraped (e.g., 'most-runs', 'most-hundreds')
    
    Returns:
        pandas.DataFrame or None: DataFrame containing the scraped data or None if scraping failed
    """
    print(f"\n{Fore.CYAN}===== Scraping {stat_type} ====={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Fetching data from {url}...{Style.RESET_ALL}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # Send request and get content
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Save HTML for debugging
        debug_filename = os.path.join(FOLDERS['debug_files'], f"page_{stat_type}.html")
        with open(debug_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Saved HTML to {debug_filename}")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get text content
        page_text = soup.get_text()
        
        # Save text for debugging
        text_filename = os.path.join(FOLDERS['debug_files'], f"text_{stat_type}.txt")
        with open(text_filename, "w", encoding="utf-8") as f:
            f.write(page_text)
        
        # Alternative approach for known pages
        if stat_type == 'most-runs':
            # Extract player names and team names from the page text
            print(f"Processing {stat_type} page...")
            df = extract_stats_from_text(page_text, stat_type)
            
            if df is not None and not df.empty:
                print(f"{Fore.GREEN}Extracted {len(df)} player entries for {stat_type}{Style.RESET_ALL}")
                return manual_cleanup(df, stat_type)
        
        elif stat_type in ['most-hundreds', 'most-fifties', 'most-6s', 'most-4s']:
            # For these pages, use our existing CSV files as backup
            print(f"Checking existing data for {stat_type}...")
            
            # First, try to extract from page text
            df = extract_stats_from_text(page_text, stat_type)
            
            if df is not None and not df.empty:
                print(f"{Fore.GREEN}Extracted {len(df)} player entries for {stat_type}{Style.RESET_ALL}")
                df = manual_cleanup(df, stat_type)
                if df is not None and not df.empty:
                    return df
            
            # If that fails, try a more direct approach for each specific type
            print(f"Using specialized extraction for {stat_type}...")
            
            # Define expected columns based on stat type
            if stat_type == 'most-hundreds':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '100s']
            elif stat_type == 'most-fifties':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '50s']
            elif stat_type == 'most-6s':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '6s']
            elif stat_type == 'most-4s':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '4s']
            
            # Look for numeric patterns that might indicate player stats
            # This is a simplified approach focusing on finding players with their stats
            lines = page_text.split('\n')
            
            # Collect player data
            players = []
            teams = []
            matches = []
            innings = []
            values = []
            
            # Manual extraction based on line-by-line analysis
            for i in range(len(lines) - 5):  # Need at least 5 consecutive lines
                line = lines[i].strip()
                
                # Look for player names (skip short lines and numeric lines)
                if (len(line) > 3 and 
                    not line[0].isdigit() and 
                    not any(keyword in line.lower() for keyword in ['batting', 'bowling', 'runs', 'most', 'hundreds', 'fifties', 'sixes'])):
                    
                    # Check next lines for team name and stats
                    next_line = lines[i+1].strip() if i+1 < len(lines) else ""
                    
                    # If next line looks like a team name
                    if (len(next_line) > 3 and 
                        not next_line[0].isdigit() and
                        not any(keyword in next_line.lower() for keyword in ['batting', 'bowling', 'runs', 'most', 'hundreds', 'fifties', 'sixes'])):
                        
                        # Check for numeric values in following lines
                        matches_val = lines[i+2].strip() if i+2 < len(lines) else ""
                        innings_val = lines[i+3].strip() if i+3 < len(lines) else ""
                        stat_val = lines[i+4].strip() if i+4 < len(lines) else ""
                        
                        # If these look like valid numeric values
                        if (matches_val.isdigit() and 
                            innings_val.isdigit() and 
                            stat_val.isdigit()):
                            
                            # Add this as a player entry
                            players.append(line)
                            teams.append(next_line)
                            matches.append(matches_val)
                            innings.append(innings_val)
                            values.append(stat_val)
            
            # If we found players using this approach
            if players:
                print(f"Found {len(players)} players using manual extraction")
                
                # Create DataFrame
                data = {
                    'Rank': list(range(1, len(players) + 1)),
                    'Player': players,
                    'Team': teams,
                    'Mat': matches,
                    'Inns': innings
                }
                
                # Add the specific stat column
                stat_col = '100s' if stat_type == 'most-hundreds' else '50s' if stat_type == 'most-fifties' else '6s'
                data[stat_col] = values
                
                df = pd.DataFrame(data)
                return df
            
            # If all else fails, try to use existing data from IPL batting stats file
            try:
                print("Trying to extract data from existing batting stats file...")
                
                # Check if we have the batting stats file from previous scraping
                batting_stats_file = 'ipl_batting_stats_20250330.csv'
                if os.path.exists(batting_stats_file):
                    batting_df = pd.read_csv(batting_stats_file)
                    
                    # Create a new DataFrame with just the columns we need
                    if stat_type == 'most-hundreds' and '100s' in batting_df.columns:
                        new_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '100s']].copy()
                        new_df = new_df.sort_values(by='100s', ascending=False).reset_index(drop=True)
                        new_df['Rank'] = range(1, len(new_df) + 1)
                        return new_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '100s']]
                    
                    elif stat_type == 'most-fifties' and '50s' in batting_df.columns:
                        new_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '50s']].copy()
                        new_df = new_df.sort_values(by='50s', ascending=False).reset_index(drop=True)
                        new_df['Rank'] = range(1, len(new_df) + 1)
                        return new_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '50s']]
                    
                    elif stat_type == 'most-6s' and '6s' in batting_df.columns:
                        new_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '6s']].copy()
                        new_df = new_df.sort_values(by='6s', ascending=False).reset_index(drop=True)
                        new_df['Rank'] = range(1, len(new_df) + 1)
                        return new_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '6s']]
                        
                    elif stat_type == 'most-4s' and '4s' in batting_df.columns:
                        new_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '4s']].copy()
                        new_df = new_df.sort_values(by='4s', ascending=False).reset_index(drop=True)
                        new_df['Rank'] = range(1, len(new_df) + 1)
                        return new_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '4s']]
            except Exception as e:
                print(f"{Fore.RED}Error extracting from batting stats file: {e}{Style.RESET_ALL}")
        
        # Bowling stats extraction
        elif stat_type in ['most-wickets', 'most-maidens', 'best-bowling-average', 'best-bowling-strike-rate', 'best-economy-rates']:
            print(f"Processing {stat_type} page...")
            df = extract_stats_from_text(page_text, stat_type)
            
            if df is not None and not df.empty:
                print(f"{Fore.GREEN}Extracted {len(df)} player entries for {stat_type}{Style.RESET_ALL}")
                return manual_cleanup(df, stat_type)
                
            # If direct extraction fails, try specialized approach for bowling stats
            print(f"Using specialized extraction for {stat_type}...")
            
            # Define expected columns based on stat type
            if stat_type == 'most-wickets':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts']
                value_column = 'Wkts'
            elif stat_type == 'most-maidens':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Maidens']
                value_column = 'Maidens'
            elif stat_type == 'best-bowling-average':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts', 'Avg']
                value_column = 'Avg'
            elif stat_type == 'best-bowling-strike-rate':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts', 'SR']
                value_column = 'SR'
            elif stat_type == 'best-economy-rates':
                columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Overs', 'Econ']
                value_column = 'Econ'
            
            # Look for numeric patterns that might indicate player stats
            lines = page_text.split('\n')
            
            # Collect player data
            players = []
            teams = []
            matches = []
            innings = []
            values = []  # This will be wickets, maidens, etc.
            extra_values = []  # For stats that have an additional column like Avg, SR, Econ
            
            # Manual extraction based on line-by-line analysis
            for i in range(len(lines) - 6):  # Need up to 6 lines for stats with extra values
                line = lines[i].strip()
                
                # Look for player names (skip short lines and numeric lines)
                if (len(line) > 3 and 
                    not line[0].isdigit() and 
                    not any(keyword in line.lower() for keyword in ['batting', 'bowling', 'most', 'wickets', 'maidens', 'economy', 'average', 'strike'])):
                    
                    # Check next lines for team name and stats
                    next_line = lines[i+1].strip() if i+1 < len(lines) else ""
                    
                    # If next line looks like a team name
                    if (len(next_line) > 3 and 
                        not next_line[0].isdigit() and
                        not any(keyword in next_line.lower() for keyword in ['batting', 'bowling', 'most', 'wickets', 'maidens', 'economy', 'average', 'strike'])):
                        
                        # Check for numeric values in following lines
                        matches_val = lines[i+2].strip() if i+2 < len(lines) else ""
                        innings_val = lines[i+3].strip() if i+3 < len(lines) else ""
                        stat_val = lines[i+4].strip() if i+4 < len(lines) else ""
                        extra_val = lines[i+5].strip() if i+5 < len(lines) and value_column in ['Avg', 'SR', 'Econ'] else ""
                        
                        # If these look like valid numeric values
                        has_valid_values = False
                        
                        if value_column in ['Wkts', 'Maidens']:
                            # For wickets and maidens, just need the first 5 values
                            has_valid_values = (matches_val.isdigit() and 
                                               innings_val.isdigit() and 
                                               stat_val.isdigit())
                        else:
                            # For stats with an extra value (Avg, SR, Econ)
                            has_valid_values = (matches_val.isdigit() and 
                                               innings_val.isdigit() and 
                                               stat_val.isdigit() and
                                               re.match(r'^[\d\.]+$', extra_val))
                        
                        if has_valid_values:
                            # Add this as a player entry
                            players.append(line)
                            teams.append(next_line)
                            matches.append(matches_val)
                            innings.append(innings_val)
                            values.append(stat_val)
                            if value_column in ['Avg', 'SR', 'Econ']:
                                extra_values.append(extra_val)
            
            # If we found players using this approach
            if players:
                print(f"Found {len(players)} players using manual extraction")
                
                # Create DataFrame
                data = {
                    'Rank': list(range(1, len(players) + 1)),
                    'Player': players,
                    'Team': teams,
                    'Mat': matches,
                    'Inns': innings
                }
                
                # Add the specific stat column
                if value_column == 'Wkts':
                    data['Wkts'] = values
                elif value_column == 'Maidens':
                    data['Maidens'] = values
                elif value_column == 'Avg':
                    data['Wkts'] = values
                    data['Avg'] = extra_values
                elif value_column == 'SR':
                    data['Wkts'] = values
                    data['SR'] = extra_values
                elif value_column == 'Econ':
                    data['Overs'] = values
                    data['Econ'] = extra_values
                
                df = pd.DataFrame(data)
                return df
        
        # If all extraction methods fail, create a template CSV as fallback
        today = datetime.datetime.now().strftime('%Y%m%d')
        folder = FOLDERS['batting_stats'] if stat_type in ['most-runs', 'most-hundreds', 'most-fifties', 'most-6s', 'most-4s'] else FOLDERS['bowling_stats']
        manual_csv_path = os.path.join(folder, f'ipl_{stat_type}_manual_{today}.csv')
        
        # Define columns based on stat type
        if stat_type == 'most-runs':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Runs', 'HS', 'Avg', 'SR', '100s', '50s', '4s', '6s']
        elif stat_type == 'most-hundreds':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '100s']
        elif stat_type == 'most-fifties':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '50s']
        elif stat_type == 'most-6s':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '6s']
        elif stat_type == 'most-4s':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', '4s']
        elif stat_type == 'most-wickets':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts']
        elif stat_type == 'most-maidens':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Maidens']
        elif stat_type == 'best-bowling-average':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts', 'Avg']
        elif stat_type == 'best-bowling-strike-rate':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Wkts', 'SR']
        elif stat_type == 'best-economy-rates':
            columns = ['Rank', 'Player', 'Team', 'Mat', 'Inns', 'Overs', 'Econ']
        
        with open(manual_csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)
            writer.writerow([1, f'Extract from {debug_filename}', '', '0', '0', '0'])
        
        print(f"{Fore.YELLOW}Created a template CSV file at {manual_csv_path}{Style.RESET_ALL}")
        print(f"Please examine {debug_filename} and manually fill in the data")
        
        return None
        
    except Exception as e:
        print(f"{Fore.RED}Error scraping data: {e}{Style.RESET_ALL}")
        return None

def clean_player_team_data(df):
    """Clean up Player and Team columns to fix any formatting issues"""
    if df is None:
        return None
    
    # Check if Player column contains newlines
    if 'Player' in df.columns:
        for idx, row in df.iterrows():
            player = str(row['Player'])
            if '\n' in player:
                parts = player.split('\n')
                if len(parts) == 2 and 'Team' in df.columns:
                    df.at[idx, 'Player'] = parts[0].strip()
                    df.at[idx, 'Team'] = parts[1].strip()
    
    return df

def save_to_csv(df, stat_type, filename=None):
    """
    Save the DataFrame to a CSV file
    
    Args:
        df (pandas.DataFrame): DataFrame to save
        stat_type (str): Type of statistic being saved
        filename (str, optional): Filename to save to. If None, a default name will be generated.
    """
    if df is None:
        print(f"{Fore.RED}No data to save.{Style.RESET_ALL}")
        return None
    
    # Clean data before saving
    df = clean_player_team_data(df)
    
    # Determine folder based on stat type
    folder = FOLDERS['batting_stats'] if stat_type in ['most-runs', 'most-hundreds', 'most-fifties', 'most-6s', 'most-4s'] else FOLDERS['bowling_stats']
    
    if filename is None:
        # Generate a filename with the current date
        today = datetime.datetime.now().strftime('%Y%m%d')
        filename = os.path.join(folder, f'ipl_{stat_type}_{today}.csv')
    
    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"{Fore.GREEN}Data saved to {filename}{Style.RESET_ALL}")
    
    # Display a preview of the data
    print(f"\n{Fore.CYAN}Preview of the data:{Style.RESET_ALL}")
    print(df.head())
    
    return filename

def generate_summary_report(results):
    """
    Generate a summary report of all the scraped data
    
    Args:
        results (dict): Dictionary containing scraping results
    """
    print(f"\n{Fore.CYAN}===== Generating Summary Report ====={Style.RESET_ALL}")
    
    summary = {
        "scraping_date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "stats_scraped": len(results),
        "successful_scrapes": sum(1 for v in results.values() if v['success']),
        "failed_scrapes": sum(1 for v in results.values() if not v['success']),
        "batting_stats": {k: v for k, v in results.items() if k in ['most-runs', 'most-hundreds', 'most-fifties', 'most-6s', 'most-4s']},
        "bowling_stats": {k: v for k, v in results.items() if k in ['most-wickets', 'most-maidens', 'best-bowling-average', 'best-bowling-strike-rate', 'best-economy-rates']}
    }
    
    # Generate top players lists
    top_players = {}
    
    # Find top run scorer
    if 'most-runs' in results and results['most-runs']['success'] and results['most-runs']['file']:
        try:
            df = pd.read_csv(results['most-runs']['file'])
            if not df.empty:
                top_player = df.iloc[0]
                top_players['top_run_scorer'] = {
                    'name': top_player['Player'],
                    'team': top_player['Team'],
                    'runs': int(top_player['Runs']) if 'Runs' in df.columns else 'N/A'
                }
        except Exception as e:
            print(f"{Fore.RED}Error getting top run scorer: {e}{Style.RESET_ALL}")
    
    # Find top wicket taker
    if 'most-wickets' in results and results['most-wickets']['success'] and results['most-wickets']['file']:
        try:
            df = pd.read_csv(results['most-wickets']['file'])
            if not df.empty:
                top_player = df.iloc[0]
                top_players['top_wicket_taker'] = {
                    'name': top_player['Player'],
                    'team': top_player['Team'],
                    'wickets': int(top_player['Wkts']) if 'Wkts' in df.columns else 'N/A'
                }
        except Exception as e:
            print(f"{Fore.RED}Error getting top wicket taker: {e}{Style.RESET_ALL}")
    
    summary['top_players'] = top_players
    
    # Save summary to JSON file
    today = datetime.datetime.now().strftime('%Y%m%d')
    summary_file = os.path.join(FOLDERS['reports'], f'ipl_stats_summary_{today}.json')
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=4)
    
    # Create a more readable HTML report
    html_report = os.path.join(FOLDERS['reports'], f'ipl_stats_report_{today}.html')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IPL Stats Report - {today}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #1a5276; }}
            .section {{ margin-bottom: 20px; }}
            .success {{ color: green; }}
            .failure {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>IPL Statistics Report</h1>
        <p>Generated on: {summary['scraping_date']}</p>
        
        <div class="section">
            <h2>Summary</h2>
            <p>Total statistics scraped: {summary['stats_scraped']}</p>
            <p>Successful scrapes: <span class="success">{summary['successful_scrapes']}</span></p>
            <p>Failed scrapes: <span class="failure">{summary['failed_scrapes']}</span></p>
        </div>
        
        <div class="section">
            <h2>Batting Statistics</h2>
            <table>
                <tr>
                    <th>Statistic</th>
                    <th>Status</th>
                    <th>File</th>
                </tr>
    """
    
    # Add batting stats to HTML
    for stat, result in summary['batting_stats'].items():
        status_class = "success" if result['success'] else "failure"
        status_text = "Success" if result['success'] else "Failed"
        html_content += f"""
                <tr>
                    <td>{stat}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{os.path.basename(result['file']) if result['file'] else 'N/A'}</td>
                </tr>
        """
    
    html_content += """
            </table>
        </div>
        
        <div class="section">
            <h2>Bowling Statistics</h2>
            <table>
                <tr>
                    <th>Statistic</th>
                    <th>Status</th>
                    <th>File</th>
                </tr>
    """
    
    # Add bowling stats to HTML
    for stat, result in summary['bowling_stats'].items():
        status_class = "success" if result['success'] else "failure"
        status_text = "Success" if result['success'] else "Failed"
        html_content += f"""
                <tr>
                    <td>{stat}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{os.path.basename(result['file']) if result['file'] else 'N/A'}</td>
                </tr>
        """
    
    html_content += """
            </table>
        </div>
        
        <div class="section">
            <h2>Top Players</h2>
    """
    
    # Add top players to HTML
    if 'top_run_scorer' in top_players:
        player = top_players['top_run_scorer']
        html_content += f"""
            <h3>Top Run Scorer</h3>
            <p>Player: {player['name']}</p>
            <p>Team: {player['team']}</p>
            <p>Runs: {player['runs']}</p>
        """
    
    if 'top_wicket_taker' in top_players:
        player = top_players['top_wicket_taker']
        html_content += f"""
            <h3>Top Wicket Taker</h3>
            <p>Player: {player['name']}</p>
            <p>Team: {player['team']}</p>
            <p>Wickets: {player['wickets']}</p>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(html_report, 'w') as f:
        f.write(html_content)
    
    print(f"{Fore.GREEN}Summary report saved to {summary_file}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}HTML report saved to {html_report}{Style.RESET_ALL}")
    
    return summary_file, html_report

def scrape_all_stats():
    """Scrape stats from multiple IPL stats pages"""
    stats_urls = {
        # Batting stats
        'most-runs': 'https://indianexpress.com/section/sports/ipl/stats/most-runs/',
        'most-hundreds': 'https://indianexpress.com/section/sports/ipl/stats/most-hundreds/',
        'most-fifties': 'https://indianexpress.com/section/sports/ipl/stats/most-fifties/',
        'most-6s': 'https://indianexpress.com/section/sports/ipl/stats/most-6s/',
        'most-4s': 'https://indianexpress.com/section/sports/ipl/stats/most-4s/',
        
        # Bowling stats
        'most-wickets': 'https://indianexpress.com/section/sports/ipl/stats/most-wickets/',
        'most-maidens': 'https://indianexpress.com/section/sports/ipl/stats/most-maidens/',
        'best-bowling-average': 'https://indianexpress.com/section/sports/ipl/stats/best-bowling-average/',
        'best-bowling-strike-rate': 'https://indianexpress.com/section/sports/ipl/stats/best-bowling-strike-rate/',
        'best-economy-rates': 'https://indianexpress.com/section/sports/ipl/stats/best-economy-rates/'
    }
    
    results = {}
    
    for stat_type, url in stats_urls.items():
        print(f"\n{Fore.CYAN}===== Scraping {stat_type} ====={Style.RESET_ALL}")
        df = scrape_ipl_stats(url, stat_type)
        saved_file = None
        if df is not None:
            saved_file = save_to_csv(df, stat_type)
            results[stat_type] = {'success': True, 'file': saved_file}
        else:
            results[stat_type] = {'success': False, 'file': None}
    
    # Generate a summary report
    generate_summary_report(results)
    
    # Summary of results
    print(f"\n{Fore.CYAN}===== Scraping Summary ====={Style.RESET_ALL}")
    for stat_type, result in results.items():
        status = f"{Fore.GREEN}Success{Style.RESET_ALL}" if result['success'] else f"{Fore.RED}Failed{Style.RESET_ALL}"
        print(f"{stat_type}: {status}")
    
    return results

def extract_data_from_existing_csv():
    """
    Extract data from existing CSV files and create derived stat files
    
    This function can be used if direct scraping fails
    """
    print(f"\n{Fore.CYAN}===== Extracting from Existing CSV ====={Style.RESET_ALL}")
    
    try:
        # Check if we have the main batting stats file
        batting_stats_file = os.path.join(FOLDERS['batting_stats'], 'ipl_most-runs_20250330.csv')
        if not os.path.exists(batting_stats_file):
            print(f"{Fore.RED}Batting stats file {batting_stats_file} not found.{Style.RESET_ALL}")
            return False
        
        # Read the batting stats file
        batting_df = pd.read_csv(batting_stats_file)
        
        # Create derived stat files
        
        # Most hundreds
        if '100s' in batting_df.columns:
            hundreds_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '100s']].copy()
            hundreds_df = hundreds_df.sort_values(by='100s', ascending=False).reset_index(drop=True)
            hundreds_df['Rank'] = range(1, len(hundreds_df) + 1)
            save_to_csv(hundreds_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '100s']], 'most-hundreds')
        
        # Most fifties
        if '50s' in batting_df.columns:
            fifties_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '50s']].copy()
            fifties_df = fifties_df.sort_values(by='50s', ascending=False).reset_index(drop=True)
            fifties_df['Rank'] = range(1, len(fifties_df) + 1)
            save_to_csv(fifties_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '50s']], 'most-fifties')
        
        # Most sixes
        if '6s' in batting_df.columns:
            sixes_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '6s']].copy()
            sixes_df = sixes_df.sort_values(by='6s', ascending=False).reset_index(drop=True)
            sixes_df['Rank'] = range(1, len(sixes_df) + 1)
            save_to_csv(sixes_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '6s']], 'most-6s')
        
        # Most fours
        if '4s' in batting_df.columns:
            fours_df = batting_df[['Player', 'Team', 'Mat', 'Inns', '4s']].copy()
            fours_df = fours_df.sort_values(by='4s', ascending=False).reset_index(drop=True)
            fours_df['Rank'] = range(1, len(fours_df) + 1)
            save_to_csv(fours_df[['Rank', 'Player', 'Team', 'Mat', 'Inns', '4s']], 'most-4s')
        
        return True
    
    except Exception as e:
        print(f"{Fore.RED}Error extracting from existing CSV: {e}{Style.RESET_ALL}")
        return False

def move_existing_files():
    """Move existing CSV and HTML files to their appropriate folders"""
    print(f"\n{Fore.CYAN}===== Organizing Existing Files ====={Style.RESET_ALL}")
    
    # Move CSV files
    for filename in os.listdir('.'):
        if filename.endswith('.csv'):
            if any(stat in filename for stat in ['most-runs', 'most-hundreds', 'most-fifties', 'most-6s', 'most-4s']):
                dest_folder = FOLDERS['batting_stats']
            elif any(stat in filename for stat in ['most-wickets', 'most-maidens', 'best-bowling-average', 'best-bowling-strike-rate', 'best-economy-rates']):
                dest_folder = FOLDERS['bowling_stats']
            else:
                continue
                
            dest_path = os.path.join(dest_folder, filename)
            try:
                os.rename(filename, dest_path)
                print(f"Moved {filename} to {dest_folder}/")
            except Exception as e:
                print(f"{Fore.RED}Error moving {filename}: {e}{Style.RESET_ALL}")
    
    # Move HTML files
    for filename in os.listdir('.'):
        if filename.endswith('.html') and filename.startswith('page_'):
            dest_path = os.path.join(FOLDERS['debug_files'], filename)
            try:
                os.rename(filename, dest_path)
                print(f"Moved {filename} to {FOLDERS['debug_files']}/")
            except Exception as e:
                print(f"{Fore.RED}Error moving {filename}: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}      IPL STATISTICS SCRAPER         {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create folder structure
    create_folders()
    
    # Move any existing files to the appropriate folders
    move_existing_files()
    
    # Scrape all stats pages
    print(f"\n{Fore.CYAN}Starting to scrape all IPL stats pages...{Style.RESET_ALL}")
    results = scrape_all_stats()
    
    # If some stats failed, try extracting from existing data
    if not all(result['success'] for result in results.values()):
        print(f"\n{Fore.YELLOW}Some statistics failed to scrape. Trying to extract from existing data...{Style.RESET_ALL}")
        extract_data_from_existing_csv()
    
    print(f"\n{Fore.GREEN}All scraping tasks completed.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")