# AsHDT — System Architecture

**Version:** PoC 0.1
**Date:** 2026-02-20

---

## What This System Does

AsHDT is a longitudinal health monitoring platform for astronauts. It maintains a persistent archive of biomarker measurements over time and, on demand, fits a polynomial to a selected marker's history to produce a **trajectory analysis** — classifying the current health state, its direction of change, and its rate of change into one of 27 discrete states.

The system is a **proof-of-concept developer dashboard**. All analysis is triggered manually by a user filling out a form. Nothing runs automatically.

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Backend language | Python | conda env `asHDT` |
| API framework | FastAPI | ≥ 0.110 |
| Data validation | Pydantic v2 | ≥ 2.6 |
| Database | SQLite (stdlib `sqlite3`) | — |
| Numerical analysis | NumPy | ≥ 1.26 |
| Frontend framework | Svelte | 5.x (Runes API) |
| Frontend build tool | Vite | 7.x |
| Visualization | Plotly.js | 3.x (`plotly.js-dist-min`) |

---

## Repository Structure

```
asHDT/
├── registry/
│   └── module_registry.json        ← single source of truth for all modules
├── data/                           ← NOT committed to Git
│   ├── archive/
│   │   └── {subject_id}/{module_id}/{marker_id}/
│   │       ├── index.json          ← chronological index of data point files
│   │       └── {timestamp}.json    ← individual data points
│   ├── reports/{subject_id}/       ← full report JSONs written on each /timegraph call
│   ├── snapshots/{subject_id}/     ← (reserved, not yet implemented)
│   └── asHDT.db                    ← SQLite database
├── backend/
│   ├── main.py                     ← FastAPI app, startup, path constants
│   ├── requirements.txt
│   ├── api/
│   │   └── routes.py               ← all route definitions and Pydantic request models
│   └── core/
│       ├── ingestion/
│       │   └── registry_loader.py  ← loads module_registry.json at startup
│       ├── state_store/
│       │   ├── database.py         ← SQLite init and connection helper
│       │   └── archive_reader.py   ← reads time-series data from the filesystem
│       ├── analysis/
│       │   └── trajectory.py       ← pure computation: polynomial fit + trajectory states
│       └── output/
│           └── report_serializer.py ← writes report JSON + DB metadata row
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── svelte.config.js
│   └── src/
│       ├── main.js                 ← Svelte app entry point
│       ├── App.svelte              ← root layout, startup data fetch
│       ├── lib/
│       │   ├── api.js              ← all fetch calls (getRegistry, getSubjects, postTimegraph)
│       │   └── stores.js           ← shared reactive state (registry, subjects, currentReport)
│       └── components/
│           ├── TimeGraphForm.svelte    ← parameter form, triggers analysis
│           ├── TrajectoryChart.svelte  ← Plotly.js chart
│           └── TrajectoryTable.svelte  ← tabular data view
└── notebooks/                      ← development/validation notebooks (not production code)
```

---

## Data Flow

```
User fills out TimeGraphForm
        │
        ▼
postTimegraph(params)          [frontend/src/lib/api.js]
        │  POST /timegraph
        ▼
routes.py: post_timegraph()    [backend/api/routes.py]
        │
        ├─ 1. Parse timeframe ISO strings to datetime objects
        │
        ├─ 2. read_timeseries()          [core/state_store/archive_reader.py]
        │       Navigates to data/archive/{subject_id}/{module_id}/{marker_id}/
        │       Reads index.json → filters by timeframe → loads each .json file
        │       Returns list of data point dicts (with parsed_timestamp added)
        │
        ├─ 3. compute_trajectory()       [core/analysis/trajectory.py]
        │       Normalizes raw values → h-space (u-shaped transform)
        │       Fits single polynomial via numpy.polyfit
        │       Evaluates polynomial + derivatives analytically at each point
        │       Assigns zone, trajectory state (1–27), time-to-transition
        │       Returns {data_points, fit_metadata}
        │
        ├─ 4. save_timegraph_report()    [core/output/report_serializer.py]
        │       Writes full report JSON to data/reports/{subject_id}/{report_id}.json
        │       Inserts metadata row into timegraph_reports table
        │
        └─ 5. Returns {report_id, data_points, fit_metadata} to frontend
                        │
                        ▼
              currentReport store updated   [frontend/src/lib/stores.js]
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
  TrajectoryChart.svelte    TrajectoryTable.svelte
  Plotly.js renders:        HTML table, rows
  - zone band backgrounds   color-coded by zone
  - raw scatter points
  - fitted curve (evaluated
    client-side from coefficients)
  - f′ trace (secondary axis)
```

---

## Backend

### Startup (`main.py`)

On startup, the FastAPI app:
1. Calls `init_db()` — creates `data/asHDT.db` and all tables if they don't exist
2. Calls `load_registry()` — reads `registry/module_registry.json` into memory
3. Stores `registry`, `db_path`, `archive_root`, and `reports_root` on `app.state`

CORS is configured to allow only `http://localhost:5173` (the Vite dev server).

### API Endpoints (`api/routes.py`)

| Method | Path | Description |
|---|---|---|
| GET | `/registry` | Returns full `module_registry.json` contents |
| GET | `/subjects` | Scans `data/archive/` subdirectories, returns list of subject IDs |
| POST | `/timegraph` | Runs trajectory analysis, saves report, returns result |

#### POST `/timegraph` request body

```json
{
  "subject_id": "subject_001",
  "module_id": "vtf_stress_test",
  "marker_id": "vo2max",
  "timeframe": {
    "start_time": "2026-01-01T00:00:00Z",
    "end_time": "2026-03-31T00:00:00Z"
  },
  "zone_boundaries": {
    "healthy_min": 45.0,
    "healthy_max": 60.0,
    "vulnerability_margin": 0.1
  },
  "fitting": {
    "polynomial_degree": 2
  }
}
```

#### POST `/timegraph` response

```json
{
  "report_id": "<UUID>",
  "data_points": [ ... ],
  "fit_metadata": {
    "coefficients": [...],
    "t0_iso": "2026-01-05T08:00:00Z",
    "polynomial_degree": 2,
    "normalization": {
      "healthy_min": 45.0, "healthy_max": 60.0,
      "mid": 52.5, "half_range": 7.5
    },
    "zone_boundaries": { "vulnerability_margin": 0.1 }
  }
}
```

### Trajectory Computation (`core/analysis/trajectory.py`)

This module is **pure computation** — no file I/O, no database calls, no FastAPI dependencies.

**Step 1 — Normalization (u-shaped transform to h-space)**

```
mid        = (healthy_min + healthy_max) / 2
half_range = (healthy_max - healthy_min) / 2
h(raw)     = 1 - |raw - mid| / half_range
```

| raw value | h |
|---|---|
| at `mid` | 1.0 (optimal) |
| at `healthy_min` or `healthy_max` | 0.0 |
| outside by one `half_range` | −1.0 |

**Step 2 — Polynomial fit**

Time is expressed as **hours elapsed since the earliest data point** (`t0`) for numerical stability. A single `numpy.polyfit` is applied to `(x_hours, h_values)`.

**Step 3 — Derivative classification**

First (`f′`) and second (`f″`) derivatives are computed analytically from the polynomial coefficients using `numpy.polyder`. A threshold of ±0.001 h-units/hour classifies each derivative as positive / zero / negative.

**Step 4 — Zone assignment**

Zone is determined from `h(raw_value)` of the actual measured value (not the fitted curve):

```
h > +vulnerability_margin   →  non_pathology
|h| ≤ vulnerability_margin  →  vulnerability
h < -vulnerability_margin   →  pathology
```

**Step 5 — Trajectory state (1–27)**

Zone sign (−1/0/+1) × f′ sign × f″ sign → integer state via lookup table.

**Step 6 — Time-to-transition**

`numpy.roots` on (polynomial − boundary) finds the earliest future time the fitted curve crosses any of the three h-space boundaries (±`vulnerability_margin`, 0).

#### Per-point output fields

| Field | Type | Description |
|---|---|---|
| `timestamp` | string | ISO 8601 UTC |
| `x_hours` | float | Hours since t0 |
| `raw_value` | float | Original measurement |
| `data_quality` | string | `good` / `degraded` / `bad` |
| `health_score` | float | h(raw_value), normalized scalar |
| `fitted_value` | float | Polynomial evaluated at x_hours (h-units) |
| `zone` | string | `non_pathology` / `vulnerability` / `pathology` |
| `f_prime` | float | First derivative (h-units/hour) |
| `f_double_prime` | float | Second derivative (h-units/hour²) |
| `trajectory_state` | int | 1–27 |
| `time_to_transition_hours` | float \| null | Hours until next zone boundary crossing |

### Database (`core/state_store/database.py`)

SQLite via the stdlib `sqlite3` module. No ORM. Parameterized queries only (`?` placeholders). `sqlite3.Row` row factory used on all connections.

**Three tables:**

- `subjects` — known subjects, populated lazily on first `/timegraph` call
- `timegraph_reports` — metadata for every report (parameters + IDs, not payload)
- `snapshots` — reserved for future snapshot feature, table exists but unused

Full report payloads live on the **filesystem** in `data/reports/`. The database stores only the metadata needed for lookup.

### Archive (`core/state_store/archive_reader.py`)

The archive is **append-only and immutable** — files are never modified after creation.

Path convention: `data/archive/{subject_id}/{module_id}/{marker_id}/`

Each marker folder contains:
- `index.json` — chronological list of `{timestamp, file}` entries
- `{timestamp}.json` — individual data point files (filename uses hyphens: `2026-01-05T08-00-00Z.json`, internal `timestamp` field uses colons: `2026-01-05T08:00:00Z`)

The archive reader filters entries by timeframe using `index.json`, then loads only the matching files. Corrupted or missing files are skipped with a warning log.

---

## Frontend

### Entry Point (`main.js` + `App.svelte`)

`main.js` mounts the Svelte 5 app using `mount()`. `App.svelte` fetches registry and subjects on mount via `Promise.all`, writes them to their stores, then renders the form. The chart and table render conditionally once `$currentReport` is non-null.

### Shared State (`lib/stores.js`)

Three Svelte writable stores:

| Store | Type | Content |
|---|---|---|
| `registry` | object \| null | Full `module_registry.json` |
| `subjects` | string[] | List of subject IDs from `GET /subjects` |
| `currentReport` | object \| null | Latest `/timegraph` response |

### API Layer (`lib/api.js`)

All fetch calls are centralized here. Error handling (non-2xx responses → thrown `Error`) lives here and nowhere else.

- `getRegistry()` → `GET /registry`
- `getSubjects()` → `GET /subjects`
- `postTimegraph(params)` → `POST /timegraph`

### `TimeGraphForm.svelte`

Collects all parameters for a `/timegraph` request using Svelte 5 `$state` and `$derived` runes. Dropdown options for module and marker are derived reactively from the `registry` store. On submit, calls `postTimegraph()` and writes the result to `currentReport`. Shows a loading state during the request and an inline error message on failure.

### `TrajectoryChart.svelte`

Renders a Plotly.js chart reactive to `$currentReport` via a Svelte 5 `$effect`. Uses `Plotly.react()` for efficient re-renders.

**Traces:**

1. **Zone bands** — Plotly `shapes` with `xref: 'paper'`, colored rectangles spanning the full x-range at fixed h-space y-values (green / yellow / red)
2. **Raw scatter** — `health_score` vs `timestamp`; marker size encodes `data_quality` (good=12px, degraded=8px, bad=5px); color encodes zone
3. **Fitted curve** — 120 points evaluated client-side from `fit_metadata.coefficients` using Horner's method; x-values converted back to timestamps using `t0_iso`; rendered as a blue dashed line
4. **f′ trace** — first derivative values on a secondary y-axis (right side), dotted grey line

### `TrajectoryTable.svelte`

Tabular view of all `data_points` from `$currentReport`. Row background color indicates zone (green / yellow / pink). Columns: Timestamp, Raw Value, Quality, Health Score, Zone, f′, f″, State, Time-to-Transition.

---

## Module Registry (`registry/module_registry.json`)

Single source of truth for all data-producing modules. A module not present here cannot inject data into the system (no route accepts unregistered modules — the frontend only presents registered modules in the form).

Each module entry contains:
- `module_id` — must match the folder name in `data/archive/`
- `markers[]` — list of biomarkers, each with `marker_id`, `unit`, `volatility_class`, `schema_version`

`volatility_class` drives confidence half-life decay (used at snapshot/report generation time):

| Class | Half-life |
|---|---|
| `acute` | 6 hours |
| `short_term` | 168 hours (1 week) |
| `medium_term` | 720 hours (30 days) |
| `stable` | 8760 hours (1 year) |

---

## Running the Stack

**Backend**
```bash
conda activate asHDT
cd backend
uvicorn main:app --reload --port 8000
```
API explorer: http://localhost:8000/docs

**Frontend**
```bash
cd frontend
npm run dev
```
Dashboard: http://localhost:5173

---

## What Is Not Yet Implemented

- Snapshot generation endpoint and UI
- Ingestion layer (automatic schema validation, index maintenance)
- Alert / notification system
- Authentication or access control
- Composite multi-marker analysis
- Continuous data formats (Parquet, HDF5)
- Cognitive assessment module
- Pre-flight baseline module and automated zone boundary suggestions
