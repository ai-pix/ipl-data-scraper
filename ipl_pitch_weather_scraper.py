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

# Load environment variables from .env file - add debugging
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
print(f"{Fore.YELLOW}API Key loaded: {OPENWEATHER_API_KEY[:5]}...{OPENWEATHER_API_KEY[-5:] if OPENWEATHER_API_KEY else 'None'}{Style.RESET_ALL}")

# Initialize colorama for colored console output
init()

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
        "cricbuzz_url": "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/venues/851/maharaja-yadavindra-singh-international-cricket-stadium-mullanpur"
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
        
        # Initialize the pitch data dictionary
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
            "last_updated": datetime.datetime.now().strftime('%Y-%m-%d')
        }
        
        # Look for the venue description paragraphs
        venue_description = ""
        # Find the paragraph with "Venue Description" heading
        venue_desc_section = soup.find('p', string=lambda text: text and 'Venue Description' in text)
        if venue_desc_section:
            # Get all the content from this paragraph
            venue_description = venue_desc_section.get_text(strip=True)
        
        # If we couldn't find it that way, try looking for all paragraphs
        if not venue_description:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                if 'Venue Description' in p.get_text() or 'venue description' in p.get_text().lower():
                    venue_description = p.get_text(strip=True)
                    break
        
        # Look for pitch information specifically
        pitch_info = ""
        for p in soup.find_all('p'):
            if 'How does the pitch play?' in p.get_text() or 'pitch' in p.get_text().lower():
                pitch_info = p.get_text(strip=True)
                break
        
        # Combine the information
        if venue_description:
            pitch_data["pitch_report"] = venue_description
        if pitch_info:
            pitch_data["pitch_report"] += "\n" + pitch_info
        
        # Get stats from tables
        tables = soup.find_all('table', class_='table')
        for table in tables:
            # Look for ODI or T20 stats
            if 'STATS - ODI' in str(table.previous_sibling) or 'STATS - T20' in str(table.previous_sibling):
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        header = cols[0].get_text(strip=True)
                        value = cols[1].get_text(strip=True)
                        
                        if 'Average 1st Inns scores' in header:
                            pitch_data["average_score"] = f"Average 1st innings score: {value}"
                        elif 'Highest total recorded' in header:
                            pitch_data["highest_score"] = f"Highest score: {value}"
                        elif 'Lowest total recorded' in header:
                            pitch_data["lowest_score"] = f"Lowest score: {value}"
        
        # Extract pitch characteristics from the venue description
        pitch_desc = pitch_data["pitch_report"].lower()
        characteristics = []
        
        # Check for various pitch characteristics in the description
        if any(term in pitch_desc for term in ["batting friendly", "batting paradise", "flat", "high scoring", "high-scoring", "run fest", "run-fest", "batting surface", "batsmen", "batters"]):
            characteristics.append("Batting friendly")
        
        if any(term in pitch_desc for term in ["spin", "spinner", "spinners", "turning", "turn", "slow"]):
            characteristics.append("Assists spin")
        
        if any(term in pitch_desc for term in ["pace", "fast", "bounce", "bouncy", "seam", "seaming", "swing"]):
            characteristics.append("Good for pacers")
        
        if any(term in pitch_desc for term in ["slow and low", "low bounce", "tired", "worn"]):
            characteristics.append("Slow and low")
        
        if any(term in pitch_desc for term in ["even contest", "balanced", "fair contest", "even battle"]):
            characteristics.append("Balanced for bat and ball")
        
        if characteristics:
            pitch_data["characteristics"] = ", ".join(characteristics)
        
        # If we have a decent amount of text in the pitch report, clean it up
        if len(pitch_data["pitch_report"]) > 20:
            # Clean up the text by removing extra whitespace and formatting
            pitch_data["pitch_report"] = re.sub(r'\s+', ' ', pitch_data["pitch_report"]).strip()
        
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
            "last_updated": datetime.datetime.now().strftime('%Y-%m-%d')
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


def save_pitch_reports_to_csv(pitch_reports):
    """
    Save pitch reports to a CSV file
    
    Args:
        pitch_reports (list): List of pitch report dictionaries
    
    Returns:
        str: Path to the CSV file
    """
    today = datetime.datetime.now().strftime('%Y%m%d')
    filename = os.path.join(FOLDERS['pitch_reports'], f'ipl_pitch_reports_{today}.csv')
    
    # Create DataFrame
    df = pd.DataFrame(pitch_reports)
    
    # Save to CSV
    df.to_csv(filename, index=False)
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
    pitch_csv = save_pitch_reports_to_csv(pitch_reports)
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