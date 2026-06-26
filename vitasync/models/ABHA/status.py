"""
"""

from enum import StrEnum


class ABHAStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
    PENDING = 'PENDING'
    SUSPENDED = 'SUSPENDED'
