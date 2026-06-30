"""
"""

from vitasync.database.base import DatabaseBase
from vitasync.database.mongodb_client import AsyncMongoDBClient
from vitasync.repositories.patient import PatientRepository


class AsyncMongoDBDatabase(DatabaseBase):
    def __init__(self, client: AsyncMongoDBClient):
        # Client
        self._client = client

        # Database
        self._hospital_database = self._client.get_database('hospital_db')

        # Collections
        self._patient_collections = self._hospital_database['patients']

        # Repositories
        self._patient_repository = PatientRepository(self._patient_collections)

        self._is_initialized = False

    @property
    def client(self) -> AsyncMongoDBClient:
        return self._client

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @property
    def hospital_db(self):
        return self._hospital_database

    @property
    def patient_collections(self):
        return self._patient_collections

    @property
    def patient_repository(self) -> PatientRepository:
        return self._patient_repository
