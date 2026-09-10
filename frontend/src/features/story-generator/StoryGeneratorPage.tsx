import { Button, Select } from "../../shared/ui";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { SegmentedTabs } from "../../shared/ui/SegmentedTabs";
import { StoryLibrary } from "./components/StoryLibrary";
import type { StoryGenerationStage } from "../../entities/story/types";
import { StoryFeatureGate } from "./components/StoryFeatureGate";
import { StorySetupForm } from "./components/StorySetupForm";
import { GenerationStages } from "./components/GenerationStages";
import { GenerationValidation } from "./components/GenerationValidation";
import { StoryLaunchButton } from "./components/StoryLaunchButton";
import { StoryGraphView } from "./graph/StoryGraphView";
import { useStoryGeneration } from "./state/useStoryGeneration";
import { stages } from "./state/stages";
import "./StoryGeneratorPage.css";

function StoryWorkspace() {
  const [params] = useSearchParams();
  const [view, setView] = useState<"create" | "library">(() =>
    params.get("view") === "library" ? "library" : "create",
  );
  const generation = useStoryGeneration();
  const [regenerationStage, setRegenerationStage] = useState<StoryGenerationStage>("narrative");
  const { task, pending, preview } = generation;
  return (
    <>
      <SegmentedTabs
        ariaLabel="剧本入口"
        idPrefix="story-view"
        value={view}
        onChange={setView}
        items={[
          { id: "create", label: "创作新剧本" },
          { id: "library", label: "已有剧本" },
        ]}
      />
      <div
        role="tabpanel"
        id="story-view-panel-library"
        aria-labelledby="story-view-library"
        hidden={view !== "library"}
      >
        {view === "library" && <StoryLibrary onCreate={() => setView("create")} />}
      </div>
      <div role="tabpanel" id="story-view-panel-create" aria-labelledby="story-view-create" hidden={view !== "create"}>
        <StorySetupForm pending={pending} onStart={generation.start} />
        {generation.error && (
          <p className="story-generator-error" role="alert">
            {generation.error}
          </p>
        )}
        {task && (
          <>
            <GenerationStages task={task} preview={preview} />
            <div className="story-generator-actions">
              {pending && (
                <Button type="button" disabled={task.cancelRequested} onClick={() => void generation.cancel()}>
                  {task.cancelRequested ? "正在取消…" : "取消生成"}
                </Button>
              )}
            </div>
            {preview?.graph && <StoryGraphView graph={preview.graph} />}
            <GenerationValidation task={task} />
            {task.status === "succeeded" && (
              <section className="section">
                <h2 className="section__title">{preview?.title || "生成的剧本"}</h2>
                <p className="section__description">剧本已保存，可立即游玩或稍后从已有剧本中继续。</p>
                <StoryLaunchButton
                  key={`${task.id}-${task.updatedAt}`}
                  storyPath={task.draftPath}
                  disabled={pending || !task.validation?.valid || !task.draftPath}
                />
                <details className="story-regenerate">
                  <summary>调整并重新生成</summary>
                  <p className="section__description">重做所选阶段及后续阶段，之前的内容会保留。</p>
                  <div className="story-generator-actions">
                    <Select
                      aria-label="重新生成阶段"
                      value={regenerationStage}
                      disabled={pending}
                      onChange={(event) => setRegenerationStage(event.target.value as StoryGenerationStage)}
                    >
                      {stages.map((stage) => (
                        <option key={stage.id} value={stage.id}>
                          {stage.label}
                        </option>
                      ))}
                    </Select>
                    <Button
                      disabled={pending}
                      type="button"
                      onClick={() => void generation.regenerate(regenerationStage)}
                    >
                      重新生成
                    </Button>
                  </div>
                </details>
              </section>
            )}
          </>
        )}
      </div>
    </>
  );
}

export function StoryGeneratorPage() {
  return (
    <div className="page story-generator-page">
      <header className="page__header">
        <div>
          <h1 className="page__title">让故事成为可游玩的剧本</h1>
          <p className="section__description">选择人物和背景创作新剧本，或从已有剧本继续你的故事。</p>
        </div>
      </header>
      <StoryFeatureGate>
        <StoryWorkspace />
      </StoryFeatureGate>
    </div>
  );
}
