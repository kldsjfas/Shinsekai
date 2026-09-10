import type { StoryGenerationTask } from "../../../entities/story/types";
import type { StoryGenerationPreview } from "../../../shared/platform/storyPreviewTypes";
import { stages, taskStatus } from "../state/stages";

const labels: Record<string, string> = {
  title: "标题",
  premise: "故事前提",
  themes: "主题",
  worldRules: "世界规则",
  immutableFacts: "既定事实",
  secrets: "隐藏信息",
  assumptions: "创作假设",
  characters: "人物",
  name: "姓名",
  responsibility: "故事职责",
  personality: "人物设定",
  description: "描述",
  profile: "人物设定",
  setting: "设定",
  summary: "简介",
};

function ArtifactContent({ value }: { value: unknown }) {
  if (Array.isArray(value))
    return (
      <ul>
        {value.map((item, index) => (
          <li key={index}>
            <ArtifactContent value={item} />
          </li>
        ))}
      </ul>
    );
  if (value && typeof value === "object")
    return (
      <dl className="story-artifact">
        {Object.entries(value)
          .filter(([key]) => key in labels)
          .map(([key, item]) => (
            <div key={key}>
              <dt>{labels[key]}</dt>
              <dd>
                <ArtifactContent value={item} />
              </dd>
            </div>
          ))}
      </dl>
    );
  return <span>{String(value ?? "")}</span>;
}

export function GenerationStages({ task, preview }: { task: StoryGenerationTask; preview?: StoryGenerationPreview }) {
  return (
    <section className="section" aria-labelledby="story-progress-title">
      <h2 className="section__title" id="story-progress-title">
        生成进度
      </h2>
      <p className="section__description" role="status" aria-live="polite">
        {taskStatus[task.status]}
        {task.currentStage === "repair" ? " · 正在修复校验问题" : ""}
      </p>
      {task.recovery && !task.cancelRequested && task.status === "running" && (
        <div className="section__description" role="status">
          <p>{task.recovery.message}。无需手动继续，离开页面后后台仍会处理。</p>
          {!!task.recovery.attempt && (
            <p>
              已自动恢复 {task.recovery.attempt} 次 · 已尝试修复 {task.repairAttempts} 次
            </p>
          )}
          {!!task.recovery.nextRetryAt && (
            <p>下次自动重试：{new Date(task.recovery.nextRetryAt).toLocaleTimeString()}</p>
          )}
          {task.recovery.lastError && (
            <details>
              <summary>查看本次错误</summary>
              <p>{task.recovery.lastError.message}</p>
            </details>
          )}
        </div>
      )}
      <ol className="story-generator-stages">
        {stages.map((stage) => {
          const completed = task.completedStages.includes(stage.id);
          const current = task.currentStage === stage.id;
          return (
            <li key={stage.id} className={completed ? "completed" : current ? "active" : ""}>
              <span aria-hidden>{completed ? "✓" : current ? "◉" : "○"}</span>
              {stage.label}
              <small>{completed ? "已完成" : current ? "处理中" : "等待中"}</small>
            </li>
          );
        })}
      </ol>
      <div className="story-stage-artifacts">
        {stages.map((stage) => (
          <details key={stage.id}>
            <summary>
              {stage.label}
              <small>{stage.description}</small>
            </summary>
            {preview?.artifacts[stage.id] ? (
              <>
                {stage.id === "narrative" ? (
                  <p className="section__description">
                    已生成 {preview.graph?.nodes.length ?? 0} 个节点，详见下方剧本图。
                  </p>
                ) : (
                  <ArtifactContent value={preview.artifacts[stage.id]} />
                )}
                <details>
                  <summary>查看完整阶段内容</summary>
                  <pre>{JSON.stringify(preview.artifacts[stage.id], null, 2)}</pre>
                </details>
              </>
            ) : (
              <p className="section__description">
                {task.completedStages.includes(stage.id) ? "正在读取阶段内容…" : "阶段完成后可查看。"}
              </p>
            )}
          </details>
        ))}
      </div>
    </section>
  );
}
