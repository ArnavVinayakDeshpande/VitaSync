"""
@file managers.py
@brief Defines exceptions used by the manager layer.

@details
The manager layer coordinates business logic between repositories and API
routers. This module provides manager-specific exceptions that wrap lower
database-layer exceptions, preventing repository implementation details from
leaking into higher layers.
"""

from vitasync.exceptions.base import VitaSyncBaseError
from vitasync.exceptions.database import VitaSyncDatabaseBaseError


class VitaSyncManagersBaseError(VitaSyncBaseError):
    """
    @brief Base class for all manager-layer exceptions.

    @details
    Serves as the common parent for exceptions raised by the application's
    business logic layer.
    """

    def __init__(self, msg: str) -> None:
        """
        @brief Initializes the exception.

        @param msg
            Human-readable error message.
        """
        super().__init__(msg=msg)


class VitaSyncPMDatabaseError(VitaSyncManagersBaseError):
    """
    @brief Raised when a patient manager encounters a database error.

    @details
    Wraps database-layer exceptions so that callers interacting with the
    manager layer need not depend directly on repository or database
    exceptions.
    """

    _MESSAGE = 'Ran into database error: {exc}'

    def __init__(self, exc: VitaSyncDatabaseBaseError) -> None:
        """
        @brief Constructs the exception.

        @param exc
            The underlying database exception.
        """
        super().__init__(self._MESSAGE.format(exc=exc))
        