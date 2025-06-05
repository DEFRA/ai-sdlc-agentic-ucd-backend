"""PII removal node for LangGraph workflow."""

import asyncio
from logging import getLogger

from app.research_analysis.agents.prompts.pii_removal import (
    PII_REMOVAL_SYSTEM_PROMPT,
    create_pii_removal_prompt,
)
from app.research_analysis.agents.state import WorkflowState
from app.research_analysis.llm.bedrock_client import chat_with_bedrock
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


async def remove_pii_node(
    state: WorkflowState, _repository: ResearchAnalysisRepository
) -> WorkflowState:
    """
    Remove PII from transcripts using Bedrock.

    Args:
        state: Current workflow state
        repository: Repository for data access

    Returns:
        Updated state with PII-cleaned transcripts
    """
    logger.info("Starting PII removal for analysis %s", state["analysis_id"])
    logger.debug(
        "Input state: %s",
        {
            k: v
            for k, v in state.items()
            if k != "transcripts" and k != "transcripts_pii_cleaned"
        },
    )

    try:
        transcripts = state.get("transcripts", [])
        if not transcripts:
            error_msg = "No transcripts available for PII removal"
            logger.error(error_msg)
            return {
                **state,
                "status": AgentStatus.FAILED,
                "error_message": error_msg,
            }

        # Process each transcript with Bedrock concurrently
        async def clean_transcript(transcript: str) -> str:
            try:
                user_prompt = create_pii_removal_prompt(transcript)
                cleaned = await chat_with_bedrock(
                    PII_REMOVAL_SYSTEM_PROMPT, user_prompt
                )
                logger.debug(
                    "Cleaned transcript, original length: %d, cleaned length: %d",
                    len(transcript),
                    len(cleaned),
                )
                return cleaned
            except Exception as e:
                logger.error("Failed to clean transcript: %s", e)
                raise

        # Clean all transcripts concurrently
        cleaned_transcripts = await asyncio.gather(
            *[clean_transcript(transcript) for transcript in transcripts]
        )

        logger.info(
            "Cleaned %d transcripts for analysis %s",
            len(cleaned_transcripts),
            state["analysis_id"],
        )

        updated_state = {
            **state,
            "transcripts_pii_cleaned": cleaned_transcripts,
            "status": AgentStatus.REMOVING_PII,
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
        error_msg = f"Failed to remove PII: {str(e)}"
        logger.error(error_msg)

        return {
            **state,
            "status": AgentStatus.FAILED,
            "error_message": error_msg,
        }
