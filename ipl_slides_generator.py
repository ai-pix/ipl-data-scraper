#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IPL Slides Generator
-------------------

This script generates interactive HTML slides showcasing IPL cricket data,
including team standings, player performance, and match predictions.

The output is a self-contained HTML file with embedded CSS and JavaScript
that creates an attractive slideshow presentation of the cricket data.

Usage:
    python ipl_slides_generator.py [options]

Options:
    --output-file   Specify custom output filename (default: ipl_slides_[date].html)
    --theme         Specify theme (light, dark, team-colors) (default: team-colors)
    --slide-count   Maximum number of slides to generate (default: all)
    --help          Show this help message and exit
"""

import os
import sys
import json
import csv
import glob
import logging
import argparse
import datetime
import re
import base64
import random
import pandas as pd  # Added pandas import
from pathlib import Path
import shutil
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ipl_slides_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default paths and settings
SLIDES_DIR = "ipl_slides"
POINTS_TABLE_DIR = "points_table"
BATTING_STATS_DIR = "batting_stats"
BOWLING_STATS_DIR = "bowling_stats"
TEAM_DATA_DIR = "team_data" 
PLAYER_IMAGES_DIR = "player_images"
LOGOS_DIR = "LOGO"
PREDICTIONS_DIR = "predictions"
COMPARISON_DATA_DIR = "comparison_data"
MATCHES_DIR = "matches"
PITCH_REPORTS_DIR = "pitch_reports"  # Added pitch reports directory
WEATHER_REPORTS_DIR = "weather_reports"  # Added weather reports directory

# Theme settings
THEMES = {
    "light": {
        "background": "#ffffff",
        "text": "#333333",
        "accent": "#007bff",
        "highlight": "#f8f9fa",
        "border": "#dee2e6"
    },
    "dark": {
        "background": "#121212",
        "text": "#f1f1f1",
        "accent": "#3498db",
        "highlight": "#2d2d2d",
        "border": "#444444"
    },
    "team-colors": "dynamic" # Will dynamically use team colors
}

# Team color mappings (approximated from actual IPL team colors)
TEAM_COLORS = {
    "chennai_super_kings": {"primary": "#FFFF00", "secondary": "#0080C8", "text": "#000000"},
    "delhi_capitals": {"primary": "#0080C8", "secondary": "#FF0000", "text": "#ffffff"},
    "gujarat_titans": {"primary": "#1F51BC", "secondary": "#0080C8", "text": "#ffffff"},
    "kolkata_knight_riders": {"primary": "#3A225D", "secondary": "#FDB913", "text": "#ffffff"},
    "lucknow_super_giants": {"primary": "#A72056", "secondary": "#FFAEC8", "text": "#ffffff"},
    "mumbai_indians": {"primary": "#004BA0", "secondary": "#D1AB3E", "text": "#ffffff"},
    "punjab_kings": {"primary": "#ED1B24", "secondary": "#FFFFFF", "text": "#ffffff"},
    "rajasthan_royals": {"primary": "#FF69B4", "secondary": "#0080C8", "text": "#ffffff"},
    "royal_challengers_bangalore": {"primary": "#EC1C24", "secondary": "#000000", "text": "#ffffff"},
    "sunrisers_hyderabad": {"primary": "#FF822A", "secondary": "#000000", "text": "#ffffff"}
}

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='IPL Slides Generator')
    parser.add_argument('--output-file', type=str, help='Specify custom output filename')
    parser.add_argument('--theme', choices=['light', 'dark', 'team-colors'], default='team-colors', 
                        help='Specify theme (light, dark, team-colors)')
    parser.add_argument('--slide-count', type=int, default=0, 
                        help='Maximum number of slides to generate (0 for all)')
    parser.add_argument('--standalone', action='store_true', 
                        help='Generate a completely standalone HTML file with embedded images')
    return parser.parse_args()

def ensure_slides_directory():
    """Ensure the slides output directory exists."""
    if not os.path.exists(SLIDES_DIR):
        os.makedirs(SLIDES_DIR)
        logger.info(f"Created slides directory: {SLIDES_DIR}")

def get_latest_file(pattern, directory):
    """Get the most recent file matching the given pattern in the directory."""
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def get_today_file(pattern, directory):
    """Get today's file matching the pattern, or latest if not found."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    today_pattern = pattern.replace('*', f'*_{today}*')
    today_files = glob.glob(os.path.join(directory, today_pattern))
    if today_files:
        return today_files[0]
    return get_latest_file(pattern, directory)

def load_points_table():
    """Load the latest points table data."""
    points_file = get_today_file("ipl_points_table_*.csv", POINTS_TABLE_DIR)
    if not points_file:
        points_file = os.path.join(POINTS_TABLE_DIR, "ipl_points_table_latest.csv")
        if not os.path.exists(points_file):
            logger.warning("No points table file found")
            return []
    
    try:
        points_data = []
        with open(points_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                points_data.append(row)
        return points_data
    except Exception as e:
        logger.error(f"Error loading points table: {str(e)}")
        return []

def load_batting_leaders():
    """Load the latest batting statistics."""
    stats = {}
    
    # Categories to load
    categories = ['most-runs', 'most-4s', 'most-6s', 'most-fifties', 'most-hundreds']
    
    for category in categories:
        stat_file = get_today_file(f"ipl_{category}_*.csv", BATTING_STATS_DIR)
        if not stat_file:
            continue
            
        try:
            with open(stat_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Only take top 5 players for each category
                stats[category] = [row for row in reader][:5]
        except Exception as e:
            logger.error(f"Error loading {category} stats: {str(e)}")
    
    return stats

def load_bowling_leaders():
    """Load the latest bowling statistics."""
    stats = {}
    
    # Categories to load
    categories = ['most-wickets', 'best-economy-rates', 
                  'best-bowling-average', 'best-bowling-strike-rate']
    
    for category in categories:
        stat_file = get_today_file(f"ipl_{category}_*.csv", BOWLING_STATS_DIR)
        if not stat_file:
            continue
            
        try:
            with open(stat_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Only take top 5 players for each category
                stats[category] = [row for row in reader][:5]
        except Exception as e:
            logger.error(f"Error loading {category} stats: {str(e)}")
    
    return stats

def load_upcoming_matches():
    """Load upcoming match data."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    matches_file = os.path.join(MATCHES_DIR, f"todays_matches_{today}.csv")
    
    if not os.path.exists(matches_file):
        # Try to find any recent matches file
        matches_files = sorted(glob.glob(os.path.join(MATCHES_DIR, "todays_matches_*.csv")), 
                             key=os.path.getmtime, reverse=True)
        if not matches_files:
            logger.warning("No matches file found")
            return []
        matches_file = matches_files[0]
    
    try:
        matches = []
        with open(matches_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matches.append(row)
        return matches
    except Exception as e:
        logger.error(f"Error loading matches: {str(e)}")
        return []

def load_weather_data():
    """Load weather data from the most recent weather report file"""
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # First look for a JSON file
    json_pattern = os.path.join('weather_reports', f'ipl_weather_reports_{today}.json')
    json_files = glob.glob(json_pattern)
    
    if json_files:
        # Use the most recent JSON file
        json_file = max(json_files, key=os.path.getctime)
        logging.info(f"Loading weather data from JSON file: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                weather_reports = data.get("weather_reports", [])
                
                # Create a dictionary mapping city names to weather data
                weather_data = {}
                for report in weather_reports:
                    city = report.get("city")
                    if city:
                        weather_data[city] = report
                
                return weather_data
                
        except Exception as e:
            logging.error(f"Error loading weather JSON data: {str(e)}")
            # If JSON fails, fall back to CSV
    
    # If no JSON files, fall back to CSV
    csv_pattern = os.path.join('weather_reports', f'ipl_weather_reports_{today}.csv')
    csv_files = glob.glob(csv_pattern)
    
    if csv_files:
        # Use the most recent CSV file
        csv_file = max(csv_files, key=os.path.getctime)
        logging.info(f"Loading weather data from CSV file: {csv_file}")
        
        try:
            # Read CSV using pandas
            df = pd.read_csv(csv_file)
            
            # Convert DataFrame to a dictionary
            weather_data = {}
            for _, row in df.iterrows():
                city = row.get("city")
                if city:
                    weather_data[city] = row.to_dict()
            
            return weather_data
            
        except Exception as e:
            logging.error(f"Error loading weather CSV data: {str(e)}")
    
    # If no files found or errors occurred, return empty dictionary
    logging.warning("No weather data files found or all attempts to load failed.")
    return {}

def load_pitch_data():
    """Load pitch data for venues."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    pitch_data = {}
    
    # Try to find pitch report files from today first
    pitch_files = glob.glob(os.path.join(PITCH_REPORTS_DIR, f"*_{today}.json"))
    
    # If no files for today, get the most recent ones
    if not pitch_files:
        pitch_files = sorted(glob.glob(os.path.join(PITCH_REPORTS_DIR, "*.json")), 
                          key=os.path.getmtime, reverse=True)
        
    if not pitch_files:
        logger.warning("No pitch report files found")
        return pitch_data
    
    # Process pitch files (limit to 5 most recent)
    for pitch_file in pitch_files[:5]:
        try:
            with open(pitch_file, 'r', encoding='utf-8') as f:
                venue_pitch = json.load(f)
                
                # Extract venue name from filename
                filename = os.path.basename(pitch_file)
                venue_name = re.sub(r'_\d{8}\.json$', '', filename)
                venue_name = venue_name.replace('_pitch_', '').replace('_', ' ').title()
                
                pitch_data[venue_name] = venue_pitch
        except Exception as e:
            logger.error(f"Error loading pitch data file {pitch_file}: {str(e)}")
            
    return pitch_data

def load_team_logos():
    """Load team logos as base64 for embedding in slides."""
    logos = {}
    
    if os.path.exists(LOGOS_DIR):
        for logo_file in os.listdir(LOGOS_DIR):
            if logo_file.endswith(('.png', '.jpg', '.jpeg')):
                team_name = os.path.splitext(logo_file)[0]
                logo_path = os.path.join(LOGOS_DIR, logo_file)
                
                try:
                    with open(logo_path, 'rb') as f:
                        image_data = f.read()
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        image_type = logo_file.split('.')[-1].lower()
                        if image_type == 'jpg':
                            image_type = 'jpeg'
                        logos[team_name] = f"data:image/{image_type};base64,{base64_data}"
                except Exception as e:
                    logger.error(f"Error loading logo for {team_name}: {str(e)}")
    
    return logos

def load_predictions():
    """Load match prediction data."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    prediction_file = os.path.join(PREDICTIONS_DIR, f"match_predictions_{today}.json")
    
    if not os.path.exists(prediction_file):
        # Try to find any recent prediction file
        prediction_files = sorted(glob.glob(os.path.join(PREDICTIONS_DIR, "match_predictions_*.json")), 
                                key=os.path.getmtime, reverse=True)
        if not prediction_files:
            logger.warning("No prediction file found")
            return {}
        prediction_file = prediction_files[0]
    
    try:
        with open(prediction_file, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
        return predictions
    except Exception as e:
        logger.error(f"Error loading predictions: {str(e)}")
        return {}

def load_player_images(num_players=20):
    """Load random player images for gallery slides."""
    player_images = []
    
    if not os.path.exists(PLAYER_IMAGES_DIR):
        logger.warning(f"Player images directory not found: {PLAYER_IMAGES_DIR}")
        return player_images
    
    # Get all team directories
    team_dirs = [d for d in os.listdir(PLAYER_IMAGES_DIR) 
                if os.path.isdir(os.path.join(PLAYER_IMAGES_DIR, d))]
    
    for team_dir in team_dirs:
        team_path = os.path.join(PLAYER_IMAGES_DIR, team_dir)
        
        # Skip non-directories or special directories
        if not os.path.isdir(team_path) or team_dir.startswith('.'):
            continue
        
        # Get all image files
        image_files = [f for f in os.listdir(team_path) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        # Randomly select some players from each team
        num_from_team = min(len(image_files), num_players // len(team_dirs) + 1)
        selected_images = random.sample(image_files, num_from_team) if image_files else []
        
        for img_file in selected_images:
            img_path = os.path.join(team_path, img_file)
            
            # Extract player name from filename
            player_name = img_file.split('.')[0].replace('_', ' ').replace('-', ' ').title()
            
            try:
                with open(img_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    ext = os.path.splitext(img_file)[1].lower()[1:]
                    if ext == 'jpg':
                        ext = 'jpeg'
                    
                    player_images.append({
                        'name': player_name,
                        'team': team_dir.replace('_', ' ').title(),
                        'image': f"data:image/{ext};base64,{base64_data}"
                    })
            except Exception as e:
                logger.error(f"Error processing player image {img_file}: {str(e)}")
    
    # Shuffle images for randomness
    random.shuffle(player_images)
    
    # Limit to desired number
    return player_images[:num_players]

def load_team_data():
    """Load team data including current squad and statistics."""
    team_data = {}
    
    if not os.path.exists(TEAM_DATA_DIR):
        logger.warning(f"Team data directory not found: {TEAM_DATA_DIR}")
        return team_data
    
    # Get team directories
    team_dirs = [d for d in os.listdir(TEAM_DATA_DIR) 
                if os.path.isdir(os.path.join(TEAM_DATA_DIR, d))]
    
    for team_dir in team_dirs:
        team_path = os.path.join(TEAM_DATA_DIR, team_dir)
        team_name = team_dir.replace('_', ' ').title()
        team_data[team_name] = {'squad': [], 'stats': {}}
        
        # Load squad data
        squad_file = os.path.join(team_path, 'players', 'squad.csv')
        if os.path.exists(squad_file):
            try:
                with open(squad_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    team_data[team_name]['squad'] = list(reader)
            except Exception as e:
                logger.error(f"Error loading squad data for {team_name}: {str(e)}")
        
        # Load team stats
        stats_file = os.path.join(team_path, 'stats', 'team_statistics.json')
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    team_data[team_name]['stats'] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading team stats for {team_name}: {str(e)}")
    
    return team_data

def load_team_comparison_data():
    """Load team comparison data for today's matches."""
    today = datetime.datetime.now().strftime("%Y%m%d")
    comparison_data = {}
    
    # Try today's comparison file first
    comparison_file = os.path.join(COMPARISON_DATA_DIR, f"today_match_comparison_summary_{today}.json")
    
    # If today's file doesn't exist, get the most recent one
    if not os.path.exists(comparison_file):
        comparison_files = sorted(glob.glob(os.path.join(COMPARISON_DATA_DIR, "today_match_comparison_summary_*.json")), 
                              key=os.path.getmtime, reverse=True)
        if comparison_files:
            comparison_file = comparison_files[0]
        else:
            logger.warning("No team comparison data files found")
            return comparison_data
    
    try:
        with open(comparison_file, 'r', encoding='utf-8') as f:
            comparison_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading comparison data: {str(e)}")
        
    return comparison_data

def generate_slides_html(args):
    """Generate HTML slides showcasing IPL data."""
    logger.info("Generating IPL slides HTML...")
    
    # Load all required data
    points_table = load_points_table()
    batting_stats = load_batting_leaders()
    bowling_stats = load_bowling_leaders()
    team_logos = load_team_logos()
    upcoming_matches = load_upcoming_matches()
    predictions = load_predictions()
    player_images = load_player_images(20) if args.standalone else []
    weather_data = load_weather_data()  # Added weather data
    pitch_data = load_pitch_data()      # Added pitch data
    team_data = load_team_data()        # Added team data
    team_comparison_data = load_team_comparison_data()  # Added comparison data
    
    # Determine theme
    theme = THEMES[args.theme]
    
    # Generate output filename based on current date
    today = datetime.datetime.now().strftime("%Y%m%d")
    if args.output_file:
        output_filename = args.output_file
    else:
        output_filename = f"ipl_slides_{today}.html"
    
    output_path = os.path.join(SLIDES_DIR, output_filename)
    
    # Collect slide data
    slides = []
    
    # Title slide
    slides.append({
        'type': 'title',
        'title': 'IPL Cricket Dashboard',
        'subtitle': f"Season {datetime.datetime.now().year}",
        'date': datetime.datetime.now().strftime("%d %B %Y")
    })
    
    # Points table slide
    if points_table:
        slides.append({
            'type': 'points-table',
            'title': 'IPL Points Table',
            'data': points_table
        })
    
    # Today's matches slide with improved match information
    if upcoming_matches:
        slides.append({
            'type': 'matches',
            'title': "Today's Matches",
            'data': upcoming_matches,
            'predictions': predictions,
            'weather_data': weather_data,
            'pitch_data': pitch_data
        })
    
    # Team comparison slides for today's matches with detailed head-to-head data
    for match in upcoming_matches:
        if 'Team 1' in match and 'Team 2' in match:
            team1 = match['Team 1']
            team2 = match['Team 2']
            venue = match.get('Venue', '')
            
            # Get head-to-head data from team comparison data
            head_to_head = {}
            match_key = f"{team1} vs {team2}"
            if match_comparison_data := team_comparison_data.get(match_key, {}):
                head_to_head = match_comparison_data.get('head_to_head', {})
            
            # Get team stats
            team1_data = team_data.get(team1, {})
            team2_data = team_data.get(team2, {})
            
            # Get venue-specific data
            venue_weather = weather_data.get(venue, {})
            venue_pitch = pitch_data.get(venue, {})
            
            slides.append({
                'type': 'detailed-team-comparison',
                'title': f"{team1} vs {team2} - Head to Head",
                'team1': team1,
                'team2': team2,
                'match_data': match,
                'prediction': predictions.get(match_key, {}),
                'head_to_head': head_to_head,
                'team1_data': team1_data,
                'team2_data': team2_data,
                'weather': venue_weather,
                'pitch': venue_pitch
            })
            
            # Add overall team stats comparison
            slides.append({
                'type': 'overall-comparison',
                'title': f"{team1} vs {team2} - Overall Comparison",
                'team1': team1,
                'team2': team2,
                'team1_data': team1_data,
                'team2_data': team2_data,
                'logo1': team_logos.get(team1.lower().replace(' ', '_'), ''),
                'logo2': team_logos.get(team2.lower().replace(' ', '_'), '')
            })
    
    # Weather and pitch report slides for today's venues
    venues_added = set()
    for match in upcoming_matches:
        venue = match.get('Venue', '')
        if venue and venue not in venues_added:
            venue_weather = weather_data.get(venue, {})
            venue_pitch = pitch_data.get(venue, {})
            
            if venue_weather or venue_pitch:
                slides.append({
                    'type': 'venue-conditions',
                    'title': f"{venue} - Match Conditions",
                    'venue': venue,
                    'weather': venue_weather,
                    'pitch': venue_pitch,
                    'matches': [m for m in upcoming_matches if m.get('Venue') == venue]
                })
                venues_added.add(venue)
    
    # Top run scorers slide
    if batting_stats.get('most-runs'):
        slides.append({
            'type': 'stat-leaders',
            'title': 'Top Run Scorers',
            'category': 'batting',
            'data': batting_stats['most-runs']
        })
    
    # Top wicket takers slide
    if bowling_stats.get('most-wickets'):
        slides.append({
            'type': 'stat-leaders',
            'title': 'Top Wicket Takers',
            'category': 'bowling',
            'data': bowling_stats['most-wickets']
        })
    
    # Team overview slides
    for team_name, data in team_data.items():
        # Only create slides for teams with sufficient data
        if data.get('stats') or data.get('squad'):
            slides.append({
                'type': 'team-overview',
                'title': f"{team_name} - Team Overview",
                'team': team_name,
                'data': data,
                'logo': team_logos.get(team_name.lower().replace(' ', '_'), '')
            })
    
    # Player gallery slide
    if player_images:
        slides.append({
            'type': 'player-gallery',
            'title': 'IPL Star Players',
            'players': player_images
        })
    
    # Batting records slides
    if batting_stats.get('most-6s'):
        slides.append({
            'type': 'stat-leaders',
            'title': 'Most Sixes',
            'category': 'batting',
            'data': batting_stats['most-6s']
        })
    
    # Bowling records slides
    if bowling_stats.get('best-economy-rates'):
        slides.append({
            'type': 'stat-leaders',
            'title': 'Best Economy Rates',
            'category': 'bowling',
            'data': bowling_stats['best-economy-rates']
        })
    
    # Limit slides if requested
    if args.slide_count > 0:
        slides = slides[:args.slide_count]
    
    # Begin HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPL Cricket Slides - {datetime.datetime.now().strftime("%Y-%m-%d")}</title>
    <style>
        /* Reset and Base styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #121212;
            color: #ffffff;
            line-height: 1.6;
            overflow: hidden;
            height: 100vh;
        }}
        
        /* Slide container */
        .slide-container {{
            position: relative;
            width: 100%;
            height: 100vh;
            overflow: hidden;
        }}
        
        /* Slides */
        .slide {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 40px;
            opacity: 0;
            transition: opacity 0.8s ease, transform 0.8s ease;
            transform: translateX(100%);
            z-index: 1;
        }}
        
        .slide.active {{
            opacity: 1;
            transform: translateX(0);
            z-index: 2;
        }}
        
        .slide.prev {{
            transform: translateX(-100%);
        }}
        
        /* Slide content */
        .slide-content {{
            position: relative;
            width: 100%;
            max-width: 1200px;
            background-color: rgba(18, 18, 18, 0.8);
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            overflow-y: auto;
            max-height: 90vh;
            z-index: 1;
        }}
        
        .slide-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            text-align: center;
            color: #ffffff;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
        }}
        
        .slide-subtitle {{
            font-size: 1.5rem;
            font-weight: 400;
            margin-bottom: 20px;
            text-align: center;
            color: #cccccc;
        }}
        
        /* Navigation controls */
        .slide-controls {{
            position: absolute;
            bottom: 20px;
            left: 0;
            width: 100%;
            display: flex;
            justify-content: center;
            gap: 20px;
            z-index: 10;
        }}
        
        .prev-btn, .next-btn {{
            background-color: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 50px;
            transition: background-color 0.3s;
        }}
        
        .prev-btn:hover, .next-btn:hover {{
            background-color: rgba(255, 255, 255, 0.4);
        }}
        
        /* Progress indicators */
        .slide-indicators {{
            position: absolute;
            bottom: 80px;
            left: 0;
            width: 100%;
            display: flex;
            justify-content: center;
            gap: 10px;
            z-index: 10;
        }}
        
        .indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: rgba(255, 255, 255, 0.3);
            cursor: pointer;
            transition: background-color 0.3s, transform 0.3s;
        }}
        
        .indicator.active {{
            background-color: #ffffff;
            transform: scale(1.2);
        }}
        
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            border-radius: 5px;
            overflow: hidden;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }}
        
        th, td {{
            padding: 12px 15px;
            text-align: left;
        }}
        
        th {{
            background-color: rgba(0, 123, 255, 0.8);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9rem;
        }}
        
        tr:nth-child(even) {{
            background-color: rgba(255, 255, 255, 0.05);
        }}
        
        tr:hover {{
            background-color: rgba(255, 255, 255, 0.1);
        }}
        
        /* Title slide */
        .title-slide {{
            text-align: center;
        }}
        
        .title-slide h1 {{
            font-size: 4rem;
            margin-bottom: 20px;
            background: linear-gradient(45deg, #3498db, #1abc9c, #9b59b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: none;
        }}
        
        .title-slide h2 {{
            font-size: 2rem;
            margin-bottom: 30px;
            color: #f1c40f;
        }}
        
        /* Stats leaders */
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            width: 100%;
        }}
        
        .stat-card {{
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }}
        
        .player-name {{
            font-weight: 600;
            font-size: 1.2rem;
            margin-bottom: 5px;
        }}
        
        .player-team {{
            color: #cccccc;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }}
        
        .player-stat {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #f1c40f;
        }}
        
        /* Team comparison */
        .team-comparison {{
            display: flex;
            width: 100%;
            justify-content: space-between;
            margin-top: 20px;
        }}
        
        .team-side {{
            flex: 1;
            text-align: center;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            margin: 0 10px;
        }}
        
        .team-logo {{
            width: 100px;
            height: 100px;
            object-fit: contain;
            margin-bottom: 15px;
        }}
        
        .vs-container {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 0 20px;
        }}
        
        .vs-text {{
            font-size: 2rem;
            font-weight: 700;
            color: #e74c3c;
            margin-bottom: 10px;
        }}
        
        .prediction-text {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #f1c40f;
            text-align: center;
            margin-top: 20px;
        }}
        
        /* Head to head comparison */
        .head-to-head {{
            margin-top: 20px;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }}
        
        .head-to-head h3 {{
            text-align: center;
            margin-bottom: 15px;
            color: #f1c40f;
        }}
        
        .head-to-head-stats {{
            display: flex;
            justify-content: space-between;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            margin: 10px 0;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: #cccccc;
        }}
        
        /* Team overview */
        .team-overview {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        .team-header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .team-stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 15px;
            width: 100%;
            margin-top: 20px;
        }}
        
        .team-stat-card {{
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        
        .team-stat-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #3498db;
            margin-bottom: 5px;
        }}
        
        .team-stat-label {{
            font-size: 0.8rem;
            color: #cccccc;
        }}
        
        /* Weather and pitch conditions */
        .venue-conditions {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 20px;
        }}
        
        .condition-box {{
            flex: 1;
            min-width: 300px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
        }}
        
        .condition-box h3 {{
            color: #f1c40f;
            margin-bottom: 15px;
            text-align: center;
        }}
        
        .weather-icon {{
            font-size: 3rem;
            text-align: center;
            margin: 10px 0;
        }}
        
        .weather-details, .pitch-details {{
            margin-top: 15px;
        }}
        
        .detail-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .detail-label {{
            font-weight: 600;
        }}
        
        /* Player gallery */
        .player-gallery {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 20px;
            width: 100%;
        }}
        
        .player-card {{
            width: 150px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;
            transition: transform 0.3s;
        }}
        
        .player-card:hover {{
            transform: translateY(-5px);
        }}
        
        .player-image {{
            width: 100%;
            height: 150px;
            object-fit: cover;
        }}
        
        .player-card-details {{
            padding: 10px;
        }}
        
        .player-card-name {{
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .player-card-team {{
            color: #cccccc;
            font-size: 0.8rem;
        }}
        
        /* Background effects */
        .slide-bg {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-size: cover;
            background-position: center;
            filter: blur(10px) brightness(0.3);
            z-index: 0;
        }}
        
        /* Team-specific colors */
        .team-colors {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7));
            z-index: 0;
        }}
        
        /* Additional styles for new slide types */
        .detailed-comparison {{
            margin-top: 20px;
        }}
        
        .comparison-tabs {{
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
        }}
        
        .comparison-tab {{
            padding: 10px 20px;
            background-color: rgba(255, 255, 255, 0.1);
            color: white;
            border: none;
            cursor: pointer;
            margin: 0 5px;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        
        .comparison-tab.active {{
            background-color: rgba(52, 152, 219, 0.8);
        }}
        
        .comparison-content {{
            display: none;
        }}
        
        .comparison-content.active {{
            display: block;
        }}
        
        .stat-bar-container {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .team-name {{
            flex: 2;
            font-weight: 600;
        }}
        
        .bar-container {{
            flex: 5;
            height: 20px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }}
        
        .bar {{
            height: 100%;
            background-color: #3498db;
            border-radius: 10px;
            transition: width 1s ease-out;
        }}
        
        .stat-value {{
            flex: 1;
            text-align: right;
        }}
        
        /* Media Queries */
        @media (max-width: 768px) {{
            .slide-content {{
                padding: 20px;
            }}
            
            .slide-title {{
                font-size: 1.8rem;
            }}
            
            .stats-container {{
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            }}
            
            table {{
                font-size: 0.9rem;
            }}
            
            th, td {{
                padding: 8px 10px;
            }}
            
            .team-comparison {{
                flex-direction: column;
                gap: 20px;
            }}
            
            .vs-container {{
                margin: 10px 0;
            }}
            
            .head-to-head-stats {{
                flex-direction: column;
            }}
        }}
        
        /* Auto-advancing animation */
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}
        
        .highlight {{
            animation: pulse 2s infinite ease-in-out;
        }}
    </style>
</head>
<body>
    <div class="slide-container">
"""
    # Generate HTML for each slide
    for i, slide in enumerate(slides):
        slide_type = slide['type']
        is_active = i == 0
        
        # Start slide div
        html_content += f"""
        <div class="slide{' active' if is_active else ''}" id="slide-{i}">
            <div class="slide-bg"></div>
"""
        
        # Add slide content based on type
        html_content += f'            <div class="slide-content">\n'
        
        if slide_type == 'title':
            html_content += f"""
                <div class="title-slide">
                    <h1>{slide['title']}</h1>
                    <h2>{slide['subtitle']}</h2>
                    <p>{slide['date']}</p>
                </div>
"""
        elif slide_type == 'points-table':
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
                <table>
                    <thead>
                        <tr>
"""
            
            # Table headers
            if slide['data']:
                for key in slide['data'][0].keys():
                    html_content += f"                            <th>{key}</th>\n"
            
            html_content += """
                        </tr>
                    </thead>
                    <tbody>
"""
            
            # Table rows
            for team in slide['data']:
                html_content += "                        <tr>\n"
                for value in team.values():
                    html_content += f"                            <td>{value}</td>\n"
                html_content += "                        </tr>\n"
            
            html_content += """
                    </tbody>
                </table>
"""
        elif slide_type == 'matches':
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
"""
            
            if slide['data']:
                for match in slide['data']:
                    team1 = match.get('Team 1', '')
                    team2 = match.get('Team 2', '')
                    venue = match.get('Venue', '')
                    match_time = match.get('Time', '')
                    match_date = match.get('Date', 'Today')
                    
                    # Get team logos if available
                    team1_logo = team_logos.get(team1.lower().replace(' ', '_'), '')
                    team2_logo = team_logos.get(team2.lower().replace(' ', '_'), '')
                    
                    # Get prediction if available
                    match_key = f"{team1} vs {team2}"
                    prediction = slide['predictions'].get(match_key, {})
                    predicted_winner = prediction.get('predicted_winner', '')
                    confidence = prediction.get('confidence', '')
                    
                    # Get venue weather and pitch if available
                    venue_weather = slide['weather_data'].get(venue, {})
                    venue_pitch = slide['pitch_data'].get(venue, {})
                    
                    html_content += f"""
                    <div class="team-comparison">
                        <div class="team-side">
                            {f'<img src="{team1_logo}" alt="{team1}" class="team-logo">' if team1_logo else ''}

                            <h3>{team1}</h3>
                        </div>
                        <div class="vs-container">
                            <div class="vs-text">VS</div>
                            <div>
                                <p><strong>{match_date}</strong></p>
                                <p><strong>Venue:</strong> {venue}</p>
                                <p><strong>Time:</strong> {match_time}</p>
                            </div>
                        </div>
                        <div class="team-side">
                            {f'<img src="{team2_logo}" alt="{team2}" class="team-logo">' if team2_logo else ''}

                            <h3>{team2}</h3>
                        </div>
                    </div>
"""
                    
                    # Add weather and pitch preview
                    if venue_weather or venue_pitch:
                        html_content += f"""
                    <div class="venue-preview" style="margin-top: 20px; text-align: center;">
                        <h4>Match Conditions Preview</h4>
                        <div style="display: flex; justify-content: center; gap: 20px; margin-top: 10px;">
"""
                        if venue_weather:
                            weather_condition = venue_weather.get('condition', 'Unknown')
                            temperature = venue_weather.get('temperature', 'N/A')
                            html_content += f"""
                            <div style="background-color: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px;">
                                <p><strong>Weather:</strong> {weather_condition}</p>
                                <p><strong>Temp:</strong> {temperature}</p>
                            </div>
"""
                        if venue_pitch:
                            pitch_type = venue_pitch.get('pitch_type', 'Unknown')
                            expected_score = venue_pitch.get('expected_first_innings_score', 'N/A')
                            html_content += f"""
                            <div style="background-color: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px;">
                                <p><strong>Pitch:</strong> {pitch_type}</p>
                                <p><strong>Expected Score:</strong> {expected_score}</p>
                            </div>
"""
                        html_content += """
                        </div>
                    </div>
"""
                    
                    if predicted_winner:
                        html_content += f"""
                    <div class="prediction-text">
                        Prediction: {predicted_winner} to win{f' ({confidence}% confidence)' if confidence else ''}

                    </div>
"""
            else:
                html_content += "<p>No matches scheduled for today</p>"
                
        elif slide_type == 'detailed-team-comparison':
            team1 = slide['team1']
            team2 = slide['team2']
            match_data = slide['match_data']
            prediction = slide['prediction']
            head_to_head = slide['head_to_head']
            
            # Get team logos if available
            team1_logo = team_logos.get(team1.lower().replace(' ', '_'), '')
            team2_logo = team_logos.get(team2.lower().replace(' ', '_'), '')
            
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
                <div class="team-comparison">
                    <div class="team-side">
                        {f'<img src="{team1_logo}" alt="{team1}" class="team-logo">' if team1_logo else ''}

                        <h3>{team1}</h3>
                        <p><strong>Form:</strong> {match_data.get('Team 1 Form', 'N/A')}</p>
                    </div>
                    <div class="vs-container">
                        <div class="vs-text">VS</div>
                        <div>
                            <p><strong>Venue:</strong> {match_data.get('Venue', 'TBD')}</p>
                            <p><strong>Time:</strong> {match_data.get('Time', 'TBD')}</p>
                        </div>
                    </div>
                    <div class="team-side">
                        {f'<img src="{team2_logo}" alt="{team2}" class="team-logo">' if team2_logo else ''}

                        <h3>{team2}</h3>
                        <p><strong>Form:</strong> {match_data.get('Team 2 Form', 'N/A')}</p>
                    </div>
                </div>
                
                <div class="head-to-head">
                    <h3>Head to Head Statistics</h3>
                    <div class="head-to-head-stats">
"""
            
            # Add head to head statistics
            if head_to_head:
                total_matches = head_to_head.get('total_matches', 0)
                team1_wins = head_to_head.get(f'{team1}_wins', 0)
                team2_wins = head_to_head.get(f'{team2}_wins', 0)
                
                html_content += f"""
                        <div>
                            <div class="stat-value">{total_matches}</div>
                            <div class="stat-label">Total Matches</div>
                        </div>
                        <div>
                            <div class="stat-value">{team1_wins}</div>
                            <div class="stat-label">{team1} Wins</div>
                        </div>
                        <div>
                            <div class="stat-value">{team2_wins}</div>
                            <div class="stat-label">{team2} Wins</div>
                        </div>
"""
                
                # Add more detailed head to head stats if available
                if 'last_encounter' in head_to_head:
                    last_encounter = head_to_head['last_encounter']
                    html_content += f"""
                        <div>
                            <div class="stat-value">{last_encounter.get('winner', 'N/A')}</div>
                            <div class="stat-label">Last Winner</div>
                        </div>
"""
            else:
                html_content += """
                        <div>No head to head data available</div>
"""
            
            html_content += """
                    </div>
                </div>
"""
            
            # Add prediction
            if prediction:
                predicted_winner = prediction.get('predicted_winner', '')
                confidence = prediction.get('confidence', '')
                
                if predicted_winner:
                    html_content += f"""
                <div class="prediction-text">
                    Match Prediction: {predicted_winner} to win{f' ({confidence}% confidence)' if confidence else ''}

                </div>
"""
                    
                    # Add key factors if available
                    if 'key_factors' in prediction:
                        html_content += """
                <div style="margin-top: 20px;">
                    <h3>Key Factors:</h3>
                    <ul>
"""
                        for factor in prediction['key_factors']:
                            html_content += f"                        <li>{factor}</li>\n"
                        html_content += """
                    </ul>
                </div>
"""
        
        elif slide_type == 'overall-comparison':
            team1 = slide['team1']
            team2 = slide['team2']
            team1_data = slide['team1_data']
            team2_data = slide['team2_data']
            team1_logo = slide.get('logo1', '')
            team2_logo = slide.get('logo2', '')
            
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
                <div class="team-comparison">
                    <div class="team-side">
                        {f'<img src="{team1_logo}" alt="{team1}" class="team-logo">' if team1_logo else ''}

                        <h3>{team1}</h3>
                    </div>
                    <div class="vs-container">
                        <div class="vs-text">VS</div>
                    </div>
                    <div class="team-side">
                        {f'<img src="{team2_logo}" alt="{team2}" class="team-logo">' if team2_logo else ''}

                        <h3>{team2}</h3>
                    </div>
                </div>
                
                <div style="margin-top: 30px;">
                    <h3 style="text-align: center; margin-bottom: 20px;">Team Performance Comparison</h3>
"""
            
            # Extract team stats for comparison
            team1_stats = team1_data.get('stats', {})
            team2_stats = team2_data.get('stats', {})
            
            # Define stats to compare and their labels
            stats_to_compare = [
                ('win_percentage', 'Win Percentage'),
                ('batting_avg', 'Batting Average'),
                ('bowling_avg', 'Bowling Average'),
                ('net_run_rate', 'Net Run Rate'),
                ('avg_score', 'Average Score'),
                ('powerplay_runs', 'Powerplay Runs'),
                ('death_over_runs', 'Death Over Runs')
            ]
            
            for stat_key, stat_label in stats_to_compare:
                team1_value = team1_stats.get(stat_key, 0)
                team2_value = team2_stats.get(stat_key, 0)
                
                # Skip if both teams have no data for this stat
                if team1_value == 0 and team2_value == 0:
                    continue
                
                # Calculate percentages for the bar chart (make sure we don't divide by zero)
                max_value = max(team1_value, team2_value) if max(team1_value, team2_value) > 0 else 1
                team1_percent = (team1_value / max_value) * 100
                team2_percent = (team2_value / max_value) * 100
                
                html_content += f"""
                    <div style="margin-bottom: 20px;">
                        <h4 style="margin-bottom: 10px;">{stat_label}</h4>
                        <div class="comparison-bars">
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="width: 100px; text-align: right; padding-right: 10px;">{team1}</span>
                                <div style="flex-grow: 1; background-color: rgba(255,255,255,0.1); height: 20px; border-radius: 10px; overflow: hidden;">
                                    <div style="width: {team1_percent}%; height: 100%; background-color: #3498db; border-radius: 10px;"></div>
                                </div>
                                <span style="width: 60px; text-align: left; padding-left: 10px;">{team1_value}</span>
                            </div>
                            <div style="display: flex; align-items: center;">
                                <span style="width: 100px; text-align: right; padding-right: 10px;">{team2}</span>
                                <div style="flex-grow: 1; background-color: rgba(255,255,255,0.1); height: 20px; border-radius: 10px; overflow: hidden;">
                                    <div style="width: {team2_percent}%; height: 100%; background-color: #e74c3c; border-radius: 10px;"></div>
                                </div>
                                <span style="width: 60px; text-align: left; padding-left: 10px;">{team2_value}</span>
                            </div>
                        </div>
                    </div>
"""
            
            # Close the stats comparison div
            html_content += """
                </div>
"""
            
        elif slide_type == 'venue-conditions':
            venue = slide['venue']
            weather = slide['weather']
            pitch = slide['pitch']
            matches = slide['matches']
            
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
                
                <div class="venue-conditions">
"""
            
            # Weather conditions
            if weather:
                html_content += f"""
                    <div class="condition-box">
                        <h3>Weather Conditions</h3>
                        <div style="text-align: center; margin: 15px 0;">
                            <div style="font-size: 3rem; margin-bottom: 10px;">
                                {get_weather_icon(weather.get('condition', 'Unknown'))}
                            </div>
                            <div style="font-size: 1.5rem; font-weight: bold;">{weather.get('condition', 'Unknown')}</div>
                        </div>
                        
                        <div class="weather-details">
"""
                
                # Add weather details
                for key, label in [
                    ('temperature', 'Temperature'),
                    ('humidity', 'Humidity'),
                    ('wind_speed', 'Wind Speed'),
                    ('precipitation', 'Precipitation'),
                    ('forecast', 'Forecast')
                ]:
                    if key in weather:
                        html_content += f"""
                            <div class="detail-row">
                                <span class="detail-label">{label}</span>
                                <span>{weather[key]}</span>
                            </div>
"""
                
                html_content += """
                        </div>
                    </div>
"""
            
            # Pitch conditions
            if pitch:
                html_content += f"""
                    <div class="condition-box">
                        <h3>Pitch Report</h3>
                        
                        <div class="pitch-details">
"""
                
                # Add pitch details
                for key, label in [
                    ('pitch_type', 'Pitch Type'),
                    ('expected_first_innings_score', 'Expected First Innings Score'),
                    ('expected_second_innings_score', 'Expected Second Innings Score'),
                    ('pitch_behavior', 'Pitch Behavior'),
                    ('bowling_advantage', 'Bowling Advantage'),
                    ('toss_decision', 'Toss Decision'),
                    ('average_score_at_venue', 'Average Score at Venue')
                ]:
                    if key in pitch:
                        html_content += f"""
                            <div class="detail-row">
                                <span class="detail-label">{label}</span>
                                <span>{pitch[key]}</span>
                            </div>
"""
                
                html_content += """
                        </div>
                    </div>
"""
            
            # Close venue conditions div
            html_content += """
                </div>
"""
            
            # Add matches at this venue
            if matches:
                html_content += f"""
                <div style="margin-top: 30px;">
                    <h3 style="text-align: center; margin-bottom: 15px;">Matches at {venue}</h3>
                    <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px;">
"""
                
                for match in matches:
                    team1 = match.get('Team 1', '')
                    team2 = match.get('Team 2', '')
                    match_time = match.get('Time', '')
                    match_date = match.get('Date', 'Today')
                    
                    html_content += f"""
                        <div style="background-color: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; min-width: 300px; text-align: center;">
                            <p><strong>{team1} vs {team2}</strong></p>
                            <p>{match_date} at {match_time}</p>
                        </div>
"""
                
                html_content += """
                    </div>
                </div>
"""
                
        elif slide_type == 'team-overview':
            team_name = slide['team']
            team_data = slide['data']
            team_logo = slide.get('logo', '')
            
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
                
                <div class="team-overview">
                    <div class="team-header">
                        {f'<img src="{team_logo}" alt="{team_name}" class="team-logo" style="margin-right: 20px;">' if team_logo else ''}

                        <h3>{team_name}</h3>
                    </div>
"""
            
            # Team stats
            team_stats = team_data.get('stats', {})
            if team_stats:
                html_content += """
                    <div class="team-stats-grid">
"""
                
                # Add team stats cards
                for key, label in [
                    ('win_percentage', 'Win Percentage'),
                    ('matches_played', 'Matches Played'),
                    ('matches_won', 'Matches Won'),
                    ('batting_avg', 'Batting Average'),
                    ('bowling_avg', 'Bowling Average'),
                    ('net_run_rate', 'Net Run Rate'),
                    ('avg_score', 'Average Score'),
                    ('powerplay_runs', 'Powerplay Runs'),
                    ('death_over_runs', 'Death Over Runs')
                ]:
                    if key in team_stats:
                        html_content += f"""
                        <div class="team-stat-card">
                            <div class="team-stat-value">{team_stats[key]}</div>
                            <div class="team-stat-label">{label}</div>
                        </div>
"""
                
                html_content += """
                    </div>
"""
            
            # Team squad
            squad = team_data.get('squad', [])
            if squad:
                html_content += """
                    <div style="margin-top: 30px; width: 100%;">
                        <h3 style="text-align: center; margin-bottom: 15px;">Key Players</h3>
                        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px;">
"""
                
                # Show up to 8 key players
                for player in squad[:8]:
                    player_name = player.get('Player', 'Unknown')
                    player_role = player.get('Role', '')
                    player_country = player.get('Country', '')
                    
                    html_content += f"""
                            <div style="background-color: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; min-width: 200px; text-align: center;">
                                <p style="font-weight: bold; font-size: 1.1rem;">{player_name}</p>
                                <p>{player_role}</p>
                                {f'<p>{player_country}</p>' if player_country else ''}
                            </div>
"""
                
                html_content += """
                        </div>
                    </div>
"""
            
            # Close team overview div
            html_content += """
                </div>
"""
            
        elif slide_type == 'stat-leaders':
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
                <div class="stats-container">
"""
            
            # Player stats
            for player in slide['data']:
                # Determine key stat to display
                stat_value = ""
                if slide['category'] == 'batting':
                    if 'Runs' in player:
                        stat_value = f"{player['Runs']} runs"
                    elif '4s' in player:
                        stat_value = f"{player['4s']} fours"
                    elif '6s' in player:
                        stat_value = f"{player['6s']} sixes"
                    elif '50s' in player:
                        stat_value = f"{player['50s']} fifties"
                    elif '100s' in player:
                        stat_value = f"{player['100s']} hundreds"
                elif slide['category'] == 'bowling':
                    if 'Wkts' in player:
                        stat_value = f"{player['Wkts']} wickets"
                    elif 'Econ' in player:
                        stat_value = f"{player['Econ']} economy"
                    elif 'Avg' in player:
                        stat_value = f"{player['Avg']} average"
                    elif 'SR' in player:
                        stat_value = f"{player['SR']} strike rate"
                
                player_name = player.get('Player', '')
                team = player.get('Team', '')
                
                html_content += f"""
                    <div class="stat-card">
                        <div class="player-name">{player_name}</div>
                        <div class="player-team">{team}</div>
                        <div class="player-stat">{stat_value}</div>
                    </div>
"""
            
            html_content += """
                </div>
"""
        elif slide_type == 'player-gallery':
            html_content += f"""
                <h2 class="slide-title">{slide['title']}</h2>
                <div class="player-gallery">
"""
            
            for player in slide['players']:
                html_content += f"""
                    <div class="player-card">
                        <img src="{player['image']}" alt="{player['name']}" class="player-image">
                        <div class="player-card-details">
                            <div class="player-card-name">{player['name']}</div>
                            <div class="player-card-team">{player['team']}</div>
                        </div>
                    </div>
"""
            
            html_content += """
                </div>
"""
        
        # Close slide content div
        html_content += '            </div>\n'
        
        # Close slide div
        html_content += '        </div>\n'
    
    # Add navigation controls
    html_content += """
        <div class="slide-controls">
            <button class="prev-btn">Previous</button>
            <button class="next-btn">Next</button>
        </div>
        
        <div class="slide-indicators">
"""
    
    for i in range(len(slides)):
        html_content += f'            <div class="indicator{" active" if i == 0 else ""}" data-slide="{i}"></div>\n'
    
    html_content += """
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Variables
            const slides = document.querySelectorAll('.slide');
            const prevBtn = document.querySelector('.prev-btn');
            const nextBtn = document.querySelector('.next-btn');
            const indicators = document.querySelectorAll('.indicator');
            let currentSlide = 0;
            let slideshowInterval;
            let isAutoSliding = true;
            const slideDuration = 10000; // 10 seconds per slide
            
            // Set dynamic backgrounds for slides
            slides.forEach((slide, index) => {
                const colors = [
                    'linear-gradient(45deg, #1a237e, #283593)', 
                    'linear-gradient(45deg, #004d40, #00695c)',
                    'linear-gradient(45deg, #b71c1c, #c62828)',
                    'linear-gradient(45deg, #4a148c, #6a1b9a)',
                    'linear-gradient(45deg, #e65100, #ef6c00)',
                    'linear-gradient(45deg, #880e4f, #ad1457)'
                ];
                
                slide.querySelector('.slide-bg').style.background = colors[index % colors.length];
            });
            
            // Function to show a specific slide
            function showSlide(n) {
                // Validate slide index
                if (n >= slides.length) {
                    currentSlide = 0;
                } else if (n < 0) {
                    currentSlide = slides.length - 1;
                } else {
                    currentSlide = n;
                }
                
                // Update slide classes
                slides.forEach((slide, index) => {
                    if (index < currentSlide) {
                        slide.className = 'slide prev';
                    } else if (index === currentSlide) {
                        slide.className = 'slide active';
                    } else {
                        slide.className = 'slide';
                    }
                });
                
                // Update indicators
                indicators.forEach((indicator, index) => {
                    indicator.classList.toggle('active', index === currentSlide);
                });
                
                // Reset slideshow timer when manually changing slides
                resetSlideshow();
            }
            
            // Function to go to the next slide
            function nextSlide() {
                showSlide(currentSlide + 1);
            }
            
            // Function to go to the previous slide
            function prevSlide() {
                showSlide(currentSlide - 1);
            }
            
            // Function to start automatic slideshow
            function startSlideshow() {
                isAutoSliding = true;
                slideshowInterval = setInterval(nextSlide, slideDuration);
            }
            
            // Function to reset slideshow timer
            function resetSlideshow() {
                clearInterval(slideshowInterval);
                startSlideshow();
            }
            
            // Function to pause slideshow
            function pauseSlideshow() {
                isAutoSliding = false;
                clearInterval(slideshowInterval);
            }
            
            // Event listeners
            nextBtn.addEventListener('click', function() {
                nextSlide();
            });
            
            prevBtn.addEventListener('click', function() {
                prevSlide();
            });
            
            indicators.forEach((indicator, index) => {
                indicator.addEventListener('click', function() {
                    showSlide(index);
                });
            });
            
            // Keyboard navigation
            document.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowRight') {
                    nextSlide();
                } else if (e.key === 'ArrowLeft') {
                    prevSlide();
                } else if (e.key === 'Escape') {
                    if (isAutoSliding) {
                        pauseSlideshow();
                    } else {
                        startSlideshow();
                    }
                }
            });
            
            // Pause slideshow when user interacts with the page
            document.addEventListener('mousemove', function() {
                pauseSlideshow();
                
                // Resume after inactivity
                clearTimeout(window.resumeTimeout);
                window.resumeTimeout = setTimeout(startSlideshow, 30000); // Resume after 30 seconds of inactivity
            });
            
            // Touch swipe functionality
            let touchStartX = 0;
            let touchEndX = 0;
            
            document.addEventListener('touchstart', function(e) {
                touchStartX = e.changedTouches[0].screenX;
            }, false);
            
            document.addEventListener('touchend', function(e) {
                touchEndX = e.changedTouches[0].screenX;
                handleSwipe();
            }, false);
            
            function handleSwipe() {
                if (touchEndX < touchStartX - 50) {
                    nextSlide(); // Swipe left
                } else if (touchEndX > touchStartX + 50) {
                    prevSlide(); // Swipe right
                }
            }
            
            // Start slideshow
            startSlideshow();
        });
    </script>
</body>
</html>
"""
    
    # Write HTML to file
    ensure_slides_directory()
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Slides HTML generated successfully: {output_path}")
    return output_path

def get_weather_icon(condition):
    """Return a simple HTML/CSS icon for weather condition."""
    condition = condition.lower()
    
    if 'sunny' in condition or 'clear' in condition:
        return '☀️'
    elif 'cloud' in condition:
        if 'partly' in condition:
            return '⛅'
        else:
            return '☁️'
    elif 'rain' in condition or 'shower' in condition:
        if 'light' in condition:
            return '🌦️'
        else:
            return '🌧️'
    elif 'thunder' in condition or 'storm' in condition:
        return '⛈️'
    elif 'snow' in condition:
        return '❄️'
    elif 'fog' in condition or 'mist' in condition:
        return '🌫️'
    elif 'wind' in condition:
        return '💨'
    else:
        return '🌡️'

# Add main execution block
if __name__ == "__main__":
    args = parse_arguments()
    output_path = generate_slides_html(args)
    print(f"Slides generated successfully at: {output_path}")
