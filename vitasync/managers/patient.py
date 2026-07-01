"""
"""

from pydantic import ValidationError

from vitasync.exceptions.managers import VitaSyncManagersBaseError, VitaSyncPMDatabaseError
from vitasync.repositories.patient import (
    ConditionGetAllArgs,
    ABHAKYCGetAllArgs,
    GetFieldsResult,
    UpdateArgs,
    PatientRepository
)
from vitasync.exceptions.generic import VitaSyncDataValidationError, VitaSyncInvalidInputsError
from vitasync.exceptions.database import VitaSyncDatabaseBaseError, VitaSyncDuplicateEntryError
from vitasync.common.idgenerator import PatientID
from vitasync.models.patient import Patient


class PatientManager:
    def __init__(
        self,
        repository: PatientRepository
    ):
        self._repository = repository

    @property
    def repository(self) -> PatientRepository:
        return self._repository

    async def create(
        self,
        patient_dict: dict,
        max_retries: int = 5
    ) -> Patient:
        max_retries = max_retries if max_retries > 0 else 5

        for i in range(max_retries):
            try:
                generated_id = PatientID.generate(patient_dict['created_on'])

                patient = Patient(
                    pid=generated_id,
                    **patient_dict
                )

                await self._repository.create(patient)

                return patient

            except KeyError as exc:
                raise VitaSyncInvalidInputsError(['patient::created_on'], f'created_on field in patient dict either does not exist or is not a valid datetime: {exc}.') from exc

            except ValidationError as exc:
                raise VitaSyncDataValidationError(exc) from exc

            except VitaSyncDuplicateEntryError as exc:
                if i == max_retries - 1:
                    raise VitaSyncPMDatabaseError(exc) from exc # TODO Change database error to add pid duplication vs fields duplication
                continue

            except VitaSyncDatabaseBaseError as exc:
                raise VitaSyncPMDatabaseError(exc) from exc

        raise VitaSyncManagersBaseError(f'Unknown error occured, could not add patient even after retrying for: {max_retries}')

    async def delete(self, pid: str) -> None:
        try:
            PatientID.validate(pid)

            await self._repository.delete(pid)

        except ValueError as exc:
            raise VitaSyncInvalidInputsError(['pid'], f'Tried to delete patient entry with invalid pid: {pid}') from exc

        except VitaSyncDatabaseBaseError as exc:
            raise VitaSyncPMDatabaseError(exc) from exc        

    async def update(
        self,
        updateargs: UpdateArgs
    ):
        try:
            await self._repository.update(updateargs)

        except VitaSyncDatabaseBaseError as exc:
            raise VitaSyncPMDatabaseError(exc) from exc

    async def get(self, pid: str) -> Patient | None:
        try:
            PatientID.validate(pid)

            return await self._repository.get(pid)

        except ValueError as exc:
            raise VitaSyncInvalidInputsError(['pid'], f'Tried to fetch a patient with an invalid pid: {pid}') from exc

        except VitaSyncDatabaseBaseError as exc:
            raise VitaSyncPMDatabaseError(exc) from exc

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
        try:
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

        except VitaSyncDatabaseBaseError as exc:
            raise VitaSyncPMDatabaseError(exc) from exc

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
        try:
            PatientID.validate(pid)

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

        except ValueError as exc:
            raise VitaSyncInvalidInputsError(['pid'], f'Tried to fetch fields from a patient with an invalid pid: {pid}') from exc

        except VitaSyncDatabaseBaseError as exc:
            raise VitaSyncPMDatabaseError(exc) from exc

    async def getpid(
        self,
        mobile_number: str | None = None,
        abha_number: str | None = None,
        abha_address: str | None = None,
        abha_mobile_number: str | None = None
    ) -> str | None:
        try:
            # TODO validation of this shit
            return await self._repository.getpid(
                mobile_number=mobile_number,
                abha_number=abha_number,
                abha_address=abha_address,
                abha_mobile_number=abha_mobile_number
            )

        except VitaSyncDatabaseBaseError as exc:
            raise VitaSyncPMDatabaseError(exc) from exc

patient_manager: PatientManager | None = None
