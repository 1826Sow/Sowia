import ast
from pathlib import Path


def test_every_home_rubrique_uses_an_accessible_unique_illustration():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    renderer = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "render_home_rubrique_art"
    )
    parameters = [arg.arg for arg in renderer.args.args]
    assert parameters == ["title", "group_index", "item_index"]

    renderer_source = ast.get_source_segment(source, renderer)
    assert "<svg" in renderer_source
    assert 'role="img"' in renderer_source
    assert "aria-label=" in renderer_source
    assert "sowia-rubrique-" in renderer_source
    assert "group_index" in renderer_source
    assert "item_index" in renderer_source

    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_home_rubrique_art"
    ]
    assert len(calls) == 1
    call = calls[0]
    assert len(call.args) == 3
    assert isinstance(call.args[0], ast.Name)
    assert call.args[0].id == "destination"
    assert isinstance(call.args[1], ast.Name)
    assert call.args[1].id == "section_index"
    assert ast.unparse(call.args[2]) == "item_start + item_offset"

    assert "enumerate(home_sections)" in source
    assert "enumerate(" in source and "section_items[item_start:item_start + 2]" in source
