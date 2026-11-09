import ast
from pathlib import Path


def _parents(tree):
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def test_premium_admin_client_is_created_only_after_payments_are_enabled():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    parents = _parents(tree)

    admin_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_admin_client"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "premium_access"
    ]
    assert len(admin_calls) == 1

    call = admin_calls[0]
    enclosing_try = parents.get(call)
    while enclosing_try is not None and not isinstance(enclosing_try, ast.Try):
        enclosing_try = parents.get(enclosing_try)
    assert enclosing_try is not None

    enclosing_if = parents.get(enclosing_try)
    assert isinstance(enclosing_if, ast.If)
    assert isinstance(enclosing_if.test, ast.Name)
    assert enclosing_if.test.id == "paypal_token"

    guarded_configuration = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "payment_config"
        and any(isinstance(op, ast.Is) for op in node.test.ops)
        and any(
            isinstance(child, ast.Raise)
            and isinstance(child.exc, ast.Call)
            and isinstance(child.exc.func, ast.Name)
            and child.exc.func.id == "RuntimeError"
            for child in ast.walk(node)
        )
        for node in enclosing_try.body
    )
    assert guarded_configuration
