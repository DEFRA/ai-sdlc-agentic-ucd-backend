"""Main LangGraph workflow for research analysis."""

from datetime import datetime, timezone
from logging import getLogger

from langgraph.graph import END, START, StateGraph

from app.research_analysis.agents.nodes.affinity_mapping import affinity_mapping_node
from app.research_analysis.agents.nodes.findings_report import findings_report_node
from app.research_analysis.agents.nodes.remove_pii import remove_pii_node
from app.research_analysis.agents.nodes.transcript_loader import transcript_loader_node
from app.research_analysis.agents.nodes.validate_pii import validate_pii_node
from app.research_analysis.agents.state import (
    WorkflowState,
    workflow_state_to_agent_state,
)
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


async def sync_state_to_db(
    state: WorkflowState, repository: ResearchAnalysisRepository
) -> None:
    """
    Sync the current WorkflowState to the MongoDB agent_state.

    Args:
        state: Current WorkflowState from LangGraph
        repository: Repository for database operations
    """
    try:
        agent_state_dict = workflow_state_to_agent_state(state)
        await repository.update_agent_state(state["analysis_id"], agent_state_dict)
        logger.debug("Synced state to DB for analysis %s", state["analysis_id"])
    except Exception as e:
        logger.error(
            "Failed to sync state to DB for analysis %s: %s", state["analysis_id"], e
        )


def create_node_with_state_sync(node_func, repository: ResearchAnalysisRepository):
    """
    Wrapper that adds state synchronization to any node function.

    Args:
        node_func: The original node function
        repository: Repository for database operations

    Returns:
        Wrapped node function that syncs state after execution
    """

    async def wrapper(state: WorkflowState) -> WorkflowState:
        # Execute the original node
        updated_state = await node_func(state, repository)

        # Sync the updated state to MongoDB
        await sync_state_to_db(updated_state, repository)

        return updated_state

    return wrapper


def should_continue(state: WorkflowState) -> str:
    """
    Conditional edge function to determine if workflow should continue or end.

    Args:
        state: Current workflow state

    Returns:
        "END" if status is FAILED, otherwise "continue"
    """
    if state.get("status") == AgentStatus.FAILED:
        logger.info(
            "Workflow stopping due to failed status for analysis %s",
            state["analysis_id"],
        )
        return "END"
    return "continue"


def create_research_analysis_workflow(
    repository: ResearchAnalysisRepository,
) -> StateGraph:
    """
    Create the research analysis LangGraph workflow.

    Args:
        repository: Repository for data access

    Returns:
        Compiled StateGraph for research analysis
    """
    # Create the graph
    graph = StateGraph(WorkflowState)

    # Create wrapped nodes with automatic state sync
    transcript_loader = create_node_with_state_sync(transcript_loader_node, repository)
    remove_pii = create_node_with_state_sync(remove_pii_node, repository)
    validate_pii = create_node_with_state_sync(validate_pii_node, repository)
    affinity_mapping = create_node_with_state_sync(affinity_mapping_node, repository)
    generate_findings = create_node_with_state_sync(findings_report_node, repository)

    # Add nodes to the graph
    graph.add_node("transcript_loader", transcript_loader)
    graph.add_node("remove_pii", remove_pii)
    graph.add_node("validate_pii", validate_pii)
    graph.add_node("affinity_mapping", affinity_mapping)
    graph.add_node("generate_findings", generate_findings)

    # Add sequential workflow with conditional error handling
    graph.add_edge(START, "transcript_loader")

    # Conditional edges that check for failures
    graph.add_conditional_edges(
        "transcript_loader", should_continue, {"continue": "remove_pii", "END": END}
    )

    graph.add_conditional_edges(
        "remove_pii", should_continue, {"continue": "validate_pii", "END": END}
    )

    graph.add_conditional_edges(
        "validate_pii", should_continue, {"continue": "affinity_mapping", "END": END}
    )

    graph.add_conditional_edges(
        "affinity_mapping",
        should_continue,
        {"continue": "generate_findings", "END": END},
    )

    # Final node always goes to END
    graph.add_edge("generate_findings", END)

    # Compile the graph
    return graph.compile()


async def execute_research_analysis_workflow(
    analysis_id: str, repository: ResearchAnalysisRepository
) -> WorkflowState:
    """
    Execute the research analysis workflow for a given analysis.

    Args:
        analysis_id: ID of the analysis to process
        repository: Repository for data access

    Returns:
        Final workflow state
    """
    logger.info("Starting research analysis workflow for analysis %s", analysis_id)

    # Create initial state
    initial_state: WorkflowState = {
        "analysis_id": analysis_id,
        "process_start_date": datetime.now(timezone.utc),
        "status": AgentStatus.STARTING,
        "error_message": None,
        "transcripts": [],
        "transcripts_pii_cleaned": [],
        "affinity_map": None,
        "findings_report": None,
    }

    # Sync initial state to DB
    await sync_state_to_db(initial_state, repository)

    # Create and execute workflow
    workflow = create_research_analysis_workflow(repository)

    try:
        final_state = await workflow.ainvoke(initial_state)
        logger.info("Completed research analysis workflow for analysis %s", analysis_id)

        # Final state sync to ensure DB is up to date
        await sync_state_to_db(final_state, repository)

        return final_state
    except Exception as e:
        error_msg = f"Workflow execution failed: {str(e)}"
        logger.error(error_msg)

        # Create error state and sync to DB
        error_state = {
            **initial_state,
            "status": AgentStatus.FAILED,
            "error_message": error_msg,
        }
        await sync_state_to_db(error_state, repository)

        return error_state
