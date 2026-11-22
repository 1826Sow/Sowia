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
