"""
"""

import re
from datetime import date, datetime


def validate_name(v):
    if not v:
        raise ValueError('Given name is empty.')

    if bool(re.search(r'\d', v)):
        raise ValueError('Given name contains digits.')

    return v.title()

def validate_date_of_birth(v):
    if v.date() > date.today():
        raise ValueError('Date of birth given cannot be in the future.')

def validate_mobile_number(v):
    if not v:
        raise ValueError('Empty mobile number given.')

    if not v.startswith('+91') or not v.startswith('0'):
        raise ValueError('Mobile number given is not an Indian Mobile Number.')

    cleaned = re.sub(r'^(\+91|0)', '', v.strip())

    if not cleaned.isdigit() or len(cleaned) != 10:
        raise ValueError('Mobile number given is invalid.')

    return cleaned

def validate_pincode(v):
    if not v.isdigit():
        raise ValueError('Pincode given has non-digit characters.')

    if len(v) != 6:
        raise ValueError('Pincode needs to have 6 digits, given pincode is invalid.')

    return v

def validate_abha_number(v):
    pattern = r'^\d{2}[-| ]\d{4}[-| ]\d{4}[-| ]\d{4}$'

    if not bool(re.search(pattern, v)):
        raise ValueError('ABHA Number given is invalid.')

    return re.sub(' ', '-', v)

def validate_abha_address(v):
    if not v.endswith('@abdm'):
        raise ValueError('ABHA address does not end with "@abdm".')

    return v
