from __future__ import annotations

import re
import unicodedata


_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_user_pseudo(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return _NON_ALNUM_PATTERN.sub("-", ascii_value).strip("-")
