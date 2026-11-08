"""Regression tests for private PDF action error handling in the Streamlit UI."""
import ast
from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "app.py"


def _action_try_block(button_label, storage_function):
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Call)
            and isinstance(test.func, ast.Attribute)
            and test.func.attr == "button"
            and test.args
            and isinstance(test.args[0], ast.Constant)
            and test.args[0].value == button_label
        ):
            continue
        for statement in node.body:
            if isinstance(statement, ast.Try):
                calls = [
                    child
                    for child in ast.walk(ast.Module(body=statement.body, type_ignores=[]))
                    if isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == storage_function
                ]
                catches_unexpected = any(
                    handler.type
                    and isinstance(handler.type, ast.Name)
                    and handler.type.id == "Exception"
                    for handler in statement.handlers
                )
                if calls and catches_unexpected:
                    return statement
    raise AssertionError(
        f"{button_label!r} must protect {storage_function} with an Exception handler"
    )


def test_private_pdf_download_preparation_handles_unexpected_errors():
    _action_try_block("Préparer le téléchargement", "download_document")


def test_private_pdf_delete_confirmation_handles_unexpected_errors():
    _action_try_block("Confirmer la suppression", "delete_document")
