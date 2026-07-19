"""
fetch_games.py

Pulls a player's game history from chess.com's public PubAPI
(https://api.chess.com/pub/) -- no authentication or API key required,
since it only serves data that's already publicly visible on the site.
"""

import json
import time
from pathlib import Path

import requests

BASE_URL = "https://api.chess.com/pub/player/{username}/games/archives"

# chess.com asks that requests identify a real client -- a descriptive
# User-Agent is good practice and avoids being mistaken for abusive traffic.
HEADERS = {"User-Agent": "chess-analytics-portfolio-project (personal use)"}


def get_archive_urls(username: str) -> list[str]:
    """Returns the list of monthly archive URLs available for a player."""
    resp = requests.get(BASE_URL.format(username=username), headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get("archives", [])


def fetch_games_for_month(archive_url: str) -> list[dict]:
    """Fetches all games from a single monthly archive URL."""
    resp = requests.get(archive_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get("games", [])


def fetch_all_games(username: str, max_months: int | None = None,
                     save_dir: str | None = None) -> list[dict]:
    """
    Fetches a player's full game history (or the most recent `max_months`
    of it). Optionally saves raw JSON per month to `save_dir` so you don't
    need to re-hit the API on every run while iterating on analysis code.
    """
    archives = get_archive_urls(username)
    if max_months:
        archives = archives[-max_months:]  # most recent N months

    all_games = []
    for i, archive_url in enumerate(archives):
        games = fetch_games_for_month(archive_url)
        all_games.extend(games)

        if save_dir:
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            month_tag = archive_url.rstrip("/").split("/")[-2:]
            out_path = Path(save_dir) / f"{'-'.join(month_tag)}.json"
            with open(out_path, "w") as f:
                json.dump(games, f)

        print(f"[{i+1}/{len(archives)}] Fetched {len(games)} games from {archive_url}")
        time.sleep(0.5)  # be polite to a free, unauthenticated public API

    return all_games


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch chess.com game history for a player.")
    parser.add_argument("username", help="chess.com username")
    parser.add_argument("--months", type=int, default=3, help="Number of most recent months to fetch")
    parser.add_argument("--save-dir", default="../sample_data/raw_games")
    args = parser.parse_args()

    games = fetch_all_games(args.username, max_months=args.months, save_dir=args.save_dir)
    print(f"\nTotal games fetched: {len(games)}")