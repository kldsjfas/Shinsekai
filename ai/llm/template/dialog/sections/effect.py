"""Selected runtime effect catalog."""

from dataclasses import dataclass

from ...core import Section
from ..context import DialogTemplateContext


@dataclass(frozen=True)
class EffectCatalogSection(Section[DialogTemplateContext]):
    id: str = "effects"

    def _render_self(self, context: DialogTemplateContext) -> str:
        if not context.use_effect or not context.effect_catalog:
            return ""
        header = context.translate("effects_header").strip()
        labels = "\n".join(f"- {label}" for label in context.effect_catalog)
        return f"{header}\n{labels}\n"
