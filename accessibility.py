"""Browser-native live speech transcription UI for SOW IA.

Audio recognition runs through the browser's Web Speech implementation.
The transcript remains inside the component until the user copies it.
"""
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
    component = """
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
    translations = {
        "Français": {},
        "English": {
            "Démarrer le micro":"Start microphone","Arrêter":"Stop","Copier le texte":"Copy text",
            "Micro désactivé":"Microphone off","Votre transcription apparaîtra ici.":"Your transcription will appear here.",
            "Autorisez le micro dans votre navigateur. La transcription peut comporter des erreurs : relisez-la avant de l'envoyer.":"Allow microphone access in your browser. Transcription may contain errors; review it before sending.",
            "Reconnaissance vocale non prise en charge. Essayez un navigateur compatible, par exemple Chrome sur Android.":"Speech recognition is not supported. Try a compatible browser, such as Chrome on Android.",
            "Parlez près du microphone : le texte apparaîtra ici.":"Speak near the microphone; your text will appear here.",
            "Écoute en cours — ":"Listening — ","Reconnaissance interrompue : ":"Recognition interrupted: ",
            "Micro arrêté. Vous pouvez copier le texte.":"Microphone stopped. You can copy the text.",
            "Impossible de démarrer. Vérifiez les autorisations du micro.":"Could not start. Check microphone permissions.",
            "Aucun texte à copier pour le moment.":"There is no text to copy yet.",
            "Texte copié. Collez-le dans le champ de conversation.":"Text copied. Paste it into the chat field.",
            "Copie impossible : sélectionnez le texte manuellement.":"Copy failed. Select the text manually."
        },
        "Español": {
            "Démarrer le micro":"Iniciar micrófono","Arrêter":"Detener","Copier le texte":"Copiar texto",
            "Micro désactivé":"Micrófono desactivado","Votre transcription apparaîtra ici.":"Tu transcripción aparecerá aquí.",
            "Autorisez le micro dans votre navigateur. La transcription peut comporter des erreurs : relisez-la avant de l'envoyer.":"Permite el micrófono en tu navegador. La transcripción puede contener errores; revísala antes de enviarla.",
            "Reconnaissance vocale non prise en charge. Essayez un navigateur compatible, par exemple Chrome sur Android.":"El reconocimiento de voz no es compatible. Prueba un navegador compatible, como Chrome en Android.",
            "Parlez près du microphone : le texte apparaîtra ici.":"Habla cerca del micrófono: el texto aparecerá aquí.",
            "Écoute en cours — ":"Escuchando — ","Reconnaissance interrompue : ":"Reconocimiento interrumpido: ",
            "Micro arrêté. Vous pouvez copier le texte.":"Micrófono detenido. Ya puedes copiar el texto.",
            "Impossible de démarrer. Vérifiez les autorisations du micro.":"No se pudo iniciar. Comprueba los permisos del micrófono.",
            "Aucun texte à copier pour le moment.":"Todavía no hay texto para copiar.",
            "Texte copié. Collez-le dans le champ de conversation.":"Texto copiado. Pégalo en el campo de conversación.",
            "Copie impossible : sélectionnez le texte manuellement.":"No se pudo copiar. Selecciona el texto manualmente."
        },
        "中文": {
            "Démarrer le micro":"开始使用麦克风","Arrêter":"停止","Copier le texte":"复制文本",
            "Micro désactivé":"麦克风已关闭","Votre transcription apparaîtra ici.":"转录内容将显示在这里。",
            "Autorisez le micro dans votre navigateur. La transcription peut comporter des erreurs : relisez-la avant de l'envoyer.":"请在浏览器中允许使用麦克风。转录可能有误，请发送前检查。",
            "Reconnaissance vocale non prise en charge. Essayez un navigateur compatible, par exemple Chrome sur Android.":"当前浏览器不支持语音识别。请尝试 Android 上的 Chrome 等兼容浏览器。",
            "Parlez près du microphone : le texte apparaîtra ici.":"请靠近麦克风说话，文字将显示在这里。",
            "Écoute en cours — ":"正在聆听 — ","Reconnaissance interrompue : ":"语音识别已中断：",
            "Micro arrêté. Vous pouvez copier le texte.":"麦克风已停止。您现在可以复制文本。",
            "Impossible de démarrer. Vérifiez les autorisations du micro.":"无法启动。请检查麦克风权限。",
            "Aucun texte à copier pour le moment.":"目前没有可复制的文本。",
            "Texte copié. Collez-le dans le champ de conversation.":"文本已复制。请粘贴到聊天输入框。",
            "Copie impossible : sélectionnez le texte manuellement.":"复制失败，请手动选择文本。"
        },
        "Deutsch": {
            "Démarrer le micro":"Mikrofon starten","Arrêter":"Stoppen","Copier le texte":"Text kopieren",
            "Micro désactivé":"Mikrofon aus","Votre transcription apparaîtra ici.":"Dein Transkript erscheint hier.",
            "Autorisez le micro dans votre navigateur. La transcription peut comporter des erreurs : relisez-la avant de l'envoyer.":"Erlaube den Mikrofonzugriff im Browser. Die Transkription kann Fehler enthalten; bitte vor dem Senden prüfen.",
            "Reconnaissance vocale non prise en charge. Essayez un navigateur compatible, par exemple Chrome sur Android.":"Spracherkennung wird nicht unterstützt. Versuche einen kompatiblen Browser wie Chrome auf Android.",
            "Parlez près du microphone : le texte apparaîtra ici.":"Sprich in die Nähe des Mikrofons; der Text erscheint hier.",
            "Écoute en cours — ":"Aufnahme läuft — ","Reconnaissance interrompue : ":"Spracherkennung unterbrochen: ",
            "Micro arrêté. Vous pouvez copier le texte.":"Mikrofon gestoppt. Du kannst den Text kopieren.",
            "Impossible de démarrer. Vérifiez les autorisations du micro.":"Start nicht möglich. Prüfe die Mikrofonberechtigungen.",
            "Aucun texte à copier pour le moment.":"Noch kein Text zum Kopieren vorhanden.",
            "Texte copié. Collez-le dans le champ de conversation.":"Text kopiert. Füge ihn in das Chatfeld ein.",
            "Copie impossible : sélectionnez le texte manuellement.":"Kopieren fehlgeschlagen. Markiere den Text manuell."
        },
        "العربية": {
            "Démarrer le micro":"بدء الميكروفون","Arrêter":"إيقاف","Copier le texte":"نسخ النص",
            "Micro désactivé":"الميكروفون متوقف","Votre transcription apparaîtra ici.":"سيظهر النص المنسوخ هنا.",
            "Autorisez le micro dans votre navigateur. La transcription peut comporter des erreurs : relisez-la avant de l'envoyer.":"اسمح باستخدام الميكروفون في المتصفح. قد يحتوي التفريغ على أخطاء؛ راجعه قبل الإرسال.",
            "Reconnaissance vocale non prise en charge. Essayez un navigateur compatible, par exemple Chrome sur Android.":"التعرف على الصوت غير مدعوم. جرّب متصفحًا متوافقًا مثل Chrome على Android.",
            "Parlez près du microphone : le texte apparaîtra ici.":"تحدث بالقرب من الميكروفون وسيظهر النص هنا.",
            "Écoute en cours — ":"جارٍ الاستماع — ","Reconnaissance interrompue : ":"تم إيقاف التعرف على الصوت: ",
            "Micro arrêté. Vous pouvez copier le texte.":"توقف الميكروفون. يمكنك نسخ النص الآن.",
            "Impossible de démarrer. Vérifiez les autorisations du micro.":"تعذر البدء. تحقق من أذونات الميكروفون.",
            "Aucun texte à copier pour le moment.":"لا يوجد نص لنسخه حاليًا.",
            "Texte copié. Collez-le dans le champ de conversation.":"تم نسخ النص. الصقه في حقل المحادثة.",
            "Copie impossible : sélectionnez le texte manuellement.":"تعذر النسخ. حدد النص يدويًا."
        },
    }
    for original, translated in translations.get(language, {}).items():
        component = component.replace(original, translated)
    return component



def supported_speech_locale(language: str) -> str:
    """Return the configured BCP-47 locale, with French as a safe fallback."""
    return LANGUAGE_LOCALES.get(language, "fr-FR")
