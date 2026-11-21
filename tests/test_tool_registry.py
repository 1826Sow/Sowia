import pytest

from tool_registry import ToolRegistry, ToolRegistryError, ToolSpec, build_default_registry


def _spec(**overrides):
    values = dict(
        tool_id="demo.lookup",
        version="1.0.0",
        description="Read-only demo lookup.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 40}},
            "required": ["query"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
            "additionalProperties": False,
        },
        required_scopes=("demo:read",),
    )
    values.update(overrides)
    return ToolSpec(**values)


def test_registry_registers_and_retrieves_exact_version():
    registry = ToolRegistry()
    assert registry.register(_spec()) == ("demo.lookup", "1.0.0")
    assert registry.get("demo.lookup", "1.0.0").description == "Read-only demo lookup."


def test_registry_rejects_duplicate_version_and_bad_semver():
    registry = ToolRegistry()
    registry.register(_spec())
    with pytest.raises(ToolRegistryError, match="déjà enregistrée"):
        registry.register(_spec())
    with pytest.raises(ToolRegistryError, match="semver"):
        registry.register(_spec(version="latest"))


def test_registry_requires_explicit_scopes():
    registry = ToolRegistry()
    registry.register(_spec())
    with pytest.raises(ToolRegistryError, match="Scopes manquants|scopes manquants"):
        registry.authorize("demo.lookup", "1.0.0", [])
    assert registry.authorize("demo.lookup", "1.0.0", ["demo:read"]).tool_id == "demo.lookup"


def test_registry_validates_required_types_and_rejects_extra_fields():
    registry = ToolRegistry()
    registry.register(_spec())
    assert registry.validate_input("demo.lookup", "1.0.0", {"query": "Paris"})
    with pytest.raises(ToolRegistryError, match="obligatoire"):
        registry.validate_input("demo.lookup", "1.0.0", {})
    with pytest.raises(ToolRegistryError, match="non autorisé"):
        registry.validate_input("demo.lookup", "1.0.0", {"query": "Paris", "admin": True})
    with pytest.raises(ToolRegistryError, match="Type incorrect"):
        registry.validate_input("demo.lookup", "1.0.0", {"query": 12})


def test_registry_validates_outputs_and_bounds():
    registry = ToolRegistry()
    registry.register(_spec())
    assert registry.validate_output("demo.lookup", "1.0.0", {"result": "ok"})
    with pytest.raises(ToolRegistryError, match="obligatoire"):
        registry.validate_output("demo.lookup", "1.0.0", {})


def test_registry_defensively_copies_specs():
    registry = ToolRegistry()
    spec = _spec()
    registry.register(spec)
    spec.input_schema["properties"]["query"]["maxLength"] = 999
    retrieved = registry.get("demo.lookup", "1.0.0")
    retrieved.input_schema["properties"]["query"]["maxLength"] = 999
    with pytest.raises(ToolRegistryError, match="trop longue"):
        registry.validate_input("demo.lookup", "1.0.0", {"query": "x" * 41})


def test_default_weather_tool_is_metadata_only_and_scoped():
    registry = build_default_registry()
    weather = registry.get("weather.forecast", "1.0.0")
    assert weather.required_scopes == ("weather:read",)
    assert weather.approval_required is False
    assert weather.estimated_cost_units == 0
    assert registry.validate_input("weather.forecast", "1.0.0", {"location": "Paris"})
    with pytest.raises(ToolRegistryError):
        registry.validate_input("weather.forecast", "1.0.0", {"location": "Paris", "days": 90})
