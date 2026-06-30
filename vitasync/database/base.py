"""
"""

from abc import ABC, abstractmethod

from vitasync.repositories.patient import PatientRepository


class AsyncDatabaseClientBase(ABC):
    @abstractmethod
    async def connect(self):
        ...

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def ping(self):
        pass

class DatabaseBase(ABC):
    @property
    @abstractmethod
    def patient_repository(self) -> PatientRepository:
        ...
