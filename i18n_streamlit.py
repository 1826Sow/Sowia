"""Apply existing SOW IA translations consistently to Streamlit UI labels.

Only presentation labels and short status messages are localized. User-authored
content, route identifiers, session-state keys, option values and stored data
are deliberately left untouched.
"""
from functools import wraps

_LOCALIZABLE_STREAMLIT_CALLS = (
    "title", "header", "subheader", "caption",
    "info", "success", "warning", "error", "exception",
    "button", "form_submit_button", "download_button",
    "text_input", "text_area", "selectbox", "radio", "checkbox",
    "toggle", "file_uploader", "date_input", "time_input",
    "number_input", "slider", "multiselect", "expander",
)

def install_streamlit_localization(st_module, translate, get_language):
    """Translate visible labels at render time without changing app data."""
    for method_name in _LOCALIZABLE_STREAMLIT_CALLS:
        original = getattr(st_module, method_name, None)
        if original is None or getattr(original, "_sowia_localized", False):
            continue

        @wraps(original)
        def localized(*args, __original=original, **kwargs):
            language = get_language() or "Français"
            if args and isinstance(args[0], str):
                args = (translate(args[0], language),) + args[1:]
            elif isinstance(kwargs.get("label"), str):
                kwargs["label"] = translate(kwargs["label"], language)
            # Translate option captions at display time while preserving the
            # original option objects used by session state and business logic.
            for display_kwarg in ("placeholder", "help"):
                display_value = kwargs.get(display_kwarg)
                if isinstance(display_value, str):
                    kwargs[display_kwarg] = translate(display_value, language)
            if method_name in ("selectbox", "radio", "multiselect"):
                kwargs.setdefault(
                    "format_func",
                    lambda option, _language=language: (
                        translate(option, _language) if isinstance(option, str) else option
                    ),
                )
            return __original(*args, **kwargs)

        localized._sowia_localized = True
        setattr(st_module, method_name, localized)
