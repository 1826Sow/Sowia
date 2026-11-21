"""Versioned, policy-first registry for SOW IA tools.

This module describes and validates capabilities; it deliberately does not execute
tool code, access credentials, or grant permissions to callers.
"""
from copy import deepcopy
from dataclasses import dataclass
import re


class ToolRegistryError(ValueError):
    """Raised when a tool definition or invocation is invalid."""


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    version: str
    description: str
    input_schema: dict
    output_schema: dict
    required_scopes: tuple = ()
    data_categories: tuple = ()
    provider: str = "internal"
    freshness: str = "on_demand"
    max_timeout_seconds: int = 15
    quota_per_minute: int = 30
    estimated_cost_units: int = 0
    approval_required: bool = False


def _validate_schema_definition(schema, path="$"):
    if not isinstance(schema, dict):
        raise ToolRegistryError(f"Schéma invalide à {path}: un objet est requis.")
    kind = schema.get("type")
    if kind not in {"object", "array", "string", "number", "integer", "boolean"}:
        raise ToolRegistryError(f"Type de schéma non pris en charge à {path}.")
    if kind == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise ToolRegistryError(f"Définition d'objet invalide à {path}.")
        if any(not isinstance(key, str) for key in properties):
            raise ToolRegistryError(f"Nom de propriété invalide à {path}.")
        if any(key not in properties for key in required):
            raise ToolRegistryError(f"Champ obligatoire inconnu à {path}.")
        for key, child in properties.items():
            _validate_schema_definition(child, f"{path}.{key}")
    elif kind == "array":
        _validate_schema_definition(schema.get("items"), f"{path}[]")
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise ToolRegistryError(f"Enum invalide à {path}.")


def _validate_value(value, schema, path="$"):
    kind = schema["type"]
    valid = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
    }[kind](value)
    if not valid:
        raise ToolRegistryError(f"Type incorrect pour {path}; attendu: {kind}.")
    if "enum" in schema and value not in schema["enum"]:
        raise ToolRegistryError(f"Valeur non autorisée pour {path}.")
    if kind == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ToolRegistryError(f"Champ(s) obligatoire(s) absent(s) à {path}: {', '.join(missing)}.")
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(properties)
            if extra:
                raise ToolRegistryError(f"Champ(s) non autorisé(s) à {path}: {', '.join(sorted(extra))}.")
        for key, item in value.items():
            if key in properties:
                _validate_value(item, properties[key], f"{path}.{key}")
    elif kind == "array":
        for index, item in enumerate(value):
            _validate_value(item, schema["items"], f"{path}[{index}]")
    if kind in {"string", "array"}:
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ToolRegistryError(f"Valeur trop courte à {path}.")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ToolRegistryError(f"Valeur trop longue à {path}.")
    if kind in {"number", "integer"}:
        if "minimum" in schema and value < schema["minimum"]:
            raise ToolRegistryError(f"Valeur inférieure au minimum à {path}.")
        if "maximum" in schema and value > schema["maximum"]:
            raise ToolRegistryError(f"Valeur supérieure au maximum à {path}.")


class ToolRegistry:
    """In-memory registry with exact version lookup and least-privilege checks."""

    def __init__(self):
        self._tools = {}

    def register(self, spec):
        if not isinstance(spec, ToolSpec):
            raise ToolRegistryError("Une définition ToolSpec est requise.")
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{1,63}", spec.tool_id or ""):
            raise ToolRegistryError("Identifiant d'outil invalide.")
        if not re.fullmatch(r"\\d+\\.\\d+\\.\\d+", spec.version or ""):
            raise ToolRegistryError("La version doit suivre le format semver X.Y.Z.")
        if not spec.description or not spec.description.strip():
            raise ToolRegistryError("La description de l'outil est obligatoire.")
        for field in ("max_timeout_seconds", "quota_per_minute"):
            value = getattr(spec, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ToolRegistryError(f"{field} doit être un entier positif.")
        if isinstance(spec.estimated_cost_units, bool) or not isinstance(spec.estimated_cost_units, int) or spec.estimated_cost_units < 0:
            raise ToolRegistryError("Le coût estimé doit être un entier positif ou nul.")
        if not isinstance(spec.approval_required, bool):
            raise ToolRegistryError("approval_required doit être booléen.")
        _validate_schema_definition(spec.input_schema)
        _validate_schema_definition(spec.output_schema)
        key = (spec.tool_id, spec.version)
        if key in self._tools:
            raise ToolRegistryError("Cette version de l'outil est déjà enregistrée.")
        self._tools[key] = deepcopy(spec)
        return key

    def get(self, tool_id, version):
        spec = self._tools.get((tool_id, version))
        if spec is None:
            raise ToolRegistryError("Outil ou version introuvable.")
        return deepcopy(spec)

    def list_tools(self):
        return [deepcopy(self._tools[key]) for key in sorted(self._tools)]

    def authorize(self, tool_id, version, granted_scopes):
        spec = self.get(tool_id, version)
        granted = set(granted_scopes or ())
        missing = set(spec.required_scopes) - granted
        if missing:
            raise ToolRegistryError("Autorisation refusée; scopes manquants: " + ", ".join(sorted(missing)) + ".")
        return spec

    def validate_input(self, tool_id, version, payload):
        spec = self.get(tool_id, version)
        _validate_value(payload, spec.input_schema)
        return True

    def validate_output(self, tool_id, version, payload):
        spec = self.get(tool_id, version)
        _validate_value(payload, spec.output_schema)
        return True


def build_default_registry():
    """Return metadata for the first direct weather capability; no execution hook."""
    registry = ToolRegistry()
    registry.register(ToolSpec(
        tool_id="weather.forecast",
        version="1.0.0",
        description="Consulter les conditions météo et les prévisions d'une localité.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "minLength": 1, "maxLength": 100},
                "forecast_days": {"type": "integer", "minimum": 1, "maximum": 7},
            },
            "required": ["location"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "location": {"type": "object"},
                "current": {"type": "object"},
                "daily": {"type": "object"},
                "source": {"type": "string"},
            },
            "required": ["location", "current", "daily", "source"],
            "additionalProperties": False,
        },
        required_scopes=("weather:read",),
        data_categories=("public_weather",),
        provider="Open-Meteo",
        freshness="live_at_request",
        max_timeout_seconds=15,
        quota_per_minute=30,
        estimated_cost_units=0,
        approval_required=False,
    ))
    return registry
