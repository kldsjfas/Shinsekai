"""Locale resolution for the runtime effect catalog."""

from i18n import tr


def translate_effect_prompt(key: str) -> str:
    return tr(f"template_gen.{key}")
