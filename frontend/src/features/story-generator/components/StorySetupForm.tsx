import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { backgroundsQueryKey, listBackgrounds } from "../../../entities/background/repository";
import type { StoryGenerationInput, TemplateSummary } from "../../../shared/platform/types";

export function StorySetupForm({
  templates,
  pending,
  onStart,
}: {
  templates: TemplateSummary[];
  pending: boolean;
  onStart: (input: StoryGenerationInput) => void;
}) {
  const [templateId, setTemplateId] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const backgrounds = useQuery({ queryKey: backgroundsQueryKey, queryFn: listBackgrounds });
  const template = templates.find((item) => item.id === templateId);
  return (
    <section className="story-generator-card" aria-labelledby="story-setup-title">
      <h2 id="story-setup-title">1. 选择模板，确定故事</h2>
      <label className="story-setup-field">
        故事模板
        <select
          aria-label="故事模板"
          value={templateId}
          disabled={pending}
          onChange={(event) => {
            const next = templates.find((item) => item.id === event.target.value);
            setTemplateId(event.target.value);
            setSynopsis(next?.scenario?.trim() || next?.content || "");
          }}
        >
          <option value="">请选择已有模板</option>
          {templates.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <p>模板提供故事起点。你可以在下面调整人物、冲突和结局方向，原模板会保留。</p>
      <label className="story-setup-field">
        剧情梗概
        <textarea
          aria-label="剧情梗概"
          disabled={pending}
          maxLength={20000}
          rows={6}
          value={synopsis}
          onChange={(event) => setSynopsis(event.target.value)}
          placeholder="选择模板后，在这里调整希望发生的故事……"
        />
      </label>
      <p>
        可用地点：
        {backgrounds.isPending
          ? "加载中…"
          : backgrounds.data
              ?.filter((item) => item.sprites.length)
              .map((item) => item.name)
              .join("、") || "暂无背景，生成时将自由描述地点"}
      </p>
      {backgrounds.isError && (
        <p role="alert">
          地点加载失败。
          <button type="button" onClick={() => void backgrounds.refetch()}>
            重试
          </button>
        </p>
      )}
      <div className="story-generator-actions">
        <button
          type="button"
          disabled={pending || !template || !synopsis.trim() || !backgrounds.isSuccess}
          onClick={() =>
            onStart({
              synopsis,
              options: {
                targetLength: "short",
                controlMode: "deterministic",
                templateId: template!.id,
              },
              resourceCatalog: {
                backgrounds: (backgrounds.data ?? []).filter((item) => item.sprites.length).map((item) => item.name),
              },
            })
          }
        >
          {pending ? "生成中…" : "开始生成"}
        </button>
        <small>各阶段完成后可查看内容。</small>
      </div>
    </section>
  );
}
