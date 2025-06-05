from logging import getLogger
from typing import Optional

from bson import ObjectId
from fastapi import Depends
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.common.exceptions import NotFoundError
from app.common.mongo import get_db
from app.research_analysis.models import (
    AnalysisFile,
    ResearchAnalysis,
    ResearchAnalysisSummary,
)

logger = getLogger(__name__)


class ResearchAnalysisRepository:
    """Repository for research analysis operations."""

    def __init__(self, db: AsyncDatabase = Depends(get_db)):
        self.db = db
        self.research_analysis_collection: AsyncCollection = db.research_analysis
        self.analysis_file_collection: AsyncCollection = db.analysis_file

    async def create_analysis(self, analysis: ResearchAnalysis) -> ResearchAnalysis:
        """Create a new research analysis session."""
        doc = analysis.dict(by_alias=True)
        result = await self.research_analysis_collection.insert_one(doc)
        analysis.id = result.inserted_id
        logger.info("Created research analysis: %s", analysis.id)
        return analysis

    async def get_analysis(self, analysis_id: str) -> ResearchAnalysis:
        """Get a research analysis by ID."""
        doc = await self.research_analysis_collection.find_one(
            {"_id": ObjectId(analysis_id)}
        )
        if not doc:
            msg = f"Analysis {analysis_id} not found"
            raise NotFoundError(msg)
        return ResearchAnalysis(**doc)

    async def list_analyses(self) -> list[ResearchAnalysisSummary]:
        """List all research analyses (summary view)."""
        cursor = self.research_analysis_collection.find(
            {},
            {"agent_state": 0},  # Exclude agent_state for summary
        ).sort("created_at", -1)

        analyses = []
        async for doc in cursor:
            analyses.append(ResearchAnalysisSummary(**doc))

        return analyses

    async def update_analysis_status(
        self, analysis_id: str, status: str, error_message: Optional[str] = None
    ) -> ResearchAnalysis:
        """Update analysis status."""
        update_doc = {"status": status}
        if error_message is not None:
            update_doc["error_message"] = error_message

        result = await self.research_analysis_collection.update_one(
            {"_id": ObjectId(analysis_id)}, {"$set": update_doc}
        )

        if result.matched_count == 0:
            msg = f"Analysis {analysis_id} not found"
            raise NotFoundError(msg)

        logger.info("Updated analysis %s status to %s", analysis_id, status)
        return await self.get_analysis(analysis_id)

    async def update_agent_state(
        self, analysis_id: str, agent_state: dict
    ) -> ResearchAnalysis:
        """Update agent state."""
        result = await self.research_analysis_collection.update_one(
            {"_id": ObjectId(analysis_id)}, {"$set": {"agent_state": agent_state}}
        )

        if result.matched_count == 0:
            msg = f"Analysis {analysis_id} not found"
            raise NotFoundError(msg)

        logger.debug("Updated agent state for analysis %s", analysis_id)
        return await self.get_analysis(analysis_id)

    async def delete_analysis(self, analysis_id: str):
        """Delete a research analysis."""
        result = await self.research_analysis_collection.delete_one(
            {"_id": ObjectId(analysis_id)}
        )

        if result.deleted_count == 0:
            msg = f"Analysis {analysis_id} not found"
            raise NotFoundError(msg)

        logger.info("Deleted analysis: %s", analysis_id)

    async def create_file(self, file: AnalysisFile) -> AnalysisFile:
        """Create a new analysis file record."""
        doc = file.dict(by_alias=True)
        result = await self.analysis_file_collection.insert_one(doc)
        file.id = result.inserted_id
        logger.info("Created analysis file: %s", file.id)
        return file

    async def list_files(self, analysis_id: str) -> list[AnalysisFile]:
        """List files for an analysis."""
        cursor = self.analysis_file_collection.find(
            {"analysis_id": ObjectId(analysis_id)}
        ).sort("uploaded_at", 1)

        files = []
        async for doc in cursor:
            files.append(AnalysisFile(**doc))

        return files

    async def delete_files_by_analysis(self, analysis_id: str) -> list[str]:
        """Delete all files for an analysis and return S3 keys."""
        files = await self.list_files(analysis_id)
        s3_keys = [file.s3_key for file in files]

        await self.analysis_file_collection.delete_many(
            {"analysis_id": ObjectId(analysis_id)}
        )

        logger.info("Deleted %d files for analysis %s", len(s3_keys), analysis_id)
        return s3_keys

    async def ensure_indexes(self):
        """Ensure required database indexes exist."""
        # Index on research_analysis.status
        await self.research_analysis_collection.create_index("status")

        # Index on analysis_file.analysis_id
        await self.analysis_file_collection.create_index("analysis_id")

        # Index on research_analysis.created_at for sorting
        await self.research_analysis_collection.create_index([("created_at", -1)])

        logger.info("Database indexes ensured")
