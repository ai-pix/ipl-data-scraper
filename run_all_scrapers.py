#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IPL Cricket Data Orchestration Script
-------------------------------------

This script coordinates the execution of all IPL cricket data scrapers,
manages data updates, and handles cleanup of old data files.

Usage:
    python run_all_scrapers.py [options]

Options:
    --clean-all      Delete all previously scraped data before running scrapers
    --skip-images    Skip updating player images (if they already exist)
    --only-clean     Only clean data without running scrapers
    --help           Show this help message and exit
"""

import os
import sys
import time
import shutil
import logging
import argparse
import importlib
import datetime
import glob
from pathlib import Path
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ipl_orchestrator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# List of scraper modules to run, in the preferred order of execution
SCRAPER_MODULES = [
    'ipl_points_table_scraper',      # Get team standings first
    'ipl_team_scraper',              # Teams info
    'ipl_stats_scraper',             # Player statistics
    'ipl_pitch_weather_scraper',     # Pitch and weather data
    'ipl_player_images_scraper',     # Player images
    'ipl_today_comparison_scraper',  # Today's match data
    'todays_match'                   # Today's match predictions
]

# Data directories that can be cleaned
DATA_DIRECTORIES = [
    'points_table',
    'team_data',
    'player_data',
    'batting_stats',
    'bowling_stats',
    'pitch_reports',
    'weather_reports',
    'match_data',
    'comparison_data',
    'predictions',
    'combined_reports',
    'match_schedule',
    'reports'
]

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='IPL Cricket Data Orchestration Script')
    parser.add_argument('--clean-all', action='store_true', help='Delete all previously scraped data before running scrapers')
    parser.add_argument('--skip-images', action='store_true', help='Skip updating player images (if they already exist)')
    parser.add_argument('--only-clean', action='store_true', help='Only clean data without running scrapers')
    return parser.parse_args()

def clean_data_directory(directory_path, retain_latest=False):
    """
    Cleans a data directory by removing files.
    
    Args:
        directory_path (str): Path to the data directory
        retain_latest (bool): Whether to retain the latest file in each directory
    """
    if not os.path.exists(directory_path):
        logger.info(f"Directory does not exist: {directory_path}")
        return
    
    logger.info(f"Cleaning directory: {directory_path}")
    files = glob.glob(os.path.join(directory_path, "*"))
    
    if not files:
        logger.info(f"No files found in {directory_path}")
        return
    
    # If retaining latest, sort files by modification time and exclude the newest
    if retain_latest and len(files) > 1:
        files.sort(key=os.path.getmtime)
        files = files[:-1]  # Exclude the newest file
        logger.info(f"Keeping latest file: {files[-1]}")
    
    # Delete files
    for file_path in files:
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {str(e)}")
        elif os.path.isdir(file_path) and not file_path.endswith('__pycache__'):
            try:
                shutil.rmtree(file_path)
                logger.info(f"Deleted directory: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete directory {file_path}: {str(e)}")

def clean_all_data(retain_latest=False):
    """Cleans all data directories."""
    logger.info("Starting cleanup of all data directories")
    
    for directory in DATA_DIRECTORIES:
        if os.path.exists(directory):
            clean_data_directory(directory, retain_latest)
    
    # Also clean debug files directory
    if os.path.exists('debug_files'):
        clean_data_directory('debug_files', False)  # Don't retain any debug files
        
    logger.info("Data cleanup complete")

def should_process_images(args, image_dir="player_images"):
    """
    Determine if we should process player images.
    Skip if requested or if directory already has many images.
    """
    if args.skip_images:
        logger.info("Skipping player images as requested")
        return False
    
    if os.path.exists(image_dir):
        image_count = len([f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))])
        if image_count > 50:  # Assume if we have more than 50 images, we have most players
            logger.info(f"Skipping player images as {image_count} images already exist")
            return False
    
    return True

def run_scraper(module_name, args):
    """
    Run a scraper module and handle any exceptions.
    
    Args:
        module_name (str): Name of the module to import and run
        args (Namespace): Command line arguments
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Running {module_name}...")
    
    # Skip player images scraper if requested or if images exist
    if module_name == 'ipl_player_images_scraper' and not should_process_images(args):
        logger.info("Skipping player images scraper")
        return True
        
    try:
        # Import the module
        module = importlib.import_module(module_name)
        
        # Check if module has a main function
        if hasattr(module, 'main'):
            # Run the main function
            module.main()
            logger.info(f"Successfully ran {module_name}")
            return True
        else:
            logger.warning(f"Module {module_name} does not have a main() function")
            return False
            
    except Exception as e:
        logger.error(f"Error running {module_name}: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def run_all_scrapers(args):
    """Run all scraper modules in sequence."""
    logger.info("Starting execution of all scrapers")
    
    successful_runs = []
    failed_runs = []
    
    start_time = time.time()
    
    for module_name in SCRAPER_MODULES:
        if run_scraper(module_name, args):
            successful_runs.append(module_name)
        else:
            failed_runs.append(module_name)
            
        # Small delay between scrapers to avoid rate limiting
        time.sleep(2)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Report results
    logger.info(f"Scraper execution completed in {duration:.2f} seconds")
    logger.info(f"Successful: {len(successful_runs)}/{len(SCRAPER_MODULES)}")
    
    if failed_runs:
        logger.warning(f"Failed runs: {', '.join(failed_runs)}")
    
    return len(failed_runs) == 0

def clean_old_data(all_successful):
    """
    Clean old data files but keep the most recent ones.
    Only performed if all scrapers were successful.
    """
    if not all_successful:
        logger.warning("Not all scrapers were successful, skipping cleanup of old data")
        return
    
    logger.info("All scrapers successful, cleaning old data files while retaining the latest")
    clean_all_data(retain_latest=True)

def main():
    """Main function to orchestrate the execution of all scrapers."""
    args = parse_arguments()
    
    try:
        # Handle clean-only mode
        if args.only_clean:
            logger.info("Running in clean-only mode")
            clean_all_data(retain_latest=False)
            logger.info("Clean-only mode completed successfully")
            return
        
        # Clean all data if requested
        if args.clean_all:
            logger.info("Cleaning all data directories before running scrapers")
            clean_all_data(retain_latest=False)
        
        # Run all scrapers
        all_successful = run_all_scrapers(args)
        
        # Clean old data if all scrapers were successful
        if not args.clean_all:  # Don't clean twice if we already cleaned everything
            clean_old_data(all_successful)
        
        logger.info("IPL Cricket Data orchestration completed")
        
    except Exception as e:
        logger.error(f"Error in orchestration script: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())