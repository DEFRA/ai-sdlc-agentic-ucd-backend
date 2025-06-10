"""Transcript loader node for LangGraph workflow."""

import asyncio
from logging import getLogger

from langchain_experimental.data_anonymizer import PresidioAnonymizer

from app.common.s3 import get_file_content, get_s3_client
from app.research_analysis.agents.state import WorkflowState
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


def _create_pii_anonymizer() -> PresidioAnonymizer:
    """
    Create and configure a PresidioAnonymizer instance for UK GDPR compliant redaction.

    This function implements technical measures for PII redaction in compliance with:
    - UK GDPR Article 25 (Data protection by design and by default)
    - ICO guidance on anonymization and pseudonymization
    - Data minimization principle (Article 5(1)(c))

    The redaction approach uses specific placeholders rather than pseudonymization
    to ensure irreversible anonymization where personal data cannot be re-identified.

    Returns:
        PresidioAnonymizer configured for UK compliance or None if initialization fails

    Note:
        This constitutes processing under UK GDPR Article 4(2) and requires appropriate
        lawful basis. The anonymization process removes personal data from scope of
        UK GDPR once completed, per ICO guidance on anonymization.
    """
    try:
        from presidio_anonymizer.entities import OperatorConfig

        # Configure redaction operators instead of fake data generators
        redaction_operators = {}
        analyzed_fields = [
            # Names and Personal Info
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            # Financial Information
            "CREDIT_CARD",
            "IBAN_CODE",
            "US_BANK_NUMBER",
            # Government/Legal IDs
            "US_SSN",
            "US_PASSPORT",
            "US_DRIVER_LICENSE",
            "US_ITIN",
            # UK-Specific Identifiers
            "UK_NHS",  # NHS numbers
            "UK_NINO",  # National Insurance numbers
            # Location/Address
            "LOCATION",
            # Dates and Time
            "DATE_TIME",
            # Professional/Medical
            "MEDICAL_LICENSE",
            # Technical
            "IP_ADDRESS",
            "URL",
            "CRYPTO",  # Cryptocurrency addresses
        ]

        # Set each field to use specific redaction placeholders
        field_placeholders = {
            # Names and Personal Info
            "PERSON": "[PERSON]",
            "EMAIL_ADDRESS": "[EMAIL]",
            "PHONE_NUMBER": "[PHONE]",
            # Financial Information
            "CREDIT_CARD": "[CREDIT_CARD]",
            "IBAN_CODE": "[BANK_ACCOUNT]",
            "US_BANK_NUMBER": "[BANK_ACCOUNT]",
            # Government/Legal IDs
            "US_SSN": "[SSN]",
            "US_PASSPORT": "[PASSPORT]",
            "US_DRIVER_LICENSE": "[DRIVER_LICENSE]",
            "US_ITIN": "[TAX_ID]",
            # UK-Specific Identifiers
            "UK_NHS": "[NHS_NUMBER]",
            "UK_NINO": "[NATIONAL_INSURANCE]",
            # Location/Address
            "LOCATION": "[ADDRESS]",
            # Dates and Time
            "DATE_TIME": "[DATE]",
            # Professional/Medical
            "MEDICAL_LICENSE": "[MEDICAL_LICENSE]",
            # Technical
            "IP_ADDRESS": "[IP_ADDRESS]",
            "URL": "[URL]",
            "CRYPTO": "[CRYPTO_ADDRESS]",
        }

        for field in analyzed_fields:
            placeholder = field_placeholders.get(field, f"[{field}]")
            redaction_operators[field] = OperatorConfig(
                "replace", {"new_value": placeholder}
            )

        # Use larger spaCy model for better PII detection accuracy
        languages_config = {
            "nlp_engine_name": "spacy",
            "models": [
                {
                    "lang_code": "en",
                    "model_name": "en_core_web_lg",
                },  # 400MB - better accuracy
            ],
        }

        return PresidioAnonymizer(
            analyzed_fields=analyzed_fields,
            operators=redaction_operators,
            languages_config=languages_config,
            add_default_faker_operators=False,  # Disable fake data generation
        )
    except Exception as e:
        logger.warning("Failed to initialize PresidioAnonymizer: %s", e)
        return None


async def _redact_pii_from_content(content: str, anonymizer: PresidioAnonymizer) -> str:
    """Redact PII from transcript content using PresidioAnonymizer."""
    if not anonymizer:
        logger.warning("No anonymizer available, returning original content")
        return content

    try:
        redacted_content = anonymizer.anonymize(content)
        logger.debug(
            "PII redaction completed, original length: %d, redacted length: %d",
            len(content),
            len(redacted_content),
        )
        return redacted_content
    except Exception as e:
        logger.error("Failed to redact PII from content: %s", e)
        # Return original content if redaction fails
        return content


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

        # Initialize PII anonymizer
        pii_anonymizer = _create_pii_anonymizer()

        async def load_and_redact_file_content(file):
            try:
                content = get_file_content(file.s3_key, s3_client)
                logger.debug("Loaded file %s, length: %d", file.s3_key, len(content))

                # Redact PII from the content
                redacted_content = await _redact_pii_from_content(
                    content, pii_anonymizer
                )
                logger.debug("Redacted PII from file %s", file.s3_key)

                return redacted_content
            except Exception as e:
                logger.error("Failed to load and redact file %s: %s", file.s3_key, e)
                raise

        # Load and redact all files concurrently
        transcripts = await asyncio.gather(
            *[load_and_redact_file_content(file) for file in files]
        )

        logger.info(
            "Loaded and redacted PII from %d transcripts for analysis %s",
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
