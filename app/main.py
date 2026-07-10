from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    routes_calls,
    routes_contest,
    routes_dashboards,
    routes_ingestion,
    routes_org,
)
from app.db.session import create_all_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all_tables()
    yield


app = FastAPI(
    title="FitNova Callsight AI",
    version="0.1.0",
    description="Sales-call intelligence pipeline foundation.",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "callsight-ai"}


app.include_router(routes_ingestion.router)
app.include_router(routes_calls.router)
app.include_router(routes_org.router)
app.include_router(routes_dashboards.router)
app.include_router(routes_contest.router)
