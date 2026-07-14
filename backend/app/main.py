"""
Zepto Clone — FastAPI Application Entry Point
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import router
from app.db.database import create_tables
from app.ml.collaborative.cf_engine import get_cf_engine
from app.ml.content.cbf_engine import get_cbf_engine
from app.ml.ranker.hybrid_ranker import get_ranker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load ML models and ensure DB tables exist."""
    logger.info("Starting up Zepto backend...")
    await create_tables()

    # Pre-load ML engines so first request isn't slow
    logger.info("Loading ML engines...")
    get_cf_engine()
    get_cbf_engine()
    get_ranker()
    logger.info("ML engines ready.")

    yield  # app is running

    logger.info("Shutting down.")


app = FastAPI(
    title="Zepto Clone API",
    description="Quick-commerce backend with 3-layer ML recommendation system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ──────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://zepto-clone.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routes ──────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "Zepto Clone API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
