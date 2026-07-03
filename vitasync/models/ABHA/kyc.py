"""
@file kyc.py

@brief Defines the ABHA Know Your Customer (KYC) model.

@details
Provides the ABHAKYC model, which encapsulates all information associated
with an individual's ABHA verification.

The model combines the individual's ABHA identifier, ABHA address,
verification status, demographic information, structural address, and the
timestamp at which the KYC information was recorded.

Validation and normalization are performed on all externally supplied
identifiers before they are stored within the model.
"""

import re
from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)

from vitasync.models.ABHA.demographic_data import ABHADemographicData
from vitasync.models.ABHA.structural_address import ABHAStructuralAddress
from vitasync.models.ABHA.status import ABHAStatus


# ── ABHA KYC Model ────────────────────────────────────────────────────────────

class ABHAKYC(BaseModel):
    """
    @brief Represents an individual's ABHA KYC information.

    @details
    Stores the complete set of information associated with an individual's
    ABHA account, including account identifiers, verification status,
    demographic information, and structural address.

    Validators normalize ABHA identifiers to ensure a consistent internal
    representation throughout the application.
    """

    model_config = ConfigDict(populate_by_name=True)

    abha_number: str = Field(
        ...,
        serialization_alias='ABHANumber',
        validation_alias='ABHANumber',
        description='The individual\'s unique fourteen-digit ABHA number.',
        min_length=14,
        max_length=17
    )

    abha_address: str = Field(
        ...,
        serialization_alias='phrAddress',
        validation_alias='phrAddress',
        description='The unique ABHA (PHR) address associated with the individual.'
    )

    abha_status: ABHAStatus = Field(
        ABHAStatus.ACTIVE,
        serialization_alias='abhaStatus',
        validation_alias='abhaStatus',
        description='The current verification status of the individual\'s ABHA account.'
    )

    demographic_data: ABHADemographicData = Field(
        ...,
        description='The individual\'s verified demographic information.'
    )

    structural_address: ABHAStructuralAddress = Field(
        ...,
        description='The individual\'s verified structured postal address.'
    )

    created_on: datetime = Field(
        default_factory=datetime.now,
        description='The timestamp at which this ABHA KYC record was created.'
    )

    @field_validator('abha_number')
    @classmethod
    def validate_abha_number(cls, v):
        """
        @brief Validates and normalizes an ABHA number.

        @details
        Ensures that the supplied ABHA number follows the expected grouped
        fourteen-digit format.

        Spaces within the supplied value are normalized into hyphens before
        the value is stored.

        @param v
            The supplied ABHA number.

        @return
            The normalized ABHA number.

        @throws ValueError
            If the supplied ABHA number is not in a valid format.
        """
        pattern = r'^\d{2}[-| ]\d{4}[-| ]\d{4}[-| ]\d{4}$'

        if not bool(re.search(pattern, v)):
            raise ValueError('ABHA Number given in ABHA KYC is invalid.')

        return re.sub(' ', '-', v)

    @field_validator('abha_address')
    @classmethod
    def validate_abha_address(cls, v):
        """
        @brief Validates an ABHA address.

        @details
        Ensures that the supplied ABHA address belongs to the expected
        ABDM namespace.

        @param v
            The supplied ABHA address.

        @return
            The validated ABHA address.

        @throws ValueError
            If the supplied address does not end with "@abdm".
        """
        if not bool(re.search(r'@abdm$', v)):
            raise ValueError('ABHA Address given in ABHA KYC does not end with "@abdm".')

        return v
        