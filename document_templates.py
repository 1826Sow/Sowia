"""Editable French templates for common professional PDF documents."""

PROFESSIONAL_TEMPLATES = {
    "Courrier professionnel": {
        "title": "Courrier professionnel",
        "body": """[Nom et coordonnées de l’expéditeur]
[Nom et coordonnées du destinataire]
[Ville], le [date]

Objet : [objet du courrier]

Madame, Monsieur,

[Présentez clairement le contexte de votre demande ou de votre information.]

[Ajoutez les précisions utiles, les dates et les actions attendues.]

Je vous remercie de votre attention et reste à votre disposition pour tout complément.

Veuillez agréer, Madame, Monsieur, mes salutations distinguées.

[Nom et fonction]""",
    },
    "Compte rendu de réunion": {
        "title": "Compte rendu de réunion",
        "body": """Date et heure : [à compléter]
Lieu / format : [à compléter]
Participants : [à compléter]
Objet : [à compléter]

1. Points abordés
[Résumez les sujets dans l’ordre.]

2. Décisions prises
- [Décision] — Responsable : [nom] — Échéance : [date]

3. Actions à suivre
- [Action] — Responsable : [nom] — Échéance : [date]

Prochaine réunion : [date / heure]
Rédigé par : [nom]""",
    },
    "Proposition commerciale": {
        "title": "Proposition commerciale",
        "body": """PROPOSITION COMMERCIALE

Émetteur : [entreprise / coordonnées]
Destinataire : [client / coordonnées]
Date : [date]
Référence : [référence]

1. Votre besoin
[Décrivez le besoin et les objectifs exprimés.]

2. Solution proposée
[Présentez les prestations, produits ou livrables.]

3. Planning prévisionnel
[Étapes, dates et délais indicatifs.]

4. Budget
[Prix, taxes applicables et conditions à préciser.]

5. Conditions et validité
[Modalités, limites de la proposition et durée de validité.]

Contact : [nom, fonction, coordonnées]""",
    },
    "Note interne": {
        "title": "Note interne",
        "body": """NOTE INTERNE

À : [destinataires]
De : [auteur / service]
Date : [date]
Objet : [sujet]

Contexte
[Présentez brièvement la situation.]

Informations essentielles
[Exposez les faits et éléments utiles.]

Décisions ou consignes
[Précisez les décisions et les consignes applicables.]

Actions attendues
[Indiquez les actions, responsables et échéances.]

Contact : [coordonnées]""",
    },
}

PROFESSIONAL_TEMPLATE_NAMES = tuple(PROFESSIONAL_TEMPLATES)


def get_professional_template(name):
    """Return a fresh editable template; reject unknown names."""
    if name not in PROFESSIONAL_TEMPLATES:
        raise ValueError("Modèle professionnel inconnu.")
    template = PROFESSIONAL_TEMPLATES[name]
    return {"title": template["title"], "body": template["body"]}
