"""
"""

from datetime import datetime, date
import re
from enum import StrEnum, auto
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict
)

from vitasync.models.ABHA.kyc import ABHAKYC
from vitasync.common.converter import concatenate_name


def validate_patient_id(pid: str) -> str:
    ID_LENGTH: int = 6
    l = len(pid)
    
    if l != ID_LENGTH:
        raise ValueError(f'Patient ID has an invalid length, expected: {ID_LENGTH} got: {l}.')

    # Custom validating logic
    if re.search(r'\d', pid) is not None:
        raise ValueError('Patient ID contains digits, which is an invalid format.')

    return pid

class MedicalCondition(StrEnum):
    PREGNANCY = auto()

class Patient(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pid: str = Field(
        ...,
        alias='patientID',
        description=''
    )
    name: str = Field(
        '',
        alias='patientName',
        description=''
    )
    mobile_number: str = Field(
        '',
        alias='mobileNumber',
        description=''
    )
    date_of_birth: datetime | None = Field(
        None,
        alias='dob',
        description=''
    )
    conditions: set[MedicalCondition] = Field(
        default_factory=set,
        alias='medicalConditions',
        description=''
    )
    is_active: bool = Field(
        True,
        alias='isActive',
        description=''
    )
    abha_kyc: ABHAKYC | None = Field(
        None,
        alias='abhaKYC',
        description=''
    )
    created_on: datetime = Field(
        default_factory=datetime.now,
        alias='createdOn',
        description=''
    )

    @field_validator('pid')
    @classmethod
    def validate_patient_id(cls, v):
        return validate_patient_id(v)

    @model_validator(mode='after')
    def validate_model(self) -> 'Patient':
        # Name
        if not self.name:
            if self.abha_kyc is None:
                raise ValueError('No name given to Patient, no ABHA KYC present to fetch the name.')

            self.name = concatenate_name(
                self.abha_kyc.demographic_data.first_name,
                self.abha_kyc.demographic_data.middle_name,
                self.abha_kyc.demographic_data.last_name
            )

        if re.search(r'\d', self.name) is not None:
            raise ValueError('Name given to Patient contains digits.')

        self.name = self.name.title()

        if self.abha_kyc is not None:
            if self.abha_kyc.demographic_data.first_name not in self.name:
                raise ValueError('First name given in ABHA KYC does not match with the name given manually.')

            if (
                self.abha_kyc.demographic_data.last_name and
                self.abha_kyc.demographic_data.last_name not in self.name
            ):
                self.name = concatenate_name(
                    self.abha_kyc.demographic_data.first_name,
                    self.abha_kyc.demographic_data.middle_name,
                    self.abha_kyc.demographic_data.last_name
                )

        # Mobile number
        if not self.mobile_number:
            if self.abha_kyc is None:
                raise ValueError('No mobile number given to Patient, no ABHA KYC present to fetch the number.')

            self.mobile_number = self.abha_kyc.demographic_data.mobile_number

        cleaned = re.sub(r'^(\+91|0)', '', self.mobile_number.strip())

        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError('Mobile number given for Patient is invalid.')

        # Date of birth
        if self.date_of_birth is None:
            if self.abha_kyc is None:
                raise ValueError('Cannot fetch date of birth automatically from ABHA KYC as no KYC was given. Input date of birth manually.')

            self.date_of_birth = self.abha_kyc.demographic_data.date_of_birth

        if self.abha_kyc is not None:
            if self.date_of_birth != self.abha_kyc.demographic_data.date_of_birth:
                raise ValueError('Manually inputted date of birth and date of birth given in ABHA KYC does not match.')

        return self

    @property
    def abha_name(self) -> str | None:
        return concatenate_name(
            self.abha_kyc.demographic_data.first_name,
            self.abha_kyc.demographic_data.middle_name,
            self.abha_kyc.demographic_data.last_name
        ) if self.abha_kyc is not None else None

    @property
    def abha_dob(self) -> date | None:
       return self.abha_kyc.demographic_data.date_of_birth if self.abha_kyc is not None else None

    def sync_mobile_number_with_abha(self) -> bool:
        if self.abha_kyc is None:
            return False

        self.mobile_number = self.abha_kyc.demographic_data.mobile_number
        return True
