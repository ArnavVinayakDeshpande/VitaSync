"""
"""

from datetime import date
import re
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)

from vitasync.exceptions.generic import *


class ABHADemographicData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    first_name: str = Field(
        ...,
        alias='firstName',
        description='Legal first name',
        min_length=1
    )
    middle_name: str = Field(
        '',
        alias='middleName',
        description='Optional middle name'
    )
    last_name: str = Field(
        '',
        alias='lastName',
        description='Optional Legal Last Name'
    )
    date_of_birth: date = Field(
        ...,
        alias='dob',
        description='Parsed date of birth.'
    )
    gender: str = Field(
        ...,
        alias='gender',
        max_length=1,
        description='M, F, or 0 identifier'
    )
    mobile_number: str = Field(
        ...,
        alias='mobile',
        description='AADHAR-linked and registered mobile number'
    )

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v):
        if not v:
            raise ValueError('First name given for ABHA Demographic Data is empty.')

        if not bool(re.search(r'\d', v)):
            raise ValueError('First name given for ABHA Demographic Data contains digits.')

        return v

    @field_validator('middle_name', 'last_name')
    @classmethod
    def validate_middle_and_last_name(cls, v):
        if not bool(re.search(r'\d', v)):
            raise ValueError('Name parameter given for ABHA Demographic Data contains digits.')

        return v

    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        if v.upper() not in ['M', 'F', '0']:
            raise ValueError('Unknown gender given for ABHA Demographic Data.')

        return v

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls, v: str):
        if not v:
            raise ValueError('Mobile number given for ABHA Demographic Data is empty.')

        cleaned = re.sub(r'^(\+91|0)', '', v.strip())

        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError('Mobile number given for ABHA Demographic Data is invalid.')

        return v
