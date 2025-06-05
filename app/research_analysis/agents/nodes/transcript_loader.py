"""Transcript loader node for LangGraph workflow."""

import asyncio
from logging import getLogger

from app.common.s3 import get_file_content, get_s3_client
from app.research_analysis.agents.state import WorkflowState
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


async def transcript_loader_node(
    state: WorkflowState, repository: ResearchAnalysisRepository
) -> WorkflowState:
    """
    Load transcript files from S3 into state.

    Args:
        state: Current workflow state
        repository: Repository for data access

    Returns:
        Updated state with loaded transcripts
    """
    logger.info("Starting transcript loading for analysis %s", state["analysis_id"])
    logger.debug(
        "Input state: %s",
        {
            k: v
            for k, v in state.items()
            if k != "transcripts" and k != "transcripts_pii_cleaned"
        },
    )

    try:
        # Get file records for this analysis
        files = await repository.list_files(state["analysis_id"])

        if not files:
            error_msg = "No transcript files found for analysis"
            logger.error(error_msg)
            return {
                **state,
                "status": AgentStatus.FAILED,
                "error_message": error_msg,
            }

        # Load file contents from S3 concurrently
        s3_client = get_s3_client()

        async def load_file_content(file):
            try:
                content = get_file_content(file.s3_key, s3_client)
                logger.debug("Loaded file %s, length: %d", file.s3_key, len(content))
                return content
            except Exception as e:
                logger.error("Failed to load file %s: %s", file.s3_key, e)
                raise

        # Load all files concurrently
        transcripts = await asyncio.gather(*[load_file_content(file) for file in files])

        logger.info(
            "Loaded %d transcripts for analysis %s",
            len(transcripts),
            state["analysis_id"],
        )

        updated_state = {
            **state,
            "transcripts": transcripts,
            "status": AgentStatus.LOADING_TRANSCRIPTS,
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
        error_msg = f"Failed to load transcripts: {str(e)}"
        logger.error(error_msg)

        return {
            **state,
            "status": AgentStatus.FAILED,
            "error_message": error_msg,
        }
