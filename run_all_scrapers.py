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
    --check-images   Only check for duplicate player images and remove broken ones 
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
import re
from pathlib import Path
import traceback
from collections import defaultdict
import json
from PIL import Image, UnidentifiedImageError
import io

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
    parser.add_argument('--check-images', action='store_true', help='Only check for duplicate player images and remove broken ones ')
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

def is_valid_image(file_path):
    """
    Check if an image file is valid/working by trying to open it with PIL.
    
    Args:
        file_path (str): Path to the image file
        
    Returns:
        bool: True if the image is valid, False otherwise
    """
    try:
        with Image.open(file_path) as img:
            # Try to load the image data to verify it's not corrupt
            img.verify()
            return True
    except (UnidentifiedImageError, IOError, SyntaxError) as e:
        logger.error(f"Invalid image {file_path}: {str(e)}")
        return False

def extract_player_info(file_name):
    """
    Extract player name and ID from file name.
    
    Args:
        file_name (str): Name of the file (without directory path)
        
    Returns:
        tuple: (player_name, player_id) or None if not extractable
    """
    # Remove file extension
    base_name = os.path.splitext(file_name)[0]
    
    # Try to extract player name and ID
    # Format is typically: PlayerName_Role_ID.ext or PlayerName__Role.ext
    parts = base_name.split('_')
    
    if len(parts) < 2:
        return None
    
    # Last part might be the ID for PNG files
    player_id = parts[-1] if parts[-1].isdigit() else None
    
    # Remove ID and role parts to get the player name
    if player_id:
        # Player name is everything before the last two parts (role and ID)
        player_name = '_'.join(parts[:-2])
    else:
        # If no ID, consider the first part as the player name
        player_name = parts[0]
    
    return player_name, player_id

def check_duplicate_images(image_dir="player_images"):
    """
    Check for duplicate player images, test which ones work, and delete broken ones.
    
    Args:
        image_dir (str): Path to the player images directory
        
    Returns:
        tuple: (duplicates_found, duplicates_resolved)
    """
    logger.info("Checking for duplicate player images...")
    
    if not os.path.exists(image_dir):
        logger.warning(f"Image directory {image_dir} does not exist")
        return 0, 0
    
    # First get all team directories
    team_dirs = [d for d in os.listdir(image_dir) 
                if os.path.isdir(os.path.join(image_dir, d)) and not d.startswith('.')]
    
    total_duplicates = 0
    resolved_duplicates = 0
    
    for team in team_dirs:
        team_path = os.path.join(image_dir, team)
        
        # Skip if not a directory or if it's a special directory
        if not os.path.isdir(team_path) or team.startswith('.') or team == "overall_summary":
            continue
            
        logger.info(f"Checking images for team: {team}")
        
        # Group files by player name
        player_files = defaultdict(list)
        
        # Get all image files
        image_files = [f for f in os.listdir(team_path) if os.path.isfile(os.path.join(team_path, f)) 
                      and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        # Group files by player name
        for img_file in image_files:
            player_info = extract_player_info(img_file)
            if player_info:
                player_name, _ = player_info
                player_files[player_name].append(img_file)
        
        # Check for duplicates
        for player, files in player_files.items():
            if len(files) > 1:
                logger.info(f"Found duplicate images for player {player}: {files}")
                total_duplicates += 1
                
                # Group files by extension
                png_files = [f for f in files if f.lower().endswith('.png')]
                jpg_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg'))]
                webp_files = [f for f in files if f.lower().endswith('.webp')]
                
                # Check which files are valid
                valid_files = []
                
                # Check all files and keep track of valid ones
                for file_list in [png_files, jpg_files, webp_files]:
                    for img_file in file_list:
                        img_path = os.path.join(team_path, img_file)
                        if is_valid_image(img_path):
                            valid_files.append((img_file, os.path.getsize(img_path)))
                
                if not valid_files:
                    logger.warning(f"No valid images found for player {player}")
                    continue
                
                # Sort by file size (larger is likely better quality)
                valid_files.sort(key=lambda x: x[1], reverse=True)
                
                # Keep the first (largest) valid file, delete the rest
                to_keep = valid_files[0][0]
                logger.info(f"Keeping image {to_keep} for player {player}")
                
                for img_file in files:
                    if img_file != to_keep:
                        try:
                            os.remove(os.path.join(team_path, img_file))
                            logger.info(f"Deleted duplicate image {img_file} for player {player}")
                            resolved_duplicates += 1
                        except OSError as e:
                            logger.error(f"Error deleting {img_file}: {str(e)}")
    
    logger.info(f"Found {total_duplicates} players with duplicate images")
    logger.info(f"Resolved {resolved_duplicates} duplicate images")
    
    return total_duplicates, resolved_duplicates

def main():
    """Main function to orchestrate the execution of all scrapers."""
    args = parse_arguments()
    
    try:
        # Handle check-images mode
        if args.check_images:
            logger.info("Running in check-images mode")
            duplicates_found, duplicates_resolved = check_duplicate_images()
            logger.info(f"Image check completed: found {duplicates_found} duplicates, resolved {duplicates_resolved}")
            return
            
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