from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI

from app.common.errors import ErrorHandlerMiddleware
from app.common.mongo import get_mongo_client
from app.common.tracing import TraceIdMiddleware
from app.health.router import router as health_router
from app.research_analysis.repository import ResearchAnalysisRepository
from app.research_analysis.router import router as research_analysis_router

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    client = await get_mongo_client()
    logger.info("MongoDB client connected")

    # Ensure database indexes
    from app.common.mongo import get_db

    db = await get_db(client)
    repository = ResearchAnalysisRepository(db)
    await repository.ensure_indexes()

    yield
    # Shutdown
    if client:
        await client.close()
        logger.info("MongoDB client closed")


app = FastAPI(
    title="Research Analysis Backend",
    description="Backend API for processing user research transcripts with agentic workflow",
    version="1.0.0",
    lifespan=lifespan,
)

# Setup middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(TraceIdMiddleware)

# Setup Routes
app.include_router(health_router)
app.include_router(research_analysis_router)
