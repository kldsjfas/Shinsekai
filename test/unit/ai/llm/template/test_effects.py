from dataclasses import replace

import pytest

from ai.llm.template.prompts.effects import EffectCatalogEntry, EffectCatalogSection
from ai.llm.template.prompts.system import (
    RuntimePromptContext,
    build_runtime_prompt_section,
)
from i18n import tr_in_bundle


AUTHORED_SYSTEM = (
    '  {"speech": "{literal}", "effect": "my field"}\n'
    "Output field contract:\n- camera (string): plugin contract\n"
    "可用音效：\n自定义段落\nRequirements:\n- User rule\n\n  "
)


@pytest.mark.parametrize("language", ["zh_CN", "en", "ja"])
def test_catalog_is_one_runtime_section_and_preserves_authored_text(language):
    translate = lambda key: tr_in_bundle(f"template_gen.{key}", language)
    context = RuntimePromptContext(
        system_template=AUTHORED_SYSTEM,
        user_scenario="Scenario",
        json_reminder="Reminder",
        translate_effect=translate,
    )
    tree = build_runtime_prompt_section()
    assert tree.render(context) == AUTHORED_SYSTEM + "\nScenario\nReminder"
    selected = replace(
        context,
        effects=(
            EffectCatalogEntry("letter, sealed letter", has_image=True),
            EffectCatalogEntry("{rain}", has_audio=True),
            EffectCatalogEntry("key", has_image=True, has_audio=True),
        ),
    )
    result = tree.render(selected)
    assert result == (
        AUTHORED_SYSTEM + "\n\n" + translate("effects_header").strip()
        + f"\n- letter, sealed letter [{translate('effect_type_image')}; before, after]"
        + f"\n- {{rain}} [{translate('effect_type_audio')}; before, after, loop, stop]"
        + f"\n- key [{translate('effect_type_image_audio')}; before, after]"
        + "\nScenario\nReminder"
    )
    disabled = replace(
        tree,
        children=tuple(
            replace(child, enabled=False)
            if isinstance(child, EffectCatalogSection)
            else child
            for child in tree.children
        ),
    )
    assert disabled.render(selected) == tree.render(context)


def test_empty_catalog_does_not_resolve_translations():
    def unreachable(_key):
        pytest.fail("an empty catalog must not load prompt copy")

    context = RuntimePromptContext(
        system_template=AUTHORED_SYSTEM,
        user_scenario="",
        json_reminder="",
        translate_effect=unreachable,
    )
    assert build_runtime_prompt_section().render(context) == AUTHORED_SYSTEM
