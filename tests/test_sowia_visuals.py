import ast
from pathlib import Path

from sowia_visuals import PAGE_VISUALS, render_page_visual


def test_every_navigation_destination_has_its_own_visual():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    nav_assignment = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "NAV_GROUPS"
                for target in node.targets)
    )
    nav_groups = ast.literal_eval(nav_assignment.value)
    destinations = {
        destination
        for group_destinations in nav_groups.values()
        for destination in group_destinations
    }

    assert destinations <= set(PAGE_VISUALS)
    assert "Accueil" in PAGE_VISUALS
    assert "Mes échanges & projets" in PAGE_VISUALS
    assert "Final Tech" in PAGE_VISUALS


def test_each_rubrique_renders_an_accessible_modern_image():
    rendered = {
        page: render_page_visual(page)
        for page in PAGE_VISUALS
    }
    assert all('data:image/svg+xml;base64,' in markup for markup in rendered.values())
    assert all('alt="Illustration de la rubrique ' in markup for markup in rendered.values())
    assert len(set(rendered.values())) == len(rendered)
