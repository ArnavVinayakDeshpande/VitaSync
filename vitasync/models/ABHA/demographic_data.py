"""
"""

from datetime import datetime, date
import re
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)

from vitasync.exceptions.generic import *
from vitasync.models.ABHA.gender import Gender


class ABHADemographicData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    first_name: str = Field(
        ...,
        serialization_alias='firstName',
        description='Legal first name',
        min_length=1
    )
    middle_name: str | None = Field(
        default=None,
        serialization_alias='middleName',
        description='Optional middle name'
    )
    last_name: str | None = Field(
        default=None,
        serialization_alias='lastName',
        description='Optional Legal Last Name'
    )
    date_of_birth: datetime = Field(
        ...,
        serialization_alias='dob',
        description='Parsed date of birth.'
    )
    gender: Gender = Field(
        ...,
        serialization_alias='gender',
        max_length=1,
        description='M, F, or O identifier'
    )
    mobile_number: str = Field(
        ...,
        serialization_alias='mobileNumber',
        description='AADHAR-linked and registered mobile number'
    )

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v):
        if not v:
            raise ValueError('First name given for ABHA Demographic Data is empty.')

        if bool(re.search(r'\d', v)):
            raise ValueError('First name given for ABHA Demographic Data contains digits.')

        return v.title()

    @field_validator('middle_name', 'last_name')
    @classmethod
    def validate_middle_and_last_name(cls, v):
        if not v:
            return None

        if bool(re.search(r'\d', v)):
            raise ValueError('Name parameter given for ABHA Demographic Data contains digits.')

        return v.title()

    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v):
        if v.date() > date.today():
            raise ValueError('Birth date given for ABHA Demographic Data is greater than current date.')

        return datetime.combine(v.date(), datetime.min.time())

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls, v: str):
        if not v:
            raise ValueError('Mobile number given for ABHA Demographic Data is empty.')

        cleaned = re.sub(r'^(\+91|0)', '', v.strip())

        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError('Mobile number given for ABHA Demographic Data is invalid.')

        return cleaned
