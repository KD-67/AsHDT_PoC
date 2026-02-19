# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Project Is

AsHDT is a modular platform for longitudinal health monitoring and early risk detection for astronauts. It maintains a persistent, continuously updated health state for each subject by integrating data from multiple independent data-producing modules (wearables, stress tests, lab results, cognitive assessments, etc.).

The system's primary analytical output is a **trajectory analysis** of individual biomarkers over time, based on a three-derivative framework:
- f(x) — current value relative to personalized zone boundaries (Non-pathology / Vulnerability / Pathology)
- f'(x) — direction of change (Improving / Stable / Worsening)
- f''(x) — rate of change (Accelerating / Steady / Decelerating)

These combine into 27 discrete trajectory states. A **time-to-zone-transition** estimate is also computed for each data point.

This is a **proof-of-concept (PoC)** build. Simplicity and transparency are preferred over optimization.

---

## Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend language | Python | pip + requirements.txt. No Poetry, no uv. |
| API framework | FastAPI | With Pydantic v2 models |
| Database | SQLite | Via raw `sqlite3` stdlib. No ORM, no SQLAlchemy. |
| Frontend framework | Svelte | Via Vite. Default dev port: 5173. |
| Visualization | Plotly.js | `plotly.js-dist-min` npm package |
| Python env | conda | Environment name: `asHDT` |
| Notebooks | Jupyter | For developing/validating backend logic before transcribing to .py |

**Do not suggest alternatives to any of the above** unless there is a clear bug or incompatibility.

---

## Running the Stack

**Backend:**
```
conda activate asHDT
cd backend
uvicorn main:app --reload --port 8000
```
API explorer: http://localhost:8000/docs

**Frontend:**
```
cd frontend
npm run dev
```
Dashboard: http://localhost:5173

---

## Repository Structure

```
asHDT/
├── registry/
│   └── module_registry.json           ← single source of truth for all modules
├── data/                              ← NOT committed to Git
│   ├── archive/
│   │   └── {subject_id}/{module_id}/{marker_id}/
│   │       ├── index.json             ← time-ordered index of data point files
│   │       └── {timestamp}.json       ← individual data points
│   ├── snapshots/{subject_id}/
│   ├── reports/{subject_id}/
│   └── asHDT.db                       ← SQLite database
├── backend/
│   ├── main.py                        ← FastAPI entry point
│   ├── requirements.txt
│   ├── api/routes.py                  ← all FastAPI route definitions
│   └── core/
│       ├── ingestion/registry_loader.py
│       ├── state_store/
│       │   ├── database.py
│       │   └── archive_reader.py
│       ├── analysis/trajectory.py     ← trajectory computer (pure computation)
│       └── output/report_serializer.py
├── frontend/src/
│   ├── App.svelte
│   ├── lib/
│   │   ├── api.js                     ← ALL fetch calls live here, nowhere else
│   │   └── stores.js
│   └── components/
│       ├── TimeGraphForm.svelte
│       ├── TrajectoryChart.svelte
│       └── TrajectoryTable.svelte
├── notebooks/                         ← analysis development and validation
└── data/dummy_data/                   ← synthetic test data
```

---

## Core Architectural Rules

### Data flow
```
Module output → Ingestion → State Store → Analysis → Output
```
- Analysis runs **on user request only**, never automatically.
- The database stores **metadata only**. Full JSON payloads live on the filesystem.
- Modules are purely data-producing. The core never calls module code — it only reads their output files.
- A module not registered in `module_registry.json` cannot inject data.

### Archive immutability
- Files in `data/archive/` are **never modified or deleted** after creation.
- The archive is append-only. `index.json` is the only file that gets updated (new entries appended).

### Trajectory computation
- Fits a **single polynomial** (`numpy.polyfit`) to the time-series. Does NOT use numerical differentiation.
- Derivatives computed analytically from polynomial coefficients via `numpy.polyder`.
- Time expressed as **hours elapsed since the earliest timestamp** for numerical stability.
- Zone assignment uses **raw measured values**, not fitted values.
- Time-to-transition uses `numpy.roots` on (polynomial − boundary_value), filtering for real positive roots beyond the current x.
- Derivative zero threshold: ±0.001 per hour.

### Frontend API calls
- **All** fetch calls must go through `frontend/src/lib/api.js`. No fetch calls elsewhere.

### Snapshots
- Generated **only on explicit user request**.
- Stored in `data/snapshots/{subject_id}/`, metadata recorded in the `snapshots` DB table.

### Confidence scoring
- Computed at report/snapshot generation time, not at ingestion.
- Formula: `confidence = 0.5 ^ (age_hours / half_life_hours)`
- Half-lives: `acute` = 6h, `short_term` = 168h, `medium_term` = 720h, `stable` = 8760h

---

## Data Schemas

### Data point JSON
```json
{
  "schema_version": "1.0",
  "module_id": "vtf_stress_test",
  "marker_id": "vo2max",
  "subject_id": "subject_001",
  "timestamp": "2026-01-05T08:00:00Z",
  "value": 52.3,
  "unit": "ml/kg/min",
  "data_quality": "good"
}
```
- `data_quality`: `"good"` | `"degraded"` | `"bad"` only.
- `timestamp`: always ISO 8601 UTC.
- Filenames use hyphens instead of colons: `2026-01-05T08-00-00Z.json`

### index.json (one per marker folder)
- Entries must be in **chronological order**.
- Archive reader uses this for time-range queries — do not bypass it.

### POST /timegraph request body
```json
{
  "subject_id": "subject_001",
  "module_id": "vtf_stress_test",
  "marker_id": "vo2max",
  "timeframe": { "from": "2026-01-01T00:00:00Z", "to": "2026-03-31T00:00:00Z" },
  "zone_boundaries": { "healthy_min": 45.0, "healthy_max": 60.0, "vulnerability_margin_pct": 10.0 },
  "fitting": { "polynomial_degree": 2 }
}
```

### Trajectory output (per data point)
```json
{
  "timestamp": "2026-01-05T08:00:00Z",
  "x_hours": 0.0,
  "raw_value": 55.1,
  "fitted_value": 54.8,
  "zone": "non_pathology",
  "f_prime": -0.18,
  "f_double_prime": 0.002,
  "trajectory_state": 9,
  "time_to_transition_hours": 312.5
}
```
- `zone`: `"non_pathology"` | `"vulnerability"` | `"pathology"`
- `trajectory_state`: integer 1–27
- `time_to_transition_hours`: may be `null`

---

## Zone Boundary Logic

```
range = healthy_max - healthy_min
margin = range * vulnerability_margin_pct / 100

vulnerability_lower = healthy_min + margin
vulnerability_upper = healthy_max - margin

raw_value < healthy_min                                      → pathology
healthy_min <= raw_value < vulnerability_lower               → vulnerability
vulnerability_lower <= raw_value <= vulnerability_upper      → non_pathology
vulnerability_upper < raw_value <= healthy_max               → vulnerability
raw_value > healthy_max                                      → pathology
```

---

## SQLite Database Schema

Three tables, created with `CREATE TABLE IF NOT EXISTS` in `database.py`.

```sql
CREATE TABLE IF NOT EXISTS subjects (
    subject_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    target_time TEXT NOT NULL,
    marker_ids TEXT NOT NULL  -- JSON array of selected marker_ids
);

CREATE TABLE IF NOT EXISTS timegraph_reports (
    report_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    marker_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    timeframe_from TEXT NOT NULL,
    timeframe_to TEXT NOT NULL,
    polynomial_degree INTEGER NOT NULL,
    healthy_min REAL NOT NULL,
    healthy_max REAL NOT NULL,
    vulnerability_margin_pct REAL NOT NULL
);
```

Use `sqlite3.Row` as `row_factory` on all connections.

---

## FastAPI Endpoints (PoC)

| Method | Path | Description |
|---|---|---|
| GET | `/registry` | Returns full module_registry.json contents |
| GET | `/subjects` | Scans `data/archive/` folders, returns list of subject_ids |
| POST | `/timegraph` | Runs trajectory analysis, saves report, returns full result |

CORS: allow `http://localhost:5173` only. Backend runs on port 8000.

---

## Frontend Component Responsibilities

- **App.svelte** — root layout, no business logic
- **lib/api.js** — three async functions: `getRegistry()`, `getSubjects()`, `postTimegraph(params)`. All error handling lives here.
- **lib/stores.js** — writable stores: `registry`, `subjects`, `currentReport`
- **TimeGraphForm.svelte** — collects parameters, calls `postTimegraph`, shows loading/error states
- **TrajectoryChart.svelte** — Plotly.js chart with zone bands, raw scatter markers (sized by data_quality: good=12px, degraded=8px, bad=5px), fitted curve (100+ points, blue dashed, evaluated client-side from `fit_metadata`), f' trace on secondary y-axis
- **TrajectoryTable.svelte** — tabular view, color-coded rows by zone

---

## Trajectory State Reference (27 States)

Indexed 1–27, combining zone sign `+`/`0`/`−`, f' sign, f'' sign:

```
 1  + + +  Accelerating Improving Non-pathology
 2  + + 0  Steadily Improving Non-pathology
 3  + + −  Decelerating Improving Non-pathology
 4  + 0 +  Improving Reversal in Non-Pathology
 5  + 0 0  Neutral Stable Non-pathology
 6  + 0 −  Worsening Reversal in Non-Pathology
 7  + − +  Decelerating Worsening Non-pathology
 8  + − 0  Steadily Worsening Non-pathology
 9  + − −  Accelerating Worsening Non-pathology
10  0 + +  Accelerating Improving Vulnerability
11  0 + 0  Steadily Improving Vulnerability
12  0 + −  Decelerating Improving Vulnerability
13  0 0 +  Improving Reversal in Vulnerability
14  0 0 0  Neutral Stable Vulnerability
15  0 0 −  Worsening Reversal in Vulnerability
16  0 − +  Decelerating Worsening Vulnerability
17  0 − 0  Steadily Worsening Vulnerability
18  0 − −  Progressively Worsening Vulnerability
19  − + +  Accelerating Improving Pathology
20  − + 0  Steadily Improving Pathology
21  − + −  Decelerating Improving Pathology
22  − 0 +  Improving Reversal in Pathology
23  − 0 0  Neutral Stable Pathology
24  − 0 −  Worsening Reversal in Pathology
25  − − +  Decelerating Worsening Pathology
26  − − 0  Steadily Worsening Pathology
27  − − −  Accelerating Worsening Pathology
```

---

## Development Conventions

- Python: `snake_case` for functions/variables, `PascalCase` for classes.
- All timestamps are ISO 8601 UTC strings throughout the stack. Parse to datetime objects only for computation; serialize back to string before storing or returning.
- `trajectory.py` is **pure computation** — no file I/O, no database calls, no FastAPI dependencies. Testable by passing a list of dicts directly.
- Add new Python file dependencies to `requirements.txt` immediately.
- New Svelte components go in `frontend/src/components/` and are imported explicitly — no auto-importing.
- Report and snapshot IDs are UUIDs from `uuid.uuid4()`.
- Use parameterized queries (`?` placeholders) for all SQL — no f-strings in queries.

---

## Jupyter Notebooks

- Use notebooks in `notebooks/` to develop and validate logic for `archive_reader.py`, `trajectory.py`, and future analysis modules.
- Once validated in a notebook, transcribe logic into the corresponding `.py` file in `backend/core/`. Notebook = scratchpad; `.py` file = source of truth.
- `main.py`, `routes.py`, and the Svelte frontend are never developed in notebooks.
- Notebook filenames reflect the module they develop (e.g. `trajectory_computer.ipynb`, `archive_reader.ipynb`).

---

## What Is NOT Implemented Yet (Do Not Add Unsolicited)

- Snapshot generation endpoint and UI
- Ingestion layer with automatic schema validation and index maintenance
- Alert / notification system
- Multimodal composite marker integration
- Continuous data format support (Parquet, HDF5)
- Authentication or access control
- Docker / containerization
- Cognitive assessment module
- Pre-flight baseline module and automated zone boundary suggestions
- Any UI beyond the developer dashboard
