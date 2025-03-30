# IPL Cricket Statistics Scraper

A Python tool that scrapes and organizes Indian Premier League (IPL) cricket statistics from the Indian Express website.

## Features

- Scrapes batting statistics (runs, hundreds, fifties, fours, sixes)
- Scrapes bowling statistics (wickets, maidens, economy rates, bowling averages, strike rates)
- Organizes data into structured CSV files
- Creates detailed summary reports in HTML and JSON formats
- Color-coded console output for better readability

## Folder Structure

- `batting_stats/`: Contains all batting-related CSV files
- `bowling_stats/`: Contains all bowling-related CSV files
- `debug_files/`: Contains the raw HTML pages and text content
- `reports/`: Contains summary reports in both JSON and HTML format

## Requirements

- Python 3.6+
- Required packages: requests, beautifulsoup4, pandas, colorama

## Usage

```
python ipl_stats_scraper.py
```

## Output

The script will:
1. Create the folder structure if it doesn't exist
2. Scrape statistics from the Indian Express website
3. Save the data to CSV files in the respective folders
4. Generate summary reports in the reports folder