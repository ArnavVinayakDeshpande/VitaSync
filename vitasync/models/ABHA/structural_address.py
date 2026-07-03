"""
@file structural_address.py

@brief Defines the ABHA structural address model.

@details
Provides the ABHAStructuralAddress model, which represents the structured
postal address associated with an individual's ABHA account.

The model stores normalized address information, including the district,
state, and postal code, while also optionally preserving the original
unparsed address supplied by external systems.
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)


# ── ABHA Structural Address Model ─────────────────────────────────────────────

class ABHAStructuralAddress(BaseModel):
    """
    @brief Represents an individual's structured ABHA address.

    @details
    Stores the normalized postal address associated with an individual's
    ABHA account.

    The model validates individual address components and ensures that the
    postal code conforms to the expected numeric format.
    """

    model_config = ConfigDict(populate_by_name=True)

    raw_address: str | None = Field(
        None,
        serialization_alias='address',
        validation_alias='address',
        description='The complete unparsed address as originally supplied by the ABHA service.'
    )

    district: str = Field(
        ...,
        serialization_alias='disctrictName',
        validation_alias='disctrictName',
        description='The verified district in which the individual resides.'
    )

    state: str = Field(
        ...,
        serialization_alias='stateName',
        validation_alias='stateName',
        description='The verified state or union territory in which the individual resides.'
    )

    pincode: str = Field(
        ...,
        serialization_alias='pinCode',
        validation_alias='pinCode',
        description='The six-digit postal PIN code corresponding to the individual\'s address.',
        min_length=6,
        max_length=6
    )

    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        """
        @brief Validates the postal PIN code.

        @details
        Ensures that the supplied postal code contains only numeric
        characters.

        @param v
            The supplied postal PIN code.

        @return
            The validated postal PIN code.

        @throws ValueError
            If the supplied postal code contains non-numeric characters.
        """
        if not v.isdigit():
            raise ValueError('Pincode given to ABHA Structural Address contains non-digit characters.')

        return v
        