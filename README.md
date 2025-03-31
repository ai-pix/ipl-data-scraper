# IPL Cricket Data Project

A comprehensive suite of Python scripts for scraping, analyzing, and visualizing data from the Indian Premier League (IPL) cricket tournament.

## Overview

This project contains multiple tools to collect various types of IPL data:
- Team information and squads
- Player images
- Match schedules
- Points table standings
- Player statistics (batting & bowling)
- Daily match information

## Features

### 1. Player Images Scraper (`ipl_player_images_scraper.py`)
- Downloads high-quality player images from all IPL teams
- Organizes images by team in dedicated folders
- Names files with player name, role, and unique ID
- Generates detailed summary reports

### 2. Points Table Scraper (`ipl_points_table_scraper.py`)
- Extracts the current IPL standings table
- Provides details on matches played, won, lost, points, and net run rate
- Saves data in CSV format with timestamps

### 3. Player Statistics Scraper (`ipl_stats_scraper.py`)
- Collects batting statistics:
  - Most runs
  - Most boundaries (4s and 6s)
  - Most fifties and hundreds
- Collects bowling statistics:
  - Most wickets
  - Best economy rates
  - Best bowling average
  - Best bowling strike rate
  - Most maidens

### 4. Team Information Scraper (`ipl_team_scraper.py`)
- Extracts detailed team information
- Collects squad lists and player details

### 5. Today's Match Information (`todays_match.py`)
- Shows information about today's IPL matches
- Updates daily

## Installation

### Prerequisites
- Python 3.6+
- Required packages listed in `requirements.txt`

### Setup
1. Clone the repository
2. Install required packages:
```
pip install -r requirements.txt
```

## Usage

### Player Images Scraper
```
python ipl_player_images_scraper.py
```
Downloads player images from all IPL teams and saves them in the `player_images` directory.

### Points Table Scraper
```
python ipl_points_table_scraper.py
```
Scrapes the current IPL points table and saves it in the `points_table` directory.

### Statistics Scraper
```
python ipl_stats_scraper.py
```
Scrapes various player statistics and saves them in the `batting_stats` and `bowling_stats` directories.

### Team Information Scraper
```
python ipl_team_scraper.py
```
Scrapes team information and saves it in the `team_data` directory.

### Today's Match
```
python todays_match.py
```
Shows information about today's IPL matches.

## Data Organization

The project organizes data into specific directories:
- `player_images/` - Player images organized by team
- `points_table/` - IPL standings tables with timestamps
- `batting_stats/` - Various batting statistics
- `bowling_stats/` - Various bowling statistics
- `team_data/` - Team information and details
- `match_schedule/` - IPL match schedules
- `match_data/` - Detailed match information
- `debug_files/` - HTML files saved for debugging purposes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Data sourced from the official IPL website (https://www.iplt20.com/)
- This project is for educational purposes only