"""Findings report node for LangGraph workflow."""

from logging import getLogger

from app.research_analysis.agents.prompts.findings_report import (
    FINDINGS_REPORT_SYSTEM_PROMPT,
    create_findings_report_prompt,
)
from app.research_analysis.agents.state import WorkflowState
from app.research_analysis.llm.bedrock_client import chat_with_bedrock
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


async def findings_report_node(
    state: WorkflowState, _repository: ResearchAnalysisRepository
) -> WorkflowState:
    """
    Generate findings report from affinity map and transcripts using Bedrock.

    Args:
        state: Current workflow state
        repository: Repository for data access

    Returns:
        Updated state with findings report
    """
    logger.info(
        "Starting findings report generation for analysis %s", state["analysis_id"]
    )
    logger.debug(
        "Input state: %s",
        {
            k: v
            for k, v in state.items()
            if k != "transcripts" and k != "transcripts_pii_cleaned"
        },
    )

    try:
        affinity_map = state.get("affinity_map")
        cleaned_transcripts = state.get("transcripts_pii_cleaned", [])

        if not affinity_map:
            error_msg = "No affinity map available for findings report generation"
            logger.error(error_msg)
            return {
                **state,
                "status": AgentStatus.FAILED,
                "error_message": error_msg,
            }

        if not cleaned_transcripts:
            error_msg = (
                "No cleaned transcripts available for findings report generation"
            )
            logger.error(error_msg)
            return {
                **state,
                "status": AgentStatus.FAILED,
                "error_message": error_msg,
            }

        # Generate findings report using Bedrock
        user_prompt = create_findings_report_prompt(affinity_map, cleaned_transcripts)
        findings_report = await chat_with_bedrock(
            FINDINGS_REPORT_SYSTEM_PROMPT, user_prompt
        )

        logger.info(
            "Generated findings report for analysis %s, length: %d",
            state["analysis_id"],
            len(findings_report),
        )

        updated_state = {
            **state,
            "findings_report": findings_report,
            "status": AgentStatus.FINISHED,
        }
        logger.debug(
            "Output state: %s",
            {
                k: v
                for k, v in updated_state.items()
                if k != "transcripts" and k != "transcripts_pii_cleaned"
            },
        )
        return updated_state

    except Exception as e:
        error_msg = f"Failed to generate findings report: {str(e)}"
        logger.error(error_msg)

        return {
            **state,
            "status": AgentStatus.FAILED,
            "error_message": error_msg,
        }
