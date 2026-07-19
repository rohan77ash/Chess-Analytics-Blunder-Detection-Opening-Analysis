"""
parse_games.py

Parses chess.com PGN game data (as returned by the PubAPI) into structured
per-game and per-move records, using python-chess to walk the move tree.

chess.com PGNs embed clock time remaining as a comment on each move, e.g.:
    1. e4 {[%clk 0:09:58]} 1... e5 {[%clk 0:09:57]}
This is what lets us later correlate move quality with time pressure.
"""

import io
import re
from dataclasses import dataclass, asdict

import chess
import chess.pgn

CLOCK_PATTERN = re.compile(r"\[%clk\s+(\d+):(\d{2}):(\d{2})(?:\.\d+)?\]")


@dataclass
class GameRecord:
    game_id: str
    date: str
    white: str
    black: str
    white_elo: int | None
    black_elo: int | None
    result: str          # "1-0", "0-1", "1/2-1/2"
    time_control: str
    eco: str | None
    termination: str | None


@dataclass
class MoveRecord:
    game_id: str
    ply: int              # 1-indexed half-move number
    move_number: int       # full move number (e.g. move 12 = plies 23,24)
    color: str             # "white" | "black"
    san: str                # move in standard algebraic notation, e.g. "Nf3"
    clock_seconds: int | None
    fen_before: str          # board position before the move -- needed for engine analysis


def _clock_to_seconds(comment: str) -> int | None:
    match = CLOCK_PATTERN.search(comment or "")
    if not match:
        return None
    h, m, s = (int(x) for x in match.groups())
    return h * 3600 + m * 60 + s


def parse_game(pgn_text: str, game_id: str) -> tuple[GameRecord, list[MoveRecord]]:
    """Parses a single PGN string into a GameRecord and its list of MoveRecords."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError(f"Could not parse PGN for game {game_id}")

    headers = game.headers
    game_record = GameRecord(
        game_id=game_id,
        date=headers.get("Date", ""),
        white=headers.get("White", ""),
        black=headers.get("Black", ""),
        white_elo=int(headers["WhiteElo"]) if headers.get("WhiteElo", "").isdigit() else None,
        black_elo=int(headers["BlackElo"]) if headers.get("BlackElo", "").isdigit() else None,
        result=headers.get("Result", ""),
        time_control=headers.get("TimeControl", ""),
        eco=headers.get("ECO"),
        termination=headers.get("Termination"),
    )

    moves: list[MoveRecord] = []
    board = game.board()
    node = game
    ply = 0

    while node.variations:
        next_node = node.variations[0]
        fen_before = board.fen()
        move = next_node.move
        san = board.san(move)

        ply += 1
        color = "white" if board.turn == chess.WHITE else "black"
        move_number = (ply + 1) // 2

        moves.append(MoveRecord(
            game_id=game_id,
            ply=ply,
            move_number=move_number,
            color=color,
            san=san,
            clock_seconds=_clock_to_seconds(next_node.comment),
            fen_before=fen_before,
        ))

        board.push(move)
        node = next_node

    return game_record, moves


def parse_games_batch(raw_games: list[dict]) -> tuple[list[GameRecord], list[MoveRecord]]:
    """
    Parses a batch of raw game dicts (as returned by chess.com's API,
    each with a "pgn" field and a "url" field used as a unique ID).
    Skips games that fail to parse (e.g. malformed/aborted games) rather
    than failing the whole batch.
    """
    all_game_records = []
    all_move_records = []

    for raw in raw_games:
        game_id = raw.get("url", "").rstrip("/").split("/")[-1] or raw.get("uuid", "unknown")
        pgn_text = raw.get("pgn")
        if not pgn_text:
            continue
        try:
            game_record, moves = parse_game(pgn_text, game_id)
            all_game_records.append(game_record)
            all_move_records.extend(moves)
        except Exception as e:
            print(f"Skipping game {game_id}: {e}")

    return all_game_records, all_move_records