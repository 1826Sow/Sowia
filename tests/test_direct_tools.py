import math
import pytest

from direct_tools import DirectToolError, answer_direct_request, calculate, convert_units


@pytest.mark.parametrize(("expression", "expected"), [
    ("2 + 3 * 4", 14),
    ("(10 - 4) / 2", 3),
    ("2^3", 8),
    ("1,5 + 2,5", 4),
    ("-5 + 2", -3),
])
def test_safe_calculator(expression, expected):
    assert calculate(expression) == expected


@pytest.mark.parametrize("expression", [
    "__import__('os').system('echo unsafe')",
    "open('/etc/passwd').read()",
    "2 ** 1000",
    "1 / 0",
    "float('inf')",
])
def test_calculator_rejects_unsafe_or_invalid_expressions(expression):
    with pytest.raises(DirectToolError):
        calculate(expression)



def test_calculator_rejects_oversized_integer_literal():
    with pytest.raises(DirectToolError, match="hors limites"):
        calculate("9" * 200)


def test_calculator_rejects_long_expression():
    with pytest.raises(DirectToolError):
        calculate("1+" * 110 + "1")


@pytest.mark.parametrize(("value", "source", "target", "expected"), [
    (1, "km", "m", 1000),
    (100, "cm", "m", 1),
    (1, "kg", "g", 1000),
    (1, "l", "ml", 1000),
    (0, "celsius", "fahrenheit", 32),
    (32, "F", "C", 0),
    (1, "mile", "km", 1.609344),
])
def test_unit_conversions(value, source, target, expected):
    assert convert_units(value, source, target) == pytest.approx(expected)


def test_conversion_rejects_incompatible_units():
    with pytest.raises(DirectToolError, match="inconnues ou incompatibles"):
        convert_units(1, "kg", "km")


def test_direct_request_intents():
    assert answer_direct_request("Calcule 12 * (3 + 2)") == "Résultat : 60."
    assert answer_direct_request("Convertis 5 km en miles") == "5 km = 3.1068559 miles."
    assert answer_direct_request("What is 10 / 2?") == "Résultat : 5."
    assert answer_direct_request("Bonjour, comment vas-tu ?") is None
