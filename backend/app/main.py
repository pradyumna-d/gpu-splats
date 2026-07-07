from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.events.bus import EventBus
from app.jobs.manager import JobManager
from app.storage.manager import StorageManager
from app.utils.config import settings

settings.outputs_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = StorageManager()
    events = EventBus()
    manager = JobManager(storage, events)
    app.state.storage = storage
    app.state.event_bus = events
    app.state.job_manager = manager
    await manager.startup()
    yield
    await manager.shutdown()


app = FastAPI(title="Gaussian Splats Workstation", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/api/outputs", StaticFiles(directory=settings.outputs_dir), name="outputs")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
