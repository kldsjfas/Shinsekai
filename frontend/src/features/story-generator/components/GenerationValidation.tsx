import type { StoryGenerationTask } from "../../../entities/story/types";

export function GenerationValidation({ task }: { task: StoryGenerationTask }) {
  return (
    <section className="section" aria-labelledby="story-validation-title">
      <h2 className="section__title" id="story-validation-title">
        可运行检查
      </h2>
      {task.validation ? (
        <>
          <p className={task.validation.valid ? "story-generator-pass" : "story-generator-error"}>
            {task.validation.valid
              ? "已通过确定性校验"
              : task.cancelRequested || task.status === "cancelled"
                ? "已停止修复，当前剧本尚未通过检查"
                : "正在自动修复问题，通过检查后即可游玩"}
          </p>
          <p className="section__description">
            可达结局 {Math.round(task.validation.endingCoverage * 100)}% · 检查了 {task.validation.exploredStates}{" "}
            个路径状态
          </p>
          {!!task.validation.issues.length && (
            <ul>
              {task.validation.issues.map((issue, index) => (
                <li key={index}>{issue.message}</li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <p className="section__description">剧情节点生成后，将检查跳转目标、人物资源与结局路径。</p>
      )}
      {!!task.assumptions.length && (
        <details>
          <summary>创作假设</summary>
          <ul>
            {task.assumptions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
