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
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError, DuplicateKeyError
from datetime import date, datetime
from enum import Enum, auto

from vitasync.exceptions.database import *
from vitasync.exceptions.generic import VitaSyncDataValidationError, VitaSyncInvalidInputsError
from vitasync.models.visit import Visit
from vitasync.models.prescription import Prescription
from vitasync.models.diagnostic_report import DiagnosticReport, DiagnosticCategory
import vitasync.common.validator as validator
from vitasync.common.converter import to_mongo_dict, date_to_datetime_range
from vitasync.common.idgenerator import PatientID, VisitID
# from vitasync.repositories.patient import GetFieldsResult
from vitasync.models.vitals import Vitals


class PrescriptionGetAllArgsCheckType(Enum):
    CHECKALL = auto()
    CHECKANY = auto()


class PrescriptionGetAllArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prescriptions: list[Prescription] = Field(
        default_factory=list,
        description=''
    )

    checktype: PrescriptionGetAllArgsCheckType = Field(
        default=PrescriptionGetAllArgsCheckType.CHECKALL
    )


class DiagnosticReportsGetAllArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: DiagnosticCategory | None = Field(
        None,
        description=''
    )

    has_clinical_summary: bool | None = Field(
        None,
        description=''
    )

    ordered_by_hpr_id: str | None = Field(
        None,
        description=''
    )

    has_report_files: bool | None = Field(
        None,
        description=''
    )

    is_abnormal: bool | None = Field(
        None,
        description=''
    )


class GetFieldsResult(BaseModel):
    vid: str = Field(
        ...,
        serialization_alias='visitID',
        validation_alias='visitID',
        description=''
    )

    pid: str | None = Field(
        None,
        serialization_alias='patientID',
        validation_alias='patientID',
        description=''
    )

    timestamp: datetime | None = Field(
        None,
        serialization_alias='timeStamp',
        validation_alias='timeStamp',
        description=''
    )

    attending_hpr_id: str | None = Field(
        None
    )

    fees_paid: float | None = Field(
        None
    )

    fees_pending: float | None = Field(
        None
    )

    notes: str | None = Field(
        None
    )

    vitals: Vitals | None = Field(
        None
    )

    was_vitals_queried: bool = Field(
        False
    )

    prescriptions: list[Prescription] | None = Field(
        None
    )

    diagnostics: list[DiagnosticReport] | None = Field(
        None
    )


class FeesUpdateArgsType(Enum):
    SET = auto()
    INC = auto()
    DEC = auto()


class FeesUpdateArgs(BaseModel):
    fees: float = Field(
        ...
    )

    updatetype: FeesUpdateArgsType = Field(
        FeesUpdateArgsType.SET
    )


class VitalsUpdateArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    systolic_bp: int | None = Field(
        None
    )

    set_systolic_bp: bool = Field(
        False
    )

    diastolic_bp: int | None = Field(
        None
    )

    set_diastolic_bp: bool = Field(
        False
    )

    weight_kg: float | None = Field(
        None
    )

    set_weight: bool = Field(
        False
    )

    pulse_bpm: int | None = Field(
        None
    )

    set_pulse: bool = Field(
        False
    )

    temperature_f: float | None = Field(
        None
    )

    set_temperature: bool = Field(
        False
    )

    spo2: int | None = Field(
        None
    )

    set_spo2: bool = Field(
        False
    )

    height_cm: float | None = Field(
        None
    )

    set_height: bool = Field(
        False
    )


class PrescriptionUpdateArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prescriptions: list[Prescription] = Field(
        ...,
        min_length=1
    )





class DiagnosticReportUpdateArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class UpdateArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fees_paid: FeesUpdateArgs | None = Field(
        None
    )

    fees_pending: FeesUpdateArgs | None = Field(
        None
    )

    notes: str | None = Field(
        None
    )

    vitals: VitalsUpdateArgs | None = Field(
        None
    )

    prescriptions: PrescriptionUpdateArgs | None = Field(
        None
    )

    diagnostics: DiagnosticReportUpdateArgs | None = Field(
        None
    )


class VisitRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        self._initialized: bool = False

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self._collection

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return

        try:
            await self._collection.create_index(
                'vid',
                unique=True
            )

            await self._collection.create_index(
                'pid',
                unique=False
            )

            await self._collection.create_index(
                'attending_hpr_id',
                unique=True
            )

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

        self._initialized = True

    async def create(
        self,
        visit: Visit
    ) -> None:
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            await self._collection.insert_one(
                to_mongo_dict(visit)
            )

        except DuplicateKeyError as exc:
            raise VitaSyncDuplicateEntryError() from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def delete(
        self,
        vid: str
    ) -> None:
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            VisitID.validate(vid)

            response = await self._collection.delete_one(
                {
                    'vid': vid
                }
            )

            if response.deleted_count == 0:
                raise VitaSyncAbsentEntryError()

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def update(
        self,
        vid: str,
        updateargs: UpdateArgs
    ):
        return

    async def get(
        self,
        vid: str
    ): 
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        VisitID.validate(vid)

        try:
            response = await self._collection.find_one(
                {
                    'vid': vid
                }
            )

            try:
                return Visit(**response) if response is not None else None

            except ValidationError as exc:
                raise VitaSyncDataValidationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc
        
    async def getall(
        self,
        size: int = 0,
        offset: int = 0,
        pid: str | None = None,
        occured_on: date | None = None,
        attending_hpr_id: str | None = None,
        is_fees_pending: bool | None = None,
        has_vitals: bool | None = None,
        prescriptions: PrescriptionGetAllArgs = PrescriptionGetAllArgs(**{}),
        diagnostics: DiagnosticReportsGetAllArgs = DiagnosticReportsGetAllArgs(**{})
    ) -> list[Visit]:
        # TODO Validation

        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        if size < 0 or offset < 0:
            raise VitaSyncInvalidInputsError(['size', 'offset'], 'One of the given values is negative, which is invalid.')

        query = {}

        if pid:
            query['pid'] = pid

        if occured_on is not None:
            datetime_range = date_to_datetime_range(occured_on)
            query['timestamp'] = {
                '$gte': datetime_range[0],
                '$lt': datetime_range[1]
            }

        if attending_hpr_id:
            query['attending_hpr_id'] = attending_hpr_id

        if is_fees_pending is not None:
            query['fees_pending'] = {'$gt': 0.0} if is_fees_pending else 0.0

        if has_vitals is not None:
            query['vitals'] = {'$ne': None} if has_vitals else None

        if prescriptions.prescriptions:
            operator = (
                '$all'
                if prescriptions.checktype == PrescriptionGetAllArgsCheckType.CHECKALL
                else '$in'
            )

            query['prescriptions'] = {
                operator: prescriptions.prescriptions
            }

        query |= {
            **({'diagnostics.category': diagnostics.category.value if diagnostics.category is not None else {}}),
            **({
                'diagnostics.clinical_summary': {'$ne': None} if diagnostics.has_clinical_summary else None
            } if diagnostics.has_clinical_summary is not None else {}),
            **({'diagnostics.ordered_by_hpr_id': diagnostics.ordered_by_hpr_id} if diagnostics.ordered_by_hpr_id else {}),
            **({
                'diagnostics.report_file_urls': {'$ne': None} if diagnostics.has_report_files else None
            } if diagnostics.has_report_files is not None else {}),
            **({'is_abnormal': diagnostics.is_abnormal} if diagnostics.is_abnormal is not None else {})
        }

        try:
            response = await (
                self._collection
                .find(query)
                .sort(
                    [
                        ('timestamp', -1),
                        ('vid', 1)
                    ]
                )
                .skip(offset)
                .limit(offset)
            ).to_list()

            try:
                return [
                    Visit(**field) for field in response
                ]
            
            except ValidationError as exc:
                raise VitaSyncDataValidationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def getfields(
        self,
        vid: str,
        pid: bool = False,
        timestamp: bool = False,
        attending_hpr_id: bool = False,
        fees_paid: bool = False,
        fees_pending: bool = False,
        notes: bool = False,
        vitals: bool = False,
        prescriptions: bool = False,
        diagnostics: bool = False
    ) -> GetFieldsResult | None:
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        # TODO Validate

        try:
            response = await self._collection.find_one(
                {
                    'vid': vid
                },
                {
                    '_id': 0,
                    'vid': 1,
                    'pid': int(pid),
                    'timestamp': int(timestamp),
                    'attending_hpr_id': int(attending_hpr_id),
                    'fees_paid': int(fees_paid),
                    'fees_pending': int(fees_pending),
                    'notes': int(notes),
                    'vitals': int(vitals),
                    'prescriptions': int(prescriptions),
                    'diagnostics': int(diagnostics)
                }
            )

            try:
                return GetFieldsResult(**response) if response is not None else None

            except ValidationError as exc:
                raise VitaSyncDataValidationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc
