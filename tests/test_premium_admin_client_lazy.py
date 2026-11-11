import ast
from pathlib import Path


def _parents(tree):
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def test_premium_admin_client_is_created_only_inside_authenticated_paypal_flows():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    parents = _parents(tree)

    admin_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_admin_client"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "premium_access"
    ]
    # Calls cover checkout validation, the authenticated subscription
    # overview, two explicit synchronization actions, and the admin-only
    # read-only control center. Every call must remain conditionally guarded.
    assert len(admin_calls) == 5

    for call in admin_calls:
        ancestor = parents.get(call)
        guarded = False
        while ancestor is not None:
            if isinstance(ancestor, ast.If):
                guarded = True
                break
            ancestor = parents.get(ancestor)
        assert guarded, "Admin client creation must stay behind a conditional flow"

    source_guard = source.index("if cloud_mode and current_user is not None:")
    assert source_guard < source.index("premium_access.create_admin_client()")
    assert 'key="sync_paypal_recurring_ledger"' in source
    assert 'key="sync_paypal_one_time_refunds"' in source
