# CricketIQ -- College Viva & Oral Examination Guide

This guide contains 25 detailed viva and technical interview questions tailored specifically for the **CricketIQ IPL Big Data Analytics System**.

---

### Q1: Why was MongoDB chosen over a traditional relational database (e.g., MySQL/PostgreSQL) for this project?
**Answer**:
1. **Semi-Structured Ball-by-Ball Data**: Cricket deliveries contain variable attributes (e.g., extras can be wides, noballs, byes, legbyes, penalty runs, or absent altogether; wickets can have dismissals, fielders, or neither). In relational databases, this requires sparse nullable columns or complex multi-table joins (`deliveries`, `wickets`, `extras`, `fielders`). MongoDB documents naturally model these polymorphic structures using embedded subdocuments and arrays.
2. **Horizontal Scalability for Big Data**: MongoDB is designed natively for distributed sharding, allowing ball-by-ball delivery collections to scale horizontally across commodity clusters.
3. **High-Performance Aggregation Framework**: MongoDB provides native C++ aggregation pipelines that process, group, and calculate statistical moments (like standard deviation) directly on the database server without pulling millions of raw rows into application memory.

---

### Q2: What is an aggregation pipeline in MongoDB, and how does it work?
**Answer**:
An aggregation pipeline is a data processing framework where documents pass through a sequential series of stages. Each stage transforms the documents as they pass through:
- `$match`: Filters documents (operates like SQL `WHERE`).
- `$group`: Groups documents by an identifier and computes aggregate metrics using accumulators like `$sum`, `$avg`, `$max`, `$min`, `$stdDevSamp` (operates like SQL `GROUP BY`).
- `$project`: Reshapes documents, computes new calculated fields, or suppresses unwanted fields (operates like SQL `SELECT`).
- `$sort`: Orders documents (operates like SQL `ORDER BY`).
- `$limit` / `$skip`: Controls pagination.
- `$lookup`: Performs a left outer equijoin with another collection.

---

### Q3: Why did you denormalize the `season` field into the `deliveries` collection instead of purely referencing `matches`?
**Answer**:
This is a standard Big Data engineering trade-off: **Query Read Optimization vs. Storage Redundancy**.
If `season` only existed in `matches`, every seasonal player query (e.g., "Top 10 Orange Cap contenders in 2023") would require a `$lookup` join of ~25,000 deliveries against the `matches` collection. By denormalizing `season` into each delivery record, the query can filter immediately using a compound index `{ season: 1, batter: 1 }` in the very first `$match` stage. This reduces memory usage, eliminates costly foreign key joins, and achieves sub-100ms response times.

---

### Q4: How does CricketIQ handle duplicate data during re-ingestion?
**Answer**:
Data idempotency is enforced through two mechanisms:
1. **Deterministic Unique Key**: In `matches`, `match_id` is derived from the Cricsheet numeric file stem or a deterministic SHA-1 hash of the match date and teams.
2. **Compound Unique Index**: In `deliveries`, a compound unique index is created on `(match_id, innings, over, delivery, batter)`.
3. **Bulk Upsert (`bulk_write`)**: Ingestion uses `UpdateOne(filter, {"$set": doc}, upsert=True)`. If a match is ingested multiple times, existing records are updated rather than duplicated.

---

### Q5: How is batting strike rate calculated in MongoDB without division-by-zero errors?
**Answer**:
A batsman's strike rate is defined as:
$$\text{Strike Rate} = \left(\frac{\text{Total Runs}}{\text{Balls Faced}}\right) \times 100$$
According to cricket rules, wides do not count as balls faced by the batter.
In the `$project` stage, we use the `$cond` operator to test if `balls_faced > 0`. If true, the formula is evaluated and rounded via `$round`; otherwise, it safely defaults to `0.0`, completely avoiding runtime divide-by-zero exceptions.

---

### Q6: How do you credit wickets to a bowler accurately?
**Answer**:
Not all wickets fall under a bowler's credit. For example, run-outs, obstructing the field, and retired hurt are team wickets or fielding dismissals.
CricketIQ filters bowler-credited wickets using:
```javascript
{
  $in: ["$wicket_kind", ["bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"]]
}
```
Only deliveries matching these specific dismissal kinds increment the bowler's wicket count.

---

### Q7: What is the significance of the `$stdDevSamp` operator in Page 6 (Player Consistency)?
**Answer**:
Traditional cricket statistics only examine batting average. However, a player averaging 40 could score 40 every game (high consistency) or alternate between 100 and 0 (high volatility).
CricketIQ uses a two-stage aggregation pipeline:
1. First stage sums the batter's runs grouped by `(batter, match_id)` to get innings scores.
2. Second stage uses `$stdDevSamp` (Sample Standard Deviation) and `$avg` to calculate performance variance across innings.
3. We then compute the **Coefficient of Variation (CV)**:
   $$\text{CV} = \frac{\sigma}{\mu} \times 100$$
A lower CV indicates a more consistent and dependable batsman.

---

### Q8: What indexes are created in CricketIQ, and why are they necessary?
**Answer**:
Without indexes, MongoDB must perform a collection scan (`COLLSCAN`), loading every document from disk into RAM.
Key indexes created:
- `matches.match_id` (Unique): Fast O(1) single-match retrieval.
- `matches.teams` (Multikey): Fast retrieval for head-to-head match queries.
- `deliveries.(season, batter)` (Compound): Allows the database engine to jump straight to the relevant index partition for batting leaderboards.
- `deliveries.(season, bowler)` (Compound): Optimizes bowling analytics.
- `deliveries.(match_id, innings, over)`: Optimizes ball-by-ball timeline queries in Match Explorer.

---

### Q9: What is the difference between an embedded document model and a reference model?
**Answer**:
- **Embedded Document Model**: Related data is stored as a nested document or array inside the parent document (e.g., `extras: { wides: 1 }` embedded inside a delivery). Best for 1-to-1 or bounded 1-to-N relationships that are always queried together.
- **Reference Model**: Documents store the `_id` of documents in another collection (e.g., `deliveries.match_id` referencing `matches.match_id`). Best for unbounded 1-to-N relationships (e.g., thousands of deliveries per match) to keep individual documents well below MongoDB's 16MB document size limit.

---

### Q10: How does the application scale to millions of records?
**Answer**:
1. **Bulk Ingestion**: Processing records in chunks of 2,000 using `bulk_write(ordered=False)` maximizes network throughput and batch writes.
2. **Early `$match` Filtering**: Pipelines place `$match` as stage 1 so index lookups immediately discard irrelevant seasons.
3. **Sharding**: The `deliveries` collection can be sharded on `{ season: 1, match_id: 1 }`, distributing match deliveries across multiple database nodes.
4. **Caching**: Streamlit utilizes `@st.cache_data(ttl=600)` to cache analytical results for 10 minutes, avoiding repeated database hits for identical parameters.
