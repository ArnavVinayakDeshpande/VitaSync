"""
@file gender.py

@brief Defines the ABHA gender enumeration.

@details
Provides the Gender enumeration, which represents the set of gender values
supported throughout the VitaSync application.

The enumeration corresponds to the gender identifiers used by the ABHA
(Ayushman Bharat Health Account) ecosystem and is referenced by demographic
information models during serialization, validation, and persistence.
"""

from enum import StrEnum


# ── ABHA Gender Enumeration ───────────────────────────────────────────────────

class Gender(StrEnum):
    """
    @brief Represents the supported ABHA gender values.

    @details
    Defines the standardized gender identifiers used throughout the
    application when representing an individual's demographic
    information.

    Each enumeration member maps directly to the corresponding value used
    by the ABHA ecosystem.
    """

    MALE = 'M'
    """Represents a male individual."""

    FEMALE = 'F'
    """Represents a female individual."""

    NONE = 'O'
    """Represents any other or unspecified gender."""
    