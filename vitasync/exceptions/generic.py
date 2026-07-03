"""
@file generic.py
@brief Defines generic application exceptions not tied to a specific subsystem.

@details
This module contains exceptions representing validation failures and invalid
application inputs.

Unlike database or manager exceptions, these errors may originate from
request validation, business logic, or model construction.
"""

from pydantic import ValidationError

from vitasync.exceptions.base import VitaSyncBaseError


class VitaSyncInvalidInputsError(VitaSyncBaseError):
    """
    @brief Raised when one or more supplied inputs are invalid.

    @details
    Used when application-level validation detects invalid user input before
    processing begins.
    """

    _MESSAGE = "Given inputs are invalid: {inputs}"

    def __init__(self, invalid_inputs: list[str], extra_msg: str | None = None):
        """
        @brief Constructs the exception.

        @param invalid_inputs
            List of invalid input fields.

        @param extra_msg
            Optional additional context describing the validation failure.
        """
        msg = self._MESSAGE.format(inputs=invalid_inputs)

        if extra_msg:
            msg += f"\n\tmsg: {extra_msg}"

        super().__init__(msg)


class VitaSyncDataValidationError(VitaSyncBaseError):
    """
    @brief Raised when Pydantic model validation fails.

    @details
    Wraps Pydantic ValidationError instances to prevent external library
    exceptions from propagating beyond the application's validation layer.
    """

    def __init__(self, exc: ValidationError):
        """
        @brief Constructs the exception.

        @param exc
            The underlying Pydantic ValidationError.
        """
        super().__init__(exc)
        