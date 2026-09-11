"""Locale resolution for the runtime effect catalog."""

from ai.llm.template.effects import EffectPromptContext, build_effect_prompt_section
from i18n import tr


def append_effect_catalog(system_template: str, labels: tuple[str, ...]) -> str:
    context = EffectPromptContext(
        system_template=system_template,
        labels=labels,
        translate=lambda key: tr(f"template_gen.{key}"),
    )
    return build_effect_prompt_section().render(context)
