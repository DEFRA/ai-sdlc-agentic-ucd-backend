"""PII redaction functionality."""

from logging import getLogger
from typing import Optional

from presidio_analyzer import AnalyzerEngine

from app.pii.person import PersonTracker
from app.pii.pii_constants import DETECTABLE_ENTITIES, ENTITY_PLACEHOLDERS

logger = getLogger(__name__)


def get_entity_placeholder(entity_type: str) -> str:
    """Get the appropriate placeholder for a given entity type."""
    return ENTITY_PLACEHOLDERS.get(entity_type, entity_type)


async def redact_pii_from_content(
    content: str,
    analyzer: AnalyzerEngine,
    person_tracker: Optional[PersonTracker] = None,
) -> str:
    """
    Redact PII from content with original values for human review.

    Args:
        content: The text content to redact
        analyzer: The PII analyzer to use
        person_tracker: Optional person tracker for consistent person ID assignment

    Returns:
        The redacted content with original values in [TYPE/original_value] format
    """
    if not analyzer:
        logger.warning("No analyzer available, returning original content")
        return content

    # Create person tracker if not provided
    if person_tracker is None:
        person_tracker = PersonTracker()

    try:
        # Analyze the content to find PII entities
        results = analyzer.analyze(
            text=content,
            language="en",
            entities=DETECTABLE_ENTITIES,
        )

        # Remove overlapping entities, prioritizing custom entities
        filtered_results = []
        for result in results:
            # Check if this result overlaps with higher priority entities
            overlaps_with_age = any(
                other.entity_type == "AGE"
                and not (result.end <= other.start or result.start >= other.end)
                for other in results
            )

            overlaps_with_address = any(
                other.entity_type == "ADDRESS"
                and not (result.end <= other.start or result.start >= other.end)
                for other in results
            )

            overlaps_with_credit_card = any(
                other.entity_type in ["CREDIT_CARD", "CREDIT_CARD_PATTERN"]
                and not (result.end <= other.start or result.start >= other.end)
                for other in results
            )

            # Priority order: AGE > CREDIT_CARD/CREDIT_CARD_PATTERN > ADDRESS > others > DATE_TIME/LOCATION
            should_keep = (
                result.entity_type == "AGE"
                or (
                    result.entity_type in ["CREDIT_CARD", "CREDIT_CARD_PATTERN"]
                    and not overlaps_with_age
                )
                or (
                    result.entity_type == "ADDRESS"
                    and not overlaps_with_age
                    and not overlaps_with_credit_card
                )
                or (
                    result.entity_type not in ["DATE_TIME", "LOCATION"]
                    and not overlaps_with_age
                    and not overlaps_with_address
                    and not overlaps_with_credit_card
                )
                or (
                    result.entity_type in ["DATE_TIME", "LOCATION"]
                    and not overlaps_with_age
                    and not overlaps_with_address
                    and not overlaps_with_credit_card
                )
            )

            if should_keep:
                filtered_results.append(result)

        # Sort results by start position in reverse order to avoid offset issues
        filtered_results.sort(key=lambda x: x.start, reverse=True)

        # First pass: assign person IDs in forward order (order of appearance in text)
        person_entities = [r for r in filtered_results if r.entity_type == "PERSON"]
        person_entities.sort(key=lambda x: x.start)  # Forward order for ID assignment

        person_id_map = {}
        for result in person_entities:
            original_value = content[result.start : result.end]
            person_id = person_tracker.get_person_id(original_value)
            person_id_map[(result.start, result.end)] = person_id

        redacted_content = content

        # Second pass: replace each detected entity with [TYPE/original_value] format
        # Process in reverse order to avoid offset issues
        for result in filtered_results:
            original_value = content[result.start : result.end]

            if result.entity_type == "PERSON":
                # Use pre-assigned person ID
                person_id = person_id_map[(result.start, result.end)]
                replacement = f"[{person_id}/{original_value}]"
            else:
                # Use standard placeholder for non-person entities
                placeholder = get_entity_placeholder(result.entity_type)
                replacement = f"[{placeholder}/{original_value}]"

            redacted_content = (
                redacted_content[: result.start]
                + replacement
                + redacted_content[result.end :]
            )

        logger.debug(
            "PII redaction completed, original length: %d, redacted length: %d, entities found: %d",
            len(content),
            len(redacted_content),
            len(filtered_results),
        )
        return redacted_content
    except Exception as e:
        logger.error("Failed to redact PII from content: %s", e)
        # Return original content if redaction fails
        return content
