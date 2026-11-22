from types import SimpleNamespace

from i18n_streamlit import install_streamlit_localization


def test_streamlit_labels_follow_active_language_without_changing_values():
    calls = []

    def button(label, **kwargs):
        calls.append(("button", label, kwargs))
        return True

    def text_input(label=None, **kwargs):
        calls.append(("text_input", label, kwargs))
        return "unchanged-user-value"

    fake_st = SimpleNamespace(button=button, text_input=text_input)
    language = {"value": "English"}

    def translate(value, active_language):
        return f"{active_language}:{value}"

    install_streamlit_localization(fake_st, translate, lambda: language["value"])

    assert fake_st.button("Valider", key="stable_key") is True
    assert calls[-1] == ("button", "English:Valider", {"key": "stable_key"})

    assert fake_st.text_input(label="Votre nom", key="user_name") == "unchanged-user-value"
    assert calls[-1] == ("text_input", "English:Votre nom", {"key": "user_name"})

    language["value"] = "中文"
    fake_st.button("Ouvrir")
    assert calls[-1][1] == "中文:Ouvrir"


def test_localization_does_not_touch_user_content_or_internal_values():
    calls = []

    def selectbox(label, options, **kwargs):
        calls.append((label, options, kwargs))
        return options[0]

    fake_st = SimpleNamespace(selectbox=selectbox)
    options = ["personal_workspace", "professional_workspace"]

    install_streamlit_localization(
        fake_st,
        lambda value, language: f"{language}:{value}",
        lambda: "Deutsch",
    )

    assert fake_st.selectbox("Espace de travail", options, key="workspace") == options[0]
    assert calls[-1][0] == "Deutsch:Espace de travail"
    assert calls[-1][1] is options
    assert calls[-1][2]["key"] == "workspace"
    assert calls[-1][2]["format_func"]("personal_workspace") == "Deutsch:personal_workspace"


def test_selection_options_are_translated_for_display_only():
    calls = []

    def radio(label, options, **kwargs):
        calls.append((label, options, kwargs))
        return options[0]

    fake_st = SimpleNamespace(radio=radio)
    options = ["Personnel", "Professionnel"]

    install_streamlit_localization(
        fake_st,
        lambda value, language: f"{language}:{value}",
        lambda: "English",
    )

    assert fake_st.radio("Choisissez un espace", options, key="space") == "Personnel"
    label, original_options, kwargs = calls[-1]
    assert label == "English:Choisissez un espace"
    assert original_options is options
    assert kwargs["key"] == "space"
    assert kwargs["format_func"]("Personnel") == "English:Personnel"
    assert kwargs["format_func"]("Professionnel") == "English:Professionnel"


def test_placeholders_help_and_common_ui_labels_are_localized():
    calls = []

    def text_input(label, **kwargs):
        calls.append((label, kwargs))
        return "user-data"

    fake_st = SimpleNamespace(text_input=text_input)
    from i18n import translate

    install_streamlit_localization(fake_st, translate, lambda: "English")
    result = fake_st.text_input(
        "Nom",
        placeholder="Saisissez votre nom",
        help="Enregistrez vos informations utiles",
        key="profile_name",
    )

    assert result == "user-data"
    label, kwargs = calls[-1]
    assert label == "Name"
    assert kwargs["placeholder"] == "Enter your name"
    assert kwargs["help"] == "Save useful information"
    assert kwargs["key"] == "profile_name"


def test_shared_interface_vocabulary_exists_for_all_supported_languages():
    from i18n import LANGUAGES, translate

    expected = {
        "English": "Confirm",
        "Español": "Confirmar",
        "中文": "确认",
        "Deutsch": "Bestätigen",
        "العربية": "تأكيد",
    }

    assert len(LANGUAGES) == 6
    for language, expected_label in expected.items():
        assert translate("Valider", language) == expected_label
        assert translate("Annuler", language) != "Annuler"


def test_existing_option_formatter_is_preserved_and_its_caption_is_translated():
    calls = []

    def selectbox(label, options, **kwargs):
        calls.append((label, options, kwargs))
        return options[0]

    fake_st = SimpleNamespace(selectbox=selectbox)
    options = [{"id": "personal", "label": "Espace personnel"}]
    original_formatter = lambda option: option["label"]

    install_streamlit_localization(
        fake_st,
        lambda value, language: f"{language}:{value}",
        lambda: "English",
    )

    assert fake_st.selectbox(
        "Espace",
        options,
        format_func=original_formatter,
        key="space",
    ) == options[0]
    label, original_options, kwargs = calls[-1]
    assert label == "English:Espace"
    assert original_options is options
    assert kwargs["format_func"](options[0]) == "English:Espace personnel"
    assert kwargs["key"] == "space"


def test_select_slider_and_link_button_are_localized_without_changing_values():
    calls = []

    def select_slider(label, options, **kwargs):
        calls.append(("select_slider", label, options, kwargs))
        return options[0]

    def link_button(label, url, **kwargs):
        calls.append(("link_button", label, url, kwargs))
        return True

    fake_st = SimpleNamespace(select_slider=select_slider, link_button=link_button)
    options = ["Débutant", "Avancé"]
    translate = lambda value, language: f"{language}:{value}"
    install_streamlit_localization(fake_st, translate, lambda: "Deutsch")

    assert fake_st.select_slider("Niveau", options, key="level") == "Débutant"
    assert calls[-1][1] == "Deutsch:Niveau"
    assert calls[-1][2] is options
    assert calls[-1][3]["format_func"]("Débutant") == "Deutsch:Débutant"

    assert fake_st.link_button("Ouvrir le guide", "https://example.test") is True
    assert calls[-1][1] == "Deutsch:Ouvrir le guide"
    assert calls[-1][2] == "https://example.test"


def test_specialist_workspace_vocabulary_is_translated_in_every_supported_language():
    from i18n import translate

    examples = {
        "English": ("Country", "Open source"),
        "Español": ("País", "Abrir la fuente"),
        "中文": ("国家/地区", "打开来源"),
        "Deutsch": ("Land", "Quelle öffnen"),
        "العربية": ("البلد", "فتح المصدر"),
    }

    for language, (country, source) in examples.items():
        assert translate("Pays", language) == country
        assert translate("Ouvrir la source", language) == source
        assert translate("Confirmer la suppression", language) != "Confirmer la suppression"


def test_markdown_headings_and_plain_text_use_catalogue_without_rewriting_html():
    calls = []
    fake_st = SimpleNamespace(
        markdown=lambda body, **kwargs: calls.append(("markdown", body, kwargs)),
        write=lambda body, **kwargs: calls.append(("write", body, kwargs)),
    )
    from i18n import translate

    install_streamlit_localization(fake_st, translate, lambda: "English")
    fake_st.markdown("### Classement proposé")
    assert calls[-1][1] == "### Proposed ranking"

    html = '<div class="partner-intro"><strong>Partnerships</strong></div>'
    fake_st.markdown(html, unsafe_allow_html=True)
    assert calls[-1][1] == html

    fake_st.write("Pays")
    assert calls[-1][1] == "Country"


def test_tabs_translate_only_visible_labels():
    calls = []
    fake_st = SimpleNamespace(tabs=lambda labels: calls.append(labels) or labels)
    install_streamlit_localization(
        fake_st,
        lambda value, language: f"{language}:{value}",
        lambda: "English",
    )
    labels = ["Personnel", "Professionnel"]
    result = fake_st.tabs(labels)
    assert result == ["English:Personnel", "English:Professionnel"]
    assert labels == ["Personnel", "Professionnel"]


def test_dashboard_status_copy_is_translated_across_locales():
    from i18n import translate

    expected = {
        "English": "Active workspace",
        "Español": "Espacio activo",
        "中文": "当前工作区",
        "Deutsch": "Aktiver Arbeitsbereich",
        "العربية": "مساحة العمل النشطة",
    }
    for language, translated in expected.items():
        assert translate("Espace actif", language) == translated
        assert translate("Décisions évaluées", language) != "Décisions évaluées"


def test_sidebar_and_nested_delta_generators_are_localized():
    class FakeDeltaGenerator:
        def button(self, label, **kwargs):
            return label

        def markdown(self, body, **kwargs):
            return body

    sidebar = FakeDeltaGenerator()
    nested_column = FakeDeltaGenerator()
    fake_st = SimpleNamespace(sidebar=sidebar)
    install_streamlit_localization(
        fake_st,
        lambda value, language: f"{language}:{value}",
        lambda: "English",
    )

    assert sidebar.button("Ouvrir") == "English:Ouvrir"
    assert nested_column.button("Enregistrer") == "English:Enregistrer"
    assert sidebar.markdown("Titre") == "English:Titre"


def test_multiline_markdown_translates_catalogue_lines_and_preserves_code_and_html():
    calls = []
    fake_st = SimpleNamespace(markdown=lambda body, **kwargs: calls.append(body))
    install_streamlit_localization(
        fake_st,
        lambda value, language: {"Titre": "Title", "Pays": "Country"}.get(value, value),
        lambda: "English",
    )
    source = "### Titre\n- Pays\n\n```python\nPays\n```\n<div>Pays</div>"
    fake_st.markdown(source)
    assert calls[-1] == "### Title\n- Country\n\n```python\nPays\n```\n<div>Pays</div>"


def test_french_remains_the_canonical_display_language():
    from i18n import translate

    for label in ("Valider", "Annuler", "Pays", "Décisions évaluées"):
        assert translate(label, "Français") == label


def test_dynamic_diagnostic_suffix_is_preserved_after_prefix_translation():
    from i18n import translate

    suffix = " ERR-2048 — fournisseur indisponible"
    expected = {
        "English": "Technical diagnostics:" + suffix,
        "Español": "Diagnóstico técnico:" + suffix,
        "中文": "技术诊断：" + suffix,
        "Deutsch": "Technische Diagnose:" + suffix,
        "العربية": "التشخيص التقني:" + suffix,
    }
    for language, result in expected.items():
        assert translate("Diagnostic technique :" + suffix, language) == result
