import ast
from pathlib import Path


def test_navigation_groups_keep_every_page_once_and_in_a_clear_folder():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "NAV_GROUPS"
                for target in node.targets)
    )
    groups = ast.literal_eval(assignment.value)
    pages = [page for group_pages in groups.values() for page in group_pages]

    assert len(pages) == len(set(pages)), "Une page apparaît dans plusieurs dossiers."
    assert "Accueil" in pages
    assert "Finance & investissements" in pages
    assert "Revenus & paiements" in pages
    assert "Abonnement" in pages
    assert len(groups) == 8
    assert max(map(len, groups.values())) <= 9
