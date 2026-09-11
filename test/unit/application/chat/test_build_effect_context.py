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


def test_selected_effect_context_builds_labels_and_runtime_maps():
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


def test_selected_effect_context_preserves_blank_tag_indexes():
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


def test_selected_effect_context_does_not_invent_labels():
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
    assert "打字" not in context.labels
    assert "雨天" not in context.labels


def test_selected_effect_context_includes_image_and_bound_audio():
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
