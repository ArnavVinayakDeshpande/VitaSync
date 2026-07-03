"""
@file idgenerator.py
@brief Provides ID generation and validation utilities for VitaSync entity identifiers.

@details
This module defines static ID generation and validation logic for patient
identifiers used throughout the VitaSync system. IDs are designed to be:

  - Human-readable: a fixed prefix makes the entity type immediately obvious
    at a glance, both in the UI and in database documents.
  - Date-stamped: the embedded registration date provides a rough chronological
    anchor without relying on fragile auto-incrementing sequences that break
    on deletion.
  - Collision-resistant: a random suffix drawn from an unambiguous character
    set provides sufficient uniqueness at clinic scale, with collision retry
    handled at the manager layer.
  - Visually unambiguous: characters that are easily confused in print or when
    read aloud (0/O, 1/I/L) are excluded from the random suffix character set.

@note This module is intentionally stateless — both PatientID methods are
      static and have no side effects. ID uniqueness is enforced at the
      database layer via a unique index on the pid field, not within this module.
"""

from datetime import date, datetime
import random
import re


class PatientID:
    """
    @brief Generates and validates Patient ID (PID) strings for VitaSync patients.

    @details
    Patient IDs follow the format:

        PAT-YYMMDD-XXXXXX

    Where:
      - PAT     : Fixed prefix identifying this as a patient identifier.
      - YYMMDD  : Two-digit year, two-digit month, two-digit day of the patient's
                  registration date. Provides a rough chronological anchor and
                  makes the registration period immediately readable.
      - XXXXXX  : Six random characters drawn from SAFE_CHARACTERS, providing
                  collision resistance within the same registration date.

    Example: PAT-260702-K7M2X9

    The random suffix character set (SAFE_CHARACTERS) deliberately excludes:
      - '0' and 'O' — visually identical in many fonts and when spoken aloud
      - '1', 'I', and 'L' — visually identical in many fonts and when spoken aloud

    This ensures PIDs can be safely read off a screen, printed on MCH cards,
    or communicated verbally without ambiguity.

    @note ID uniqueness across the patient collection is enforced by a MongoDB
          unique index on the pid field, created during PatientRepository.initialize().
          On the rare occasion that two patients registered on the same day receive
          the same random suffix, the PatientManager.create() method handles the
          resulting DuplicateKeyError by retrying with a newly generated PID.
    """

    RANDOM_PART_LENGTH: int = 6
    """@brief Number of random characters in the PID suffix. Default is 6."""

    SAFE_CHARACTERS: str = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    """
    @brief Character pool for the random PID suffix.

    @details
    Uppercase alphanumeric characters with visually ambiguous characters removed:
      - Excluded digits : 0, 1
      - Excluded letters: I, L, O
    Yields 31 distinct characters, giving 31^6 = ~887 million possible suffixes
    per registration date — far exceeding VitaSync's expected patient volume.
    """

    @staticmethod
    def generate(created_on: date) -> str:
        """
        @brief Generates a new unique Patient ID for a given registration date.

        @details
        Constructs a PID by combining a fixed 'PAT' prefix, a six-digit date
        part derived from the registration date, and a six-character random
        suffix sampled with replacement from SAFE_CHARACTERS.

        The date part uses two-digit year formatting (%y) to keep the PID
        concise. This is intentional — the embedded date is a human-readable
        hint, not a precise timestamp, and two-digit years are unambiguous
        within the expected operational lifetime of the system.

        @note This method does not guarantee uniqueness on its own. Uniqueness
              is enforced at the database layer. Callers (PatientManager.create)
              should handle DuplicateKeyError by calling generate() again with
              a fresh invocation.

        @param created_on The registration date of the patient, used to construct
                          the date portion of the PID. Typically date.today() at
                          the time of patient registration.

        @return A PID string in the format 'PAT-YYMMDD-XXXXXX', e.g. 'PAT-260702-K7M2X9'.
        """
        date_part = created_on.strftime('%y%m%d')
        random_part = ''.join(
            random.choices(
                PatientID.SAFE_CHARACTERS,
                k=PatientID.RANDOM_PART_LENGTH
            )
        )
        return f'PAT-{date_part}-{random_part}'

    @staticmethod
    def validate(pid: str) -> str:
        """
        @brief Validates a Patient ID string against the expected PID format.

        @details
        Performs three sequential validation checks:

          1. Emptiness check: rejects blank or empty strings immediately before
             attempting regex matching, producing a clearer error message.

          2. Format check: validates the full PID structure against the canonical
             regex pattern, ensuring the prefix, date segment, separator hyphens,
             and random suffix all conform to the expected shape and character set.

          3. Date validity check: extracts the six-digit date segment from the
             matched PID and attempts to parse it as a real calendar date in
             %y%m%d format. This rejects structurally valid but semantically
             nonsensical PIDs such as 'PAT-269999-K7M2X9' where '9999' is not
             a valid month-day combination.

        This method is intended for use as a Pydantic field validator in the
        Patient model, and as a guard in any code path that receives a PID
        from an external source (e.g. path parameters in the patient router).

        @param pid The Patient ID string to validate.

        @return The original pid string, unchanged, if all validation checks pass.
                This allows the method to be used directly as a Pydantic
                field_validator return value.

        @throws ValueError If the pid is empty, does not match the expected
                           format PAT-YYMMDD-XXXXXX, or contains an invalid
                           embedded date segment.
        """
        if not pid:
            raise ValueError(
                'Patient ID cannot be empty. '
                'Expected format: PAT-YYMMDD-XXXXXX (e.g. PAT-260702-K7M2X9).'
            )

        pattern = (
            fr'^PAT-(\d{{6}})-'
            fr'([{re.escape(PatientID.SAFE_CHARACTERS)}]{{{PatientID.RANDOM_PART_LENGTH}}})$'
        )

        matched = re.match(pattern, pid)

        if not matched:
            raise ValueError(
                f'Patient ID "{pid}" does not match the expected format PAT-YYMMDD-XXXXXX. '
                f'The prefix must be "PAT", the date segment must be six digits (YYMMDD), '
                f'and the suffix must be {PatientID.RANDOM_PART_LENGTH} characters drawn '
                f'from the allowed character set (uppercase letters and digits, '
                f'excluding 0, 1, I, L, O).'
            )

        date_str = matched.group(1)

        try:
            datetime.strptime(date_str, '%y%m%d')

        except ValueError as exc:
            raise ValueError(
                f'Patient ID "{pid}" contains an invalid embedded date segment "{date_str}". '
                f'The date portion must represent a real calendar date in YYMMDD format '
                f'(e.g. "260702" for 2nd July 2026).'
            ) from exc

        return pid
        