import type { StoryGenerationStage } from "../../../entities/story/types";

export const stages: Array<{ id: StoryGenerationStage; label: string; description: string }> = [
  { id: "foundation", label: "故事基础", description: "确定世界、冲突与隐藏信息" },
  { id: "characters", label: "人物列表", description: "创作故事中的人物与关系" },
  { id: "narrative", label: "剧情节点", description: "安排各段剧情、地点和跳转条件" },
];
export const taskStatus = {
  queued: "等待生成",
  running: "正在生成",
  succeeded: "剧本已生成",
  failed: "生成未完成",
  cancelled: "已取消",
};
