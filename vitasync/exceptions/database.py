"""
@file database.py
@brief Defines database-related exceptions used throughout VitaSync.

@details
This module provides the application's database exception hierarchy.

Its primary responsibility is to translate exceptions originating from the
MongoDB driver (PyMongo/Motor) into VitaSync-specific exceptions, preventing
third-party exception types from leaking into repositories, managers, or
router layers.

All database-related exceptions ultimately derive from
VitaSyncDatabaseBaseError.
"""

from pymongo.errors import PyMongoError

from vitasync.exceptions.base import VitaSyncBaseError


# Alias representing the root exception type raised by the external
# MongoDB driver.
type ExternalDatabaseBaseError = PyMongoError


class VitaSyncDatabaseBaseError(VitaSyncBaseError):
    """
    @brief Base class for all database-related VitaSync exceptions.

    @details
    Serves as the common parent for every exception originating from the
    application's database layer.
    """

    def __init__(self, msg: str) -> None:
        """
        @brief Initializes a database exception.

        @param msg
            Human-readable error message.
        """
        super().__init__(msg=msg)


class VitaSyncDatabaseDisconnectedError(VitaSyncDatabaseBaseError):
    """
    @brief Raised when a database operation is attempted on a disconnected client.

    @details
    Indicates that the application's MongoDB client has not been initialized,
    has already been closed, or the underlying driver reported a connection
    failure.
    """

    _MESSAGE = 'Failed to connect to database: {exc}.'

    def __init__(self, exc: ExternalDatabaseBaseError | None = None) -> None:
        """
        @brief Constructs the exception.

        @param exc
            Optional underlying PyMongo exception that caused the failure.
        """
        super().__init__(self._MESSAGE.format(exc=exc) if exc is not None else self._MESSAGE)


class VitaSyncDatabaseExecutionError(VitaSyncDatabaseBaseError):
    """
    @brief Raised when execution of a database operation fails.

    @details
    Wraps unexpected exceptions originating from the MongoDB driver during
    CRUD operations.
    """

    _MESSAGE = 'Ran into error while executing a database query: {exc}.'

    def __init__(self, exc: ExternalDatabaseBaseError) -> None:
        """
        @brief Constructs the exception.

        @param exc
            The underlying PyMongo exception.
        """
        super().__init__(self._MESSAGE.format(exc=exc))


class VitaSyncAbsentEntryError(VitaSyncDatabaseBaseError):
    """
    @brief Raised when a requested database entry does not exist.

    @details
    Used by repositories to indicate that no matching document could be
    found for the requested query.
    """

    _MESSAGE = 'Requested entry is absent from the database.'

    def __init__(self) -> None:
        """@brief Constructs the exception."""
        super().__init__(self._MESSAGE)


class VitaSyncDuplicateEntryError(VitaSyncDatabaseBaseError):
    """
    @brief Raised when an operation would create a duplicate database entry.

    @details
    Indicates that a uniqueness constraint would be violated by the requested
    operation.
    """

    _MESSAGE = 'Given entry already exists.'

    def __init__(self) -> None:
        """@brief Constructs the exception."""
        super().__init__(self._MESSAGE)
        