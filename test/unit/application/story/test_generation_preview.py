from copy import deepcopy

import pytest

from application.story.generation import StoryGenerationError, StoryGenerationStage
from application.story.generation_preview import generation_preview
from config.feature_flags import FeatureDisabledError, FeatureFlagConfigManager
from test.unit.application.story.test_generation import (
    ScriptedModel,
    service_at,
    stage_artifacts,
)


def test_preview_exposes_only_completed_checkpoints(tmp_path):
    service, repository = service_at(tmp_path, ScriptedModel({}))
    task = service.create("Story")
    artifacts = stage_artifacts()
    repository.save_artifact(task["id"], StoryGenerationStage.FOUNDATION, artifacts["foundation"])
    repository.save_artifact(task["id"], StoryGenerationStage.NARRATIVE, artifacts["narrative"])
    task["completedStages"] = ["foundation"]
    repository.save(task)

    preview = generation_preview(service, task["id"])
    assert preview["artifacts"] == {"foundation": artifacts["foundation"]}
    assert preview["graph"] is None
    assert preview["title"] == artifacts["foundation"]["title"]


def test_preview_prefers_repaired_draft_and_clears_regenerated_graph(tmp_path):
    service, repository = service_at(tmp_path, ScriptedModel({}))
    task = service.create("Story")
    artifacts = stage_artifacts()
    for stage in StoryGenerationStage:
        repository.save_artifact(task["id"], stage, artifacts[stage.value])
    task["completedStages"] = [stage.value for stage in StoryGenerationStage]
    repository.save(task)
    graph = deepcopy(artifacts["narrative"])
    graph["nodes"][0]["title"] = "Repaired opening"
    repository.save_draft(task["id"], {"title": "Repaired", "narrativeGraph": graph})

    assert generation_preview(service, task["id"])["graph"] == graph
    service.regenerate_from(task["id"], StoryGenerationStage.NARRATIVE)
    assert generation_preview(service, task["id"])["graph"] is None


def test_preview_keeps_feature_and_task_path_guards(tmp_path):
    service, _ = service_at(tmp_path, ScriptedModel({}))
    with pytest.raises(StoryGenerationError, match="safe identifier"):
        generation_preview(service, "../outside")
    service.flags = FeatureFlagConfigManager(environ={})
    with pytest.raises(FeatureDisabledError):
        generation_preview(service, "test")
