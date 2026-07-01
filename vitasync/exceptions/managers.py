"""
"""

from vitasync.exceptions.base import VitaSyncBaseError
from vitasync.exceptions.database import VitaSyncDatabaseBaseError


class VitaSyncManagersBaseError(VitaSyncBaseError):
    def __init__(self, msg: str) -> None:
        super().__init__(msg=msg)

class VitaSyncPMDatabaseError(VitaSyncManagersBaseError):
    _MESSAGE = 'Ran into database error: {exc}'

    def __init__(self, exc: VitaSyncDatabaseBaseError) -> None:
        super().__init__(self._MESSAGE.format(exc=exc))
