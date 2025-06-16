"""Person tracking functionality for PII detection."""

import re
from typing import Optional


class PersonTracker:
    """Tracks and assigns consistent IDs to persons across a document."""

    def __init__(self):
        self.person_names: dict[
            int, set[str]
        ] = {}  # person_id -> set of name variations
        self.name_to_id: dict[str, int] = {}  # normalized_name -> person_id
        self.next_id = 1

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Remove common titles and clean up
        name = re.sub(
            r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sir|Lady)\.\s*", "", name, flags=re.IGNORECASE
        )
        name = re.sub(r"\s+", " ", name.strip())
        return name.lower()

    def _extract_name_parts(self, name: str) -> set[str]:
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

    def _find_matching_person(self, name_parts: set[str]) -> Optional[int]:
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
