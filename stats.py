import csv

with open('../sample_output/games.csv') as f:
    games = list(csv.DictReader(f))

with open('../sample_output/move_evaluations.csv') as f:
    moves = list(csv.DictReader(f))

wins = sum(1 for g in games if (g['white']=='rohanbaz' and g['result']=='1-0') or (g['black']=='rohanbaz' and g['result']=='0-1'))
losses = sum(1 for g in games if (g['white']=='rohanbaz' and g['result']=='0-1') or (g['black']=='rohanbaz' and g['result']=='1-0'))
draws = len(games) - wins - losses

blunders = sum(1 for m in moves if m['classification']=='blunder')
mistakes = sum(1 for m in moves if m['classification']=='mistake')

print(f'Total games: {len(games)}')
print(f'Wins: {wins}, Losses: {losses}, Draws: {draws}')
print(f'Total moves analyzed: {len(moves)}')
print(f'Blunders: {blunders} ({100*blunders/len(moves):.1f}%)')
print(f'Mistakes: {mistakes} ({100*mistakes/len(moves):.1f}%)')