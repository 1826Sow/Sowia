from accessibility import live_transcription_component, speech_readout_component, supported_speech_locale


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



def test_speech_readout_uses_device_voice_and_selected_language():
    component = speech_readout_component("Bonjour", "Français")
    assert "speechSynthesis" in component
    assert "getVoices()" in component
    assert 'const locale = "fr-FR"' in component
    assert "Lecture en cours" in component
    assert "Lecture terminée" in component
    assert "engine.cancel()" in component


def test_speech_readout_escapes_untrusted_message_html():
    component = speech_readout_component("<script>alert(1)</script>", "Français")
    assert "&lt;script&gt;" in component
    assert "<script>alert(1)</script>" not in component


def test_speech_readout_falls_back_to_french_for_unknown_language():
    component = speech_readout_component("Hello", "Unknown")
    assert 'const locale = "fr-FR"' in component
