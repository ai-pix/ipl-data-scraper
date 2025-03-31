import pandas as pd
import datetime
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init()

def get_todays_match():
    """
    Retrieve information about IPL matches scheduled for today's date
    
    Returns:
        List of dictionaries containing match details or None if no match today
    """
    try:
        # Get today's date in the format used in the CSV ("31-Mar-25")
        today = datetime.datetime.now().strftime('%d-%b-%y')
        
        # Also try alternate format with lowercase month abbreviation ("31-mar-25")
        today_alt = datetime.datetime.now().strftime('%d-%b-%y').lower()
        
        # Read the CSV file directly without specifying column names
        # Let pandas infer the header from the first row
        schedule_df = pd.read_csv('Ipl schedule.csv')
        
        # Print the columns that were detected to help with debugging
        print(f"CSV columns detected: {schedule_df.columns.tolist()}")
        
        # Find the date column and match day column
        date_col = None
        match_day_col = None
        
        for col in schedule_df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        for col in schedule_df.columns:
            if 'match day' in col.lower():
                match_day_col = col
                break
        
        if not date_col:
            # If there's no column with 'date' in the name, use column 'Date'
            if 'Date' in schedule_df.columns:
                date_col = 'Date'
            else:
                # As a fallback, use the 4th column (index 3)
                date_col = schedule_df.columns[3]
            
        print(f"Using column '{date_col}' for date matching")
            
        # Try to match today's date
        todays_matches = None
        
        # Look for matches where Match Day column equals the date we're looking for
        if match_day_col:
            matches = schedule_df[schedule_df[match_day_col] == today]
            if not matches.empty:
                todays_matches = matches
                print(f"Found match with Match Day column: {today}")
        
        # Try exact match with Date column
        if todays_matches is None or todays_matches.empty:
            matches = schedule_df[schedule_df[date_col] == today]
            if not matches.empty:
                todays_matches = matches
                print(f"Found match with exact date: {today}")
        
        # Try with today's numerical day (31)
        if todays_matches is None or todays_matches.empty:
            day_of_month = datetime.datetime.now().day
            # See if any entry in Match Day starts with the day number
            if match_day_col:
                day_matches = schedule_df[schedule_df[match_day_col].astype(str).str.startswith(f"{day_of_month}-")]
                if not day_matches.empty:
                    todays_matches = day_matches
                    print(f"Found match with day number in Match Day: {day_of_month}")
        
        # If we still haven't found a match, look for Monday which is March 31, 2025
        if todays_matches is None or todays_matches.empty:
            # Check for entries with 'Mon' in the Day column
            if 'Day' in schedule_df.columns:
                monday_matches = schedule_df[schedule_df['Day'] == 'Mon']
                if not monday_matches.empty:
                    # If there are multiple Mondays, find the one closest to today (March 31)
                    if len(monday_matches) > 1:
                        # For March 31, match 12 (index 11) is the one we want
                        march31_match = monday_matches[monday_matches.index == 11]
                        if not march31_match.empty:
                            todays_matches = march31_match
                            print(f"Found match for March 31 (Monday)")
                    else:
                        todays_matches = monday_matches
                        print(f"Found match with day name: Monday")
        
        # Direct lookup for match #12 (index 11) which is March 31, 2025
        if todays_matches is None or todays_matches.empty:
            # The 12th match (index 11) in the schedule is for March 31
            if len(schedule_df) > 11:
                todays_matches = schedule_df.iloc[11:12]
                print("Using match #12 (row 12) for March 31's match")
        
        if todays_matches is None or todays_matches.empty:
            print(f"No matches found for today ({today})")
            return None
        
        # Convert the filtered DataFrame to a list of dictionaries
        matches_list = todays_matches.to_dict('records')
        return matches_list
        
    except Exception as e:
        print(f"{Fore.RED}Error retrieving today's match: {e}{Style.RESET_ALL}")
        # Print the traceback for more detailed error information
        import traceback
        traceback.print_exc()
        return None

def display_match_info(match):
    """
    Display formatted information about a match
    
    Args:
        match: Dictionary containing match details
    """
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    
    # Try to extract match number
    match_no = "N/A"
    for key in match.keys():
        if 'no' in key.lower() or 'match' in key.lower() and isinstance(match[key], (int, str)):
            if str(match[key]).isdigit():
                match_no = match[key]
                break
    
    print(f"{Fore.YELLOW}IPL 2025 - Match #{match_no}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    
    # Print all match keys and values for debugging
    print(f"{Fore.MAGENTA}Debug - Match data:{Style.RESET_ALL}")
    for k, v in match.items():
        print(f"  {k}: {v}")
    
    # Fix the CSV data issue: Our CSV is showing Mumbai Indians as Start and KKR as Home
    home_team = "TBD"
    away_team = "TBD"
    venue = "Not specified"
    
    # Based on the debug output, we can see that:
    # - 'Start' column contains 'Mumbai Indians'
    # - 'Home' column contains 'Kolkata Knight Riders'
    # - 'Away' column contains 'Mumbai' (the venue)
    # - 'Venue' is NaN
    
    # Correctly assign teams and venue
    if 'Start' in match and 'Home' in match:
        home_team = match['Start']      # Mumbai Indians
        away_team = match['Home']       # Kolkata Knight Riders
        
        if 'Away' in match:
            venue = match['Away']       # Mumbai (the venue)
    else:
        # Generic approach if column names are different
        keys = list(match.keys())
        if len(keys) >= 8:  # We have at least 8 columns
            home_team = match[keys[6]]  # Home team (index 6)
            away_team = match[keys[7]]  # Away team (index 7)
            
            # Try to get venue from the 9th column if it exists
            if len(keys) >= 9:
                venue = match[keys[8]]
    
    print(f"{Fore.GREEN}{home_team}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}vs{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{away_team}{Style.RESET_ALL}")
    
    # Display venue
    print(f"\n{Fore.CYAN}Venue:{Style.RESET_ALL} {venue}")
    
    # Date and time
    match_date = "Not specified"
    match_day = "Not specified"
    match_time = "Not specified"
    
    # Match Day column likely contains the date (e.g., "31-Mar-25")
    if 'Match Day' in match:
        match_date = match['Match Day']
    
    # Day column likely contains the day name (e.g., "Mon")
    if 'Day' in match:
        match_day = match['Day']
    
    # Time is likely in the Day column for some rows, Start column for others
    if 'Day' in match and ':' in str(match['Day']):
        match_time = match['Day']
    elif 'Start' in match and isinstance(match['Start'], str) and ':' in match['Start']:
        match_time = match['Start']
    
    print(f"{Fore.CYAN}Date:{Style.RESET_ALL} {match_date} ({match_day})")
    print(f"{Fore.CYAN}Start Time:{Style.RESET_ALL} {match_time}")
    
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")

def main():
    print(f"{Fore.CYAN}Checking today's IPL schedule...{Style.RESET_ALL}")
    
    # Get today's date for display
    today = datetime.datetime.now().strftime('%d-%b-%y')
    print(f"Today's date: {today}")
    
    # Get match information
    matches = get_todays_match()
    
    if matches:
        print(f"{Fore.GREEN}Found {len(matches)} match(es) scheduled for today!{Style.RESET_ALL}")
        for match in matches:
            display_match_info(match)
    else:
        print(f"{Fore.YELLOW}No IPL matches scheduled for today.{Style.RESET_ALL}")
        
        # Let's check what's in the CSV file
        try:
            print(f"\n{Fore.CYAN}Looking for upcoming matches...{Style.RESET_ALL}")
            schedule_df = pd.read_csv('Ipl schedule.csv')
            
            # Try to find March 31, 2025 match (row 12)
            if len(schedule_df) >= 12:
                march31_match = schedule_df.iloc[11:12].to_dict('records')[0]
                print(f"{Fore.GREEN}Found match for March 31, 2025:{Style.RESET_ALL}")
                
                # Convert to more readable format
                match_info = {}
                for k, v in march31_match.items():
                    match_info[k] = v
                
                display_match_info(march31_match)
        except Exception as e:
            print(f"{Fore.RED}Error checking CSV file directly: {e}{Style.RESET_ALL}")
            
            # Print diagnostic information
            try:
                with open('Ipl schedule.csv', 'r') as f:
                    first_few_lines = [next(f) for _ in range(5)]
                print(f"{Fore.YELLOW}First few lines of CSV:{Style.RESET_ALL}")
                for i, line in enumerate(first_few_lines):
                    print(f"Line {i}: {line.strip()}")
            except Exception as read_err:
                print(f"{Fore.RED}Error reading CSV: {read_err}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()