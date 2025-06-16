"""Custom PII recognizers for Presidio."""

from presidio_analyzer import Pattern, PatternRecognizer


def create_age_recognizer() -> PatternRecognizer:
    """Create a recognizer for age patterns."""
    age_patterns = [
        Pattern(name="age_years_old", regex=r"\b\d{1,3}\s+years?\s+old\b", score=0.85),
        Pattern(name="age_years", regex=r"\b\d{1,3}\s+years?\b", score=0.7),
        Pattern(name="age_yo", regex=r"\b\d{1,3}\s*y\.?o\.?\b", score=0.8),
        Pattern(name="aged", regex=r"\baged\s+\d{1,3}\b", score=0.85),
        Pattern(name="age_simple", regex=r"\bage\s+\d{1,3}\b", score=0.75),
    ]

    return PatternRecognizer(
        supported_entity="AGE",
        patterns=age_patterns,
        name="AgeRecognizer",
    )


def create_address_recognizer() -> PatternRecognizer:
    """Create a recognizer for address patterns."""
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

    return PatternRecognizer(
        supported_entity="ADDRESS",
        patterns=address_patterns,
        name="AddressRecognizer",
    )


def create_credit_card_recognizer() -> PatternRecognizer:
    """Create a recognizer for credit card patterns."""
    credit_card_patterns = [
        # Standard 16-digit patterns: "1234 5678 9012 3456", "1234-5678-9012-3456"
        Pattern(
            name="card_16_spaced",
            regex=r"\b\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\b",
            score=0.9,
        ),
        Pattern(name="card_16_dashed", regex=r"\b\d{4}-\d{4}-\d{4}-\d{4}\b", score=0.9),
        Pattern(name="card_16_solid", regex=r"\b\d{16}\b", score=0.85),
        # 15-digit Amex patterns: "1234 567890 12345"
        Pattern(name="amex_15_spaced", regex=r"\b\d{4}\s+\d{6}\s+\d{5}\b", score=0.9),
        Pattern(name="amex_15_dashed", regex=r"\b\d{4}-\d{6}-\d{5}\b", score=0.9),
        Pattern(name="amex_15_solid", regex=r"\b\d{15}\b", score=0.85),
        # 14-digit Diners patterns: "1234 567890 1234"
        Pattern(
            name="diners_14_spaced", regex=r"\b\d{4}\s+\d{6}\s+\d{4}\b", score=0.85
        ),
        Pattern(name="diners_14_dashed", regex=r"\b\d{4}-\d{6}-\d{4}\b", score=0.85),
        Pattern(name="diners_14_solid", regex=r"\b\d{14}\b", score=0.8),
        # Context-aware patterns - just the numbers after keywords
        Pattern(
            name="card_with_context",
            regex=r"(?i)(?<=card\s+(?:number|#)\s*(?:is|:)?\s*)\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|(?<=credit\s+card\s*(?:number|#)?\s*(?:is|:)?\s*)\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|(?<=debit\s+card\s*(?:number|#)?\s*(?:is|:)?\s*)\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
            score=0.8,
        ),
    ]

    return PatternRecognizer(
        supported_entity="CREDIT_CARD_PATTERN",
        patterns=credit_card_patterns,
        name="CreditCardPatternRecognizer",
    )
