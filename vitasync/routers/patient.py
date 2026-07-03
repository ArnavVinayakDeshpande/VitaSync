"""
@file patient_router.py
@brief FastAPI router defining all HTTP endpoints for patient-related operations.

@details
This router exposes the full patient management API for VitaSync, covering
patient registration, retrieval, search, field projection, PID resolution,
updates, and deletion. All routes delegate business logic to the PatientManager
layer and never interact with the database directly.

All endpoints are prefixed with /patients and grouped under the 'Patients'
tag in the auto-generated Swagger/OpenAPI documentation.

@note Route declaration order is intentional — static path segments (/search,
      /resolve) are declared before dynamic path parameters (/{patientID}) to
      prevent FastAPI from matching literal segments as path parameter values.
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query,
    Body,
    Depends,
    status
)
from pydantic import BaseModel, Field, ConfigDict

import vitasync.managers.patient as PM
from vitasync.managers.patient import PatientManager
from vitasync.models.patient import PatientCreate, MedicalCondition
from vitasync.repositories.patient import (
    ConditionGetAllArgs,
    ABHAKYCGetAllArgs,
    UpdateArgs
)
from vitasync.exceptions.managers import VitaSyncPMDatabaseError, VitaSyncManagersBaseError
from vitasync.exceptions.database import VitaSyncDuplicateEntryError
from vitasync.exceptions.generic import VitaSyncInvalidInputsError


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(
    prefix='/patients',
    tags=['Patients']
)


# ── Request Models ─────────────────────────────────────────────────────────────

class GetAllArgs(BaseModel):
    """
    @brief Request body model for the POST /patients/search endpoint.

    @details
    Encapsulates all filter, pagination, and search parameters for querying
    the patient collection. All fields are optional — an empty body or omitted
    body returns an unfiltered paginated list of patients.

    Supports both camelCase (from frontend JSON) and snake_case (from internal
    Python code) via validation aliases and populate_by_name=True.
    """
    model_config = ConfigDict(populate_by_name=True)

    size: int = Field(
        default=50,
        ge=0,
        validation_alias='size',
        description='Maximum number of patient records to return. 0 returns all records with no limit.'
    )
    offset: int = Field(
        default=0,
        ge=0,
        validation_alias='offset',
        description='Number of records to skip before returning results. Used for pagination.'
    )
    name_search: str | None = Field(
        default=None,
        validation_alias='nameSearch',
        description='Case-insensitive prefix search on patient name. Returns all patients whose name starts with this string.'
    )
    condition_args: ConditionGetAllArgs | None = Field(
        default=None,
        validation_alias='conditionArgs',
        description='Filter patients by medical conditions. Supports CHECKALL (must have all) and CHECKANY (must have at least one) modes.'
    )
    is_active: bool | None = Field(
        default=None,
        validation_alias='isActive',
        description='Filter by patient active status. True returns only active patients, False returns only inactive. Omit to return both.'
    )
    age: int | None = Field(
        default=None,
        ge=1,
        validation_alias='age',
        description='Filter patients by exact age in years. Computes a date-of-birth range from the given age.'
    )
    abha_kyc_exists: bool | None = Field(
        default=None,
        validation_alias='abhaKYCExists',
        description='Filter by whether ABHA KYC is linked. True returns only patients with KYC, False returns only patients without.'
    )
    abha_kyc_args: ABHAKYCGetAllArgs | None = Field(
        default=None,
        validation_alias='abhaKYCArgs',
        description='Filter patients by nested ABHA KYC attributes such as status, gender, and name completeness.'
    )


# ── Dependency ─────────────────────────────────────────────────────────────────

def get_patient_manager() -> PatientManager:
    """
    @brief FastAPI dependency that resolves and validates the PatientManager singleton.

    @details
    Checks that the module-level PatientManager singleton has been initialized
    during application startup via the lifespan context manager. If the manager
    is None (i.e. startup did not complete successfully), raises a 503 Service
    Unavailable rather than a 500, since the server is technically running but
    not ready to serve patient requests.

    This dependency is injected into every route function via FastAPI's
    Depends() mechanism, eliminating the need for repetitive None checks
    inside each route handler.

    @throws HTTPException 503 if PatientManager has not been initialized.

    @return The initialized PatientManager singleton instance.
    """
    if PM.patient_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                'The Patient Manager has not been initialized. '
                'The server may still be starting up or encountered an error '
                'during initialization. Please try again shortly.'
            )
        )
    return PM.patient_manager


# ── Routes — Static Paths ──────────────────────────────────────────────────────

@router.post(
    '/search',
    status_code=status.HTTP_200_OK,
    summary='Search and filter patients',
    description=(
        'Returns a paginated list of patient records matching the given filter criteria. '
        'All fields in the request body are optional — an empty body or omitted body '
        'returns an unfiltered list of patients ordered by name. '
        'Supports filtering by name prefix, age, active status, ABHA KYC presence, '
        'medical conditions (with CHECKALL/CHECKANY semantics), and nested ABHA KYC attributes.'
    ),
    responses={
        200: {'description': 'List of matching patient records returned successfully.'},
        500: {'description': 'Internal database error while executing the search query.'}
    }
)
async def getall(
    search_args: GetAllArgs | None = Body(
        default=None,
        description='Search and filter parameters. All fields optional. Omit body entirely for unfiltered results.'
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Searches the patient collection with optional filters and pagination.

    @details
    Accepts an optional GetAllArgs body. If the body is omitted or None,
    defaults to an unfiltered paginated query using GetAllArgs defaults
    (size=20, offset=0, all filters None). Unpacks the model into keyword
    arguments for PatientManager.getall().

    @param search_args Optional GetAllArgs body containing filter and pagination params.
    @param manager     Injected PatientManager dependency.

    @throws HTTPException 500 on database execution failure.

    @return A JSON array of patient records matching the given criteria,
            serialized with camelCase aliases.
    """
    try:
        args = search_args or GetAllArgs()
        response = await manager.getall(**args.model_dump())
        return [patient.model_dump(by_alias=True) for patient in response]

    except VitaSyncPMDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f'A database error occurred while searching for patients. '
                f'Reason: {str(exc)}'
            )
        ) from exc


@router.get(
    '/resolve',
    status_code=status.HTTP_200_OK,
    summary='Resolve a patient PID from known identifiers',
    description=(
        'Looks up and returns the Patient ID (PID) for a patient identified by one or more '
        'known identifiers: mobile number, ABHA number, ABHA address, or ABHA-linked mobile number. '
        'At least one identifier must be provided. Returns 404 if no patient matches.'
    ),
    responses={
        200: {'description': 'PID resolved and returned successfully.'},
        404: {'description': 'No patient found matching the provided identifiers.'},
        500: {'description': 'Internal database error while resolving the PID.'}
    }
)
async def getpid(
    mobile_number: str | None = Query(
        default=None,
        alias='mobileNumber',
        description="The patient's registered mobile number (e.g. +919876543210 or 09876543210)."
    ),
    abha_number: str | None = Query(
        default=None,
        alias='abhaNumber',
        description="The patient's 14-digit ABHA number in format XX-XXXX-XXXX-XXXX."
    ),
    abha_address: str | None = Query(
        default=None,
        alias='abhaAddress',
        description="The patient's ABHA address ending in @abdm (e.g. priya.sharma@abdm)."
    ),
    abha_mobile_number: str | None = Query(
        default=None,
        alias='abhaMobileNumber',
        description="The mobile number linked to the patient's ABHA account, if different from their registered number."
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Resolves a patient PID from one or more known external identifiers.

    @details
    Queries the patient collection using whichever identifiers are provided.
    All parameters are optional but at least one should be supplied for a
    meaningful query — providing none will likely return None and a 404.

    @param mobile_number      Patient's registered mobile number.
    @param abha_number        Patient's ABHA number in hyphenated format.
    @param abha_address       Patient's ABHA address ending in @abdm.
    @param abha_mobile_number Mobile number linked to the patient's ABHA account.
    @param manager            Injected PatientManager dependency.

    @throws HTTPException 404 if no patient matches the given identifiers.
    @throws HTTPException 500 on database execution failure.

    @return A JSON object containing the resolved pid: {"pid": "PAT-YYMMDD-XXXXXX"}.
    """
    try:
        response = await manager.getpid(
            mobile_number=mobile_number,
            abha_number=abha_number,
            abha_address=abha_address,
            abha_mobile_number=abha_mobile_number
        )

        if response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    'No patient found matching the provided identifiers. '
                    'Verify the mobile number, ABHA number, or ABHA address and try again.'
                )
            )

        return {'patientID': response}

    except VitaSyncPMDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'A database error occurred while resolving the patient PID. Reason: {str(exc)}'
        ) from exc


@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    summary='Register a new patient',
    description=(
        'Creates and persists a new patient record. The Patient ID (PID) is auto-generated '
        'by the server in the format PAT-YYMMDD-XXXXXX and does not need to be supplied. '
        'ABHA KYC is not set at registration time — it is linked asynchronously via the '
        'PATCH /patients/{patientID}/kyc endpoint after ABDM verification. '
        'Returns the full created patient record including the generated PID.'
    ),
    responses={
        201: {'description': 'Patient registered successfully. Returns the full patient record.'},
        409: {'description': 'A patient with this mobile number already exists in the system.'},
        422: {'description': 'Validation error — one or more input fields are invalid.'},
        500: {'description': 'Internal server error during patient registration.'}
    }
)
async def create(
    patient_create: PatientCreate = Body(
        ...,
        description='Patient registration payload. PID and ABHA KYC are not required and will be ignored if provided.'
    ),
    max_retries: int = Query(
        default=5,
        ge=1,
        le=10,
        alias='maxRetries',
        description='Maximum number of PID generation retry attempts on collision. Defaults to 5.'
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Registers a new patient in the VitaSync system.

    @details
    Passes the validated PatientCreate payload to PatientManager.create(),
    which generates a unique PID, constructs the full Patient model,
    runs all model validators, and persists the record to MongoDB.

    PID generation retries automatically on collision up to max_retries times.
    If the mobile number already exists in the system, raises 409 immediately
    without retrying since changing the PID would not resolve a mobile number conflict.

    @param patient_create The validated patient registration payload.
    @param max_retries    Maximum PID generation retry attempts. Defaults to 5.
    @param manager        Injected PatientManager dependency.

    @throws HTTPException 409 if the mobile number already exists.
    @throws HTTPException 500 on unrecoverable database or manager error.

    @return The full created patient record serialized with camelCase aliases.
    """
    try:
        response = await manager.create(
            patient_create=patient_create,
            max_retries=max_retries
        )
        return response.model_dump(by_alias=True)

    except VitaSyncDuplicateEntryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f'A patient with this mobile number or ABHA identifier already exists. '
                f'Use GET /patients/resolve to look up the existing patient PID. '
                f'Reason: {str(exc)}'
            )
        ) from exc

    except VitaSyncManagersBaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An error occurred during patient registration. Reason: {str(exc)}'
        ) from exc


# ── Routes — Dynamic Paths ─────────────────────────────────────────────────────

@router.get(
    '/{patientID}',
    status_code=status.HTTP_200_OK,
    summary='Fetch a patient by PID',
    description=(
        'Retrieves the complete patient record for the given Patient ID (PID). '
        'Returns all fields including ABHA KYC data if linked. '
        'Returns 404 if no patient exists with the given PID.'
    ),
    responses={
        200: {'description': 'Full patient record returned successfully.'},
        404: {'description': 'No patient found with the given PID.'},
        500: {'description': 'Internal database error while fetching the patient record.'}
    }
)
async def get(
    patientID: str = Path(
        ...,
        description='The unique Patient ID in format PAT-YYMMDD-XXXXXX.',
        examples=['PAT-260702-K7M2X9']
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Fetches the full patient record for a given PID.

    @details
    Delegates to PatientManager.get(), which queries the patient collection
    by pid and reconstructs the full Patient Pydantic model from the
    MongoDB document. Returns None if no document matches, which is
    converted to a 404 response.

    @param patientID The unique patient identifier in format PAT-YYMMDD-XXXXXX.
    @param manager   Injected PatientManager dependency.

    @throws HTTPException 404 if no patient exists with the given PID.
    @throws HTTPException 500 on database execution failure.

    @return The full patient record serialized with camelCase aliases.
    """
    try:
        response = await manager.get(pid=patientID)

        if response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No patient found with PID '{patientID}'. "
                    f'Verify the PID and try again, or use GET /patients/resolve '
                    f'to look up a PID from a mobile number or ABHA identifier.'
                )
            )

        return response.model_dump(by_alias=True)

    except VitaSyncPMDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'A database error occurred while fetching patient {patientID}. Reason: {str(exc)}'
        ) from exc


@router.get(
    '/{patientID}/fields',
    status_code=status.HTTP_200_OK,
    summary='Fetch specific fields for a patient',
    description=(
        'Returns a projection of the patient record containing only the requested fields. '
        'Use this endpoint instead of GET /{patientID} when only a subset of patient data '
        'is needed, to reduce response payload size and database read overhead. '
        'At minimum, the patient PID is always returned regardless of which fields are requested.'
    ),
    responses={
        200: {'description': 'Projected patient fields returned successfully.'},
        400: {'description': 'Invalid input — e.g. age parameter is less than or equal to zero.'},
        404: {'description': 'No patient found with the given PID.'},
        500: {'description': 'Internal database error while fetching patient fields.'}
    }
)
async def getfields(
    patientID: str = Path(
        ...,
        description='The unique Patient ID in format PAT-YYMMDD-XXXXXX.',
        examples=['PAT-260702-K7M2X9']
    ),
    name: bool = Query(
        default=False,
        description='Include the patient full name in the response.'
    ),
    mobile_number: bool = Query(
        default=False,
        alias='mobileNumber',
        description='Include the patient registered mobile number in the response.'
    ),
    date_of_birth: bool = Query(
        default=False,
        alias='dateOfBirth',
        description='Include the patient date of birth in the response.'
    ),
    conditions: bool = Query(
        default=False,
        description='Include the patient medical conditions set in the response.'
    ),
    is_active: bool = Query(
        default=False,
        alias='isActive',
        description='Include the patient active/inactive status in the response.'
    ),
    abha_kyc: bool = Query(
        default=False,
        alias='abhaKYC',
        description='Include the full ABHA KYC sub-document in the response if linked.'
    ),
    created_on: bool = Query(
        default=False,
        alias='createdOn',
        description='Include the patient record creation timestamp in the response.'
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Returns a field projection of a patient record.

    @details
    Fetches only the requested fields from the patient document via a MongoDB
    projection query, avoiding the overhead of fetching the full document when
    only a subset of fields is needed. The PID is always included in the response
    regardless of which boolean flags are set.

    @param patientID    The unique patient identifier.
    @param name         Include patient name if True.
    @param mobile_number Include registered mobile number if True.
    @param date_of_birth Include date of birth if True.
    @param conditions   Include medical conditions set if True.
    @param is_active    Include active status if True.
    @param abha_kyc     Include full ABHA KYC sub-document if True.
    @param created_on   Include record creation timestamp if True.
    @param manager      Injected PatientManager dependency.

    @throws HTTPException 400 on invalid input parameters.
    @throws HTTPException 404 if no patient exists with the given PID.
    @throws HTTPException 500 on database execution failure.

    @return A partial patient record containing only the requested fields,
            serialized with camelCase aliases.
    """
    try:
        response = await manager.getfields(
            pid=patientID,
            name=name,
            mobile_number=mobile_number,
            date_of_birth=date_of_birth,
            conditions=conditions,
            is_active=is_active,
            abha_kyc=abha_kyc,
            created_on=created_on
        )

        if response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No patient found with PID '{patientID}'. "
                    f'Verify the PID and try again.'
                )
            )

        return response.model_dump(by_alias=True)

    except VitaSyncInvalidInputsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid input provided to patient field projection query. Reason: {str(exc)}'
        ) from exc

    except VitaSyncPMDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'A database error occurred while fetching fields for patient {patientID}. Reason: {str(exc)}'
        ) from exc


@router.delete(
    '/{patientID}',
    status_code=status.HTTP_200_OK,
    summary='Delete a patient record',
    description=(
        'Permanently removes the patient record with the given PID from the system. '
        'This action is irreversible. Associated visit records are not automatically '
        'deleted and must be handled separately. '
        'Returns 404 if no patient exists with the given PID.'
    ),
    responses={
        200: {'description': 'Patient record deleted successfully.'},
        404: {'description': 'No patient found with the given PID.'},
        500: {'description': 'Internal database error during deletion.'}
    }
)
async def delete(
    patientID: str = Path(
        ...,
        description='The unique Patient ID of the record to permanently delete.',
        examples=['PAT-260702-K7M2X9']
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Permanently deletes a patient record by PID.

    @details
    Delegates to PatientManager.delete(), which removes the patient document
    from the MongoDB collection. Raises 404 if the PID does not match any
    existing document. This operation is irreversible.

    @param patientID The unique patient identifier of the record to delete.
    @param manager   Injected PatientManager dependency.

    @throws HTTPException 404 if no patient exists with the given PID.
    @throws HTTPException 500 on database execution failure.

    @return A JSON object confirming the deletion: {"patientID": "...", "deleted": true}.
    """
    try:
        await manager.delete(patientID)
        return {
            'patientID': patientID,
            'deleted': True
        }

    except VitaSyncPMDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'A database error occurred while deleting patient {patientID}. Reason: {str(exc)}'
        ) from exc

    except VitaSyncInvalidInputsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid input provided to patient deletion. Reason: {str(exc)}'
        ) from exc


@router.patch(
    '/{patientID}',
    status_code=status.HTTP_200_OK,
    summary='Partially update a patient record',
    description=(
        'Performs a partial update on the patient record identified by the given PID. '
        'Only the fields included in the request body are updated — omitted fields '
        'are left unchanged. Supports updating top-level demographic fields '
        '(name, mobile number, date of birth, active status) as well as the '
        'medical conditions set (append, remove, or replace). '
        'ABHA KYC updates are handled separately via PATCH /patients/{patientID}/kyc.'
    ),
    responses={
        200: {'description': 'Patient record updated successfully.'},
        400: {'description': 'Invalid input — e.g. malformed field values.'},
        404: {'description': 'No patient found with the given PID.'},
        500: {'description': 'Internal database error during update.'}
    }
)
async def update(
    patientID: str = Path(
        ...,
        description='The unique Patient ID of the record to update.',
        examples=['PAT-260702-K7M2X9']
    ),
    updateargs: UpdateArgs = Body(
        ...,
        description=(
            'Partial update payload. All fields are optional — include only the fields '
            'to be changed. For conditions, specify the update type (APPEND, REMOVE, or SET) '
            'alongside the conditions set.'
        )
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Partially updates a patient record by PID.

    @details
    Delegates to PatientManager.update(), passing the PID from the path
    and the UpdateArgs payload. The manager constructs a sparse MongoDB
    $set / $addToSet / $pullAll update document from only the non-None
    fields in UpdateArgs, ensuring untouched fields are never overwritten.

    @param patientID  The unique patient identifier of the record to update.
    @param updateargs Partial update payload containing only the fields to change.
    @param manager    Injected PatientManager dependency.

    @throws HTTPException 400 on invalid input field values.
    @throws HTTPException 404 if no patient exists with the given PID.
    @throws HTTPException 500 on database execution failure.

    @return A JSON object confirming the update: {"patientID": "...", "updated": true}.
    """
    try:
        await manager.update(patientID, updateargs)
        return {
            'patientID': patientID,
            'updated': True
        }

    except VitaSyncInvalidInputsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid input provided to patient update. Reason: {str(exc)}'
        ) from exc

    except VitaSyncPMDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'A database error occurred while updating patient {patientID}. Reason: {str(exc)}'
        ) from exc
