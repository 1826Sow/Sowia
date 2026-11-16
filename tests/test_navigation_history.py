"""Regression tests for SOW IA's Streamlit navigation history."""
import ast
from pathlib import Path
from types import SimpleNamespace


class SessionState(dict):
    """Minimal dict- and attribute-compatible stand-in for Streamlit state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def load_navigation():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {"category_for_page", "remember_navigation_target", "choose_navigation_category",
              "sync_navigation_category", "go_back_navigation", "go_to_page"}
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "NAV_GROUPS"
            for target in node.targets
        ):
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            nodes.append(node)
    namespace = {"st": SimpleNamespace(session_state=SessionState())}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "app.py", "exec"), namespace)
    return namespace, namespace["st"].session_state


def test_back_button_walks_pages_in_reverse_order():
    nav, state = load_navigation()
    state.update(page_nav="Hub SOWIA", sowia_current_page="Hub SOWIA")
    nav["go_to_page"]("Assistant IA")
    nav["go_to_page"]("Analyse PDF")

    nav["go_back_navigation"]()
    assert state["page_nav"] == "Assistant IA"
    assert state["nav_category"] == nav["category_for_page"]("Assistant IA")

    nav["go_back_navigation"]()
    assert state["page_nav"] == "Hub SOWIA"


def test_opening_current_page_does_not_add_duplicate_history():
    nav, state = load_navigation()
    state.update(page_nav="Accueil", sowia_current_page="Accueil")
    nav["go_to_page"]("Accueil")
    assert state.get("sowia_navigation_history", []) == []


def test_category_change_keeps_previous_page_available_for_back():
    nav, state = load_navigation()
    state.update(
        page_nav="Assistant IA",
        sowia_current_page="Assistant IA",
        nav_category="📚 Échanges & projets",
    )
    nav["choose_navigation_category"]()

    assert state["page_nav"] == "Mes échanges & projets"
    assert state["sowia_navigation_history"] == ["Assistant IA"]
    nav["go_back_navigation"]()
    assert state["page_nav"] == "Assistant IA"


def test_back_ignores_stale_or_unknown_history_entries():
    nav, state = load_navigation()
    state.update(
        page_nav="Analyse PDF",
        sowia_current_page="Analyse PDF",
        sowia_navigation_history=["ancienne rubrique supprimée", "Accueil"],
    )
    nav["go_back_navigation"]()
    assert state["page_nav"] == "Accueil"
    assert state["sowia_navigation_history"] == ["ancienne rubrique supprimée"]
