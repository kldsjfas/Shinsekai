"""Selected sound-effect projection for chat prompts and runtime playback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from core.media.effect_audio import parse_effect_audio_bindings
from core.media.effect_image import ImageEffectAsset


@dataclass(frozen=True)
class SelectedEffectContext:
    """One normalized view of the effects selected for a chat session."""

    selected_names: tuple[str, ...]
    labels: tuple[str, ...]
    keyword_map: dict[str, str]
    image_keyword_map: dict[str, ImageEffectAsset] = field(default_factory=dict)


class EffectConfigReader(Protocol):
    """Narrow configuration dependency required by the chat effect action."""

    def list_effects(self) -> Sequence[Any]: ...


def _selected_name_keys(selected_names: Any) -> set[str]:
    if isinstance(selected_names, str):
        values = selected_names.split(",")
    elif isinstance(selected_names, (list, tuple, set, frozenset)):
        values = selected_names
    else:
        values = []
    return {value.casefold() for item in values if (value := str(item or "").strip())}


def build_effect_context(
    config_reader: EffectConfigReader | None,
    selected_names: Any,
) -> SelectedEffectContext:
    """Build the sole normalized effect view used by prompt and runtime paths.

    ``audio_tags`` and ``audio_list`` are line/index aligned. Empty tag lines are
    deliberately retained so a later label cannot move onto an earlier audio file.
    """

    selected_keys = _selected_name_keys(selected_names)
    if not selected_keys or config_reader is None:
        return SelectedEffectContext((), (), {})

    canonical_names: list[str] = []
    labels: list[str] = []
    seen_labels: set[str] = set()
    keyword_map: dict[str, str] = {}
    image_keyword_map: dict[str, ImageEffectAsset] = {}
    effects = config_reader.list_effects()

    for effect in effects:
        effect_name = str(getattr(effect, "name", "") or "").strip()
        if not effect_name or effect_name.casefold() not in selected_keys:
            continue
        canonical_names.append(effect_name)

        bindings = parse_effect_audio_bindings(
            getattr(effect, "audio_tags", ""),
            getattr(effect, "audio_list", []) or [],
        )
        for binding in bindings:
            keyword_map[binding.keyword.casefold()] = binding.audio_path
            label = binding.source_label or binding.keyword
            keyword_map[label.casefold()] = binding.audio_path
            label_key = label.casefold()
            if label_key not in seen_labels:
                seen_labels.add(label_key)
                labels.append(label)

        images = getattr(effect, "image_list", []) or []
        image_audio = getattr(effect, "image_audio_list", []) or []
        image_tags = str(getattr(effect, "image_tags", "") or "")
        for index, line in enumerate(image_tags.splitlines()):
            if index >= len(images):
                break
            asset = ImageEffectAsset(
                image_path=str(images[index] or ""),
                audio_path=(
                    str(image_audio[index] or "") if index < len(image_audio) else ""
                ),
            )
            for binding in parse_effect_audio_bindings(line, [asset.image_path]):
                label = binding.source_label or binding.keyword
                # Later resources win as a whole, including an absent bound audio.
                image_keyword_map[binding.keyword.casefold()] = asset
                image_keyword_map[label.casefold()] = asset
                label_key = label.casefold()
                if label_key not in seen_labels:
                    seen_labels.add(label_key)
                    labels.append(label)

    return SelectedEffectContext(
        selected_names=tuple(canonical_names),
        labels=tuple(labels),
        keyword_map=keyword_map,
        image_keyword_map=image_keyword_map,
    )
