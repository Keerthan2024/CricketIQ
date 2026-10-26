# CricketIQ -- MongoDB Database Schema

## Database: CricketIQ

### Collection: matches

Stores one document per IPL match.

| Field            | Type              | Description                                    |
|------------------|-------------------|------------------------------------------------|
| match_id         | string (unique)   | Cricsheet file stem (e.g. "335982") or SHA-1   |
| date             | string YYYY-MM-DD | First date of the match                        |
| season           | string            | IPL season (e.g. "2023" or "2007/08")          |
| teams            | string[]          | Original raw team names from match             |
| canonical_teams  | string[]          | Normalized canonical franchise names           |
| venue            | string            | Stadium name                                   |
| city             | string (optional) | City                                           |
| toss_winner      | string            | Team that won the toss (raw)                   |
| canonical_toss_winner | string       | Canonical franchise that won the toss          |
| toss_decision    | string            | "bat" or "field"                               |
| winner           | string (optional) | Match winner; null if no result/tie (raw)      |
| canonical_winner | string (optional) | Canonical franchise winner                     |
| result           | string            | Human-readable result string                   |
| player_of_match  | string[]          | Player(s) of the match                         |
| match_type       | string            | "T20"                                          |
| event_name       | string (optional) | Event name from Cricsheet                      |
| source_file      | string            | Original JSON filename                         |
| meta_data_version| string            | Cricsheet JSON version used                    |

**Indexes:**
- match_id (unique)
- season
- teams (multikey)
- venue
- date
- winner

---

### Collection: deliveries

Stores one document per ball bowled.

| Field            | Type              | Description                                     |
|------------------|-------------------|-------------------------------------------------|
| match_id         | string            | FK to matches.match_id                          |
| season           | string            | Denormalised for efficient season filtering     |
| innings          | int               | 1 or 2 (or 3/4 for super overs)                |
| batting_team     | string            | Team currently batting (raw)                    |
| canonical_batting_team | string      | Canonical franchise batting                     |
| bowling_team     | string            | Team currently bowling (raw)                    |
| canonical_bowling_team | string      | Canonical franchise bowling                     |
| over             | int               | Over number (0-indexed, as in Cricsheet)        |
| delivery         | int               | Delivery within the over (1-indexed)            |
| batter           | string            | Batter facing the ball                          |
| non_striker      | string (optional) | Non-striking batter                             |
| bowler           | string            | Bowler delivering the ball                      |
| batter_runs      | int               | Runs scored by the batter off this ball         |
| extras_runs      | int               | Total extra runs on this delivery               |
| total_runs       | int               | batter_runs + extras_runs                       |
| extras           | object (optional) | {wides, noballs, byes, legbyes, penalty}        |
| wicket_kind      | string (optional) | Dismissal type; null if no wicket               |
| dismissed_batter | string (optional) | Batter dismissed; null if no wicket             |
| fielders         | string[]          | Fielders involved in dismissal                  |

**Composite unique index:** (match_id, innings, over, delivery, batter)

**Additional indexes:**
- match_id
- batter
- bowler
- batting_team
- bowling_team
- season (for filtering)
- wicket_kind

---

## Design Decisions

1. **Season denormalised in deliveries** -- Avoids a  against matches for every seasonal
   delivery aggregation. This is the standard trade-off for analytical workloads.

2. **No delivery-level venue** -- Venue is in matches only. Venue aggregations use .

3. **Stable match_id** -- Uses Cricsheet numeric file stem when available; SHA-1 fallback
   ensures safe re-import without duplicates.

4. **Cricsheet extras object preserved** -- Stored as-is so downstream aggregations can
   correctly compute wides, no-balls, byes, and leg-byes separately.
