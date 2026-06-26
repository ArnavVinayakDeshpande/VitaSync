"""
"""

from datetime import datetime
import re
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)

from vitasync.models.prescription import Prescription
from vitasync.models.vitals import Vitals


def validate_visit_id(vid: str) -> str:
    ID_LENGTH: int = 8
    l = len(vid)

    if l != ID_LENGTH:
        raise ValueError(f'Visit ID has an invalid length, expected: {ID_LENGTH} got: {l}')

    # Custom validating logic
    if re.search(r'\d', vid) is not None:
        raise ValueError('Visit ID contains digits, which is an invalid format.')

    return vid

class Visit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vid: str = Field(
        ...,
        alias='visitID',
        description=''
    )
    timestamp: datetime = Field(
        ...,
        alias='timeStamp',
        description=''
    )
    prescriptions: list[Prescription] = Field(
        default_factory=list,
        alias='prescriptions',
        description=''
    )
    notes: str = Field(
        '',
        alias='notes',
        description=''
    )
    fees_paid: float = Field(
        0,
        alias='feesPaid',
        description=''
    )
    fees_pending: float = Field(
        0,
        alias='feesPending',
        description=''
    )
    vitals: Vitals | None = Field(
        None,
        alias='vitals',
        description=''
    )

    @field_validator('vid')
    @classmethod
    def validate_visit_id(cls, v):
        return validate_visit_id(v)

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        if v > datetime.now():
            raise ValueError('Visit timestamp is greater than timestamp of "now". Cannot input timestamps of the future.')
        return v

    @field_validator('fees_paid', 'fees_pending')
    def validate_fees(cls, v):
        if v < 0:
            raise ValueError('Fees of some kind (paid/pending) are less than zero, which is invalid.')
        return v
