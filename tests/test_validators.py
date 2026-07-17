from otto.engine.validators import VALIDATORS, validate_cpf


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
