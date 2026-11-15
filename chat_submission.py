"""Helpers for safely capturing chat submissions across Streamlit reruns."""


def normalize_chat_prompt(value):
    """Return a trimmed non-empty chat prompt, or None for an empty draft."""
    if not isinstance(value, str):
        return None
    prompt = value.strip()
    return prompt or None
