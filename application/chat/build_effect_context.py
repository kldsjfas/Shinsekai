"""Selected sound-effect projection for chat prompts and runtime playback."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from core.media.effect_audio import parse_effect_audio_bindings
from i18n import tr as tr_i18n


_LEGACY_EFFECT_HEADERS = (
    "已选特效提示：",
    "可用音效：",
    "音效触发时机与模式：",
)
_EFFECT_CATALOG_HEADERS = (
    "可用特效标签（",
    "Available effect labels (",
    "利用可能なエフェクトラベル（",
)
_PROMPT_SECTION_BOUNDARIES = (
    "立绘说明:",
    "Sprite sheets:",
    "立ち絵の説明:",
    "可调用工具",
    "Callable tools",
    "呼び出し可能なツール",
    "要求：",
    "Requirements:",
    "要件：",
)
_CATALOG_INSERT_BOUNDARIES = (
    "可调用工具",
    "Callable tools",
    "呼び出し可能なツール",
    "要求：",
    "Requirements:",
    "要件：",
)
_BUILTIN_FIELD_PREFIXES = (
    "- character_name (",
    "- sprite (",
    "- speech (",
    "- effect (",
    "- translate (",
)


def _line_marker_position(text: str, markers: tuple[str, ...], start: int = 0) -> int:
    positions = [
        match.start()
        for marker in markers
        if (match := re.search(rf"(?m)^{re.escape(marker)}", text[start:]))
    ]
    return start + min(positions) if positions else -1


def _strip_effect_prompt_sections(system_template: str) -> str:
    template = str(system_template or "")

    start = _line_marker_position(template, _LEGACY_EFFECT_HEADERS)
    while start >= 0:
        end = _line_marker_position(template, _PROMPT_SECTION_BOUNDARIES, start)
        before = template[:start].rstrip()
        after = template[end:].lstrip() if end >= 0 else ""
        template = f"{before}\n\n{after}" if before and after else before or after
        start = _line_marker_position(template, _LEGACY_EFFECT_HEADERS)

    lines = template.splitlines()
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if any(line.startswith(header) for header in _EFFECT_CATALOG_HEADERS):
            index += 1
            while index < len(lines) and (
                not lines[index].strip() or lines[index].startswith("- ")
            ):
                index += 1
            while cleaned and not cleaned[-1].strip():
                cleaned.pop()
            if cleaned and index < len(lines):
                cleaned.append("")
            continue
        cleaned.append(line)
        index += 1
    return "\n".join(cleaned).strip()


def _strip_builtin_output_contract(system_template: str) -> str:
    lines = str(system_template or "").splitlines()
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != "Output field contract:":
            cleaned.append(lines[index])
            index += 1
            continue

        index += 1
        preserved: list[str] = []
        while index < len(lines) and (
            not lines[index].strip() or lines[index].startswith("- ")
        ):
            line = lines[index]
            if line.strip() and not line.startswith(_BUILTIN_FIELD_PREFIXES):
                preserved.append(line)
            index += 1
        while cleaned and not cleaned[-1].strip():
            cleaned.pop()
        if preserved:
            if cleaned:
                cleaned.append("")
            cleaned.extend(preserved)
        if cleaned and index < len(lines):
            cleaned.append("")
    return "\n".join(cleaned).strip()


def _strip_effect_contract(system_template: str) -> str:
    lines = []
    for line in str(system_template or "").splitlines():
        stripped = line.strip()
        if stripped.startswith('"effect":'):
            continue
        if stripped.startswith(
            (
                "- 特效使用：effect 可选",
                "- Effect: optional",
                "- effect：任意",
            )
        ):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _insert_effect_contract(system_template: str) -> str:
    lines = str(system_template or "").splitlines()
    json_effect_line = tr_i18n("template_gen.json_line_effect").rstrip("\r\n")
    effect_rule = f'- {tr_i18n("template_gen.r_effect").strip()}'

    speech_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().startswith('"speech":')
        ),
        -1,
    )
    if speech_index >= 0:
        lines.insert(speech_index + 1, json_effect_line)

    requirement_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith(("要求：", "Requirements:", "要件："))
        ),
        -1,
    )
    if requirement_index >= 0:
        last_rule_index = max(
            (
                index
                for index in range(requirement_index + 1, len(lines))
                if lines[index].startswith("- ")
            ),
            default=requirement_index,
        )
        lines.insert(last_rule_index + 1, effect_rule)
    return "\n".join(lines).strip()


def _replace_prompt_catalog(system_template: str, prompt_catalog: str) -> str:
    template = _strip_effect_contract(
        _strip_builtin_output_contract(
            _strip_effect_prompt_sections(system_template)
        )
    )
    catalog = str(prompt_catalog or "").strip()
    if not catalog:
        return template

    template = _insert_effect_contract(template)

    boundary = _line_marker_position(template, _CATALOG_INSERT_BOUNDARIES)
    if boundary < 0:
        return f"{template}\n\n{catalog}" if template else catalog
    before = template[:boundary].rstrip()
    after = template[boundary:].lstrip()
    return f"{before}\n\n{catalog}\n\n{after}" if before else f"{catalog}\n\n{after}"


@dataclass(frozen=True)
class SelectedEffectContext:
    """One normalized view of the effects selected for a chat session."""

    selected_names: tuple[str, ...]
    labels: tuple[str, ...]
    keyword_map: dict[str, str]
    prompt_catalog: str
    image_keyword_map: dict[str, str] = field(default_factory=dict)
    image_audio_keyword_map: dict[str, str] = field(default_factory=dict)

    def append_prompt_catalog(self, system_template: str) -> str:
        return _replace_prompt_catalog(system_template, self.prompt_catalog)


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
        return SelectedEffectContext((), (), {}, "")

    canonical_names: list[str] = []
    labels: list[str] = []
    seen_labels: set[str] = set()
    keyword_map: dict[str, str] = {}
    image_keyword_map: dict[str, str] = {}
    image_audio_keyword_map: dict[str, str] = {}
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
            keyword_map[binding.keyword] = binding.audio_path
            label = binding.source_label or binding.keyword
            keyword_map[label] = binding.audio_path
            label_key = label.casefold()
            if label_key not in seen_labels:
                seen_labels.add(label_key)
                labels.append(label)

        image_bindings = parse_effect_audio_bindings(
            getattr(effect, "image_tags", ""),
            getattr(effect, "image_list", []) or [],
        )
        image_audio_bindings = parse_effect_audio_bindings(
            getattr(effect, "image_tags", ""),
            getattr(effect, "image_audio_list", []) or [],
        )
        for binding in image_bindings:
            image_keyword_map[binding.keyword] = binding.audio_path
            label = binding.source_label or binding.keyword
            image_keyword_map[label] = binding.audio_path
            label_key = label.casefold()
            if label_key not in seen_labels:
                seen_labels.add(label_key)
                labels.append(label)
        for binding in image_audio_bindings:
            image_audio_keyword_map[binding.keyword] = binding.audio_path
            image_audio_keyword_map[
                binding.source_label or binding.keyword
            ] = binding.audio_path

    prompt_catalog = ""
    if labels:
        header = tr_i18n("template_gen.effects_header").strip()
        prompt_catalog = "\n".join([header, *(f"- {label}" for label in labels)])

    return SelectedEffectContext(
        selected_names=tuple(canonical_names),
        labels=tuple(labels),
        keyword_map=keyword_map,
        prompt_catalog=prompt_catalog,
        image_keyword_map=image_keyword_map,
        image_audio_keyword_map=image_audio_keyword_map,
    )
