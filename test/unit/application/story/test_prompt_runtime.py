from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from application.story.coordinator import (
    start_or_recover_story_session,
    story_snapshot_patch,
)
from application.story.prompt_runtime import (
    StoryPromptHooks,
    install_story_prompt_hooks,
    load_prompt_session,
)
from application.story.library import prepare_story_launch
from application.chat.session_store import save_template_session
from sdk.hooks import BeforeChatContext, MessageAddedContext, PluginHookDispatcher
from test.unit.application.story.test_library import selected_story


def running_story(tmp_path, response=None):
    state, task, _, _ = selected_story(tmp_path)
    state.chat_session = {"historyPath": str(state.history_dir / "save")}
    session = start_or_recover_story_session(
        state, task["draftPath"], command_id="start"
    )
    adapter = SimpleNamespace(
        chat=Mock(return_value=response or {"nextNodeId": "school-lobby"})
    )
    hooks = StoryPromptHooks(
        state.chat_session["historyPath"], state.config_manager.feature_flags, adapter
    )
    return state, session, adapter, hooks


def context():
    return BeforeChatContext(
        messages=[
            {
                "role": "system",
                "content": "原模板：人物立绘索引、背景索引、dialog 输出格式",
            },
            {"role": "user", "content": "请进去调查"},
        ],
        tools=[{"type": "function", "function": {"name": "normal_workflow"}}],
        generation_kwargs={"temperature": 0.8},
        stream=True,
    )


def response_context():
    message = {
        "role": "assistant",
        "content": json.dumps(
            {
                "dialog": [
                    {
                        "character_name": "临时路人",
                        "speech": "去新地点看看吧。",
                        "sprite": 3,
                        "background": 7,
                        "workflow": "用户原来的 workflow",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    }
    return MessageAddedContext(
        role="assistant", message=message, messages=[*context().messages, message]
    )


def test_injection_keeps_template_tools_generation_settings_and_reply_contract(
    tmp_path,
):
    _, _, adapter, hooks = running_story(tmp_path)
    request = context()
    original = deepcopy(request)
    hooks.before_chat(request)
    assert request.messages[0] == original.messages[0]
    assert request.messages[2:] == original.messages[1:]
    assert "Ling invites" in request.messages[1]["content"]
    assert "speakerAllowlist" not in request.messages[1]["content"]
    assert "characterSetting" not in request.messages[1]["content"]
    assert request.tools == original.tools
    assert request.generation_kwargs == original.generation_kwargs
    assert request.stream is True
    adapter.chat.assert_not_called()


def test_normal_reply_is_unchanged_and_next_request_uses_new_node(tmp_path):
    state, _, adapter, hooks = running_story(tmp_path)
    hooks.publish = Mock()
    hooks.before_chat(context())
    reply = response_context()
    original = deepcopy(reply)
    hooks.message_added(reply)
    assert reply == original
    assert len(adapter.chat.call_args.args[0]) == 2
    assert hooks.publish.call_args.args[0]["currentNodeId"] == "school-lobby"
    assert story_snapshot_patch(state)["story"]["currentNodeId"] == "school-lobby"
    assert state.story_cast_service is None and state.story_scene_service is None
    next_request = context()
    hooks.before_chat(next_request)
    assert "Let the player investigate" in next_request.messages[1]["content"]
    assert "Ling invites" not in next_request.messages[1]["content"]


@pytest.mark.parametrize(
    "decision",
    [{"nextNodeId": "not-a-node"}, "not JSON", {"nextNodeId": ["school-lobby"]}],
)
def test_bad_state_assessment_never_replaces_normal_dialogue(tmp_path, decision):
    state, _, _, hooks = running_story(tmp_path, decision)
    hooks.before_chat(context())
    reply = response_context()
    original = deepcopy(reply)
    hooks.message_added(reply)
    saved = load_prompt_session(
        state.chat_session["historyPath"], state.config_manager.feature_flags
    )
    assert saved.active_branch.state.current_node_id == "school-gate"
    assert saved.active_branch.state.node_turn_count == 1
    assert reply == original


def test_tool_rounds_and_invalid_dialogue_do_not_advance_story(tmp_path):
    state, _, adapter, hooks = running_story(tmp_path)
    hooks.before_chat(context())
    reply = response_context()
    reply.message["tool_calls"] = [{"id": "tool-1"}]
    hooks.message_added(reply)
    reply.message.pop("tool_calls")
    reply.message["content"] = "{broken"
    hooks.message_added(reply)
    adapter.chat.assert_not_called()
    assert (
        load_prompt_session(
            state.chat_session["historyPath"], state.config_manager.feature_flags
        ).active_branch.state.node_turn_count
        == 0
    )


def test_rollback_while_assessment_is_running_discards_stale_result(tmp_path):
    state, _, adapter, hooks = running_story(tmp_path)
    hooks.before_chat(context())

    def switch(*args, **kwargs):
        saved = load_prompt_session(
            state.chat_session["historyPath"], state.config_manager.feature_flags
        )
        saved.fork("different-branch")
        return {"nextNodeId": "school-lobby"}

    adapter.chat.side_effect = switch
    hooks.message_added(response_context())
    saved = load_prompt_session(
        state.chat_session["historyPath"], state.config_manager.feature_flags
    )
    assert saved.active_branch_id == "different-branch"
    assert saved.active_branch.state.current_node_id == "school-gate"


def test_normal_chat_without_binding_is_untouched(tmp_path):
    state, _, adapter, _ = running_story(tmp_path)
    hooks = StoryPromptHooks(
        str(tmp_path / "normal"), state.config_manager.feature_flags, adapter
    )
    request = context()
    original = deepcopy(request)
    hooks.before_chat(request)
    hooks.message_added(response_context())
    assert request == original
    adapter.chat.assert_not_called()


def test_installation_reuses_existing_plugin_hooks(tmp_path):
    state, _, adapter, _ = running_story(tmp_path)
    dispatcher = PluginHookDispatcher()
    existing = Mock()
    dispatcher.register_before_chat(existing)
    manager = SimpleNamespace(hook_dispatcher=dispatcher, llm_adapter=adapter)
    install_story_prompt_hooks(
        manager, state.config_manager, state.chat_session["historyPath"]
    )
    request = context()
    dispatcher.dispatch_before_chat(request)
    existing.assert_called_once()
    assert manager.hook_dispatcher is dispatcher
    assert len(request.messages) == 3


def test_story_launch_inherits_normal_workflow_and_template_options_without_saving(
    tmp_path,
):
    state, task, _, _ = selected_story(tmp_path)
    state.template_dir_path = str(tmp_path / "data" / "templates")
    save_template_session(
        state.template_dir_path,
        {
            "workflow_path": "my-existing-workflow.json",
            "use_cg_yes": True,
            "use_choice_yes": False,
            "use_stat_yes": False,
            "use_tr_yes": False,
            "system_template_text": "用户普通模板",
            "scenario_text": "普通剧情",
            "max_dialog_items": 6,
        },
    )
    path = tmp_path / "data/config/template_tab_last_launch.json"
    before = path.read_bytes()
    launch = prepare_story_launch(state, task["draftPath"])
    assert launch["workflowPath"] == "my-existing-workflow.json"
    assert launch["useCg"] is True and launch["useChoice"] is False
    assert launch["maxDialogItems"] == 6
    args = state.template_generator.generate_chat_template.call_args.args
    assert args[3:7] == (True, False, False, False)
    assert path.read_bytes() == before
