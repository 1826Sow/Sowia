"""SOW IA — illustrations vectorielles cohérentes pour chaque rubrique."""
from __future__ import annotations

import base64
import html
from pathlib import Path

# Chaque destination réelle de NAV_GROUPS possède sa propre identité visuelle.
# Les rubriques déjà illustrées conservent leurs créations SVG dédiées.
PAGE_VISUALS = {
    "Hub SOWIA": ("CENTRE DE PILOTAGE", "dashboard"),
    "Accueil": ("VOTRE CENTRE DE PILOTAGE", "globe"),
    "Assistant IA": ("CONVERSATION INTELLIGENTE", "assistant"),
    "Ma mémoire": ("MÉMOIRE PERSONNELLE", "memory"),
    "Recherche Web": ("EXPLORATION & SOURCES", "search"),
    "Analyse PDF": ("ANALYSE DOCUMENTAIRE", "document"),
    "Créer un PDF": ("CRÉATION DE DOCUMENTS", "create"),
    "Mes documents": ("BIBLIOTHÈQUE DOCUMENTAIRE", "library"),
    "Mes échanges & projets": ("PROJETS & ÉCHANGES", "projects"),
    "Historique": ("CONVERSATIONS", "history"),
    "Développement mondial": ("DÉVELOPPEMENT INTERNATIONAL", "globe"),
    "SOWIA NIGHT EXCHANGE": ("ÉCOSYSTÈME MONDIAL", "network"),
    "Bourse aux applications": ("MARCHÉ NUMÉRIQUE", "market"),
    "SOWIA GLOBAL ID": ("IDENTITÉ NUMÉRIQUE", "identity"),
    "SOWIA GLOBAL DIRECTORY": ("ANNUAIRE INTERNATIONAL", "directory"),
    "SOWIA GLOBAL TRUST": ("CONFIANCE & VÉRIFICATION", "shield"),
    "SOWIA GLOBAL ADMIN & MODERATION": ("GOUVERNANCE MONDIALE", "governance"),
    "SOW IA Business Club": ("RÉSEAU PROFESSIONNEL", "business"),
    "Opportunités et revenus": ("OPPORTUNITÉS & CROISSANCE", "opportunities"),
    "Technologies & fournisseurs": ("TECHNOLOGIES & FOURNISSEURS", "technology"),
    "SOWIA GLOBAL COLLABORATION HUB": ("COLLABORATION INTERNATIONALE", "collaboration"),
    "Décisions humaines vs SOW IA": ("AIDE À LA DÉCISION", "decision"),
    "SOWIA GLOBAL INTELLIGENCE": ("INTELLIGENCE GLOBALE", "intelligence"),
    "SOWIA GLOBAL PULSE": ("SIGNAUX & TENDANCES", "pulse"),
    "SOWIA GLOBAL STRATEGIC FORECAST": ("PRÉVISIONS STRATÉGIQUES", "forecast"),
    "SOWIA GLOBAL DECISION ENGINE": ("MOTEUR DE DÉCISION", "decision"),
    "SOWIA GLOBAL LEARNING ENGINE": ("APPRENTISSAGE CONTINU", "learning"),
    "Stratégie & scénarios": ("STRATÉGIE & SCÉNARIOS", "strategy"),
    "SOWIA GLOBAL AUTONOMOUS STRATEGY": ("STRATÉGIE AUTONOME", "strategy"),
    "SOWIA GLOBAL ACTION GOVERNANCE": ("GOUVERNANCE DES ACTIONS", "governance"),
    "SOWIA GLOBAL PERFORMANCE & IMPACT": ("PERFORMANCE & IMPACT", "performance"),
    "SOWIA GLOBAL PORTFOLIO CONTROL": ("CONTRÔLE DE PORTEFEUILLE", "portfolio"),
    "SOWIA GLOBAL EXECUTIVE REPORTS": ("RAPPORTS DE DIRECTION", "reports"),
    "Finance & investissements": ("FINANCE & INVESTISSEMENTS", "finance"),
    "Revenus & paiements": ("REVENUS & PAIEMENTS", "payments"),
    "Abonnement": ("ESPACE PREMIUM", "premium"),
    "Centre de notifications": ("ALERTES & NOTIFICATIONS", "notifications"),
    "SOWIA CONTROL CENTER": ("CENTRE DE CONTRÔLE", "control"),
    "Paramètres": ("PERSONNALISATION & SÉCURITÉ", "settings"),
    "Aide": ("ASSISTANCE SOW IA", "help"),
    "Final Tech": ("VALIDATION & SÉCURITÉ", "shield"),
}

SPECIAL_ASSETS = {
    "SOWIA NIGHT EXCHANGE": "assets/sections/night-exchange.svg",
    "SOWIA GLOBAL ID": "assets/sections/global-id.svg",
    "SOWIA GLOBAL DIRECTORY": "assets/sections/global-directory.svg",
    "SOWIA GLOBAL TRUST": "assets/sections/global-trust.svg",
    "SOWIA GLOBAL INTELLIGENCE": "assets/sections/global-intelligence.svg",
    "SOWIA GLOBAL PULSE": "assets/sections/global-pulse.svg",
    "SOWIA GLOBAL STRATEGIC FORECAST": "assets/sections/global-strategic-forecast.svg",
    "SOWIA GLOBAL DECISION ENGINE": "assets/sections/global-decision-engine.svg",
    "SOW IA Business Club": "assets/sections/business-club.svg",
    "Opportunités et revenus": "assets/sections/opportunities.svg",
    "SOWIA GLOBAL COLLABORATION HUB": "assets/sections/collaboration-hub.svg",
    "Final Tech": "assets/sections/final-tech.svg",
}
HOME_HERO = "assets/sections/home-hero.svg"

_PALETTES = {
    "personnel": ("#07172d", "#0d3b58", "#36def4", "#e9c477"),
    "global": ("#050d25", "#12345b", "#36dfff", "#f0c979"),
    "business": ("#071a2d", "#17435a", "#52e4e8", "#edc77b"),
    "intelligence": ("#090e2b", "#26345e", "#7b9cff", "#f1cf83"),
    "finance": ("#071c2d", "#174b50", "#55e2c2", "#edc77b"),
    "admin": ("#08182c", "#253b57", "#55d9ef", "#e9c477"),
}
_GROUPS = {
    "CENTRE DE PILOTAGE": "personnel", "VOTRE CENTRE DE PILOTAGE": "global",
    "CONVERSATION INTELLIGENTE": "personnel", "MÉMOIRE PERSONNELLE": "personnel",
    "EXPLORATION & SOURCES": "global", "ANALYSE DOCUMENTAIRE": "personnel",
    "CRÉATION DE DOCUMENTS": "personnel", "BIBLIOTHÈQUE DOCUMENTAIRE": "personnel",
    "PROJETS & ÉCHANGES": "business", "CONVERSATIONS": "personnel",
    "DÉVELOPPEMENT INTERNATIONAL": "global", "ÉCOSYSTÈME MONDIAL": "global",
    "MARCHÉ NUMÉRIQUE": "business", "IDENTITÉ NUMÉRIQUE": "global",
    "ANNUAIRE INTERNATIONAL": "global", "CONFIANCE & VÉRIFICATION": "admin",
    "GOUVERNANCE MONDIALE": "admin", "RÉSEAU PROFESSIONNEL": "business",
    "OPPORTUNITÉS & CROISSANCE": "business", "TECHNOLOGIES & FOURNISSEURS": "intelligence",
    "COLLABORATION INTERNATIONALE": "business", "AIDE À LA DÉCISION": "intelligence",
    "INTELLIGENCE GLOBALE": "intelligence", "SIGNAUX & TENDANCES": "intelligence",
    "PRÉVISIONS STRATÉGIQUES": "intelligence", "MOTEUR DE DÉCISION": "intelligence",
    "APPRENTISSAGE CONTINU": "intelligence", "STRATÉGIE & SCÉNARIOS": "intelligence",
    "STRATÉGIE AUTONOME": "intelligence", "GOUVERNANCE DES ACTIONS": "admin",
    "PERFORMANCE & IMPACT": "business", "CONTRÔLE DE PORTEFEUILLE": "finance",
    "RAPPORTS DE DIRECTION": "intelligence", "FINANCE & INVESTISSEMENTS": "finance",
    "REVENUS & PAIEMENTS": "finance", "ESPACE PREMIUM": "business",
    "ALERTES & NOTIFICATIONS": "admin", "CENTRE DE CONTRÔLE": "admin",
    "PERSONNALISATION & SÉCURITÉ": "admin", "ASSISTANCE SOW IA": "personnel",
    "VALIDATION & SÉCURITÉ": "admin",
}
_MOTIFS = {
    "dashboard": '<rect x="-112" y="-86" width="224" height="172" rx="22" fill="#0b2947" stroke="{a}" stroke-width="3"/><path d="M-76-42H-12M-76-8H18M-76 26H-30" stroke="#d8f7ff" stroke-width="8" stroke-linecap="round"/><path d="M20 48L58 8L82 25L112-30" fill="none" stroke="{b}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>',
    "globe": '<circle r="105" fill="#0b2947" stroke="{a}" stroke-width="4"/><ellipse rx="48" ry="105" fill="none" stroke="#bcefff" stroke-width="3"/><path d="M-102 0H102M-88-55H88M-88 55H88" fill="none" stroke="{b}" stroke-width="3"/><path d="M-70-65L0-105L70-65L92 0L45 72L-45 72L-92 0Z" fill="none" stroke="{a}" stroke-width="3"/>',
    "assistant": '<path d="M-100-55Q-100-100-55-100H55Q100-100 100-55V24Q100 65 55 65H10L-45 105V65H-55Q-100 65-100 24Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><circle cx="-45" cy="-18" r="10" fill="{b}"/><circle cy="-18" r="10" fill="{b}"/><circle cx="45" cy="-18" r="10" fill="{b}"/><path d="M-45 28Q0 58 45 28" fill="none" stroke="#d8f7ff" stroke-width="5" stroke-linecap="round"/>',
    "memory": '<path d="M-78-95H38L82-50V95H-78Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M38-95V-50H82M-48-25H48M-48 10H48M-48 45H25" stroke="#d8f7ff" stroke-width="7" stroke-linecap="round"/><path d="M-5-110L8-140L21-110" fill="none" stroke="{b}" stroke-width="6"/>',
    "document": '<path d="M-78-105H36L82-58V105H-78Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M36-105V-58H82M-45-20H45M-45 16H45M-45 52H20" stroke="#d8f7ff" stroke-width="7" stroke-linecap="round"/><circle cx="48" cy="52" r="28" fill="#0b2947" stroke="{b}" stroke-width="5"/>',
    "create": '<path d="M-80-95H42L80-56V95H-80Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M42-95V-56H80M-48-20H36M-48 15H24" stroke="#d8f7ff" stroke-width="7" stroke-linecap="round"/><path d="M10 80L80 10L102 32L32 102Z" fill="{b}" stroke="#fff" stroke-width="3"/>',
    "library": '<path d="M-100-82H100V92H-100Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M-65-82V92M-5-82V92M55-82V92" stroke="{b}" stroke-width="9"/><path d="M-82-45H-28M-82-12H-28M-82 22H-28" stroke="#d8f7ff" stroke-width="5"/>',
    "projects": '<path d="M-110-58H-25L-5-82H110V82H-110Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M-62-5L-20 35L52-38" fill="none" stroke="{b}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><circle cx="65" cy="54" r="19" fill="#0b2947" stroke="#e9c477" stroke-width="5"/>',
    "history": '<circle r="93" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M0-56V4L45 30" fill="none" stroke="{b}" stroke-width="10" stroke-linecap="round"/><path d="M-100-5L-125-35L-135 10" fill="none" stroke="#d8f7ff" stroke-width="7"/>',
    "network": '<circle r="35" fill="#0b2947" stroke="{a}" stroke-width="5"/><g fill="#0b2947" stroke="{b}" stroke-width="5"><circle cx="-105" cy="-65" r="25"/><circle cx="110" cy="-70" r="25"/><circle cx="-110" cy="72" r="25"/><circle cx="105" cy="78" r="25"/></g><path d="M-80-55L-30-18M80-55L30-18M-82 58L-30 18M80 62L30 18" stroke="#d8f7ff" stroke-width="5"/>',
    "market": '<path d="M-100-28H100L80-92H-80Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-82-28V95H82V-28M-25 95V22H25V95" fill="#0b2947" stroke="{b}" stroke-width="6"/><path d="M-110-28Q-100 12-65-10Q-30 15 0-10Q35 15 65-10Q100 12 110-28" fill="none" stroke="#d8f7ff" stroke-width="6"/>',
    "identity": '<circle r="96" fill="#0b2947" stroke="{a}" stroke-width="5"/><circle cy="-30" r="30" fill="none" stroke="{b}" stroke-width="7"/><path d="M-58 65Q-50 8 0 8Q50 8 58 65" fill="none" stroke="#d8f7ff" stroke-width="8"/><path d="M-120-100L-80-125M120-100L80-125" stroke="{b}" stroke-width="5"/>',
    "directory": '<path d="M-105-90H105V90H-105Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><g fill="none" stroke="{b}" stroke-width="5"><circle cx="-55" cy="-38" r="18"/><circle cx="0" cy="-38" r="18"/><circle cx="55" cy="-38" r="18"/></g><path d="M-82 30H82M-82 60H48" stroke="#d8f7ff" stroke-width="7" stroke-linecap="round"/>',
    "shield": '<path d="M0-120L100-80V8Q90 85 0 125Q-90 85-100 8V-80Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-48 0L-10 40L58-42" fill="none" stroke="{b}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>',
    "governance": '<path d="M-100 75H100M-80 30H80M-60-15H60M-40-60H40" stroke="{a}" stroke-width="10" stroke-linecap="round"/><path d="M0-105V90" stroke="{b}" stroke-width="7"/><circle r="17" fill="#e9c477"/>',
    "business": '<path d="M-105-55H105V90H-105Z" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M-45-55V-88H45V-55M-105-8H105M-20-8V10H20V-8" fill="none" stroke="{b}" stroke-width="7"/>',
    "opportunities": '<path d="M-100 85L-45 25L-5 50L70-45" fill="none" stroke="{b}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M35-45H70V-10" fill="none" stroke="#d8f7ff" stroke-width="8"/><circle cx="-100" cy="85" r="12" fill="#e9c477"/>',
    "technology": '<rect x="-90" y="-90" width="180" height="180" rx="24" fill="#0b2947" stroke="{a}" stroke-width="5"/><rect x="-48" y="-48" width="96" height="96" rx="12" fill="none" stroke="{b}" stroke-width="7"/><path d="M-120 0H-90M90 0H120M0-120V-90M0 90V120M-82-82L-60-60M82 82L60 60M82-82L60-60M-82 82L-60 60" stroke="#d8f7ff" stroke-width="6"/>',
    "collaboration": '<circle cx="-65" cy="-30" r="28" fill="#0b2947" stroke="{a}" stroke-width="5"/><circle cx="65" cy="-30" r="28" fill="#0b2947" stroke="{b}" stroke-width="5"/><circle cy="65" r="28" fill="#0b2947" stroke="#e9c477" stroke-width="5"/><path d="M-40-12L-12 38M40-12L12 38M-36-30H36" stroke="#d8f7ff" stroke-width="6"/>',
    "decision": '<path d="M0-112L95-55V55L0 112L-95 55V-55Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-52 0H-12L12-42L48 42" fill="none" stroke="{b}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>',
    "intelligence": '<circle r="100" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M-65-10Q-75-72-18-72Q0-112 30-72Q85-75 68-10Q100 42 45 60Q10 110-20 65Q-80 70-65-10Z" fill="none" stroke="{b}" stroke-width="6"/><path d="M0-65V65M-50-20H50M-45 30H45" stroke="#d8f7ff" stroke-width="4"/>',
    "pulse": '<path d="M-120 10H-70L-40-45L0 72L38-22L62 10H120" fill="none" stroke="{b}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/><circle r="115" fill="none" stroke="{a}" stroke-width="4" stroke-dasharray="8 14"/>',
    "forecast": '<path d="M-105 80V-80M-105 80H110" stroke="#d8f7ff" stroke-width="6"/><path d="M-90 55L-48 18L-8 30L38-32L95-80" fill="none" stroke="{b}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/><path d="M60-80H95V-45" fill="none" stroke="{a}" stroke-width="7"/>',
    "learning": '<path d="M-100-60Q-45-100 0-60Q45-100 100-60V70Q45 30 0 70Q-45 30-100 70Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M0-60V70M-68-20L-25-5M68-20L25-5" stroke="{b}" stroke-width="6"/>',
    "strategy": '<path d="M-100 75L-30-65L20 10L75-90L110 75Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-30-65L-10-15L75-90" fill="none" stroke="{b}" stroke-width="8"/><circle cx="75" cy="-90" r="12" fill="#e9c477"/>',
    "performance": '<path d="M-105 85V-20H-55V85M-25 85V-70H25V85M55 85V-110H105V85" fill="#0b2947" stroke="{a}" stroke-width="4"/><path d="M-115 95H115" stroke="{b}" stroke-width="7"/>',
    "portfolio": '<rect x="-105" y="-85" width="210" height="170" rx="20" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-68-42H68M-68-5H35M-68 32H52" stroke="{b}" stroke-width="8" stroke-linecap="round"/><circle cx="70" cy="50" r="22" fill="#0b2947" stroke="#e9c477" stroke-width="5"/>',
    "reports": '<path d="M-82-100H40L82-58V100H-82Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M40-100V-58H82M-48-22H48M-48 14H48M-48 50H20" stroke="#d8f7ff" stroke-width="7" stroke-linecap="round"/><path d="M-48 82L-15 60L10 74L45 38" fill="none" stroke="{b}" stroke-width="6"/>',
    "finance": '<circle r="96" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M0-58V58M35-30Q25-58-10-58Q-55-58-55-20Q-55 8 0 14Q55 20 55 48Q55 62 15 62Q-25 62-42 38" fill="none" stroke="{b}" stroke-width="9" stroke-linecap="round"/>',
    "payments": '<rect x="-110" y="-70" width="220" height="140" rx="20" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-110-25H110M-70 25H-20" stroke="{b}" stroke-width="12" stroke-linecap="round"/><circle cx="62" cy="30" r="18" fill="#e9c477"/>',
    "premium": '<path d="M0-115L30-40L110-35L48 15L68 100L0 55L-68 100L-48 15L-110-35L-30-40Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><circle r="24" fill="{b}"/>',
    "notifications": '<path d="M-78 55H78L58 30V-28Q58-80 0-80Q-58-80-58-28V30Z" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-25 75Q0 110 25 75" fill="none" stroke="{b}" stroke-width="8"/><circle cx="65" cy="-70" r="18" fill="#e9c477"/>',
    "control": '<circle r="102" fill="#0b2947" stroke="{a}" stroke-width="5"/><circle r="65" fill="none" stroke="{b}" stroke-width="8"/><circle r="25" fill="#e9c477"/><path d="M0-135V-105M0 105V135M-135 0H-105M105 0H135" stroke="#d8f7ff" stroke-width="8"/>',
    "settings": '<circle r="48" fill="#0b2947" stroke="{a}" stroke-width="8"/><circle r="17" fill="{b}"/><path d="M-12-118L12-118L20-85L45-75L72-95L92-78L78-48L88-22L120-12L120 12L88 22L78 48L92 78L72 95L45 75L20 85L12 118L-12 118L-20 85L-45 75L-72 95L-92 78L-78 48L-88 22L-120 12L-120-12L-88-22L-78-48L-92-78L-72-95L-45-75L-20-85Z" fill="none" stroke="{b}" stroke-width="6"/>',
    "help": '<circle r="100" fill="#0b2947" stroke="{a}" stroke-width="5"/><path d="M-32-30Q-25-75 20-70Q65-65 60-25Q58-5 25 15Q0 30 0 52" fill="none" stroke="{b}" stroke-width="12" stroke-linecap="round"/><circle cy="80" r="8" fill="#e9c477"/>',
}

def _generated_svg(page_name: str) -> str:
    section, motif = PAGE_VISUALS.get(page_name, ("ESPACE SOW IA", "dashboard"))
    group = _GROUPS.get(section, "global")
    bg1, bg2, cyan, gold = _PALETTES[group]
    title = html.escape(str(page_name).replace("SOWIA", "SOW IA").upper())
    kicker = html.escape(section)
    motif_markup = _MOTIFS.get(motif, _MOTIFS["dashboard"]).format(a=cyan, b=gold)
    title_size = 46 if len(title) > 27 else 56 if len(title) > 20 else 66
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360" role="img" aria-label="SOW IA — {title}">
<defs>
 <linearGradient id="bg" x2="1" y2="1"><stop stop-color="{bg1}"/><stop offset=".58" stop-color="{bg2}"/><stop offset="1" stop-color="#061426"/></linearGradient>
 <radialGradient id="aura"><stop stop-color="{cyan}" stop-opacity=".3"/><stop offset="1" stop-color="{cyan}" stop-opacity="0"/></radialGradient>
 <pattern id="grid" width="42" height="42" patternUnits="userSpaceOnUse"><path d="M42 0H0V42" fill="none" stroke="{cyan}" stroke-opacity=".09"/></pattern>
 <filter id="glow"><feGaussianBlur stdDeviation="22"/></filter>
</defs>
<rect width="1200" height="360" rx="28" fill="url(#bg)"/><rect width="1200" height="360" rx="28" fill="url(#grid)"/>
<ellipse cx="930" cy="180" rx="280" ry="220" fill="url(#aura)"/><circle cx="930" cy="180" r="160" fill="{cyan}" opacity=".09" filter="url(#glow)"/>
<g transform="translate(930 180)"><circle r="145" fill="none" stroke="{cyan}" stroke-opacity=".48" stroke-width="2" stroke-dasharray="4 13"/><ellipse rx="172" ry="78" transform="rotate(-28)" fill="none" stroke="{gold}" stroke-width="2" opacity=".75"/>{motif_markup}</g>
<path d="M630 65L720 110L760 170M650 295L735 250L770 210M1080 70L1150 112M1080 290L1150 248" fill="none" stroke="{cyan}" stroke-opacity=".38" stroke-width="2"/>
<g fill="{gold}"><circle cx="630" cy="65" r="5"/><circle cx="650" cy="295" r="5"/><circle cx="1150" cy="112" r="5"/><circle cx="1150" cy="248" r="5"/></g>
<text x="72" y="86" fill="{gold}" font-family="Arial,sans-serif" font-size="18" font-weight="700" letter-spacing="5">{kicker}</text>
<text x="68" y="170" fill="#f4fbff" font-family="Arial,sans-serif" font-size="{title_size}" font-weight="800" letter-spacing=".5">{title}</text>
<path d="M74 204H500" stroke="{cyan}" stroke-width="3"/>
<text x="74" y="252" fill="#d3eafa" font-family="Arial,sans-serif" font-size="22">Un espace dédié pour explorer, créer et avancer.</text>
<text x="74" y="300" fill="#8fcddd" font-family="Arial,sans-serif" font-size="14" letter-spacing="3">SOW IA  ·  INTELLIGENCE EN ACTION</text>
</svg>'''

def render_page_visual(page_name: str) -> str:
    """Return an accessible, responsive SVG banner for the selected rubrique."""
    safe_name = html.escape(str(page_name).replace("SOWIA", "SOW IA"))
    asset_path = HOME_HERO if page_name == "Accueil" else SPECIAL_ASSETS.get(page_name)
    if asset_path:
        try:
            svg = Path(asset_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            svg = _generated_svg(page_name)
    else:
        svg = _generated_svg(page_name)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        '<div class="sowia-page-visual" style="width:100%;margin:.25rem 0 1rem;'
        'overflow:hidden;border-radius:20px;border:1px solid rgba(75,220,240,.25);'
        'box-shadow:0 14px 36px rgba(0,0,0,.24);">'
        f'<img src="data:image/svg+xml;base64,{encoded}" alt="Illustration de la rubrique {safe_name}" '
        'style="display:block;width:100%;height:auto;max-height:390px;object-fit:cover;" />'
        '</div>'
    )
