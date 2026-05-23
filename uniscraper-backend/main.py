# main.py
# FastAPI application entry point.
# - Creates app with title="UniScraper API", version="1.0.0"
# - Adds CORSMiddleware using settings.cors_origins
# - Registers all four routers under /api/v1 prefix
# - Startup event: calls database.ping(), logs success or failure
# - GET /health returns {"status": "ok", "version": "1.0.0"}
# - Uvicorn runs on host 0.0.0.0, port 8000

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
import database
from routers import scrape, history, batch, export

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    ok = await database.ping()
    if ok:
        logger.info("✓ MongoDB connected")
    else:
        logger.warning("✗ MongoDB unavailable — check MONGODB_URI in .env")
    yield
    # Shutdown (nothing to clean up for now)


app = FastAPI(
    title="UniScraper API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scrape.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(batch.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
