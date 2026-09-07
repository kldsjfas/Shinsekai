from queue import Queue

from application.chat.presentation_state import (
    PresentationSelectionState,
    catalog_key,
    replay_presentation_selections,
)
from application.chat.dialog_media import AssetCandidate


def test_state_prunes_resolved_media_at_a_message_boundary() -> None:
    state = PresentationSelectionState()
    state.record(
        kind="sprite",
        name="Alice",
        asset_id="1",
        message_count=2,
    )
    state.record(
        kind="sprite",
        name="Alice",
        asset_id="2",
        message_count=4,
    )

    state.prune(2)

    assert state.latest("sprite", name="Alice")["assetId"] == "1"


def test_catalog_key_invalidates_a_selection_after_asset_edits() -> None:
    state = PresentationSelectionState()
    candidates = (AssetCandidate("1", 0, "one", path="one.png", tags="calm"),)
    key = catalog_key(candidates)
    state.record(
        kind="sprite",
        name="Alice",
        asset_id="1",
        message_count=2,
        catalog_key=key,
    )

    assert state.latest("sprite", name="Alice", catalog_key=key) is not None
    assert (
        state.latest(
            "sprite",
            name="Alice",
            catalog_key=catalog_key(
                (AssetCandidate("1", 0, "two", path="two.png", tags="angry"),)
            ),
        )
        is None
    )


def test_replay_restores_latest_branch_owned_media() -> None:
    state = PresentationSelectionState()
    state.record(kind="scene", name="School", asset_id="2", message_count=2)
    state.record(
        kind="bgm",
        name="School",
        asset_id="3",
        path="tense.mp3",
        message_count=2,
    )
    state.record(kind="sprite", name="Alice", asset_id="4", message_count=2)
    output = Queue()

    assert replay_presentation_selections(state, output) is True

    messages = [output.get_nowait(), output.get_nowait(), output.get_nowait()]
    assert [(message.name, message.asset_id) for message in messages] == [
        ("SCENE", "2"),
        ("bgm", "3"),
        ("Alice", "4"),
    ]
    assert messages[1].audio_path == "tense.mp3"
