"""Transcript loader node for LangGraph workflow."""

import asyncio
import re
from logging import getLogger

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.common.s3 import get_file_content, get_s3_client
from app.research_analysis.agents.state import WorkflowState
from app.research_analysis.models import AgentStatus
from app.research_analysis.repository import ResearchAnalysisRepository

logger = getLogger(__name__)


class PersonTracker:
    """Tracks and assigns consistent IDs to persons across a document."""

    def __init__(self):
        self.person_names = {}  # person_id -> set of name variations
        self.name_to_id = {}  # normalized_name -> person_id
        self.next_id = 1

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Remove common titles and clean up
        name = re.sub(
            r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sir|Lady)\.\s*", "", name, flags=re.IGNORECASE
        )
        name = re.sub(r"\s+", " ", name.strip())
        return name.lower()

    def _extract_name_parts(self, name: str) -> set:
        """Extract meaningful parts of a name for matching."""
        normalized = self._normalize_name(name)
        parts = set()

        # Split into words
        words = normalized.split()

        # Add individual words (excluding very short ones)
        for word in words:
            if len(word) > 2:
                parts.add(word)

        # Add full name
        parts.add(normalized)

        # Add combinations for compound names
        if len(words) >= 2:
            # First + Last
            parts.add(f"{words[0]} {words[-1]}")
            # Add surname patterns
            if len(words[-1]) > 2:
                parts.add(words[-1])  # Just last name

        return parts

    def _find_matching_person(self, name_parts: set) -> int:
        """Find if this name matches an existing person."""
        for person_id, existing_parts in self.person_names.items():
            # Check for significant overlap in name parts
            overlap = name_parts.intersection(existing_parts)
            if overlap:
                # If there's any meaningful overlap, it's likely the same person
                # This handles "Marcus Chen" -> "Marcus" -> "Mr. Chen" -> "Chen"
                return person_id
        return None

    def get_person_id(self, name: str) -> str:
        """Get or assign a person ID for a given name."""
        name_parts = self._extract_name_parts(name)

        # Check if we've seen this exact normalized name
        normalized = self._normalize_name(name)
        if normalized in self.name_to_id:
            return f"PERSON_{self.name_to_id[normalized]}"

        # Check if this matches an existing person
        existing_person_id = self._find_matching_person(name_parts)
        if existing_person_id:
            # Add this name variation to the existing person
            self.person_names[existing_person_id].update(name_parts)
            self.name_to_id[normalized] = existing_person_id
            return f"PERSON_{existing_person_id}"

        # New person
        person_id = self.next_id
        self.next_id += 1

        # Store the name parts for this person
        self.person_names[person_id] = name_parts.copy()
        self.name_to_id[normalized] = person_id

        return f"PERSON_{person_id}"


def _create_pii_analyzer() -> AnalyzerEngine:
    """
    Create and configure a PresidioAnalyzer instance for UK GDPR compliant PII detection.

    This function implements technical measures for PII detection in compliance with:
    - UK GDPR Article 25 (Data protection by design and by default)
    - ICO guidance on anonymization and pseudonymization
    - Data minimization principle (Article 5(1)(c))

    Returns:
        AnalyzerEngine configured for UK compliance or None if initialization fails

    Note:
        This constitutes processing under UK GDPR Article 4(2) and requires appropriate
        lawful basis. The detection process identifies personal data for human review.
    """
    try:
        # Use larger spaCy model for better PII detection accuracy
        nlp_configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {
                    "lang_code": "en",
                    "model_name": "en_core_web_lg",
                },  # 400MB - better accuracy
            ],
        }

        # Create NLP engine provider
        provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        nlp_engine = provider.create_engine()

        # Create analyzer with the NLP engine
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

        # Add custom AGE recognizer
        age_patterns = [
            Pattern(
                name="age_years_old", regex=r"\b\d{1,3}\s+years?\s+old\b", score=0.85
            ),
            Pattern(name="age_years", regex=r"\b\d{1,3}\s+years?\b", score=0.7),
            Pattern(name="age_yo", regex=r"\b\d{1,3}\s*y\.?o\.?\b", score=0.8),
            Pattern(name="aged", regex=r"\baged\s+\d{1,3}\b", score=0.85),
            Pattern(name="age_simple", regex=r"\bage\s+\d{1,3}\b", score=0.75),
        ]

        age_recognizer = PatternRecognizer(
            supported_entity="AGE",
            patterns=age_patterns,
            name="AgeRecognizer",
        )

        analyzer.registry.add_recognizer(age_recognizer)

        # Add custom ADDRESS recognizer for street addresses
        address_patterns = [
            # UK-style addresses: "47 Brunswick Street", "123 High Street"
            Pattern(
                name="uk_street_address",
                regex=r"\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Close|Cl|Place|Pl|Square|Sq|Court|Ct|Crescent|Cres|Gardens|Gdns|Terrace|Ter|Way|Walk|Row|Hill|Green|Common|Mews|Park|View|Rise|Grove|Vale|Heights|Approach|Parade|Promenade|Esplanade|Embankment|Quay|Wharf|Bridge|Gate|End|Side|North|South|East|West|Upper|Lower|Old|New)\b",
                score=0.85,
            ),
            # US-style addresses: "123 Main Street", "456 Oak Avenue"
            Pattern(
                name="us_street_address",
                regex=r"\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Circle|Cir|Court|Ct|Place|Pl|Way|Trail|Pkwy|Parkway)\b",
                score=0.85,
            ),
            # General numeric addresses: "123 Any Street Name"
            Pattern(
                name="general_street_address",
                regex=r"\b\d{1,5}\s+[A-Z][a-zA-Z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Close|Place|Way)\b",
                score=0.8,
            ),
            # Apartment/Unit numbers: "Flat 3", "Unit 12A", "Apartment 5B"
            Pattern(
                name="apartment_unit",
                regex=r"\b(?:Flat|Apartment|Apt|Unit|Suite|Ste)\s+\d+[A-Z]?\b",
                score=0.75,
            ),
        ]

        address_recognizer = PatternRecognizer(
            supported_entity="ADDRESS",
            patterns=address_patterns,
            name="AddressRecognizer",
        )

        analyzer.registry.add_recognizer(address_recognizer)

        # Add custom CREDIT_CARD_PATTERN recognizer for card-like patterns
        credit_card_patterns = [
            # Standard 16-digit patterns: "1234 5678 9012 3456", "1234-5678-9012-3456"
            Pattern(
                name="card_16_spaced",
                regex=r"\b\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\b",
                score=0.9,
            ),
            Pattern(
                name="card_16_dashed", regex=r"\b\d{4}-\d{4}-\d{4}-\d{4}\b", score=0.9
            ),
            Pattern(name="card_16_solid", regex=r"\b\d{16}\b", score=0.85),
            # 15-digit Amex patterns: "1234 567890 12345"
            Pattern(
                name="amex_15_spaced", regex=r"\b\d{4}\s+\d{6}\s+\d{5}\b", score=0.9
            ),
            Pattern(name="amex_15_dashed", regex=r"\b\d{4}-\d{6}-\d{5}\b", score=0.9),
            Pattern(name="amex_15_solid", regex=r"\b\d{15}\b", score=0.85),
            # 14-digit Diners patterns: "1234 567890 1234"
            Pattern(
                name="diners_14_spaced", regex=r"\b\d{4}\s+\d{6}\s+\d{4}\b", score=0.85
            ),
            Pattern(
                name="diners_14_dashed", regex=r"\b\d{4}-\d{6}-\d{4}\b", score=0.85
            ),
            Pattern(name="diners_14_solid", regex=r"\b\d{14}\b", score=0.8),
            # Context-aware patterns - just the numbers after keywords
            Pattern(
                name="card_with_context",
                regex=r"(?i)(?<=card\s+(?:number|#)\s*(?:is|:)?\s*)\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|(?<=credit\s+card\s*(?:number|#)?\s*(?:is|:)?\s*)\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|(?<=debit\s+card\s*(?:number|#)?\s*(?:is|:)?\s*)\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
                score=0.8,
            ),
        ]

        credit_card_pattern_recognizer = PatternRecognizer(
            supported_entity="CREDIT_CARD_PATTERN",
            patterns=credit_card_patterns,
            name="CreditCardPatternRecognizer",
        )

        analyzer.registry.add_recognizer(credit_card_pattern_recognizer)

        return analyzer
    except Exception as e:
        logger.warning("Failed to initialize PresidioAnalyzer: %s", e)
        return None


def _get_entity_placeholder(entity_type: str) -> str:
    """Get the appropriate placeholder for a given entity type."""
    field_placeholders = {
        # Names and Personal Info
        "PERSON": "PERSON",
        "EMAIL_ADDRESS": "EMAIL",
        "PHONE_NUMBER": "PHONE",
        # Financial Information
        "CREDIT_CARD": "CREDIT_CARD",
        "CREDIT_CARD_PATTERN": "CREDIT_CARD",
        "IBAN_CODE": "BANK_ACCOUNT",
        "US_BANK_NUMBER": "BANK_ACCOUNT",
        # Government/Legal IDs
        "US_SSN": "SSN",
        "US_PASSPORT": "PASSPORT",
        "US_DRIVER_LICENSE": "DRIVER_LICENSE",
        "US_ITIN": "TAX_ID",
        # UK-Specific Identifiers
        "UK_NHS": "NHS_NUMBER",
        "UK_NINO": "NATIONAL_INSURANCE",
        "UK_PASSPORT": "UK_PASSPORT",
        "UK_DRIVER_LICENSE": "UK_DRIVER_LICENSE",
        "UK_SORT_CODE": "UK_SORT_CODE",
        "UK_TAX_ID": "UK_TAX_ID",
        "UK_POSTCODE": "UK_POSTCODE",
        "UK_VAT_NUMBER": "UK_VAT_NUMBER",
        "UK_COMPANY_NUMBER": "UK_COMPANY_NUMBER",
        "UK_COUNCIL_TAX_REF": "UK_COUNCIL_TAX_REF",
        "UK_UTILITY_ACCOUNT": "UK_UTILITY_ACCOUNT",
        "UK_ELECTORAL_ROLL": "UK_ELECTORAL_ROLL",
        "UK_STUDENT_ID": "UK_STUDENT_ID",
        "UK_PENSION_REF": "UK_PENSION_REF",
        "UK_BENEFIT_REF": "UK_BENEFIT_REF",
        "UK_COURT_REF": "UK_COURT_REF",
        "UK_MEDICAL_REF": "UK_MEDICAL_REF",
        "UK_INSURANCE_POLICY": "UK_INSURANCE_POLICY",
        # Location/Address
        "LOCATION": "ADDRESS",
        # Dates and Time
        "DATE_TIME": "DATE",
        "AGE": "AGE",
        # Professional/Medical
        "MEDICAL_LICENSE": "MEDICAL_LICENSE",
        # Technical
        "IP_ADDRESS": "IP_ADDRESS",
        "URL": "URL",
        "CRYPTO": "CRYPTO_ADDRESS",
    }

    return field_placeholders.get(entity_type, entity_type)


async def _redact_pii_from_content(
    content: str, analyzer: AnalyzerEngine, person_tracker: PersonTracker = None
) -> str:
    """Redact PII from transcript content with original values for human review."""
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
            entities=[
                # Names and Personal Info
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                # Financial Information
                "CREDIT_CARD",
                "CREDIT_CARD_PATTERN",
                "IBAN_CODE",
                "US_BANK_NUMBER",
                # Government/Legal IDs
                "US_SSN",
                "US_PASSPORT",
                "US_DRIVER_LICENSE",
                "US_ITIN",
                # UK-Specific Identifiers (if supported)
                "UK_NHS",
                "UK_NINO",
                "UK_PASSPORT",
                "UK_DRIVER_LICENSE",
                "UK_SORT_CODE",
                "UK_TAX_ID",
                "UK_POSTCODE",
                "UK_VAT_NUMBER",
                "UK_COMPANY_NUMBER",
                "UK_COUNCIL_TAX_REF",
                "UK_UTILITY_ACCOUNT",
                "UK_ELECTORAL_ROLL",
                "UK_STUDENT_ID",
                "UK_PENSION_REF",
                "UK_BENEFIT_REF",
                "UK_COURT_REF",
                "UK_MEDICAL_REF",
                "UK_INSURANCE_POLICY",
                # Location/Address
                "LOCATION",
                "ADDRESS",
                # Dates and Time
                "DATE_TIME",
                "AGE",
                # Professional/Medical
                "MEDICAL_LICENSE",
                # Technical
                "IP_ADDRESS",
                "URL",
                "CRYPTO",
            ],
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
                placeholder = _get_entity_placeholder(result.entity_type)
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

        # Initialize PII analyzer
        pii_analyzer = _create_pii_analyzer()

        async def load_and_redact_file_content(file):
            try:
                content = get_file_content(file.s3_key, s3_client)
                logger.debug("Loaded file %s, length: %d", file.s3_key, len(content))

                # Create fresh person tracker for each transcript file
                person_tracker = PersonTracker()

                # Redact PII from the content with fresh person tracking per file
                redacted_content = await _redact_pii_from_content(
                    content, pii_analyzer, person_tracker
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
