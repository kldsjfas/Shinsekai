import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listTemplates, templatesQueryKey } from "../../entities/template/repository";
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
  const templates = useQuery({ queryKey: templatesQueryKey, queryFn: listTemplates });
  const generation = useStoryGeneration();
  const [regenerationStage, setRegenerationStage] = useState<StoryGenerationStage>("narrative");
  const { task, pending, preview } = generation;
  const template = templates.data?.find((item) => item.id === task?.options.templateId);
  return (
    <>
      {templates.isPending && <p role="status">正在加载模板…</p>}
      {templates.isError && (
        <p role="alert">
          {templates.error.message}
          <button type="button" onClick={() => void templates.refetch()}>
            重试
          </button>
        </p>
      )}
      {templates.isSuccess &&
        (templates.data.length ? (
          <StorySetupForm templates={templates.data} pending={pending} onStart={generation.start} />
        ) : (
          <section className="story-generator-card">
            <h2>还没有模板</h2>
            <p>请切换到正常模式，创建并保存一个模板后再来生成剧本。</p>
          </section>
        ))}
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
              <button type="button" disabled={task.cancelRequested} onClick={() => void generation.cancel()}>
                {task.cancelRequested ? "正在取消…" : "取消生成"}
              </button>
            )}
            {["failed", "cancelled"].includes(task.status) && (
              <button type="button" disabled={pending} onClick={() => void generation.resume()}>
                从断点继续
              </button>
            )}
          </div>
          {preview?.graph && <StoryGraphView graph={preview.graph} />}
          <GenerationValidation task={task} />
          {task.status === "succeeded" && (
            <section className="story-generator-card">
              <h2>{preview?.title || "生成的剧本"}</h2>
              <p>使用模板：{template?.name || "原模板已不存在，请选择模板重新生成。"}</p>
              <StoryLaunchButton
                key={`${task.id}-${task.updatedAt}`}
                task={task}
                template={template}
                disabled={pending || !task.validation?.valid || !task.draftPath}
              />
              <details className="story-regenerate">
                <summary>调整并重新生成</summary>
                <p>重做所选阶段及后续阶段，之前的内容会保留。</p>
                <div className="story-generator-actions">
                  <select
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
                  </select>
                  <button
                    disabled={pending}
                    type="button"
                    onClick={() => void generation.regenerate(regenerationStage)}
                  >
                    重新生成
                  </button>
                </div>
              </details>
            </section>
          )}
        </>
      )}
    </>
  );
}

export function StoryGeneratorPage() {
  return (
    <div className="story-generator-page">
      <header className="story-generator-header">
        <h1>让故事成为可游玩的剧本</h1>
        <p>从一个模板开始，逐步生成人物与剧情，查看每段故事如何走向结局。</p>
      </header>
      <StoryFeatureGate>
        <StoryWorkspace />
      </StoryFeatureGate>
    </div>
  );
}
