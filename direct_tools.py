"""Safe, deterministic calculator and unit conversion tools for SOW IA."""
import ast
import math
import operator
import re


class DirectToolError(ValueError):
    """Raised when a direct calculation or conversion is invalid."""


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_number(node, depth=0):
    if depth > 20:
        raise DirectToolError("Expression trop complexe.")
    if isinstance(node, ast.Expression):
        return _safe_number(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = node.value
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        value = _UNARY[type(node.op)](_safe_number(node.operand, depth + 1))
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _safe_number(node.left, depth + 1)
        right = _safe_number(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e100):
            raise DirectToolError("Puissance trop importante.")
        try:
            value = _BINARY[type(node.op)](left, right)
        except (ArithmeticError, OverflowError) as exc:
            raise DirectToolError("Calcul impossible (division par zéro ou dépassement numérique).") from exc
    else:
        raise DirectToolError("Expression non autorisée. Seules les opérations arithmétiques simples sont acceptées.")
    if isinstance(value, complex) or abs(value) > 1e100:
        raise DirectToolError("Résultat hors limites.")
    try:
        if not math.isfinite(value):
            raise DirectToolError("Résultat hors limites.")
    except OverflowError as exc:
        raise DirectToolError("Résultat hors limites.") from exc
    return value


def calculate(expression):
    """Evaluate arithmetic only; never eval arbitrary Python."""
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 200:
        raise DirectToolError("Expression vide ou trop longue.")
    normalized = expression.strip().replace(",", ".").replace("×", "*").replace("÷", "/").replace("^", "**")
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise DirectToolError("Expression mathématique invalide.") from exc
    return _safe_number(tree)


_UNIT_ALIASES = {
    "mm": ("length", 0.001), "millimetre": ("length", 0.001), "millimetres": ("length", 0.001),
    "cm": ("length", 0.01), "centimetre": ("length", 0.01), "centimetres": ("length", 0.01),
    "m": ("length", 1.0), "metre": ("length", 1.0), "metres": ("length", 1.0), "meter": ("length", 1.0), "meters": ("length", 1.0),
    "km": ("length", 1000.0), "kilometre": ("length", 1000.0), "kilometres": ("length", 1000.0), "kilometer": ("length", 1000.0), "kilometers": ("length", 1000.0),
    "mi": ("length", 1609.344), "mile": ("length", 1609.344), "miles": ("length", 1609.344),
    "g": ("mass", 0.001), "gramme": ("mass", 0.001), "grammes": ("mass", 0.001), "gram": ("mass", 0.001), "grams": ("mass", 0.001),
    "kg": ("mass", 1.0), "kilo": ("mass", 1.0), "kilos": ("mass", 1.0), "kilogramme": ("mass", 1.0), "kilogrammes": ("mass", 1.0), "kilogram": ("mass", 1.0), "kilograms": ("mass", 1.0),
    "lb": ("mass", 0.45359237), "lbs": ("mass", 0.45359237), "pound": ("mass", 0.45359237), "pounds": ("mass", 0.45359237),
    "oz": ("mass", 0.028349523125), "ounce": ("mass", 0.028349523125), "ounces": ("mass", 0.028349523125),
    "ml": ("volume", 0.001), "millilitre": ("volume", 0.001), "millilitres": ("volume", 0.001), "milliliter": ("volume", 0.001), "milliliters": ("volume", 0.001),
    "cl": ("volume", 0.01), "centilitre": ("volume", 0.01), "centilitres": ("volume", 0.01),
    "l": ("volume", 1.0), "litre": ("volume", 1.0), "litres": ("volume", 1.0), "liter": ("volume", 1.0), "liters": ("volume", 1.0),
}
_TEMP = {"c": "c", "°c": "c", "celsius": "c", "f": "f", "°f": "f", "fahrenheit": "f"}


def convert_units(value, source_unit, target_unit):
    """Convert common length, mass, volume and temperature units."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DirectToolError("Valeur numérique invalide.") from exc
    if not math.isfinite(number) or abs(number) > 1e100:
        raise DirectToolError("Valeur numérique hors limites.")
    source = str(source_unit).strip().lower()
    target = str(target_unit).strip().lower()
    if source in _TEMP and target in _TEMP:
        celsius = number if _TEMP[source] == "c" else (number - 32) * 5 / 9
        result = celsius if _TEMP[target] == "c" else celsius * 9 / 5 + 32
    else:
        source_info = _UNIT_ALIASES.get(source)
        target_info = _UNIT_ALIASES.get(target)
        if not source_info or not target_info or source_info[0] != target_info[0]:
            raise DirectToolError("Unités inconnues ou incompatibles.")
        result = number * source_info[1] / target_info[1]
    if not math.isfinite(result):
        raise DirectToolError("Résultat de conversion hors limites.")
    return result


_NUMBER = r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)"
_UNIT = r"[a-zA-Z°]+"
_CONVERSION = re.compile(
    rf"^\s*(?:convert(?:is|ir|issez)?\s+)?({_NUMBER})\s*({_UNIT})\s+(?:en|vers|to)\s+({_UNIT})\s*[?.!]*\s*$",
    re.IGNORECASE,
)
_CALC_PREFIX = re.compile(r"^\s*(?:calcule(?:r|z)?|combien font|what is|calculate)\s+(.+?)[?.!]*\s*$", re.IGNORECASE)


def answer_direct_request(prompt):
    """Return a French answer for recognized calculator/conversion prompts, else None."""
    if not isinstance(prompt, str):
        return None
    match = _CONVERSION.fullmatch(prompt)
    if match:
        raw_value, source, target = match.groups()
        value = float(raw_value.replace(",", "."))
        result = convert_units(value, source, target)
        return f"{value:g} {source} = {result:.9g} {target}."
    match = _CALC_PREFIX.fullmatch(prompt)
    if match:
        result = calculate(match.group(1))
        return f"Résultat : {result:.12g}."
    return None
