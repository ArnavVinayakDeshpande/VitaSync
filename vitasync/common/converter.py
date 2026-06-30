"""
"""

from datetime import (
    date,
    datetime,
    time,
    timedelta
)

from vitasync.models.ABHA.demographic_data import ABHADemographicData
from vitasync.models.ABHA.structural_address import ABHAStructuralAddress
from vitasync.models.ABHA.kyc import ABHAKYC
from vitasync.models.patient import (
    Patient
)


def concatenate_name(
    first_name: str,
    middle_name: str | None = None,
    last_name: str | None = None
) -> str:
    return ' '.join(
        filter(
            None,
            [
                first_name,
                middle_name,
                last_name
            ]
        )
    )

# ===========================

def age_to_date_range(age: int) -> tuple[date, date] | None:
    if age <= 0:
        return None

    today = date.today()
    youngest = today.replace(year=today.year-age)
    oldest = today.replace(year=youngest.year-1) + timedelta(days=1)
    
    return (youngest, oldest)

def date_to_datetime_range(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min)
    end = start + timedelta(days=1)

    return (start, end)
