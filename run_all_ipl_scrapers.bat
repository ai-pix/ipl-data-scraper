@echo off
echo.
echo ===============================================
echo    IPL CRICKET DATA SCRAPER - MASTER RUNNER
echo ===============================================
echo.
echo Starting all IPL cricket data scrapers...
echo.
echo Timestamp: %date% %time%
echo.

:: Create log directory if it doesn't exist
if not exist "logs" mkdir logs

:: Set the Python interpreter path
set PYTHON_PATH=python

echo 1. Running Points Table Scraper...
%PYTHON_PATH% ipl_points_table_scraper.py > logs\points_table_log.txt 2>&1
echo    - Completed Points Table Scraper
echo.

echo 2. Running Team Scraper...
%PYTHON_PATH% ipl_team_scraper.py > logs\team_scraper_log.txt 2>&1
echo    - Completed Team Scraper
echo.

echo 3. Running Stats Scraper...
%PYTHON_PATH% ipl_stats_scraper.py > logs\stats_scraper_log.txt 2>&1
echo    - Completed Stats Scraper
echo.

echo 4. Running Pitch and Weather Scraper...
%PYTHON_PATH% ipl_pitch_weather_scraper.py > logs\pitch_weather_log.txt 2>&1
echo    - Completed Pitch and Weather Scraper
echo.

echo 5. Running Player Images Scraper...
%PYTHON_PATH% ipl_player_images_scraper.py > logs\player_images_log.txt 2>&1
echo    - Completed Player Images Scraper
echo.

echo 6. Running Today's Match Data Scraper...
%PYTHON_PATH% todays_match.py > logs\todays_match_log.txt 2>&1
echo    - Completed Today's Match Data Scraper
echo.

echo 7. Running Match Comparison Scraper...
%PYTHON_PATH% ipl_today_comparison_scraper.py > logs\today_comparison_log.txt 2>&1
echo    - Completed Match Comparison Scraper
echo.

echo 8. Running Data Orchestrator (creates HTML summary)...
%PYTHON_PATH% run_all_scrapers.py > logs\orchestrator_log.txt 2>&1
echo    - Completed Data Orchestrator
echo.

echo ===============================================
echo All IPL cricket data scrapers completed!
echo.
echo Logs are available in the logs directory.
echo.
echo The IPL data dashboard is available at:
echo ipl_data_content.html
echo ===============================================

:: Open the HTML dashboard
start ipl_data_content.html

echo.
echo Press any key to exit...
pause > nul