import { SegmentedTabs } from "../../shared/ui/SegmentedTabs";
import { lazy, Suspense, useState } from "react";
import { useSearchParams } from "react-router-dom";
import "./TemplateWorkspacePage.css";

const NormalMode = lazy(() =>
  import("../template-editor/TemplateEditorPage").then(({ TemplateEditorPage }) => ({ default: TemplateEditorPage })),
);
const StoryMode = lazy(() =>
  import("../story-generator/StoryGeneratorPage").then(({ StoryGeneratorPage }) => ({ default: StoryGeneratorPage })),
);
const modes = [
  { id: "normal", label: "正常模式" },
  { id: "story", label: "剧本模式" },
] as const;

export function TemplateWorkspacePage() {
  const [params, setParams] = useSearchParams();
  const mode = params.get("mode") === "story" ? "story" : "normal";
  const [visited, setVisited] = useState(() => new Set([mode]));
  const select = (next: typeof mode) => {
    setVisited((previous) => new Set([...previous, next]));
    setParams((previous) => {
      previous.set("mode", next);
      return previous;
    });
  };
  return (
    <div className="template-workspace">
      <SegmentedTabs
        ariaLabel="创作模式"
        className="template-workspace__tabs"
        idPrefix="mode"
        items={modes}
        value={mode}
        onChange={select}
      />
      {modes.map((item) => (
        <div
          key={item.id}
          id={`mode-panel-${item.id}`}
          role="tabpanel"
          aria-labelledby={`mode-${item.id}`}
          hidden={mode !== item.id}
        >
          {(visited.has(item.id) || mode === item.id) && (
            <Suspense fallback={<p role="status">正在加载…</p>}>
              {item.id === "normal" ? <NormalMode /> : <StoryMode />}
            </Suspense>
          )}
        </div>
      ))}
    </div>
  );
}
