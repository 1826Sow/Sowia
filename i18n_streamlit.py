"""Apply SOW IA interface translations to all Streamlit display surfaces.

The wrapper changes presentation text only. It never changes option values,
session-state keys, route identifiers, uploaded files or user-authored data.
"""
from functools import wraps
import re

_LOCALIZABLE_STREAMLIT_CALLS = (
    "title", "header", "subheader", "caption",
    "info", "success", "warning", "error", "exception",
    "button", "form_submit_button", "download_button", "link_button",
    "text_input", "text_area", "selectbox", "radio", "checkbox",
    "toggle", "file_uploader", "date_input", "time_input",
    "number_input", "slider", "select_slider", "multiselect",
    "expander", "metric", "markdown", "text", "tabs", "status",
)


def _translate_markdown_text(value, language, translate):
    """Translate exact UI phrases line by line while preserving Markdown."""
    output = []
    in_code_fence = False
    for line in value.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(chr(96) * 3) or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            output.append(line)
            continue
        if in_code_fence or not stripped or "<" in line or "](" in line or "![" in line:
            output.append(line)
            continue

        ending = "\n" if line.endswith("\n") else ""
        body = line[:-1] if ending else line
        patterns = (
            r"^(\s*#{1,6}\s+)(.+)$",
            r"^(\s*\*\*)(.+?)(\*\*\s*)$",
            r"^(\s*(?:[-*+]\s+|\d+\.\s+))(.+)$",
            r"^(\s*>\s*)(.+)$",
        )
        translated_line = body
        for pattern in patterns:
            match = re.match(pattern, body)
            if match:
                if len(match.groups()) == 2:
                    prefix, phrase = match.groups()
                    translated_line = prefix + translate(phrase, language)
                else:
                    prefix, phrase, suffix = match.groups()
                    translated_line = prefix + translate(phrase, language) + suffix
                break
        else:
            if not any(token in body for token in ("**", chr(96), "{", "}")):
                translated_line = translate(body, language)
        output.append(translated_line + ending)
    return "".join(output)


def install_streamlit_localization(st_module, translate, get_language):
    """Localize UI labels while leaving arbitrary st.write content untouched."""

    def wrap_method(target, method_name, bound):
        original = getattr(target, method_name, None)
        if original is None or getattr(original, "_sowia_localized", False):
            return

        @wraps(original)
        def localized(*args, __original=original, __method=method_name, __bound=bound, **kwargs):
            language = get_language() or "Français"
            label_index = 1 if __bound else 0
            mutable_args = list(args)

            if len(mutable_args) > label_index and isinstance(mutable_args[label_index], str):
                first = mutable_args[label_index]
                if __method == "markdown":
                    first = _translate_markdown_text(first, language, translate)
                else:
                    first = translate(first, language)
                mutable_args[label_index] = first
            elif isinstance(kwargs.get("label"), str):
                kwargs["label"] = translate(kwargs["label"], language)

            tabs_index = 1 if __bound else 0
            if __method == "tabs" and len(mutable_args) > tabs_index and isinstance(mutable_args[tabs_index], (list, tuple)):
                labels = mutable_args[tabs_index]
                mutable_args[tabs_index] = type(labels)(
                    translate(item, language) if isinstance(item, str) else item
                    for item in labels
                )

            for display_kwarg in ("placeholder", "help"):
                display_value = kwargs.get(display_kwarg)
                if isinstance(display_value, str):
                    kwargs[display_kwarg] = translate(display_value, language)

            if __method in ("selectbox", "radio", "multiselect", "select_slider"):
                caller_format = kwargs.get("format_func")

                def localized_format(option, _formatter=caller_format, _language=language):
                    display = _formatter(option) if _formatter else option
                    return translate(display, _language) if isinstance(display, str) else display

                kwargs["format_func"] = localized_format

            return __original(*mutable_args, **kwargs)

        localized._sowia_localized = True
        setattr(target, method_name, localized)

    # Streamlit exports pre-bound functions at module level.
    for method_name in _LOCALIZABLE_STREAMLIT_CALLS:
        wrap_method(st_module, method_name, bound=False)

    # Sidebar, columns, tabs, forms and nested containers are DeltaGenerators.
    sidebar = getattr(st_module, "sidebar", None)
    if sidebar is not None:
        generator_type = type(sidebar)
        for method_name in _LOCALIZABLE_STREAMLIT_CALLS:
            wrap_method(generator_type, method_name, bound=True)
