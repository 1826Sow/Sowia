"""Outils de développement commercial et de promotion internationale de SOW IA."""
from urllib.parse import urlparse


REGIONS = {
    "Monde entier": "international worldwide global",
    "Europe": "Europe European Union United Kingdom",
    "Amérique du Nord": "United States Canada North America",
    "Afrique": "Africa francophone Africa",
    "Asie-Pacifique": "Asia Pacific India Singapore Japan",
    "Moyen-Orient": "Middle East Gulf countries",
}

PARTNER_TYPES = {
    "Tous les partenaires": "technology integration agencies SaaS resellers affiliates training communities",
    "Agences numériques": "digital agencies AI consulting agencies",
    "Intégrateurs et logiciels": "software integration partners API integrations SaaS",
    "Affiliation et distribution": "affiliate program reseller program referral partners",
    "Formation et communautés": "AI training organizations professional communities",
}

LANGUAGES = ["Français", "English", "Español", "中文", "Deutsch", "العربية"]


def build_partner_search_query(region: str, partner_type: str, product: str) -> str:
    """Build a bounded, region-aware query for potential business partners."""
    region_terms = REGIONS.get(region)
    partner_terms = PARTNER_TYPES.get(partner_type)
    cleaned_product = str(product or "").strip()
    if not region_terms or not partner_terms:
        raise ValueError("Choisissez une région et un type de partenaire valides.")
    if not cleaned_product:
        raise ValueError("Décrivez brièvement SOW IA avant la prospection.")
    if len(cleaned_product) > 240:
        raise ValueError("La description de SOW IA est trop longue (240 caractères maximum).")
    return (
        f'("partner program" OR partnership OR affiliate OR reseller) '
        f'{partner_terms} {region_terms} "{cleaned_product}" '
        "official website apply contact"
    )[:500]


def normalize_partner_result(item: dict) -> dict | None:
    """Keep only linkable results with safe HTTP(S) destinations."""
    if not isinstance(item, dict):
        return None
    url = str(item.get("url") or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    title = str(item.get("title") or "Partenaire potentiel").strip()[:240]
    content = str(item.get("content") or item.get("snippet") or "").strip()[:1200]
    return {
        "title": title or "Partenaire potentiel",
        "url": url,
        "domain": parsed.netloc.lower(),
        "content": content,
    }


def build_partner_intro(language: str, partner_name: str, product: str) -> str:
    """Prepare a transparent, editable first-contact draft; never send it."""
    name = str(partner_name or "votre équipe").strip()[:120]
    description = str(product or "SOW IA, une plateforme d'assistance par intelligence artificielle").strip()[:300]
    if language == "English":
        return (
            f"Subject: Potential partnership with SOW IA\n\n"
            f"Hello {name},\n\n"
            f"I'm reaching out to explore a possible partnership. {description}. "
            "I would be glad to understand your partner program, eligibility criteria "
            "and possible collaboration models.\n\n"
            "Would you be available for a short introductory conversation?\n\n"
            "Best regards,\nSOW IA"
        )
    if language == "Español":
        return (
            f"Asunto: Posible colaboración con SOW IA\n\n"
            f"Hola, equipo de {name}:\n\n"
            f"Me gustaría explorar una posible colaboración. {description}. "
            "¿Podrían compartir sus condiciones y modalidades de colaboración?\n\n"
            "Un cordial saludo,\nSOW IA"
        )
    if language == "Deutsch":
        return (
            f"Betreff: Mögliche Partnerschaft mit SOW IA\n\n"
            f"Guten Tag, Team von {name},\n\n"
            f"ich möchte eine mögliche Partnerschaft prüfen. {description}. "
            "Könnten Sie mir Ihre Partnerbedingungen und Kooperationsmodelle mitteilen?\n\n"
            "Mit freundlichen Grüßen\nSOW IA"
        )
    if language == "中文":
        return (
            f"主题：SOW IA 合作机会\n\n"
            f"您好，{name} 团队：\n\n"
            f"我希望了解双方合作的可能性。{description}。"
            "请问贵方是否可以介绍合作计划、申请条件及合作方式？\n\n"
            "此致\nSOW IA"
        )
    if language == "العربية":
        return (
            f"الموضوع: فرصة شراكة مع SOW IA\n\n"
            f"مرحباً بفريق {name}،\n\n"
            f"أود استكشاف إمكانية التعاون. {description}. "
            "هل يمكنكم مشاركة شروط برنامج الشراكة ونماذج التعاون المتاحة؟\n\n"
            "مع خالص التحية،\nSOW IA"
        )
    return (
        f"Objet : Proposition de partenariat avec SOW IA\n\n"
        f"Bonjour à l'équipe {name},\n\n"
        f"Je souhaite étudier une éventuelle collaboration. {description}. "
        "Pourriez-vous me communiquer les conditions de votre programme partenaire "
        "et les modalités de collaboration possibles ?\n\n"
        "Seriez-vous disponible pour un bref échange de présentation ?\n\n"
        "Bien cordialement,\nSOW IA"
    )
