"""
@file patient_router.py
@brief FastAPI router defining all HTTP endpoints for patient-related operations.

@details
This router exposes the complete patient management API for VitaSync,
including patient registration, retrieval, searching, field projection,
PID resolution, partial updates, and deletion.

The router is intentionally thin and contains no business logic. Every route
delegates work to the PatientManager layer and is responsible only for:

  - Request validation performed by FastAPI/Pydantic.
  - Dependency injection.
  - Translating VitaSync exceptions into appropriate HTTP responses.
  - Serialising response models for the client.

All endpoints are prefixed with /patients and grouped under the "Patients"
tag in the generated OpenAPI documentation.

Exception Mapping
──────────────────────────────────────────────────────────────────────────────

Manager/Repository Exception                  HTTP Status
──────────────────────────────────────────────────────────────────────────────
VitaSyncNotFoundError                         404 Not Found
VitaSyncInvalidInputsError                    400 Bad Request
VitaSyncDuplicateEntryError                   409 Conflict
VitaSyncDatabaseDisconnectedError             503 Service Unavailable
VitaSyncDatabaseUnreachableError              503 Service Unavailable
VitaSyncDatabaseTimeoutError                  504 Gateway Timeout
VitaSyncDatabaseOperationError                500 Internal Server Error
VitaSyncDatabaseExecutionError                500 Internal Server Error
VitaSyncValidationError                       500 Internal Server Error
VitaSyncIDGenerationError                     500 Internal Server Error
Unhandled VitaSyncError                       500 Internal Server Error

@note Route declaration order is intentional. Static paths such as
      /search and /resolve are declared before dynamic path parameters
      (/{patientID}) so FastAPI does not interpret literal path segments
      as patient identifiers.
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
from vitasync.common.error import *


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(
    prefix='/patients',
    tags=['Patients']
)


# ── Request Models ─────────────────────────────────────────────────────────────

class GetAllArgs(BaseModel):
    """
    @brief Request model for POST /patients/search.

    @details
    Encapsulates every supported search, filtering, and pagination parameter
    accepted by the patient search endpoint.

    Every field is optional. When omitted, the endpoint performs an
    unfiltered paginated query using the default pagination values.

    The model accepts both camelCase and snake_case field names through
    validation aliases while always exposing camelCase fields externally.

    @note Validation constraints are intentionally limited to structural
          validation. Business-rule validation is performed by the manager
          layer and surfaced as VitaSyncInvalidInputsError.
    """

    model_config = ConfigDict(populate_by_name=True)

    size: int = Field(
        default=50,
        ge=0,
        validation_alias='size',
        description=(
            'Maximum number of patient records to return. '
            'A value of 0 disables pagination and returns all matching records.'
        )
    )

    offset: int = Field(
        default=0,
        ge=0,
        validation_alias='offset',
        description='Number of matching records to skip before returning results.'
    )

    name_search: str | None = Field(
        default=None,
        validation_alias='nameSearch',
        description='Case-insensitive prefix search on patient names.'
    )

    condition_args: ConditionGetAllArgs | None = Field(
        default=None,
        validation_alias='conditionArgs',
        description=(
            'Optional medical-condition filtering parameters supporting '
            'CHECKALL and CHECKANY matching semantics.'
        )
    )

    is_active: bool | None = Field(
        default=None,
        validation_alias='isActive',
        description='Filters patients by active or inactive status.'
    )

    age: int | None = Field(
        default=None,
        ge=1,
        validation_alias='age',
        description='Filters patients by exact age in completed years.'
    )

    abha_kyc_exists: bool | None = Field(
        default=None,
        validation_alias='abhaKYCExists',
        description='Filters patients by whether ABHA KYC information exists.'
    )

    abha_kyc_args: ABHAKYCGetAllArgs | None = Field(
        default=None,
        validation_alias='abhaKYCArgs',
        description='Optional filters applied to nested ABHA KYC fields.'
    )


# ── Dependency ─────────────────────────────────────────────────────────────────

def get_patient_manager() -> PatientManager:
    """
    @brief Returns the application's PatientManager singleton.

    @details
    Validates that the PatientManager has been successfully initialised during
    application startup before allowing any route to execute.

    Failure to initialise indicates that the application has not yet completed
    startup or encountered a fatal initialisation error. Since the API itself
    is reachable but cannot service requests, the appropriate response is
    HTTP 503 Service Unavailable.

    @throws HTTPException
            - 503 Service Unavailable if the PatientManager has not been
              initialised.

    @return Initialised PatientManager singleton.
    """
    if PM.patient_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                'The patient management service is currently unavailable '
                'because it has not finished initialising. '
                'Please try again shortly.'
            )
        )

    return PM.patient_manager


# ── Routes — Static Paths ──────────────────────────────────────────────────────

@router.post(
    '/search',
    status_code=status.HTTP_200_OK,
    summary='Search and filter patients',
    description=(
        'Returns a paginated collection of patients matching the supplied '
        'search criteria. Omitting the request body performs an unfiltered '
        'query using the default pagination parameters.'
    ),
    responses={
        200: {'description': 'Matching patient records returned successfully.'},
        400: {'description': 'One or more business-rule validations failed.'},
        503: {'description': 'Database service unavailable.'},
        504: {'description': 'Database operation timed out.'},
        500: {'description': 'Unexpected internal server error.'}
    }
)
async def getall(
    search_args: GetAllArgs | None = Body(
        default=None,
        description=(
            'Optional search and pagination arguments. '
            'When omitted, default search parameters are used.'
        )
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Searches the patient collection.

    @details
    Delegates the search operation entirely to PatientManager.getall(),
    translating VitaSync exceptions into the corresponding HTTP responses.

    @param search_args Optional search, filtering, and pagination arguments.
    @param manager Injected PatientManager dependency.

    @throws HTTPException
            - 400 if business-rule validation fails.
            - 503 if the database is unavailable.
            - 504 if the database operation times out.
            - 500 for any other internal VitaSync failure.

    @return List of matching patients serialised using response aliases.
    """
    try:
        args = search_args or GetAllArgs()
        response = await manager.getall(**args.model_dump())

        return [
            patient.model_dump(by_alias=True)
            for patient in response
        ]

    except VitaSyncInvalidInputsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseDisconnectedError,
        VitaSyncDatabaseUnreachableError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc

    except VitaSyncDatabaseTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseOperationError,
        VitaSyncDatabaseExecutionError,
        VitaSyncValidationError,
        VitaSyncDatabaseError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.get(
    '/resolve',
    status_code=status.HTTP_200_OK,
    summary='Resolve a patient PID from known identifiers',
    description=(
        'Returns the Patient ID corresponding to one or more known patient '
        'identifiers such as a mobile number or ABHA information.'
    ),
    responses={
        200: {'description': 'Patient identifier resolved successfully.'},
        404: {'description': 'No matching patient exists.'},
        503: {'description': 'Database service unavailable.'},
        504: {'description': 'Database operation timed out.'},
        500: {'description': 'Unexpected internal server error.'}
    }
)
async def getpid(
    mobile_number: str | None = Query(
        default=None,
        alias='mobileNumber',
        description="Patient's registered mobile number."
    ),
    abha_number: str | None = Query(
        default=None,
        alias='abhaNumber',
        description="Patient's ABHA number."
    ),
    abha_address: str | None = Query(
        default=None,
        alias='abhaAddress',
        description="Patient's ABHA address."
    ),
    abha_mobile_number: str | None = Query(
        default=None,
        alias='abhaMobileNumber',
        description='Mobile number linked to the patient ABHA account.'
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Resolves a Patient ID using external identifiers.

    @details
    Delegates identifier resolution to PatientManager.getpid(). If no matching
    patient exists, the manager raises VitaSyncNotFoundError which is converted
    into HTTP 404.

    @param mobile_number Registered patient mobile number.
    @param abha_number Patient ABHA number.
    @param abha_address Patient ABHA address.
    @param abha_mobile_number Mobile number linked to the ABHA account.
    @param manager Injected PatientManager dependency.

    @throws HTTPException
            - 404 if no matching patient exists.
            - 503 if the database is unavailable.
            - 504 if the database operation times out.
            - 500 for all remaining internal failures.

    @return JSON object containing the resolved patient identifier.
    """
    try:
        response = await manager.getpid(
            mobile_number=mobile_number,
            abha_number=abha_number,
            abha_address=abha_address,
            abha_mobile_number=abha_mobile_number
        )

        return {
            'patientID': response
        }

    except VitaSyncNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseDisconnectedError,
        VitaSyncDatabaseUnreachableError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc

    except VitaSyncDatabaseTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseOperationError,
        VitaSyncDatabaseExecutionError,
        VitaSyncValidationError,
        VitaSyncDatabaseError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    summary='Register a new patient',
    description=(
        'Registers a new patient in the VitaSync system. '
        'A unique Patient ID (PID) is generated automatically. '
        'ABHA KYC information is not created during registration and must '
        'be linked separately after successful ABDM verification.'
    ),
    responses={
        201: {'description': 'Patient registered successfully.'},
        409: {'description': 'A unique field conflicts with an existing patient.'},
        503: {'description': 'Database service unavailable.'},
        504: {'description': 'Database operation timed out.'},
        500: {'description': 'Unexpected internal server error.'}
    }
)
async def create(
    patient_create: PatientCreate = Body(
        ...,
        description='Validated patient registration payload.'
    ),
    max_retries: int = Query(
        default=5,
        ge=1,
        le=10,
        alias='maxRetries',
        description='Maximum number of PID generation retries.'
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Registers a new patient.

    @details
    Delegates patient creation entirely to PatientManager.create(). The
    manager generates a unique Patient ID, validates the resulting Patient
    model, and persists it to the database.

    Duplicate unique fields are surfaced as HTTP 409, while infrastructure
    failures are translated according to the VitaSync exception hierarchy.

    @param patient_create Validated patient registration payload.
    @param max_retries Maximum PID generation retry attempts.
    @param manager Injected PatientManager dependency.

    @throws HTTPException
            - 409 if a unique constraint is violated.
            - 503 if the database is unavailable.
            - 504 if the database operation times out.
            - 500 for all remaining internal failures.

    @return Newly created patient record.
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
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseDisconnectedError,
        VitaSyncDatabaseUnreachableError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc

    except VitaSyncDatabaseTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncIDGenerationError,
        VitaSyncDatabaseOperationError,
        VitaSyncDatabaseExecutionError,
        VitaSyncValidationError,
        VitaSyncDatabaseError,
        VitaSyncManagerError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


# ── Routes — Dynamic Paths ─────────────────────────────────────────────────────

@router.get(
    '/{patientID}',
    status_code=status.HTTP_200_OK,
    summary='Fetch a patient by PID',
    description=(
        'Returns the complete patient record associated with the supplied '
        'Patient ID.'
    ),
    responses={
        200: {'description': 'Patient returned successfully.'},
        404: {'description': 'Patient not found.'},
        503: {'description': 'Database service unavailable.'},
        504: {'description': 'Database operation timed out.'},
        500: {'description': 'Unexpected internal server error.'}
    }
)
async def get(
    patientID: str = Path(
        ...,
        description='Unique Patient ID.',
        examples=['PAT-260702-K7M2X9']
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Returns a patient by Patient ID.

    @details
    Delegates retrieval to PatientManager.get(). Missing patients are reported
    by the manager using VitaSyncNotFoundError and translated into HTTP 404.

    @param patientID Unique Patient ID.
    @param manager Injected PatientManager dependency.

    @throws HTTPException
            - 404 if the patient does not exist.
            - 503 if the database is unavailable.
            - 504 if the database operation times out.
            - 500 for all remaining internal failures.

    @return Complete patient record.
    """
    try:
        response = await manager.get(pid=patientID)

        if response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Could not find required patient.'
            ) 

        return response.model_dump(by_alias=True) 

    except (
        VitaSyncDatabaseDisconnectedError,
        VitaSyncDatabaseUnreachableError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc

    except VitaSyncDatabaseTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseOperationError,
        VitaSyncDatabaseExecutionError,
        VitaSyncValidationError,
        VitaSyncDatabaseError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.get(
    '/{patientID}/fields',
    status_code=status.HTTP_200_OK,
    summary='Fetch selected patient fields',
    description=(
        'Returns only the requested fields for a patient record using a '
        'database projection.'
    ),
    responses={
        200: {'description': 'Requested fields returned successfully.'},
        400: {'description': 'Business-rule validation failed.'},
        404: {'description': 'Patient not found.'},
        503: {'description': 'Database service unavailable.'},
        504: {'description': 'Database operation timed out.'},
        500: {'description': 'Unexpected internal server error.'}
    }
)
async def getfields(
    patientID: str = Path(
        ...,
        description='Unique Patient ID.',
        examples=['PAT-260702-K7M2X9']
    ),
    name: bool = Query(
        default=False,
        description='Include patient name.'
    ),
    mobile_number: bool = Query(
        default=False,
        alias='mobileNumber',
        description='Include registered mobile number.'
    ),
    date_of_birth: bool = Query(
        default=False,
        alias='dateOfBirth',
        description='Include date of birth.'
    ),
    conditions: bool = Query(
        default=False,
        description='Include medical conditions.'
    ),
    is_active: bool = Query(
        default=False,
        alias='isActive',
        description='Include active status.'
    ),
    abha_kyc: bool = Query(
        default=False,
        alias='abhaKYC',
        description='Include ABHA KYC information.'
    ),
    created_on: bool = Query(
        default=False,
        alias='createdOn',
        description='Include creation timestamp.'
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Returns a projected patient document.

    @details
    Delegates projection to PatientManager.getfields(), allowing the manager
    to determine which database fields should be retrieved.

    @param patientID Unique Patient ID.
    @param name Include patient name.
    @param mobile_number Include registered mobile number.
    @param date_of_birth Include date of birth.
    @param conditions Include medical conditions.
    @param is_active Include active status.
    @param abha_kyc Include ABHA KYC information.
    @param created_on Include creation timestamp.
    @param manager Injected PatientManager dependency.

    @throws HTTPException
            - 400 if business-rule validation fails.
            - 404 if the patient does not exist.
            - 503 if the database is unavailable.
            - 504 if the database operation times out.
            - 500 for all remaining internal failures.

    @return Projected patient document.
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
                detail='Could not find the required patient.'
            )

        return response.model_dump(by_alias=True)

    except VitaSyncInvalidInputsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseDisconnectedError,
        VitaSyncDatabaseUnreachableError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc

    except VitaSyncDatabaseTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseOperationError,
        VitaSyncDatabaseExecutionError,
        VitaSyncValidationError,
        VitaSyncDatabaseError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.delete(
    '/{patientID}',
    status_code=status.HTTP_200_OK,
    summary='Delete a patient record',
    description=(
        'Permanently removes the patient identified by the supplied Patient '
        'ID from the system.'
    ),
    responses={
        200: {'description': 'Patient deleted successfully.'},
        400: {'description': 'Business-rule validation failed.'},
        404: {'description': 'Patient not found.'},
        503: {'description': 'Database service unavailable.'},
        504: {'description': 'Database operation timed out.'},
        500: {'description': 'Unexpected internal server error.'}
    }
)
async def delete(
    patientID: str = Path(
        ...,
        description='Unique Patient ID.',
        examples=['PAT-260702-K7M2X9']
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Permanently deletes a patient.

    @details
    Delegates deletion entirely to PatientManager.delete(). The manager
    validates the request, performs the deletion, and reports any failure
    using the VitaSync exception hierarchy.

    @param patientID Unique Patient ID.
    @param manager Injected PatientManager dependency.

    @throws HTTPException
            - 400 if business-rule validation fails.
            - 404 if the patient does not exist.
            - 503 if the database is unavailable.
            - 504 if the database operation times out.
            - 500 for all remaining internal failures.

    @return Confirmation object indicating successful deletion.
    """
    try:
        await manager.delete(patientID)

        return {
            'patientID': patientID,
            'deleted': True
        }

    except VitaSyncInvalidInputsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

    except VitaSyncNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseDisconnectedError,
        VitaSyncDatabaseUnreachableError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc

    except VitaSyncDatabaseTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseOperationError,
        VitaSyncDatabaseExecutionError,
        VitaSyncValidationError,
        VitaSyncDatabaseError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.patch(
    '/{patientID}',
    status_code=status.HTTP_200_OK,
    summary='Partially update a patient record',
    description=(
        'Updates one or more fields of an existing patient record. '
        'Only the fields supplied in the request body are modified.'
    ),
    responses={
        200: {'description': 'Patient updated successfully.'},
        400: {'description': 'Business-rule validation failed.'},
        404: {'description': 'Patient not found.'},
        409: {'description': 'Update violates a unique constraint.'},
        503: {'description': 'Database service unavailable.'},
        504: {'description': 'Database operation timed out.'},
        500: {'description': 'Unexpected internal server error.'}
    }
)
async def update(
    patientID: str = Path(
        ...,
        description='Unique Patient ID.',
        examples=['PAT-260702-K7M2X9']
    ),
    updateargs: UpdateArgs = Body(
        ...,
        description=(
            'Partial update payload. Only supplied fields are modified.'
        )
    ),
    manager: PatientManager = Depends(get_patient_manager)
):
    """
    @brief Partially updates an existing patient.

    @details
    Delegates update processing to PatientManager.update(), which applies
    only the supplied fields while leaving all unspecified fields unchanged.

    Validation of business rules and construction of the underlying database
    update operation are entirely the responsibility of the manager layer.

    @param patientID Unique Patient ID.
    @param updateargs Partial update payload.
    @param manager Injected PatientManager dependency.

    @throws HTTPException
            - 400 if business-rule validation fails.
            - 404 if the patient does not exist.
            - 409 if the update violates a unique database constraint.
            - 503 if the database is unavailable.
            - 504 if the database operation times out.
            - 500 for all remaining internal failures.

    @return Confirmation object indicating successful update.
    """
    try:
        await manager.update(
            patientID,
            updateargs
        )

        return {
            'patientID': patientID,
            'updated': True
        }

    except VitaSyncInvalidInputsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

    except VitaSyncNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        ) from exc

    except VitaSyncDuplicateEntryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseDisconnectedError,
        VitaSyncDatabaseUnreachableError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc)
        ) from exc

    except VitaSyncDatabaseTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc)
        ) from exc

    except (
        VitaSyncDatabaseOperationError,
        VitaSyncDatabaseExecutionError,
        VitaSyncValidationError,
        VitaSyncDatabaseError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc
        