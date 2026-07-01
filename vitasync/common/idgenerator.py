"""
"""

from datetime import date, datetime
import random
import re


class PatientID:
    RANDOM_PART_LENGTH: int = 6
    SAFE_CHARACTERS: str = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'

    @staticmethod
    def generate(created_on: date) -> str:
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
        if not pid:
            raise ValueError('PatientID is empty.')

        pattern = fr'^PAT-(\d{{6}})-([{"|".join(PatientID.SAFE_CHARACTERS)}]{{{PatientID.RANDOM_PART_LENGTH}}})$'

        matched = re.match(pattern, pid)

        if not bool(matched):
            raise ValueError(f'Invalid PatientID: "{pid}"')

        date_str = matched.group(1)

        try:
            datetime.strptime(date_str, '%y%m%d')

        except ValueError as exc:
            raise ValueError(
                f'PatientID "{pid}" contains an invalid embedded date.'
            ) from exc

        return pid
