from types import SimpleNamespace

from application.chat.build_effect_context import build_effect_context


def _manager(*effects):
    return SimpleNamespace(list_effects=lambda: list(effects))


def _effect(name: str, audio_tags: str, audio_list: list[str], **values):
    return SimpleNamespace(
        name=name,
        audio_tags=audio_tags,
        audio_list=audio_list,
        image_tags=values.get("image_tags", ""),
        image_list=values.get("image_list", []),
        image_audio_list=values.get("image_audio_list", []),
    )


def test_selected_effect_context_is_empty_without_a_selection():
    context = build_effect_context(_manager(), [])

    assert context.selected_names == ()
    assert context.labels == ()
    assert context.keyword_map == {}
    assert context.image_keyword_map == {}
    assert context.image_audio_keyword_map == {}
    assert context.prompt_catalog == ""
    assert context.append_prompt_catalog("system") == "system"


def test_empty_selection_removes_migrated_effect_prompt_sections():
    context = build_effect_context(_manager(), [])
    template = (
        "JSON\n\nOutput field contract:\n- character_name (string): built in\n"
        "- camera (string): plugin field\n\ncharacter\n\n"
        "已选特效提示：\nold image\n\n"
        "音效触发时机与模式：\n- loop:old\n\n"
        '可用音效：\nold audio\n\n可调用工具\n- search\n\n要求：\n'
        '- normal rule\n- 特效使用：effect 可选，old rule\n\n'
        '    "speech": "line",\n    "effect": "old effect",'
    )

    rendered = context.append_prompt_catalog(template)

    assert "已选特效提示：" not in rendered
    assert "可用音效：" not in rendered
    assert "特效使用：effect 可选" not in rendered
    assert '"effect":' not in rendered
    assert "Output field contract:" not in rendered
    assert "- character_name (" not in rendered
    assert "- camera (string): plugin field" in rendered
    assert "可调用工具\n- search" in rendered


def test_selected_effect_context_builds_prompt_and_runtime_map_once(monkeypatch):
    monkeypatch.setattr(
        "application.chat.build_effect_context.tr_i18n",
        lambda key: "Available labels" if key == "template_gen.effects_header" else key,
    )
    context = build_effect_context(
        _manager(
            _effect(
                "Ambient",
                "Effect 1：door, open door\nEffect 2：cloth，rustle\n",
                ["door.wav", "cloth.wav"],
            ),
            _effect("Other", "Effect 1：unused\n", ["unused.wav"]),
        ),
        [" ambient ", "missing"],
    )

    assert context.selected_names == ("Ambient",)
    assert context.labels == ("door, open door", "cloth，rustle")
    assert context.keyword_map == {
        "door": "door.wav",
        "open door": "door.wav",
        "door, open door": "door.wav",
        "cloth": "cloth.wav",
        "rustle": "cloth.wav",
        "cloth，rustle": "cloth.wav",
    }
    assert context.prompt_catalog == (
        "Available labels\n- door, open door\n- cloth，rustle"
    )
    assert context.append_prompt_catalog("character\n\nCallable tools\n- search") == (
        "character\n\nAvailable labels\n- door, open door\n- cloth，rustle"
        "\n\nCallable tools\n- search"
    )


def test_selected_effect_context_replaces_existing_catalog_once(monkeypatch):
    translations = {
        "template_gen.effects_header": "可用特效标签（仅在实际发生时使用）：",
        "template_gen.json_line_effect": '    "effect": "新说明",\n',
        "template_gen.r_effect": "特效使用：effect 可选，新规则",
    }
    monkeypatch.setattr(
        "application.chat.build_effect_context.tr_i18n",
        translations.__getitem__,
    )
    context = build_effect_context(
        _manager(_effect("Current", "特效 1：雨声\n", ["rain.wav"])),
        ["Current"],
    )
    template = (
        'JSON\n    "speech": "台词",\n    "effect": "旧说明",\n\n角色\n\n场景\n\n'
        "可用特效标签（仅在实际发生时使用）：\n- 旧标签\n\n"
        "要求：\n- 规则\n- 特效使用：effect 可选，旧规则\n\n开始场景"
    )

    rendered = context.append_prompt_catalog(template)

    assert rendered.count("可用特效标签（") == 1
    assert "- 旧标签" not in rendered
    assert rendered.count('"effect":') == 1
    assert rendered.count("- 特效使用：effect 可选") == 1
    assert rendered.index("场景") < rendered.index("可用特效标签（") < rendered.index("要求：")


def test_selected_effect_context_preserves_blank_tag_indexes(monkeypatch):
    monkeypatch.setattr(
        "application.chat.build_effect_context.tr_i18n", lambda _key: "Labels"
    )
    context = build_effect_context(
        _manager(
            _effect(
                "Ambient",
                "Effect 1：impact\n\nEffect 3：notice\n",
                ["a1.wav", "a2.wav", "a3.wav"],
            )
        ),
        "Ambient",
    )

    assert context.keyword_map == {
        "impact": "a1.wav",
        "notice": "a3.wav",
    }
    assert "a2.wav" not in context.keyword_map.values()


def test_selected_effect_context_does_not_invent_labels(monkeypatch):
    monkeypatch.setattr(
        "application.chat.build_effect_context.tr_i18n", lambda _key: "Labels"
    )
    context = build_effect_context(
        _manager(
            _effect(
                "Custom",
                "Effect 1：typing\nEffect 2：rain\n",
                ["typing.wav", "rain.wav"],
            )
        ),
        ["Custom"],
    )

    assert context.labels == ("typing", "rain")
    assert "打字" not in context.prompt_catalog
    assert "雨天" not in context.prompt_catalog


def test_selected_effect_context_includes_image_and_bound_audio(monkeypatch):
    monkeypatch.setattr(
        "application.chat.build_effect_context.tr_i18n", lambda _key: "Labels"
    )
    context = build_effect_context(
        _manager(
            _effect(
                "Items",
                "",
                [],
                image_tags="图片 1：letter, sealed letter\n",
                image_list=["letter.png"],
                image_audio_list=["paper.wav"],
            )
        ),
        ["Items"],
    )

    assert context.labels == ("letter, sealed letter",)
    assert context.image_keyword_map == {
        "letter": "letter.png",
        "sealed letter": "letter.png",
        "letter, sealed letter": "letter.png",
    }
    assert context.image_audio_keyword_map == {
        "letter": "paper.wav",
        "sealed letter": "paper.wav",
        "letter, sealed letter": "paper.wav",
    }
