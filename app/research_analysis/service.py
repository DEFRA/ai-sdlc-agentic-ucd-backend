import asyncio
from logging import getLogger

from bson import ObjectId
from fastapi import Depends, UploadFile

from app.common.exceptions import (
    InvalidStatusError,
    UnsupportedFileTypeError,
    ValidationError,
)
from app.common.s3 import delete_file, get_s3_client, upload_file
from app.research_analysis.models import (
    AnalysisFile,
    AnalysisListResponse,
    AnalysisResponse,
    AnalysisStatus,
    FileResponse,
    ResearchAnalysis,
    StatusUpdateRequest,
)
from app.research_analysis.repository import ResearchAnalysisRepository
from app.research_analysis.workflow import start_analysis_workflow

logger = getLogger(__name__)

ALLOWED_FILE_TYPES = {".md", ".txt"}
ALLOWED_MIME_TYPES = {"text/markdown", "text/plain", "text/x-markdown"}


class ResearchAnalysisService:
    """Service layer for research analysis operations."""

    def __init__(
        self,
        repository: ResearchAnalysisRepository = Depends(),
        s3_client=Depends(get_s3_client),
    ):
        self.repository = repository
        self.s3_client = s3_client

    async def create_analysis(self) -> AnalysisResponse:
        """Create a new research analysis session."""
        analysis = ResearchAnalysis()
        created_analysis = await self.repository.create_analysis(analysis)

        return AnalysisResponse(
            id=str(created_analysis.id),
            created_at=created_analysis.created_at,
            status=created_analysis.status,
            error_message=created_analysis.error_message,
            agent_state=created_analysis.agent_state,
        )

    async def list_analyses(self) -> list[AnalysisListResponse]:
        """List all research analyses."""
        analyses = await self.repository.list_analyses()

        return [
            AnalysisListResponse(
                id=str(analysis.id),
                created_at=analysis.created_at,
                status=analysis.status,
            )
            for analysis in analyses
        ]

    async def get_analysis(self, analysis_id: str) -> AnalysisResponse:
        """Get a research analysis by ID."""
        analysis = await self.repository.get_analysis(analysis_id)

        return AnalysisResponse(
            id=str(analysis.id),
            created_at=analysis.created_at,
            status=analysis.status,
            error_message=analysis.error_message,
            agent_state=analysis.agent_state,
        )

    async def update_analysis_status(
        self, analysis_id: str, request: StatusUpdateRequest
    ) -> AnalysisResponse:
        """Update analysis status and trigger workflow if needed."""
        # Get current analysis
        current_analysis = await self.repository.get_analysis(analysis_id)

        # Validate status transition
        if not self._is_valid_status_transition(
            current_analysis.status, request.status
        ):
            msg = (
                f"Cannot transition from {current_analysis.status} to {request.status}"
            )
            raise InvalidStatusError(msg)

        # If already in the requested status, return current state (idempotent)
        if current_analysis.status == request.status:
            logger.info("Analysis %s already in status %s", analysis_id, request.status)
            return await self.get_analysis(analysis_id)

        # Update status
        await self.repository.update_analysis_status(analysis_id, request.status)

        # Trigger workflow if moving to RUNNING
        if request.status == AnalysisStatus.RUNNING:
            # Initialize agent state with process start date
            from datetime import datetime, timezone

            from app.research_analysis.models import AgentState, AgentStatus

            agent_state = AgentState(
                process_start_date=datetime.now(timezone.utc),
                status=AgentStatus.STARTING,
            )
            await self.repository.update_agent_state(analysis_id, agent_state.dict())

            # Start background workflow
            asyncio.create_task(start_analysis_workflow(analysis_id, self.repository))
            logger.info("Started background workflow for analysis %s", analysis_id)

        return await self.get_analysis(analysis_id)

    async def delete_analysis(self, analysis_id: str):
        """Delete a research analysis and all associated files."""
        # Get S3 keys for cleanup
        s3_keys = await self.repository.delete_files_by_analysis(analysis_id)

        # Delete files from S3
        for s3_key in s3_keys:
            try:
                delete_file(s3_key, self.s3_client)
            except Exception as e:
                logger.error("Failed to delete S3 file %s: %s", s3_key, e)
                # Continue with deletion despite S3 errors

        # Delete analysis record
        await self.repository.delete_analysis(analysis_id)
        logger.info("Deleted analysis %s and %d files", analysis_id, len(s3_keys))

    async def upload_transcripts(
        self, analysis_id: str, files: list[UploadFile]
    ) -> list[FileResponse]:
        """Upload transcript files for an analysis."""
        # Validate analysis exists and is in valid state for uploads
        analysis = await self.repository.get_analysis(analysis_id)

        if analysis.status not in [AnalysisStatus.INIT, AnalysisStatus.FILES_UPLOADED]:
            msg = f"Cannot upload files to analysis in {analysis.status} status"
            raise ValidationError(msg)

        # Validate files
        for file in files:
            self._validate_file(file)

        # Upload files and create records
        uploaded_files = []
        for file in files:
            try:
                # Upload to S3
                s3_key = upload_file(
                    file.file, analysis_id, file.filename, self.s3_client
                )

                # Create file record
                analysis_file = AnalysisFile(
                    analysis_id=ObjectId(analysis_id), s3_key=s3_key
                )
                created_file = await self.repository.create_file(analysis_file)

                uploaded_files.append(
                    FileResponse(
                        id=str(created_file.id),
                        analysis_id=analysis_id,
                        s3_key=created_file.s3_key,
                        uploaded_at=created_file.uploaded_at,
                    )
                )

            except Exception as e:
                logger.error("Failed to upload file %s: %s", file.filename, e)
                # Clean up any already uploaded files
                import contextlib

                for uploaded_file in uploaded_files:
                    with contextlib.suppress(Exception):
                        delete_file(uploaded_file.s3_key, self.s3_client)
                msg = f"Failed to upload file {file.filename}"
                raise ValidationError(msg) from e

        # Update analysis status to FILES_UPLOADED if it was INIT
        if analysis.status == AnalysisStatus.INIT:
            await self.repository.update_analysis_status(
                analysis_id, AnalysisStatus.FILES_UPLOADED
            )
            logger.info("Updated analysis %s status to FILES_UPLOADED", analysis_id)

        return uploaded_files

    async def list_transcripts(self, analysis_id: str) -> list[FileResponse]:
        """List transcript files for an analysis."""
        # Verify analysis exists
        await self.repository.get_analysis(analysis_id)

        files = await self.repository.list_files(analysis_id)

        return [
            FileResponse(
                id=str(file.id),
                analysis_id=str(file.analysis_id),
                s3_key=file.s3_key,
                uploaded_at=file.uploaded_at,
            )
            for file in files
        ]

    def _validate_file(self, file: UploadFile):
        """Validate uploaded file type."""
        if not file.filename:
            msg = "File must have a filename"
            raise UnsupportedFileTypeError(msg)

        # Check file extension
        file_ext = "." + file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_FILE_TYPES:
            msg = f"File type {file_ext} not supported. Allowed types: {ALLOWED_FILE_TYPES}"
            raise UnsupportedFileTypeError(msg)

        # Check MIME type if available
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            msg = f"MIME type {file.content_type} not supported. Allowed types: {ALLOWED_MIME_TYPES}"
            raise UnsupportedFileTypeError(msg)

    def _is_valid_status_transition(
        self, current: AnalysisStatus, new: AnalysisStatus
    ) -> bool:
        """Check if status transition is valid."""
        valid_transitions = {
            AnalysisStatus.INIT: [AnalysisStatus.FILES_UPLOADED],
            AnalysisStatus.FILES_UPLOADED: [AnalysisStatus.RUNNING],
            AnalysisStatus.RUNNING: [
                AnalysisStatus.RUNNING,
                AnalysisStatus.COMPLETED,
                AnalysisStatus.ERROR,
            ],
            AnalysisStatus.COMPLETED: [],
            AnalysisStatus.ERROR: [],
        }

        return new in valid_transitions.get(current, [])
