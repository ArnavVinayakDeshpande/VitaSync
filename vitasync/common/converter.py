"""
@file converter.py
@brief Utility functions for data type conversion and serialization within VitaSync.

@details
This module provides pure, stateless helper functions used across the VitaSync
codebase for three categories of conversion:

  1. Name concatenation — combining first, middle, and last name components
     into a single normalized full name string.

  2. Date and age arithmetic — converting ages to date ranges, and converting
     Python date/datetime objects into MongoDB-compatible datetime objects.

  3. MongoDB serialization — converting Pydantic model instances into BSON-safe
     Python dicts suitable for direct insertion into MongoDB via Motor/PyMongo,
     handling type mismatches such as Python sets (unsupported by BSON) and
     bare date objects (which must be datetime for BSON Date encoding).

@note All functions in this module are pure and stateless — they have no side
      effects and do not interact with the database, network, or filesystem.
      They are safe to call from any layer of the application.
"""

from datetime import (
    date,
    datetime,
    time,
    timedelta
)


# ── Name Utilities ─────────────────────────────────────────────────────────────

def concatenate_name(
    first_name: str,
    middle_name: str | None = None,
    last_name: str | None = None
) -> str:
    """
    @brief Concatenates name components into a single full name string.

    @details
    Joins the provided name parts with single spaces, automatically filtering
    out any None or empty string values. This ensures that patients with only
    a first name, or without a middle name, do not produce leading, trailing,
    or double spaces in the resulting name string.

    Examples:
    @code
    concatenate_name("Priya")                        # "Priya"
    concatenate_name("Priya", None, "Sharma")        # "Priya Sharma"
    concatenate_name("Priya", "Kumari", "Sharma")    # "Priya Kumari Sharma"
    concatenate_name("Priya", "", "Sharma")          # "Priya Sharma"
    @endcode

    @param first_name The patient's legal first name. Required, must be non-empty.
    @param middle_name The patient's middle name. Optional, pass None to omit.
    @param last_name The patient's legal last name. Optional, pass None to omit.

    @return A single space-separated full name string containing only the
            non-None, non-empty name components.
    """
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


# ── Date & Age Arithmetic ──────────────────────────────────────────────────────

def age_to_date_range(age: int) -> tuple[date, date] | None:
    """
    @brief Converts an age in years to a corresponding date-of-birth range.

    @details
    Given an age in whole years, computes the inclusive range of dates of birth
    that would result in a person being exactly that age today. This is used
    to construct MongoDB range queries on the date_of_birth field when filtering
    patients by age.

    The range is computed as:
      - youngest: today's date with the year decremented by age (the most recent
        date of birth that still results in the given age today)
      - oldest: one day after the date one additional year back (the earliest
        date of birth that still results in the given age today, not yet having
        turned age+1)

    Example for age=30 on 2026-07-02:
      youngest = 1996-07-02  (born today 30 years ago — still 30)
      oldest   = 1995-07-03  (born one day after this would make them 31)

    @param age The age in whole years to convert. Must be greater than zero.

    @return A tuple of (youngest_dob, oldest_dob) as date objects representing
            the inclusive date-of-birth range for the given age, or None if
            age is less than or equal to zero.
    """
    if age <= 0:
        return None

    today = date.today()
    youngest = today.replace(year=today.year - age)
    oldest = today.replace(year=youngest.year - 1) + timedelta(days=1)

    return (youngest, oldest)


def date_to_datetime(d: date) -> datetime:
    """
    @brief Converts a Python date object to a datetime at midnight (00:00:00).

    @details
    MongoDB's BSON format does not natively support Python's bare date type —
    all date-like values must be stored as BSON Date, which maps to Python's
    datetime. This function converts a date to a datetime at midnight (time.min),
    which is the VitaSync convention for storing date-only values such as
    date of birth, LMP date, and EDD date.

    @note datetime is a subclass of date in Python. This function should only
          be called with bare date objects, not datetime instances. The caller
          is responsible for ensuring the correct type is passed. In
          convert_types_to_mongodb_types(), this is enforced via an explicit
          isinstance(value, datetime) exclusion check.

    @param d The bare date object to convert.

    @return A datetime object representing the same calendar date at 00:00:00.
    """
    return datetime.combine(d, time.min)


def date_to_datetime_range(d: date) -> tuple[datetime, datetime]:
    """
    @brief Converts a date to a half-open datetime range covering that calendar day.

    @details
    Produces a (start, end) tuple where start is the given date at midnight
    (00:00:00) and end is the start of the following calendar day (also midnight).
    This represents the half-open interval [start, end) covering the entire
    24-hour period of the given date.

    Used when constructing MongoDB range queries on datetime fields that were
    originally bare date values — for example, querying all records whose
    date_of_birth falls on a specific calendar date.

    Example for date(2005, 3, 12):
      start = datetime(2005, 3, 12, 0, 0, 0)
      end   = datetime(2005, 3, 13, 0, 0, 0)

    @param d The calendar date to convert to a datetime range.

    @return A tuple of (start_datetime, end_datetime) where start is the given
            date at 00:00:00 and end is the following date at 00:00:00.
    """
    start = datetime.combine(d, time.min)
    end = start + timedelta(days=1)
    return (start, end)


# ── MongoDB Serialization ──────────────────────────────────────────────────────

def convert_types_to_mongodb_types(model_dict: dict) -> dict:
    """
    @brief Recursively converts a dict's values to BSON-compatible Python types.

    @details
    Motor/PyMongo encodes Python dicts to BSON for MongoDB storage, but not all
    Python types map cleanly to BSON. This function performs the following
    conversions recursively across all nested dicts:

      - set → list:
        BSON has no native set type. Python sets are not encodable by PyMongo
        and will raise bson.errors.InvalidDocument if passed directly. They are
        converted to lists since BSON arrays (lists) are the closest equivalent.
        Set uniqueness semantics are preserved at the application layer via
        MongoDB's $addToSet operator on updates.

      - date → datetime (midnight):
        BSON Date maps to Python datetime, not bare date. Bare date objects are
        not natively encodable by PyMongo. They are converted to datetime at
        midnight (00:00:00) via date_to_datetime(), consistent with VitaSync's
        date-as-datetime storage convention.

        Note: the isinstance(value, datetime) exclusion is critical here since
        datetime is a subclass of date in Python — without it, already-correct
        datetime values would be re-converted, stripping their time component.

      - dict → recursively converted dict:
        Nested Pydantic sub-models (e.g. ABHAKYC, ABHADemographicData) are
        dumped as nested dicts by model_dump(). This function recurses into
        them to apply the same type conversions at every level of nesting.

    @param model_dict A flat or nested dict produced by Pydantic's model_dump(),
                      to be converted in-place to BSON-safe types.

    @return The same dict with all values converted to BSON-compatible types.
            Mutation is performed in-place but the dict is also returned for
            convenience in chained calls.
    """
    for key, value in model_dict.items():
        if isinstance(value, set):
            model_dict[key] = list(value)

        if isinstance(value, date) and not isinstance(value, datetime):
            model_dict[key] = date_to_datetime(value)

        if isinstance(value, dict):
            model_dict[key] = convert_types_to_mongodb_types(value)

    return model_dict


def to_mongo_dict(model) -> dict:
    """
    @brief Converts a Pydantic model instance to a BSON-safe dict for MongoDB insertion.

    @details
    This is the primary serialization entry point for writing any Pydantic model
    to MongoDB. It performs two steps:

      1. model.model_dump() — serializes the Pydantic model to a plain Python dict
         using Python field names (not aliases), with all nested sub-models also
         serialized to dicts. None values are included by default.

      2. convert_types_to_mongodb_types() — recursively converts any Python types
         that PyMongo/Motor cannot encode to BSON (sets → lists, date → datetime).

    This function should be called in every repository create() and update()
    method before passing data to Motor's insert_one() or update_one(), and
    should never be bypassed in favor of passing raw model_dump() output directly
    to Motor, as that risks bson.errors.InvalidDocument errors on any model
    containing set or bare date fields.

    @param model Any Pydantic BaseModel instance to serialize for MongoDB storage.

    @return A BSON-safe Python dict suitable for direct use in Motor's
            insert_one(), update_one(), or replace_one() operations.
    """
    data = model.model_dump()
    return convert_types_to_mongodb_types(data)
    