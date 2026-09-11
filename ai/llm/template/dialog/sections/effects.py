"""Selected audio and image effect catalogs for dialogue."""

from dataclasses import dataclass

from ai.llm.template.core.section import Section
from ai.llm.template.dialog.context import EffectCatalogContext


@dataclass(frozen=True)
class EffectCatalogSection(Section[EffectCatalogContext]):
    id: str = "effects"

    def _render_self(self, context: EffectCatalogContext) -> str:
        if not context.effects:
            return ""
        if context.translate is None:
            raise ValueError("effect catalog requires a translator")
        translate = context.translate
        lines = [translate("effects_header").strip()]
        for entry in context.effects:
            if entry.has_image:
                kind = "image_audio" if entry.has_audio else "image"
            else:
                kind = "audio"
            modes = "before, after" if entry.has_image else "before, after, loop, stop"
            lines.append(f"- {entry.label} [{translate(f'effect_type_{kind}')}; {modes}]")
        return "\n" + "\n".join(lines)
