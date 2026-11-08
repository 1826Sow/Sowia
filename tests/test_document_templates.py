"""Tests for editable professional PDF templates."""

import pytest

from document_templates import (
    PROFESSIONAL_TEMPLATE_NAMES,
    get_professional_template,
)


def test_professional_templates_are_available_and_have_content():
    assert set(PROFESSIONAL_TEMPLATE_NAMES) == {
        "Courrier professionnel",
        "Compte rendu de réunion",
        "Proposition commerciale",
        "Note interne",
    }
    for name in PROFESSIONAL_TEMPLATE_NAMES:
        template = get_professional_template(name)
        assert template["title"].strip()
        assert template["body"].strip()


def test_template_returns_an_independent_editable_copy():
    first = get_professional_template("Note interne")
    second = get_professional_template("Note interne")
    first["body"] = "Contenu personnalisé"
    assert second["body"] != first["body"]


def test_unknown_template_is_rejected():
    with pytest.raises(ValueError, match="Modèle professionnel inconnu"):
        get_professional_template("Contrat magique")
