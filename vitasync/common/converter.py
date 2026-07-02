r"""
"""

from datetime import (
    date,
    datetime,
    time,
    timedelta
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

def date_to_datetime(d: date) -> datetime:
    return datetime.combine(d, time.min)

def date_to_datetime_range(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min)
    end = start + timedelta(days=1)

    return (start, end)

def convert_types_to_mongodb_types(model_dict: dict) -> dict:
    for key, value in model_dict.items():
        if isinstance(value, set):
            model_dict[key] = list(value)

        if isinstance(value, date) and not isinstance(value, datetime):
            model_dict[key] = date_to_datetime(value)

        if isinstance(value, dict):
            model_dict[key] = convert_types_to_mongodb_types(value)

    return model_dict

def to_mongo_dict(model) -> dict:
    data = model.model_dump()
    return convert_types_to_mongodb_types(data)
