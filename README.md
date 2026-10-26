# CricketIQ -- IPL Big Data Analytics System

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-MongoDB%20Atlas%20%7C%20Community-green.svg)](https://www.mongodb.com/)
[![Framework](https://img.shields.io/badge/Dashboard-Streamlit-red.svg)](https://streamlit.io/)
[![Visualizations](https://img.shields.io/badge/Charts-Plotly-purple.svg)](https://plotly.com/)
[![Tests](https://img.shields.io/badge/Tests-91%20Passed-brightgreen.svg)]()

> **Academic Project Submission**: "Implement a MongoDB-Based Application to Store Big Data for Data Processing and Analyzing the Results."

CricketIQ is an enterprise-grade Big Data analytics platform built on **MongoDB**, **Python**, and **Streamlit**. It ingests semi-structured ball-by-ball Indian Premier League (IPL) cricket datasets, processes them using native multi-stage MongoDB aggregation pipelines, and visualizes analytical insights across a sleek, modern multi-page dashboard.

---

## Key System Features

1. **Big Data Storage & Ingestion**:
   - Parses official Cricsheet JSON match logs into normalized, query-optimized document structures.
   - Bulk upsert operations with idempotency guarantees (preventing duplicate match records).
   - Automated creation of compound and multikey B-tree indexes for high-throughput analytical queries.

2. **Server-Side MongoDB Aggregations**:
   - Complex multi-stage pipelines executing `$match`, `$group`, `$project`, `$sort`, `$lookup`, `$unwind`, and statistical operators (`$stdDevSamp`).
   - Zero division errors handled gracefully with `$cond` expressions.
   - Strict adherence to ICC cricket rules (e.g., wides excluded from balls faced; bowler-credited dismissals only).

3. **Multi-Page Interactive Dashboard**:
   - **Overview / Home**: Global metrics, dataset summary, seasonal distributions, and toss impact analysis.
   - **Page 1: Batting Analytics**: Top run scorers, strike rate vs average scatter plots, boundary distributions (4s & 6s), and custom batter deep-dives.
   - **Page 2: Bowling Analytics**: Leading wicket takers, economy rates, runs conceded, and dismissal breakdown pie charts.
   - **Page 3: Team Analytics**: All-time win/loss standings, winning percentages, and Head-to-Head (H2H) comparative matrix.
   - **Page 4: Venue Analytics**: Matches hosted per stadium, first-innings par scores, and run-scoring trends.
   - **Page 5: Match Explorer**: Individual match scorecard inspector, over-by-over run progression, and delivery-level ball log.
   - **Page 6: Player Consistency**: Advanced statistical analysis utilizing sample standard deviation ($\sigma$) and Coefficient of Variation (CV) to quantify batting dependability.

4. **Rigorous Quality Assurance**:
   - Comprehensive test suite with **91 unit tests** verifying parser logic, batting formulas, bowling rules, and team records.

---

## Architecture Diagram

```
+-------------------------------------------------------------+
|                Cricsheet IPL Datasets (JSON)                |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                Data Importer & Parser                       |
|   (Validates schema, extracts metadata, batches deliveries) |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 MongoDB Database Engine                     |
|  - matches collection (indexed by match_id, season, teams)  |
|  - deliveries collection (indexed by batter, bowler, over)  |
+-------------------------------------------------------------+
                              |  Native Multi-Stage Pipelines
                              v  ($match, $group, $project)
+-------------------------------------------------------------+
|               Analytics Engine (Python/PyMongo)             |
|   - queries.py, batting.py, bowling.py, teams.py, venues.py |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 Streamlit Presentation Layer                |
|   - Interactive Plotly charts, dark-themed UI components    |
+-------------------------------------------------------------+
```

---

## Directory Structure

```
CricketIQ/
├── app.py                      # Main entrypoint & dashboard overview
├── config.py                   # Global configurations, DB names, rules
├── fix_encoding.py             # File encoding sanity utility
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
│
├── analytics/                  # MongoDB aggregation query layer
│   ├── batting.py              # Batting leaderboards & player summaries
│   ├── bowling.py              # Bowling statistics & dismissal logic
│   ├── queries.py              # Standard queries (Orange Cap, Purple Cap, etc.)
│   ├── teams.py                # Standings & head-to-head records
│   └── venues.py               # Venue scoring averages & match counts
│
├── database/                   # MongoDB connection & index manager
│   ├── connection.py           # Client pool & database factory
│   └── indexes.py              # Compound & multikey index setup
│
├── importer/                   # Ingestion & parsing pipeline
│   ├── parser.py               # Cricsheet JSON parser & normalizer
│   └── loader.py               # Batch loader with upsert support
│
├── pages/                      # Streamlit multi-page interface
│   ├── 1_Batting_Analytics.py
│   ├── 2_Bowling_Analytics.py
│   ├── 3_Team_Analytics.py
│   ├── 4_Venue_Analytics.py
│   ├── 5_Match_Explorer.py
│   └── 6_Player_Consistency.py
│
├── tests/                      # Automated unit test suite (91 tests)
│   ├── test_batting.py
│   ├── test_bowling.py
│   ├── test_parser.py
│   └── test_teams.py
│
└── docs/                       # Project documentation & viva guide
    ├── database_schema.md      # Collection schemas & index documentation
    ├── pipeline_documentation.md # Aggregation pipeline mathematical reference
    └── viva_questions_and_answers.md # 25 college viva Q&A
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.10 or higher installed.
- Access to a MongoDB instance (MongoDB Atlas free cluster or local MongoDB Community Server).

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/your-username/CricketIQ.git
cd CricketIQ
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and specify your MongoDB connection URI:
```env
MONGODB_URI=mongodb://localhost:27017/
# Or for MongoDB Atlas:
# MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/CricketIQ?retryWrites=true&w=majority
DATABASE_NAME=CricketIQ
```

### 4. Ingesting IPL Data
You can either let CricketIQ download the dataset automatically, or use locally extracted files:

**Option A (Recommended — 1 Command Automatic Download & Ingestion):**
```bash
python -m importer.import_data --download
```
*To import a smaller subset for quick testing (e.g. 50 matches):*
```bash
python -m importer.import_data --download --limit 50
```

**Option B (Manual):**
1. Download the **IPL (all matches in JSON format)** zip from [Cricsheet](https://cricsheet.org/downloads/ipl_json.zip) (~5.2 MB).
2. Extract the JSON files into `./data/`.
3. Run:
```bash
python -m importer.import_data --data-dir ./data
```

### 5. Launch the Dashboard
Run the Streamlit application:
```bash
python -m streamlit run app.py
```
Open your browser at `http://localhost:8501` to access CricketIQ.

---

## Running the Unit Tests

Execute pytest from the root folder:
```bash
python -m pytest tests/ -v
```

Expected output:
```
tests/test_batting.py ...............                           [ 16%]
tests/test_bowling.py .....................                     [ 39%]
tests/test_parser.py ....................................       [ 79%]
tests/test_teams.py ..................                          [100%]
============================= 91 passed in 0.21s ==============================
```

---

## Database Schema & Indexes

| Collection | Role | Primary/Composite Key | Notable Indexes |
|:---|:---|:---|:---|
| `matches` | 1 document per match | `match_id` (Unique) | `teams`, `season`, `venue`, `date`, `winner` |
| `deliveries` | 1 document per ball | `(match_id, innings, over, delivery, batter)` | `(season, batter)`, `(season, bowler)`, `(match_id, innings, over)` |

Detailed schema documentation is available at [docs/database_schema.md](docs/database_schema.md).

---

## Academic Assessment Reference
- **Aggregation Pipelines Documentation**: [docs/pipeline_documentation.md](docs/pipeline_documentation.md)
- **College Viva & Oral Exam Q&A**: [docs/viva_questions_and_answers.md](docs/viva_questions_and_answers.md)

---

## License & Attribution
- Built for Academic Big Data Analytics evaluation.
- Cricket match data is provided courtesy of [Cricsheet](https://cricsheet.org/) under the Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) license.
