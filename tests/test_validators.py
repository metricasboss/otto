from otto.engine.validators import (
    VALIDATORS,
    validate_cpf,
    validate_no_anonymization_context,
    validate_no_consent_context,
)


def test_valid_cpf():
    assert validate_cpf("529.982.247-25") is True


def test_invalid_check_digits():
    assert validate_cpf("123.456.789-00") is False


def test_repeated_digits_invalid():
    assert validate_cpf("111.111.111-11") is False


def test_wrong_length_invalid():
    assert validate_cpf("12.345.678-9") is False


def test_registry():
    assert VALIDATORS["cpf"] is validate_cpf


def test_no_consent_context_suppresses_when_consent_call_present():
    matched = (
        "if (hasConsent('functional')) {\n"
        "  document.cookie = `user_id=${userId}`;\n"
    )
    assert validate_no_consent_context(matched) is False


def test_no_consent_context_passes_when_no_consent_call():
    matched = (
        "function setCookie(userId) {\n"
        "  document.cookie = `user_id=${userId}`;\n"
    )
    assert validate_no_consent_context(matched) is True


def test_no_consent_context_comment_mentioning_consent_still_flags():
    # A bare mention of "consent" (e.g. in a comment) is not a consent *call*,
    # so this must still be flagged.
    matched = (
        "// setting cookie without consent\n"
        "  document.cookie = `user_id=${userId}`;\n"
    )
    assert validate_no_consent_context(matched) is True


def test_no_anonymization_context_suppresses_when_anonymize_call_present():
    matched = (
        "const safeUser = anonymize(user);\n"
        "axios.post('/api/share', safeUser);\n"
    )
    assert validate_no_anonymization_context(matched) is False


def test_no_anonymization_context_passes_when_no_anonymization_call():
    matched = "axios.post('/api/share', user.profile);\n"
    assert validate_no_anonymization_context(matched) is True
