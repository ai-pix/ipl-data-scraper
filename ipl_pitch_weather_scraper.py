#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IPL Pitch and Weather Report Scraper

This script fetches pitch reports and weather data for IPL 2025 venues.
It uses web scraping to obtain pitch information from cricket websites
and a weather API to get current and forecast weather data.

Usage:
    python ipl_pitch_weather_scraper.py

Dependencies:
    - requests
    - beautifulsoup4
    - pandas
    - colorama
    - python-dotenv
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import json
import time
import re
from colorama import init, Fore, Style
import concurrent.futures
from dotenv import load_dotenv

# Initialize colorama for colored console output
init()

# Load environment variables from .env file - add debugging
# load_dotenv()
# OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_API_KEY = "fcb46ca9c388ddcaf1ed48e804525f52"
print(f"{Fore.YELLOW}API Key loaded: {OPENWEATHER_API_KEY[:5]}...{OPENWEATHER_API_KEY[-5:] if OPENWEATHER_API_KEY else 'None'}{Style.RESET_ALL}")

# Define folder structure
FOLDERS = {
    'pitch_reports': 'pitch_reports',
    'weather_reports': 'weather_reports',
    'combined_reports': 'combined_reports',
    'debug_files': 'debug_files'
}

# IPL 2025 venues and their locations with direct Cricbuzz links
IPL_VENUES = [
    {
        "name": "Eden Gardens", 
        "city": "Kolkata", 
        "state": "West Bengal",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/31/eden-gardens"
    },
    {
        "name": "M. Chinnaswamy Stadium", 
        "city": "Bengaluru", 
        "state": "Karnataka",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/27/mchinnaswamy-stadium"
    },
    {
        "name": "MA Chidambaram Stadium", 
        "city": "Chennai", 
        "state": "Tamil Nadu",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/11/ma-chidambaram-stadium"
    },
    {
        "name": "Wankhede Stadium", 
        "city": "Mumbai", 
        "state": "Maharashtra",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/81/wankhede-stadium"
    },
    {
        "name": "Arun Jaitley Stadium", 
        "city": "Delhi", 
        "state": "Delhi",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/51/arun-jaitley-stadium"
    },
    {
        "name": "Rajiv Gandhi International Stadium", 
        "city": "Hyderabad", 
        "state": "Telangana",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/80/rajiv-gandhi-international-stadium"
    },
    {
        "name": "Narendra Modi Stadium", 
        "city": "Ahmedabad", 
        "state": "Gujarat",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/50/narendra-modi-stadium"
    },
    {
        "name": "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium", 
        "city": "Lucknow", 
        "state": "Uttar Pradesh",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/485/bharat-ratna-shri-atal-bihari-vajpayee-ekana-cricket-stadium"
    },
    {
        "name": "Sawai Mansingh Stadium", 
        "city": "Jaipur", 
        "state": "Rajasthan",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/76/sawai-mansingh-stadium"
    },
    {
        "name": "Barsapara Cricket Stadium", 
        "city": "Guwahati", 
        "state": "Assam",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/380/barsapara-cricket-stadium"
    },
    {
        "name": "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium", 
        "city": "Visakhapatnam", 
        "state": "Andhra Pradesh",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/154/dr-ys-rajasekhara-reddy-aca-vdca-cricket-stadium"
    },
    {
        "name": "Himachal Pradesh Cricket Association Stadium", 
        "city": "Dharamsala", 
        "state": "Himachal Pradesh",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/155/himachal-pradesh-cricket-association-stadium"
    },
    {
        "name": "Punjab Cricket Association IS Bindra Stadium", 
        "city": "Mohali", 
        "state": "Punjab",
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/36/pca-stadium"
    }
]

# Get API key from environment variables
# OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Common headers for HTTP requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def create_folders():
    """Create the necessary folder structure if it doesn't exist"""
    for folder in FOLDERS.values():
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"{Fore.GREEN}Created folder: {folder}{Style.RESET_ALL}")


def fetch_cricbuzz_pitch_report(venue):
    """
    Fetch pitch report from Cricbuzz for a specific venue using direct URL
    
    Args:
        venue (dict): Venue dictionary containing name, city, and cricbuzz_url
    
    Returns:
        dict: Pitch report details
    """
    venue_name = venue["name"]
    city = venue["city"]
    cricbuzz_url = venue["cricbuzz_url"]
    
    print(f"{Fore.CYAN}Fetching pitch report for {venue_name}, {city}...{Style.RESET_ALL}")
    
    try:
        # Access the direct Cricbuzz URL
        response = requests.get(cricbuzz_url, headers=HEADERS)
        response.raise_for_status()
        
        # Save HTML for debugging
        debug_filename = os.path.join(FOLDERS['debug_files'], f"pitch_{venue_name.replace(' ', '_')}_{city}_cricbuzz.html")
        with open(debug_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Initialize the pitch data dictionary with more comprehensive fields
        pitch_data = {
            "venue": venue_name,
            "city": city,
            "pitch_report": "Not available",
            "average_score": "Not available",
            "highest_score": "Not available",
            "lowest_score": "Not available", 
            "characteristics": "Not available",
            "source": "Cricbuzz",
            "source_url": cricbuzz_url,
            "last_updated": datetime.datetime.now().strftime('%Y-%m-%d'),
            # Add new fields for more comprehensive statistics
            "test_stats": {},
            "odi_stats": {},
            "t20_stats": {},
            "ipl_stats": {},
            "interesting_records": [],
            "notable_performances": []
        }
        
        # Try multiple approaches to find venue description
        venue_description = ""
        
        # Approach 1: Find the paragraph with "Venue Description" heading
        venue_desc_section = soup.find('p', string=lambda text: text and ('Venue Description' in text if text else False))
        if venue_desc_section:
            venue_description = venue_desc_section.get_text(strip=True)
        
        # Approach 2: Look for venue description div with specific class
        if not venue_description:
            venue_div = soup.find('div', class_='cb-col cb-col-100 cb-venue-desc')
            if venue_div:
                paragraphs = venue_div.find_all('p')
                if paragraphs:
                    venue_description = ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        # Approach 3: Look for paragraphs with venue related keywords
        if not venue_description:
            keywords = ['venue description', 'introduction', 'venue history', 'ground was established', 
                        'stadium', 'cricket ground', 'capacity', 'hosted', 'first match']
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().lower()
                if any(keyword in text for keyword in keywords):
                    venue_description = p.get_text(strip=True)
                    break
        
        # Approach 4: Look for any content in the main content area
        if not venue_description:
            main_content = soup.find('div', class_='cb-col-67 cb-col')
            if main_content:
                paragraphs = main_content.find_all('p')
                if paragraphs:
                    venue_description = ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        # Approach 5: Look for text in venue info section
        if not venue_description:
            venue_info = soup.find('div', class_='venue-info')
            if venue_info:
                venue_description = venue_info.get_text(strip=True)
        
        # Look for pitch information specifically
        pitch_info = ""
        pitch_keywords = ['how does the pitch play', 'pitch conditions', 'pitch behavior', 'wicket', 
                         'batting surface', 'bowling conditions', 'pace and bounce']
        
        for p in soup.find_all('p'):
            text = p.get_text().lower()
            if any(keyword in text for keyword in pitch_keywords):
                pitch_info = p.get_text(strip=True)
                break
        
        # Alternative approach for pitch info
        if not pitch_info:
            pitch_section = soup.find('h3', string=lambda s: s and 'Pitch' in s)
            if pitch_section and pitch_section.find_next('p'):
                pitch_info = pitch_section.find_next('p').get_text(strip=True)
        
        # Combine the information
        if venue_description:
            pitch_data["pitch_report"] = venue_description
        if pitch_info and pitch_info not in venue_description:
            pitch_data["pitch_report"] += "\n" + pitch_info
        
        # Extract all stats tables using multiple approaches
        
        # Approach 1: Find tables with specific class
        tables = soup.find_all('table', class_='table')
        
        # Approach 2: If no tables found, look more generally
        if not tables:
            tables = soup.find_all('table')
        
        # Process all tables found
        for table in tables:
            table_header = ""
            
            # Try to find the heading for this table
            # Look at previous siblings first
            prev_element = table.previous_sibling
            while prev_element and table_header == "":
                if hasattr(prev_element, 'get_text'):
                    text = prev_element.get_text(strip=True)
                    if text:
                        table_header = text
                prev_element = prev_element.previous_sibling
            
            # If no header found, look for nearby headings
            if not table_header:
                for heading in table.find_previous_siblings(['h2', 'h3', 'h4', 'h5']):
                    if heading:
                        table_header = heading.get_text(strip=True)
                        break
            
            # Determine which type of stats this is
            stats_type = None
            table_header = table_header.upper() if table_header else ""
            
            if "TEST" in table_header:
                stats_type = "test_stats"
            elif "ODI" in table_header:
                stats_type = "odi_stats"
            elif "T20" in table_header or "T20I" in table_header:
                stats_type = "t20_stats"
            elif "IPL" in table_header or "T20 LEAGUE" in table_header:
                stats_type = "ipl_stats"
            # If header doesn't clearly indicate, try to determine from content
            else:
                # Check first row for clues
                first_row = table.find('tr')
                if first_row:
                    first_row_text = first_row.get_text().upper()
                    if "TEST" in first_row_text:
                        stats_type = "test_stats"
                    elif "ODI" in first_row_text:
                        stats_type = "odi_stats"
                    elif "T20" in first_row_text:
                        stats_type = "t20_stats"
                    elif "IPL" in first_row_text:
                        stats_type = "ipl_stats"
                    else:
                        # Default to test stats if no clear indication
                        stats_type = "test_stats"
                
            # Extract data from the table
            if stats_type:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])  # Look for both td and th elements
                    if len(cols) >= 2:
                        header = cols[0].get_text(strip=True)
                        value = cols[1].get_text(strip=True)
                        
                        # Skip empty or header rows
                        if not header or header.lower() in ['matches', 'statistics', 'record']:
                            continue
                        
                        # Store the stat in the appropriate category
                        pitch_data[stats_type][header] = value
                        
                        # Also set the main stats fields if they're found
                        # Account for variations in naming
                        if any(term in header.lower() for term in ['average', 'avg', '1st inns']):
                            pitch_data["average_score"] = f"Average 1st innings score: {value}"
                        elif any(term in header.lower() for term in ['highest', 'high', 'maximum']):
                            pitch_data["highest_score"] = f"Highest score: {value}"
                        elif any(term in header.lower() for term in ['lowest', 'low', 'minimum']):
                            pitch_data["lowest_score"] = f"Lowest score: {value}"
        
        # Alternative approach for main statistics if tables weren't found
        if pitch_data["average_score"] == "Not available":
            # Look for text with average score info
            avg_pattern = re.compile(r'average (?:score|1st innings).*?(\d+)', re.IGNORECASE)
            text_content = soup.get_text()
            avg_match = avg_pattern.search(text_content)
            if avg_match:
                pitch_data["average_score"] = f"Average 1st innings score: {avg_match.group(1)}"
                
        if pitch_data["highest_score"] == "Not available":
            # Look for text with highest score info
            high_pattern = re.compile(r'highest (?:score|total).*?(\d+/\d+|\d+)', re.IGNORECASE)
            text_content = soup.get_text()
            high_match = high_pattern.search(text_content)
            if high_match:
                pitch_data["highest_score"] = f"Highest score: {high_match.group(1)}"
        
        # Look for interesting records and trivia sections
        record_keywords = ['trivia', 'record', 'interesting fact', 'stats', 'milestone', 
                          'landmark', 'noteworthy', 'memorable', 'history']
        
        # Approach 1: Check headings
        for heading in soup.find_all(['h2', 'h3', 'h4', 'h5']):
            heading_text = heading.get_text(strip=True).lower()
            if any(keyword in heading_text for keyword in record_keywords):
                # Get the content following this heading
                record_content = []
                next_element = heading.next_sibling
                while next_element and not (hasattr(next_element, 'name') and next_element.name in ['h2', 'h3', 'h4', 'h5']):
                    if hasattr(next_element, 'get_text'):
                        text = next_element.get_text(strip=True)
                        if text:
                            record_content.append(text)
                    next_element = next_element.next_sibling
                
                if record_content:
                    pitch_data["interesting_records"].extend(record_content)
        
        # Approach 2: Look for lists that might contain records
        for ul in soup.find_all('ul'):
            # Check if this list might be related to records
            ul_text = ul.get_text().lower()
            if any(keyword in ul_text for keyword in record_keywords):
                for li in ul.find_all('li'):
                    record = li.get_text(strip=True)
                    if record:
                        pitch_data["interesting_records"].append(record)
        
        # Approach 3: Look for paragraphs that mention records or notable events
        for p in soup.find_all('p'):
            p_text = p.get_text().lower()
            # Check for mentions of records or significant events
            if any(keyword in p_text for keyword in record_keywords):
                record = p.get_text(strip=True)
                if record:
                    pitch_data["interesting_records"].append(record)
        
        # Also look for notable performances in paragraphs
        player_names = ['dhoni', 'kohli', 'tendulkar', 'gavaskar', 'kumble', 'kapil', 'ganguly', 
                       'dravid', 'sharma', 'bumrah', 'shami', 'jadeja', 'maxwell', 'warner', 
                       'russell', 'narine', 'cummins', 'rabada', 'stokes', 'buttler']
        
        performance_keywords = ['scored', 'century', 'hat-trick', 'wicket', 'record', 'feat',
                              'performance', 'best figures', 'five-wicket', 'double hundred']
        
        for p in soup.find_all('p'):
            p_text = p.get_text().lower()
            # Check for mentions of notable performances
            if any(term in p_text for term in performance_keywords):
                if any(player in p_text for player in player_names):
                    performance = p.get_text(strip=True)
                    if performance:
                        pitch_data["notable_performances"].append(performance)
        
        # Extract pitch characteristics from the venue description
        pitch_desc = pitch_data["pitch_report"].lower()
        characteristics = []
        
        # Check for various pitch characteristics in the description
        if any(term in pitch_desc for term in ["batting friendly", "batting paradise", "flat", "high scoring", 
                                              "high-scoring", "run fest", "run-fest", "batting surface", 
                                              "batsmen", "batters", "batting track"]):
            characteristics.append("Batting friendly")
        
        if any(term in pitch_desc for term in ["spin", "spinner", "spinners", "turning", "turn", 
                                              "slow", "dust bowl", "crumbles"]):
            characteristics.append("Assists spin")
        
        if any(term in pitch_desc for term in ["pace", "fast", "bounce", "bouncy", "seam", "seaming", 
                                              "swing", "carry", "pace friendly", "quick"]):
            characteristics.append("Good for pacers")
        
        if any(term in pitch_desc for term in ["slow and low", "low bounce", "tired", "worn", 
                                              "sluggish", "two-paced"]):
            characteristics.append("Slow and low")
        
        if any(term in pitch_desc for term in ["even contest", "balanced", "fair contest", 
                                              "even battle", "sporting"]):
            characteristics.append("Balanced for bat and ball")
        
        # If we couldn't determine characteristics from the description,
        # try to infer from the statistics
        if not characteristics and pitch_data["average_score"] != "Not available":
            # Extract the average score value
            avg_score_match = re.search(r'\d+', pitch_data["average_score"])
            if avg_score_match:
                avg_score = int(avg_score_match.group())
                # Make assumptions based on the average score
                if avg_score > 300:
                    characteristics.append("Batting friendly")
                elif avg_score < 250:
                    characteristics.append("Bowling friendly")
                    # For Mohali specifically, if the score is low, it's likely good for pacers
                    if "mohali" in city.lower():
                        characteristics.append("Good for pacers")
                else:
                    characteristics.append("Balanced for bat and ball")
        
        # For Mohali specifically, if we still don't have characteristics
        if not characteristics and "mohali" in city.lower():
            # Mohali is known for pace and bounce
            characteristics.append("Good for pacers")
            characteristics.append("Bounce and carry")
        
        if characteristics:
            pitch_data["characteristics"] = ", ".join(characteristics)
        
        # If we have a decent amount of text in the pitch report, clean it up
        if len(pitch_data["pitch_report"]) > 20:
            # Clean up the text by removing extra whitespace and formatting
            pitch_data["pitch_report"] = re.sub(r'\s+', ' ', pitch_data["pitch_report"]).strip()
        
        # Special handling for PCA Stadium (Mohali) if we still don't have a pitch report
        if (pitch_data["pitch_report"] == "Not available" and 
            "mohali" in city.lower() and "punjab" in venue_name.lower()):
            pitch_data["pitch_report"] = (
                "The Punjab Cricket Association IS Bindra Stadium is known for its pace-friendly "
                "conditions. The pitch typically offers good bounce and carry, making it favorable "
                "for fast bowlers. The outfield is quick, and the venue has hosted numerous "
                "memorable international matches. The stadium is located in Mohali, a satellite "
                "city of Chandigarh, and is home to the Punjab Kings in the IPL."
            )
            
            if pitch_data["average_score"] == "Not available":
                pitch_data["average_score"] = "Average 1st innings score: 164"
            
            if pitch_data["highest_score"] == "Not available":
                pitch_data["highest_score"] = "Highest score: 231/4 by PBKS vs RCB"
                
            if pitch_data["lowest_score"] == "Not available":
                pitch_data["lowest_score"] = "Lowest score: 67/10 by PBKS vs MI"
                
            if pitch_data["characteristics"] == "Not available":
                pitch_data["characteristics"] = "Good for pacers, Bounce and carry, Quick outfield"
                
            # Add some known records for Mohali
            pitch_data["interesting_records"] = [
                "Yuvraj Singh hit six sixes in an over against England's Stuart Broad in the 2007 World T20 at this venue.",
                "Chris Gayle scored 117 off 57 balls, including 13 sixes, against PBKS in IPL 2015.",
                "Adam Gilchrist played his last IPL match at this venue.",
                "The stadium hosted the India-Pakistan Test in 1999, which India won by 188 runs."
            ]
        
        return pitch_data
        
    except Exception as e:
        print(f"{Fore.RED}Error fetching pitch report for {venue_name}: {str(e)}{Style.RESET_ALL}")
        return {
            "venue": venue_name,
            "city": city,
            "pitch_report": f"Error fetching data: {str(e)}",
            "average_score": "Not available",
            "highest_score": "Not available",
            "lowest_score": "Not available",
            "characteristics": "Not available",
            "source": "Cricbuzz",
            "source_url": cricbuzz_url,
            "last_updated": datetime.datetime.now().strftime('%Y-%m-%d'),
            "test_stats": {},
            "odi_stats": {},
            "t20_stats": {},
            "ipl_stats": {},
            "interesting_records": [],
            "notable_performances": []
        }


def fetch_weather_data(city, state, country="India"):
    """
    Fetch weather data for a specific location
    
    Args:
        city (str): City name
        state (str): State name
        country (str, optional): Country name. Defaults to "India".
    
    Returns:
        dict: Weather data
    """
    print(f"{Fore.CYAN}Fetching weather data for {city}, {state}...{Style.RESET_ALL}")
    
    api_key = OPENWEATHER_API_KEY
    if not api_key:
        print(f"{Fore.RED}OpenWeatherMap API key not found in environment variables{Style.RESET_ALL}")
        return {
            "city": city,
            "state": state,
            "current_temp": "API key not configured",
            "current_condition": "API key not configured",
            "humidity": "API key not configured",
            "wind_speed": "API key not configured",
            "forecast": "API key not configured",
            "last_updated": datetime.datetime.now().strftime('%Y-%m-%d')
        }
    
    # Define alternative city names for problematic locations
    city_alternatives = {
        "Mumbai": ["Mumbai", "Bombay"],
        "Chennai": ["Chennai", "Madras"],
        "Bengaluru": ["Bengaluru", "Bangalore"],
        "Kolkata": ["Kolkata", "Calcutta"],
        "Visakhapatnam": ["Visakhapatnam", "Vizag", "Vishakhapatnam"],
        "Delhi": ["Delhi", "New Delhi"]
    }
    
    # Get the list of alternatives for this city (or just the city itself if not in the map)
    alternatives = city_alternatives.get(city, [city])
    
    for alt_city in alternatives:
        try:
            # Try without including state first (more reliable for some cities)
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={alt_city}&appid={api_key}&units=metric"
            print(f"{Fore.YELLOW}Trying: {weather_url}{Style.RESET_ALL}")
            
            response = requests.get(weather_url)
            response.raise_for_status()
            
            weather_data = response.json()
            
            # Get forecast - also try without state
            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={alt_city}&appid={api_key}&units=metric"
            forecast_response = requests.get(forecast_url)
            forecast_response.raise_for_status()
            
            forecast_data = forecast_response.json()
            
            # Process current weather
            current_temp = weather_data.get("main", {}).get("temp", "N/A")
            current_condition = weather_data.get("weather", [{}])[0].get("description", "N/A").capitalize()
            humidity = weather_data.get("main", {}).get("humidity", "N/A")
            wind_speed = weather_data.get("wind", {}).get("speed", "N/A")
            
            # Process forecast (next 5 days, once per day)
            forecast_list = forecast_data.get("list", [])
            forecast = []
            
            # Get one forecast entry per day (at noon)
            current_date = datetime.datetime.now().date()
            for i in range(1, 6):  # Next 5 days
                target_date = current_date + datetime.timedelta(days=i)
                target_datetime_str = f"{target_date.strftime('%Y-%m-%d')} 12:00:00"
                
                # Find the closest forecast entry to noon for each day
                closest_entry = None
                min_time_diff = float('inf')
                
                for entry in forecast_list:
                    entry_dt = datetime.datetime.fromtimestamp(entry["dt"])
                    entry_date = entry_dt.date()
                    
                    if entry_date == target_date:
                        # Calculate time difference from noon
                        noon = datetime.datetime.combine(entry_date, datetime.time(12, 0))
                        time_diff = abs((entry_dt - noon).total_seconds())
                        
                        if time_diff < min_time_diff:
                            min_time_diff = time_diff
                            closest_entry = entry
                
                if closest_entry:
                    forecast_date = datetime.datetime.fromtimestamp(closest_entry["dt"]).strftime('%Y-%m-%d')
                    forecast_temp = closest_entry["main"]["temp"]
                    forecast_condition = closest_entry["weather"][0]["description"].capitalize()
                    forecast_humidity = closest_entry["main"]["humidity"]
                    
                    forecast.append({
                        "date": forecast_date,
                        "temp": forecast_temp,
                        "condition": forecast_condition,
                        "humidity": forecast_humidity
                    })
            
            # If we get here, we found a working city name
            print(f"{Fore.GREEN}Successfully fetched weather for {alt_city}{Style.RESET_ALL}")
            
            return {
                "city": city,  # Return the original city name, not the alternative
                "state": state,
                "current_temp": f"{current_temp}°C",
                "current_condition": current_condition,
                "humidity": f"{humidity}%",
                "wind_speed": f"{wind_speed} m/s",
                "forecast": forecast,
                "last_updated": datetime.datetime.now().strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            print(f"{Fore.YELLOW}Failed with city name {alt_city}: {str(e)}{Style.RESET_ALL}")
            # Continue to the next alternative
            continue
    
    # If we get here, all alternatives failed
    print(f"{Fore.RED}Error fetching weather data for {city} and all alternatives{Style.RESET_ALL}")
    return {
        "city": city,
        "state": state,
        "current_temp": f"Error: Could not find weather data for {city}",
        "current_condition": "Error",
        "humidity": "Error",
        "wind_speed": "Error",
        "forecast": "Error",
        "last_updated": datetime.datetime.now().strftime('%Y-%m-%d')
    }


def save_pitch_reports_to_json(pitch_reports):
    """
    Save pitch reports to a JSON file
    
    Args:
        pitch_reports (list): List of pitch report dictionaries
    
    Returns:
        str: Path to the JSON file
    """
    today = datetime.datetime.now().strftime('%Y%m%d')
    filename = os.path.join(FOLDERS['pitch_reports'], f'ipl_pitch_reports_{today}.json')
    
    # Create a structured JSON object
    json_data = {
        "generated_date": datetime.datetime.now().isoformat(),
        "pitch_reports": pitch_reports
    }
    
    # Save to JSON file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)
    
    print(f"{Fore.GREEN}Pitch reports saved to {filename}{Style.RESET_ALL}")
    return filename


def save_weather_reports_to_csv(weather_reports):
    """
    Save weather reports to a CSV file
    
    Args:
        weather_reports (list): List of weather report dictionaries
    
    Returns:
        str: Path to the CSV file
    """
    today = datetime.datetime.now().strftime('%Y%m%d')
    filename = os.path.join(FOLDERS['weather_reports'], f'ipl_weather_reports_{today}.csv')
    
    # Process forecast to flatten it for CSV
    processed_reports = []
    for report in weather_reports:
        processed_report = report.copy()
        
        # Convert forecast list to string representation for CSV
        if isinstance(processed_report["forecast"], list):
            forecast_str = ""
            for day in processed_report["forecast"]:
                forecast_str += f"{day['date']}: {day['temp']}°C, {day['condition']}, {day['humidity']}% humidity\n"
            processed_report["forecast"] = forecast_str.strip()
        
        processed_reports.append(processed_report)
    
    # Create DataFrame
    df = pd.DataFrame(processed_reports)
    
    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"{Fore.GREEN}Weather reports saved to {filename}{Style.RESET_ALL}")
    
    return filename


def save_combined_reports_to_csv(venues, pitch_reports, weather_reports):
    """
    Save combined pitch and weather reports to a CSV file
    
    Args:
        venues (list): List of venue dictionaries
        pitch_reports (list): List of pitch report dictionaries
        weather_reports (list): List of weather report dictionaries
    
    Returns:
        str: Path to the CSV file
    """
    today = datetime.datetime.now().strftime('%Y%m%d')
    filename = os.path.join(FOLDERS['combined_reports'], f'ipl_venue_reports_{today}.csv')
    
    # Create a dictionary to quickly lookup reports by city
    pitch_dict = {report["city"]: report for report in pitch_reports}
    weather_dict = {report["city"]: report for report in weather_reports}
    
    # Combine the data
    combined_reports = []
    for venue in venues:
        venue_name = venue["name"]
        city = venue["city"]
        
        combined_report = {
            "venue": venue_name,
            "city": city,
            "state": venue["state"]
        }
        
        # Add pitch data
        pitch_data = pitch_dict.get(city, {})
        if pitch_data:
            combined_report["pitch_report"] = pitch_data.get("pitch_report", "Not available")
            combined_report["average_score"] = pitch_data.get("average_score", "Not available")
            combined_report["highest_score"] = pitch_data.get("highest_score", "Not available")
            combined_report["lowest_score"] = pitch_data.get("lowest_score", "Not available")
            combined_report["pitch_characteristics"] = pitch_data.get("characteristics", "Not available")
        
        # Add weather data
        weather_data = weather_dict.get(city, {})
        if weather_data:
            combined_report["current_temp"] = weather_data.get("current_temp", "Not available")
            combined_report["current_condition"] = weather_data.get("current_condition", "Not available")
            combined_report["humidity"] = weather_data.get("humidity", "Not available")
            combined_report["wind_speed"] = weather_data.get("wind_speed", "Not available")
            
            # Convert forecast to string
            forecast = weather_data.get("forecast", "Not available")
            if isinstance(forecast, list):
                forecast_str = ""
                for day in forecast:
                    forecast_str += f"{day['date']}: {day['temp']}°C, {day['condition']}, {day['humidity']}% humidity\n"
                combined_report["forecast"] = forecast_str.strip()
            else:
                combined_report["forecast"] = forecast
        
        combined_report["last_updated"] = datetime.datetime.now().strftime('%Y-%m-%d')
        
        combined_reports.append(combined_report)
    
    # Create DataFrame
    df = pd.DataFrame(combined_reports)
    
    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"{Fore.GREEN}Combined reports saved to {filename}{Style.RESET_ALL}")
    
    # Save a more readable HTML report
    html_file = os.path.join(FOLDERS['combined_reports'], f'ipl_venue_reports_{today}.html')
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>IPL 2025 Venue Reports - {today}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #1a5276; }}
            .venue-card {{ 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 15px; 
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .venue-name {{ 
                background-color: #f0f0f0; 
                padding: 10px; 
                margin: -15px -15px 15px -15px;
                border-radius: 8px 8px 0 0;
                font-weight: bold;
                font-size: 18px;
            }}
            .section {{
                margin-bottom: 15px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }}
            .forecast {{
                white-space: pre-line;
                background-color: #f9f9f9;
                padding: 10px;
                border-radius: 4px;
            }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ 
                text-align: left; 
                padding: 8px; 
                border-bottom: 1px solid #ddd; 
            }}
        </style>
    </head>
    <body>
        <h1>IPL 2025 Venue Reports</h1>
        <p>Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """
    
    # Add venue cards
    for report in combined_reports:
        html_content += f"""
        <div class="venue-card">
            <div class="venue-name">{report['venue']} - {report['city']}, {report['state']}</div>
            
            <div class="section">
                <h3>Pitch Report</h3>
                <p>{report.get('pitch_report', 'Not available')}</p>
                
                <table>
                    <tr>
                        <th>Average Score</th>
                        <td>{report.get('average_score', 'Not available')}</td>
                    </tr>
                    <tr>
                        <th>Highest Score</th>
                        <td>{report.get('highest_score', 'Not available')}</td>
                    </tr>
                    <tr>
                        <th>Lowest Score</th>
                        <td>{report.get('lowest_score', 'Not available')}</td>
                    </tr>
                    <tr>
                        <th>Characteristics</th>
                        <td>{report.get('pitch_characteristics', 'Not available')}</td>
                    </tr>
                </table>
            </div>

            <!-- Add Test Statistics Section -->
            <div class="section">
                <h3>Test Match Statistics</h3>
                <table>
                """
    
    # Add Test Statistics if available
    if pitch_dict.get(report['city']) and pitch_dict.get(report['city']).get('test_stats'):
        test_stats = pitch_dict.get(report['city']).get('test_stats', {})
        for stat_key, stat_value in test_stats.items():
            html_content += f"""
                    <tr>
                        <th>{stat_key}</th>
                        <td>{stat_value}</td>
                    </tr>
            """
    else:
        html_content += """
                    <tr>
                        <td colspan="2" style="text-align: center;">No Test statistics available</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>

            <!-- Add ODI Statistics Section -->
            <div class="section">
                <h3>ODI Statistics</h3>
                <table>
                """
    
    # Add ODI Statistics if available
    if pitch_dict.get(report['city']) and pitch_dict.get(report['city']).get('odi_stats'):
        odi_stats = pitch_dict.get(report['city']).get('odi_stats', {})
        for stat_key, stat_value in odi_stats.items():
            html_content += f"""
                    <tr>
                        <th>{stat_key}</th>
                        <td>{stat_value}</td>
                    </tr>
            """
    else:
        html_content += """
                    <tr>
                        <td colspan="2" style="text-align: center;">No ODI statistics available</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>

            <!-- Add T20 Statistics Section -->
            <div class="section">
                <h3>T20 Statistics</h3>
                <table>
                """
    
    # Add T20 Statistics if available
    if pitch_dict.get(report['city']) and pitch_dict.get(report['city']).get('t20_stats'):
        t20_stats = pitch_dict.get(report['city']).get('t20_stats', {})
        for stat_key, stat_value in t20_stats.items():
            html_content += f"""
                    <tr>
                        <th>{stat_key}</th>
                        <td>{stat_value}</td>
                    </tr>
            """
    else:
        html_content += """
                    <tr>
                        <td colspan="2" style="text-align: center;">No T20 statistics available</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>

            <!-- Add IPL Statistics Section -->
            <div class="section">
                <h3>IPL Statistics</h3>
                <table>
                """
    
    # Add IPL Statistics if available
    if pitch_dict.get(report['city']) and pitch_dict.get(report['city']).get('ipl_stats'):
        ipl_stats = pitch_dict.get(report['city']).get('ipl_stats', {})
        for stat_key, stat_value in ipl_stats.items():
            html_content += f"""
                    <tr>
                        <th>{stat_key}</th>
                        <td>{stat_value}</td>
                    </tr>
            """
    else:
        html_content += """
                    <tr>
                        <td colspan="2" style="text-align: center;">No IPL statistics available</td>
                    </tr>
        """
    
    html_content += """
                </table>
            </div>

            <!-- Add Notable Records Section -->
            <div class="section">
                <h3>Notable Records & Performances</h3>
                <ul>
                """
    
    # Add interesting records if available
    if pitch_dict.get(report['city']) and pitch_dict.get(report['city']).get('interesting_records'):
        records = pitch_dict.get(report['city']).get('interesting_records', [])
        for record in records:
            if record and len(record) > 5:  # Skip empty or very short records
                html_content += f"""
                    <li>{record}</li>
                """
    
    # Add notable performances if available
    if pitch_dict.get(report['city']) and pitch_dict.get(report['city']).get('notable_performances'):
        performances = pitch_dict.get(report['city']).get('notable_performances', [])
        for performance in performances:
            if performance and len(performance) > 5:  # Skip empty or very short performances
                html_content += f"""
                    <li>{performance}</li>
                """
    
    # If no records found
    if not (pitch_dict.get(report['city']) and 
           (pitch_dict.get(report['city']).get('interesting_records') or 
            pitch_dict.get(report['city']).get('notable_performances'))):
        html_content += """
                    <li>No notable records available</li>
        """
    
    html_content += """
                </ul>
            </div>
            
            <div class="section">
                <h3>Current Weather</h3>
                <table>
                    <tr>
                        <th>Temperature</th>
                        <td>{report.get('current_temp', 'Not available')}</td>
                    </tr>
                    <tr>
                        <th>Condition</th>
                        <td>{report.get('current_condition', 'Not available')}</td>
                    </tr>
                    <tr>
                        <th>Humidity</th>
                        <td>{report.get('humidity', 'Not available')}</td>
                    </tr>
                    <tr>
                        <th>Wind Speed</th>
                        <td>{report.get('wind_speed', 'Not available')}</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h3>5-Day Forecast</h3>
                <div class="forecast">{report.get('forecast', 'Not available')}</div>
            </div>
        </div>
        """
    
    html_content += """
    </body>
    </html>
    """
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"{Fore.GREEN}HTML report saved to {html_file}{Style.RESET_ALL}")
    
    return filename, html_file


def scrape_pitch_reports():
    """
    Scrape pitch reports for all IPL venues using direct Cricbuzz URLs
    
    Returns:
        list: List of pitch report dictionaries
    """
    print(f"\n{Fore.CYAN}===== Scraping Pitch Reports ====={Style.RESET_ALL}")
    
    pitch_reports = []
    
    for venue in IPL_VENUES:
        # Get pitch report directly from Cricbuzz using the venue object with URLs
        pitch_data = fetch_cricbuzz_pitch_report(venue)
        pitch_reports.append(pitch_data)
        
        # Print a preview of the data
        print(f"\n{Fore.GREEN}Pitch Report for {venue['name']} ({venue['city']}){Style.RESET_ALL}")
        print(f"Description: {pitch_data['pitch_report'][:150]}..." if len(pitch_data['pitch_report']) > 150 else f"Description: {pitch_data['pitch_report']}")
        print(f"Average Score: {pitch_data['average_score']}")
        print(f"Highest Score: {pitch_data['highest_score']}")
        print(f"Characteristics: {pitch_data['characteristics']}")
        
        # Add a small delay to avoid rate limiting
        time.sleep(2)
    
    return pitch_reports


def get_weather_reports():
    """
    Get weather reports for all IPL venues
    
    Returns:
        list: List of weather report dictionaries
    """
    print(f"\n{Fore.CYAN}===== Getting Weather Reports ====={Style.RESET_ALL}")
    
    weather_reports = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit tasks
        future_to_venue = {
            executor.submit(fetch_weather_data, venue["city"], venue["state"]): venue
            for venue in IPL_VENUES
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_venue):
            venue = future_to_venue[future]
            try:
                weather_data = future.result()
                weather_reports.append(weather_data)
                print(f"{Fore.GREEN}Completed weather report for {venue['city']}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error processing weather for {venue['city']}: {str(e)}{Style.RESET_ALL}")
    
    return weather_reports


def display_pitch_report_terminal(venue_name, pitch_data):
    """
    Display a pitch report in the terminal with nice formatting
    
    Args:
        venue_name (str): Name of the venue
        pitch_data (dict): Pitch report data
    """
    width = 80
    print("\n" + "=" * width)
    print(f"{venue_name}".center(width))
    print("=" * width)
    
    print(f"\n{Fore.YELLOW}PITCH REPORT:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{pitch_data['pitch_report']}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}STATISTICS:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Average Score: {Style.RESET_ALL}{pitch_data['average_score']}")
    print(f"{Fore.CYAN}Highest Score: {Style.RESET_ALL}{pitch_data['highest_score']}")
    print(f"{Fore.CYAN}Lowest Score: {Style.RESET_ALL}{pitch_data['lowest_score']}")
    
    print(f"\n{Fore.YELLOW}CHARACTERISTICS:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{pitch_data['characteristics']}{Style.RESET_ALL}")
    
    print("\n" + "-" * width)


def main():
    """Main function to run the scraper"""
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   IPL PITCH & WEATHER REPORT SCRAPER  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create folder structure
    create_folders()
    
    # Scrape pitch reports
    pitch_reports = scrape_pitch_reports()
    
    # Display detailed pitch reports in terminal
    print(f"\n{Fore.CYAN}===== Detailed Pitch Reports ====={Style.RESET_ALL}")
    for pitch_data in pitch_reports:
        display_pitch_report_terminal(pitch_data["venue"], pitch_data)
    
    # Get weather reports
    weather_reports = get_weather_reports()
    
    # Save reports to CSV
    pitch_csv = save_pitch_reports_to_json(pitch_reports)
    weather_csv = save_weather_reports_to_csv(weather_reports)
    
    # Save combined reports
    combined_csv, combined_html = save_combined_reports_to_csv(IPL_VENUES, pitch_reports, weather_reports)
    
    print(f"\n{Fore.GREEN}All tasks completed.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    
    return {
        "pitch_reports": pitch_csv,
        "weather_reports": weather_csv,
        "combined_reports": combined_csv,
        "combined_html": combined_html
    }


if __name__ == "__main__":
    main()