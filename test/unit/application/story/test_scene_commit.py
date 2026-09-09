import json

import pytest

from application.chat.runtime_process import _chat_snapshot, _handle_chat_command
from application.story import (
    JsonGlobalStoryProgressStore,
    JsonStorySessionRepository,
    StorySession,
)
from application.story.history_projection import project_story_history
from application.story.scene import SceneOrchestrator
from application.story.session import SceneTurnCommand
from core.chat_history.storage import chat_history_active_path, load_branch_state
from test.unit.application.story.test_chat_integration import _state
from test.unit.application.story.test_scene import _Model
from test.unit.application.story.test_simple_scene_nodes import _dialogue, _simple_scene


def _persisted_scene(tmp_path, *responses):
    session, model, scene = _simple_scene(*responses)
    session.repository = JsonStorySessionRepository(tmp_path / "session")
    session.global_store = JsonGlobalStoryProgressStore(tmp_path / "global")
    session.owner_history_path = str(tmp_path / "session")
    session.replace_history_entries([])
    return session, model, scene


def _recover(session, scene):
    recovered = StorySession.recover(
        session.runtime,
        scene.flags,
        repository=session.repository,
        global_store=session.global_store,
    )
    recovered.owner_history_path = session.owner_history_path
    model = _Model()  # A retry must use the stored reply without calling a model.
    return (
        recovered,
        model,
        SceneOrchestrator(
            scene.flags,
            program=scene.program,
            session=recovered,
            cast_service=scene.cast_service,
            model=model,
        ),
    )


def _crash_after_commit(stage):
    if stage == "after_session_commit":
        raise RuntimeError("simulated crash after commit")


@pytest.mark.parametrize("repair", [False, True])
def test_crash_after_advance_recovers_reply_history_and_receipt_together(
    tmp_path, repair
):
    responses = ([_dialogue("无效目标", "missing")] if repair else []) + [
        _dialogue("走进大厅。", "lobby")
    ]
    session, model, scene = _persisted_scene(tmp_path, *responses)
    initial_generation = session.active_branch.generation
    session.failure_injector = _crash_after_commit

    with pytest.raises(RuntimeError, match="simulated crash"):
        scene.handle_free_text(
            "进去", command_id="turn", message_id="m", user_name="小明"
        )

    recovered, retry_model, retry_scene = _recover(session, scene)
    result = retry_scene.handle_free_text("进去", command_id="turn", message_id="m")

    assert result.duplicate and not result.degraded
    assert result.dialogue[0].text == "走进大厅。"
    assert result.next_node_id == "lobby"
    assert result.revision == recovered.active_branch.state.revision
    assert retry_model.requests == []
    assert len(model.requests) == (2 if repair else 1)
    branch = recovered.active_branch
    assert branch.state.current_node_id == "lobby"
    assert branch.generation == initial_generation + 1
    assert [entry["text"] for entry in branch.history_entries] == [
        "小明: 进去",
        "ling: 走进大厅。",
    ]
    assert branch.checkpoints[-1].history_entries == branch.history_entries
    assert {"turn", "turn:advance"} <= branch.idempotency.records.keys()
    assert recovered.chat_snapshot()["historyEntries"] == list(branch.history_entries)

    fork = recovered.fork("alternate", generation=initial_generation)
    assert fork.state.current_node_id == "opening"
    assert fork.history_entries == ()
    assert fork.idempotency.lookup(SceneTurnCommand("turn", "m", "进去")) is None
    recovered.switch_branch("main")
    assert recovered.active_branch.history_entries == branch.history_entries


def test_failed_write_leaves_no_advance_receipt_or_history(tmp_path, monkeypatch):
    session, _, scene = _persisted_scene(tmp_path, _dialogue("走进大厅。", "lobby"))
    original = session.repository.load()

    def fail_write(_payload):
        raise OSError("disk unavailable")

    monkeypatch.setattr(session.repository, "save", fail_write)

    with pytest.raises(OSError, match="disk unavailable"):
        scene.handle_free_text("进去", command_id="turn", message_id="m")

    assert session.repository.load() == original
    assert session.active_branch.state.current_node_id == "opening"
    assert session.active_branch.history_entries == ()
    assert "turn:advance" not in session.active_branch.idempotency.records
    assert "turn" not in session.active_branch.idempotency.records
    recovered, _, _ = _recover(session, scene)
    assert recovered.active_branch.state == session.active_branch.state


def test_every_persisted_advance_includes_scene_receipt_and_history(
    tmp_path, monkeypatch
):
    session, _, scene = _persisted_scene(
        tmp_path, _dialogue("进大厅", "lobby"), _dialogue("再见", "ending")
    )
    saved = []
    save = session.repository.save

    def capture(payload):
        # Freeze the actual on-disk representation, including later outbox saves.
        save(payload)
        saved.append(session.repository.load())

    monkeypatch.setattr(session.repository, "save", capture)

    for index in range(2):
        scene.handle_free_text(
            "继续", command_id=f"turn-{index}", message_id=f"m-{index}"
        )

    for payload in saved:
        branch = payload["branches"]["main"]
        records = {item["commandId"]: item for item in branch["idempotency"]}
        for index in range(2):
            if f"turn-{index}:advance" in records:
                assert f"turn-{index}" in records
                assert len(branch["historyEntries"]) >= 2 * (index + 1)
    assert session.global_progress.unlocked_ending_ids == {"ending"}


def test_projection_failure_retries_without_regeneration_or_duplicate_history(
    tmp_path, monkeypatch
):
    session, model, scene = _persisted_scene(tmp_path, _dialogue("走进大厅。", "lobby"))
    state = _state(enabled=True)
    state.story_session, state.story_scene_service = session, scene
    state.chat_session["historyPath"] = session.owner_history_path
    command = {"type": "send-message", "cmdId": "turn", "payload": "进去"}

    def fail_projection(_session):
        raise OSError("projection interrupted")

    monkeypatch.setattr(
        "application.chat.runtime_process.project_story_history", fail_projection
    )
    with pytest.raises(OSError, match="projection interrupted"):
        _handle_chat_command(state, command)

    recovered, retry_model, retry_scene = _recover(session, scene)
    state.story_session, state.story_scene_service = recovered, retry_scene
    # Snapshot recovery uses committed history even while the stream is stale.
    assert len(_chat_snapshot(state)["historyEntries"]) == 2
    monkeypatch.setattr(
        "application.chat.runtime_process.project_story_history", project_story_history
    )
    for _ in range(2):
        snapshot = _handle_chat_command(state, command)
    assert len(snapshot["historyEntries"]) == 2
    assert len(model.requests) == 1 and retry_model.requests == []
    messages = json.loads(
        chat_history_active_path(session.owner_history_path).read_text(encoding="utf-8")
    )
    assert messages == [
        {"role": "user", "content": "进去"},
        {"role": "assistant", "name": "ling", "content": "走进大厅。"},
    ]
    tree = load_branch_state(session.owner_history_path)
    assert tree["branches"]["main"]["messages"] == messages
