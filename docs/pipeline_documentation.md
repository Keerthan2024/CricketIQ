# CricketIQ -- MongoDB Aggregation Pipeline Technical Reference

This document provides a comprehensive academic and engineering reference for the MongoDB aggregation pipelines used in the **CricketIQ IPL Big Data Analytics System**. It explains the pipeline stages, mathematical operations, indexing strategies, and big data optimization rationale.

---

## 1. Architectural Overview of Aggregation in MongoDB

In Big Data analytics, processing large volumes of semi-structured event logs (ball-by-ball deliveries) at query time requires moving computation directly into the database engine to minimize network I/O. MongoDB's **Aggregation Framework** is modeled as a multi-stage data processing pipeline where documents flow sequentially through optimized C++ native execution stages.

```
Raw Documents (deliveries/matches)
       |
       v
  [$match]      <-- Filters early using B-tree indexes (reduces working set)
       |
       v
  [$group]      <-- Accumulates metrics (sums, counts, averages, sets)
       |
       v
 [$project]     <-- Computes derived formulas (strike rates, economy, boundaries)
       |
       v
  [$sort]       <-- Orders by analytical metrics (runs, wickets, win %)
       |
       v
  [$limit]      <-- Limits output volume for dashboard consumption
```

---

## 2. Core Aggregation Pipelines

### Pipeline 1: Top Run Scorers (`q1_top_run_scorers`)

* **Target Collection**: `deliveries`
* **Analytical Purpose**: Calculate career or seasonal batting aggregate runs, balls faced, strike rates, fours, sixes, and innings played for all batters.

```javascript
[
  // Stage 1: Optional Season Filter (uses multikey/compound index)
  { $match: { season: "2023" } },

  // Stage 2: Group by Batter and Accumulate
  {
    $group: {
      _id: "$batter",
      total_runs: { $sum: "$batter_runs" },
      // Ball count excludes wides (Rule: wide ball does not count as legal ball faced)
      balls_faced: {
        $sum: {
          $cond: [{ $ifNull: ["$extras.wides", false] }, 0, 1]
        }
      },
      fours: {
        $sum: { $cond: [{ $eq: ["$batter_runs", 4] }, 1, 0] }
      },
      sixes: {
        $sum: { $cond: [{ $eq: ["$batter_runs", 6] }, 1, 0] }
      },
      matches: { $addToSet: "$match_id" }
    }
  },

  // Stage 3: Derived Statistical Computations
  {
    $project: {
      batter: "$_id",
      total_runs: 1,
      balls_faced: 1,
      fours: 1,
      sixes: 1,
      innings: { $size: "$matches" },
      strike_rate: {
        $cond: [
          { $gt: ["$balls_faced", 0] },
          { $round: [{ $multiply: [{ $divide: ["$total_runs", "$balls_faced"] }, 100] }, 2] },
          0.0
        ]
      }
    }
  },

  // Stage 4: Order by Highest Run Aggregate
  { $sort: { total_runs: -1 } },

  // Stage 5: Output Top N
  { $limit: 10 }
]
```

**Optimization & Indexing**:
- Relies on `{ season: 1, batter: 1 }` index for direct stage-1 filtering.
- Uses `$addToSet` to count distinct matches without requiring an expensive secondary lookup.

---

### Pipeline 2: Top Wicket Takers (`q2_top_wicket_takers`)

* **Target Collection**: `deliveries`
* **Analytical Purpose**: Calculate bowler statistics adhering strictly to ICC cricket rules (run-outs, obstructing the field, and retired hurt are NOT credited to the bowler).

```javascript
[
  // Stage 1: Match deliveries Bowled in Specified Season
  { $match: { season: "2023" } },

  // Stage 2: Group by Bowler
  {
    $group: {
      _id: "$bowler",
      // Bowler runs conceded = batter_runs + wides + noballs (excludes byes and leg-byes)
      runs_conceded: {
        $sum: {
          $add: [
            "$batter_runs",
            { $ifNull: ["$extras.wides", 0] },
            { $ifNull: ["$extras.noballs", 0] }
          ]
        }
      },
      // Legal balls: excludes wides and no-balls
      legal_balls: {
        $sum: {
          $cond: [
            {
              $or: [
                { $gt: [{ $ifNull: ["$extras.wides", 0] }, 0] },
                { $gt: [{ $ifNull: ["$extras.noballs", 0] }, 0] }
              ]
            },
            0,
            1
          ]
        }
      },
      // Wickets: bowler-credited dismissals only
      wickets: {
        $sum: {
          $cond: [
            {
              $in: [
                "$wicket_kind",
                ["bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"]
              ]
            },
            1,
            0
          ]
        }
      },
      matches: { $addToSet: "$match_id" }
    }
  },

  // Stage 3: Compute Overs, Economy Rate, Bowling Average
  {
    $project: {
      bowler: "$_id",
      wickets: 1,
      runs_conceded: 1,
      legal_balls: 1,
      overs: { $round: [{ $divide: ["$legal_balls", 6] }, 1] },
      economy: {
        $cond: [
          { $gt: ["$legal_balls", 0] },
          { $round: [{ $multiply: [{ $divide: ["$runs_conceded", "$legal_balls"] }, 6] }, 2] },
          0.0
        ]
      },
      average: {
        $cond: [
          { $gt: ["$wickets", 0] },
          { $round: [{ $divide: ["$runs_conceded", "$wickets"] }, 2] },
          null
        ]
      }
    }
  },

  // Stage 4: Order by Wickets (descending) and Economy (ascending)
  { $sort: { wickets: -1, economy: 1 } },
  { $limit: 10 }
]
```

---

### Pipeline 3: Win Margin Distribution (`q3_win_margins`)

* **Target Collection**: `matches`
* **Analytical Purpose**: Bucket match results into victories by runs vs. victories by wickets to analyze competitive balance.

```javascript
[
  { $match: { winner: { $ne: null } } },
  {
    $project: {
      winner: 1,
      season: 1,
      victory_type: {
        $cond: [
          { $regexMatch: { input: "$result", regex: /runs/i } },
          "by Runs",
          {
            $cond: [
              { $regexMatch: { input: "$result", regex: /wickets/i } },
              "by Wickets",
              "Tie/Super Over"
            ]
          }
        ]
      }
    }
  },
  {
    $group: {
      _id: "$victory_type",
      count: { $sum: 1 }
    }
  }
]
```

---

### Pipeline 4: Toss Impact Analysis (`q4_toss_impact`)

* **Target Collection**: `matches`
* **Analytical Purpose**: Determine whether winning the toss yields a statistically significant advantage in match outcome.

```javascript
[
  { $match: { winner: { $ne: null } } },
  {
    $project: {
      season: 1,
      toss_winner: 1,
      match_winner: "$winner",
      toss_decision: 1,
      toss_winner_won: { $eq: ["$toss_winner", "$winner"] }
    }
  },
  {
    $group: {
      _id: {
        season: "$season",
        toss_winner_won: "$toss_winner_won",
        decision: "$toss_decision"
      },
      count: { $sum: 1 }
    }
  }
]
```

---

### Pipeline 5: Venue First-Innings Average (`q5_venue_first_innings_avg`)

* **Target Collection**: `deliveries`
* **Analytical Purpose**: Calculate the expected first-innings par score at each venue by joining delivery data with match venue metadata via `$lookup`.

```javascript
[
  // Stage 1: Filter to 1st innings only
  { $match: { innings: 1 } },

  // Stage 2: Aggregate total score per match
  {
    $group: {
      _id: "$match_id",
      innings_runs: { $sum: "$total_runs" }
    }
  },

  // Stage 3: Join with matches collection to obtain venue name
  {
    $lookup: {
      from: "matches",
      localField: "_id",
      foreignField: "match_id",
      as: "match_info"
    }
  },
  { $unwind: "$match_info" },

  // Stage 4: Group by Venue and compute average and match count
  {
    $group: {
      _id: "$match_info.venue",
      avg_first_innings: { $avg: "$innings_runs" },
      matches_played: { $sum: 1 }
    }
  },

  // Stage 5: Filter venues with at least 5 matches for statistical validity
  { $match: { matches_played: { $gte: 5 } } },
  {
    $project: {
      venue: "$_id",
      avg_score: { $round: ["$avg_first_innings", 1] },
      matches_played: 1
    }
  },
  { $sort: { avg_score: -1 } }
]
```

---

### Pipeline 6: Player Consistency Metrics (`q7_player_consistency`)

* **Target Collection**: `deliveries`
* **Analytical Purpose**: Use two-stage statistical aggregation (`$stdDevSamp`) across innings to measure batsman reliability and performance variance.

```javascript
[
  // Stage 1: Group runs scored by batter within each individual match
  {
    $group: {
      _id: { batter: "$batter", match_id: "$match_id" },
      match_runs: { $sum: "$batter_runs" }
    }
  },

  // Stage 2: Calculate statistical moments across innings
  {
    $group: {
      _id: "$_id.batter",
      innings_count: { $sum: 1 },
      total_runs: { $sum: "$match_runs" },
      avg_runs: { $avg: "$match_runs" },
      std_dev: { $stdDevSamp: "$match_runs" },
      high_score: { $max: "$match_runs" },
      thirty_plus: {
        $sum: { $cond: [{ $gte: ["$match_runs", 30] }, 1, 0] }
      },
      fifties: {
        $sum: { $cond: [{ $gte: ["$match_runs", 50] }, 1, 0] }
      }
    }
  },

  // Stage 3: Filter for sample size validity (minimum 10 innings)
  { $match: { innings_count: { $gte: 10 } } },

  // Stage 4: Compute Coefficient of Variation (CV = std_dev / avg_runs)
  {
    $project: {
      batter: "$_id",
      innings: "$innings_count",
      total_runs: 1,
      average: { $round: ["$avg_runs", 2] },
      std_dev: { $round: [{ $ifNull: ["$std_dev", 0] }, 2] },
      high_score: 1,
      fifties: 1,
      consistency_score: {
        $cond: [
          { $gt: ["$avg_runs", 0] },
          { $round: [{ $multiply: [{ $divide: [{ $ifNull: ["$std_dev", 0] }, "$avg_runs"] }, 100] }, 1] },
          999.0
        ]
      }
    }
  },
  { $sort: { total_runs: -1 } }
]
```

---

## 3. Big Data Index Optimization Strategy

To support sub-second query response times over large delivery datasets, the following compound and multikey indexes are maintained in MongoDB:

| Collection | Index Fields | Index Type | Target Query Optimization |
|:---|:---|:---|:---|
| `deliveries` | `{ season: 1, batter: 1 }` | Compound | Fast seasonal filtering for batting leaderboards |
| `deliveries` | `{ season: 1, bowler: 1 }` | Compound | Fast seasonal filtering for bowling leaderboards |
| `deliveries` | `{ match_id: 1, innings: 1, over: 1 }` | Compound | Sequential over-by-over ball reconstruction in Match Explorer |
| `deliveries` | `{ match_id: 1, innings: 1, over: 1, delivery: 1, batter: 1 }` | Compound Unique | Primary data integrity & deduplication key |
| `deliveries` | `{ batter: 1, match_id: 1 }` | Compound | Player consistency grouping stage |
| `matches` | `{ match_id: 1 }` | Unique Single | Direct O(1) match document retrieval |
| `matches` | `{ season: 1, date: 1 }` | Compound | Seasonal date-range filtering |
| `matches` | `{ teams: 1 }` | Multikey | Head-to-head lookup across both competing teams |
| `matches` | `{ venue: 1 }` | Single | Venue aggregation and join operations |
