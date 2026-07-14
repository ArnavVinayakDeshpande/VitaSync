"""
@file patient.py
@brief MongoDB repository implementation for patient data persistence.

@details
This module provides PatientRepository, the repository responsible for all
persistent storage and retrieval operations involving Patient objects.

The repository encapsulates all MongoDB-specific logic and exposes a typed,
domain-oriented interface for performing CRUD operations and patient queries.
Higher application layers (such as managers and API routers) interact only
with repository methods and never directly access MongoDB collections or
construct MongoDB queries.

In addition to the repository implementation, this module defines several
Pydantic models representing the structured arguments accepted by repository
operations. These models provide validation and strongly typed interfaces for
complex queries and partial updates, including:

  - Patient filtering criteria used by getall().
  - Partial update specifications for update().
  - Field projection results returned by getfields().

Repository responsibilities include:

  - Creating and maintaining MongoDB indexes required for data integrity and
    efficient querying.

  - Translating MongoDB driver exceptions into VitaSync-specific database
    exceptions, preventing Motor or PyMongo exception types from propagating
    beyond the repository layer.

  - Converting MongoDB documents into validated Patient model instances before
    returning them to higher layers, ensuring that malformed database records
    are detected immediately.

  - Constructing MongoDB query and update documents from strongly typed
    repository argument models.

This repository represents the only component within the application that has
direct knowledge of MongoDB collection names, document structure, indexes, and
query syntax.

@note Repository initialization must be performed explicitly by calling
      PatientRepository.initialize() during application startup before any
      CRUD operations are attempted. Initialization creates the indexes relied
      upon for uniqueness constraints and query performance.

@note All database operations are asynchronous and are implemented using
      Motor's AsyncIOMotorCollection API.
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
    NetworkTimeout,
    OperationFailure,
    PyMongoError,
    DuplicateKeyError
)
from datetime import datetime

from vitasync.common.error import *
from vitasync.models.patient import (
    MedicalCondition,
    Patient
)
from vitasync.common.idgenerator import PatientID
from vitasync.models.ABHA.kyc import ABHAKYC
from vitasync.models.ABHA.status import ABHAStatus
from vitasync.models.ABHA.gender import Gender
from vitasync.common.converter import (
    age_to_date_range,
    date_to_datetime_range,
    to_mongo_dict
)
import vitasync.common.validator as validator


# ── Query Argument Models ─────────────────────────────────────────────────────

class ConditionGetAllArgsCheckType(StrEnum):
    """
    @brief Specifies how multiple medical conditions should be matched.

    @details
    Defines the matching strategy used when filtering patients by multiple
    medical conditions. This enumeration is consumed by
    PatientRepository.getall() to determine whether all specified conditions
    must be satisfied or whether the presence of any single condition is
    sufficient.

    @note
        This enumeration only defines the desired matching semantics. The
        actual MongoDB query construction is performed by the repository.
    """

    CHECKALL = auto()
    """Require that a patient possesses all specified medical conditions."""

    CHECKANY = auto()
    """Require that a patient possesses at least one specified medical condition."""


class ConditionGetAllArgs(BaseModel):
    """
    @brief Encapsulates medical condition filtering arguments.

    @details
    Represents the collection of arguments used when querying patients based
    on their recorded medical conditions.

    The model groups both the medical conditions themselves and the desired
    matching strategy into a single validated object, allowing repository
    methods to accept a strongly typed parameter instead of multiple loosely
    related arguments.

    Validation ensures that at least one medical condition is supplied,
    preventing construction of meaningless database queries.
    """

    conditions: set[MedicalCondition] = Field(
        ...,
        serialization_alias='conditions',
        validation_alias='conditions',
        description=(
            'The collection of medical conditions used to filter patients. '
            'Depending on the specified matching strategy, patients must '
            'possess either all or at least one of these conditions.'
        )
    )

    checktype: ConditionGetAllArgsCheckType = Field(
        default=ConditionGetAllArgsCheckType.CHECKALL,
        serialization_alias='checkType',
        validation_alias='checkType',
        description=(
            'Specifies how the supplied medical conditions should be matched '
            'against each patient record during query execution.'
        )
    )

    @field_validator('conditions')
    @classmethod
    def validate_conditions(cls, v):
        """
        @brief Validates the supplied set of medical conditions.

        @details
        Ensures that the caller provides at least one medical condition.
        Performing this validation during model construction prevents the
        repository from executing queries with an empty condition set, which
        would not represent a meaningful filter.

        @param v
            The set of medical conditions supplied by the caller.

        @return
            The validated set of medical conditions.

        @throws ValueError
            If the supplied set of medical conditions is empty.
        """
        if len(v) == 0:
            raise ValueError(
                'For list of conditions given in repositories.patient.ConditionGetAllArgs, '
                'there are no values, i.e. the list is empty.'
            )

        return v


class ABHAKYCGetAllArgs(BaseModel):
    """
    @brief Encapsulates ABHA KYC filtering arguments.

    @details
    Represents the optional filtering criteria used when querying patients
    based on their ABHA KYC information.

    Every field is optional. Only fields explicitly provided by the caller
    are translated into MongoDB query predicates, allowing repository
    methods to construct queries ranging from broad searches to highly
    specific filters.
    """

    abha_status: ABHAStatus | None = Field(
        default=None,
        serialization_alias='abhaStatus',
        validation_alias='abhaStatus',
        description=(
            'Filters patients by their current ABHA KYC verification status. '
            'If omitted, patients are returned regardless of their ABHA '
            'verification state.'
        )
    )

    has_middle_name: bool | None = Field(
        default=None,
        serialization_alias='hasMiddleName',
        validation_alias='hasMiddleName',
        description=(
            'Filters patients based on whether a middle name is present in '
            'their recorded personal information.'
        )
    )

    has_last_name: bool | None = Field(
        default=None,
        serialization_alias='hasLastName',
        validation_alias='hasLastName',
        description=(
            'Filters patients based on whether a last name is present in '
            'their recorded personal information.'
        )
    )

    gender: Gender | None = Field(
        default=None,
        serialization_alias='gender',
        validation_alias='gender',
        description=(
            'Filters patients by their recorded gender.'
        )
    )


# ── Query Result Models ───────────────────────────────────────────────────────

class GetFieldsResult(BaseModel):
    """
    @brief Represents a partially populated patient record.

    @details
    Defines the result model returned by PatientRepository.getfields(),
    allowing callers to retrieve only a selected subset of patient
    information instead of an entire Patient object.

    Since MongoDB field projections may include any combination of document
    fields, every attribute except the patient identifier is optional. This
    model therefore represents a validated partial patient document rather
    than a complete patient record.

    @note
        This model is intended exclusively for projected query results and
        should not be used when a complete Patient object is required.
    """

    model_config = ConfigDict(populate_by_name=True)

    pid: str = Field(
        ...,
        serialization_alias='patientID',
        validation_alias='patientID',
        description=(
            'The unique identifier assigned to the patient.'
        )
    )

    name: str | None = Field(
        serialization_alias='patientName',
        validation_alias='patientName',
        default=None,
        description=(
            'The patient\'s full name.'
        )
    )

    mobile_number: str | None = Field(
        default=None,
        serialization_alias='mobileNumber',
        validation_alias='mobileNumber',
        description=(
            'The patient\'s registered mobile phone number.'
        )
    )

    date_of_birth: datetime | None = Field(
        default=None,
        serialization_alias='dob',
        validation_alias='dob',
        description=(
            'The patient\'s date of birth.'
        )
    )

    conditions: list[MedicalCondition] | None = Field(
        default=None,
        serialization_alias='medicalConditions',
        validation_alias='medicalConditions',
        description=(
            'The list of medical conditions currently associated with the '
            'patient.'
        )
    )

    is_active: bool | None = Field(
        default=None,
        serialization_alias='isActive',
        validation_alias='isActive',
        description=(
            'Indicates whether the patient is currently marked as an active '
            'patient within the hospital system.'
        )
    )

    abha_kyc: ABHAKYC | None = Field(
        default=None,
        serialization_alias='abhaKYC',
        validation_alias='abhaKYC',
        description=(
            'The patient\'s ABHA Know Your Customer (KYC) information, '
            'including verification status and associated details.'
        )
    )

    created_on: datetime | None = Field(
        default=None,
        serialization_alias='createdOn',
        validation_alias='createdOn',
        description=(
            'The date and time at which the patient record was originally '
            'created.'
        )
    )

# ── Update Argument Models ────────────────────────────────────────────────────

class ConditionUpdateArgsUpdateType(StrEnum):
    """
    @brief Specifies how a patient's medical conditions should be updated.

    @details
    Defines the operation performed on a patient's existing collection of
    medical conditions during an update operation.

    Depending on the selected update type, the repository will append new
    conditions, remove existing ones, or replace the entire collection with
    the supplied set of conditions.

    @note
        This enumeration only specifies the desired update behaviour. The
        corresponding MongoDB update operations are constructed by the
        repository.
    """

    APPEND = auto()
    """Append the supplied medical conditions to the existing collection."""

    REMOVE = auto()
    """Remove the supplied medical conditions from the existing collection."""

    SET = auto()
    """Replace the existing collection of medical conditions with the supplied set."""


class ConditionUpdateArgs(BaseModel):
    """
    @brief Encapsulates medical condition update arguments.

    @details
    Represents the information required to modify a patient's recorded
    medical conditions.

    The model combines the collection of medical conditions with the desired
    update strategy, allowing repository methods to perform additions,
    removals, or complete replacements using a single validated object.
    """

    conditions: set[MedicalCondition] = Field(
        ...,
        serialization_alias='medicalConditions',
        validation_alias='medicalConditions',
        description=(
            'The collection of medical conditions involved in the update '
            'operation. The interpretation of this collection depends on '
            'the selected update type.'
        )
    )

    updatetype: ConditionUpdateArgsUpdateType = Field(
        default=ConditionUpdateArgsUpdateType.APPEND,
        serialization_alias='updateType',
        validation_alias='updateType',
        description=(
            'Specifies how the supplied medical conditions should be applied '
            'to the patient record.'
        )
    )


class ABHAKYCUpdateArgs(BaseModel):
    """
    @brief Encapsulates updates to a patient's ABHA KYC information.

    @details
    Represents the subset of ABHA KYC information that should be modified
    during a patient update operation.

    Every field is optional. Only fields explicitly provided by the caller
    are considered for modification, allowing partial updates without
    requiring the complete ABHA KYC record.

    Boolean "set" flags are used for nullable fields where distinguishing
    between "leave unchanged" and "explicitly clear the value" is necessary.
    """

    abha_number: str | None = Field(
        default=None,
        serialization_alias='abhaNumber',
        validation_alias='abhaNumber',
        description=(
            'The patient\'s ABHA number.'
        )
    )

    abha_address: str | None = Field(
        default=None,
        serialization_alias='abhaAddress',
        validation_alias='abhaAddress',
        description=(
            'The patient\'s ABHA address.'
        )
    )

    abha_status: ABHAStatus | None = Field(
        default=None,
        serialization_alias='abhaStatus',
        validation_alias='abhaStatus',
        description=(
            'The patient\'s current ABHA KYC verification status.'
        )
    )

    first_name: str | None = Field(
        default=None,
        serialization_alias='firstName',
        validation_alias='firstName',
        description=(
            'The patient\'s first name as recorded in the ABHA system.'
        )
    )

    set_middle_name: bool = Field(
        default=False,
        serialization_alias='setMiddleName',
        validation_alias='setMiddleName',
        description=(
            'Indicates whether the middle name field should be updated. '
            'This allows the middle name to be explicitly cleared by '
            'providing a null value.'
        )
    )

    middle_name: str | None = Field(
        default=None,
        serialization_alias='middleName',
        validation_alias='middleName',
        description=(
            'The patient\'s middle name as recorded in the ABHA system.'
        )
    )

    set_last_name: bool = Field(
        default=False,
        serialization_alias='setLastName',
        validation_alias='setLastName',
        description=(
            'Indicates whether the last name field should be updated. '
            'This allows the last name to be explicitly cleared by '
            'providing a null value.'
        )
    )

    last_name: str | None = Field(
        default=None,
        serialization_alias='lastName',
        validation_alias='lastName',
        description=(
            'The patient\'s last name as recorded in the ABHA system.'
        )
    )

    date_of_birth: datetime | None = Field(
        default=None,
        serialization_alias='dob',
        validation_alias='dob',
        description=(
            'The patient\'s date of birth.'
        )
    )

    gender: Gender | None = Field(
        default=None,
        serialization_alias='gender',
        validation_alias='gender',
        description=(
            'The patient\'s recorded gender.'
        )
    )

    mobile_number: str | None = Field(
        default=None,
        serialization_alias='mobileNumber',
        validation_alias='mobileNumber',
        description=(
            'The mobile phone number associated with the patient\'s ABHA '
            'record.'
        )
    )

    set_address: bool = Field(
        default=False,
        serialization_alias='setAddress',
        validation_alias='setAddress',
        description=(
            'Indicates whether the address fields should be updated. '
            'This allows an existing address to be explicitly removed by '
            'providing null values.'
        )
    )

    address: str | None = Field(
        default=None,
        serialization_alias='address',
        validation_alias='address',
        description=(
            'The patient\'s street address.'
        )
    )

    district: str | None = Field(
        default=None,
        serialization_alias='district',
        validation_alias='district',
        description=(
            'The district corresponding to the patient\'s address.'
        )
    )

    state: str | None = Field(
        default=None,
        serialization_alias='state',
        validation_alias='state',
        description=(
            'The state corresponding to the patient\'s address.'
        )
    )

    pincode: str | None = Field(
        default=None,
        serialization_alias='pinCode',
        validation_alias='pinCode',
        description=(
            'The postal PIN code corresponding to the patient\'s address.'
        )
    )

    @field_validator('abha_number')
    @classmethod
    def validate_abha_number(cls, v):
        """
        @brief Validates the supplied ABHA number.

        @param v
            The ABHA number supplied by the caller.

        @return
            The validated ABHA number.
        """
        return validator.validate_abha_number(v) if v is not None else None

    @field_validator('abha_address')
    @classmethod
    def validate_abha_address(cls, v):
        """
        @brief Validates the supplied ABHA address.

        @param v
            The ABHA address supplied by the caller.

        @return
            The validated ABHA address.
        """
        return validator.validate_abha_address(v) if v is not None else None

    @field_validator('first_name', 'middle_name', 'last_name')
    @classmethod
    def validate_first_name(cls, v):
        """
        @brief Validates a patient's name component.

        @details
        Validates the supplied first name, middle name, or last name using
        the application's shared name validation logic.

        @param v
            The name component supplied by the caller.

        @return
            The validated name component.
        """
        return validator.validate_name(v) if v is not None else None

    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v):
        """
        @brief Validates the supplied date of birth.

        @param v
            The date of birth supplied by the caller.

        @return
            The validated date of birth.
        """
        return validator.validate_date_of_birth(v) if v is not None else None

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls, v):
        """
        @brief Validates the supplied mobile number.

        @param v
            The mobile number supplied by the caller.

        @return
            The validated mobile number.
        """
        return validator.validate_mobile_number(v) if v is not None else None

    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        """
        @brief Validates the supplied postal PIN code.

        @param v
            The postal PIN code supplied by the caller.

        @return
            The validated postal PIN code.
        """
        return validator.validate_pincode(v) if v is not None else None


class UpdateArgs(BaseModel):
    """
    @brief Encapsulates patient update arguments.

    @details
    Represents the collection of fields that may be modified during a patient
    update operation.

    Every field is optional, allowing callers to perform partial updates
    without supplying a complete Patient object. Fields omitted by the caller
    are left unchanged by the repository.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(
        default=None,
        serialization_alias='patientName',
        validation_alias='patientName',
        description=(
            'The patient\'s updated full name.'
        )
    )

    mobile_number: str | None = Field(
        default=None,
        serialization_alias='mobileNumber',
        validation_alias='mobileNumber',
        description=(
            'The patient\'s updated mobile phone number.'
        )
    )

    date_of_birth: datetime | None = Field(
        default=None,
        serialization_alias='dob',
        validation_alias='dob',
        description=(
            'The patient\'s updated date of birth.'
        )
    )

    conditions: ConditionUpdateArgs | None = Field(
        default=None,
        serialization_alias='medicalConditions',
        validation_alias='medicalConditions',
        description=(
            'Instructions describing how the patient\'s medical conditions '
            'should be updated.'
        )
    )

    is_active: bool | None = Field(
        default=None,
        serialization_alias='isActive',
        validation_alias='isActive',
        description=(
            'Indicates whether the patient should be marked as active.'
        )
    )

    abha_kyc: ABHAKYCUpdateArgs | None = Field(
        default=None,
        serialization_alias='abhaKYC',
        validation_alias='abhaKYC',
        description=(
            'The subset of ABHA KYC information to be updated.'
        )
    )

    @field_validator('name')
    @classmethod
    def validate_patient_name(cls, v):
        """
        @brief Validates the supplied patient name.

        @param v
            The patient name supplied by the caller.

        @return
            The validated patient name.
        """
        return validator.validate_name(v) if v is not None else None

    @model_validator(mode='after')
    def validate_model(self) -> 'UpdateArgs':
        """
        @brief Performs model-level validation.

        @details
        Invoked after all field-level validation has completed. This validator
        provides a central location for enforcing validation rules involving
        multiple fields simultaneously.

        @return
            The validated UpdateArgs model instance.
        """
        # TODO Validation
        return self

        
# ── Patient Repository ────────────────────────────────────────────────────────

class PatientRepository:
    """
    @brief Repository responsible for managing patient records within MongoDB.

    @details
    Encapsulates all database operations involving Patient objects, including
    record creation, retrieval, modification, deletion, and querying.

    This repository serves as the application's data access layer for patient
    information, isolating MongoDB-specific implementation details from higher
    application layers such as managers and API routers. Callers interact with
    strongly typed repository methods rather than constructing MongoDB queries
    directly.

    In addition to performing CRUD operations, the repository is responsible
    for:

      - Initializing the indexes required to enforce data integrity and
        improve query performance.

      - Translating MongoDB driver exceptions into VitaSync-specific database
        exceptions.

      - Constructing MongoDB query and update documents from validated
        repository argument models.

      - Converting MongoDB documents into validated Patient model instances
        before returning them to higher application layers.

    @note
        Repository initialization must be performed by calling initialize()
        before any CRUD operations are executed.
    """

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        """
        @brief Initializes the patient repository.

        @details
        Stores a reference to the MongoDB collection containing patient
        records and prepares the repository for subsequent initialization.

        Construction of the repository does not perform any database
        operations. Index creation is deferred until initialize() is invoked,
        allowing application startup to explicitly control repository
        initialization.

        @param collection
            The MongoDB collection containing the application\'s patient
            records.
        """

        # MongoDB collection containing all patient documents.
        self._collection = collection

        # Indicates whether the repository has completed initialization.
        self._initialized: bool = False

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """
        @brief Returns the MongoDB collection managed by the repository.

        @details
        Provides access to the underlying MongoDB collection used for all
        patient-related database operations.

        This property primarily exists for internal use and should generally
        not be accessed directly by higher application layers.

        @return
            The MongoDB collection storing patient records.
        """
        return self._collection

    @property
    def is_initialized(self) -> bool:
        """
        @brief Indicates whether the repository has been initialized.

        @details
        Returns whether initialize() has completed successfully. Repository
        initialization creates the indexes relied upon for uniqueness
        constraints and efficient query execution.

        @return
            True if repository initialization has completed successfully;
            otherwise False.
        """
        return self._initialized

    # ── Initialization ────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """
        @brief Initializes the patient repository.

        @details
        Creates all MongoDB indexes required by the repository before it is
        used by the application.

        The created indexes enforce uniqueness constraints on patient
        identifiers and other unique patient attributes while improving the
        performance of commonly executed queries.

        Sparse indexes are used for optional ABHA-related fields so that
        uniqueness is enforced only for documents containing those fields.

        Upon successful completion, the repository is marked as initialized
        and becomes ready to service CRUD operations.

        @throws VitaSyncDatabaseExecutionError
            If an error occurs while creating one or more MongoDB indexes.
        """
        try:
            # Create patient identifier index.
            await self._collection.create_index(
                'pid',
                unique=True
            )

            # Create mobile number indexes.
            await self._collection.create_index(
                'mobile_number',
                unique=True
            )
            
            await self._collection.create_index(
                'abha_kyc.demographic_data.mobile_number',
                unique=True,
                sparse=True
            )

            # Create ABHA number index.
            await self._collection.create_index(
                'abha_kyc.abha_number',
                unique=True,
                sparse=True
            )

            # Create ABHA address index.
            await self._collection.create_index(
                'abha_kyc.abha_address',
                unique=True,
                sparse=True
            )

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

        # Mark repository initialization as complete.
        self._initialized = True

        # ── CRUD Operations ────────────────────────────────────────────────────────

    async def create(
        self,
        patient: Patient
    ) -> None:
        """
        @brief Creates a new patient record.

        @details
        Inserts the supplied Patient object into the MongoDB collection after
        converting it into its corresponding MongoDB document representation.

        Before attempting the insertion, the repository verifies that it has
        been successfully initialized. Any MongoDB driver exceptions are
        translated into VitaSync-specific database exceptions before being
        propagated to higher application layers.

        @param patient
            The patient record to be inserted into the database.

        @throws VitaSyncDatabaseDisconnectedError
            If the repository has not been initialized.

        @throws VitaSyncDuplicateEntryError
            If a patient record already exists with one or more unique
            attributes matching the supplied patient.

        @throws VitaSyncDatabaseExecutionError
            If an unexpected database error occurs while inserting the
            patient record.
        """
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            # Insert the patient record into the MongoDB collection.
            await self._collection.insert_one(
                to_mongo_dict(patient)
            )

        except DuplicateKeyError as exc:
            raise VitaSyncDuplicateEntryError('', exc) from exc # TODO Field

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def delete(
        self,
        pid: str
    ) -> None:
        """
        @brief Deletes an existing patient record.

        @details
        Deletes the patient record corresponding to the supplied patient
        identifier.

        Before attempting the deletion, the repository verifies that it has
        been successfully initialized. If no matching patient record exists,
        a VitaSyncAbsentEntryError is raised. Any MongoDB driver exceptions
        are translated into VitaSync-specific database exceptions before
        being propagated to higher application layers.

        @param pid
            The unique identifier of the patient to be deleted.

        @throws VitaSyncDatabaseDisconnectedError
            If the repository has not been initialized.

        @throws VitaSyncAbsentEntryError
            If no patient exists with the supplied patient identifier.

        @throws VitaSyncDatabaseExecutionError
            If an unexpected database error occurs while deleting the
            patient record.
        """
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            PatientID.validate(pid)

        except ValueError as exc:
            raise VitaSyncInvalidInputsError(
                ['PatientRepository::delete::pid'],
                'PatientID does not fit the format expected.'
            ) from exc

        try:
            # Delete the patient record matching the supplied patient identifier.
            response = await self._collection.delete_one(
                {
                    'pid': pid
                }
            )

            # Ensure that a matching patient record was found.
            if response.deleted_count == 0:
                raise VitaSyncNotFoundError('Patient', pid)

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    async def update(
        self,
        pid: str,
        updateargs: UpdateArgs
    ) -> None:
        """
        @brief Updates an existing patient record.

        @details
        Applies one or more modifications to the patient identified by the
        supplied patient identifier.

        The supplied UpdateArgs object represents a partial update, meaning
        that only the fields explicitly provided by the caller are modified.
        Fields omitted from the update request remain unchanged.

        The repository dynamically constructs the MongoDB update document
        based on the supplied update arguments, ensuring that only the
        requested modifications are sent to the database.

        Before performing the update, the repository verifies that it has
        been successfully initialized. MongoDB driver exceptions are
        translated into VitaSync-specific database exceptions before being
        propagated to higher application layers.

        @param pid
            The unique identifier of the patient to be updated.

        @param updateargs
            The collection of fields describing the requested modifications.

        @throws VitaSyncDatabaseDisconnectedError
            If the repository has not been initialized.

        @throws VitaSyncInvalidInputsError
            If no update fields have been supplied.

        @throws VitaSyncAbsentEntryError
            If no patient exists with the supplied patient identifier.

        @throws VitaSyncDatabaseExecutionError
            If an unexpected database error occurs while updating the
            patient record.
        """

        # TODO Validation

        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        # Construct the base MongoDB '$set' operation containing all simple
        # patient attributes that have been supplied by the caller.
        updater = {
            '$set': {
                **({'name': updateargs.name} if updateargs.name else {}),
                **({'mobile_number': updateargs.mobile_number} if updateargs.mobile_number else {}),
                **({'date_of_birth': updateargs.date_of_birth} if updateargs.date_of_birth else {}),
                **({'is_active': updateargs.is_active} if updateargs.is_active is not None else {})
            }
        }

        # Apply updates to the patient\'s medical conditions, if requested.
        if updateargs.conditions is not None:
            ua = updateargs.conditions
            conditions_list = list(ua.conditions)

            # Select the appropriate MongoDB update operator based on the
            # requested condition update strategy.
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

        # Apply updates to the patient\'s ABHA KYC information, if requested.
        if updateargs.abha_kyc is not None:
            ua = updateargs.abha_kyc

            # Merge all supplied ABHA KYC fields into the existing '$set'
            # operation. Only explicitly supplied fields are included.
            updater['$set'] |= {
                # ABHA KYC information.
                **({'abha_kyc.abha_number': ua.abha_number} if ua.abha_number else {}),
                **({'abha_kyc.abha_address': ua.abha_address} if ua.abha_address else {}),
                **({'abha_kyc.abha_status': ua.abha_status.value} if ua.abha_status is not None else {}),

                # Demographic information.
                **({'abha_kyc.demographic_data.first_name': ua.first_name} if ua.first_name else {}),
                **({'abha_kyc.demographic_data.middle_name': ua.middle_name} if ua.set_middle_name else {}),
                **({'abha_kyc.demographic_data.last_name': ua.last_name} if ua.set_last_name else {}),
                **({'abha_kyc.demographic_data.date_of_birth': ua.date_of_birth} if ua.date_of_birth is not None else {}),
                **({'abha_kyc.demographic_data.gender': ua.gender.value} if ua.gender is not None else {}),
                **({'abha_kyc.demographic_data.mobile_number': ua.mobile_number} if ua.mobile_number else {}),

                # Structured address information.
                **({'abha_kyc.structural_address.address': ua.address} if ua.set_address else {}),
                **({'abha_kyc.structural_address.district': ua.district} if ua.district else {}),
                **({'abha_kyc.structural_address.state': ua.state} if ua.state else {}),
                **({'abha_kyc.structural_address.pincode': ua.pincode} if ua.pincode else {})
            }

        # Remove any MongoDB update operators that do not contain fields.
        updater = {k: v for k, v in updater.items() if v}

        # Reject update requests that do not modify any fields.
        if not updater:
            raise VitaSyncInvalidInputsError(
                ['PatientManager::update::updateargs'],
                'UpdateArgs has all None fields, which is invalid.'
            )

        try:
            # Apply the constructed update document to the matching patient.
            response = await self._collection.update_one(
                {
                    'pid': pid
                },
                updater
            )

            # Ensure that a matching patient record exists.
            if response.matched_count == 0:
                raise VitaSyncNotFoundError(
                    'Patient',
                    pid
                )

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

        # ── Retrieval Operations ───────────────────────────────────────────────────

    async def get(
        self,
        pid: str
    ) -> Patient | None:
        """
        @brief Retrieves a patient by their unique identifier.

        @details
        Searches the patient collection for a record matching the supplied
        patient identifier.

        If a matching document is found, it is converted into a validated
        Patient model before being returned. If no matching patient exists,
        None is returned.

        Before performing the lookup, the repository verifies that it has
        been successfully initialized.

        @param pid
            The unique identifier of the patient to retrieve.

        @return
            A validated Patient object if a matching record exists;
            otherwise None.

        @throws VitaSyncDatabaseDisconnectedError
            If the repository has not been initialized.

        @throws VitaSyncDataValidationError
            If the retrieved MongoDB document cannot be converted into a
            valid Patient model.

        @throws VitaSyncDatabaseExecutionError
            If an unexpected database error occurs while querying the
            database.
        """
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            PatientID.validate(pid)

        except ValueError as exc:
            raise VitaSyncInvalidInputsError(
                [
                    'PatientRepository::get::pid'
                ],
                'PatientID does not fit the format expected.'
            )

        try:
            # Retrieve the patient document matching the supplied identifier.
            response = await self._collection.find_one(
                {
                    'pid': pid
                }
            )

            try:
                # Convert the MongoDB document into a validated Patient model.
                return Patient(**response) if response is not None else None

            except ValidationError as exc:
                raise VitaSyncValidationError(exc) from exc

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

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
        """
        @brief Retrieves multiple patient records.

        @details
        Returns a collection of patients matching the supplied filtering
        criteria.

        The query is constructed dynamically so that only filters explicitly
        provided by the caller are included. Results are ordered by patient
        name and patient identifier before pagination is applied.

        Pagination is performed using MongoDB's skip and limit operations.

        @param size
            The maximum number of patient records to return.

        @param offset
            The number of matching records to skip before returning results.

        @param name_search
            Performs a case-insensitive prefix search on patients'
            names.

        @param conditions
            Filters patients by their recorded medical conditions.

        @param is_active
            Filters patients according to their active status.

        @param age
            Filters patients by age.

        @param abha_kyc_exists
            Indicates whether only patients with or without ABHA KYC
            information should be returned.

        @param abha_kyc
            Additional filters applied to patients' ABHA KYC information.

        @return
            A list containing all matching Patient objects.

        @throws VitaSyncDatabaseDisconnectedError
            If the repository has not been initialized.

        @throws VitaSyncInvalidInputsError
            If one or more supplied filter values are invalid.

        @throws VitaSyncDataValidationError
            If one or more retrieved MongoDB documents cannot be converted
            into valid Patient models.

        @throws VitaSyncDatabaseExecutionError
            If an unexpected database error occurs while querying the
            database.
        """
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        # Ensure pagination parameters are non-negative.
        if size < 0:
            raise VitaSyncInvalidInputsError(
                ['PatientRepository::getall::size'],
                'Size of data requested must be non-negative. Set it to zero for no pagination (default) or a positive integer for pagination.'
            )

        if offset < 0:
            raise VitaSyncInvalidInputsError(
                ['PatientRepository::getall::offset'],
                'Offset of data requested must be non-negative. Set it to zero for no pagination offset (default) or a positive integer for pagination offset.'
            )

        # Construct the MongoDB query document.
        query = {}

        # Filter by active status.
        if is_active is not None:
            query['is_active'] = is_active

        # Filter by patient age.
        if age is not None:
            date_range = age_to_date_range(age)

            if date_range is None:  # age <= 0
                raise VitaSyncInvalidInputsError(
                    ['PatientRepository::getall::age'],
                    'Age of a patient must be greater than zero, given age is negative.'
                )

            # Convert the calculated date range into datetime boundaries.
            to_datetime_range = (
                date_to_datetime_range(date_range[0]),
                date_to_datetime_range(date_range[1])
            )

            query['date_of_birth'] = {
                '$lte': to_datetime_range[1][1],
                '$gte': to_datetime_range[0][0]
            }

        # Filter based on whether ABHA KYC information exists.
        if abha_kyc_exists is not None:
            query['abha_kyc'] = abha_kyc_exists

            # Ignore detailed ABHA filters when searching for patients
            # without ABHA KYC information.
            if not abha_kyc_exists and abha_kyc is not None:
                abha_kyc = None

        # Perform a case-insensitive prefix search on patient names.
        if name_search:
            query['name'] = {
                '$regex': f'^{re.escape(name_search)}',
                '$options': 'i'
            }

        # Apply ABHA KYC-specific filtering.
        if abha_kyc is not None:
            if abha_kyc.abha_status:
                query['abha_kyc.abha_status'] = abha_kyc.abha_status

            if abha_kyc.has_middle_name is not None:
                query['abha_kyc.demographic_data.middle_name'] = {
                    '$ne': None
                } if abha_kyc.has_middle_name else None

            if abha_kyc.has_last_name is not None:
                query['abha_kyc.demographic_data.last_name'] = {
                    '$ne': None
                } if abha_kyc.has_last_name else None

            if abha_kyc.gender is not None:
                query['abha_kyc.demographic_data.gender'] = abha_kyc.gender.value

        # Filter by medical conditions.
        if conditions is not None:
            operator = (
                '$all'
                if conditions.checktype == ConditionGetAllArgsCheckType.CHECKALL
                else '$in'
            )

            query['conditions'] = {
                operator: conditions.conditions
            }

        try:
            # Execute the query, apply sorting, and paginate the results.
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
            ).to_list(length=None)  # TODO figure out if you need some forced pagination to avoid massive list creation

            try:
                # Convert every MongoDB document into a validated Patient model.
                return [
                    Patient(**field) for field in response
                ]

            except ValidationError as exc:
                raise VitaSyncValidationError(exc) from exc

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

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
        """
        @brief Retrieves selected fields from a patient record.

        @details
        Retrieves the patient record corresponding to the supplied patient
        identifier while returning only the fields explicitly requested by
        the caller.

        Instead of returning a complete Patient object, this method performs
        a MongoDB field projection so that only the selected attributes are
        fetched from the database. This reduces unnecessary data transfer
        when only a subset of patient information is required.

        The retrieved document is converted into a validated
        GetFieldsResult model before being returned. If no matching patient
        exists, None is returned.

        @param pid
            The unique identifier of the patient whose information should be
            retrieved.

        @param name
            Indicates whether the patient's name should be included in the
            returned result.

        @param mobile_number
            Indicates whether the patient's mobile number should be included
            in the returned result.

        @param date_of_birth
            Indicates whether the patient's date of birth should be included
            in the returned result.

        @param conditions
            Indicates whether the patient's recorded medical conditions
            should be included in the returned result.

        @param is_active
            Indicates whether the patient's active status should be included
            in the returned result.

        @param abha_kyc
            Indicates whether the patient's ABHA KYC information should be
            included in the returned result.

        @param created_on
            Indicates whether the timestamp recording when the patient
            record was created should be included in the returned result.

        @return
            A validated GetFieldsResult object containing only the requested
            fields if a matching patient exists; otherwise None.

        @throws VitaSyncDatabaseDisconnectedError
            If the repository has not been initialized.

        @throws VitaSyncDataValidationError
            If the retrieved MongoDB document cannot be converted into a
            valid GetFieldsResult model.

        @throws VitaSyncDatabaseExecutionError
            If an unexpected database error occurs while retrieving the
            patient record.
        """
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            PatientID.validate(pid)

        except ValueError as exc:
            raise VitaSyncInvalidInputsError(
                ['PatientRepository::getfields::pid'],
                'PatientID does not fit the format expected.'
            )

        try:
            # Retrieve only the requested fields from the patient record.
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
                # Convert the projected document into the result model.
                return GetFieldsResult(**response) if response is not None else None

            except ValidationError as exc:
                raise VitaSyncValidationError(exc) from exc

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc


    async def getpid(
        self,
        mobile_number: str | None = None,
        abha_number: str | None = None,
        abha_address: str | None = None,
        abha_mobile_number: str | None = None
    ) -> str | None:
        """
        @brief Retrieves a patient's identifier using alternate identifiers.

        @details
        Searches for a patient using one or more alternate identifying
        attributes and returns the corresponding patient identifier.

        Any combination of the supported identifiers may be supplied. All
        supplied identifiers are combined into the MongoDB query.

        @return
            The matching patient identifier if a patient is found;
            otherwise None.

        @throws VitaSyncDatabaseDisconnectedError

        @throws VitaSyncInvalidInputsError
            If no identifying information has been supplied.

        @throws VitaSyncDatabaseExecutionError
        """
        if not self._initialized:
            raise VitaSyncDatabaseDisconnectedError()

        # TODO Validators

        # Ensure that at least one identifier has been supplied.
        if not (
            any(
                [
                    mobile_number,
                    abha_number,
                    abha_address,
                    abha_mobile_number
                ]
            )
        ):
            raise VitaSyncInvalidInputsError(
                [
                    'PatientRepository::getpid::mobile_number',
                    'PatientRepository::getpid::abha_number',
                    'PatientRepository::getpid::abha_address',
                    'PatientRepository::getpid::abha_mobile_number'
                ],
                (
                    'Atleast one of the parameters is required to be not None.'
                    'All given parameters are None.'
                )
            )

        try:
            # Search for the patient using the supplied identifiers.
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

            # Return the matching patient identifier, if one exists.
            return response['pid'] if response is not None else None

        except OperationFailure as exc:
            raise VitaSyncDatabaseOperationError(exc) from exc

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc
