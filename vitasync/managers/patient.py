"""
@file patient.py

@brief Implements the patient management layer.

@details
Provides the PatientManager class, which encapsulates the application's
business logic for managing patient records.

The patient manager acts as an intermediary between higher application
layers and the patient repository by performing input validation,
constructing Patient model instances, generating unique patient
identifiers, and translating repository exceptions into manager-level
exceptions.

Unlike the repository layer, this module contains no database-specific
logic. Instead, it coordinates business operations while delegating all
data persistence and retrieval to PatientRepository.
"""

from pydantic import ValidationError
from datetime import datetime

from vitasync.exceptions.managers import VitaSyncManagersBaseError, VitaSyncPMDatabaseError
from vitasync.repositories.patient import (
    ConditionGetAllArgs,
    ABHAKYCGetAllArgs,
    GetFieldsResult,
    UpdateArgs,
    PatientRepository
)
from vitasync.common.error import *
from vitasync.common.idgenerator import PatientID
from vitasync.models.patient import (
    Patient,
    PatientCreate
)


# ── Patient Manager ────────────────────────────────────────────────────────────

class PatientManager:
    """
    @brief Manages patient-related business operations.

    @details
    Provides the application's business layer for patient management by
    coordinating validation, model construction, patient identifier
    generation, and persistence operations.

    The manager serves as an abstraction over PatientRepository, allowing
    higher application layers to interact with patient records without
    directly depending on repository implementation details.

    Responsibilities of the manager include:

      - Generating unique patient identifiers.

      - Constructing validated Patient objects from user-supplied input.

      - Performing high-level validation before repository operations.

      - Translating repository exceptions into manager-specific exceptions.

      - Delegating all persistence operations to PatientRepository.

    @note
        The manager contains business logic only. All database interaction
        is delegated to the underlying repository.
    """

    def __init__(
        self,
        repository: PatientRepository
    ):
        """
        @brief Initializes the patient manager.

        @details
        Creates a new PatientManager using the supplied patient repository.

        The manager stores a reference to the repository and delegates all
        patient persistence and retrieval operations through it.

        @param repository
            The patient repository used by the manager to perform all
            database operations.
        """

        # Repository responsible for patient persistence.
        self._repository = repository

        if not self._repository.is_initialized:
            raise VitaSyncInvalidInputsError(
                ['PatientManager::init::repository'],
                'PatientManager expects an already initialized repository, the repository given has not been initialized.'
            )

    @property
    def repository(self) -> PatientRepository:
        """
        @brief Returns the managed patient repository.

        @details
        Provides access to the PatientRepository instance used internally
        by the manager for all patient persistence and retrieval
        operations.

        @return
            The managed PatientRepository instance.
        """
        return self._repository

    async def create(
        self,
        patient_create: PatientCreate,
        max_retries: int = 5
    ) -> Patient:
        """
        @brief Creates a new patient record.

        @details
        Creates a new patient by generating a unique patient identifier,
        constructing a validated Patient model, and persisting it through
        the underlying patient repository.

        Since patient identifier generation may occasionally produce a
        duplicate identifier, the operation is automatically retried a
        configurable number of times before ultimately failing.

        Any repository-level database exceptions are translated into
        manager-level exceptions before being propagated to higher
        application layers.

        @param patient_create
            The validated patient creation data used to construct the new
            patient record.

        @param max_retries
            The maximum number of attempts to generate a unique patient
            identifier before reporting failure.

        @return
            The newly created Patient object.

        @throws VitaSyncDataValidationError
            If the constructed Patient model fails validation.

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while creating the patient
            record.

        @throws VitaSyncManagersBaseError
            If the patient could not be created even after exhausting all
            retry attempts.
        """
        # Ensure that at least one retry attempt is performed.
        max_retries = max_retries if max_retries > 0 else 5

        # Retry patient creation in the unlikely event of a generated
        # patient identifier collision.
        for i in range(max_retries):
            try:
                # Record the creation timestamp.
                created_on = datetime.now()

                # Generate a unique patient identifier.
                generated_id = PatientID.generate(created_on)

                # Construct the validated patient model.
                patient = Patient(
                    pid=generated_id,
                    created_on=created_on,
                    **patient_create.model_dump()
                )

                # Persist the patient record.
                await self._repository.create(patient)

                return patient

            # except KeyError as exc:
            #     raise VitaSyncInvalidInputsError(['patient::created_on'], f'created_on field in patient dict either does not exist or is not a valid datetime: {exc}.') from exc

            except ValidationError as exc:
                raise VitaSyncValidationError(exc) from exc

            # Retry only when the generated patient identifier collides
            # with an existing record.
            except VitaSyncDuplicateEntryError as exc:
                if i == max_retries - 1:
                    raise exc from exc  # TODO Change database error to add pid duplication vs fields duplication
                continue

        # This point should only be reached if every retry attempt fails.
        raise VitaSyncManagerError(
            f'Unknown error occured, could not add patient even after retrying for: {max_retries}'
        )

    async def create_unsafe(
        self,
        patient_data: dict,
        max_retries: int = 5
    ) -> Patient:
        """
        @brief Creates a patient from unvalidated input data.

        @details
        Creates a new patient using a raw dictionary instead of a validated
        PatientCreate model.

        This method is intended for trusted internal callers that already
        possess validated patient data or need to bypass the PatientCreate
        model.

        The creation workflow is otherwise identical to create(), including
        patient identifier generation, retry handling, model validation,
        and repository persistence.

        @warning
            This method accepts raw input data and should therefore only be
            used by trusted internal components.

        @param patient_data
            A dictionary containing the patient attributes used to construct
            the Patient model.

        @param max_retries
            The maximum number of attempts to generate a unique patient
            identifier before reporting failure.

        @return
            The newly created Patient object.

        @throws VitaSyncDataValidationError
            If the supplied patient data cannot be converted into a valid
            Patient model.

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while creating the patient
            record.

        @throws VitaSyncManagersBaseError
            If the patient could not be created even after exhausting all
            retry attempts.
        """
        # Ensure that at least one retry attempt is performed.
        max_retries = max_retries if max_retries > 0 else 5

        # Retry patient creation in the unlikely event of a generated
        # patient identifier collision.
        for i in range(max_retries):
            try:
                # Record the creation timestamp.
                created_on = datetime.now()

                # Generate a unique patient identifier.
                generated_id = PatientID.generate(created_on)

                # Construct the validated patient model.
                patient = Patient(
                    pid=generated_id,
                    created_on=created_on,
                    **patient_data
                )

                # Persist the patient record.
                await self._repository.create(patient)

                return patient

            # except KeyError as exc:
            #     raise VitaSyncInvalidInputsError(['patient::created_on'], f'created_on field in patient dict either does not exist or is not a valid datetime: {exc}.') from exc

            except ValidationError as exc:
                raise VitaSyncValidationError(exc) from exc

            # Retry only when the generated patient identifier collides
            # with an existing record.
            except VitaSyncDuplicateEntryError as exc:
                if i == max_retries - 1:
                    raise exc from exc  # TODO Change database error to add pid duplication vs fields duplication
                continue

        # This point should only be reached if every retry attempt fails.
        raise VitaSyncManagerError(
            f'Unknown error occured, could not add patient even after retrying for: {max_retries}'
        )

    async def delete(self, pid: str) -> None:
        """
        @brief Deletes an existing patient record.

        @details
        Validates the supplied patient identifier before delegating the
        deletion request to the underlying patient repository.

        Repository-level exceptions are translated into manager-level
        exceptions to provide a consistent interface to higher application
        layers.

        @param pid
            The unique identifier of the patient to be deleted.

        @throws VitaSyncInvalidInputsError
            If the supplied patient identifier is invalid.

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while deleting the patient.
        """
        await self._repository.delete(pid)

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

        The manager delegates all update operations to the repository while
        translating repository exceptions into manager-level exceptions.

        @param pid
            The unique identifier of the patient to update.

        @param updateargs
            The collection of requested updates to be applied.

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while updating the patient.
        """
        await self._repository.update(
            pid=pid,
            updateargs=updateargs
        )

    async def get(self, pid: str) -> Patient | None:
        """
        @brief Retrieves a patient by their unique identifier.

        @details
        Validates the supplied patient identifier before retrieving the
        corresponding patient record from the repository.

        @param pid
            The unique identifier of the patient to retrieve.

        @return
            The matching Patient object if one exists; otherwise None.

        @throws VitaSyncInvalidInputsError
            If the supplied patient identifier is invalid.

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while retrieving the patient.
        """
        return await self._repository.get(pid)

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

        The manager forwards all filtering parameters to the repository,
        which performs the actual query construction and data retrieval.

        @param size
            The maximum number of patient records to return.

        @param offset
            The number of matching patient records to skip.

        @param name_search
            A case-insensitive prefix used to search patients' names.

        @param conditions
            Filters patients according to their recorded medical
            conditions.

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

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while retrieving patients.
        """
        return await self._repository.getall(
            size=size,
            offset=offset,
            name_search=name_search,
            conditions=conditions,
            is_active=is_active,
            age=age,
            abha_kyc_exists=abha_kyc_exists,
            abha_kyc=abha_kyc
        )

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
        Validates the supplied patient identifier before requesting only
        the selected fields from the repository.

        This method is useful when only a subset of patient information is
        required, avoiding retrieval of the complete patient record.

        @param pid
            The unique identifier of the patient.

        @param name
            Indicates whether the patient's name should be returned.

        @param mobile_number
            Indicates whether the patient's mobile number should be
            returned.

        @param date_of_birth
            Indicates whether the patient's date of birth should be
            returned.

        @param conditions
            Indicates whether the patient's medical conditions should be
            returned.

        @param is_active
            Indicates whether the patient's active status should be
            returned.

        @param abha_kyc
            Indicates whether the patient's ABHA KYC information should be
            returned.

        @param created_on
            Indicates whether the patient's record creation timestamp
            should be returned.

        @return
            A GetFieldsResult object containing the requested fields if a
            matching patient exists; otherwise None.

        @throws VitaSyncInvalidInputsError
            If the supplied patient identifier is invalid.

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while retrieving the
            requested fields.
        """
        return await self._repository.getfields(
            pid=pid,
            name=name,
            mobile_number=mobile_number,
            date_of_birth=date_of_birth,
            conditions=conditions,
            is_active=is_active,
            abha_kyc=abha_kyc,
            created_on=created_on
        )

    async def getpid(
        self,
        mobile_number: str | None = None,
        abha_number: str | None = None,
        abha_address: str | None = None,
        abha_mobile_number: str | None = None
    ) -> str | None:
        """
        @brief Retrieves a patient's unique identifier.

        @details
        Searches for a patient using one or more alternate identifying
        attributes and returns the corresponding patient identifier.

        The manager delegates the lookup to the repository after receiving
        the supplied identifiers.

        @param mobile_number
            The patient's registered mobile number.

        @param abha_number
            The patient's ABHA number.

        @param abha_address
            The patient's ABHA address.

        @param abha_mobile_number
            The mobile number recorded within the patient's ABHA
            demographic information.

        @return
            The matching patient identifier if one exists; otherwise None.

        @throws VitaSyncPMDatabaseError
            If a database-related error occurs while retrieving the patient
            identifier.
        """
        return await self._repository.getpid(
            mobile_number=mobile_number,
            abha_number=abha_number,
            abha_address=abha_address,
            abha_mobile_number=abha_mobile_number
        )

# Global patient manager instance.
#
# This reference is intended to store the application's shared
# PatientManager instance once it has been initialized.
patient_manager: PatientManager | None = None
