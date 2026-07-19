import csv
from collections import defaultdict

with open('../sample_output/games.csv') as f:
    games = list(csv.DictReader(f))

USERNAME = 'rohanbaz'

stats = defaultdict(lambda: {'played': 0, 'wins': 0, 'losses': 0, 'draws': 0})

for g in games:
    eco = g['eco'] or 'Unknown'
    is_white = g['white'].lower() == USERNAME.lower()
    result = g['result']

    stats[eco]['played'] += 1

    if result == '1/2-1/2':
        stats[eco]['draws'] += 1
    elif (is_white and result == '1-0') or (not is_white and result == '0-1'):
        stats[eco]['wins'] += 1
    else:
        stats[eco]['losses'] += 1

print(f"{'ECO':<8} {'Games':<8} {'Wins':<6} {'Losses':<8} {'Draws':<7} {'Win rate'}")
for eco, s in sorted(stats.items(), key=lambda x: -x[1]['played']):
    win_rate = 100 * s['wins'] / s['played']
    print(f"{eco:<8} {s['played']:<8} {s['wins']:<6} {s['losses']:<8} {s['draws']:<7} {win_rate:.1f}%")