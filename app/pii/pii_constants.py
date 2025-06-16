"""Types and constants for PII handling."""

# Entity type to placeholder mapping
ENTITY_PLACEHOLDERS: dict[str, str] = {
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

# List of entities to detect
DETECTABLE_ENTITIES = [
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
    # UK-Specific Identifiers
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
]
