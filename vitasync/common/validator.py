"""
@file validator.py
@brief Shared field validation functions for VitaSync Pydantic models.

@details
This module provides reusable, pure validation functions that are called
from Pydantic @field_validator methods across multiple models in the
VitaSync codebase. By centralizing validation logic here, each rule is
defined exactly once and referenced wherever needed — preventing the
duplication and silent divergence that would occur if the same validation
logic were copy-pasted into every model that requires it.

Each function in this module follows the Pydantic field validator contract:
  - Accepts the raw field value as input.
  - Returns the validated (and optionally normalized) value on success.
  - Raises ValueError with a descriptive message on failure.
    Pydantic catches this ValueError and wraps it into a ValidationError
    at the model level — callers should never need to catch ValueError
    from these functions directly.

@note All functions are pure and stateless. They perform no I/O, no database
      access, and no network calls. They are safe to call from any layer
      of the application, including model validators, manager logic, and
      standalone scripts.

@note These functions validate and normalize values for storage. Mobile numbers,
      for example, are stripped of their prefix and stored as 10-digit strings.
      Callers should be aware of this normalization behavior.
"""

import re
from datetime import date, datetime


def validate_name(v: str) -> str:
    """
    @brief Validates and normalizes a human name string.

    @details
    Enforces two rules:
      1. The name must not be empty or whitespace-only.
      2. The name must not contain any digit characters (0-9).

    On success, the name is normalized to title case (e.g. "priya sharma"
    becomes "Priya Sharma") to ensure consistent casing in stored records
    regardless of how the input was provided.

    This function is used to validate first_name, middle_name, and last_name
    fields across Patient, ABHADemographicData, and any other model that
    stores human name components.

    @param v The name string to validate. May be a first, middle, or last name.

    @return The name string normalized to title case.

    @throws ValueError If the name is empty or contains digit characters.
    """
    if not v:
        raise ValueError(
            'Name field cannot be empty. '
            'A valid non-empty name string must be provided.'
        )

    if bool(re.search(r'\d', v)):
        raise ValueError(
            f'Name "{v}" contains digit characters, which are not permitted in a name field. '
            f'Please provide a name containing only alphabetic characters and spaces.'
        )

    return v.title()


def validate_date_of_birth(v: datetime) -> datetime:
    """
    @brief Validates that a date of birth is not in the future.

    @details
    Compares the date component of the provided datetime against today's date.
    A date of birth set in the future is nonsensical and indicates either a
    data entry error or a malformed request.

    This function expects a datetime object (not a bare date), consistent with
    VitaSync's convention of storing all date-only values as datetime at midnight
    after conversion via date_to_datetime(). The time component is ignored during
    comparison — only the calendar date is checked.

    @param v The datetime representing the date of birth to validate.
             Must be a datetime instance, not a bare date.

    @return The original datetime value, unchanged, if validation passes.

    @throws ValueError If the date of birth is later than today's date.
    """
    if v.date() > date.today():
        raise ValueError(
            f'Date of birth "{v.date().isoformat()}" cannot be in the future. '
            f'Please provide a valid date of birth on or before today ({date.today().isoformat()}).'
        )

    return v


def validate_mobile_number(v: str) -> str:
    """
    @brief Validates and normalizes an Indian mobile phone number.

    @details
    Enforces the following rules for Indian mobile numbers:
      1. The number must not be empty or whitespace-only.
      2. The number must begin with either '+91' (international format) or
         '0' (domestic trunk prefix format).
      3. After stripping the prefix, the remaining digits must be exactly
         10 characters long and consist entirely of digit characters.

    On success, the prefix is stripped and only the bare 10-digit number
    is returned. This normalized form is what is stored in the database,
    ensuring consistent lookup regardless of whether the number was originally
    provided with '+91' or '0'.

    Example normalizations:
      '+919876543210' → '9876543210'
      '09876543210'   → '9876543210'

    @param v The mobile number string to validate. Leading/trailing whitespace
             is stripped before processing.

    @return The normalized 10-digit mobile number string with no prefix.

    @throws ValueError If the number is empty, does not begin with a valid
                       Indian prefix, or is not a valid 10-digit number after
                       prefix removal.
    """
    if not v:
        raise ValueError(
            'Mobile number cannot be empty. '
            'A valid Indian mobile number must be provided.'
        )

    stripped = v.strip()

    if not stripped.startswith('+91') and not stripped.startswith('0'):
        raise ValueError(
            f'Mobile number "{v}" does not appear to be a valid Indian mobile number. '
            f'Indian mobile numbers must begin with "+91" (international format) '
            f'or "0" (domestic trunk prefix format).'
        )

    cleaned = re.sub(r'^(\+91|0)', '', stripped)

    if not cleaned.isdigit() or len(cleaned) != 10:
        raise ValueError(
            f'Mobile number "{v}" is invalid. After removing the country or trunk prefix, '
            f'the number must consist of exactly 10 digit characters. '
            f'Got "{cleaned}" ({len(cleaned)} characters).'
        )

    return cleaned


def validate_pincode(v: str) -> str:
    """
    @brief Validates an Indian postal pincode string.

    @details
    Enforces the following rules for Indian pincodes:
      1. The pincode must consist entirely of digit characters (no letters,
         spaces, or special characters).
      2. The pincode must be exactly 6 digits long, consistent with India's
         6-digit postal index number (PIN) format.

    The value is returned unchanged on success — no normalization is applied
    since a valid pincode is already in its canonical form.

    @param v The pincode string to validate.

    @return The original pincode string, unchanged, if validation passes.

    @throws ValueError If the pincode contains non-digit characters or is
                       not exactly 6 digits in length.
    """
    if not v.isdigit():
        raise ValueError(
            f'Pincode "{v}" contains non-digit characters. '
            f'Indian pincodes must consist of exactly 6 digit characters (e.g. "400001").'
        )

    if len(v) != 6:
        raise ValueError(
            f'Pincode "{v}" has {len(v)} digit(s), but Indian pincodes must be '
            f'exactly 6 digits in length (e.g. "400001").'
        )

    return v


def validate_abha_number(v: str) -> str:
    """
    @brief Validates and normalizes an ABHA number string.

    @details
    ABHA (Ayushman Bharat Health Account) numbers are 14-digit identifiers
    issued by the National Health Authority of India, formatted as:

        XX-XXXX-XXXX-XXXX

    Where each segment is separated by a hyphen. The NHA also accepts space
    as a separator in some contexts. This function validates that the provided
    string matches the expected segmented format (with either hyphens or spaces
    as separators), then normalizes all spaces to hyphens for consistent storage.

    The regex pattern is anchored at both ends (^ and $) to reject strings that
    contain a valid ABHA number embedded within additional characters.

    Example normalizations:
      '14 4567 8901 2345' → '14-4567-8901-2345'
      '14-4567-8901-2345' → '14-4567-8901-2345' (unchanged)

    @param v The ABHA number string to validate. May use hyphens or spaces
             as segment separators.

    @return The ABHA number string with all segment separators normalized to
            hyphens.

    @throws ValueError If the string does not match the expected ABHA number
                       format XX-XXXX-XXXX-XXXX.
    """
    pattern = r'^\d{2}[-| ]\d{4}[-| ]\d{4}[-| ]\d{4}$'

    if not bool(re.match(pattern, v)):
        raise ValueError(
            f'ABHA number "{v}" does not match the expected format XX-XXXX-XXXX-XXXX '
            f'(e.g. "14-4567-8901-2345"). Segment separators may be hyphens or spaces. '
            f'The number must consist of exactly 14 digits across four segments.'
        )

    return re.sub(r' ', '-', v)


def validate_abha_address(v: str) -> str:
    """
    @brief Validates an ABHA address (PHR address) string.

    @details
    ABHA addresses (also known as PHR addresses — Personal Health Record addresses)
    are user-chosen health identifiers issued under the ABDM ecosystem, following
    the format:

        username@abdm

    This function enforces the mandatory '@abdm' suffix, which identifies the
    address as belonging to the national ABDM health identity namespace.
    No validation is performed on the username portion — only the suffix
    is checked.

    Example valid addresses:
      'priya.sharma@abdm'
      'priya123@abdm'

    @param v The ABHA address string to validate.

    @return The original ABHA address string, unchanged, if validation passes.

    @throws ValueError If the address does not end with the '@abdm' suffix.
    """
    if not v.endswith('@abdm'):
        raise ValueError(
            f'ABHA address "{v}" does not end with "@abdm". '
            f'All ABHA addresses must use the "@abdm" namespace suffix '
            f'(e.g. "priya.sharma@abdm").'
        )

    return v
    