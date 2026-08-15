import os
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.config import settings
from src.database import init_db
from src.data_ingestion import run_ingestion


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Predictive Maintenance Intelligence System...")
    init_db()
    logger.info("Database initialized and seeded.")

    try:
        run_ingestion(settings.raw_data_dir)
    except Exception as e:
        logger.error(f"Data ingestion failed (non-fatal): {e}")

    try:
        from src.data.cmapss_processor import cmapss
        cmapss.load()
        logger.info("NASA CMAPSS turbofan data loaded.")
    except Exception as e:
        logger.warning(f"CMAPSS data loading failed (non-fatal): {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Hybrid RAG + LangGraph Agentic System for industrial equipment fault diagnosis",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from src.api.routers.auth import router as auth_router
from src.api.routers.equipment import router as equipment_router
from src.api.routers.diagnostic import router as diagnostic_router
from src.api.routers.workorders import router as workorders_router
from src.api.routers.evaluation import router as evaluation_router

app.include_router(auth_router)
app.include_router(equipment_router)
app.include_router(diagnostic_router)
app.include_router(workorders_router)
app.include_router(evaluation_router)


@app.get("/api/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True
#     )