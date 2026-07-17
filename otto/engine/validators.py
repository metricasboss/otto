from __future__ import annotations

import re
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


_CONSENT_CALL_RE = re.compile(r"consent\w*\s*\(", re.IGNORECASE)


def validate_no_consent_context(text: str) -> bool:
    """True (flag it) only if no consent-check *call* appears in the matched span.

    Rules that widen their match to include a couple of preceding lines (e.g.
    ``cookie_without_consent``) rely on this to avoid flagging code that gates
    the sensitive call behind a consent check on an adjacent line. Matching a
    call-like pattern (``hasConsent(``, ``cookieConsent(``, ...) rather than the
    bare word ``consent`` keeps a nearby comment such as "without consent" from
    accidentally suppressing a genuine finding.
    """
    return not _CONSENT_CALL_RE.search(text)


_ANONYMIZATION_MARKERS = (
    "anonymize(",
    "anonymise(",
    "pseudonymize(",
    "pseudonymise(",
    "hash(",
)


def validate_no_anonymization_context(text: str) -> bool:
    """True (flag it) only if no anonymization/pseudonymization call appears in span."""
    lowered = text.lower()
    return not any(marker in lowered for marker in _ANONYMIZATION_MARKERS)


VALIDATORS: Dict[str, Callable[[str], bool]] = {
    "cpf": validate_cpf,
    "no_consent_context": validate_no_consent_context,
    "no_anonymization_context": validate_no_anonymization_context,
}
