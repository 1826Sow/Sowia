"""Workspace selection and server-side feature entitlement checks."""

WORKSPACE_MODES = ("Personnel", "Professionnel")

# Explicit registry: unknown feature names are denied until deliberately added.
FREE_FEATURES = frozenset({
    "Accueil",
    "Assistant IA",
    "Ma mémoire",
    "Recherche Web",
    "Analyse PDF",
    "Créer un PDF",
    "Historique",
    "Abonnement",
    "Paramètres",
    "Aide",
})
PREMIUM_FEATURES = frozenset({"Mes documents"})

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

# The professional workspace focuses on work tools and does not expose the
# personal memory page in its navigation. This is a UI/workspace boundary,
# not a replacement for server-side authorization.
WORKSPACE_HIDDEN_PAGES = {
    "Professionnel": frozenset({"Ma mémoire"}),
}


def workspace_navigation(mode):
    """Return the navigation pages visible in the selected workspace."""
    workspace = normalize_workspace_mode(mode)
    hidden = WORKSPACE_HIDDEN_PAGES.get(workspace, frozenset())
    return tuple(page for page in NAVIGATION_PAGES if page not in hidden)



def normalize_workspace_mode(value):
    """Return a supported workspace mode, defaulting safely to Personnel."""
    return value if value in WORKSPACE_MODES else "Personnel"


def has_active_premium(entitlement):
    """Only a server-loaded active entitlement grants Premium access."""
    return isinstance(entitlement, dict) and entitlement.get("status") == "active"


def can_access_feature(feature, entitlement):
    """Allow known free features; require active Premium or deny unknown names."""
    if feature in FREE_FEATURES:
        return True
    if feature in PREMIUM_FEATURES:
        return has_active_premium(entitlement)
    return False


def workspace_home_content(mode, premium_active=False):
    """Return honest, workspace-specific home copy and shortcuts."""
    workspace = normalize_workspace_mode(mode)
    if workspace == "Professionnel":
        shortcuts = (
            ("💬", "Assistant IA", "Préparez des réponses, idées et contenus de travail"),
            ("🌐", "Recherche Web", "Documentez un sujet ou une activité"),
            ("📄", "Analyse PDF", "Examinez des contrats et documents PDF"),
            ("🪄", "Créer un PDF", "Préparez des documents professionnels"),
            ("📁", "Mes documents", "Retrouvez vos documents sauvegardés"),
            ("🕘", "Historique", "Reprenez vos échanges précédents"),
            ("⚙️", "Paramètres", "Vérifiez votre configuration"),
            ("❓", "Aide", "Consultez les indications d’utilisation"),
        )
        notice = "" if premium_active else (
            "Aperçu de l’espace Professionnel. Le rangement Premium des documents "
            "reste verrouillé tant qu’un accès Premium actif n’est pas confirmé."
        )
        return {
            "title": "Votre espace Professionnel",
            "description": "Un espace pour préparer, analyser et organiser vos travaux et documents professionnels.",
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
