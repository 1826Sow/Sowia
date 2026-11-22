"""Apply existing SOW IA translations consistently to Streamlit UI labels.

Only presentation labels and short status messages are localized. User-authored
content, route identifiers, session-state keys, option values and stored data
are deliberately left untouched.
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
    "expander", "metric", "markdown", "write", "text", "tabs", "status",
)


def install_streamlit_localization(st_module, translate, get_language):
    """Localize both st.* and DeltaGenerator UI methods (sidebar/columns/tabs)."""

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
                    # Translate exact catalogue phrases only; preserve HTML,
                    # CSS, links, code blocks and arbitrary rich content.
                    if not any(token in first.lower() for token in ("<", "```", "![", "](")):
                        match = re.match(r"^(#{1,6}\\s+|\\*\\*)(.*?)(\\*\\*)?$", first, re.S)
                        if match:
                            prefix, body, suffix = match.group(1), match.group(2), match.group(3) or ""
                            first = prefix + translate(body, language) + suffix
                        else:
                            first = translate(first, language)
                else:
                    first = translate(first, language)
                mutable_args[label_index] = first
            elif isinstance(kwargs.get("label"), str):
                kwargs["label"] = translate(kwargs["label"], language)

            # Tabs receive a sequence of visible labels rather than label=.
            tabs_index = 1 if __bound else 0
            if __method == "tabs" and len(mutable_args) > tabs_index and isinstance(mutable_args[tabs_index], (list, tuple)):
                labels = mutable_args[tabs_index]
                mutable_args[tabs_index] = type(labels)(
                    translate(item, language) if isinstance(item, str) else item for item in labels
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

    # Module-level functions are pre-bound aliases in Streamlit.
    for method_name in _LOCALIZABLE_STREAMLIT_CALLS:
        wrap_method(st_module, method_name, bound=False)

    # DeltaGenerator powers sidebar, columns, tabs, forms and nested containers.
    # Wrapping its methods covers those UI surfaces without changing their data.
    sidebar = getattr(st_module, "sidebar", None)
    if sidebar is not None:
        generator_type = type(sidebar)
        for method_name in _LOCALIZABLE_STREAMLIT_CALLS:
            wrap_method(generator_type, method_name, bound=True)
