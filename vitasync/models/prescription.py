"""
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)
from enum import StrEnum, auto


class Frequency(StrEnum):
    ONCE_DAILY = auto()
    TWICE_DAILY = auto()
    THRICE_DAILY = auto()
    EVERY_MORNING = auto()
    EVERY_NIGHT = auto()
    AS_NEEDED = auto()

class Prescription(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    medicine_name: str = Field(
        ...,
        serialization_alias='medicineName',
        validation_alias='medicineName',
        description='',
        min_length=1
    )

    dosage: str = Field(
        ...,
        serialization_alias='dosage',
        validation_alias='dosage',
        description='',
        min_length=1
    )

    frequency: Frequency = Field(
        ...,
        serialization_alias='frequency',
        validation_alias='frequency',
        description=''
    )

    duration_days: int | None = Field(
        default=None,
        serialization_alias='durationDays',
        validation_alias='durationDays',
        description='',
        gt=0
    )

    duration_notes: str | None = Field(
        default=None,
        serialization_alias='durationNotes',
        validation_alias='durationNotes',
        description=''
    )

    special_instructions: str | None = Field(
        default=None,
        serialization_alias='specialInstructions',
        validation_alias='specialInstructions',
        description=''
    )

    refillable: bool = Field(
        default=False,
        serialization_alias='refillable',
        validation_alias='refillable',
        description=''
    )