from dataclasses import replace

import pytest

from ai.llm.template.core.section import Section
from ai.llm.template.effects import (
    EffectCatalogSection,
    EffectPromptContext,
    build_effect_prompt_section,
)
from i18n import tr_in_bundle


AUTHORED_SYSTEM = (
    '  {"speech": "{literal}", "effect": "my field"}\n'
    "Output field contract:\n- character_name (string): keep\n"
    "- camera (string): plugin contract\n"
    "可用音效：\n自定义段落\nRequirements:\n- User rule\n\n  "
)


@pytest.mark.parametrize("language", ["zh_CN", "en", "ja"])
def test_effect_selection_never_rewrites_authored_system_text(language):
    context = EffectPromptContext(
        system_template=AUTHORED_SYSTEM,
        labels=(),
        translate=lambda key: tr_in_bundle(f"template_gen.{key}", language),
    )
    tree = build_effect_prompt_section()
    assert tree.render(context) == AUTHORED_SYSTEM

    selected = replace(context, labels=("letter, sealed letter", "{rain}"))
    result = tree.render(selected)
    assert result == (
        AUTHORED_SYSTEM
        + "\n\n"
        + tr_in_bundle("template_gen.effects_header", language).strip()
        + "\n- letter, sealed letter\n- {rain}"
    )
    assert tree.render(selected) == result
    assert tree.render(context) == AUTHORED_SYSTEM


def test_catalog_can_be_disabled_without_disabling_the_authored_system():
    tree = build_effect_prompt_section()
    assert isinstance(tree, Section)
    context = EffectPromptContext(AUTHORED_SYSTEM, ("rain",), lambda _: "Catalog")
    disabled = replace(
        tree,
        children=tuple(
            replace(child, enabled=False)
            if isinstance(child, EffectCatalogSection)
            else child
            for child in tree.children
        ),
    )
    assert disabled.render(context) == AUTHORED_SYSTEM
    assert tree.render(context).endswith("Catalog\n- rain")


def test_catalog_without_selection_does_not_resolve_translations():
    def unreachable(_key):
        pytest.fail("an empty catalog must not load prompt copy")

    assert (
        build_effect_prompt_section().render(
            EffectPromptContext(AUTHORED_SYSTEM, (), unreachable)
        )
        == AUTHORED_SYSTEM
    )
