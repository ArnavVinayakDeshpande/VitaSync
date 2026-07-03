"""
@file status.py

@brief Defines the ABHA KYC status enumeration.

@details
Provides the ABHAStatus enumeration, which represents the possible
verification states of an individual's ABHA account within VitaSync.

These values are used when storing and processing ABHA KYC information.
"""

from enum import StrEnum


# ── ABHA Status Enumeration ───────────────────────────────────────────────────

class ABHAStatus(StrEnum):
    """
    @brief Represents the verification status of an ABHA account.

    @details
    Defines the possible lifecycle states of an individual's ABHA KYC
    information as recognised by the application.
    """

    ACTIVE = 'ACTIVE'
    """The ABHA account is active and fully usable."""

    INACTIVE = 'INACTIVE'
    """The ABHA account currently exists but is inactive."""

    PENDING = 'PENDING'
    """The ABHA verification process is currently pending."""

    SUSPENDED = 'SUSPENDED'
    """The ABHA account has been suspended."""
    