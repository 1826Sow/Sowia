import ast
from pathlib import Path


def test_premium_admin_client_is_not_created_when_payments_are_disabled():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "admin_ready"
            for target in node.targets
        )
    ]

    assert len(assignments) == 1
    value = assignments[0].value
    assert isinstance(value, ast.IfExp)
    assert isinstance(value.test, ast.Compare)
    assert isinstance(value.test.left, ast.Name)
    assert value.test.left.id == "payment_config"
    assert any(
        isinstance(operator, ast.IsNot)
        for operator in value.test.ops
    )
    assert isinstance(value.orelse, ast.Constant)
    assert value.orelse.value is False
