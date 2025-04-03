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
    --parallel       Run scrapers in parallel for faster execution (default: False)
    --workers        Number of worker processes for parallel scraping (default: auto)
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
import csv
import base64
from PIL import Image, UnidentifiedImageError
import io
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

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
    'todays_match',                  # Today's match predictions
    'ipl_slides_generator'           # Generate IPL slides
]

# Group of scrapers that can be run in parallel safely (no dependencies between them)
PARALLEL_SAFE_SCRAPERS = [
    'ipl_stats_scraper',             # Player statistics
    'ipl_pitch_weather_scraper',     # Pitch and weather data
    'ipl_player_images_scraper',     # Player images
]

# Scrapers that should run sequentially (have dependencies or share resources)
SEQUENTIAL_SCRAPERS = [
    'ipl_points_table_scraper',      # Get team standings first
    'ipl_team_scraper',              # Teams info (needs points table)
    'ipl_today_comparison_scraper',  # Today's match data (needs team info)
    'todays_match'                   # Today's match predictions (needs comparison data)
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

# Path for the data summary files
DATA_SUMMARY_JSON = 'ipl_data_summary.json'
DATA_SUMMARY_HTML = 'ipl_data_content.html'

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='IPL Cricket Data Orchestration Script')
    parser.add_argument('--clean-all', action='store_true', help='Delete all previously scraped data before running scrapers')
    parser.add_argument('--skip-images', action='store_true', help='Skip updating player images (if they already exist)')
    parser.add_argument('--only-clean', action='store_true', help='Only clean data without running scrapers')
    parser.add_argument('--check-images', action='store_true', help='Only check for duplicate player images and remove broken ones')
    parser.add_argument('--parallel', action='store_true', help='Run scrapers in parallel for faster execution')
    parser.add_argument('--workers', type=int, default=0, help='Number of worker processes for parallel scraping (default: auto)')
    return parser.parse_args()

def clean_data_directory(directory_path, retain_latest=False, update_only=True):
    """
    Cleans a data directory by updating files instead of removing them.

    Args:
        directory_path (str): Path to the data directory
        retain_latest (bool): Whether to retain the latest file in each directory
        update_only (bool): If True, mark files for update instead of deleting them
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

    # Special handling for image files - don't update or delete them
    is_image_dir = 'player_images' in directory_path or 'LOGO' in directory_path

    # Process files
    for file_path in files:
        if os.path.isfile(file_path):
            # Skip image files in image directories
            if is_image_dir and file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                logger.debug(f"Preserving image file: {file_path}")
                continue

            if update_only:
                # Mark file for update instead of deleting
                try:
                    with open(file_path, 'a') as f:
                        # Add update marker without modifying content
                        pass
                    logger.info(f"Marked file for update: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to mark {file_path} for update: {str(e)}")
            else:
                # Original delete behavior
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {str(e)}")
        elif os.path.isdir(file_path) and not file_path.endswith('__pycache__'):
            # For subdirectories, recursively process them with the same update policy
            if update_only and not is_image_dir:
                clean_data_directory(file_path, retain_latest, update_only)
            else:
                try:
                    shutil.rmtree(file_path)
                    logger.info(f"Deleted directory: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete directory {file_path}: {str(e)}")

def clean_all_data(retain_latest=True, update_only=True):
    """
    Clean all data directories by updating files instead of removing them.

    Args:
        retain_latest (bool): Whether to retain the latest file in each directory
        update_only (bool): If True, mark files for update instead of deleting them
    """
    logger.info("Cleaning all data directories...")

    files_processed = 0
    for data_dir in DATA_DIRECTORIES:
        if not os.path.exists(data_dir):
            continue

        logger.info(f"Processing directory: {data_dir}")

        # Skip player_images directory - images don't need to be updated once downloaded
        if data_dir == 'player_images':
            logger.info(f"Skipping player images directory as images don't need updating")
            continue

        # Get all files in the directory
        all_files = []
        for root, _, files in os.walk(data_dir):
            for file in files:
                file_path = os.path.join(root, file)
                mod_time = os.path.getmtime(file_path)
                all_files.append((file_path, mod_time))

        # Group files by their base names (without date suffixes)
        file_groups = defaultdict(list)
        for file_path, mod_time in all_files:
            file_name = os.path.basename(file_path)
            # Skip image files
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue

            # Remove date patterns like YYYYMMDD or YYYY-MM-DD from filename for grouping
            base_name = re.sub(r'_?\d{4}[-_]?\d{2}[-_]?\d{2}', '', file_name)
            base_name = re.sub(r'_?\d{8}', '', base_name)
            # Skip _latest or latest files from grouping (always preserve these)
            if 'latest' in file_name.lower():
                base_name = file_name  # Keep latest files in their own groups
            file_groups[base_name].append((file_path, mod_time))

        # Process each group
        for base_name, group_files in file_groups.items():
            # Sort by modification time, newest first
            sorted_files = sorted(group_files, key=lambda x: x[1], reverse=True)

            # Determine which files to keep and which to process
            files_to_keep = []

            # If retaining latest, keep the newest file
            if retain_latest and sorted_files:
                files_to_keep.append(sorted_files[0][0])

            # Always keep files with "latest" in the name
            for file_path, _ in sorted_files:
                if 'latest' in os.path.basename(file_path).lower():
                    files_to_keep.append(file_path)

            # Process files not in the keep list
            for file_path, _ in sorted_files:
                if file_path not in files_to_keep:
                    if update_only:
                        try:
                            # Mark file for update without deleting
                            with open(file_path, 'a') as f:
                                # Touch file to update modification time
                                pass
                            files_processed += 1
                            logger.debug(f"Marked file for update: {file_path}")
                        except Exception as e:
                            logger.error(f"Error marking file {file_path} for update: {str(e)}")
                    else:
                        try:
                            os.remove(file_path)
                            files_processed += 1
                            logger.debug(f"Removed file: {file_path}")
                        except Exception as e:
                            logger.error(f"Error removing file {file_path}: {str(e)}")

    logger.info(f"Cleanup completed. Processed {files_processed} files.")

# Helper function to check if a file should be updated
def should_update_file(file_path):
    """
    Determine if a file should be updated based on its type and age.

    Args:
        file_path (str): Path to the file to check

    Returns:
        bool: True if the file should be updated, False otherwise
    """
    # Don't update image files
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
        return False

    # Don't update files with 'latest' in the name
    if 'latest' in os.path.basename(file_path).lower():
        return False

    # Don't update files modified today
    today = datetime.datetime.now().strftime("%Y%m%d")
    if today in os.path.basename(file_path):
        return False

    return True

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

def run_scraper_parallel(module_name, args_dict):
    """
    Run a scraper module in a separate process.
    This function is designed to be used with multiprocessing.

    Args:
        module_name (str): Name of the module to import and run
        args_dict (dict): Dictionary of arguments (converted from Namespace for pickling)

    Returns:
        tuple: (module_name, success)
    """
    # Convert args_dict back to a Namespace object
    class Args:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    args = Args(**args_dict)

    # Configure process-specific logging
    process_logger = logging.getLogger(f"{module_name}_process")
    process_logger.setLevel(logging.INFO)

    # Skip player images scraper if requested or if images exist
    if module_name == 'ipl_player_images_scraper' and not should_process_images(args):
        process_logger.info(f"Skipping player images scraper")
        return (module_name, True)

    process_logger.info(f"Starting scraper {module_name} in parallel process")

    try:
        # Import the module
        module = importlib.import_module(module_name)

        # Check if module has a main function
        if hasattr(module, 'main'):
            # Run the main function
            start_time = time.time()
            module.main()
            duration = time.time() - start_time
            process_logger.info(f"Successfully ran {module_name} in {duration:.2f} seconds")
            return (module_name, True)
        else:
            process_logger.warning(f"Module {module_name} does not have a main() function")
            return (module_name, False)

    except Exception as e:
        process_logger.error(f"Error running {module_name}: {str(e)}")
        process_logger.error(traceback.format_exc())
        return (module_name, False)

def run_all_scrapers(args):
    """Run all scraper modules in sequence or parallel based on arguments."""
    logger.info("Starting execution of scrapers")

    if args.parallel:
        return run_scrapers_in_parallel(args)
    else:
        return run_scrapers_sequentially(args)

def run_scrapers_sequentially(args):
    """Run all scraper modules in sequence."""
    logger.info("Running scrapers sequentially")

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
    logger.info(f"Sequential scraper execution completed in {duration:.2f} seconds")
    logger.info(f"Successful: {len(successful_runs)}/{len(SCRAPER_MODULES)}")

    if failed_runs:
        logger.warning(f"Failed runs: {', '.join(failed_runs)}")

    return len(failed_runs) == 0

def run_scrapers_in_parallel(args):
    """Run scraper modules in parallel where possible, sequential where necessary."""
    logger.info("Running scrapers in parallel mode")

    # Convert Namespace args to dictionary for pickling in multiprocessing
    args_dict = vars(args)

    successful_runs = []
    failed_runs = []
    overall_start_time = time.time()

    # Determine number of worker processes
    num_workers = args.workers if args.workers > 0 else min(len(PARALLEL_SAFE_SCRAPERS), multiprocessing.cpu_count())
    logger.info(f"Using {num_workers} worker processes for parallel execution")

    # First run sequential scrapers that must run first
    logger.info("Running sequential scrapers first...")
    for module_name in SEQUENTIAL_SCRAPERS[:2]:  # Run only points table and team scrapers first
        if run_scraper(module_name, args):
            successful_runs.append(module_name)
        else:
            failed_runs.append(module_name)
        time.sleep(1)  # Brief delay between sequential scrapers

    # Run parallel safe scrapers
    logger.info(f"Running {len(PARALLEL_SAFE_SCRAPERS)} scrapers in parallel...")
    parallel_start_time = time.time()

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all parallel-safe scrapers
        future_to_scraper = {
            executor.submit(run_scraper_parallel, module_name, args_dict): module_name
            for module_name in PARALLEL_SAFE_SCRAPERS
        }

        # Process results as they complete
        for future in as_completed(future_to_scraper):
            module_name, success = future.result()
            if success:
                successful_runs.append(module_name)
                logger.info(f"Parallel scraper {module_name} completed successfully")
            else:
                failed_runs.append(module_name)
                logger.warning(f"Parallel scraper {module_name} failed")

    parallel_duration = time.time() - parallel_start_time
    logger.info(f"Parallel scrapers completed in {parallel_duration:.2f} seconds")

    # Run remaining sequential scrapers (that depend on both sequential and parallel results)
    logger.info("Running remaining sequential scrapers...")
    for module_name in SEQUENTIAL_SCRAPERS[2:]:
        if run_scraper(module_name, args):
            successful_runs.append(module_name)
        else:
            failed_runs.append(module_name)
        time.sleep(1)  # Brief delay between sequential scrapers

    overall_duration = time.time() - overall_start_time

    # Report results
    logger.info(f"Parallel scraper execution completed in {overall_duration:.2f} seconds")
    logger.info(f"Successful: {len(successful_runs)}/{len(SCRAPER_MODULES)}")

    if failed_runs:
        logger.warning(f"Failed runs: {', '.join(failed_runs)}")

    return len(failed_runs) == 0

def clean_old_data(all_successful=True, today_date=None):
    """
    Clean old data files while keeping only the newest ones from today's run.

    This function cleans up all previous versions of data files from various data directories,
    keeping only the files generated in the current run (with today's date).

    Args:
        all_successful (bool): Whether all scrapers ran successfully
        today_date (str): Today's date in YYYYMMDD format to protect new files
    """
    if not all_successful:
        logger.warning("Not all scrapers were successful. Skipping old data cleanup.")
        return

    logger.info("Cleaning old data files (keeping only files from today's run)...")

    # Get today's date string for protecting new files
    if today_date is None:
        today_date = datetime.datetime.now().strftime("%Y%m%d")

    # Process each data directory
    files_removed = 0
    for data_dir in DATA_DIRECTORIES:
        if not os.path.exists(data_dir):
            continue

        logger.info(f"Cleaning directory: {data_dir}")

        # Get all files in the directory
        for root, _, files in os.walk(data_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_name = os.path.basename(file_path)

                # Skip files created today (protect new files)
                if today_date in file_name:
                    logger.debug(f"Keeping today's file: {file_path}")
                    continue

                # Skip files with 'latest' in the name (these are special markers)
                if 'latest' in file_name.lower():
                    logger.debug(f"Keeping latest marker file: {file_path}")
                    continue

                # Remove all other files (previous versions)
                try:
                    os.remove(file_path)
                    files_removed += 1
                    logger.debug(f"Removed old file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {str(e)}")

    logger.info(f"Cleanup completed. Removed {files_removed} old files.")

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

def generate_data_summary():
    """
    Generate a summary of all scraped data and save it to a JSON file.

    This function scans all data directories, collects metadata about the files,
    and creates a comprehensive summary of what data has been scraped.

    Returns:
        dict: The data summary dictionary
    """
    logger.info("Generating data summary...")

    # Initialize the data summary dictionary
    summary = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "directories": {},
        "overview": {
            "total_files": 0,
            "total_size_bytes": 0,
            "file_types": defaultdict(int)
        }
    }

    # Add player_images directory to the list to scan
    directories_to_scan = DATA_DIRECTORIES + ['player_images', 'LOGO', 'matches']

    # Scan each directory and gather data
    for directory in directories_to_scan:
        if not os.path.exists(directory):
            continue

        dir_info = {
            "file_count": 0,
            "total_size_bytes": 0,
            "latest_file": None,
            "latest_file_date": None,
            "file_types": defaultdict(int),
            "subdirectories": {}
        }

        # Walk through the directory and its subdirectories
        for root, dirs, files in os.walk(directory):
            relative_path = os.path.relpath(root, directory)
            current_dir = dir_info

            # Navigate to the correct subdirectory in our structure
            if relative_path != '.':
                path_parts = relative_path.split(os.sep)
                for part in path_parts:
                    if part not in current_dir["subdirectories"]:
                        current_dir["subdirectories"][part] = {
                            "file_count": 0,
                            "total_size_bytes": 0,
                            "latest_file": None,
                            "latest_file_date": None,
                            "file_types": defaultdict(int),
                            "subdirectories": {}
                        }
                    current_dir = current_dir["subdirectories"][part]

            # Process files in this directory
            for file in files:
                if file.startswith('.') or file == DATA_SUMMARY_JSON:
                    continue

                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                file_mod_time = os.path.getmtime(file_path)
                file_extension = os.path.splitext(file)[1].lower()

                # Update current directory info
                current_dir["file_count"] += 1
                current_dir["total_size_bytes"] += file_size
                current_dir["file_types"][file_extension] += 1

                # Update latest file info
                if not current_dir["latest_file"] or file_mod_time > current_dir["latest_file_date"]:
                    current_dir["latest_file"] = file
                    current_dir["latest_file_date"] = file_mod_time

                # Update main directory info
                dir_info["file_count"] += 1
                dir_info["total_size_bytes"] += file_size
                dir_info["file_types"][file_extension] += 1

                # If latest file in whole directory, update
                if not dir_info["latest_file"] or file_mod_time > dir_info["latest_file_date"]:
                    dir_info["latest_file"] = os.path.join(relative_path, file)
                    dir_info["latest_file_date"] = file_mod_time

        # Convert defaultdicts to regular dicts for JSON serialization
        dir_info["file_types"] = dict(dir_info["file_types"])

        # Convert timestamps to readable format
        if dir_info["latest_file_date"]:
            dir_info["latest_file_date"] = datetime.datetime.fromtimestamp(
                dir_info["latest_file_date"]
            ).strftime("%Y-%m-%d %H:%M:%S")

        # Process subdirectories recursively
        def process_subdirs(subdir_dict):
            for subdir_name, subdir_info in list(subdir_dict.items()):
                subdir_info["file_types"] = dict(subdir_info["file_types"])
                if subdir_info["latest_file_date"]:
                    subdir_info["latest_file_date"] = datetime.datetime.fromtimestamp(
                        subdir_info["latest_file_date"]
                    ).strftime("%Y-%m-%d %H:%M:%S")
                process_subdirs(subdir_info["subdirectories"])

                # If subdirectory is empty, remove it
                if subdir_info["file_count"] == 0 and not subdir_info["subdirectories"]:
                    del subdir_dict[subdir_name]

        process_subdirs(dir_info["subdirectories"])

        # Only include directories that have files
        if dir_info["file_count"] > 0 or dir_info["subdirectories"]:
            summary["directories"][directory] = dir_info

    # Convert overview defaultdict to regular dict
    summary["overview"]["file_types"] = dict(summary["overview"]["file_types"])

    # Add human-readable file sizes
    def add_human_readable_sizes(data_dict):
        if "total_size_bytes" in data_dict:
            data_dict["total_size_human"] = format_file_size(data_dict["total_size_bytes"])

        if "subdirectories" in data_dict:
            for subdir in data_dict["subdirectories"].values():
                add_human_readable_sizes(subdir)

    add_human_readable_sizes(summary["overview"])
    for dir_info in summary["directories"].values():
        add_human_readable_sizes(dir_info)

    # Save to JSON file
    with open(DATA_SUMMARY_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Data summary saved to {DATA_SUMMARY_JSON}")
    return summary

def format_file_size(size_in_bytes):
    """Convert file size in bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def generate_html_data_content():
    """
    Generate an HTML file with the actual content of all scraped data.

    This function reads the content of scraped data files and formats them
    into a comprehensive HTML document for easy viewing.

    Returns:
        str: Path to the generated HTML file
    """
    logger.info("Generating HTML data content...")

    today = datetime.datetime.now().strftime("%Y%m%d")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Initialize HTML content with styles and header
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPL Cricket Data Content - {timestamp}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background-color: #004c8c;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        nav {{
            background-color: #f4f4f4;
            padding: 10px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        nav ul {{
            list-style-type: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
        }}
        nav li {{
            margin: 0 10px;
        }}
        nav a {{
            text-decoration: none;
            color: #004c8c;
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 3px;
        }}
        nav a:hover {{
            background-color: #004c8c;
            color: white;
        }}
        section {{
            margin: 40px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            background-color: #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #004c8c;
            border-bottom: 2px solid #004c8c;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #004c8c;
            margin-top: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #004c8c;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        tr:hover {{
            background-color: #e6f2ff;
        }}
        .team-logo {{
            max-width: 50px;
            max-height: 50px;
        }}
        .player-image {{
            max-width: 100px;
            max-height: 100px;
            border-radius: 50%;
        }}
        .summary-box {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .summary-item {{
            flex: 1;
            min-width: 200px;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            background-color: #f9f9f9;
            box-shadow: 0 2px 3px rgba(0,0,0,0.05);
        }}
        .summary-value {{
            font-size: 24px;
            font-weight: bold;
            color: #004c8c;
            margin: 10px 0;
        }}
        .json-data {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 15px;
            overflow-x: auto;
            white-space: pre-wrap;
            font-family: monospace;
        }}
        .tab-container {{
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }}
        .tab-buttons {{
            display: flex;
            background-color: #f4f4f4;
        }}
        .tab-button {{
            padding: 10px 20px;
            border: none;
            background-color: transparent;
            cursor: pointer;
            font-weight: bold;
        }}
        .tab-button.active {{
            background-color: #004c8c;
            color: white;
        }}
        .tab-content {{
            display: none;
            padding: 20px;
        }}
        .tab-content.active {{
            display: block;
        }}
        footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background-color: #004c8c;
            color: white;
        }}
    </style>
    <script>
        // JavaScript for tab functionality
        document.addEventListener('DOMContentLoaded', function() {{
            // Function to handle tab switching
            function openTab(evt, tabName) {{
                // Hide all tab content
                const tabContents = document.getElementsByClassName('tab-content');
                for (let i = 0; i < tabContents.length; i++) {{
                    tabContents[i].classList.remove('active');
                }}

                // Remove active class from all tab buttons
                const tabButtons = document.getElementsByClassName('tab-button');
                for (let i = 0; i < tabButtons.length; i++) {{
                    tabButtons[i].classList.remove('active');
                }}

                // Show the current tab and add active class to the button
                document.getElementById(tabName).classList.add('active');
                evt.currentTarget.classList.add('active');
            }}

            // Attach click handlers to all tab buttons
            const tabButtons = document.getElementsByClassName('tab-button');
            for (let i = 0; i < tabButtons.length; i++) {{
                tabButtons[i].addEventListener('click', function(event) {{
                    openTab(event, this.getAttribute('data-tab'));
                }});
            }}

            // Set default active tab
            if (tabButtons.length > 0) {{
                tabButtons[0].click();
            }}
        }});
    </script>
</head>
<body>
    <header>
        <h1>IPL Cricket Data Dashboard</h1>
        <p>Generated on {timestamp}</p>
    </header>

    <nav>
        <ul>
            <li><a href="#overview">Overview</a></li>
            <li><a href="#points-table">Points Table</a></li>
            <li><a href="#teams">Teams</a></li>
            <li><a href="#batting-stats">Batting Stats</a></li>
            <li><a href="#bowling-stats">Bowling Stats</a></li>
            <li><a href="#matches">Matches</a></li>
            <li><a href="#predictions">Predictions</a></li>
            <li><a href="#reports">Reports</a></li>
        </ul>
    </nav>

    <div class="container">
    """

    # Get summary data for overview section
    summary = {}
    if os.path.exists(DATA_SUMMARY_JSON):
        with open(DATA_SUMMARY_JSON, 'r', encoding='utf-8') as f:
            summary = json.load(f)

    # Add overview section
    html_content += f"""
        <section id="overview">
            <h2>Overview</h2>
            <div class="summary-box">
                <div class="summary-item">
                    <h3>Total Files</h3>
                    <div class="summary-value">{summary.get("overview", {}).get("total_files", 0)}</div>
                </div>
                <div class="summary-item">
                    <h3>Total Size</h3>
                    <div class="summary-value">{summary.get("overview", {}).get("total_size_human", "0 MB")}</div>
                </div>
                <div class="summary-item">
                    <h3>Last Updated</h3>
                    <div class="summary-value">{summary.get("generated_at", timestamp)}</div>
                </div>
            </div>
        </section>
    """

    # Add points table section
    html_content += """
        <section id="points-table">
            <h2>Points Table</h2>
    """

    points_table_file = os.path.join('points_table', 'ipl_points_table_latest.html')
    if os.path.exists(points_table_file):
        with open(points_table_file, 'r', encoding='utf-8') as f:
            points_content = f.read()
            # Extract the table part from the HTML
            table_match = re.search(r'<table.*?</table>', points_content, re.DOTALL)
            if table_match:
                html_content += table_match.group(0)
            else:
                html_content += f"""
                    <div class="json-data">
                        {points_content}
                    </div>
                """
    else:
        html_content += "<p>No points table data available</p>"

    html_content += "</section>"

    # Add teams section
    html_content += """
        <section id="teams">
            <h2>Teams</h2>
            <div class="team-logos">
    """

    # Add team logos
    if os.path.exists('LOGO'):
        logo_files = [f for f in os.listdir('LOGO') if f.endswith('.png')]
        for logo_file in logo_files:
            team_name = os.path.splitext(logo_file)[0]
            logo_path = os.path.join('LOGO', logo_file)

            # Convert image to base64 for embedding
            try:
                with open(logo_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    html_content += f"""
                    <div style="display: inline-block; margin: 10px; text-align: center;">
                        <img src="data:image/png;base64,{img_data}" alt="{team_name}" class="team-logo" style="width: 100px; height: auto;">
                        <p>{team_name}</p>
                    </div>
                    """
            except Exception as e:
                logger.error(f"Error embedding team logo {logo_file}: {str(e)}")

    # Team data tabs
    html_content += """
        <div class="tab-container">
            <div class="tab-buttons">
    """

    # Create tab buttons for each team
    team_dirs = []
    if os.path.exists('team_data'):
        team_dirs = [d for d in os.listdir('team_data') if os.path.isdir(os.path.join('team_data', d))]

    for i, team_dir in enumerate(team_dirs):
        active_class = " active" if i == 0 else ""
        html_content += f"""
            <button class="tab-button{active_class}" data-tab="team-tab-{i}">{team_dir.replace('_', ' ')}</button>
        """

    html_content += """
            </div>
    """

    # Create tab content for each team
    for i, team_dir in enumerate(team_dirs):
        active_class = " active" if i == 0 else ""
        team_path = os.path.join('team_data', team_dir)

        html_content += f"""
            <div id="team-tab-{i}" class="tab-content{active_class}">
                <h3>{team_dir.replace('_', ' ')}</h3>
        """

        # Add player data if available
        players_path = os.path.join(team_path, 'players')
        if os.path.exists(players_path):
            squad_file = os.path.join(players_path, 'squad.csv')
            if os.path.exists(squad_file):
                html_content += "<h4>Squad</h4>"
                try:
                    with open(squad_file, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        headers = next(reader)

                        html_content += "<table>"
                        # Table headers
                        html_content += "<tr>"
                        for header in headers:
                            html_content += f"<th>{header}</th>"
                        html_content += "</tr>"

                        # Table rows
                        for row in reader:
                            html_content += "<tr>"
                            for cell in row:
                                html_content += f"<td>{cell}</td>"
                            html_content += "</tr>"

                        html_content += "</table>"
                except Exception as e:
                    logger.error(f"Error reading squad file for {team_dir}: {str(e)}")

        # Add stats data if available
        stats_path = os.path.join(team_path, 'stats')
        if os.path.exists(stats_path):
            stats_file = os.path.join(stats_path, 'team_statistics.json')
            if os.path.exists(stats_file):
                html_content += "<h4>Team Statistics</h4>"
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats_data = json.load(f)
                        html_content += f"""
                            <div class="json-data">
                                {json.dumps(stats_data, indent=4)}
                            </div>
                        """
                except Exception as e:
                    logger.error(f"Error reading stats file for {team_dir}: {str(e)}")

        html_content += """
            </div>
        """

    html_content += """
        </div>
        </div>
        </section>
    """

    # Add batting stats section
    html_content += """
        <section id="batting-stats">
            <h2>Batting Statistics</h2>
    """

    # Find the latest batting stats file
    batting_files = []
    if os.path.exists('batting_stats'):
        batting_files = glob.glob(os.path.join('batting_stats', f'ipl_*_{today}.csv'))
        if not batting_files:
            # If no files for today, get the most recent ones
            batting_files = sorted(glob.glob(os.path.join('batting_stats', 'ipl_*.csv')),
                                key=os.path.getmtime, reverse=True)

    if batting_files:
        for batting_file in batting_files[:3]:  # Limit to 3 most recent files
            filename = os.path.basename(batting_file)
            stat_type = filename.split('_')[1].split('.')[0].replace('-', ' ').title()

            html_content += f"<h3>{stat_type}</h3>"

            try:
                with open(batting_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader)

                    html_content += "<table>"
                    # Table headers
                    html_content += "<tr>"
                    for header in headers:
                        html_content += f"<th>{header}</th>"
                    html_content += "</tr>"

                    # Table rows
                    for row in reader:
                        html_content += "<tr>"
                        for cell in row:
                            html_content += f"<td>{cell}</td>"
                        html_content += "</tr>"

                    html_content += "</table>"
            except Exception as e:
                logger.error(f"Error reading batting stats file {batting_file}: {str(e)}")
    else:
        html_content += "<p>No batting statistics available</p>"

    html_content += "</section>"

    # Add bowling stats section
    html_content += """
        <section id="bowling-stats">
            <h2>Bowling Statistics</h2>
    """

    # Find the latest bowling stats file
    bowling_files = []
    if os.path.exists('bowling_stats'):
        bowling_files = glob.glob(os.path.join('bowling_stats', f'ipl_*_{today}.csv'))
        if not bowling_files:
            # If no files for today, get the most recent ones
            bowling_files = sorted(glob.glob(os.path.join('bowling_stats', 'ipl_*.csv')),
                                key=os.path.getmtime, reverse=True)

    if bowling_files:
        for bowling_file in bowling_files[:3]:  # Limit to 3 most recent files
            filename = os.path.basename(bowling_file)
            stat_type = filename.split('_')[1].split('.')[0].replace('-', ' ').title()

            html_content += f"<h3>{stat_type}</h3>"

            try:
                with open(bowling_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader)

                    html_content += "<table>"
                    # Table headers
                    html_content += "<tr>"
                    for header in headers:
                        html_content += f"<th>{header}</th>"
                    html_content += "</tr>"

                    # Table rows
                    for row in reader:
                        html_content += "<tr>"
                        for cell in row:
                            html_content += f"<td>{cell}</td>"
                        html_content += "</tr>"

                    html_content += "</table>"
            except Exception as e:
                logger.error(f"Error reading bowling stats file {bowling_file}: {str(e)}")
    else:
        html_content += "<p>No bowling statistics available</p>"

    html_content += "</section>"

    # Add matches section
    html_content += """
        <section id="matches">
            <h2>Today's Matches</h2>
    """

    # Find today's matches
    matches_file = os.path.join('matches', f'todays_matches_{today}.csv')
    if os.path.exists(matches_file):
        try:
            with open(matches_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)

                html_content += "<table>"
                # Table headers
                html_content += "<tr>"
                for header in headers:
                    html_content += f"<th>{header}</th>"
                html_content += "</tr>"

                # Table rows
                for row in reader:
                    html_content += "<tr>"
                    for cell in row:
                        html_content += f"<td>{cell}</td>"
                    html_content += "</tr>"

                html_content += "</table>"
        except Exception as e:
            logger.error(f"Error reading matches file {matches_file}: {str(e)}")
    else:
        html_content += "<p>No matches scheduled for today</p>"

    # Add match comparison data if available
    comparison_file = os.path.join('comparison_data', f'today_match_comparison_summary_{today}.json')
    if os.path.exists(comparison_file):
        html_content += "<h3>Match Comparison</h3>"
        try:
            with open(comparison_file, 'r', encoding='utf-8') as f:
                comparison_data = json.load(f)
                html_content += f"""
                    <div class="json-data">
                        {json.dumps(comparison_data, indent=4)}
                    </div>
                """
        except Exception as e:
            logger.error(f"Error reading comparison file {comparison_file}: {str(e)}")

    html_content += "</section>"

    # Add predictions section
    html_content += """
        <section id="predictions">
            <h2>Predictions</h2>
    """

    # Find prediction files
    prediction_files = []
    if os.path.exists('predictions'):
        prediction_files = glob.glob(os.path.join('predictions', f'*_{today}.json'))
        if not prediction_files:
            # If no files for today, get the most recent ones
            prediction_files = sorted(glob.glob(os.path.join('predictions', '*.json')),
                                  key=os.path.getmtime, reverse=True)

    if prediction_files:
        for pred_file in prediction_files[:2]:  # Limit to 2 most recent files
            filename = os.path.basename(pred_file)
            pred_type = filename.split('_')[0].replace('-', ' ').title()

            html_content += f"<h3>{pred_type}</h3>"

            try:
                with open(pred_file, 'r', encoding='utf-8') as f:
                    pred_data = json.load(f)
                    html_content += f"""
                        <div class="json-data">
                            {json.dumps(pred_data, indent=4)}
                        </div>
                    """
            except Exception as e:
                logger.error(f"Error reading prediction file {pred_file}: {str(e)}")
    else:
        html_content += "<p>No prediction data available</p>"

    html_content += "</section>"

    # Add reports section
    html_content += """
        <section id="reports">
            <h2>Reports</h2>
    """

    # Find report files in the reports directory
    report_files = []
    if os.path.exists('reports'):
        report_files = glob.glob(os.path.join('reports', f'*_{today}.html'))
        if not report_files:
            # If no files for today, get the most recent ones
            report_files = sorted(glob.glob(os.path.join('reports', '*.html')),
                               key=os.path.getmtime, reverse=True)

    # Also check combined_reports directory
    combined_report_files = []
    if os.path.exists('combined_reports'):
        combined_report_files = glob.glob(os.path.join('combined_reports', f'*_{today}.html'))
        if not combined_report_files:
            # If no files for today, get the most recent ones
            combined_report_files = sorted(glob.glob(os.path.join('combined_reports', '*.html')),
                                       key=os.path.getmtime, reverse=True)

    all_report_files = report_files + combined_report_files

    if all_report_files:
        for report_file in all_report_files[:3]:  # Limit to 3 most recent files
            filename = os.path.basename(report_file)
            report_type = filename.split('_')[1].replace('-', ' ').title()

            html_content += f"<h3>{report_type} Report</h3>"

            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_content = f.read()

                    # Extract just the content part of the HTML (skip head, scripts, etc.)
                    body_match = re.search(r'<body.*?>(.*?)</body>', report_content, re.DOTALL)
                    if body_match:
                        report_body = body_match.group(1)
                        html_content += f"""
                            <div class="report-content">
                                {report_body}
                            </div>
                        """
                    else:
                        # If no body tag, include the whole content
                        html_content += f"""
                            <div class="report-content">
                                {report_content}
                            </div>
                        """
            except Exception as e:
                logger.error(f"Error reading report file {report_file}: {str(e)}")
    else:
        html_content += "<p>No reports available</p>"

    html_content += "</section>"

    # Add footer
    html_content += f"""
        </div>
        <footer>
            <p>IPL Cricket Data Dashboard - Generated on {timestamp}</p>
        </footer>
    </body>
    </html>
    """

    # Save HTML content to file
    with open(DATA_SUMMARY_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"HTML data content saved to {DATA_SUMMARY_HTML}")
    return DATA_SUMMARY_HTML

def main():
    """Main function to orchestrate the execution of all scrapers."""
    args = parse_arguments()

    try:
        # Handle check-images mode
        if args.check_images:
            logger.info("Running in check-images mode")
            duplicates_found, duplicates_resolved = check_duplicate_images()
            logger.info(f"Image check completed: found {duplicates_found} duplicates, resolved {duplicates_resolved}")
            # Generate data summaries even in check-images mode
            generate_data_summary()
            generate_html_data_content()
            return

        # Handle clean-only mode
        if args.only_clean:
            logger.info("Running in clean-only mode")
            clean_all_data(retain_latest=True)  # Changed to True to always retain latest
            logger.info("Clean-only mode completed successfully")
            # No data summary in clean-only mode as data was deleted
            return

        # Clean all data if requested
        if args.clean_all:
            logger.info("Cleaning all data directories before running scrapers")
            clean_all_data(retain_latest=True)  # Changed to True to always retain latest

        # Run all scrapers (either sequentially or in parallel)
        all_successful = run_all_scrapers(args)

        # Get today's date for protecting new files
        today_date = datetime.datetime.now().strftime("%Y%m%d")

        # Clean old data if all scrapers were successful (and delete all previous versions)
        if not args.clean_all:  # Don't clean twice if we already cleaned everything
            # Pass today's date to protect new files and delete all previous versions
            clean_old_data(all_successful, today_date=today_date)

        # Generate data summaries after all scrapers have run
        generate_data_summary()
        generate_html_data_content()

        logger.info("IPL Cricket Data orchestration completed")

    except Exception as e:
        logger.error(f"Error in orchestration script: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())

def extract_player_info(filename):
    """
    Extract player name and team information from an image filename.

    Args:
        filename (str): The filename of the player image

    Returns:
        tuple: (player_name, team_name) or None if extraction fails
    """
    try:
        # Remove file extension
        base_name = os.path.splitext(filename)[0]

        # Common patterns for player image filenames
        # Pattern 1: "PlayerName_TeamName"
        if '_' in base_name:
            parts = base_name.split('_')
            if len(parts) >= 2:
                player_name = parts[0].replace('-', ' ').title()
                team_name = parts[1].replace('-', ' ').title()
                return (player_name, team_name)

        # Pattern 2: "PlayerName-TeamName"
        if '-' in base_name:
            parts = base_name.split('-')
            if len(parts) >= 2:
                player_name = parts[0].replace('_', ' ').title()
                team_name = parts[-1].replace('_', ' ').title()
                return (player_name, team_name)

        # Pattern 3: Just the player name (team implied from directory)
        return (base_name.replace('-', ' ').replace('_', ' ').title(), None)

    except Exception as e:
        logger.error(f"Error extracting player info from filename {filename}: {str(e)}")
        return None

def is_valid_image(image_path):
    """
    Check if an image file is valid and can be opened.

    Args:
        image_path (str): Path to the image file

    Returns:
        bool: True if the image is valid, False otherwise
    """
    try:
        # Try to open the image with PIL
        with Image.open(image_path) as img:
            # Verify the image by loading it
            img.verify()

            # Check if the image has a valid size
            width, height = img.size
            if width < 10 or height < 10:
                logger.warning(f"Image too small: {image_path}, size: {width}x{height}")
                return False

            return True
    except (IOError, UnidentifiedImageError, OSError) as e:
        logger.warning(f"Invalid image file: {image_path}, Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error checking image {image_path}: {str(e)}")
        return False