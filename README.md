# IPL Cricket Data Collection & Analysis

A comprehensive Python toolkit for scraping, organizing, and analyzing Indian Premier League (IPL) cricket data from multiple sources.

## 🏏 Features

### Statistics Collection
- **Batting Statistics**: Runs, hundreds, fifties, fours, sixes, strike rates, and averages
- **Bowling Statistics**: Wickets, maidens, economy rates, bowling averages, strike rates
- **Team-specific Data**: Performance history, win percentages, player rosters
- **Player Profiles**: Career statistics, performance trends, team history

### Data Organization
- Organized folder structure for different data types
- CSV exports for easy data manipulation in spreadsheets
- JSON exports for programmatic access
- HTML reports for visual presentation

### Analysis Tools
- Performance comparisons between teams and players
- Historical trend analysis
- Match prediction support
- Color-coded console output for better readability
- Today's match information and predictions using local CSV schedule

## 📁 Project Structure

```
ipl_cric/
├── batting_stats/       # Batting statistics CSV files
├── bowling_stats/       # Bowling statistics CSV files
├── debug_files/         # Raw HTML and extracted text for debugging
├── matches/             # Today's match predictions and data
├── reports/             # Summary reports in JSON and HTML formats
├── team_data/           # Team-specific information
│   ├── [Team_Name]/
│   │   ├── news/        # Team news articles
│   │   ├── players/     # Player information and statistics
│   │   ├── matches/     # Team match history
│   │   └── stats/       # Team performance statistics
└── Ipl schedule.csv     # Schedule of IPL matches for the season
```

## 🔧 Requirements

- Python 3.6+
- Required packages:
  ```
  requests
  beautifulsoup4
  pandas
  colorama
  matplotlib (for visualization)
  ```

## 📥 Installation

1. Clone the repository
   ```
   git clone https://github.com/yourusername/ipl-cricket-data.git
   cd ipl-cricket-data
   ```

2. Install required packages
   ```
   pip install -r requirements.txt
   ```

## 🚀 Usage

### Statistics Scraper

Collect comprehensive IPL statistics from official sources:

```
python ipl_stats_scraper.py
```

### Team Information Scraper

Gather detailed information about IPL teams:

```
python ipl_team_scraper.py
```

### Today's Match Information

Get details and predictions for today's IPL matches using the local schedule CSV:

```
python todays_match.py
```

## 📊 Output Examples

The scripts will generate:

1. CSV files with player and team statistics
2. JSON data files for programmatic access
3. HTML reports with visualizations and summaries
4. Console output with color-coded information
5. Daily match prediction files in CSV and JSON formats

## 📈 Data Visualization

The toolkit includes capabilities for generating:
- Performance trend charts
- Comparison visualizations
- Team performance dashboards
- Player statistics summaries

## 🛠️ Advanced Usage

### Custom Data Collection

You can modify the scraping parameters in the configuration files to collect specific types of data:

```python
# Example: Configure the stats scraper to focus on specific statistics
STATS_CONFIG = {
    'batting': ['most-runs', 'most-hundreds', 'most-fifties'],
    'bowling': ['most-wickets', 'best-economy-rates']
}
```

### Using Local Schedule Data

The application now uses the local CSV file (`Ipl schedule.csv`) instead of web scraping to retrieve match schedules, making it more reliable:

```python
# The schedule CSV file should have the following format:
# Match,No,Match Day,Date,Day,Start,Home,Away,Venue
# 12,10,31-Mar-25,Mon,7:30 PM,Mumbai Indians,Kolkata Knight Riders,Mumbai
```

### Data Analysis

Use the collected data for custom analysis:

```python
import pandas as pd

# Load batting statistics
batting_stats = pd.read_csv('batting_stats/ipl_most-runs_20240401.csv')

# Analyze top performers
top_batsmen = batting_stats.sort_values(by='Runs', ascending=False).head(10)
print(top_batsmen[['Player', 'Team', 'Runs', 'Avg', 'SR']])
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or feedback, please open an issue on the GitHub repository.

## 📆 Recent Updates

- **March 31, 2025**: Updated the today's match functionality to use local CSV schedule data instead of web scraping, improving reliability
- Added better date matching and flexible parsing for different date formats
- Enhanced match prediction display with team win rates and title information
- Improved error handling and debugging information