"""Append the selected runtime catalog without rewriting an authored template."""

from dataclasses import dataclass
from typing import Callable

from ai.llm.template.core.context import TemplateContext
from ai.llm.template.core.section import Section, TextSection


@dataclass(frozen=True)
class EffectPromptContext(TemplateContext):
    system_template: str
    labels: tuple[str, ...]
    translate: Callable[..., str]


@dataclass(frozen=True)
class EffectCatalogSection(Section[EffectPromptContext]):
    id: str = "effects"

    def _render_self(self, context: EffectPromptContext) -> str:
        if not context.labels:
            return ""
        header = context.translate("effects_header").strip()
        return "\n".join((header, *(f"- {label}" for label in context.labels)))


def build_effect_prompt_section() -> Section[EffectPromptContext]:
    return Section(
        "runtime.effects",
        separator="\n\n",
        children=(
            TextSection("system", text=lambda context: context.system_template),
            EffectCatalogSection(),
        ),
    )
