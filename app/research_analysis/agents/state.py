from datetime import datetime
from typing import Optional, TypedDict

from app.research_analysis.models import AgentStatus


class WorkflowState(TypedDict):
    """LangGraph workflow state definition."""

    # Core workflow fields
    analysis_id: str
    process_start_date: Optional[datetime]
    status: AgentStatus
    error_message: Optional[str]

    # Transcript data
    transcripts: list[str]
    transcripts_pii_cleaned: list[str]

    # Generated outputs
    affinity_map: Optional[str]
    findings_report: Optional[str]


def workflow_state_to_agent_state(state: WorkflowState) -> dict:
    """
    Convert WorkflowState to AgentState dict for MongoDB persistence.

    Args:
        state: Current WorkflowState from LangGraph

    Returns:
        Dictionary representation of AgentState for MongoDB
    """
    return {
        "process_start_date": state.get("process_start_date"),
        "transcripts": state.get("transcripts", []),
        "transcripts_pii_cleaned": state.get("transcripts_pii_cleaned", []),
        "affinity_map": state.get("affinity_map"),
        "findings_report": state.get("findings_report"),
        "status": state.get("status"),
        "error_message": state.get("error_message"),
    }
