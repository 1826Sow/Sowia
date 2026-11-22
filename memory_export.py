"""Plain-text export for SOW IA memory notes."""

from collections.abc import Iterable, Mapping


def format_memory_export(memories: Iterable[Mapping], workspace_label: str) -> str:
    """Format only the supplied workspace notes as a portable UTF-8 text file."""
    label = str(workspace_label or "personnel").strip().capitalize()
    items = [
        item for item in (memories or [])
        if str(item.get("content") or "").strip()
    ]
    lines = [
        "SOW IA — Export de mémoire",
        f"Espace : {label}",
        f"Nombre de notes : {len(items)}",
        "",
    ]

    for index, item in enumerate(items, start=1):
        content = str(item.get("content") or "").strip()
        created_at = str(item.get("created_at") or "").strip()
        lines.append(f"Note {index}")
        if created_at:
            lines.append(f"Date : {created_at}")
        category = str(item.get("category") or "general").strip()
        importance = item.get("importance", 3)
        source = str(item.get("source") or "user").strip()
        tags = item.get("tags") or []
        lines.append(f"Catégorie : {category}")
        lines.append(f"Priorité : {importance}/5")
        lines.append(f"Source : {source}")
        if tags:
            lines.append("Tags : " + ", ".join(str(tag) for tag in tags))
        if item.get("project_id") is not None:
            lines.append(f"Projet ID : {item['project_id']}")
        lines.append(content)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
