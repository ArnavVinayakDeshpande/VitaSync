"""
@file demographic_data.py

@brief Defines the ABHA demographic information model.

@details
Provides the ABHADemographicData model, which represents the demographic
information associated with an individual's ABHA (Ayushman Bharat Health
Account).

The model stores personal identity information including the individual's
name, date of birth, gender, and ABHA-linked mobile number. It also
performs validation and normalization of all supplied data to ensure that
the information conforms to the application's expected format before being
used elsewhere in the system.
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


# ── ABHA Demographic Data Model ────────────────────────────────────────────────

class ABHADemographicData(BaseModel):
    """
    @brief Represents an individual's ABHA demographic information.

    @details
    Stores the demographic information associated with an individual's
    ABHA account, including their legal name, date of birth, gender, and
    registered mobile number.

    The model validates and normalizes all supplied values to ensure
    consistency throughout the application. Name fields are converted to
    title case, mobile numbers are normalized to the standard ten-digit
    format, and dates of birth are validated to ensure they do not refer
    to a future date.
    """

    model_config = ConfigDict(populate_by_name=True)

    first_name: str = Field(
        ...,
        serialization_alias='firstName',
        validation_alias='firstName',
        description='The individual\'s legal first name as recorded in their ABHA demographic information.',
        min_length=1
    )

    middle_name: str | None = Field(
        default=None,
        serialization_alias='middleName',
        validation_alias='middleName',
        description='The individual\'s legal middle name, if one exists.'
    )

    last_name: str | None = Field(
        default=None,
        serialization_alias='lastName',
        validation_alias='lastName',
        description='The individual\'s legal last name or family name, if one exists.'
    )

    date_of_birth: datetime = Field(
        ...,
        serialization_alias='dob',
        validation_alias='dob',
        description='The individual\'s date of birth. The time component is normalized during validation.'
    )

    gender: Gender = Field(
        ...,
        serialization_alias='gender',
        validation_alias='gender',
        max_length=1,
        description='The individual\'s gender as represented by the ABHA Gender enumeration.'
    )

    mobile_number: str = Field(
        ...,
        serialization_alias='mobileNumber',
        validation_alias='mobileNumber',
        description='The mobile number registered with and linked to the individual\'s ABHA account.'
    )

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v):
        """
        @brief Validates the individual's first name.

        @details
        Ensures that the supplied first name is not empty and does not
        contain numeric characters.

        The validated name is normalized into title case before being
        stored.

        @param v
            The supplied first name.

        @return
            The normalized first name.

        @throws ValueError
            If the supplied first name is empty or contains numeric
            characters.
        """
        if not v:
            raise ValueError('First name given for ABHA Demographic Data is empty.')

        if bool(re.search(r'\d', v)):
            raise ValueError('First name given for ABHA Demographic Data contains digits.')

        return v.title()

    @field_validator('middle_name', 'last_name')
    @classmethod
    def validate_middle_and_last_name(cls, v):
        """
        @brief Validates optional middle and last names.

        @details
        Ensures that optional name fields do not contain numeric
        characters.

        If no value is supplied, None is returned. Otherwise, the supplied
        name is normalized into title case before being stored.

        @param v
            The supplied middle or last name.

        @return
            The normalized name, or None if no value was supplied.

        @throws ValueError
            If the supplied name contains numeric characters.
        """
        if not v:
            return None

        if bool(re.search(r'\d', v)):
            raise ValueError('Name parameter given for ABHA Demographic Data contains digits.')

        return v.title()

    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v):
        """
        @brief Validates the individual's date of birth.

        @details
        Ensures that the supplied date of birth is not later than the
        current date.

        The returned value is normalized so that its time component is set
        to midnight.

        @param v
            The supplied date of birth.

        @return
            The normalized date of birth.

        @throws ValueError
            If the supplied date of birth lies in the future.
        """
        if v.date() > date.today():
            raise ValueError('Birth date given for ABHA Demographic Data is greater than current date.')

        return datetime.combine(v.date(), datetime.min.time())

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls, v: str):
        """
        @brief Validates an ABHA-linked mobile number.

        @details
        Removes supported Indian dialing prefixes before validating that
        the resulting mobile number contains exactly ten numeric digits.

        @param v
            The supplied mobile number.

        @return
            The normalized ten-digit mobile number.

        @throws ValueError
            If the supplied mobile number is empty or is not a valid
            Indian mobile number.
        """
        if not v:
            raise ValueError('Mobile number given for ABHA Demographic Data is empty.')

        cleaned = re.sub(r'^(\+91|0)', '', v.strip())

        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError('Mobile number given for ABHA Demographic Data is invalid.')

        return cleaned
        