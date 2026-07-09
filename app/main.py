from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import deleted, group_tasks, projects

APP_DIR = Path(__file__).parent

app = FastAPI(title="Strata")

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

templates = Jinja2Templates(directory=APP_DIR / "templates")

app.include_router(projects.router)
app.include_router(group_tasks.router)
app.include_router(deleted.router)
