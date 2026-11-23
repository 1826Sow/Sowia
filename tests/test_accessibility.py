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


def test_transcription_component_localizes_visible_controls_and_statuses():
    english = live_transcription_component("English")
    chinese = live_transcription_component("中文")
    arabic = live_transcription_component("العربية")
    assert "Start microphone" in english
    assert "Microphone stopped. You can copy the text." in english
    assert "开始使用麦克风" in chinese
    assert "语音识别已中断：" in chinese
    assert "بدء الميكروفون" in arabic
    assert "تم نسخ النص" in arabic
    assert "Démarrer le micro" in live_transcription_component("Français")
