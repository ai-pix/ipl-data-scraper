import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import re
import pandas as pd
from colorama import init, Fore, Style
import pytz  # Add this import for timezone support

# Initialize colorama for colored console output
init()

# Base URLs and headers (kept for potential future use)
BASE_URL = "https://www.cricbuzz.com/cricket-schedule/upcoming-series/ipl-2024"
MATCH_DETAILS_BASE_URL = "https://www.cricbuzz.com/live-cricket-scorecard/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# IPL Schedule file path
IPL_SCHEDULE_FILE = "Ipl schedule.csv"

# Create folders if they don't exist
FOLDERS = {
    'matches': 'matches',
    'predictions': 'predictions',
    'debug_files': 'debug_files'
}

for folder in FOLDERS.values():
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"{Fore.GREEN}Created folder: {folder}{Style.RESET_ALL}")

# Load team data for predictions
def load_team_data():
    """Load team statistics for prediction"""
    team_data = {}
    team_data_folder = 'team_data'
    
    if not os.path.exists(team_data_folder):
        print(f"{Fore.YELLOW}Team data folder not found. Predictions will be limited.{Style.RESET_ALL}")
        return team_data
    
    # Loop through each team folder
    for team_name in os.listdir(team_data_folder):
        team_path = os.path.join(team_data_folder, team_name)
        
        if os.path.isdir(team_path):
            # Try to load team overview
            overview_path = os.path.join(team_path, 'stats', 'team_overview.json')
            
            if os.path.exists(overview_path):
                try:
                    with open(overview_path, 'r', encoding='utf-8') as f:
                        overview = json.load(f)
                    
                    # Add to team data
                    team_data[team_name] = overview
                except Exception as e:
                    print(f"{Fore.RED}Error loading team data for {team_name}: {e}{Style.RESET_ALL}")
    
    return team_data

def convert_schedule_to_json():
    """Convert the CSV schedule to a clean JSON format for easier parsing"""
    try:
        json_schedule = []
        with open(IPL_SCHEDULE_FILE, 'r') as f:
            # Skip header
            header = f.readline().strip().split(',')
            
            for line in f:
                parts = line.strip().split(',')
                if len(parts) < 9:  # Skip incomplete rows
                    continue
                
                # Create a clean structured match entry
                match = {
                    "match_number": parts[0].strip(),
                    "match_id": parts[1].strip(),
                    "date": parts[2].strip(),
                    "day": parts[3].strip(),
                    "time": parts[4].strip(),
                    "home_team": parts[5].strip(),
                    "away_team": parts[6].strip(),
                    "venue": parts[7].strip()
                }
                
                # Add captains if available
                if len(parts) > 9:
                    match["home_captain"] = parts[8].strip()
                    match["away_captain"] = parts[9].strip() if len(parts) > 10 else ""
                
                json_schedule.append(match)
        
        # Write to JSON file
        json_file = "ipl_schedule.json"
        with open(json_file, 'w') as f:
            json.dump(json_schedule, f, indent=4)
        
        print(f"{Fore.GREEN}Converted schedule to JSON: {json_file}{Style.RESET_ALL}")
        return json_file
    
    except Exception as e:
        print(f"{Fore.RED}Error converting schedule to JSON: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return None

def fetch_today_matches():
    """Fetch today's IPL matches from the schedule"""
    print(f"{Fore.CYAN}Fetching today's IPL matches from schedule...{Style.RESET_ALL}")
    
    # Get current date in Indian Standard Time (IST)
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.datetime.now(ist)
    today_date_format = today.strftime("%d-%b-%y")  # Format: "01-Apr-25"
    
    print(f"{Fore.CYAN}Current date in IST: {today.strftime('%d-%b-%Y (%A)')} {Style.RESET_ALL}")
    print(f"{Fore.CYAN}Looking for matches with date: {today_date_format} {Style.RESET_ALL}")
    
    # First, convert CSV to JSON for reliable parsing
    json_file = convert_schedule_to_json()
    if not json_file:
        print(f"{Fore.RED}Failed to convert schedule to JSON.{Style.RESET_ALL}")
        return []
    
    try:
        # Load the JSON schedule
        with open(json_file, 'r') as f:
            schedule = json.load(f)
        
        print(f"Loaded {len(schedule)} matches from JSON schedule")
        
        # Find matches for today
        today_matches = []
        for match in schedule:
            date_str = match.get('date', '').strip()
            
            # Try different date formats
            match_found = False
            for fmt in ["%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y"]:
                try:
                    match_date = datetime.datetime.strptime(date_str, fmt)
                    if (match_date.day == today.day and 
                        match_date.month == today.month and 
                        match_date.year == today.year):
                        match_found = True
                        break
                except ValueError:
                    continue
            
            if match_found:
                print(f"{Fore.GREEN}Found match for today: {match['home_team']} vs {match['away_team']}{Style.RESET_ALL}")
                
                # Create standardized match entry
                match_entry = {
                    'team1': match['home_team'],
                    'team2': match['away_team'],
                    'time': match['time'],
                    'venue': match['venue'],
                    'match_id': match['match_id']
                }
                
                # Debug output
                print(f"Match details:")
                for k, v in match_entry.items():
                    print(f"  {k}: {v}")
                
                today_matches.append(match_entry)
        
        if today_matches:
            return today_matches
        
        # If no matches today, find upcoming match
        print(f"{Fore.YELLOW}No matches found for today. Looking for upcoming matches.{Style.RESET_ALL}")
        
        next_match = None
        min_days = float('inf')
        
        for match in schedule:
            date_str = match.get('date', '').strip()
            
            # Try to parse date
            match_date = None
            for fmt in ["%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y"]:
                try:
                    match_date = datetime.datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if match_date and match_date > today.replace(tzinfo=None):
                days_diff = (match_date - today.replace(tzinfo=None)).days
                if days_diff < min_days:
                    min_days = days_diff
                    next_match = {
                        'team1': match['home_team'],
                        'team2': match['away_team'],
                        'time': match['time'],
                        'venue': match['venue'],
                        'match_id': match['match_id'],
                        'match_date': match_date.strftime("%d-%b-%Y")
                    }
        
        if next_match:
            print(f"{Fore.YELLOW}Showing upcoming match on {next_match['match_date']}{Style.RESET_ALL}")
            return [next_match]
        
        # No matches found
        print(f"{Fore.RED}No upcoming matches found in the schedule.{Style.RESET_ALL}")
        return []
        
    except Exception as e:
        print(f"{Fore.RED}Error reading schedule: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return []


def convert_team_name(team_name):
    """Convert team name to a standardized format"""
    # Common IPL team names and their variations
    team_mapping = {
        'chennai super kings': 'Chennai_Super_Kings',
        'csk': 'Chennai_Super_Kings',
        'mumbai indians': 'Mumbai_Indians',
        'mi': 'Mumbai_Indians',
        'royal challengers bangalore': 'Royal_Challengers_Bengaluru',
        'royal challengers bengaluru': 'Royal_Challengers_Bengaluru',
        'rcb': 'Royal_Challengers_Bengaluru',
        'kolkata knight riders': 'Kolkata_Knight_Riders',
        'kkr': 'Kolkata_Knight_Riders',
        'delhi capitals': 'Delhi_Capitals',
        'dc': 'Delhi_Capitals',
        'punjab kings': 'Punjab_Kings',
        'pbks': 'Punjab_Kings',
        'sunrisers hyderabad': 'Sunrisers_Hyderabad',
        'srh': 'Sunrisers_Hyderabad',
        'rajasthan royals': 'Rajasthan_Royals',
        'rr': 'Rajasthan_Royals',
        'gujarat titans': 'Gujarat_Titans',
        'gt': 'Gujarat_Titans',
        'lucknow super giants': 'Lucknow_Super_Giants',
        'lsg': 'Lucknow_Super_Giants'
    }
    
    return team_mapping.get(team_name.lower(), team_name)

def get_team_stats(team_name, team_data):
    """Get team statistics from loaded data"""
    standardized_name = convert_team_name(team_name)
    
    # Return team data if found
    return team_data.get(standardized_name, {})

def predict_match_outcome(team1, team2, team_data):
    """Make a simple prediction based on team statistics"""
    team1_stats = get_team_stats(team1, team_data)
    team2_stats = get_team_stats(team2, team_data)
    
    # Check if we have data for both teams
    if not team1_stats or not team2_stats:
        return {
            'prediction': 'Insufficient data for prediction',
            'confidence': 0,
            'reason': 'Missing team statistics'
        }
    
    # Calculate win percentages
    team1_matches = int(team1_stats.get('total_matches', 0) or 0)
    team1_wins = int(team1_stats.get('matches_won', 0) or 0)
    team1_win_percent = (team1_wins / team1_matches * 100) if team1_matches > 0 else 0
    
    team2_matches = int(team2_stats.get('total_matches', 0) or 0)
    team2_wins = int(team2_stats.get('matches_won', 0) or 0)
    team2_win_percent = (team2_wins / team2_matches * 100) if team2_matches > 0 else 0
    
    # Get team titles
    team1_titles = len(team1_stats.get('titles', []))
    team2_titles = len(team2_stats.get('titles', []))
    
    # Calculate a simple prediction score (50% win percentage, 50% titles)
    team1_score = (team1_win_percent * 0.7) + (team1_titles * 10 * 0.3)
    team2_score = (team2_win_percent * 0.7) + (team2_titles * 10 * 0.3)
    
    # Determine winner and confidence
    if team1_score > team2_score:
        winner = team1
        confidence = min(100, max(50, (team1_score - team2_score) * 2))
        reason = f"Higher win percentage ({team1_win_percent:.1f}% vs {team2_win_percent:.1f}%)"
        if team1_titles > team2_titles:
            reason += f" and more IPL titles ({team1_titles} vs {team2_titles})"
    elif team2_score > team1_score:
        winner = team2
        confidence = min(100, max(50, (team2_score - team1_score) * 2))
        reason = f"Higher win percentage ({team2_win_percent:.1f}% vs {team1_win_percent:.1f}%)"
        if team2_titles > team1_titles:
            reason += f" and more IPL titles ({team2_titles} vs {team1_titles})"
    else:
        winner = "Equal chances"
        confidence = 50
        reason = "Teams have similar overall performance"
    
    return {
        'prediction': winner,
        'confidence': confidence,
        'reason': reason,
        'team1_win_percent': team1_win_percent,
        'team2_win_percent': team2_win_percent,
        'team1_titles': team1_titles,
        'team2_titles': team2_titles
    }

def display_match_details(match, team_data):
    """Display match details and prediction"""
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Match: {match['team1']} vs {match['team2']}{Style.RESET_ALL}")
    print(f"Time: {match['time']}")
    print(f"Venue: {match['venue']}")
    
    # Make prediction
    prediction = predict_match_outcome(match['team1'], match['team2'], team_data)
    
    # Determine color based on confidence
    if prediction['confidence'] >= 75:
        confidence_color = Fore.GREEN
    elif prediction['confidence'] >= 50:
        confidence_color = Fore.YELLOW
    else:
        confidence_color = Fore.RED
    
    print(f"\n{Fore.MAGENTA}Prediction:{Style.RESET_ALL}")
    print(f"Likely Winner: {confidence_color}{prediction['prediction']}{Style.RESET_ALL}")
    print(f"Confidence: {confidence_color}{prediction['confidence']:.1f}%{Style.RESET_ALL}")
    print(f"Reason: {prediction['reason']}")
    
    # Display team stats if available
    if 'team1_win_percent' in prediction:
        print(f"\n{Fore.CYAN}Team Stats:{Style.RESET_ALL}")
        print(f"{match['team1']}: Win Rate {prediction['team1_win_percent']:.1f}%, Titles: {prediction['team1_titles']}")        
        print(f"{match['team2']}: Win Rate {prediction['team2_win_percent']:.1f}%, Titles: {prediction['team2_titles']}")
    
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

def save_matches_to_json(matches, filename=None):
    """Save matches to a JSON file"""
    if not matches:
        print(f"{Fore.YELLOW}No matches to save.{Style.RESET_ALL}")
        return None
    
    try:
        # Create output directory if it doesn't exist
        output_dir = "matches"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"{Fore.GREEN}Created output directory: {output_dir}{Style.RESET_ALL}")
        
        # Generate default filename if none provided
        if filename is None:
            today = datetime.datetime.now().strftime('%Y%m%d')
            filename = os.path.join(output_dir, f"todays_matches_{today}.json")
        
        # Create structured JSON object
        json_data = {
            "generated_date": datetime.datetime.now().isoformat(),
            "matches": matches
        }
        
        # Write to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)
            
        print(f"{Fore.GREEN}Matches saved to {filename}{Style.RESET_ALL}")
        return filename
        
    except Exception as e:
        print(f"{Fore.RED}Error saving matches to JSON: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return None

def process_csv_row(row, idx):
    """Process a CSV row to extract match data in a consistent format"""
    try:
        # Print full row data for debugging
        print(f"\n{Fore.CYAN}Full row data for debugging:{Style.RESET_ALL}")
        for key, value in row.items():
            print(f"  {key}: {value}")
            
        # The CSV column structure from inspection is:
        # Match,No,Match Day,Date,Day,Start,Home,Away,Venue,Home Captain,Away Captain
        
        # Extract data directly from the correct columns
        home_team = str(row['Home']).strip()
        away_team = str(row['Away']).strip()
        venue = str(row['Venue']).strip()
        
        # Get time from Start column
        time_val = "7:30 PM"  # Default
        if 'Start' in row and pd.notna(row['Start']):
            time_val = str(row['Start']).strip()
            
        match_id = row.get('No', idx)
        
        # Print extracted values
        print(f"\n{Fore.GREEN}Correctly extracted match data:{Style.RESET_ALL}")
        print(f"  Home team: {home_team}")
        print(f"  Away team: {away_team}")
        print(f"  Time: {time_val}")
        print(f"  Venue: {venue}")
        print(f"  Match ID: {match_id}")
        
        return {
            'team1': home_team,
            'team2': away_team,
            'time': time_val,
            'venue': venue,
            'match_id': match_id
        }
    except Exception as e:
        print(f"{Fore.RED}Error processing row: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return {
            'team1': f"Error: {str(e)}",
            'team2': "Unknown",
            'time': "Unknown",
            'venue': "Unknown",
            'match_id': idx
        }

def main():
    """Main function"""
    # Get current date in Indian Standard Time (IST)
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.datetime.now(ist)
    
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}      TODAY'S IPL MATCHES           {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"Date: {today.strftime('%Y-%m-%d')} (IST)")
    
    # Load team data for predictions
    team_data = load_team_data()
    print(f"Loaded data for {len(team_data)} teams")
    
    # Fetch today's matches
    matches = fetch_today_matches()
    
    if not matches:
        print(f"{Fore.YELLOW}No IPL matches scheduled for today.{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}Found {len(matches)} IPL matches for today:{Style.RESET_ALL}")
    
    # Print raw match data for debugging
    for i, match in enumerate(matches):
        print(f"\nRaw match data #{i+1}:")
        for key, value in match.items():
            print(f"  {key}: {value}")
    
    # Display match details and predictions
    for match in matches:
        display_match_details(match, team_data)
    
    # Save match data
    save_matches_to_json(matches)
    
    print(f"\n{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Analysis complete!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")

if __name__ == "__main__":
    main()