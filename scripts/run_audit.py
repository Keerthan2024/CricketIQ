"""
Audit script for CricketIQ dashboard metrics against MongoDB data.
"""
from database.connection import get_db, close_client

db = get_db()
m = db['matches']
d = db['deliveries']

print("=" * 60)
print("CricketIQ Comprehensive Data Audit")
print("=" * 60)

# 1. Direct Document Counts
match_count = m.count_documents({})
delivery_count = d.count_documents({})
print(f"[1] Direct Document Counts:")
print(f"    matches collection   : {match_count:,}")
print(f"    deliveries collection: {delivery_count:,}")

# 2. Seasons Audit
seasons = sorted(m.distinct('season'), key=lambda s: str(s))
print(f"\n[2] Seasons in DB ({len(seasons)} seasons):")
for s in seasons:
    cnt = m.count_documents({'season': s})
    sample = m.find_one({'season': s}, {'date': 1, 'dates': 1})
    d_val = sample.get('date') or (sample.get('dates') or [''])[0]
    print(f"    Season {s:<10}: {cnt:>3} matches (e.g. date: {d_val})")

# 3. Runs Audit
run_stats = list(d.aggregate([
    {
        '$group': {
            '_id': None,
            'sum_total_runs': {'$sum': '$total_runs'},
            'sum_batter_runs': {'$sum': '$batter_runs'},
            'sum_extras_runs': {'$sum': '$extras_runs'},
            'formula_mismatch': {
                '$sum': {
                    '$cond': [
                        {'$ne': ['$total_runs', {'$add': ['$batter_runs', '$extras_runs']}]},
                        1,
                        0
                    ]
                }
            }
        }
    }
]))[0]

print(f"\n[3] Runs Calculation Audit:")
print(f"    Sum of 'total_runs'  : {run_stats['sum_total_runs']:,}")
print(f"    Sum of 'batter_runs' : {run_stats['sum_batter_runs']:,}")
print(f"    Sum of 'extras_runs' : {run_stats['sum_extras_runs']:,}")
print(f"    Batter + Extras sum  : {run_stats['sum_batter_runs'] + run_stats['sum_extras_runs']:,}")
print(f"    Formula mismatches   : {run_stats['formula_mismatch']}")

# 4. Wickets Audit
wicket_stats = list(d.aggregate([
    {
        '$group': {
            '_id': None,
            'wickets_not_null': {
                '$sum': {'$cond': [{'$ne': ['$wicket_kind', None]}, 1, 0]}
            },
            'batter_not_null': {
                '$sum': {'$cond': [{'$ne': ['$dismissed_batter', None]}, 1, 0]}
            }
        }
    }
]))[0]

print(f"\n[4] Wickets Calculation Audit:")
print(f"    Deliveries with wicket_kind != None      : {wicket_stats['wickets_not_null']:,}")
print(f"    Deliveries with dismissed_batter != None : {wicket_stats['batter_not_null']:,}")

# Breakdown by wicket_kind
kinds = list(d.aggregate([
    {'$match': {'wicket_kind': {'$ne': None}}},
    {'$group': {'_id': '$wicket_kind', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
]))
print("    Breakdown of wicket kinds:")
for k in kinds:
    print(f"      {k['_id']:<25}: {k['count']:,}")

# 5. Check if raw JSON files had multiple wickets on a single delivery
from pathlib import Path
from importer.parser import load_json_file
multi_wicket_deliveries = 0
for p in Path('./data').glob('*.json'):
    raw = load_json_file(p)
    if not raw: continue
    for inn in raw.get('innings', []):
        for over in inn.get('overs', []):
            for deliv in over.get('deliveries', []):
                w_list = deliv.get('wickets', [])
                if len(w_list) > 1:
                    multi_wicket_deliveries += 1
print(f"\n[5] Raw JSON multi-wicket deliveries check:")
print(f"    Deliveries with >1 wicket object in raw JSON: {multi_wicket_deliveries}")

close_client()
