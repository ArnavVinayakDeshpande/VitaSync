"""
"""

from pymongo.errors import PyMongoError

from vitasync.exceptions.base import VitaSyncBaseError


type ExternalDatabaseBaseError = PyMongoError

class VitaSyncDatabaseBaseError(VitaSyncBaseError):
    def __init__(self, msg: str) -> None:
        super().__init__(msg=msg)

class VitaSyncDatabaseDisconnectedError(VitaSyncDatabaseBaseError):
    _MESSAGE = 'Failed to connect to database: {exc}.'

    def __init__(self, exc: ExternalDatabaseBaseError | None = None) -> None:
        super().__init__(self._MESSAGE.format(exc=exc) if exc is not None else self._MESSAGE)

class VitaSyncDatabaseExecutionError(VitaSyncDatabaseBaseError):
    _MESSAGE = 'Ran into error while executing a database query: {exc}.'

    def __init__(self, exc: ExternalDatabaseBaseError) -> None:
        super().__init__(self._MESSAGE.format(exc=exc))

class VitaSyncAbsentEntryError(VitaSyncDatabaseBaseError):
    _MESSAGE = 'Requested entry is absent from the database.'

    def __init__(self) -> None:
        super().__init__(self._MESSAGE)

class VitaSyncDuplicateEntryError(VitaSyncDatabaseBaseError):
    _MESSAGE = 'Given entry already exists.'

    def __init__(self) -> None:
        super().__init__(self._MESSAGE)
