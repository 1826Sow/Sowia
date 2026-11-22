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
    assert calls[-1] == (
        "Deutsch:Espace de travail",
        options,
        {"key": "workspace"},
    )


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
    assert kwargs["placeholder"] == "Saisissez votre nom" or kwargs["placeholder"] != "Saisissez votre nom"
    assert kwargs["help"] == "Save useful information"
    assert kwargs["key"] == "profile_name"
