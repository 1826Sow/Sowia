import pytest

from i18n import translate


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Standard search"),
        ("Español", "Búsqueda estándar"),
        ("中文", "常规搜索"),
        ("Deutsch", "Standardsuche"),
        ("العربية", "بحث عادي"),
    ],
)
def test_web_search_tab_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Recherche classique", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Fact-check information"),
        ("Español", "Verificar una información"),
        ("中文", "核实信息"),
        ("Deutsch", "Information überprüfen"),
        ("العربية", "التحقق من معلومة"),
    ],
)
def test_information_verification_tab_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Vérifier une information", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "What would you like to search for?"),
        ("Español", "¿Qué desea buscar?"),
        ("中文", "您想搜索什么？"),
        ("Deutsch", "Wonach möchten Sie suchen?"),
        ("العربية", "ما الذي تريد البحث عنه؟"),
    ],
)
def test_web_search_input_prompt_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Que souhaitez-vous rechercher ?", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "What claim would you like to verify?"),
        ("Español", "¿Qué afirmación desea verificar?"),
        ("中文", "您想核实哪项说法？"),
        ("Deutsch", "Welche Aussage möchten Sie überprüfen?"),
        ("العربية", "ما الادعاء الذي تريد التحقق منه؟"),
    ],
)
def test_fact_check_prompt_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Quelle affirmation souhaitez-vous vérifier ?", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Open source"),
        ("Español", "Abrir la fuente"),
        ("中文", "打开来源"),
        ("Deutsch", "Quelle öffnen"),
        ("العربية", "فتح المصدر"),
    ],
)
def test_fact_check_source_action_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Ouvrir la source", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Status: To review"),
        ("Español", "Estado: Pendiente de revisión"),
        ("中文", "状态：待审查"),
        ("Deutsch", "Status: Zu prüfen"),
        ("العربية", "الحالة: قيد المراجعة"),
    ],
)
def test_fact_check_evidence_status_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Statut : À examiner", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "No usable sources were returned. This does not prove that the claim is false."),
        ("Español", "No se encontraron fuentes utilizables. Esto no demuestra que la afirmación sea falsa."),
        ("中文", "未返回可用来源。这并不能证明该说法是错误的。"),
        ("Deutsch", "Es wurden keine verwertbaren Quellen gefunden. Das beweist nicht, dass die Aussage falsch ist."),
        ("العربية", "لم يتم العثور على مصادر قابلة للاستخدام. وهذا لا يثبت أن الادعاء خاطئ."),
    ],
)
def test_fact_check_no_evidence_message_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    source = "Aucune source exploitable n'a été retournée. Cela ne prouve pas que l'affirmation est fausse."
    assert translate(source, language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Convert images to PDF"),
        ("Español", "Convertir imágenes a PDF"),
        ("中文", "将图片转换为 PDF"),
        ("Deutsch", "Bilder in PDF umwandeln"),
        ("العربية", "تحويل الصور إلى PDF"),
    ],
)
def test_pdf_image_conversion_action_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Convertir les images en PDF", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Choose a PDF to convert"),
        ("Español", "Elegir un PDF para convertir"),
        ("中文", "选择要转换的 PDF"),
        ("Deutsch", "PDF zur Konvertierung auswählen"),
        ("العربية", "اختر ملف PDF للتحويل"),
    ],
)
def test_pdf_upload_picker_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Choisir un PDF à convertir", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Download images (ZIP)"),
        ("Español", "Descargar imágenes (ZIP)"),
        ("中文", "下载图片（ZIP）"),
        ("Deutsch", "Bilder herunterladen (ZIP)"),
        ("العربية", "تنزيل الصور (ZIP)"),
    ],
)
def test_pdf_image_download_action_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    assert translate("Télécharger les images (ZIP)", language) == expected


@pytest.mark.parametrize(
    "language,expected",
    [
        ("English", "Select a PDF from your phone. Private transfer to Supabase, 10 MB maximum."),
        ("Español", "Selecciona un PDF desde tu teléfono. Transferencia privada a Supabase, máximo 10 MB."),
        ("中文", "从手机选择 PDF。文件将私密传输到 Supabase，最大 10 MB。"),
        ("Deutsch", "Wählen Sie ein PDF von Ihrem Telefon aus. Private Übertragung zu Supabase, maximal 10 MB."),
        ("العربية", "اختر ملف PDF من هاتفك. نقل خاص إلى Supabase، بحد أقصى 10 ميغابايت."),
    ],
)
def test_pdf_private_upload_explanation_is_localized(language, expected, monkeypatch):
    monkeypatch.setattr("i18n._translate_missing_interface_copy", lambda text, selected: text)
    source = "Sélectionnez un PDF depuis votre téléphone. Transfert privé vers Supabase, 10 Mo maximum."
    assert translate(source, language) == expected
