from __future__ import annotations

from typing import Callable, Dict


def validate_cpf(text: str) -> bool:
    """True if text contains a mathematically valid CPF (check digits ok)."""
    digits = [int(c) for c in text if c.isdigit()]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    for i in (9, 10):
        total = sum(d * w for d, w in zip(digits[:i], range(i + 1, 1, -1)))
        if (total * 10) % 11 % 10 != digits[i]:
            return False
    return True


VALIDATORS: Dict[str, Callable[[str], bool]] = {"cpf": validate_cpf}
