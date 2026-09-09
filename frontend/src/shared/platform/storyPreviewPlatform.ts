import type { ChatSnapshot, ShinsekaiPlatform, StoryGenerationTask, TaskProgressOptions } from "./types";
import { previewStoryGraph } from "./previewStoryGraph";

function previewStoryGeneration(id: string, status: StoryGenerationTask["status"]): StoryGenerationTask {
  const now = Date.now();
  return {
    artifactHashes: {},
    assumptions: ["Browser preview uses a compact three-scene mystery."],
    cancelRequested: status === "cancelled",
    completedStages: status === "succeeded" ? ["foundation", "characters", "narrative"] : [],
    cost: { estimatedTokens: 2100, inputChars: 5600, outputChars: 2800, requests: 3 },
    createdAt: now,
    currentStage: status === "succeeded" ? "complete" : "foundation",
    draftPath: status === "succeeded" ? `data/stories/.generation/${id}/draft.json` : "",
    error: null,
    id,
    options: {},
    repairAttempts: 0,
    resourceCatalog: {},
    status,
    synopsis: "A compact preview story.",
    updatedAt: now,
    validation:
      status === "succeeded"
        ? {
            castFailureNodeIds: [],
            endingCoverage: 1,
            endingNodeIds: ["truth-ending", "leave-ending"],
            exploredStates: 12,
            issues: [],
            reachableEndingIds: ["truth-ending", "leave-ending"],
            reachableNodeIds: ["opening", "clue", "truth-ending", "leave-ending"],
            sourceHash: "preview",
            valid: true,
          }
        : null,
  };
}

export function createStoryPreviewPlatform(
  getChat: () => ChatSnapshot,
  setChat: (snapshot: ChatSnapshot) => void,
): ShinsekaiPlatform["story"] {
  const tasks = new Map<string, StoryGenerationTask>();
  const read = (id: string) => {
    const task = tasks.get(id);
    if (!task) throw new Error("预览任务已过期，请重新生成。");
    return task;
  };
  const finish = async (task: StoryGenerationTask, options?: TaskProgressOptions<StoryGenerationTask>) => {
    tasks.set(task.id, task);
    options?.onTaskUpdate?.({
      id: task.id,
      kind: "story-generation",
      title: "生成剧本",
      message: "已完成",
      createdAt: task.createdAt,
      updatedAt: task.updatedAt,
      logs: [],
      error: "",
      phase: "complete",
      progress: 1,
      result: task,
      status: "succeeded",
    });
    return task;
  };
  return {
    getGeneration: async (id) => read(id),
    getPreview: async (id) => {
      read(id);
      return structuredClone(previewStoryGraph);
    },
    cancelGeneration: async (id) => finish({ ...read(id), status: "cancelled", cancelRequested: true }),
    regenerateGeneration: async (id, _stage, options) => finish({ ...read(id), updatedAt: Date.now() }, options),
    resumeGeneration: async (id, options) =>
      finish({ ...read(id), status: "succeeded", cancelRequested: false }, options),
    startGeneration: async (input, options) =>
      finish(
        {
          ...previewStoryGeneration(`story-preview-${Date.now()}`, "succeeded"),
          synopsis: input.synopsis,
          options: input.options ?? {},
          resourceCatalog: input.resourceCatalog ?? {},
        },
        options,
      ),
    startSession: async () => {
      const snapshot = {
        ...getChat(),
        story: {
          activeCast: [],
          castRevision: 0,
          currentNodeId: "opening",
          currentNodeTitle: "校门前的邀约",
          currentNodeType: "limited_turn_node",
          maxRounds: 3,
          nodeTurnCount: 0,
          objectives: [],
          options: [],
          revision: 1,
          storyId: "preview-story",
          storyVersion: 1,
          unlockedNotifications: [],
          visibleVariables: [],
        },
      };
      setChat(snapshot);
      return snapshot;
    },
  };
}
