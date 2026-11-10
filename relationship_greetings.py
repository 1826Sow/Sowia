"""Culturally aware relationship greetings for SOW IA.

This module drafts messages only. It never sends email, SMS, or social messages.
"""
from __future__ import annotations

from datetime import date

SUPPORTED_LANGUAGES = ("Français", "English", "Español", "中文", "Deutsch", "العربية")

COUNTRY_DEFAULTS = {
    "France": ("Français", "14 juillet"),
    "Belgique": ("Français", "21 juillet"),
    "Suisse": ("Français", "1er août"),
    "Canada": ("English", "1er juillet"),
    "United States": ("English", "4 juillet"),
    "United Kingdom": ("English", "second Saturday of June"),
    "Ireland": ("English", "17 mars"),
    "Spain": ("Español", "12 octobre"),
    "Mexico": ("Español", "16 septembre"),
    "Germany": ("Deutsch", "3 octobre"),
    "Austria": ("Deutsch", "26 octobre"),
    "China": ("中文", "1er octobre"),
    "Japan": ("English", "11 février"),
    "Singapore": ("English", "9 août"),
    "United Arab Emirates": ("العربية", "2 décembre"),
    "Saudi Arabia": ("العربية", "23 septembre"),
    "Morocco": ("العربية", "30 juillet"),
    "Senegal": ("Français", "4 avril"),
    "Côte d’Ivoire": ("Français", "7 août"),
}

OCCASIONS = (
    "Anniversaire personnel",
    "Anniversaire de l'entreprise",
    "Nouvel An",
    "Noël",
    "Fête nationale",
    "Fête de fin de Ramadan / Aïd el-Fitr",
    "Aïd el-Adha",
    "Nouvel An lunaire",
    "Diwali",
    "Remerciement / partenariat",
    "Félicitations professionnelles",
    "Message de bienvenue",
)

def default_language(country: str) -> str:
    return COUNTRY_DEFAULTS.get(str(country or "").strip(), ("English", ""))[0]


def national_day(country: str) -> str:
    return COUNTRY_DEFAULTS.get(str(country or "").strip(), ("", "Date à confirmer localement"))[1]


def _copy(language: str, occasion: str, name: str, company: str, country: str) -> str:
    recipient = str(name or "à toute votre équipe").strip()[:100]
    organization = str(company or "").strip()[:120]
    destination = f" de {organization}" if organization else ""
    messages = {
        "Français": {
            "Anniversaire personnel": f"Joyeux anniversaire, {recipient} ! Toute l’équipe SOW IA vous souhaite une très belle journée, remplie de joie et de beaux projets.",
            "Anniversaire de l'entreprise": f"Joyeux anniversaire{destination} ! SOW IA vous adresse ses félicitations et vous souhaite une nouvelle année de réussite et d’innovation.",
            "Nouvel An": f"Très belle année ! SOW IA vous adresse ses meilleurs vœux de santé, de réussite et de belles collaborations pour cette nouvelle année.",
            "Noël": f"Joyeux Noël, {recipient} ! SOW IA vous souhaite de belles fêtes, chaleureuses et sereines, à vous et à vos proches.",
            "Fête nationale": f"À l’occasion de la fête nationale de {country}, SOW IA adresse ses meilleurs vœux à votre équipe et à toutes celles et ceux qui célèbrent cette journée.",
            "Fête de fin de Ramadan / Aïd el-Fitr": f"Aïd Moubarak ! SOW IA vous adresse ses vœux les plus chaleureux de paix, de santé et de prospérité, à vous et à vos proches.",
            "Aïd el-Adha": f"Aïd Moubarak ! Que cette fête soit placée sous le signe du partage, de la paix et de la générosité. Avec les meilleurs vœux de SOW IA.",
            "Nouvel An lunaire": f"Belle célébration du Nouvel An lunaire ! SOW IA vous souhaite bonheur, santé et prospérité pour cette nouvelle année.",
            "Diwali": f"Joyeux Diwali ! Que cette fête des lumières vous apporte joie, paix et prospérité. Meilleurs vœux de la part de SOW IA.",
            "Remerciement / partenariat": f"Bonjour {recipient}, SOW IA vous remercie sincèrement pour votre confiance et la qualité de nos échanges. Au plaisir de poursuivre cette collaboration{destination}.",
            "Félicitations professionnelles": f"Félicitations, {recipient} ! Toute l’équipe SOW IA vous souhaite beaucoup de succès dans cette nouvelle étape.",
            "Message de bienvenue": f"Bienvenue, {recipient} ! SOW IA est heureuse de vous compter parmi ses contacts et vous souhaite une excellente expérience.",
        },
        "English": {
            "Anniversaire personnel": f"Happy birthday, {recipient}! Everyone at SOW IA wishes you a wonderful day and a year filled with happiness and new opportunities.",
            "Anniversaire de l'entreprise": f"Happy anniversary{destination}! SOW IA sends its congratulations and wishes your team continued growth, innovation and success.",
            "Nouvel An": "Wishing you a happy New Year! May it bring health, success and meaningful new opportunities. Best wishes from SOW IA.",
            "Noël": f"Merry Christmas, {recipient}! Wishing you and your loved ones a peaceful and joyful holiday season.",
            "Fête nationale": f"Warm wishes to your team and everyone celebrating the national day of {country}. Best regards from SOW IA.",
            "Fête de fin de Ramadan / Aïd el-Fitr": "Eid Mubarak! May this celebration bring peace, good health and prosperity to you and your loved ones. Best wishes from SOW IA.",
            "Aïd el-Adha": "Eid Mubarak! Wishing you and your loved ones a celebration filled with peace, generosity and togetherness.",
            "Nouvel An lunaire": "Happy Lunar New Year! Wishing you health, happiness and prosperity in the year ahead.",
            "Diwali": "Happy Diwali! May the festival of lights bring joy, peace and prosperity to you and your family.",
            "Remerciement / partenariat": f"Hello {recipient}, thank you for your trust and the quality of our conversations. SOW IA looks forward to continuing our relationship{destination}.",
            "Félicitations professionnelles": f"Congratulations, {recipient}! Everyone at SOW IA wishes you every success in this exciting new chapter.",
            "Message de bienvenue": f"Welcome, {recipient}! SOW IA is pleased to connect with you and wishes you a great experience.",
        },
        "Español": {
            "Anniversaire personnel": f"¡Feliz cumpleaños, {recipient}! Todo el equipo de SOW IA te desea un día maravilloso y un año lleno de alegría y nuevos proyectos.",
            "Anniversaire de l'entreprise": f"¡Feliz aniversario{destination}! SOW IA les desea crecimiento, innovación y muchos éxitos.",
            "Nouvel An": "¡Feliz Año Nuevo! Que este año traiga salud, prosperidad y nuevas oportunidades. Los mejores deseos de SOW IA.",
            "Noël": f"¡Feliz Navidad, {recipient}! Te deseamos a ti y a tus seres queridos unas fiestas llenas de paz y alegría.",
            "Fête nationale": f"Nuestros mejores deseos a tu equipo y a todas las personas que celebran el día nacional de {country}.",
            "Fête de fin de Ramadan / Aïd el-Fitr": "¡Eid Mubarak! Que esta celebración traiga paz, salud y prosperidad a ti y a tus seres queridos.",
            "Aïd el-Adha": "¡Eid Mubarak! Que esta festividad esté llena de generosidad, paz y unión.",
            "Nouvel An lunaire": "¡Feliz Año Nuevo Lunar! Te deseamos salud, felicidad y prosperidad.",
            "Diwali": "¡Feliz Diwali! Que el festival de las luces te traiga alegría, paz y prosperidad.",
            "Remerciement / partenariat": f"Hola {recipient}, gracias por tu confianza y por la calidad de nuestros intercambios. SOW IA espera seguir colaborando{destination}.",
            "Félicitations professionnelles": f"¡Enhorabuena, {recipient}! Todo el equipo de SOW IA te desea mucho éxito en esta nueva etapa.",
            "Message de bienvenue": f"¡Bienvenido/a, {recipient}! SOW IA se alegra de conectar contigo y te desea una excelente experiencia.",
        },
        "Deutsch": {
            "Anniversaire personnel": f"Alles Gute zum Geburtstag, {recipient}! Das Team von SOW IA wünscht Ihnen einen wundervollen Tag und ein erfolgreiches neues Lebensjahr.",
            "Anniversaire de l'entreprise": f"Herzlichen Glückwunsch zum Firmenjubiläum{destination}! SOW IA wünscht Ihrem Team weiterhin viel Erfolg und Innovation.",
            "Nouvel An": "Ein frohes neues Jahr! Wir wünschen Ihnen Gesundheit, Erfolg und viele neue Möglichkeiten. Ihre SOW IA.",
            "Noël": f"Frohe Weihnachten, {recipient}! Wir wünschen Ihnen und Ihren Lieben ein friedliches und schönes Fest.",
            "Fête nationale": f"Herzliche Grüße an Ihr Team und alle, die den Nationalfeiertag von {country} begehen.",
            "Fête de fin de Ramadan / Aïd el-Fitr": "Eid Mubarak! Wir wünschen Ihnen und Ihren Angehörigen Frieden, Gesundheit und Wohlstand.",
            "Aïd el-Adha": "Eid Mubarak! Möge dieses Fest von Frieden, Großzügigkeit und Zusammenhalt geprägt sein.",
            "Nouvel An lunaire": "Frohes Mondneujahr! Wir wünschen Ihnen Gesundheit, Glück und Wohlstand.",
            "Diwali": "Frohes Diwali! Möge das Lichterfest Ihnen Freude, Frieden und Wohlstand bringen.",
            "Remerciement / partenariat": f"Guten Tag {recipient}, vielen Dank für Ihr Vertrauen und den wertvollen Austausch. SOW IA freut sich auf die weitere Zusammenarbeit{destination}.",
            "Félicitations professionnelles": f"Herzlichen Glückwunsch, {recipient}! Das Team von SOW IA wünscht Ihnen viel Erfolg für diesen neuen Abschnitt.",
            "Message de bienvenue": f"Herzlich willkommen, {recipient}! SOW IA freut sich auf den Austausch mit Ihnen.",
        },
        "中文": {
            "Anniversaire personnel": f"{recipient}，生日快乐！SOW IA 团队祝您度过美好的一天，并在新的一岁收获幸福与成功。",
            "Anniversaire de l'entreprise": f"祝贺{organization or '贵公司'}周年纪念！SOW IA 祝愿贵团队持续创新、蓬勃发展。",
            "Nouvel An": "新年快乐！SOW IA 祝您身体健康、事业顺利，并迎来更多合作机遇。",
            "Noël": f"{recipient}，圣诞快乐！SOW IA 祝您和家人节日平安、温馨愉快。",
            "Fête nationale": f"值此{country}国庆日，SOW IA 向贵团队及所有庆祝这一节日的人们致以诚挚祝福。",
            "Fête de fin de Ramadan / Aïd el-Fitr": "开斋节吉庆！SOW IA 祝您和家人平安、健康、幸福。",
            "Aïd el-Adha": "古尔邦节吉庆！愿节日带来和平、分享与美好。",
            "Nouvel An lunaire": "新春快乐！祝您新的一年身体健康、万事如意、事业兴旺。",
            "Diwali": "排灯节快乐！愿光明与喜悦伴随您和家人，带来和平与繁荣。",
            "Remerciement / partenariat": f"{recipient}，感谢您的信任与交流。SOW IA 期待继续推进双方合作{destination}。",
            "Félicitations professionnelles": f"{recipient}，恭喜您取得新的成就！SOW IA 祝愿您未来一切顺利。",
            "Message de bienvenue": f"欢迎您，{recipient}！SOW IA 很高兴与您建立联系。",
        },
        "العربية": {
            "Anniversaire personnel": f"عيد ميلاد سعيد، {recipient}! يتمنى لكم فريق SOW IA يوماً جميلاً وعاماً مليئاً بالسعادة والنجاح.",
            "Anniversaire de l'entreprise": f"نهنئ{destination} بذكرى تأسيسها، ونتمنى لفريقكم دوام النمو والابتكار والنجاح. مع تحيات SOW IA.",
            "Nouvel An": "كل عام وأنتم بخير! نتمنى لكم عاماً جديداً مليئاً بالصحة والنجاح والفرص الواعدة. تحيات SOW IA.",
            "Noël": f"عيد ميلاد مجيد، {recipient}! نتمنى لكم ولأحبائكم أعياداً هادئة وسعيدة.",
            "Fête nationale": f"أطيب التهاني لفريقكم ولكل من يحتفل باليوم الوطني في {country}. مع تحيات SOW IA.",
            "Fête de fin de Ramadan / Aïd el-Fitr": "عيد مبارك! نسأل لكم ولأحبابكم السلام والصحة والازدهار.",
            "Aïd el-Adha": "عيد أضحى مبارك! أعاده الله عليكم بالخير والسلام والتآلف.",
            "Nouvel An lunaire": "عام قمري سعيد! نتمنى لكم الصحة والسعادة والازدهار.",
            "Diwali": "ديوالي سعيد! نتمنى لكم ولعائلاتكم الفرح والسلام والازدهار.",
            "Remerciement / partenariat": f"مرحباً {recipient}، نشكركم على ثقتكم وجودة التواصل. يتطلع SOW IA إلى مواصلة التعاون{destination}.",
            "Félicitations professionnelles": f"تهانينا {recipient}! يتمنى لكم فريق SOW IA كل النجاح في هذه المرحلة الجديدة.",
            "Message de bienvenue": f"أهلاً وسهلاً بكم {recipient}! يسعد SOW IA بالتواصل معكم.",
        },
    }
    if occasion not in OCCASIONS:
        raise ValueError("Occasion non prise en charge.")
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Langue non prise en charge.")
    return messages[language][occasion]


def build_greeting(language: str, occasion: str, contact_name: str = "",
                  organization: str = "", country: str = "") -> str:
    """Build a ready-to-review greeting in the selected language."""
    body = _copy(language, occasion, contact_name, organization, country or "votre pays")
    signoffs = {
        "Français": "Bien cordialement,\nL’équipe SOW IA",
        "English": "Warm regards,\nThe SOW IA team",
        "Español": "Un cordial saludo,\nEl equipo de SOW IA",
        "Deutsch": "Mit freundlichen Grüßen,\nDas SOW IA Team",
        "中文": "此致\nSOW IA 团队",
        "العربية": "مع أطيب التحيات،\nفريق SOW IA",
    }
    return f"{body}\n\n{signoffs[language]}"


def upcoming_fixed_occasions(country: str, year: int | None = None) -> list[dict]:
    """Return the basic fixed-date calendar. Movable holidays require verified local dates."""
    year = year or date.today().year
    result = [{"occasion": "Nouvel An", "date": date(year, 1, 1).isoformat()}]
    result.append({"occasion": "Noël", "date": date(year, 12, 25).isoformat()})
    day = national_day(country)
    if day == "14 juillet":
        result.append({"occasion": "Fête nationale", "date": date(year, 7, 14).isoformat()})
    elif day == "21 juillet":
        result.append({"occasion": "Fête nationale", "date": date(year, 7, 21).isoformat()})
    elif day == "1er août":
        result.append({"occasion": "Fête nationale", "date": date(year, 8, 1).isoformat()})
    elif day == "1er juillet":
        result.append({"occasion": "Fête nationale", "date": date(year, 7, 1).isoformat()})
    elif day == "4 juillet":
        result.append({"occasion": "Fête nationale", "date": date(year, 7, 4).isoformat()})
    elif day == "12 octobre":
        result.append({"occasion": "Fête nationale", "date": date(year, 10, 12).isoformat()})
    elif day == "16 septembre":
        result.append({"occasion": "Fête nationale", "date": date(year, 9, 16).isoformat()})
    elif day == "3 octobre":
        result.append({"occasion": "Fête nationale", "date": date(year, 10, 3).isoformat()})
    elif day == "26 octobre":
        result.append({"occasion": "Fête nationale", "date": date(year, 10, 26).isoformat()})
    elif day == "11 février":
        result.append({"occasion": "Fête nationale", "date": date(year, 2, 11).isoformat()})
    elif day == "9 août":
        result.append({"occasion": "Fête nationale", "date": date(year, 8, 9).isoformat()})
    elif day == "2 décembre":
        result.append({"occasion": "Fête nationale", "date": date(year, 12, 2).isoformat()})
    elif day == "23 septembre":
        result.append({"occasion": "Fête nationale", "date": date(year, 9, 23).isoformat()})
    elif day == "30 juillet":
        result.append({"occasion": "Fête nationale", "date": date(year, 7, 30).isoformat()})
    elif day == "4 avril":
        result.append({"occasion": "Fête nationale", "date": date(year, 4, 4).isoformat()})
    elif day == "7 août":
        result.append({"occasion": "Fête nationale", "date": date(year, 8, 7).isoformat()})
    return sorted(result, key=lambda item: item["date"])
