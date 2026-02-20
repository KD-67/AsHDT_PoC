import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.ingestion.registry_loader import load_registry
from core.state_store.database import init_db
from api.routes import router


# Paths / Constants 
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(BASE_DIR, "..", "data")
DB_PATH      = os.path.join(DATA_DIR, "asHDT.db")
ARCHIVE_ROOT = os.path.join(DATA_DIR, "archive")
REPORTS_ROOT = os.path.join(DATA_DIR, "reports")
REGISTRY_PATH = os.path.join(BASE_DIR, "..", "registry", "module_registry.json")


# App setup & make sure the browser accepts requests from port 5173 where the frontend runs
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# Startup handler
@app.on_event("startup")
def startup():
    init_db(DB_PATH)

    app.state.registry     = load_registry(REGISTRY_PATH)
    app.state.db_path      = DB_PATH
    app.state.archive_root = ARCHIVE_ROOT
    app.state.reports_root = REPORTS_ROOT
