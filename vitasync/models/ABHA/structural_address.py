"""
"""

from pydantic import (
    BaseModel, 
    Field,
    field_validator,
    ConfigDict
)


class ABHAStructuralAddress(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    raw_address: str | None = Field(
        None,
        serialization_alias='address',
        validation_alias='address',
        description='Full unparsed raw address.'
    )
    district: str = Field(
        ...,
        serialization_alias='disctrictName',
        validation_alias='disctrictName',
        description='Verified district name.'
    )
    state: str = Field(
        ...,
        serialization_alias='stateName',
        validation_alias='stateName',
        description='Verified state name.'
    )
    pincode: str = Field(
        ...,
        serialization_alias='pinCode',
        validation_alias='pinCode',
        description='6-digit localized and verified postal code.',
        min_length=6,
        max_length=6
    )

    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        if not v.isdigit():
            raise ValueError('Pincode given to ABHA Structural Address contains non-digit characters.')

        return v
