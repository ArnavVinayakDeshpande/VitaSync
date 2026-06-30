"""
"""

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection
)
from pymongo.errors import PyMongoError

from vitasync.exceptions.database import *
from vitasync.database.base import AsyncDatabaseClientBase


class AsyncMongoDBClient(AsyncDatabaseClientBase):
    def __init__(self, uri: str) -> None:
        self._uri = uri
        self._client = AsyncIOMotorClient(self._uri)

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def client(self) -> AsyncIOMotorClient | None:
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def connect(self):
        pass

    async def close(self):
        if self._client is None:
            return

        self._client.close()
        self._client = None

    async def ping(self):
        if self._client is None:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            await self._client.admin.command('ping')

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    def get_database(self, database: str) -> AsyncIOMotorDatabase:
        if self._client is None:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            return self._client[database] 

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc

    def get_collection(
        self,
        database: str,
        collection: str) -> AsyncIOMotorCollection:
        if self._client is None:
            raise VitaSyncDatabaseDisconnectedError()

        try:
            return self._client[database][collection]

        except PyMongoError as exc:
            raise VitaSyncDatabaseExecutionError(exc) from exc
