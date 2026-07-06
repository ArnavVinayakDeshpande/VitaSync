"""
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict
)
from enum import StrEnum, auto
from datetime import datetime
import vitasync.common.validator as validator


class DiagnosticCategory(StrEnum):
    IMAGING = auto()
    LABORATORY = auto()
    PATHOLOGY = auto()
    OTHER = auto()

class DiagnosticReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    test_name: str = Field(
        ...,
        serialization_alias='testName',
        validation_alias='testName',
        description='',
        min_length=1
    )

    category: DiagnosticCategory = Field(
        ...,
        serialization_alias='category',
        validation_alias='category',
        description=''
    )

    clinical_summary: str | None = Field(
        default=None,
        serialization_alias='clinicalSummary',
        validation_alias='clinicalSummary',
        description=''
    )

    ordered_by_hpr_id: str = Field(
        ...,
        serialization_alias='orderedByHPRID',
        validation_alias='orderedByHPRID',
        description=''
    )

    report_file_urls: list[str] = Field(
        default_factory=list,
        serialization_alias='reportFileURLs',
        validation_alias='serializationURLs',
        description=''
    )

    result_date: datetime | None = Field(
        default=None,
        serialization_alias='resultDate',
        validation_alias='resultDate',
        description=''
    )

    is_abnormal: bool | None = Field(
        default=None,
        serialization_alias='isAbnormal',
        validation_alias='isAbnormal',
        description=''
    )

    @field_validator('ordered_by_hpr_id')
    @classmethod
    def validate_hpr_id(cls, v):
        return validator.validate_hpr_id(v)
