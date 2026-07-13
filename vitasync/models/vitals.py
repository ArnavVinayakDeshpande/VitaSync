"""
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)


class Vitals(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    systolic_bp: int | None = Field(
        default=None,
        serialization_alias='systolicBP',
        validation_alias='systolicBP',
        description=''
    )

    diastolic_bp: int | None = Field(
        default=None,
        serialization_alias='diastolicBP',
        validation_alias='diastolicBP',
        description=''
    )

    weight_kg: float | None = Field(
        default=None,
        serialization_alias='weightKG',
        validation_alias='weightKG',
        description=''
    )

    pulse_bpm: int | None = Field(
        default=None,
        serialization_alias='pulseBPM',
        validation_alias='pulseBPM',
        description=''
    )

    temperature_f: float | None = Field(
        default=None,
        serialization_alias='temperatureF',
        validation_alias='temperatureF',
        description=''
    )

    spo2: int | None = Field(
        default=None,
        serialization_alias='spO2',
        validation_alias='spO2',
        description=''
    )

    height_cm: float | None = Field(
        default=None,
        serialization_alias='heightCM',
        validation_alias='heightCM',
        description=''
    )

    @field_validator(
        'systolic_bp', 
        'diastolic_bp',
        'weight_kg',
        'pulse_bpm',
        'temperature_f',
        'spo2',
        'height_cm'
    )
    @classmethod
    def validate_systolic_bp(cls, v):
        if not v:
            return None

        if v <= 0:
            raise ValueError('Given vitals cannot be less than or equal to zero.')

        return v
