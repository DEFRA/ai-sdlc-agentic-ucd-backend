"""Affinity mapping node for LangGraph workflow."""

from logging import getLogger

from app.research_analysis.agents.prompts.affinity_mapping import (
    AFFINITY_MAPPING_SYSTEM_PROMPT,
    create_affinity_mapping_prompt,
)
from app.research_analysis.agents.state import WorkflowState
from app.research_analysis.llm.bedrock_client import chat_with_bedrock
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


async def affinity_mapping_node(
    state: WorkflowState, _repository: ResearchAnalysisRepository
) -> WorkflowState:
    """
    Generate affinity map from cleaned transcripts using Bedrock.

    Args:
        state: Current workflow state
        repository: Repository for data access

    Returns:
        Updated state with affinity map
    """
    logger.info("Starting affinity mapping for analysis %s", state["analysis_id"])
    logger.debug(
        "Input state: %s",
        {
            k: v
            for k, v in state.items()
            if k != "transcripts" and k != "transcripts_pii_cleaned"
        },
    )

    try:
        cleaned_transcripts = state.get("transcripts_pii_cleaned", [])
        if not cleaned_transcripts:
            error_msg = "No cleaned transcripts available for affinity mapping"
            logger.error(error_msg)
            return {
                **state,
                "status": AgentStatus.FAILED,
                "error_message": error_msg,
            }

        # Generate affinity map using Bedrock
        user_prompt = create_affinity_mapping_prompt(cleaned_transcripts)
        affinity_map = await chat_with_bedrock(
            AFFINITY_MAPPING_SYSTEM_PROMPT, user_prompt
        )

        logger.info(
            "Generated affinity map for analysis %s, length: %d",
            state["analysis_id"],
            len(affinity_map),
        )

        updated_state = {
            **state,
            "affinity_map": affinity_map,
            "status": AgentStatus.GENERATING_AFFINITY_MAP,
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
        error_msg = f"Failed to generate affinity map: {str(e)}"
        logger.error(error_msg)

        return {
            **state,
            "status": AgentStatus.FAILED,
            "error_message": error_msg,
        }
