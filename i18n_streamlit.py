"""Apply existing SOW IA translations consistently to Streamlit UI labels.

Only presentation labels and short status messages are localized. User-authored
content, route identifiers, session-state keys, option values and stored data
are deliberately left untouched.
"""
from functools import wraps

_LOCALIZABLE_STREAMLIT_CALLS = (
    "title", "header", "subheader", "caption",
    "info", "success", "warning", "error", "exception",
    "button", "form_submit_button", "download_button", "link_button",
    "text_input", "text_area", "selectbox", "radio", "checkbox",
    "toggle", "file_uploader", "date_input", "time_input",
    "number_input", "slider", "select_slider", "multiselect",
    "expander", "metric", "markdown", "write", "text", "tabs", "status",
)


def install_streamlit_localization(st_module, translate, get_language):
    """Translate visible labels at render time without changing app data."""
    for method_name in _LOCALIZABLE_STREAMLIT_CALLS:
        original = getattr(st_module, method_name, None)
        if original is None or getattr(original, "_sowia_localized", False):
            continue

        @wraps(original)
        def localized(*args, __original=original, __method=method_name, **kwargs):
            language = get_language() or "Français"
            if args and isinstance(args[0], str):
                first = args[0]
                if __method == "markdown":
                    # Translate exact catalogue phrases only; leave HTML, CSS,
                    # links and code blocks untouched.
                    import re
                    if not any(token in first.lower() for token in ("<", "```", "![", "](")):
                        match = re.match(r"^(#{1,6}\s+|\*\*)(.*?)(\*\*)?$", first, re.S)
                        if match:
                            prefix, body, suffix = match.group(1), match.group(2), match.group(3) or ""
                            first = prefix + translate(body, language) + suffix
                        else:
                            first = translate(first, language)
                else:
                    first = translate(first, language)
                args = (first,) + args[1:]
            elif __method == "tabs" and args and isinstance(args[0], (list, tuple)):
                args = (type(args[0])(translate(item, language) if isinstance(item, str) else item for item in args[0]),) + args[1:]
            elif isinstance(kwargs.get("label"), str):
                kwargs["label"] = translate(kwargs["label"], language)

            # Help and placeholder are presentation copy, not stored values.
            for display_kwarg in ("placeholder", "help"):
                display_value = kwargs.get(display_kwarg)
                if isinstance(display_value, str):
                    kwargs[display_kwarg] = translate(display_value, language)

            if __method in ("selectbox", "radio", "multiselect", "select_slider"):
                # Preserve a caller-provided formatter, then translate only its
                # string output. Option objects and selected values stay intact.
                caller_format = kwargs.get("format_func")

                def localized_format(option, _formatter=caller_format, _language=language):
                    display = _formatter(option) if _formatter else option
                    return translate(display, _language) if isinstance(display, str) else display

                kwargs["format_func"] = localized_format

            return __original(*args, **kwargs)

        localized._sowia_localized = True
        setattr(st_module, method_name, localized)
