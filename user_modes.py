"""Session-level work modes for SOW IA.

Personnel and Professionnel change the assistant's working context only.
They are not subscription tiers and never grant Premium entitlements.
"""
MODE_OPTIONS = {
    "Personnel": "Réponses adaptées aux besoins personnels, à la vie quotidienne et aux projets individuels.",
    "Professionnel": "Réponses adaptées au travail, aux activités professionnelles, aux clients et aux livrables structurés.",
}


def normalize_user_mode(value):
    """Return a supported mode, falling back safely to Personnel."""
    return value if value in MODE_OPTIONS else "Personnel"


def mode_system_instruction(value):
    """Build a bounded, trusted instruction for the selected work mode."""
    mode = normalize_user_mode(value)
    return (
        f"MODE DE TRAVAIL ACTIF : {mode}. "
        f"{MODE_OPTIONS[mode]} "
        "Adapte le ton, les exemples et le niveau de structuration à ce contexte. "
        "Ne prétends jamais que ce mode modifie les droits d'abonnement ou les accès."
    )
