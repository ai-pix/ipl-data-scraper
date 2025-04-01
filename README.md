# IPL Cricket Data System

A comprehensive suite of Python scripts for scraping, analyzing, and visualizing data from the Indian Premier League (IPL) cricket tournament.

## Overview

This project contains multiple scrapers to collect various types of IPL cricket data:
- Team information and player squads
- Player statistics (batting & bowling)
- Player images
- Pitch and weather reports for venues
- Match schedules and points table standings
- Daily match information and team comparisons

The system is designed to run either individual scrapers or orchestrate all scrapers with a single command, providing the most up-to-date IPL cricket data.

## Key Components

### 1. Orchestration Script (`run_all_scrapers.py`)
- Executes all scrapers in sequence with a single command
- Handles dependencies between scrapers
- Cleans up outdated files to save disk space
- Generates detailed execution logs

### 2. Player Images Scraper (`ipl_player_images_scraper.py`)
- Downloads high-quality player images from all IPL teams
- Organizes images by team in dedicated folders
- Skips already downloaded images to save bandwidth

### 3. Points Table Scraper (`ipl_points_table_scraper.py`)
- Extracts the current IPL standings table
- Provides details on matches played, won, lost, points, and net run rate
- Saves data in both CSV and HTML formats with timestamps

### 4. Player Statistics Scraper (`ipl_stats_scraper.py`)
- Collects batting statistics (runs, hundreds, fifties, boundaries)
- Collects bowling statistics (wickets, economy rates, averages)
- Generates comprehensive HTML and JSON reports

### 5. Team Information Scraper (`ipl_team_scraper.py`)
- Extracts detailed team information for all 10 IPL teams
- Collects complete squad lists with player details
- Gathers team statistics and latest news

### 6. Pitch & Weather Scraper (`ipl_pitch_weather_scraper.py`)
- Collects detailed pitch reports for all IPL venues
- Gathers real-time weather data using OpenWeatherMap API
- Creates combined reports for match analysis

### 7. Today's Match Information (`todays_match.py`)
- Identifies matches scheduled for the current day
- Provides match timings, venues, and team information
- Exports data in both JSON and CSV formats

### 8. Today's Match Comparison Scraper (`ipl_today_comparison_scraper.py`)
- Automatically scrapes comparison data for today's scheduled IPL matches
- Provides comprehensive team comparison metrics
- Identifies key players for each team

## Installation

### Prerequisites
- Python 3.6+
- Chrome browser (for scrapers using browser automation)
- Required packages listed in `requirements.txt`

### Setup
1. Clone the repository
2. Install required packages:
```
pip install -r requirements.txt
```
3. Set up API keys:
   - Create a file named `api_keys.py` in the project root
   - Add your OpenWeatherMap API key: `OPENWEATHER_API_KEY = "your_api_key_here"`

## Usage

### Running All Scrapers (Recommended)
```bash
python run_all_scrapers.py
```
This command executes all scrapers in sequence, handles dependencies, and cleans up outdated files.

Command-line options:
- `--clean-all`: Force cleanup of all data files regardless of scraper success
- `--only-clean`: Only clean data without running scrapers
- `--keep-days N`: Keep the last N days of data (default: 7)

### Running Individual Scrapers

Each scraper can be run independently:
```bash
python <scraper_filename>.py
```

For example:
```bash
python ipl_player_images_scraper.py
```

## Data Organization

The project organizes data into specific directories:
- `player_images/` - Player images organized by team
- `points_table/` - IPL standings tables with timestamps
- `batting_stats/` & `bowling_stats/` - Player statistics
- `team_data/` - Team information and details
- `pitch_reports/` & `weather_reports/` - Venue information
- `combined_reports/` - Integrated venue information
- `matches/` - Today's match information
- `comparison_data/` - Team comparison data for today's matches
- `reports/` - Summary reports and analysis
- `debug_files/` - Debugging information

## Troubleshooting

If you encounter issues:

1. Check the log files:
   - `ipl_orchestrator.log` - Main log for the orchestration script

2. Examine debug files in the `debug_files` directory

3. Common issues:
   - Chrome driver errors: Update Chrome browser
   - API rate limits: Add delays between requests
   - Data parsing errors: Check if website structure has changed

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Data sourced from the official IPL website (https://www.iplt20.com/) and other cricket statistic sites
- Weather data provided by OpenWeatherMap API
- This project is for educational and non-commercial purposes only

## Project Status

Last updated: April 1, 2025
Current IPL season: 2025