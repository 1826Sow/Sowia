"""Illustrations de navigation SOW IA — visuels SVG légers et adaptatifs."""
from __future__ import annotations

import html

# Chaque page possède son propre symbole : les sous-rubriques ne réutilisent
# pas toutes la même vignette. Les illustrations sont vectorielles et locales.
PAGE_VISUALS = {
    "Hub SOWIA": ("🌐", "Centre de pilotage", "Vue d’ensemble de votre espace SOW IA"),
    "Accueil": ("✨", "Bienvenue", "Retrouvez vos outils et vos activités"),
    "Assistant IA": ("🧠", "Assistant intelligent", "Dialogue, raisonnement et accompagnement"),
    "Ma mémoire": ("💡", "Mémoire intelligente", "Retrouvez vos informations et vos repères"),
    "Recherche Web": ("🔎", "Recherche connectée", "Explorez les informations et les sources du web"),
    "Analyse PDF": ("📄", "Analyse documentaire", "Comprenez et exploitez vos documents"),
    "Créer un PDF": ("📝", "Création de documents", "Composez des PDF clairs et professionnels"),
    "Mes documents": ("🗂️", "Bibliothèque documentaire", "Vos fichiers et ressources organisés"),
    "Mes échanges & projets": ("🧭", "Échanges et projets", "Reprenez vos conversations et vos travaux"),
    "Historique": ("🕰️", "Historique", "Retrouvez le fil de vos activités"),
    "Développement mondial": ("🌍", "Développement mondial", "Ouvrez vos perspectives à l’international"),
    "SOWIA NIGHT EXCHANGE": ("🌙", "Night Exchange", "Rencontres et échanges au sein de l’écosystème"),
    "Bourse aux applications": ("📱", "Bourse aux applications", "Découvrez et partagez des applications"),
    "SOWIA GLOBAL ID": ("🪪", "Global ID", "Identité numérique au sein de l’écosystème"),
    "SOWIA GLOBAL DIRECTORY": ("📚", "Global Directory", "Annuaire et découverte des membres"),
    "SOWIA GLOBAL TRUST": ("🛡️", "Global Trust", "Confiance, sécurité et transparence"),
    "SOWIA GLOBAL ADMIN & MODERATION": ("⚖️", "Administration et modération", "Outils de contrôle et de modération"),
    "SOW IA Business Club": ("🤝", "Business Club", "Connectez les acteurs et les opportunités"),
    "Opportunités et revenus": ("📈", "Opportunités et revenus", "Suivez les pistes de développement"),
    "Technologies & fournisseurs": ("⚙️", "Technologies et fournisseurs", "Explorez les solutions et partenaires"),
    "SOWIA GLOBAL COLLABORATION HUB": ("🧩", "Collaboration Hub", "Faites avancer les projets collectifs"),
    "Décisions humaines vs SOW IA": ("⚖️", "Décisions comparées", "Analysez les options et leurs conséquences"),
    "SOWIA GLOBAL INTELLIGENCE": ("🧠", "Global Intelligence", "Transformez les signaux en compréhension"),
    "SOWIA GLOBAL PULSE": ("💓", "Global Pulse", "Suivez les tendances et les signaux"),
    "SOWIA GLOBAL STRATEGIC FORECAST": ("🔭", "Prévisions stratégiques", "Anticipez les scénarios possibles"),
    "SOWIA GLOBAL DECISION ENGINE": ("🎯", "Decision Engine", "Structurez les décisions importantes"),
    "SOWIA GLOBAL LEARNING ENGINE": ("🎓", "Learning Engine", "Apprentissage et amélioration continue"),
    "Stratégie & scénarios": ("♟️", "Stratégie et scénarios", "Préparez vos prochaines orientations"),
    "SOWIA GLOBAL AUTONOMOUS STRATEGY": ("🧭", "Stratégie autonome", "Coordonnez les objectifs et les actions"),
    "SOWIA GLOBAL ACTION GOVERNANCE": ("🏛️", "Gouvernance des actions", "Cadrez les validations et responsabilités"),
    "SOWIA GLOBAL PERFORMANCE & IMPACT": ("📊", "Performance et impact", "Mesurez les résultats et les effets"),
    "SOWIA GLOBAL PORTFOLIO CONTROL": ("🗃️", "Portfolio Control", "Pilotez votre portefeuille de projets"),
    "SOWIA GLOBAL EXECUTIVE REPORTS": ("📑", "Rapports exécutifs", "Consultez les synthèses de pilotage"),
    "Finance & investissements": ("💶", "Finance et investissements", "Suivez les indicateurs financiers"),
    "Revenus & paiements": ("💳", "Revenus et paiements", "Consultez les mouvements et règlements"),
    "Abonnement": ("⭐", "Abonnement", "Gérez votre formule et vos avantages"),
    "Centre de notifications": ("🔔", "Notifications", "Retrouvez les alertes et informations utiles"),
    "SOWIA CONTROL CENTER": ("🎛️", "Control Center", "Espace de contrôle réservé aux administrateurs"),
    "Paramètres": ("⚙️", "Paramètres", "Personnalisez votre expérience SOW IA"),
    "Aide": ("🛟", "Centre d’aide", "Guides et assistance pour utiliser SOW IA"),
}

CATEGORY_VISUALS = {
    "👤 Personnel & documents": ("👤", "#087f9b", "#174b78"),
    "📚 Échanges & projets": ("🧭", "#176f9c", "#263d79"),
    "🌐 Écosystème mondial": ("🌍", "#087f82", "#245a8e"),
    "🤝 Entreprises & opportunités": ("🤝", "#087f72", "#23577c"),
    "🧠 Intelligence & décisions": ("🧠", "#6252a2", "#176c8d"),
    "🏛️ Gouvernance & performance": ("🏛️", "#315e91", "#087b83"),
    "💶 SOWIA FINANCIAL HUB": ("💶", "#087b76", "#315b91"),
    "💳 Abonnements & compte": ("💳", "#126f9c", "#3d5591"),
    "🛡️ Administration & assistance": ("🛡️", "#285c87", "#087b83"),
}


def render_page_visual(page: str, category: str) -> str:
    """Return a compact, accessible visual banner for the selected page."""
    symbol, title, subtitle = PAGE_VISUALS.get(
        page, (CATEGORY_VISUALS.get(category, ("✨", "#087f9b", "#174b78"))[0], page, category)
    )
    category_symbol, start, end = CATEGORY_VISUALS.get(
        category, ("✨", "#087f9b", "#174b78")
    )
    safe_symbol = html.escape(symbol)
    safe_title = html.escape(title)
    safe_subtitle = html.escape(subtitle)
    safe_category = html.escape(category.replace("SOWIA", "SOW IA"))
    return f"""
    <section class="sowia-page-visual" role="img" aria-label="{safe_title} — {safe_subtitle}">
      <div class="sowia-visual-art" style="--visual-start:{start};--visual-end:{end}">
        <span class="sowia-visual-orbit sowia-orbit-one"></span>
        <span class="sowia-visual-orbit sowia-orbit-two"></span>
        <span class="sowia-visual-symbol">{safe_symbol}</span>
        <span class="sowia-visual-spark sowia-spark-one">✦</span>
        <span class="sowia-visual-spark sowia-spark-two">✧</span>
      </div>
      <div class="sowia-visual-copy">
        <div class="sowia-visual-kicker">{safe_category}</div>
        <div class="sowia-visual-title">{safe_title}</div>
        <div class="sowia-visual-subtitle">{safe_subtitle}</div>
      </div>
    </section>
    """
