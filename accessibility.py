"""Browser-native live speech transcription UI for SOW IA.

Audio recognition runs through the browser's Web Speech implementation.
The transcript remains inside the component until the user copies it.
"""
import html
import json


LANGUAGE_LOCALES = {
    "Français": "fr-FR",
    "English": "en-US",
    "Español": "es-ES",
    "中文": "zh-CN",
    "Deutsch": "de-DE",
    "العربية": "ar-SA",
}


def live_transcription_component(language: str) -> str:
    """Return an accessible, browser-native speech-to-text component."""
    locale = LANGUAGE_LOCALES.get(language, "fr-FR")
    locale_js = json.dumps(locale)
    return """
<div style="font-family:Arial,sans-serif;color:#17212b;padding:8px;border:1px solid #8b9aa8;border-radius:12px;background:#fff">
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px">
    <button id="start" type="button" style="min-height:46px;padding:10px 16px;border:2px solid #174b67;border-radius:9px;background:#174b67;color:#fff;font-weight:700">Démarrer le micro</button>
    <button id="stop" type="button" disabled style="min-height:46px;padding:10px 16px;border:2px solid #555;border-radius:9px;background:#fff;color:#17212b;font-weight:700">Arrêter</button>
    <button id="copy" type="button" style="min-height:46px;padding:10px 16px;border:2px solid #555;border-radius:9px;background:#fff;color:#17212b;font-weight:700">Copier le texte</button>
  </div>
  <div id="status" role="status" aria-live="polite" style="font-weight:700;margin:6px 0">Micro désactivé</div>
  <div id="transcript" role="log" aria-live="polite" aria-relevant="additions text"
       style="min-height:76px;max-height:150px;overflow:auto;padding:10px;border:1px solid #aab4bd;border-radius:8px;background:#f7f9fb;line-height:1.55;white-space:pre-wrap">Votre transcription apparaîtra ici.</div>
  <div style="font-size:12px;color:#44515c;margin-top:7px">Autorisez le micro dans votre navigateur. La transcription peut comporter des erreurs : relisez-la avant de l'envoyer.</div>
</div>
<script>
(() => {
  const locale = """ + locale_js + """;
  const start = document.getElementById('start');
  const stop = document.getElementById('stop');
  const copy = document.getElementById('copy');
  const status = document.getElementById('status');
  const output = document.getElementById('transcript');
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let finalText = '';
  let interimText = '';

  if (!Recognition) {
    status.textContent = 'Reconnaissance vocale non prise en charge. Essayez un navigateur compatible, par exemple Chrome sur Android.';
    start.disabled = true;
    start.setAttribute('aria-disabled', 'true');
    return;
  }

  recognition = new Recognition();
  recognition.lang = locale;
  recognition.continuous = true;
  recognition.interimResults = true;

  const render = () => {
    const text = (finalText + ' ' + interimText).trim();
    output.textContent = text || 'Parlez près du microphone : le texte apparaîtra ici.';
  };

  recognition.onstart = () => {
    status.textContent = 'Écoute en cours — ' + locale;
    start.disabled = true;
    stop.disabled = false;
  };
  recognition.onresult = (event) => {
    interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const part = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += part + ' ';
      else interimText += part;
    }
    render();
  };
  recognition.onerror = (event) => {
    status.textContent = 'Reconnaissance interrompue : ' + event.error;
    start.disabled = false;
    stop.disabled = true;
  };
  recognition.onend = () => {
    start.disabled = false;
    stop.disabled = true;
    if (status.textContent.indexOf('Reconnaissance interrompue') !== 0) {
      status.textContent = 'Micro arrêté. Vous pouvez copier le texte.';
    }
  };
  start.addEventListener('click', () => {
    try {
      recognition.lang = locale;
      recognition.start();
    } catch (error) {
      status.textContent = 'Impossible de démarrer. Vérifiez les autorisations du micro.';
    }
  });
  stop.addEventListener('click', () => {
    if (recognition) recognition.stop();
  });
  copy.addEventListener('click', async () => {
    const text = (finalText + ' ' + interimText).trim();
    if (!text) {
      status.textContent = 'Aucun texte à copier pour le moment.';
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = 'Texte copié. Collez-le dans le champ de conversation.';
    } catch (error) {
      const field = document.createElement('textarea');
      field.value = text;
      document.body.appendChild(field);
      field.select();
      const copied = document.execCommand('copy');
      field.remove();
      status.textContent = copied ? 'Texte copié. Collez-le dans le champ de conversation.' : 'Copie impossible : sélectionnez le texte manuellement.';
    }
  });
})();
</script>
"""


def supported_speech_locale(language: str) -> str:
    """Return the configured BCP-47 locale, with French as a safe fallback."""
    return LANGUAGE_LOCALES.get(language, "fr-FR")



def speech_readout_component(message: str, language: str) -> str:
    """Return a safe, browser-native text-to-speech control for one answer."""
    locale = json.dumps(LANGUAGE_LOCALES.get(language, "fr-FR"))
    safe_message = html.escape(str(message), quote=True)
    return """
<div style="font-family:Arial,sans-serif;padding:4px 0">
  <button id="sowiaSpeak" type="button" style="padding:10px 16px;border:2px solid #174b67;border-radius:10px;background:#102943;color:#eff9ff;font-weight:700;min-height:44px">🔊 Écouter cette réponse</button>
  <button id="sowiaStop" type="button" style="padding:10px 16px;border:2px solid #555;border-radius:10px;background:#102943;color:#eff9ff;font-weight:700;min-height:44px">■ Arrêter</button>
  <span id="sowiaVoiceStatus" role="status" aria-live="polite"></span>
  <div id="sowiaVoiceText" style="display:none">""" + safe_message + """</div>
  <script>
  (() => {
    const text = document.getElementById('sowiaVoiceText').textContent;
    const status = document.getElementById('sowiaVoiceStatus');
    const speakButton = document.getElementById('sowiaSpeak');
    const stopButton = document.getElementById('sowiaStop');
    const locale = """ + locale + """;
    speakButton.addEventListener('click', () => {
      if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
        status.textContent = 'Lecture vocale non prise en charge par ce navigateur.';
        return;
      }
      const engine = window.speechSynthesis;
      engine.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = locale;
      utterance.rate = 1;
      utterance.pitch = 1;
      utterance.volume = 1;
      const voices = engine.getVoices();
      const wantedLanguage = locale.toLowerCase();
      const matchingVoice = voices.find(voice => voice.lang.toLowerCase() === wantedLanguage)
        || voices.find(voice => voice.lang.toLowerCase().startsWith(wantedLanguage.slice(0, 2)));
      if (matchingVoice) utterance.voice = matchingVoice;
      utterance.onstart = () => { status.textContent = 'Lecture en cours'; speakButton.disabled = true; };
      utterance.onend = () => { status.textContent = 'Lecture terminée'; speakButton.disabled = false; };
      utterance.onerror = (event) => {
        status.textContent = event.error === 'canceled' ? 'Lecture arrêtée' : 'Lecture indisponible sur cet appareil.';
        speakButton.disabled = false;
      };
      status.textContent = voices.length ? 'Préparation de la lecture…' : 'Utilisation de la voix par défaut…';
      engine.speak(utterance);
    });
    stopButton.addEventListener('click', () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      status.textContent = 'Lecture arrêtée';
      speakButton.disabled = false;
    });
  })();
  </script>
</div>
"""
