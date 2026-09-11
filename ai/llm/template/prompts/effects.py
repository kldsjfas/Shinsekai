"""The selected effect catalog, rendered inside the runtime system prompt."""

from collections.abc import Callable
from dataclasses import dataclass

from ai.llm.template.core.context import TemplateContext
from ai.llm.template.core.section import Section


@dataclass(frozen=True)
class EffectCatalogEntry:
    label: str
    has_audio: bool = False
    has_image: bool = False


@dataclass(frozen=True, kw_only=True)
class EffectPromptContext(TemplateContext):
    effects: tuple[EffectCatalogEntry, ...] = ()
    translate_effect: Callable[[str], str] | None = None


@dataclass(frozen=True)
class EffectCatalogSection(Section[EffectPromptContext]):
    id: str = "effects"

    def _render_self(self, context: EffectPromptContext) -> str:
        if not context.effects:
            return ""
        if context.translate_effect is None:
            raise ValueError("effect catalog requires a translator")
        translate = context.translate_effect
        lines = [translate("effects_header").strip()]
        for entry in context.effects:
            if entry.has_image:
                kind = "image_audio" if entry.has_audio else "image"
            else:
                kind = "audio"
            modes = "before, after" if entry.has_image else "before, after, loop, stop"
            lines.append(f"- {entry.label} [{translate(f'effect_type_{kind}')}; {modes}]")
        return "\n" + "\n".join(lines)
