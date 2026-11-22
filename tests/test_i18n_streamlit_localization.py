from types import SimpleNamespace

from i18n_streamlit import install_streamlit_localization


def test_module_widgets_follow_active_language_and_keep_returned_values():
    calls = []
    fake_st = SimpleNamespace(
        button=lambda label, **kwargs: calls.append((label, kwargs)) or True,
        text_input=lambda label=None, **kwargs: "unchanged-user-value",
    )
    language = {"value": "English"}
    translate = lambda value, active: f"{active}:{value}"

    install_streamlit_localization(fake_st, translate, lambda: language["value"])

    assert fake_st.button("Valider", key="stable") is True
    assert calls[-1] == ("English:Valider", {"key": "stable"})
    assert fake_st.text_input(label="Votre nom", key="name") == "unchanged-user-value"

    language["value"] = "中文"
    fake_st.button("Ouvrir")
    assert calls[-1][0] == "中文:Ouvrir"


def test_selection_values_are_unchanged_and_display_labels_are_localized():
    calls = []

    def selectbox(label, options, **kwargs):
        calls.append((label, options, kwargs))
        return options[0]

    fake_st = SimpleNamespace(selectbox=selectbox)
    options = ["personal_workspace", "professional_workspace"]
    install_streamlit_localization(
        fake_st, lambda value, language: f"{language}:{value}", lambda: "Deutsch"
    )

    assert fake_st.selectbox("Espace", options, key="workspace") == options[0]
    label, original_options, kwargs = calls[-1]
    assert label == "Deutsch:Espace"
    assert original_options is options
    assert kwargs["key"] == "workspace"
    assert kwargs["format_func"]("personal_workspace") == "Deutsch:personal_workspace"


def test_custom_option_formatter_is_preserved_and_translated():
    calls = []

    def selectbox(label, options, **kwargs):
        calls.append((label, options, kwargs))
        return options[0]

    options = [{"key": "profile", "caption": "Espace personnel"}]
    formatter = lambda option: option["caption"]
    fake_st = SimpleNamespace(selectbox=selectbox)
    install_streamlit_localization(
        fake_st, lambda value, language: f"{language}:{value}", lambda: "English"
    )

    assert fake_st.selectbox("Espace", options, format_func=formatter) is options[0]
    assert calls[-1][2]["format_func"](options[0]) == "English:Espace personnel"
    assert calls[-1][2]["format_func"] is not formatter


def test_placeholder_help_and_select_slider_are_localized_without_changing_values():
    calls = []

    def text_input(label, **kwargs):
        calls.append(("input", label, kwargs))
        return "user-data"

    def select_slider(label, options, **kwargs):
        calls.append(("slider", label, options, kwargs))
        return options[0]

    fake_st = SimpleNamespace(text_input=text_input, select_slider=select_slider)
    install_streamlit_localization(
        fake_st, lambda value, language: f"{language}:{value}", lambda: "Español"
    )

    assert fake_st.text_input("Nom", placeholder="Saisir", help="Aide") == "user-data"
    assert calls[-1][1] == "Español:Nom"
    assert calls[-1][2]["placeholder"] == "Español:Saisir"
    assert calls[-1][2]["help"] == "Español:Aide"

    options = ["Débutant", "Avancé"]
    assert fake_st.select_slider("Niveau", options, key="level") == "Débutant"
    assert calls[-1][2] is options
    assert calls[-1][3]["format_func"]("Débutant") == "Español:Débutant"


def test_markdown_headings_and_html_are_localized_safely():
    calls = []
    fake_st = SimpleNamespace(markdown=lambda body, **kwargs: calls.append(body))
    translate = lambda value, language: {"Classement proposé": "Proposed ranking"}.get(value, value)
    install_streamlit_localization(fake_st, translate, lambda: "English")

    fake_st.markdown("### Classement proposé")
    assert calls[-1] == "### Proposed ranking"

    html = '<div class="partner-intro"><strong>Partnerships</strong></div>'
    fake_st.markdown(html, unsafe_allow_html=True)
    assert calls[-1] == html



def test_markdown_uses_catalogue_only_without_external_fallback():
    calls = []

    def translate(value, language, *, allow_fallback=True):
        calls.append((value, language, allow_fallback))
        return "Texte traduit" if value == "Titre connu" else value

    fake_st = SimpleNamespace(markdown=lambda body, **kwargs: calls.append(("rendered", body)))
    install_streamlit_localization(fake_st, translate, lambda: "English")

    fake_st.markdown("### Titre connu")
    fake_st.markdown("Contenu privé dynamique")

    assert ("Titre connu", "English", False) in calls
    assert ("Contenu privé dynamique", "English", False) in calls
    assert ("rendered", "### Texte traduit") in calls
    assert ("rendered", "Contenu privé dynamique") in calls

def test_write_preserves_dynamic_and_user_supplied_content_verbatim():
    calls = []
    fake_st = SimpleNamespace(write=lambda body, **kwargs: calls.append(body))
    translate = lambda value, language: f"{language}:{value}"
    install_streamlit_localization(fake_st, translate, lambda: "English")

    user_text = "Pays — notification privée reçue"
    fake_st.write(user_text)
    assert calls[-1] == user_text


def test_multiline_markdown_translates_exact_phrases_and_preserves_code_html_and_urls():
    calls = []
    fake_st = SimpleNamespace(markdown=lambda body, **kwargs: calls.append(body))
    translate = lambda value, language: {"Titre": "Title", "Pays": "Country"}.get(value, value)
    install_streamlit_localization(fake_st, translate, lambda: "English")

    fence = chr(96) * 3
    source = "### Titre\n- Pays\n\n" + fence + "python\nPays\n" + fence + "\n<div>Pays</div>\n[site](https://example.test)"
    expected = "### Title\n- Country\n\n" + fence + "python\nPays\n" + fence + "\n<div>Pays</div>\n[site](https://example.test)"
    fake_st.markdown(source)
    assert calls[-1] == expected


def test_tabs_translate_only_visible_labels_and_preserve_original_sequence():
    calls = []
    fake_st = SimpleNamespace(tabs=lambda labels: calls.append(labels) or labels)
    labels = ["Personnel", "Professionnel"]
    install_streamlit_localization(
        fake_st, lambda value, language: f"{language}:{value}", lambda: "English"
    )

    assert fake_st.tabs(labels) == ["English:Personnel", "English:Professionnel"]
    assert labels == ["Personnel", "Professionnel"]


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
        fake_st, lambda value, language: f"{language}:{value}", lambda: "English"
    )

    assert sidebar.button("Ouvrir") == "English:Ouvrir"
    assert nested_column.button("Enregistrer") == "English:Enregistrer"
    assert sidebar.markdown("Titre") == "English:Titre"


def test_chat_input_label_and_placeholder_follow_active_language():
    calls = []

    def chat_input(label=None, **kwargs):
        calls.append((label, kwargs))
        return "unchanged-user-message"

    fake_st = SimpleNamespace(chat_input=chat_input)
    install_streamlit_localization(
        fake_st, lambda value, language: f"{language}:{value}", lambda: "English"
    )

    assert fake_st.chat_input("Votre message", placeholder="Écrire ici") == "unchanged-user-message"
    assert calls[-1] == (
        "English:Votre message",
        {"placeholder": "English:Écrire ici"},
    )



def test_spinner_and_progress_messages_follow_active_language():
    calls = []

    class FakeSpinner:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    def spinner(message):
        calls.append(("spinner", message))
        return FakeSpinner()

    def progress(value, **kwargs):
        calls.append(("progress", value, kwargs))
        return "progress-result"

    fake_st = SimpleNamespace(spinner=spinner, progress=progress)
    install_streamlit_localization(
        fake_st, lambda value, language: f"{language}:{value}", lambda: "Deutsch"
    )

    with fake_st.spinner("Analyse du document en cours..."):
        pass
    assert calls[-1] == ("spinner", "Deutsch:Analyse du document en cours...")

    assert fake_st.progress(35, text="Préparation en cours") == "progress-result"
    assert calls[-1] == ("progress", 35, {"text": "Deutsch:Préparation en cours"})
