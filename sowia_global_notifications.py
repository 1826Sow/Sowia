"""Localized labels for SOWIA GLOBAL NOTIFICATIONS."""

SUPPORTED_LANGUAGES = ("fr", "en", "es", "pt", "zh", "ar")

MESSAGES = {
    "fr": {
        "connection_request_received": "Nouvelle demande de mise en relation",
        "connection_request_accepted": "Votre demande de mise en relation a été acceptée",
        "connection_request_declined": "Votre demande de mise en relation a été refusée",
        "new_message": "Vous avez reçu un nouveau message",
        "title": "Notifications SOWIA",
        "empty": "Aucune notification pour le moment.",
        "mark_all": "Tout marquer comme lu",
        "unread": "Non lue",
        "read": "Lue",
        "language": "Langue des notifications",
        "enabled": "Activer les notifications dans SOWIA",
    },
    "en": {
        "connection_request_received": "New connection request",
        "connection_request_accepted": "Your connection request was accepted",
        "connection_request_declined": "Your connection request was declined",
        "new_message": "You received a new message",
        "title": "SOWIA notifications",
        "empty": "No notifications yet.",
        "mark_all": "Mark all as read",
        "unread": "Unread",
        "read": "Read",
        "language": "Notification language",
        "enabled": "Enable in-app notifications",
    },
    "es": {
        "connection_request_received": "Nueva solicitud de contacto",
        "connection_request_accepted": "Tu solicitud de contacto fue aceptada",
        "connection_request_declined": "Tu solicitud de contacto fue rechazada",
        "new_message": "Has recibido un mensaje nuevo",
        "title": "Notificaciones SOWIA",
        "empty": "Todavía no hay notificaciones.",
        "mark_all": "Marcar todo como leído",
        "unread": "No leída",
        "read": "Leída",
        "language": "Idioma de notificaciones",
        "enabled": "Activar notificaciones en la aplicación",
    },
    "pt": {
        "connection_request_received": "Novo pedido de conexão",
        "connection_request_accepted": "Seu pedido de conexão foi aceito",
        "connection_request_declined": "Seu pedido de conexão foi recusado",
        "new_message": "Você recebeu uma nova mensagem",
        "title": "Notificações SOWIA",
        "empty": "Ainda não há notificações.",
        "mark_all": "Marcar tudo como lido",
        "unread": "Não lida",
        "read": "Lida",
        "language": "Idioma das notificações",
        "enabled": "Ativar notificações no aplicativo",
    },
    "zh": {
        "connection_request_received": "收到新的合作联系请求",
        "connection_request_accepted": "您的联系请求已获接受",
        "connection_request_declined": "您的联系请求已被拒绝",
        "new_message": "您收到一条新消息",
        "title": "SOWIA 通知",
        "empty": "暂时没有通知。",
        "mark_all": "全部标记为已读",
        "unread": "未读",
        "read": "已读",
        "language": "通知语言",
        "enabled": "启用应用内通知",
    },
    "ar": {
        "connection_request_received": "طلب تواصل جديد",
        "connection_request_accepted": "تم قبول طلب التواصل الخاص بك",
        "connection_request_declined": "تم رفض طلب التواصل الخاص بك",
        "new_message": "تلقيت رسالة جديدة",
        "title": "إشعارات SOWIA",
        "empty": "لا توجد إشعارات حالياً.",
        "mark_all": "تحديد الكل كمقروء",
        "unread": "غير مقروء",
        "read": "مقروء",
        "language": "لغة الإشعارات",
        "enabled": "تفعيل الإشعارات داخل التطبيق",
    },
}


def translate(event_type, language="fr"):
    locale = language if language in MESSAGES else "fr"
    return MESSAGES[locale].get(event_type, MESSAGES[locale]["title"])


def safe_notification_projection(record):
    if not isinstance(record, dict):
        return {}
    allowed = ("id", "event_type", "reference_id", "created_at", "read_at")
    return {key: record[key] for key in allowed if key in record}
