"""
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict,
    ValidationError,
    model_validator
)
from enum import StrEnum, auto
import re
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import (
    PyMongoError,
    DuplicateKeyError
)
from datetime import datetime

from vitasync.exceptions.database import *
from vitasync.exceptions.generic import VitaSyncDataValidationError, VitaSyncInvalidInputsError
from vitasync.models.patient import (
    MedicalCondition,
    Patient,
    validate_patient_id as validate_pid
)
from vitasync.models.ABHA.kyc import ABHAKYC
from vitasync.models.ABHA.status import ABHAStatus
from vitasync.models.ABHA.gender import Gender
from vitasync.common.converter import (
    age_to_date_range,
    date_to_datetime_range
)
import vitasync.common.validator as validator


class ConditionGetAllArgsCheckType(StrEnum):
    CHECKALL = auto()
    CHECKANY = auto()

class ConditionGetAllArgs(BaseModel):
    conditions: set[MedicalCondition] = Field(
        ...,
        alias='conditions',
        description=''
    )
    checktype: ConditionGetAllArgsCheckType = Field(
        default=ConditionGetAllArgsCheckType.CHECKALL,
        alias='checkType',
        description=''
    )

    @field_validator('conditions')
    @classmethod
    def validate_conditions(cls, v):
        if len(v) == 0:
            raise ValueError('For list of conditions given in repositories.patient.ConditionGetAllArgs, there are no values, i.e. the list is empty.')

        return v

class ABHAKYCGetAllArgs(BaseModel):
    abha_status: ABHAStatus | None = Field(
        default=None,
        alias='abhaStatus',
        description=''
    )
    has_middle_name: bool | None = Field(
        default=None,
        alias='hasMiddleName',
        description=''
    )
    has_last_name: bool | None = Field(
        default=None,
        alias='hasLastName',
        description=''
    )
    gender: Gender | None = Field(
        default=None,
        alias='gender',
        description=''
    )

class GetFieldsResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pid: str = Field(
        ...,
        alias='patientID',
        description=''
    )
    name: str | None = Field(
        alias='patientName',
        default=None,
        description=''
    )
    mobile_number: str | None = Field(
        default=None,
        alias='mobileNumber',
        description=''
    )
    date_of_birth: datetime | None = Field(
        default=None,
        alias='dob',
        description=''
    )
    conditions: list[MedicalCondition] | None = Field(
        default=None,
        alias='medicalConditions',
        description=''
    )
    is_active: bool | None = Field(
        default=None,
        alias='isActive',
        description=''
    )
    abha_kyc: ABHAKYC | None = Field(
        default=None,
        alias='abhaKYC',
        description=''
    )
    created_on: datetime | None = Field(
        default=None,
        alias='createdOn',
        description=''
    )

class ConditionUpdateArgsUpdateType(StrEnum):
    APPEND = auto()
    REMOVE = auto()
    SET = auto()

class ConditionUpdateArgs(BaseModel):
    conditions: set[MedicalCondition] = Field(
        ...,
        alias='medicalConditions',
        description=''
    )
    updatetype: ConditionUpdateArgsUpdateType = Field(
        default=ConditionUpdateArgsUpdateType.APPEND,
        alias='updateType',
        description=''
    )

class ABHAKYCUpdateArgs(BaseModel):
    abha_number: str | None = Field(
        default=None,
        alias='abhaNumber',
        description=''
    )
    abha_address: str | None = Field(
        default=None,
        alias='abhaAddress',
        description=''
    )
    abha_status: ABHAStatus | None = Field(
        default=None,
        alias='abhaStatus',
        description=''
    )
    first_name: str | None = Field(
        default=None,
        alias='firstName',
        description=''
    )
    set_middle_name: bool = Field(
        default=False,
        alias='setMiddleName',
        description=''
    )
    middle_name: str | None = Field(
        default=None,
        alias='middleName',
        description=''
    )
    set_last_name: bool = Field(
        default=False,
        alias='setLastName',
        description=''
    )
    last_name: str | None = Field(
        default=None,
        alias='lastName',
        description=''
    )
    date_of_birth: datetime | None = Field(
        default=None,
        alias='dob',
        description=''
    )
    gender: Gender | None = Field(
        default=None,
        alias='gender',
        description=''
    )
    mobile_number: str | None = Field(
        default=None,
        alias='mobileNumber',
        description=''
    )
    set_address: bool = Field(
        default=False,
        alias='setAddress',
        description=''
    )
    address: str | None = Field(
        default=None,
        alias='address',
        description=''
    )
    district: str | None = Field(
        default=None,
        alias='district',
        description=''
    )
    state: str | None = Field(
        default=None,
        alias='state',
        description=''
    )
    pincode: str | None = Field(
        default=None,
        alias='pinCode',
        description=''
    )

    @field_validator('abha_number')
    @classmethod
    def validate_abha_number(cls, v):
        return validator.validate_abha_number(v) if v is not None else None

    @field_validator('abha_address')
    @classmethod
    def validate_abha_address(cls, v):
        return validator.validate_abha_address(v) if v is not None else None

    @field_validator('first_name', 'middle_name', 'last_name')
    @classmethod
    def validate_first_name(cls, v):
        return validator.validate_name(v) if v is not None else None

    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v):
        return validator.validate_date_of_birth(v) if v is not None else None

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls, v):
        return validator.validate_mobile_number(v) if v is not None else None

    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        return validator.validate_pincode(v) if v is not None else None

class UpdateArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pid: str = Field(
        ...,
        alias='patientID',
        description=''
    )
    name: str | None = Field(
        default=None,
        alias='patientName',
        description=''
    )
    mobile_number: str | None = Field(
        default=None,
        alias='mobileNumber',
        description=''
    )
    date_of_birth: datetime | None = Field(
        default=None,
        alias='dob',
        description=''
    )
    conditions: ConditionUpdateArgs | None = Field(
        default=None,
        alias='medicalConditions',
        description=''
    )
    is_active: bool | None = Field(
        default=None,
        alias='isActive',
        description=''
    )
    abha_kyc: ABHAKYCUpdateArgs | None = Field(
        default=None,
        alias='abhaKYC',
        description=''
    )

    @field_validator('pid')
    @classmethod
    def validate_patient_id(cls, v):
        return validate_pid(v)

    @field_validator('name')
    @classmethod
    def validate_patient_name(cls, v):
        return validator.validate_name(v) if v is not None else None

    @model_validator(mode='after')
    def validate_model(self) -> 'UpdateArgs':
        # TODO Validation
        return self

class PatientRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self._collection

    async def initialize(self) -> None:
        # Create patient id index
        await self._collection.create_index(
            'pid',
            unique=True
        )

        # Create mobile_number index
        await self._collection.create_index(
            'mobile_number',
            unique=True
        )
        await self._collection.create_index(
            'abha_kyc.demographic_data.mobile_number',
            unique=True
        )

        # Create abha number index
        await self._collection.create_index(
            'abha_kyc.abha_number',
            unique=True
        )

        # Create abha address index
        await self._collection.create_index(
            'abha_kyc.abha_address',
            unique=True
        )

    async def create(
        self,
        patient: Patient
    ) -> None:
        try:
            await self._collection.insert_one(
                patient.model_dump()
            )

        except DuplicateKeyError as exc:
            raise VitaSyncDuplicateEntryError() from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def delete(
        self,
        pid: str
    ):
        try:
            response = await self._collection.delete_one(
                {
                    'pid': pid
                }
            )

            if response.deleted_count == 0:
                raise VitaSyncAbsentEntryError()

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def update(
        self,
        updateargs: UpdateArgs
    ) -> None:
        # TODO Validation

        updater = {
            '$set': {
                **({'name': updateargs.name} if updateargs.name else {}),
                **({'mobile_number': updateargs.mobile_number} if updateargs.mobile_number else {}),
                **({'date_of_birth': updateargs.date_of_birth} if updateargs.date_of_birth else {}),
                **({'is_active': updateargs.is_active} if updateargs.is_active is not None else {})
            }
        }

        if updateargs.conditions is not None:
            ua = updateargs.conditions
            conditions_list = list(ua.conditions)

            match ua.updatetype:
                case ConditionUpdateArgsUpdateType.APPEND:
                    updater['$addToSet'] = {
                        'conditions': {
                            '$each': conditions_list
                        }
                    }

                case ConditionUpdateArgsUpdateType.REMOVE:
                    updater['$pullAll'] = {
                        'conditions': conditions_list
                    }

                case ConditionUpdateArgsUpdateType.SET:
                    updater['$set']['conditions'] = conditions_list

        if updateargs.abha_kyc is not None:
            ua = updateargs.abha_kyc

            updater['$set'] |= {
                # abha kyc
                **({'abha_kyc.abha_number': ua.abha_number} if ua.abha_number else {}),
                **({'abha_kyc.abha_address': ua.abha_address} if ua.abha_address else {}),
                **({'abha_kyc.abha_status': ua.abha_status.value} if ua.abha_status is not None else {}),

                # demograpbic data
                **({'abha_kyc.demographic_data.first_name': ua.first_name} if ua.first_name else {}),
                **({'abha_kyc.demographic_data.middle_name': ua.middle_name} if ua.set_middle_name else {}),
                **({'abha_kyc.demographic_data.last_name': ua.last_name} if ua.set_last_name else {}),
                **({'abha_kyc.demographic_data.date_of_birth': ua.date_of_birth} if ua.date_of_birth is not None else {}),
                **({'abha_kyc.demographic_data.gender': ua.gender.value} if ua.gender is not None else {}),
                **({'abha_kyc.demographic_data.mobile_number': ua.mobile_number} if ua.mobile_number else {}),

                # structural address
                **({'abha_kyc.structural_address.address': ua.address} if ua.set_address else {}),
                **({'abha_kyc.structural_address.district': ua.district} if ua.district else {}),
                **({'abha_kyc.structural_address.state': ua.state} if ua.state else {}),
                **({'abha_kyc.structural_address.pincode': ua.pincode} if ua.pincode else {})
            }

        updater = {k: v for k, v in updater.items() if v}

        if not updater: 
            # Empty dict
            raise VitaSyncInvalidInputsError(['updateargs'], 'No fields provided to update.')

        try:
            response = await self._collection.update_one(
                {
                    'pid': updateargs.pid
                },
                updater
            )

            if response.matched_count == 0:
                raise VitaSyncAbsentEntryError()

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def get(
        self,
        pid: str
    ) -> Patient | None:
        try:
            response = await self._collection.find_one(
                {
                    'pid': pid
                }
            )

            try:
                return Patient(**response) if response is not None else None

            except ValidationError as exc:
                raise VitaSyncDataValidationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def getall(
        self,
        size: int = 0,
        offset: int = 0,
        name_search: str | None = None,
        conditions: ConditionGetAllArgs | None = None,
        is_active: bool | None = None,
        age: int | None = None,
        abha_kyc_exists: bool | None = None,
        abha_kyc: ABHAKYCGetAllArgs | None = None
    ) -> list[Patient]:
        size = size if size >= 0 else 0
        offset = offset if offset >= 0 else 0

        query = {}

        if is_active is not None:
            query['is_active'] = is_active

        if age is not None: 
            date_range = age_to_date_range(age)

            if date_range is None: # age <= 0
                raise VitaSyncInvalidInputsError(['patient repository getall age'], 'Age parameter given to PatientRepository::getall is lte 0.')

            to_datetime_range = (
                date_to_datetime_range(date_range[0]),
                date_to_datetime_range(date_range[1])
            )

            query['date_of_birth'] = {
                '$lte': to_datetime_range[1][1],
                '$gte': to_datetime_range[0][0]
            }

        if abha_kyc_exists is not None:
            query['abha_kyc'] = abha_kyc_exists

            if not abha_kyc_exists and abha_kyc is not None:
                abha_kyc = None

        if name_search:
            query['name'] = {
                '$regex': f'^{re.escape(name_search)}',
                '$options': 'i'
            }

        if abha_kyc is not None:
            if abha_kyc.abha_status:
                query['abha_kyc.abha_status'] = abha_kyc.abha_status

            if abha_kyc.has_middle_name is not None:
                query['abha_kyc.middle_name'] = {
                    '$ne': None
                } if abha_kyc.has_middle_name else None

            if abha_kyc.has_last_name is not None:
                query['abha_kyc.last_name'] = {
                    '$ne': None
                } if abha_kyc.has_last_name else None

            if abha_kyc.gender is not None:
                query['abha_kyc.gender'] = abha_kyc.gender.value

        if conditions is not None:
            operator = '$all' if conditions.checktype == ConditionGetAllArgsCheckType.CHECKALL else '$in'
            query['conditions'] = {
                operator: conditions.conditions
            }

        try:
            response = await (
                self._collection
                .find(query)
                .sort(
                    [
                        ('name', 1),
                        ('pid', 1)
                    ]
                )
                .skip(offset)
                .limit(size)
            ).to_list() # TODO figure out if you need some forced pagination to avoid massive list creation

            try:
                return [
                    Patient(**field) for field in response
                ]    

            except ValidationError as exc:
                raise VitaSyncDataValidationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def getfields(
        self,
        pid: str,
        name: bool = False,
        mobile_number: bool = False,
        date_of_birth: bool = False,
        conditions: bool = False,
        is_active: bool = False,
        abha_kyc: bool = False,
        created_on: bool = False
    ) -> GetFieldsResult | None:
        if not pid:
            return

        try:
            response = await self._collection.find_one(
                {
                    'pid': pid
                },
                {
                    '_id': 0,
                    'pid': 1,
                    'name': int(name),
                    'mobile_number': int(mobile_number),
                    'date_of_birth': int(date_of_birth),
                    'conditions': int(conditions),
                    'is_active': int(is_active),
                    'abha_kyc': int(abha_kyc),
                    'created_on': int(created_on)
                }
            )

            try:
                return GetFieldsResult(**response) if response is not None else None

            except ValidationError as exc:
                raise VitaSyncDataValidationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def getpid(
        self,
        mobile_number: str | None = None,
        abha_number: str | None = None,
        abha_address: str | None = None,
        abha_mobile_number: str | None = None
    ) -> str | None:
        try:
            response = await self._collection.find_one(
                {
                    **({'mobile_number': mobile_number} if mobile_number else {}),
                    **({'abha_kyc.abha_number': abha_number} if abha_number else {}),
                    **({'abha_kyc.abha_address': abha_address} if abha_address else {}),
                    **({'abha_kyc.demographic_data.mobile_number': abha_mobile_number} if abha_mobile_number else {})
                },
                {
                    '_id': 0,
                    'pid': 1
                }
            )

            return response['pid'] if response is not None else None

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc
