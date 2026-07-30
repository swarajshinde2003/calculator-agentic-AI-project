"""Shared numeric extraction helper used by all calculator tools."""
import re
from typing import List


# Matches an optional leading minus, digits, and an optional decimal part.
# Works for integers, decimals, and negative values.
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def parse_numbers(text: str) -> List[float]:
    """Return all signed integers/decimals found in *text* as floats."""
    return [float(m) for m in _NUMBER_RE.findall(text)]


def fmt(n: float) -> str:
    """Return an integer string when *n* is whole, otherwise a float string."""
    return str(int(n)) if n == int(n) else str(n)
