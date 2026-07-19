"""
engine_analysis.py

Runs each parsed game through the Stockfish engine to evaluate move quality.
For every move made by the player we're analyzing, we compare the engine's
evaluation of the position immediately before the move to the evaluation
immediately after -- the drop in evaluation (in centipawns, from the mover's
perspective) tells us how much the move worsened their position relative to
the engine's assessment of best play.

Classification thresholds:
    >= 300 centipawns lost  -> blunder
    100-299                  -> mistake
    50-99                     -> inaccuracy
    < 50                       -> ok

Requires a local Stockfish installation.
"""

from dataclasses import dataclass

import chess
import chess.engine

from parse_games import MoveRecord

MATE_SCORE_CP = 10000  # centipawn value used to represent a forced mate, for comparison purposes


@dataclass
class MoveEvaluation:
    game_id: str
    ply: int
    color: str
    san: str
    clock_seconds: int | None
    eval_before_cp: int
    eval_after_cp: int
    centipawn_loss: int
    classification: str  # "blunder" | "mistake" | "inaccuracy" | "ok"


def _score_to_cp(score: chess.engine.PovScore, pov_color: bool) -> int:
    """Converts a python-chess PovScore to a plain centipawn int from the given color's perspective."""
    pov_score = score.pov(pov_color)
    if pov_score.is_mate():
        mate_in = pov_score.mate()
        sign = 1 if mate_in > 0 else -1
        return sign * (MATE_SCORE_CP - abs(mate_in))
    return pov_score.score()


def _classify(centipawn_loss: int) -> str:
    if centipawn_loss >= 300:
        return "blunder"
    if centipawn_loss >= 100:
        return "mistake"
    if centipawn_loss >= 50:
        return "inaccuracy"
    return "ok"


class EngineAnalyzer:
    def __init__(self, stockfish_path: str = "/usr/games/stockfish", depth: int = 12):
        """
        depth controls analysis quality vs. speed. Depth 12 is reasonably
        fast and good enough to catch real blunders/mistakes. Raise it
        (e.g. 18-20) for more precise evaluations at the cost of
        significantly more time.
        """
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        self.depth = depth

    def close(self):
        self.engine.quit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _evaluate(self, board: chess.Board, pov_color: bool) -> int:
        if board.is_checkmate():
            # The side to move has been mated -- that side's score is
            # "as bad as it gets", the other side's is "as good as it gets".
            # No engine search is possible here since there are no legal moves.
            side_to_move_is_pov = board.turn == pov_color
            return -MATE_SCORE_CP if side_to_move_is_pov else MATE_SCORE_CP
        if board.is_stalemate() or board.is_insufficient_material():
            return 0  # drawn position, roughly neutral regardless of POV
        info = self.engine.analyse(board, chess.engine.Limit(depth=self.depth))
        return _score_to_cp(info["score"], pov_color)

    def analyze_game(self, game_id: str, moves: list[MoveRecord],
                      target_color: str | None = None) -> list[MoveEvaluation]:
        """
        Analyzes every move in a game. If target_color is set ("white" or
        "black"), only moves by that color are evaluated (saves ~half the
        engine calls when you only care about one player's move quality).
        If None, evaluates every move.
        """
        evaluations = []
        board = chess.Board()

        # Cache: eval of the position before move N == eval of the position
        # after move N-1, so each position only needs to be evaluated once.
        prev_eval_white_pov = self._evaluate(board, chess.WHITE)

        for move_rec in moves:
            board_before = chess.Board(move_rec.fen_before)
            move = board_before.parse_san(move_rec.san)
            eval_before_white_pov = prev_eval_white_pov

            board_before.push(move)
            eval_after_white_pov = self._evaluate(board_before, chess.WHITE)
            prev_eval_white_pov = eval_after_white_pov

            if target_color and move_rec.color != target_color:
                continue

            pov_is_white = move_rec.color == "white"
            eval_before = eval_before_white_pov if pov_is_white else -eval_before_white_pov
            eval_after = eval_after_white_pov if pov_is_white else -eval_after_white_pov

            centipawn_loss = max(0, eval_before - eval_after)

            evaluations.append(MoveEvaluation(
                game_id=game_id,
                ply=move_rec.ply,
                color=move_rec.color,
                san=move_rec.san,
                clock_seconds=move_rec.clock_seconds,
                eval_before_cp=eval_before,
                eval_after_cp=eval_after,
                centipawn_loss=centipawn_loss,
                classification=_classify(centipawn_loss),
            ))

        return evaluations