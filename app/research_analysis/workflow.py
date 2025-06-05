import asyncio
from datetime import datetime, timezone
from logging import getLogger

from app.common.exceptions import NotFoundError
from app.common.s3 import get_file_content
from app.research_analysis.models import AgentState, AgentStatus, AnalysisStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)

# Global registry of running workflows to prevent duplicates
_running_workflows = set()


async def start_analysis_workflow(
    analysis_id: str, repository: ResearchAnalysisRepository
):
    """
    Start the analysis workflow for the given analysis ID.
    This is a mock implementation of what would be a LangGraph workflow.
    """
    if analysis_id in _running_workflows:
        logger.info("Workflow already running for analysis %s", analysis_id)
        return

    _running_workflows.add(analysis_id)

    try:
        # Get analysis and files
        await repository.get_analysis(analysis_id)  # Verify analysis exists
        files = await repository.list_files(analysis_id)

        if not files:
            await _update_error_state(
                repository, analysis_id, "No transcript files found for analysis"
            )
            return

        # Initialize agent state
        agent_state = AgentState(
            process_start_date=datetime.now(timezone.utc),
            status=AgentStatus.STARTING,
        )

        await repository.update_agent_state(analysis_id, agent_state.dict())
        logger.info("Started workflow for analysis %s", analysis_id)

        # Run workflow steps
        await _run_workflow_steps(repository, analysis_id, files, agent_state)

    except Exception as e:
        logger.error("Workflow failed for analysis %s: %s", analysis_id, e)
        await _update_error_state(repository, analysis_id, str(e))
    finally:
        _running_workflows.discard(analysis_id)


async def _run_workflow_steps(
    repository: ResearchAnalysisRepository,
    analysis_id: str,
    files,
    agent_state: AgentState,
):
    """Run the mock LangGraph workflow steps."""

    try:
        # Step 1: Load transcripts
        agent_state.status = AgentStatus.LOADING_TRANSCRIPTS
        await repository.update_agent_state(analysis_id, agent_state.dict())

        transcripts = []
        for file in files:
            from app.common.s3 import get_s3_client

            s3_client = get_s3_client()
            content = get_file_content(file.s3_key, s3_client)
            transcripts.append(content)

        agent_state.transcripts = transcripts
        await repository.update_agent_state(analysis_id, agent_state.dict())
        await asyncio.sleep(1)  # Simulate processing time

        # Step 2: Remove PII (mock implementation)
        agent_state.status = AgentStatus.REMOVING_PII
        await repository.update_agent_state(analysis_id, agent_state.dict())

        # Mock PII removal - just add a note
        pii_cleaned = []
        for transcript in transcripts:
            cleaned = transcript + "\n\n[PII has been removed from this transcript]"
            pii_cleaned.append(cleaned)

        agent_state.transcripts_pii_cleaned = pii_cleaned
        await repository.update_agent_state(analysis_id, agent_state.dict())
        await asyncio.sleep(2)  # Simulate processing time

        # Step 3: Validate PII removal (mock implementation)
        agent_state.status = AgentStatus.VALIDATING_PII
        await repository.update_agent_state(analysis_id, agent_state.dict())
        await asyncio.sleep(1)  # Simulate validation time

        # Step 4: Generate affinity map (mock implementation)
        agent_state.status = AgentStatus.GENERATING_AFFINITY_MAP
        await repository.update_agent_state(analysis_id, agent_state.dict())

        affinity_map = _generate_mock_affinity_map(len(transcripts))
        agent_state.affinity_map = affinity_map
        await repository.update_agent_state(analysis_id, agent_state.dict())
        await asyncio.sleep(3)  # Simulate processing time

        # Step 5: Generate findings report (mock implementation)
        agent_state.status = AgentStatus.GENERATING_FINDINGS
        await repository.update_agent_state(analysis_id, agent_state.dict())

        findings_report = _generate_mock_findings_report(len(transcripts))
        agent_state.findings_report = findings_report
        await repository.update_agent_state(analysis_id, agent_state.dict())
        await asyncio.sleep(3)  # Simulate processing time

        # Step 6: Complete
        agent_state.status = AgentStatus.FINISHED
        await repository.update_agent_state(analysis_id, agent_state.dict())

        # Update main analysis status to COMPLETED
        await repository.update_analysis_status(analysis_id, AnalysisStatus.COMPLETED)
        logger.info("Workflow completed for analysis %s", analysis_id)

    except Exception as e:
        logger.error("Workflow step failed for analysis %s: %s", analysis_id, e)
        raise


async def _update_error_state(
    repository: ResearchAnalysisRepository, analysis_id: str, error_message: str
):
    """Update analysis to error state."""
    try:
        analysis = await repository.get_analysis(analysis_id)
        if analysis.agent_state:
            analysis.agent_state.status = AgentStatus.FAILED
            analysis.agent_state.error_message = error_message
            await repository.update_agent_state(
                analysis_id, analysis.agent_state.dict()
            )

        await repository.update_analysis_status(
            analysis_id, AnalysisStatus.ERROR, error_message
        )
    except NotFoundError:
        logger.error(
            "Could not update error state for analysis %s: not found", analysis_id
        )


def _generate_mock_affinity_map(num_transcripts: int) -> str:
    """Generate a mock affinity map."""
    return f"""# Affinity Map

## User Needs
- Need for better accessibility features
- Desire for simplified navigation
- Request for faster loading times

## Pain Points
- Complex user interface
- Slow response times
- Difficulty finding information

## Insights
- Users prefer visual indicators
- Mobile-first approach is critical
- Personalization increases engagement

---
*Generated from {num_transcripts} transcript(s)*
"""


def _generate_mock_findings_report(num_transcripts: int) -> str:
    """Generate a mock findings report."""
    return f"""# Research Findings Report

## Executive Summary
Based on our analysis of {num_transcripts} user interview transcript(s), we have identified key themes and actionable insights for product improvement.

## Key Findings

### 1. Usability Challenges
- **Finding**: Users struggle with current navigation structure
- **Impact**: High abandonment rates on key user journeys
- **Recommendation**: Implement simplified navigation with clear visual hierarchy

### 2. Performance Concerns
- **Finding**: Loading times are a major friction point
- **Impact**: User satisfaction scores below benchmark
- **Recommendation**: Optimize critical path performance and implement progressive loading

### 3. Accessibility Gaps
- **Finding**: Current implementation lacks adequate accessibility features
- **Impact**: Excluding significant user segment
- **Recommendation**: Conduct accessibility audit and implement WCAG 2.1 AA standards

## Next Steps
1. Prioritize navigation redesign based on user mental models
2. Implement performance optimizations for core user flows
3. Develop accessibility improvement roadmap

---
*Analysis completed on {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC*
"""
