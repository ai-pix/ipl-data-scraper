from bs4 import BeautifulSoup
import requests
import os
import datetime
from colorama import init, Fore, Style
import time
import urllib.parse
import re
import json

# Initialize colorama for colored console output
init()

# Define the team URLs
TEAM_URLS = [
    "https://www.iplt20.com/teams/chennai-super-kings",
    "https://www.iplt20.com/teams/delhi-capitals",
    "https://www.iplt20.com/teams/gujarat-titans",
    "https://www.iplt20.com/teams/kolkata-knight-riders",
    "https://www.iplt20.com/teams/lucknow-super-giants",
    "https://www.iplt20.com/teams/mumbai-indians",
    "https://www.iplt20.com/teams/punjab-kings",
    "https://www.iplt20.com/teams/rajasthan-royals",
    "https://www.iplt20.com/teams/royal-challengers-bangalore",
    "https://www.iplt20.com/teams/sunrisers-hyderabad"
]

# Define the folder to save images
PLAYER_IMAGES_FOLDER = 'player_images'
if not os.path.exists(PLAYER_IMAGES_FOLDER):
    os.makedirs(PLAYER_IMAGES_FOLDER)
    print(f"{Fore.GREEN}Created folder: {PLAYER_IMAGES_FOLDER}{Style.RESET_ALL}")

# Debug files folder
DEBUG_FILES_FOLDER = 'debug_files'
if not os.path.exists(DEBUG_FILES_FOLDER):
    os.makedirs(DEBUG_FILES_FOLDER)
    print(f"{Fore.GREEN}Created folder: {DEBUG_FILES_FOLDER}{Style.RESET_ALL}")

def fetch_team_page(team_url):
    """
    Fetch a team page from IPL website
    
    Args:
        team_url (str): URL of the team page
    
    Returns:
        BeautifulSoup object or None if request failed
    """
    team_name = team_url.split('/')[-1]
    print(f"{Fore.CYAN}Fetching {team_name} page from {team_url}...{Style.RESET_ALL}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(team_url, headers=headers)
        response.raise_for_status()
        
        # Save HTML for debugging
        debug_filename = os.path.join(DEBUG_FILES_FOLDER, f"{team_name}_player_images_page_{datetime.datetime.now().strftime('%Y%m%d')}.html")
        with open(debug_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"{Fore.GREEN}Saved HTML to {debug_filename}{Style.RESET_ALL}")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Network error fetching {team_name} page: {e}{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Unexpected error fetching {team_name} page: {e}{Style.RESET_ALL}")
        return None

def extract_player_image_urls(soup):
    """
    Extract player image URLs directly from the HTML
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        list: List of dictionaries with player info and image URLs
    """
    players = []
    
    # Find all player card elements
    player_cards = soup.select('.ih-pcard1')
    
    print(f"{Fore.YELLOW}Found {len(player_cards)} potential player cards on the page.{Style.RESET_ALL}")
    
    # Find all lazyload images with data-src
    images_with_data_src = soup.select('img.lazyload[data-src]')
    print(f"{Fore.YELLOW}Found {len(images_with_data_src)} images with data-src attributes.{Style.RESET_ALL}")
    
    for card in player_cards:
        # Get player link
        player_link = card.find('a')
        if not player_link:
            continue
            
        # Get player name from data-player_name attribute or text content
        player_name = player_link.get('data-player_name', '')
        if not player_name:
            name_elem = card.select_one('.ih-p-cont-in h3')
            if name_elem:
                player_name = name_elem.text.strip()
        
        # Get player ID from href attribute
        href = player_link.get('href', '')
        player_id = href.split('/')[-1].strip() if href else ''
        
        # Get player role
        role_elem = card.select_one('.d-block.w-100.text-center')
        role = role_elem.text.strip() if role_elem else ""
        
        # Find the image in this card
        img_elem = card.select_one('img.lazyload[data-src]')
        if img_elem and img_elem.get('data-src'):
            img_url = img_elem['data-src']
            
            # Extract the image ID from URL (e.g., 102.png from https://documents.iplt20.com/ipl/IPLHeadshot2025/102.png)
            img_id = img_url.split('/')[-1].split('.')[0] if img_url else ''
            
            players.append({
                "name": player_name,
                "role": role,
                "url_id": player_id,  # ID from URL
                "image_id": img_id,   # ID from image URL
                "image_url": img_url
            })
            print(f"{Fore.MAGENTA}Found player: {player_name} (Image ID: {img_id}){Style.RESET_ALL}")
    
    return players

def download_player_images(players, team_name):
    """
    Download player images to local folder
    
    Args:
        players: List of dictionaries containing player info and image URLs
        team_name: Name of the team
    
    Returns:
        list: List of dictionaries with updated download status
    """
    print(f"{Fore.CYAN}Downloading {len(players)} player images for {team_name}...{Style.RESET_ALL}")
    
    team_folder = os.path.join(PLAYER_IMAGES_FOLDER, team_name)
    if not os.path.exists(team_folder):
        os.makedirs(team_folder)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        # Add headers to accept AVIF format
        "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8"
    }
    
    for i, player in enumerate(players):
        try:
            if not player.get("image_url"):
                print(f"{Fore.YELLOW}No image URL for {player['name']} - skipping{Style.RESET_ALL}")
                player["download_status"] = "No image URL"
                continue
                
            # Create a valid filename from player name
            valid_filename = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in player["name"])
            valid_filename = valid_filename.replace(' ', '_')
            
            # Add role to filename if available
            if player.get("role"):
                role_text = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in player["role"])
                valid_filename = f"{valid_filename}_{role_text.replace(' ', '_')}"
            
            # Add image ID to ensure uniqueness
            if player.get("image_id"):
                valid_filename = f"{valid_filename}_{player['image_id']}"
            
            # Determine file extension from URL
            img_url = player["image_url"]
            if ".avif" in img_url.lower():
                file_extension = ".avif"
            elif ".webp" in img_url.lower():
                file_extension = ".webp"  
            elif ".png" in img_url.lower():
                file_extension = ".png"
            else:
                file_extension = ".jpg"  # Default
            
            # Create complete filename
            filename = f"{valid_filename}{file_extension}"
            filepath = os.path.join(team_folder, filename)
            
            # Check if file already exists
            if os.path.exists(filepath):
                print(f"{Fore.YELLOW}Image for {player['name']} already exists - skipping{Style.RESET_ALL}")
                player["download_status"] = "Already exists"
                player["local_path"] = filepath
                continue
                
            # Download the image
            print(f"{Fore.CYAN}[{i+1}/{len(players)}] Downloading image for {player['name']}...{Style.RESET_ALL}")
            response = requests.get(player["image_url"], headers=headers, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"{Fore.GREEN}Downloaded image for {player['name']} to {filepath}{Style.RESET_ALL}")
            
            # Update player info with download status and local path
            player["download_status"] = "Success"
            player["local_path"] = filepath
            
            # Sleep for a short time to avoid hammering the server
            time.sleep(0.5)
            
        except Exception as e:
            print(f"{Fore.RED}Error downloading image for {player['name']}: {e}{Style.RESET_ALL}")
            player["download_status"] = f"Error: {str(e)}"
            player["local_path"] = ""
    
    return players

def process_team(team_url):
    """
    Process a single team: fetch page, extract players, download images
    
    Args:
        team_url: URL of the team page
    
    Returns:
        dict: Summary of the download results
    """
    team_name = team_url.split('/')[-1]
    print(f"{Fore.CYAN}Processing team: {team_name}{Style.RESET_ALL}")
    
    # Fetch team page
    soup = fetch_team_page(team_url)
    
    if not soup:
        print(f"{Fore.RED}Failed to fetch page for {team_name}. Skipping.{Style.RESET_ALL}")
        return {
            "team_name": team_name,
            "team_url": team_url,
            "scraping_timestamp": datetime.datetime.now().isoformat(),
            "total_players": 0,
            "successful_downloads": 0,
            "error": "Failed to fetch page"
        }
    
    # Extract player images
    players = extract_player_image_urls(soup)
    
    if not players:
        print(f"{Fore.RED}No player images found for {team_name}.{Style.RESET_ALL}")
        return {
            "team_name": team_name,
            "team_url": team_url,
            "scraping_timestamp": datetime.datetime.now().isoformat(),
            "total_players": 0,
            "successful_downloads": 0,
            "error": "No player images found"
        }
    
    # Download player images
    players = download_player_images(players, team_name)
    
    # Count successful downloads
    success_count = sum(1 for player in players if player.get("download_status") in ["Success", "Already exists"])
    print(f"\n{Fore.GREEN}Successfully downloaded/found {success_count} out of {len(players)} player images for {team_name}.{Style.RESET_ALL}")
    
    # Create summary
    summary = {
        "team_name": team_name,
        "team_url": team_url,
        "scraping_timestamp": datetime.datetime.now().isoformat(),
        "total_players": len(players),
        "successful_downloads": success_count,
        "players": players
    }
    
    # Save summary to file
    summary_file = os.path.join(PLAYER_IMAGES_FOLDER, team_name, f'download_summary_{datetime.datetime.now().strftime("%Y%m%d")}.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)
    
    print(f"{Fore.GREEN}Summary saved to {summary_file}{Style.RESET_ALL}")
    return summary

def main():
    """Main function to run the IPL player images scraper"""
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    IPL PLAYER IMAGES SCRAPER        {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    
    start_time = datetime.datetime.now()
    print(f"Scraping started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Process each team and collect summaries
    all_summaries = []
    for team_url in TEAM_URLS:
        team_summary = process_team(team_url)
        all_summaries.append(team_summary)
        print(f"{Fore.CYAN}--------------------------------------{Style.RESET_ALL}")
    
    # Calculate overall statistics
    total_players = sum(summary["total_players"] for summary in all_summaries)
    total_success = sum(summary["successful_downloads"] for summary in all_summaries)
    
    # Print overall summary
    print(f"\n{Fore.GREEN}OVERALL SUMMARY:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Total players found: {total_players}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Total images downloaded/found: {total_success}{Style.RESET_ALL}")
    
    # Save overall summary
    overall_summary = {
        "scraping_timestamp": datetime.datetime.now().isoformat(),
        "total_teams": len(TEAM_URLS),
        "total_players": total_players,
        "total_successful_downloads": total_success,
        "team_summaries": all_summaries
    }
    
    overall_summary_file = os.path.join(PLAYER_IMAGES_FOLDER, f'overall_summary_{datetime.datetime.now().strftime("%Y%m%d")}.json')
    with open(overall_summary_file, 'w', encoding='utf-8') as f:
        json.dump(overall_summary, f, indent=4)
    
    print(f"{Fore.GREEN}Overall summary saved to {overall_summary_file}{Style.RESET_ALL}")
    
    end_time = datetime.datetime.now()
    print(f"\n{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"Scraping finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time taken: {end_time - start_time}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")

if __name__ == "__main__":
    main()