"""
Test ID extraction for a single movie (Bad Ben)
"""
import requests
from bs4 import BeautifulSoup
import re

url = "https://letterboxd.com/film/bad-ben/"

print(f"Fetching: {url}")
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
response.raise_for_status()

soup = BeautifulSoup(response.content, 'html.parser')

# Extract title
title_elem = soup.find('h1', class_='headline-1')
if title_elem:
    title = title_elem.get_text(strip=True)
    print(f"Title: {title}")

# Extract year
year_elem = soup.find('small', class_='number')
if year_elem:
    year_text = year_elem.get_text(strip=True)
    year_match = re.search(r'(\d{4})', year_text)
    if year_match:
        print(f"Year: {year_match.group(1)}")

# Extract TMDB ID (just use data-track-action, not class)
tmdb_link = soup.find('a', attrs={'data-track-action': 'TMDB'})
if tmdb_link:
    tmdb_href = tmdb_link.get('href', '')
    print(f"TMDB href: {tmdb_href}")
    tmdb_match = re.search(r'/(movie|tv)/(\d+)/', tmdb_href)
    if tmdb_match:
        print(f"✓ TMDB ID: {tmdb_match.group(2)} (type: {tmdb_match.group(1)})")
    else:
        print("✗ TMDB regex didn't match")
else:
    print("✗ No TMDB link found")

# Extract IMDb ID (just use data-track-action, not class)
imdb_link = soup.find('a', attrs={'data-track-action': 'IMDb'})
if imdb_link:
    imdb_href = imdb_link.get('href', '')
    print(f"IMDb href: {imdb_href}")
    imdb_match = re.search(r'/title/(tt\d+)/?', imdb_href)
    if imdb_match:
        print(f"✓ IMDb ID: {imdb_match.group(1)}")
    else:
        print("✗ IMDb regex didn't match")
else:
    print("✗ No IMDb link found")

# Debug: Print all micro-buttons found
print("\nAll micro-buttons on page:")
all_micro_buttons = soup.find_all('a', class_='micro-button')
for btn in all_micro_buttons:
    track_action = btn.get('data-track-action', 'N/A')
    href = btn.get('href', 'N/A')
    print(f"  - {track_action}: {href}")

# Debug: Print all links with data-track-action
print("\nAll links with data-track-action:")
all_track_links = soup.find_all('a', attrs={'data-track-action': True})
for link in all_track_links:
    track_action = link.get('data-track-action')
    href = link.get('href', 'N/A')
    classes = link.get('class', [])
    print(f"  - {track_action}: {href} (classes: {classes})")
