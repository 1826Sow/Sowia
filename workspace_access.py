"""Workspace presentation and navigation rules for SOW IA.

Workspace selection changes the visible navigation and explanatory home page.
It does not grant subscription rights; protected operations keep their own
server-side checks in feature_access.py.
"""

WORKSPACE_MODES = ("Personnel", "Professionnel")
NAVIGATION_PAGES = (
    "Accueil",
    "Assistant IA",
    "Ma mémoire",
    "Recherche Web",
    "Analyse PDF",
    "Créer un PDF",
    "Mes documents",
    "Historique",
    "Abonnement",
    "Paramètres",
    "Aide",
)
WORKSPACE_HIDDEN_PAGES = {
    "Professionnel": frozenset({"Ma mémoire"}),
}


def normalize_workspace_mode(value):
    """Return a supported workspace mode, defaulting safely to Personnel."""
    return value if value in WORKSPACE_MODES else "Personnel"


def workspace_navigation(mode):
    """Return navigation pages visible in the selected workspace."""
    workspace = normalize_workspace_mode(mode)
    hidden = WORKSPACE_HIDDEN_PAGES.get(workspace, frozenset())
    return tuple(page for page in NAVIGATION_PAGES if page not in hidden)


def workspace_home_content(mode, premium_active=False):
    """Return workspace-specific copy and shortcuts without granting access."""
    workspace = normalize_workspace_mode(mode)
    if workspace == "Professionnel":
        shortcuts = (
            ("💬", "Assistant IA", "Préparez vos réponses et contenus de travail"),
            ("🌐", "Recherche Web", "Documentez un sujet ou une activité"),
            ("📄", "Analyse PDF", "Examinez vos documents PDF"),
            ("🪄", "Créer un PDF", "Préparez vos documents professionnels"),
            ("📁", "Mes documents", "Retrouvez vos documents sauvegardés"),
            ("🕘", "Historique", "Reprenez vos échanges précédents"),
            ("⚙️", "Paramètres", "Vérifiez votre configuration"),
            ("❓", "Aide", "Consultez les indications d’utilisation"),
        )
        notice = "" if premium_active else (
            "Aperçu de l’espace Professionnel. Le rangement privé des documents "
            "reste verrouillé tant qu’un accès Premium actif n’est pas confirmé."
        )
        return {
            "title": "Votre espace Professionnel",
            "description": "Un espace pour préparer, analyser et organiser vos travaux et documents.",
            "notice": notice,
            "shortcuts": shortcuts,
        }

    shortcuts = (
        ("💬", "Assistant IA", "Posez vos questions et obtenez de l’aide"),
        ("🧠", "Ma mémoire", "Enregistrez vos informations utiles"),
        ("🌐", "Recherche Web", "Recherchez des informations en ligne"),
        ("📄", "Analyse PDF", "Importez et analysez un PDF"),
        ("🪄", "Créer un PDF", "Préparez vos documents PDF"),
        ("📁", "Mes documents", "Retrouvez votre espace documentaire"),
        ("🕘", "Historique", "Consultez vos conversations"),
        ("👑", "Abonnement", "Découvrez l’espace Premium"),
        ("⚙️", "Paramètres", "Vérifiez votre configuration"),
        ("❓", "Aide", "Consultez les indications d’utilisation"),
    )
    return {
        "title": "Bienvenue sur SOW IA",
        "description": "Votre espace personnel pour apprendre, réfléchir, créer et organiser vos idées.",
        "notice": "",
        "shortcuts": shortcuts,
    }
