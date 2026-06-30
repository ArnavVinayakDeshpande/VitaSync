"""
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from vitasync.exceptions.database import *


class MongoDBClient:
    def __init__(self, uri: str) -> None:
        self._uri = uri
        self._client = AsyncIOMotorClient(self._uri)

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def client(self) -> AsyncIOMotorClient:
        return self._client

    async def check_connection(self):
        try:
            await self._client.admin.command('ping')

        except PyMongoError as exc:
            raise VitaSyncDatabaseDisconnectedError(exc) from exc
