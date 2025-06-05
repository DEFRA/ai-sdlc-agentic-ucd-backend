from fastapi import APIRouter, Depends, File, UploadFile, status

from app.research_analysis.models import (
    AnalysisListResponse,
    AnalysisResponse,
    FileResponse,
    StatusUpdateRequest,
)
from app.research_analysis.service import ResearchAnalysisService

router = APIRouter(prefix="/api/v1/research-analyses", tags=["research-analysis"])


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_session(service: ResearchAnalysisService = Depends()):
    """
    Create Analysis Session (Story 1.1)

    Create a new empty research-analysis session that can later have
    transcripts attached and be processed.
    """
    return await service.create_analysis()


@router.get("", response_model=list[AnalysisListResponse])
async def list_analysis_sessions(service: ResearchAnalysisService = Depends()):
    """
    List Analysis Sessions (Story 1.2)

    Get all sessions with coarse status for dashboard display.
    Returns sessions sorted by created_at descending.
    """
    return await service.list_analyses()


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis_session(
    analysis_id: str, service: ResearchAnalysisService = Depends()
):
    """
    Retrieve Analysis Session (Story 1.3)

    Get a session with full agent state for progress or final artifacts display.
    """
    return await service.get_analysis(analysis_id)


@router.patch("/{analysis_id}", response_model=AnalysisResponse)
async def update_analysis_status(
    analysis_id: str,
    request: StatusUpdateRequest,
    service: ResearchAnalysisService = Depends(),
):
    """
    Update Analysis Session Status (Story 1.4)

    Update a session's status to trigger workflow execution.
    Operation is idempotent - repeated requests with same status are safe.
    """
    return await service.update_analysis_status(analysis_id, request)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis_session(
    analysis_id: str, service: ResearchAnalysisService = Depends()
):
    """
    Delete Analysis Session (Story 1.5)

    Permanently delete a session and its transcript files to remove sensitive data.
    Deletes related files from S3 and database records.
    """
    await service.delete_analysis(analysis_id)


@router.post(
    "/{analysis_id}/transcripts",
    response_model=list[FileResponse],
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "format": "binary",
                                    "description": "Transcript files (.md or .txt)",
                                },
                            }
                        },
                        "required": ["files"],
                    },
                    "encoding": {"files": {"contentType": "text/markdown, text/plain"}},
                }
            },
            "required": True,
        }
    },
)
async def upload_transcripts(
    analysis_id: str,
    files: list[UploadFile] = File(...),
    service: ResearchAnalysisService = Depends(),
):
    """
    Upload Transcripts to Session (Story 2.1)

    Upload one or more .md/.txt transcript files for analysis.
    Files are streamed to S3 and registered in the database.
    Parent status becomes FILES_UPLOADED if it was INIT.
    """
    return await service.upload_transcripts(analysis_id, files)


@router.get("/{analysis_id}/transcripts", response_model=list[FileResponse])
async def list_transcripts(
    analysis_id: str, service: ResearchAnalysisService = Depends()
):
    """
    List Transcripts for Session (Story 2.2)

    Retrieve metadata for uploaded transcripts to display what has been attached.
    Returns file metadata without file bodies.
    """
    return await service.list_transcripts(analysis_id)
