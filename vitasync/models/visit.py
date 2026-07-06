"""
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)
from datetime import datetime

import vitasync.common.validator as validator
from vitasync.common.idgenerator import (
    PatientID, 
    VisitID
)
from vitasync.models.vitals import Vitals
from vitasync.models.prescription import Prescription
from vitasync.models.diagnostic_report import DiagnosticReport


class Visit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vid: str = Field(
        ...,
        serialization_alias='visitID',
        validation_alias='visitID',
        description=''
    )

    pid: str = Field(
        ...,
        serialization_alias='patientID',
        validation_alias='patientID',
        description=''
    )

    timestamp: datetime = Field(
        ...,
        serialization_alias='timestamp',
        validation_alias='timestamp',
        description=''
    )

    attending_hpr_id: str = Field(
        ...,
        serialization_alias='attendingHPRID',
        validation_alias='attendingHRPID',
        description=''
    )

    fees_paid: float = Field(
        default=0.0,
        serialization_alias='feesPaid',
        validation_alias='feesPaid',
        description=''
    )

    fees_pending: float = Field(
        default=0.0,
        serialization_alias='feesPending',
        validation_alias='feesPending',
        description=''
    )

    notes: str = Field(
        default='',
        serialization_alias='notes',
        validation_alias='notes',
        description=''
    )

    vitals: Vitals | None = Field(
        default=None,
        serialization_alias='vitals',
        validation_alias='vitals',
        description=''
    )

    prescriptions: list[Prescription] = Field(
        default_factory=list,
        serialization_alias='prescriptions',
        validation_alias='prescriptions',
        description=''
    )

    diagnostics: list[DiagnosticReport] = Field(
        default_factory=list,
        serialization_alias='diagnostics',
        validation_alias='diagnostics',
        description=''
    )

    @field_validator('vid')
    @classmethod
    def validate_vid(cls, v):
        return VisitID.validate(v)

    @field_validator('pid')
    @classmethod
    def validate_pid(cls, v):
        return PatientID.validate(v)

    @field_validator('attending_hpr_id')
    @classmethod
    def validate_attending_hpr_id(cls, v):
        return validator.validate_hpr_id(v)

    @field_validator('fees_paid', 'fees_pending')
    @classmethod
    def validate_fees(cls, v):
        if v < 0.0:
            raise ValueError('Fees paid or pending cannot be less than zero.')

        return v

    @field_validator('prescriptions')
    @classmethod
    def validate_prescriptions(cls, v):
        return v # TODO See if this requires any validation

    @field_validator('diagnostics')
    @classmethod
    def validate_diagnostics(cls, v):
        return v # TODO See if this requires any validation
