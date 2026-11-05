"""Private persistent history for SOW IA document comparisons."""
import json
from datetime import datetime, timezone

from storage import _connect


def _user_id(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def _serialize(report):
    if not isinstance(report, dict) or not isinstance(report.get("comparison"), dict):
        raise ValueError("Rapport de comparaison invalide.")
    payload = json.dumps(report, ensure_ascii=False)
    if len(payload) > 250000:
        raise ValueError("Le rapport dépasse la taille autorisée.")
    return payload


def save_local(report):
    payload = _serialize(report)
    created_at = str(report.get("created_at") or datetime.now(timezone.utc).isoformat())
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS comparison_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        cursor = conn.execute(
            "INSERT INTO comparison_history(payload, created_at) VALUES(?, ?)",
            (payload, created_at),
        )
        conn.execute(
            "DELETE FROM comparison_history WHERE id NOT IN "
            "(SELECT id FROM comparison_history ORDER BY id DESC LIMIT 100)"
        )
        return cursor.lastrowid


def list_local(limit=50):
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS comparison_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        rows = conn.execute(
            "SELECT id, payload, created_at FROM comparison_history ORDER BY id DESC LIMIT ?",
            (min(max(int(limit), 1), 100),),
        ).fetchall()
    return [{"id": row[0], "report": json.loads(row[1]), "created_at": row[2]} for row in rows]


def get_local(report_id):
    if isinstance(report_id, bool) or not str(report_id).isdecimal() or int(report_id) <= 0:
        raise ValueError("Identifiant de rapport invalide.")
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, payload, created_at FROM comparison_history WHERE id=?",
            (int(report_id),),
        ).fetchone()
    return {"id": row[0], "report": json.loads(row[1]), "created_at": row[2]} if row else None


def delete_local(report_id):
    if isinstance(report_id, bool) or not str(report_id).isdecimal() or int(report_id) <= 0:
        raise ValueError("Identifiant de rapport invalide.")
    with _connect() as conn:
        conn.execute("DELETE FROM comparison_history WHERE id=?", (int(report_id),))


def save_cloud(client, user, report):
    user_id = user_id
    payload = _serialize(report)
    return client.table("sowia_comparison_history").insert({
        "user_id": user_id,
        "report": json.loads(payload),
    }).execute().data


def list_cloud(client, user, limit=50):
    user_id = user_id
    return (client.table("sowia_comparison_history")
        .select("id, report, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(min(max(int(limit), 1), 100)).execute().data)


def get_cloud(client, user, report_id):
    user_id = user_id
    if isinstance(report_id, bool) or not str(report_id).isdecimal() or int(report_id) <= 0:
        raise ValueError("Identifiant de rapport invalide.")
    rows = (client.table("sowia_comparison_history")
        .select("id, report, created_at")
        .eq("user_id", user_id).eq("id", int(report_id))
        .limit(1).execute().data)
    return rows[0] if rows else None


def delete_cloud(client, user, report_id):
    user_id = user_id
    if isinstance(report_id, bool) or not str(report_id).isdecimal() or int(report_id) <= 0:
        raise ValueError("Identifiant de rapport invalide.")
    return (client.table("sowia_comparison_history").delete()
        .eq("user_id", user_id).eq("id", int(report_id)).execute())
