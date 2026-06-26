"""
"""


from vitasync.exceptions.base import VitaSyncBaseException


class VitaSyncInvalidInputsError(VitaSyncBaseException):
    _MESSAGE = "Given inputs are invalid: {inputs}"

    def __init__(self, invalid_inputs: list[str], extra_msg: str | None = None):
        msg = self._MESSAGE.format(inputs=invalid_inputs)

        if extra_msg:
            msg += f"\n\tmsg: {extra_msg}"

        super().__init__(msg)
