"""
main.py

Orchestrates the full pipeline for a chess.com username:
    fetch games -> parse PGNs -> run Stockfish analysis -> export CSVs

Output: two CSVs ready to load into Snowflake (or any warehouse) --
    games.csv          -- one row per game (metadata, result, ratings)
    move_evaluations.csv -- one row per analyzed move (eval, blunder classification, clock time)

Usage:
    python main.py your_username --months 3 --target-only
"""

import argparse
import csv
from dataclasses import asdict

from fetch_games import fetch_all_games
from parse_games import parse_games_batch
from engine_analysis import EngineAnalyzer


def run_pipeline(username: str, months: int, target_only: bool,
                  stockfish_path: str, depth: int, out_dir: str) -> None:
    print(f"Fetching games for {username} (last {months} months)...")
    raw_games = fetch_all_games(username, max_months=months)
    print(f"Fetched {len(raw_games)} games total.\n")

    print("Parsing PGNs...")
    game_records, move_records = parse_games_batch(raw_games)
    print(f"Parsed {len(game_records)} games, {len(move_records)} total moves.\n")

    print(f"Running Stockfish analysis (depth={depth})... this is the slow part.")
    all_evaluations = []
    moves_by_game: dict[str, list] = {}
    for m in move_records:
        moves_by_game.setdefault(m.game_id, []).append(m)

    with EngineAnalyzer(stockfish_path=stockfish_path, depth=depth) as analyzer:
        for i, game in enumerate(game_records):
            game_moves = moves_by_game.get(game.game_id, [])
            target_color = None
            if target_only:
                if game.white.lower() == username.lower():
                    target_color = "white"
                elif game.black.lower() == username.lower():
                    target_color = "black"

            evals = analyzer.analyze_game(game.game_id, game_moves, target_color=target_color)
            all_evaluations.extend(evals)

            if (i + 1) % 5 == 0 or (i + 1) == len(game_records):
                print(f"  Analyzed {i + 1}/{len(game_records)} games")

    print(f"\nTotal moves evaluated: {len(all_evaluations)}\n")

    games_path = f"{out_dir}/games.csv"
    with open(games_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(game_records[0]).keys()) if game_records else [])
        writer.writeheader()
        for g in game_records:
            writer.writerow(asdict(g))

    moves_path = f"{out_dir}/move_evaluations.csv"
    with open(moves_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(all_evaluations[0]).keys()) if all_evaluations else [])
        writer.writeheader()
        for e in all_evaluations:
            writer.writerow(asdict(e))

    print(f"Saved: {games_path}")
    print(f"Saved: {moves_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chess.com game analytics pipeline with Stockfish blunder detection.")
    parser.add_argument("username", help="chess.com username to analyze")
    parser.add_argument("--months", type=int, default=3, help="How many recent months of games to pull")
    parser.add_argument("--target-only", action="store_true",
                         help="Only analyze moves made by `username`, not both players (faster)")
    parser.add_argument("--stockfish-path", default="/usr/games/stockfish",
                         help="Path to the stockfish binary")
    parser.add_argument("--depth", type=int, default=12, help="Engine search depth (higher = slower, more accurate)")
    parser.add_argument("--out-dir", default="../sample_output")
    args = parser.parse_args()

    run_pipeline(
        username=args.username,
        months=args.months,
        target_only=args.target_only,
        stockfish_path=args.stockfish_path,
        depth=args.depth,
        out_dir=args.out_dir,
    )