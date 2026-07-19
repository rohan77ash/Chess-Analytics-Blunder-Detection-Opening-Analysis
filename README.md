# Chess Analytics: Blunder Detection & Opening Analysis Pipeline

An end-to-end data pipeline that pulls my own chess.com game history, replays
every move through the Stockfish chess engine to measure move quality, and
structures the results for analysis in Snowflake/Power BI -- answering real
questions like *"do I blunder more when my clock is low?"* and *"which
openings am I actually winning with?"*

This is run against my own real chess.com game history.

## Real results from my own games

Running the pipeline against my last 3 years of chess.com games:

- **16 games analyzed** (2 wins, 13 losses, 1 draw -- I'm not a strong player, but that's exactly what makes this interesting to analyze)
- **461 of my own moves evaluated** by Stockfish
- **12.4% of my moves were blunders** (57 moves)
- **20.6% were mistakes** (95 moves)

These numbers come directly from `sample_output/games.csv` and
`sample_output/move_evaluations.csv` -- real output from the pipeline below,
not fabricated data.

## Real finding: time pressure analysis

Checking blunder rate against clock time remaining (from my own 461 analyzed moves):

| Time remaining | Moves | Blunders | Blunder rate |
|---|---|---|---|
| Under 30s | 20 | 0 | 0.0% |
| 30-60s | 23 | 3 | 13.0% |
| 1-2 min | 18 | 5 | 27.8% |
| Over 2 min | 400 | 49 | 12.2% |

**Honest takeaway:** no clean "more time pressure = more blunders" pattern
emerged -- the worst bucket was actually 1-2 minutes remaining, not the more
extreme under-30-seconds bucket. Sample sizes in the low-time buckets are
small (18-23 moves), so this isn't a statistically strong conclusion -- it
would need many more games of data to say anything confident about my own
time-pressure tendencies. This is a good example of why small personal
datasets need to be read cautiously rather than over-interpreted.

## Why this is more than a stats dashboard

Most "personal analytics" projects just aggregate counts (wins, losses,
average rating). This pipeline does real move-level analysis: every move
I make is evaluated by a chess engine and compared to what the engine
considers the best move in that position, producing an objective measure
of move quality -- not just win/loss outcome, which can be misleading
(you can play a great game and still lose, or blunder badly and still win
if your opponent blunders back).

Combined with the clock time embedded in chess.com's game data, this lets
me correlate move quality with time pressure -- a genuinely interesting,
non-generic analytical question.

## Pipeline

fetch_games.py       --> pulls game history from chess.com's public PubAPI (no auth needed)
parse_games.py         --> parses PGN move data + clock times into structured records
engine_analysis.py      --> runs Stockfish on every position, classifies move quality
main.py                   --> orchestrates the full run, exports CSVs for warehouse loading
schema.sql                 --> suggested Snowflake table DDL + example analysis queries

## How move quality is measured

For every move, the engine's evaluation of the position **before** the move
is compared to its evaluation **after** the move (both from the mover's
perspective, in centipawns -- 100 centipawns is roughly the value of one
pawn). The drop in evaluation is the "centipawn loss" for that move:

| Centipawn loss | Classification |
|---|---|
| 300+ | blunder |
| 100-299 | mistake |
| 50-99 | inaccuracy |
| < 50 | ok |

These thresholds follow the same rough convention used by chess.com and
lichess's own analysis boards.

## Setup & running it

**1. Install Stockfish** (the chess engine -- free, open source):
- Windows: download from stockfishchess.org
- Mac: `brew install stockfish`
- Linux: `sudo apt install stockfish`

**2. Install Python dependencies:**
```bash
pip install -r requirements.txt
```

**3. Run the pipeline against a chess.com username:**
```bash
cd src
python main.py your_chesscom_username --months 36 --target-only --stockfish-path "path/to/stockfish.exe"
```

- `--months`: how many recent months of game history to pull
- `--target-only`: only analyze your own moves, not your opponents' too
- `--depth`: engine search depth (default 12). Higher = more accurate but much slower

This produces `games.csv` and `move_evaluations.csv` in `sample_output/`,
ready to load into Snowflake using the schema in `schema.sql`.

## Analysis ideas once it's in Snowflake/Power BI

- Blunder rate by time remaining on the clock (time pressure analysis)
- Win rate by opening (ECO code)
- Move quality trend over time -- am I actually improving?
- Blunder rate by color (white vs. black)
- Move quality by time control (bullet vs. blitz vs. rapid)

`schema.sql` includes example queries for the first two.

## Known limitations / honest scope notes

- Engine depth is a real speed/accuracy trade-off -- this project uses a
  modest default depth (12) to keep runtime reasonable for a personal
  dataset.
- Only chess.com is supported (its PubAPI needs no authentication, which
  keeps setup simple).
- The engine runs locally and sequentially -- for large histories, this
  could be parallelized across multiple engine processes.
- Time-pressure sample sizes are small for a 16-game dataset -- more games
  would be needed for statistically confident conclusions.

## Tech stack

Python, python-chess, Stockfish (local chess engine), chess.com PubAPI, Snowflake, Power BI.
