"""
"""

from pydantic import ValidationError

from vitasync.exceptions.base import VitaSyncBaseError


class VitaSyncInvalidInputsError(VitaSyncBaseError):
    _MESSAGE = "Given inputs are invalid: {inputs}"

    def __init__(self, invalid_inputs: list[str], extra_msg: str | None = None):
        msg = self._MESSAGE.format(inputs=invalid_inputs)

        if extra_msg:
            msg += f"\n\tmsg: {extra_msg}"

        super().__init__(msg)

class VitaSyncDataValidationError(VitaSyncBaseError):
    def __init__(self, exc: ValidationError):
        super().__init__(exc)
