"""
@file base.py
@brief Defines the root exception class for all VitaSync-specific exceptions.

@details
This module provides VitaSyncBaseError, the common base class inherited by
every custom exception defined within the VitaSync project.

Using a dedicated application-specific exception hierarchy provides several
benefits:

  - Prevents application logic from depending directly on third-party
    exception types.

  - Allows higher application layers to catch all VitaSync-generated errors
    using a single base class.

  - Provides a consistent foundation for organizing exceptions by subsystem
    (database, managers, validation, etc.).

Every custom exception in the project should inherit, either directly or
indirectly, from VitaSyncBaseError.
"""


class VitaSyncBaseError(Exception):
    """
    @brief Base class for all VitaSync-specific exceptions.

    @details
    Extends Python's built-in Exception class and serves as the root of the
    application's exception hierarchy.

    Derived exception classes typically provide predefined error messages
    describing specific failure conditions while preserving compatibility
    with Python's standard exception handling mechanisms.
    """

    def __init__(self, msg) -> None:
        """
        @brief Initializes the exception with an error message.

        @param msg
            Human-readable description of the error.
        """
        super().__init__(msg)
        