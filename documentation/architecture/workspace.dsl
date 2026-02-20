workspace "AsHDT" "Astronaut Health Data Tracker — longitudinal health monitoring and early risk detection platform." {

    model {

        # ── People ──────────────────────────────────────────────────────────
        healthOfficer = person "Mission Health Officer" "Primary user. Reviews trajectory analyses and monitors astronaut health status over time."
        astronaut     = person "Astronaut" "Data subject. Performs stress tests and wears sensors that produce the health data."

        # ── External systems ─────────────────────────────────────────────────
        dataModules = softwareSystem "Data Modules" "Wearable sensors, spaceflight analog study data, biochemical markers, and cognitive assessment tools. Each module writes JSON data-point files to the archive." {
            tags "External"
        }

        # ── AsHDT software system ─────────────────────────────────────────────
        asHDT = softwareSystem "AsHDT" "Maintains a persistent, continuously updated health state for each subject. Computes trajectory analyses of individual biomarkers over time using a three-derivative framework." {

            # ── Containers ────────────────────────────────────────────────────
            frontend = container "Frontend" "Dashboard. Takes user requests for data analysis and presents requested trajectory charts and tables." "Svelte 5 / Vite" {
                tags "Browser"

                group "src/" {
                    appSvelte = component "App.svelte" "Root layout component. Fetches registry and subject list on mount; no business logic." "Svelte component"
                    mainJs    = component "main.js" "Vite entry point. Mounts App into the DOM." "JavaScript"
                }

                group "src/lib/" {
                    apiJs    = component "api.js" "All fetch calls to the backend API. Exports getRegistry(), getSubjects(), postTimegraph(). All error handling lives here." "JavaScript module"
                    storesJs = component "stores.js" "Svelte writable stores: registry, subjects, currentReport." "Svelte store"
                }

                group "src/components/" {
                    timeGraphForm    = component "TimeGraphForm.svelte" "Collects analysis parameters (subject, module, marker, timeframe, zone boundaries, polynomial degree). Calls postTimegraph(); shows loading/error states." "Svelte component"
                    trajectoryChart  = component "TrajectoryChart.svelte" "Plotly.js chart with zone bands, raw scatter markers sized by data_quality, fitted curve evaluated client-side from fit_metadata, and f' trace on secondary y-axis." "Svelte component"
                    trajectoryTable  = component "TrajectoryTable.svelte" "Tabular view of trajectory output. Rows are color-coded by zone." "Svelte component"
                }
            }

            backend = container "Backend" "REST API server. Orchestrates data retrieval, analysis, and long-term storage." "Python / FastAPI / uvicorn (port 8000)" {
                tags "API"

                mainPy = component "main.py" "FastAPI application entry point. Triggers startup tasks, configures CORS (ports), defines relevant file paths." "Python module"

                group "api/" {
                    routesPy = component "routes.py" "All FastAPI route definitions: GET /registry, GET /subjects, POST /timegraph." "Python module"
                }

                group "core/ingestion/" {
                    registryLoaderPy = component "registry_loader.py" "Loads and validates module_registry.json at startup." "Python module"
                }

                group "core/state_store/" {
                    databasePy      = component "database.py" "SQLite connection manager. Makes sure tables exist for metadata to be received and makes the connection to the database." "Python module"
                    archiveReaderPy = component "archive_reader.py" "Reads index.json and datapoint JSON files from the archive, returns clean sorted lists ready for analysis." "Python module"
                }

                group "core/analysis/" {
                    trajectoryPy = component "trajectory.py" "Pure computation module. Normalises raw data, fits a polynomial, computes derivatives, assigns zones and trajectory states, estimates time-to-transition." "Python module"
                }

                group "core/output/" {
                    reportSerializerPy = component "report_serializer.py" "Sends full JSON report results to the archive and inserts report metadata into the SQLite database." "Python module"
                }
            }

            db = container "SQLite Database" "Stores metadata for subjects, snapshots, and timegraph reports. Full JSON files live in the archive." "SQLite (data/asHDT.db)" {
                tags "Database"
            }

            archive = container "Archive" "Append-only JSON filesystem. Stores individual datapoint files and generated report files. Never modified after creation." "Filesystem (data/archive/, data/reports/)" {
                tags "Filesystem"
            }

            moduleRegistry = container "Module Registry" "Single source of truth for all available data modules. Read once at backend startup." "JSON config (registry/module_registry.json)" {
                tags "Config"
            }
        }

        # ── Relationships — container level ───────────────────────────────────
        healthOfficer -> frontend    "Uses dashboard via"                    "Browser / HTTP"
        astronaut     -> dataModules "Performs tests measured by"            "Sensors / Data Input"
        dataModules   -> archive     "Writes datapoint JSON files to"        "Write to disk"

        frontend  -> backend        "Calls REST API"                         "HTTP/JSON (port 8000)"
        backend   -> moduleRegistry "Reads list of possible data modules at startup"    "File read"       
        backend   -> db             "Reads and writes report metadata"       "SQLite3"
        backend   -> archive        "Reads datapoint files; writes reports"  "Write to disk"

        # ── Relationships — backend component level ───────────────────────────
        mainPy -> registryLoaderPy   "Calls load_registry() at startup"
        mainPy -> databasePy         "Calls init_db() at startup"
        mainPy -> routesPy           "Registers API router"

        routesPy -> archiveReaderPy    "Calls read_timeseries()"
        routesPy -> trajectoryPy       "Calls compute_trajectory()"
        routesPy -> reportSerializerPy "Calls save_timegraph_report()"
        routesPy -> databasePy         "Calls get_connection() for subject upsert"

        reportSerializerPy -> databasePy "Sends report metadata"
        reportSerializerPy -> archive    "Saves report as JSON file"

        archiveReaderPy  -> archive        "Reads index.json and datapoint files"
        registryLoaderPy -> moduleRegistry "Reads module_registry.json"
        databasePy       -> db             "Creates tables; single connection to database"

        # ── Relationships — frontend component level ──────────────────────────
        appSvelte -> apiJs    "Calls getRegistry(), getSubjects() on mount"
        appSvelte -> storesJs "Writes registry, subjects stores"

        timeGraphForm   -> apiJs    "Calls postTimegraph()"
        timeGraphForm   -> storesJs "Writes currentReport store"

        trajectoryChart -> storesJs "Reads currentReport store"
        trajectoryTable -> storesJs "Reads currentReport store"

        apiJs -> backend "HTTP fetch"  "HTTP/JSON (port 8000)"
    }

    views {

        # ── Level 1: System Context ───────────────────────────────────────────
        systemContext asHDT "SystemContext" "C4 Level 1 — system context showing AsHDT and its actors." {
            include *
            autoLayout
        }

        # ── Level 2: Containers ───────────────────────────────────────────────
        container asHDT "Containers" "C4 Level 2 — containers inside AsHDT and their relationships." {
            include *
            autoLayout
        }

        # ── Level 3: Backend components (conceptual grouping) ─────────────────
        component backend "BackendComponents" "C4 Level 3 — Python modules in the FastAPI backend, grouped by package directory." {
            include *
            autoLayout
        }

        # ── Level 3: Frontend components ──────────────────────────────────────
        component frontend "FrontendComponents" "C4 Level 3 — Svelte components and JavaScript modules in the frontend SPA." {
            include *
            autoLayout
        }

        # ── Level 4: Deep filesystem view (contributed by filesystem.dsl) ─────
        !include filesystem.dsl

        # ── Styles ────────────────────────────────────────────────────────────
        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
            element "Database" {
                shape Cylinder
                background #438dd5
                color #ffffff
            }
            element "Filesystem" {
                shape Folder
                background #438dd5
                color #ffffff
            }
            element "Config" {
                shape Ellipse
                background #438dd5
                color #ffffff
            }
            element "API" {
                background #1168bd
                color #ffffff
            }
            element "Browser" {
                shape WebBrowser
                background #438dd5
                color #ffffff
            }
        }
    }
}
