from accessibility import live_transcription_component, supported_speech_locale


def test_speech_locale_matches_all_sowia_interface_languages():
    assert supported_speech_locale("Français") == "fr-FR"
    assert supported_speech_locale("English") == "en-US"
    assert supported_speech_locale("Español") == "es-ES"
    assert supported_speech_locale("中文") == "zh-CN"
    assert supported_speech_locale("Deutsch") == "de-DE"
    assert supported_speech_locale("العربية") == "ar-SA"


def test_unknown_language_falls_back_to_french():
    assert supported_speech_locale("Unknown") == "fr-FR"


def test_transcription_component_is_accessible_and_does_not_auto_submit():
    component = live_transcription_component("Français")
    assert 'aria-live="polite"' in component
    assert "SpeechRecognition" in component
    assert "Copier le texte" in component
    assert "recognition.start()" in component
    assert "GenUI.issueNewTurn" not in component
    assert "zh-CN" not in component
