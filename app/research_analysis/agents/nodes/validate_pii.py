"""PII validation node for LangGraph workflow."""

import asyncio
import re
from logging import getLogger

from app.research_analysis.agents.prompts.pii_validation import (
    PII_VALIDATION_SYSTEM_PROMPT,
    create_pii_validation_prompt,
)
from app.research_analysis.agents.state import WorkflowState
from app.research_analysis.llm.bedrock_client import chat_with_bedrock
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


def _extract_pii_found(line: str) -> bool | None:
    """Extract PII_FOUND value from a line."""
    match = re.search(r"PII_FOUND:\s*(YES|NO)", line, re.IGNORECASE)
    return match.group(1).upper() == "YES" if match else None


def _extract_issues(line: str) -> str | None:
    """Extract ISSUES value from a line."""
    match = re.search(r"ISSUES:\s*(.*)", line, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_confidence(line: str) -> str | None:
    """Extract CONFIDENCE value from a line."""
    match = re.search(r"CONFIDENCE:\s*(HIGH|MEDIUM|LOW)", line, re.IGNORECASE)
    return match.group(1).upper() if match else None


def parse_pii_validation_response(response: str) -> dict:
    """
    Parse PII validation response with robust error handling.

    Args:
        response: Raw response from the LLM

    Returns:
        Dict with pii_found, issues, and confidence

    Raises:
        ValueError: If response cannot be parsed
    """
    response = response.strip()
    logger.debug("Parsing PII validation response: %s", response)

    # Initialize defaults
    pii_found = None
    issues = None
    confidence = None

    # Split by lines and process each
    lines = [line.strip() for line in response.split("\n") if line.strip()]

    # Try to extract required fields
    for line in lines:
        line_upper = line.upper()
        if line_upper.startswith("PII_FOUND:"):
            pii_found = _extract_pii_found(line)
        elif line_upper.startswith("ISSUES:"):
            issues = _extract_issues(line)
        elif line_upper.startswith("CONFIDENCE:"):
            confidence = _extract_confidence(line)

    # Validate that we got all required fields
    if pii_found is None:
        error_msg = f"Could not parse PII_FOUND from response. Response: {response}"
        raise ValueError(error_msg)
    if issues is None:
        error_msg = f"Could not parse ISSUES from response. Response: {response}"
        raise ValueError(error_msg)
    if confidence is None:
        logger.warning("Could not parse CONFIDENCE from response, defaulting to MEDIUM")
        confidence = "MEDIUM"

    logger.debug(
        "Successfully parsed - PII_FOUND: %s, ISSUES: %s, CONFIDENCE: %s",
        pii_found,
        issues,
        confidence,
    )

    return {
        "pii_found": pii_found,
        "issues": issues,
        "confidence": confidence,
    }


async def validate_pii_node(
    state: WorkflowState, _repository: ResearchAnalysisRepository
) -> WorkflowState:
    """
    Validate PII removal from transcripts using Bedrock.

    Args:
        state: Current workflow state
        repository: Repository for data access

    Returns:
        Updated state after PII validation
    """
    logger.info("Starting PII validation for analysis %s", state["analysis_id"])
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
            error_msg = "No cleaned transcripts available for PII validation"
            logger.error(error_msg)
            return {
                **state,
                "status": AgentStatus.FAILED,
                "error_message": error_msg,
            }

        # Validate each cleaned transcript with Bedrock concurrently
        async def validate_transcript(transcript: str, transcript_index: int) -> dict:
            try:
                user_prompt = create_pii_validation_prompt(transcript)
                logger.debug(
                    "PII validation prompt for transcript %d: %s",
                    transcript_index + 1,
                    user_prompt[:200] + "...",
                )

                validation_result = await chat_with_bedrock(
                    PII_VALIDATION_SYSTEM_PROMPT, user_prompt
                )
                logger.debug(
                    "Raw PII validation result for transcript %d: %s",
                    transcript_index + 1,
                    validation_result,
                )

                # Parse validation result with robust error handling
                try:
                    parsed_result = parse_pii_validation_response(validation_result)
                    parsed_result["transcript_index"] = transcript_index
                    return parsed_result
                except ValueError as parse_error:
                    logger.error(
                        "Failed to parse PII validation response for transcript %d: %s",
                        transcript_index + 1,
                        parse_error,
                    )
                    # Return a safe default that treats unparseable responses as potential PII issues
                    return {
                        "pii_found": True,  # Be conservative - treat parsing errors as PII issues
                        "issues": f"Unable to parse validation response: {str(parse_error)}",
                        "confidence": "LOW",
                        "transcript_index": transcript_index,
                    }

            except Exception as e:
                logger.error(
                    "Failed to validate transcript %d: %s", transcript_index + 1, e
                )
                # Return a safe default for any validation errors
                return {
                    "pii_found": True,  # Be conservative
                    "issues": f"Validation failed: {str(e)}",
                    "confidence": "LOW",
                    "transcript_index": transcript_index,
                }

        # Validate all transcripts concurrently with indices
        validation_results = await asyncio.gather(
            *[
                validate_transcript(transcript, i)
                for i, transcript in enumerate(cleaned_transcripts)
            ]
        )

        # Check if any PII was found
        pii_issues = []
        for result in validation_results:
            if result["pii_found"]:
                transcript_num = result["transcript_index"] + 1
                pii_issues.append(f"Transcript {transcript_num}: {result['issues']}")

        if pii_issues:
            error_msg = f"PII validation failed. Issues found: {'; '.join(pii_issues)}"
            logger.error(error_msg)

            return {
                **state,
                "status": AgentStatus.FAILED,
                "error_message": error_msg,
            }

        logger.info("PII validation passed for analysis %s", state["analysis_id"])

        updated_state = {
            **state,
            "status": AgentStatus.VALIDATING_PII,
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
        error_msg = f"Failed to validate PII removal: {str(e)}"
        logger.error(error_msg)

        return {
            **state,
            "status": AgentStatus.FAILED,
            "error_message": error_msg,
        }
