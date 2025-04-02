#!/usr/bin/env python3
"""
IPL Cricket Pre-Match Analysis Slides Generator

This script generates HTML slides for IPL cricket pre-match analysis using:
1. Local data from various scrapers
2. Gemini API for intelligent analysis and insights
3. Customizable templates for different slide types

The slides can be customized for different teams, matches, and presentation styles.
"""

import os
import json
import datetime
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional, Union
import re
from datetime import datetime
import pandas as pd  # Add pandas for CSV data handling

# Import Gemini API
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ipl_slides_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Constants
TEMPLATE_DIR = Path("slide_templates")
PARTIALS_DIR = TEMPLATE_DIR / "partials"
OUTPUT_DIR = Path("ipl_slides")
TEAM_DATA_DIR = Path("team_data")
PLAYER_IMAGES_DIR = Path("player_images")
VENUE_IMAGES_DIR = Path("venue_images")
POINTS_TABLE_DIR = Path("points_table")
BATTING_STATS_DIR = Path("batting_stats")
BOWLING_STATS_DIR = Path("bowling_stats")
WEATHER_REPORTS_DIR = Path("weather_reports")
PITCH_REPORTS_DIR = Path("pitch_reports")
MATCHES_DIR = Path("matches")

# Team colors for styling
TEAM_COLORS = {
    "CSK": {
        "primary": "#FFCC00",
        "secondary": "#0081E5",
        "gradient": "linear-gradient(45deg, #FFCC00, #0081E5)",
        "text": "#000000"
    },
    "MI": {
        "primary": "#003B7A",
        "secondary": "#68BFFF",
        "gradient": "linear-gradient(45deg, #003B7A, #68BFFF)",
        "text": "#FFFFFF"
    },
    "RCB": {
        "primary": "#EC1C24",
        "secondary": "#000000",
        "gradient": "linear-gradient(45deg, #EC1C24, #000000)",
        "text": "#FFFFFF"
    },
    "KKR": {
        "primary": "#3A225D",
        "secondary": "#D4AF37",
        "gradient": "linear-gradient(45deg, #3A225D, #D4AF37)",
        "text": "#FFFFFF"
    },
    "DC": {
        "primary": "#0078BC",
        "secondary": "#EF1C25",
        "gradient": "linear-gradient(45deg, #0078BC, #EF1C25)",
        "text": "#FFFFFF"
    },
    "PBKS": {
        "primary": "#ED1B24",
        "secondary": "#A7A9AC",
        "gradient": "linear-gradient(45deg, #ED1B24, #A7A9AC)",
        "text": "#FFFFFF"
    },
    "RR": {
        "primary": "#254AA5",
        "secondary": "#FF4F81",
        "gradient": "linear-gradient(45deg, #254AA5, #FF4F81)",
        "text": "#FFFFFF"
    },
    "SRH": {
        "primary": "#FF822A",
        "secondary": "#000000",
        "gradient": "linear-gradient(45deg, #FF822A, #000000)",
        "text": "#FFFFFF"
    },
    "GT": {
        "primary": "#1C1C1C",
        "secondary": "#0085CA",
        "gradient": "linear-gradient(45deg, #1C1C1C, #0085CA)",
        "text": "#FFFFFF"
    },
    "LSG": {
        "primary": "#A5E0E5",
        "secondary": "#353E94",
        "gradient": "linear-gradient(45deg, #A5E0E5, #353E94)",
        "text": "#000000"
    }
}

# Map of full team names to abbreviations
TEAM_ABBREVIATIONS = {
    "Chennai Super Kings": "CSK",
    "Mumbai Indians": "MI",
    "Royal Challengers Bengaluru": "RCB",
    "Kolkata Knight Riders": "KKR",
    "Delhi Capitals": "DC",
    "Punjab Kings": "PBKS",
    "Rajasthan Royals": "RR",
    "Sunrisers Hyderabad": "SRH",
    "Gujarat Titans": "GT",
    "Lucknow Super Giants": "LSG"
}


class IPLSlidesGenerator:
    """
    Generates HTML slides for IPL cricket pre-match analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the IPL Slides Generator.
        
        Args:
            config: Optional configuration dictionary to override defaults
        """
        self.config = config or {}
        self.setup_gemini_api()
        self.templates = self.load_templates()
        self.partials = self.load_partials()
        self.today = datetime.now().strftime("%Y%m%d")
        self.slide_index = 0
        self.slides_content = []
        
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(exist_ok=True)
        
    def setup_gemini_api(self):
        """Set up the Gemini API with API key from environment variables."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables. Gemini API features will be disabled.")
            self.gemini_enabled = False
            return
            
        # Configure Gemini API
        genai.configure(api_key=api_key)
        
        # Try to initialize with Gemini 2.0 Flash
        try:
            # Attempt to create the Gemini 2.0 Flash model
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Test with a simple prompt to verify it works
            response = self.model.generate_content("Hello")
            self.gemini_enabled = True
            logger.info("Gemini API initialized successfully with gemini-2.0-flash model")
        except Exception as e:
            logger.warning(f"Failed to initialize gemini-2.0-flash model: {e}")
            
            # Fallback to other model versions
            fallback_models = [
                'gemini-1.5-flash',
                'gemini-pro',
                'gemini-1.0-pro'
            ]
            
            for model_name in fallback_models:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    response = self.model.generate_content("Hello")
                    self.gemini_enabled = True
                    logger.info(f"Gemini API initialized successfully with {model_name} model")
                    break
                except Exception as e:
                    logger.warning(f"Failed to initialize {model_name} model: {e}")
            
            if not self.gemini_enabled:
                logger.error("Failed to initialize any Gemini model. AI analysis will be unavailable.")
    
    def get_gemini_analysis(self, prompt: str) -> str:
        """
        Get analysis from Gemini API.
        
        Args:
            prompt: Prompt to send to Gemini API
            
        Returns:
            Response from Gemini API or a placeholder message if API is disabled
        """
        if not self.gemini_enabled:
            return "AI analysis not available. The slide generator couldn't connect to the Gemini API."
            
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error getting Gemini analysis: {e}")
            # Return a reasonable placeholder instead of error message
            return "AI-powered analysis couldn't be generated due to API connection issues."
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template to render
            context: Context data for the template
            
        Returns:
            Rendered template as a string
        """
        if template_name not in self.templates:
            logger.error(f"Template '{template_name}' not found")
            return ""
            
        template = self.templates[template_name]
        
        # Simple template rendering using string replacement
        for key, value in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
            
        return template
    
    def render_partial(self, partial_name: str, context: Dict[str, Any]) -> str:
        """
        Render a partial template with the given context.
        
        Args:
            partial_name: Name of the partial template to render
            context: Context data for the partial template
            
        Returns:
            Rendered partial template as a string
        """
        if partial_name not in self.partials:
            logger.error(f"Partial template '{partial_name}' not found")
            return ""
            
        partial = self.partials[partial_name]
        
        # Simple template rendering using string replacement
        for key, value in context.items():
            partial = partial.replace(f"{{{{{key}}}}}", str(value))
            
        return partial
    
    def add_title_slide(self, title: str, subtitle: str, date: str):
        """
        Add a title slide to the presentation.
        
        Args:
            title: Main title for the slide
            subtitle: Subtitle for the slide
            date: Date to display on the slide
        """
        context = {
            "slide_index": self.slide_index,
            "main_title": title,
            "subtitle": subtitle,
            "date": date
        }
        
        rendered_slide = self.render_template("title_slide", context)
        self.slides_content.append(rendered_slide)
        self.slide_index += 1
        
    def add_points_table_slide(self):
        """Add a points table slide to the presentation."""
        # Get the latest points table data
        points_table_files = list(POINTS_TABLE_DIR.glob(f"*_{self.today}.json"))
        if not points_table_files:
            # If no data for today, use the most recent data
            points_table_files = sorted(list(POINTS_TABLE_DIR.glob("*.json")), key=lambda x: x.stem.split("_")[-1], reverse=True)
            
        if not points_table_files:
            logger.warning("No points table data found")
            return
            
        points_table_data = self.load_json_data(points_table_files[0])
        
        # Generate the points table rows HTML
        points_table_rows = ""
        for team in points_table_data.get("teams", []):
            row = f"""
            <tr>
                <td>{team.get('position', '')}</td>
                <td><img src="{team.get('logo', '')}" class="team-logo" alt="{team.get('name', '')}"></td>
                <td>{team.get('name', '')}</td>
                <td>{team.get('played', '')}</td>
                <td>{team.get('won', '')}</td>
                <td>{team.get('lost', '')}</td>
                <td>{team.get('nr', '0')}</td>
                <td>{team.get('nrr', '')}</td>
                <td>{team.get('for', '')}</td>
                <td>{team.get('against', '')}</td>
                <td>{team.get('points', '')}</td>
                <td>{team.get('form', '')}</td>
            </tr>
            """
            points_table_rows += row
            
        context = {
            "slide_index": self.slide_index,
            "points_table_rows": points_table_rows
        }
        
        rendered_slide = self.render_template("points_table_slide", context)
        self.slides_content.append(rendered_slide)
        self.slide_index += 1
        
    def add_player_stats_slide(self, stats_title: str, stats_type: str, unit: str = ""):
        """
        Add a player stats slide to the presentation.
        
        Args:
            stats_title: Title for the slide
            stats_type: Type of stats (e.g., most-runs, most-wickets)
            unit: Unit for the stats (e.g., runs, wickets)
        """
        # Determine the directory based on the stats type
        if any(stat in stats_type for stat in ["runs", "4s", "6s", "fifties", "hundreds"]):
            stats_dir = BATTING_STATS_DIR
        else:
            stats_dir = BOWLING_STATS_DIR
            
        # Get the latest stats data
        stats_files = list(stats_dir.glob(f"ipl_{stats_type}_{self.today}.json"))
        if not stats_files:
            # If no data for today, use the most recent data
            stats_files = sorted(list(stats_dir.glob(f"ipl_{stats_type}_*.json")), key=lambda x: x.stem.split("_")[-1], reverse=True)
            
        if not stats_files:
            logger.warning(f"No {stats_type} data found")
            return
            
        stats_data = self.load_json_data(stats_files[0])
        
        # Generate the player stats cards HTML
        player_stats_cards = ""
        for player in stats_data.get("players", [])[:5]:  # Show top 5 players
            context = {
                "player_name": player.get("name", ""),
                "player_team": player.get("team", ""),
                "player_stat_value": player.get("value", ""),
                "player_stat_unit": unit
            }
            player_stats_cards += self.render_partial("stats_card", context)
            
        context = {
            "slide_index": self.slide_index,
            "stats_title": stats_title,
            "player_stats_cards": player_stats_cards
        }
        
        rendered_slide = self.render_template("player_stats_slide", context)
        self.slides_content.append(rendered_slide)
        self.slide_index += 1
            
    def add_team_overview_slide(self, team_name: str):
        """
        Add a team overview slide to the presentation.
        
        Args:
            team_name: Name of the team
        """
        # Get team data
        team_abbr = TEAM_ABBREVIATIONS.get(team_name, team_name)
        team_data_file = TEAM_DATA_DIR / f"{team_abbr.lower()}_profile.json"
        
        if not team_data_file.exists():
            logger.warning(f"No team data found for {team_name}")
            return
            
        team_data = self.load_json_data(team_data_file)
        
        # Generate team stats HTML
        team_stats = ""
        for stat_name, stat_value in team_data.get("statistics", {}).items():
            stat_html = f"""
            <div class="team-stat-card">
                <div class="team-stat-value">{stat_value}</div>
                <div class="team-stat-label">{stat_name}</div>
            </div>
            """
            team_stats += stat_html
            
        # Generate key players HTML
        key_players = ""
        for player in team_data.get("key_players", [])[:4]:  # Show top 4 key players
            context = {
                "player_name": player.get("name", ""),
                "player_role": player.get("role", ""),
                "player_stat1_label": player.get("key_stat1_name", ""),
                "player_stat1_value": player.get("key_stat1_value", ""),
                "player_stat2_label": player.get("key_stat2_name", ""),
                "player_stat2_value": player.get("key_stat2_value", "")
            }
            key_players += self.render_partial("key_player_card", context)
            
        context = {
            "slide_index": self.slide_index,
            "team_name": team_name,
            "team_logo": team_data.get("logo", ""),
            "team_stats": team_stats,
            "key_players": key_players
        }
        
        rendered_slide = self.render_template("team_overview_slide", context)
        self.slides_content.append(rendered_slide)
        self.slide_index += 1
    
    def add_venue_pitch_slide(self, venue_name: str):
        """
        Add a venue and pitch conditions slide to the presentation.
        
        Args:
            venue_name: Name of the venue
        """
        # Get venue pitch report and weather data
        pitch_report_file = PITCH_REPORTS_DIR / f"{venue_name.lower().replace(' ', '_')}_{self.today}.json"
        weather_report_file = WEATHER_REPORTS_DIR / f"{venue_name.lower().replace(' ', '_')}_{self.today}.json"
        
        pitch_data = self.load_json_data(pitch_report_file) if pitch_report_file.exists() else {}
        weather_data = self.load_json_data(weather_report_file) if weather_report_file.exists() else {}
        
        # If we don't have today's data, get Gemini to analyze historical data
        if not pitch_data or not weather_data:
            pitch_analysis = self.get_gemini_analysis(
                f"Analyze cricket pitch conditions at {venue_name} for IPL matches. "
                f"Include details about the surface, bounce, average first innings score, "
                f"toss decision preference, and whether it favors batsmen or bowlers."
            )
        else:
            pitch_analysis = pitch_data.get("summary", "No pitch analysis available.")
            
        # Calculate venue statistics
        total_games = pitch_data.get("total_matches", 0)
        batting_first_wins = pitch_data.get("batting_first_wins", 0)
        chasing_wins = pitch_data.get("chasing_wins", 0)
        
        if total_games > 0:
            batting_first_win_percent = (batting_first_wins / total_games) * 100
            chasing_win_percent = (chasing_wins / total_games) * 100
        else:
            batting_first_win_percent = 0
            chasing_win_percent = 0
            
        # Get Gemini to provide match insight based on pitch and weather
        gemini_venue_analysis = self.get_gemini_analysis(
            f"Provide a concise analysis of how the pitch and weather conditions at {venue_name} "
            f"might affect the upcoming IPL match. Weather: {weather_data.get('summary', 'Unknown')}. "
            f"Pitch conditions: {pitch_data.get('surface', 'Unknown')}. "
            f"Suggest which team might have an advantage and key players who could excel in these conditions."
        )
            
        context = {
            "slide_index": self.slide_index,
            "venue_name": venue_name,
            "weather_icon": weather_data.get("icon", "☀️"),
            "temperature": weather_data.get("temperature", "N/A"),
            "humidity": weather_data.get("humidity", "N/A"),
            "wind_speed": weather_data.get("wind_speed", "N/A"),
            "rain_chance": weather_data.get("precipitation", "N/A"),
            "pitch_surface": pitch_data.get("surface", "N/A"),
            "pitch_bounce": pitch_data.get("bounce", "N/A"),
            "avg_first_innings": pitch_data.get("avg_first_innings", "N/A"),
            "toss_decision": pitch_data.get("toss_decision", "N/A"),
            "pitch_favors": pitch_data.get("favors", "N/A"),
            "pitch_summary": pitch_analysis,
            "batting_first_wins": batting_first_wins,
            "chasing_wins": chasing_wins,
            "total_games": total_games,
            "batting_first_win_percent": batting_first_win_percent,
            "chasing_win_percent": chasing_win_percent,
            "gemini_venue_analysis": gemini_venue_analysis
        }
        
        rendered_slide = self.render_template("venue_pitch_slide", context)
        self.slides_content.append(rendered_slide)
        self.slide_index += 1
    
    def add_match_comparison_slide(self, team1: str, team2: str, venue: str, match_time: str):
        """
        Add a match comparison slide to the presentation.
        
        Args:
            team1: Name of the first team
            team2: Name of the second team
            venue: Name of the venue
            match_time: Time of the match
        """
        # Get team data
        team1_abbr = TEAM_ABBREVIATIONS.get(team1, team1)
        team2_abbr = TEAM_ABBREVIATIONS.get(team2, team2)
        
        team1_data_file = TEAM_DATA_DIR / f"{team1_abbr.lower()}_profile.json"
        team2_data_file = TEAM_DATA_DIR / f"{team2_abbr.lower()}_profile.json"
        
        team1_data = self.load_json_data(team1_data_file) if team1_data_file.exists() else {}
        team2_data = self.load_json_data(team2_data_file) if team2_data_file.exists() else {}
        
        # Get head-to-head data
        head_to_head_file = MATCHES_DIR / f"{team1_abbr.lower()}_{team2_abbr.lower()}_h2h.json"
        if not head_to_head_file.exists():
            head_to_head_file = MATCHES_DIR / f"{team2_abbr.lower()}_{team1_abbr.lower()}_h2h.json"
            
        h2h_data = self.load_json_data(head_to_head_file) if head_to_head_file.exists() else {}
        
        # If we don't have head-to-head data, get Gemini to generate it
        if not h2h_data:
            total_matches = 0
            team1_wins = 0
            team2_wins = 0
            
            h2h_analysis = self.get_gemini_analysis(
                f"Provide head-to-head statistics between {team1} and {team2} in IPL cricket. "
                f"Include total matches played, number of wins for each team, and recent form."
            )
            
            # Try to extract numbers from the analysis
            matches_match = re.search(r"(\d+)\s+matches", h2h_analysis)
            team1_wins_match = re.search(fr"({team1}|{team1_abbr}).*?(\d+)\s+wins", h2h_analysis)
            team2_wins_match = re.search(fr"({team2}|{team2_abbr}).*?(\d+)\s+wins", h2h_analysis)
            
            if matches_match:
                total_matches = int(matches_match.group(1))
            if team1_wins_match:
                team1_wins = int(team1_wins_match.group(2))
            if team2_wins_match:
                team2_wins = int(team2_wins_match.group(2))
        else:
            total_matches = h2h_data.get("total_matches", 0)
            team1_wins = h2h_data.get(f"{team1_abbr}_wins", 0)
            team2_wins = h2h_data.get(f"{team2_abbr}_wins", 0)
            
        # Generate batting comparison
        batting_comparison = ""
        batting_metrics = [
            ("Avg. Score", "avg_score"),
            ("Run Rate", "run_rate"),
            ("Powerplay Avg.", "powerplay_avg"),
            ("Death Overs Avg.", "death_overs_avg")
        ]
        
        for label, metric in batting_metrics:
            team1_value = team1_data.get("batting_stats", {}).get(metric, 0)
            team2_value = team2_data.get("batting_stats", {}).get(metric, 0)
            
            # Calculate percentage for bar width (max is 100%)
            max_value = max(team1_value, team2_value, 1)  # Avoid division by zero
            team1_percentage = (team1_value / max_value) * 100
            team2_percentage = (team2_value / max_value) * 100
            
            # Team 1 bar
            context = {
                "stat_name": f"{team1} {label}",
                "stat_percentage": team1_percentage,
                "stat_value": team1_value
            }
            batting_comparison += self.render_partial("comparison_bar", context)
            
            # Team 2 bar
            context = {
                "stat_name": f"{team2} {label}",
                "stat_percentage": team2_percentage,
                "stat_value": team2_value
            }
            batting_comparison += self.render_partial("comparison_bar", context)
            
        # Generate bowling comparison (similar to batting)
        bowling_comparison = ""
        bowling_metrics = [
            ("Economy Rate", "economy_rate"),
            ("Bowling Avg.", "bowling_avg"),
            ("Strike Rate", "strike_rate"),
            ("Dot Ball %", "dot_ball_percentage")
        ]
        
        for label, metric in bowling_metrics:
            team1_value = team1_data.get("bowling_stats", {}).get(metric, 0)
            team2_value = team2_data.get("bowling_stats", {}).get(metric, 0)
            
            # For bowling, lower is better for most metrics
            is_inverted = metric != "dot_ball_percentage"
            max_value = max(team1_value, team2_value, 1)
            
            if is_inverted:
                # Invert the percentages for metrics where lower is better
                team1_percentage = ((max_value - team1_value) / max_value) * 100
                team2_percentage = ((max_value - team2_value) / max_value) * 100
            else:
                team1_percentage = (team1_value / max_value) * 100
                team2_percentage = (team2_value / max_value) * 100
            
            # Team 1 bar
            context = {
                "stat_name": f"{team1} {label}",
                "stat_percentage": team1_percentage,
                "stat_value": team1_value
            }
            bowling_comparison += self.render_partial("comparison_bar", context)
            
            # Team 2 bar
            context = {
                "stat_name": f"{team2} {label}",
                "stat_percentage": team2_percentage,
                "stat_value": team2_value
            }
            bowling_comparison += self.render_partial("comparison_bar", context)
            
        # Generate form comparison
        form_comparison = ""
        form_metrics = [
            ("Last 5 Matches", "last5"),
            ("Home Win %", "home_win_percentage"),
            ("Away Win %", "away_win_percentage")
        ]
        
        for label, metric in form_metrics:
            team1_value = team1_data.get("form", {}).get(metric, 0)
            team2_value = team2_data.get("form", {}).get(metric, 0)
            
            max_value = max(team1_value, team2_value, 1)
            team1_percentage = (team1_value / max_value) * 100
            team2_percentage = (team2_value / max_value) * 100
            
            # Team 1 bar
            context = {
                "stat_name": f"{team1} {label}",
                "stat_percentage": team1_percentage,
                "stat_value": team1_value
            }
            form_comparison += self.render_partial("comparison_bar", context)
            
            # Team 2 bar
            context = {
                "stat_name": f"{team2} {label}",
                "stat_percentage": team2_percentage,
                "stat_value": team2_value
            }
            form_comparison += self.render_partial("comparison_bar", context)
            
        # Get Gemini to generate match prediction
        pitch_report_file = PITCH_REPORTS_DIR / f"{venue.lower().replace(' ', '_')}_{self.today}.json"
        weather_report_file = WEATHER_REPORTS_DIR / f"{venue.lower().replace(' ', '_')}_{self.today}.json"
        
        pitch_data = self.load_json_data(pitch_report_file) if pitch_report_file.exists() else {}
        weather_data = self.load_json_data(weather_report_file) if weather_report_file.exists() else {}
        
        match_prediction = self.get_gemini_analysis(
            f"Predict the outcome of the IPL match between {team1} and {team2} at {venue}. "
            f"Consider these factors: "
            f"1. {team1} has won {team1_wins} out of {total_matches} matches against {team2}. "
            f"2. Pitch conditions: {pitch_data.get('summary', 'Unknown')}. "
            f"3. Weather: {weather_data.get('summary', 'Unknown')}. "
            f"Based on these factors, which team has the advantage? Give a brief prediction in 1-2 sentences."
        )
            
        context = {
            "slide_index": self.slide_index,
            "team1_name": team1,
            "team2_name": team2,
            "team1_logo": team1_data.get("logo", ""),
            "team2_logo": team2_data.get("logo", ""),
            "venue": venue,
            "match_time": match_time,
            "match_prediction": match_prediction,
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "total_matches": total_matches,
            "batting_comparison": batting_comparison,
            "bowling_comparison": bowling_comparison,
            "form_comparison": form_comparison
        }
        
        rendered_slide = self.render_template("match_comparison_slide", context)
        self.slides_content.append(rendered_slide)
        self.slide_index += 1
        
    def generate_html(self) -> str:
        """
        Generate the final HTML output for all slides.
        
        Returns:
            Complete HTML document as string
        """
        # Generate indicators HTML
        indicators = ""
        for i in range(self.slide_index):
            active_class = " active" if i == 0 else ""
            indicators += f'<div class="indicator{active_class}" data-slide="{i}"></div>\n'
            
        # Generate background gradients
        background_gradients = """
            'linear-gradient(45deg, #1a237e, #283593)', 
            'linear-gradient(45deg, #004d40, #00695c)',
            'linear-gradient(45deg, #b71c1c, #c62828)',
            'linear-gradient(45deg, #4a148c, #6a1b9a)',
            'linear-gradient(45deg, #e65100, #ef6c00)',
            'linear-gradient(45deg, #880e4f, #ad1457)'
        """
        
        # Generate custom CSS for team colors if applicable
        team_specific_css = ""
        if "team1" in self.config and "team2" in self.config:
            team1 = self.config["team1"]
            team2 = self.config["team2"]
            team1_abbr = TEAM_ABBREVIATIONS.get(team1, team1)
            team2_abbr = TEAM_ABBREVIATIONS.get(team2, team2)
            
            if team1_abbr in TEAM_COLORS and team2_abbr in TEAM_COLORS:
                team1_colors = TEAM_COLORS[team1_abbr]
                team2_colors = TEAM_COLORS[team2_abbr]
                
                team_specific_css = f"""
                :root {{
                    --primary-color: {team1_colors["primary"]};
                    --secondary-color: {team2_colors["primary"]};
                    --accent-color: #f1c40f;
                    --gradient-start: {team1_colors["primary"]};
                    --gradient-mid: #333333;
                    --gradient-end: {team2_colors["primary"]};
                }}
                """
        
        # Custom JavaScript if needed
        custom_scripts = """
        // JavaScript for comparison tabs
        const tabBtns = document.querySelectorAll('.comparison-tab');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                
                // Update active tab button
                tabBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                // Update active content
                const contents = document.querySelectorAll('.comparison-content');
                contents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === tabName) {
                        content.classList.add('active');
                    }
                });
            });
        });
        """
        
        # Combine all slides content
        all_slides = "".join(self.slides_content)
        
        # Prepare the context for the base template
        today_date = datetime.now().strftime("%Y-%m-%d")
        context = {
            "title": f"IPL Cricket Analysis - {today_date}",
            "slides_content": all_slides,
            "indicators": indicators,
            "background_gradients": background_gradients,
            "team_specific_css": team_specific_css,
            "custom_scripts": custom_scripts
        }
        
        # Render the base template
        return self.render_template("base", context)
        
    def generate_slides_for_match(self, team1: str, team2: str, venue: str, match_time: str, 
                                output_filename: Optional[str] = None):
        """
        Generate slides for a specific match.
        
        Args:
            team1: Name of the first team
            team2: Name of the second team
            venue: Name of the venue
            match_time: Time of the match
            output_filename: Optional custom filename for the output HTML
        """
        self.config = {
            "team1": team1,
            "team2": team2,
            "venue": venue,
            "match_time": match_time
        }
        
        # Reset slides
        self.slide_index = 0
        self.slides_content = []
        
        # Generate title slide
        today_date = datetime.now().strftime("%d %B %Y")
        self.add_title_slide(
            title="IPL Cricket Pre-Match Analysis",
            subtitle=f"{team1} vs {team2}",
            date=today_date
        )
        
        # Add points table
        self.add_points_table_slide()
        
        # Add match comparison
        self.add_match_comparison_slide(team1, team2, venue, match_time)
        
        # Add venue and pitch analysis
        self.add_venue_pitch_slide(venue)
        
        # Add team overviews
        self.add_team_overview_slide(team1)
        self.add_team_overview_slide(team2)
        
        # Add player stats slides
        self.add_player_stats_slide("Top Run Scorers", "most-runs", "runs")
        self.add_player_stats_slide("Top Wicket Takers", "most-wickets", "wickets")
        self.add_player_stats_slide("Most Sixes", "most-6s", "sixes")
        self.add_player_stats_slide("Best Economy Rates", "best-economy-rates", "economy")
        
        # Generate final HTML
        html_output = self.generate_html()
        
        # Write HTML to file
        if output_filename is None:
            formatted_teams = f"{team1.replace(' ', '_')}_{team2.replace(' ', '_')}"
            output_filename = f"ipl_prematch_{formatted_teams}_{self.today}.html"
            
        output_path = OUTPUT_DIR / output_filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_output)
            
        logger.info(f"Generated slides at {output_path}")
        return output_path
    
    def load_templates(self) -> Dict[str, str]:
        """
        Load all HTML templates from the template directory.
        
        Returns:
            Dictionary of template name to template content
        """
        templates = {}
        
        for template_file in TEMPLATE_DIR.glob("*.html"):
            if template_file.name.startswith("base_"):
                # Load base template
                with open(template_file, "r", encoding="utf-8") as f:
                    templates["base"] = f.read()
            else:
                # Load slide templates
                template_name = template_file.stem
                with open(template_file, "r", encoding="utf-8") as f:
                    templates[template_name] = f.read()
                    
        logger.info(f"Loaded {len(templates)} templates")
        return templates
    
    def load_partials(self) -> Dict[str, str]:
        """
        Load all partial HTML templates.
        
        Returns:
            Dictionary of partial name to partial content
        """
        partials = {}
        
        for partial_file in PARTIALS_DIR.glob("*.html"):
            partial_name = partial_file.stem
            with open(partial_file, "r", encoding="utf-8") as f:
                partials[partial_name] = f.read()
                
        logger.info(f"Loaded {len(partials)} partial templates")
        return partials
        
    def load_json_data(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load data from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dictionary containing the loaded JSON data
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading JSON file {file_path}: {e}")
            return {}
        

def generate_slides_for_today():
    """
    Generate slides for today's matches by loading the schedule.
    """
    generator = IPLSlidesGenerator()
    
    # Load schedule data
    schedule_file = Path("ipl_schedule.json")
    if not schedule_file.exists():
        logger.error("Schedule file not found")
        return
        
    schedule_data = generator.load_json_data(schedule_file)
    today = datetime.now().strftime("%d-%b-%y")  # Match format in schedule JSON (e.g., "02-Apr-25")
    
    # Find today's matches
    todays_matches = []
    for match in schedule_data:  # Schedule data is a list, not a dictionary
        match_date = match.get("date", "")
        if match_date == today:
            todays_matches.append(match)
            
    if not todays_matches:
        logger.info(f"No matches scheduled for today ({today})")
        
        # For testing purposes, use the next upcoming match
        for match in schedule_data:  # Schedule data is a list, not a dictionary
            match_date = match.get("date", "")
            if match_date >= today:
                todays_matches.append(match)
                break
    
    # Generate slides for each match
    for match in todays_matches:
        team1 = match.get("home_team", "")
        team2 = match.get("away_team", "")
        venue = match.get("venue", "")
        match_time = match.get("time", "")
        
        if team1 and team2 and venue:
            generator.generate_slides_for_match(team1, team2, venue, match_time)
        else:
            logger.error(f"Invalid match data: {match}")
            
    return len(todays_matches)


if __name__ == "__main__":
    try:
        num_matches = generate_slides_for_today()
        if num_matches:
            logger.info(f"Successfully generated slides for {num_matches} match(es)")
        else:
            logger.warning("No slides were generated")
    except Exception as e:
        logger.exception(f"Error generating slides: {e}")