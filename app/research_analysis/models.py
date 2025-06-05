from datetime import datetime
from enum import Enum
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    """Custom ObjectId field for Pydantic v2."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        msg = "Invalid ObjectId"
        raise ValueError(msg)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, handler):
        field_schema.update(type="string")
        return field_schema


class AnalysisStatus(str, Enum):
    """Coarse-grained analysis status."""

    INIT = "INIT"
    FILES_UPLOADED = "FILES_UPLOADED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class AgentStatus(str, Enum):
    """Fine-grained agent workflow status."""

    STARTING = "STARTING"
    LOADING_TRANSCRIPTS = "LOADING_TRANSCRIPTS"
    REMOVING_PII = "REMOVING_PII"
    VALIDATING_PII = "VALIDATING_PII"
    GENERATING_AFFINITY_MAP = "GENERATING_AFFINITY_MAP"
    GENERATING_FINDINGS = "GENERATING_FINDINGS"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class AgentState(BaseModel):
    """Agent state sub-document for LangGraph workflow."""

    process_start_date: Optional[datetime] = None
    transcripts: list[str] = Field(default_factory=list)
    transcripts_pii_cleaned: list[str] = Field(default_factory=list)
    affinity_map: Optional[str] = None
    findings_report: Optional[str] = None
    status: Optional[AgentStatus] = None
    error_message: Optional[str] = None


class ResearchAnalysis(BaseModel):
    """Research analysis session model."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AnalysisStatus = AnalysisStatus.INIT
    error_message: Optional[str] = None
    agent_state: Optional[AgentState] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ResearchAnalysisSummary(BaseModel):
    """Summary view of research analysis (without agent state)."""

    id: PyObjectId = Field(alias="_id")
    created_at: datetime
    status: AnalysisStatus

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AnalysisFile(BaseModel):
    """Analysis file model."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    analysis_id: PyObjectId
    s3_key: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Request/Response models
class StatusUpdateRequest(BaseModel):
    """Request model for status updates."""

    status: AnalysisStatus


class AnalysisResponse(BaseModel):
    """Response model for analysis operations."""

    id: str = Field(alias="_id")
    created_at: datetime
    status: AnalysisStatus
    error_message: Optional[str] = None
    agent_state: Optional[AgentState] = None

    class Config:
        populate_by_name = True


class AnalysisListResponse(BaseModel):
    """Response model for listing analyses."""

    id: str = Field(alias="_id")
    created_at: datetime
    status: AnalysisStatus

    class Config:
        populate_by_name = True


class FileResponse(BaseModel):
    """Response model for file operations."""

    id: str = Field(alias="_id")
    analysis_id: str
    s3_key: str
    uploaded_at: datetime

    class Config:
        populate_by_name = True
