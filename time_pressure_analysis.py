import csv

with open('../sample_output/move_evaluations.csv') as f:
    moves = list(csv.DictReader(f))

def bucket(clock_seconds):
    s = int(clock_seconds)
    if s < 30:
        return "under_30s"
    elif s < 60:
        return "30_to_60s"
    elif s < 120:
        return "1_to_2min"
    else:
        return "over_2min"

buckets = {}
for m in moves:
    if not m['clock_seconds']:
        continue
    b = bucket(m['clock_seconds'])
    buckets.setdefault(b, {'total': 0, 'blunders': 0})
    buckets[b]['total'] += 1
    if m['classification'] == 'blunder':
        buckets[b]['blunders'] += 1

print(f"{'Time bucket':<15} {'Total moves':<15} {'Blunders':<12} {'Blunder rate'}")
for b in ['under_30s', '30_to_60s', '1_to_2min', 'over_2min']:
    if b in buckets:
        total = buckets[b]['total']
        blunders = buckets[b]['blunders']
        rate = 100 * blunders / total
        print(f"{b:<15} {total:<15} {blunders:<12} {rate:.1f}%")