"""Tests for built-in professional PDF document templates."""

import pytest

from document_templates import (
    PROFESSIONAL_TEMPLATE_NAMES,
    get_professional_template,
)


def test_professional_templates_are_available_and_have_content():
    assert len(PROFESSIONAL_TEMPLATE_NAMES) == 4
    for name in PROFESSIONAL_TEMPLATE_NAMES:
        template = get_professional_template(name)
        assert template["title"]
        assert len(template["body"]) > 100


def test_professional_templates_include_practical_sections():
    assert "Objet :" in get_professional_template("Courrier professionnel")["body"]
    assert "Décisions prises" in get_professional_template("Compte rendu de réunion")["body"]
    assert "Budget" in get_professional_template("Proposition commerciale")["body"]
    assert "Actions attendues" in get_professional_template("Note interne")["body"]


def test_unknown_template_is_rejected():
    with pytest.raises(ValueError):
        get_professional_template("Template inventé")


def test_returned_template_is_a_fresh_copy():
    first = get_professional_template("Note interne")
    first["body"] = "modified"
    assert get_professional_template("Note interne")["body"] != "modified"
