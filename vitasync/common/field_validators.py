"""
"""

import re


def validate_name(name: str, msg: str) -> str:
    if not name:
        raise ValueError(msg)

    return name

