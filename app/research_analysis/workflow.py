from logging import getLogger

from app.research_analysis.agents.workflow import execute_research_analysis_workflow
from app.research_analysis.models import AnalysisStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)

# Global registry of running workflows to prevent duplicates
_running_workflows = set()


async def start_analysis_workflow(
    analysis_id: str, repository: ResearchAnalysisRepository
):
    """
    Start the LangGraph analysis workflow for the given analysis ID.
    """
    if analysis_id in _running_workflows:
        logger.info("Workflow already running for analysis %s", analysis_id)
        return

    _running_workflows.add(analysis_id)

    try:
        # Verify analysis exists
        await repository.get_analysis(analysis_id)
        logger.info("Starting LangGraph workflow for analysis %s", analysis_id)

        # Execute the LangGraph workflow
        final_state = await execute_research_analysis_workflow(analysis_id, repository)

        # Update main analysis status based on workflow result
        if final_state["status"].value == "FINISHED":
            await repository.update_analysis_status(
                analysis_id, AnalysisStatus.COMPLETED
            )
            logger.info(
                "LangGraph workflow completed successfully for analysis %s", analysis_id
            )
        else:
            await repository.update_analysis_status(
                analysis_id, AnalysisStatus.ERROR, final_state.get("error_message")
            )
            logger.error(
                "LangGraph workflow failed for analysis %s: %s",
                analysis_id,
                final_state.get("error_message"),
            )

    except Exception as e:
        error_msg = f"Workflow execution failed: {str(e)}"
        logger.error("Workflow failed for analysis %s: %s", analysis_id, e)
        await repository.update_analysis_status(
            analysis_id, AnalysisStatus.ERROR, error_msg
        )
    finally:
        _running_workflows.discard(analysis_id)
