"""
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


class ABHAKYC(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    abha_number: str = Field(
        ...,
        alias='ABHANumber',
        description='14-digit hyphenated ABHA number.',
        min_length=14,
        max_length=17
    )
    abha_address: str = Field(
        ...,
        alias='phrAddress',
        description=''
    )
    abha_status: ABHAStatus = Field(
        ABHAStatus.ACTIVE,
        alias='abhaStatus',
        description=''
    )  
    demographic_data: ABHADemographicData = Field(...)
    structural_address: ABHAStructuralAddress = Field(...)
    created_on: datetime = Field(
        default_factory=datetime.now
    )

    @field_validator('abha_number')
    @classmethod
    def validate_abha_number(cls, v):
        pattern = r'\d{2}[-| ]\d{4}[-| ]\d{4}[-| ]\d{4}'

        if not bool(re.search(pattern, v)):
            raise ValueError('ABHA Number given in ABHA KYC is invalid.')

        return re.sub(' ', '-', v)

    @field_validator('abha_address')
    @classmethod
    def validate_abha_address(cls, v):
        if not bool(re.search(r'@abdm$', v)):
            raise ValueError('ABHA Address given in ABHA KYC does not end with "@abdm".')

        return v
