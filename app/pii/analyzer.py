"""PII analyzer creation and configuration."""

from logging import getLogger

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.pii.recognizers import (
    create_address_recognizer,
    create_age_recognizer,
    create_credit_card_recognizer,
)

logger = getLogger(__name__)


def create_pii_analyzer() -> AnalyzerEngine:
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

        # Add custom recognizers
        analyzer.registry.add_recognizer(create_age_recognizer())
        analyzer.registry.add_recognizer(create_address_recognizer())
        analyzer.registry.add_recognizer(create_credit_card_recognizer())

        return analyzer
    except Exception as e:
        logger.warning("Failed to initialize PresidioAnalyzer: %s", e)
        return None
