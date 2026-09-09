import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { sampleConfig } from "../../../shared/platform/sampleData";
import { previewStoryGraph } from "../../../shared/platform/previewStoryGraph";
import { I18nProvider } from "../../../shared/i18n";

import { StoryGeneratorPage } from "../../../features/story-generator/StoryGeneratorPage";
import type { StoryGenerationTask } from "../../../entities/story/types";

const startStoryGeneration = vi.fn();
const resumeStoryGeneration = vi.fn();
const regenerateStoryGeneration = vi.fn();
const cancelStoryGeneration = vi.fn();
const getStoryGeneration = vi.fn();

vi.mock("../../../entities/config/repository", () => ({
  configQueryKey: ["config"],
  getAppConfig: () =>
    Promise.resolve({ ...sampleConfig, system_config: { ...sampleConfig.system_config, story_system_enabled: true } }),
}));
vi.mock("../../../entities/template/repository", () => ({
  templatesQueryKey: ["templates"],
  listTemplates: () =>
    Promise.resolve([{ id: "campus.txt", name: "校园模板", scenario: "调查废弃校舍", content: "旧内容" }]),
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  return render(
    <QueryClientProvider client={client}>
      <I18nProvider language="zh_CN">
        <MemoryRouter>
          <StoryGeneratorPage />
        </MemoryRouter>
      </I18nProvider>
    </QueryClientProvider>,
  );
}

vi.mock("../../../entities/background/repository", () => ({
  backgroundsQueryKey: ["backgrounds"],
  listBackgrounds: vi.fn().mockResolvedValue([
    { name: "旧校舍", sprites: [{ path: "school.png" }] },
    { name: "空背景", sprites: [] },
  ]),
}));

vi.mock("../../../entities/story/repository", () => ({
  startStoryGeneration: (...args: unknown[]) => startStoryGeneration(...args),
  resumeStoryGeneration: (...args: unknown[]) => resumeStoryGeneration(...args),
  regenerateStoryGeneration: (...args: unknown[]) => regenerateStoryGeneration(...args),
  cancelStoryGeneration: (...args: unknown[]) => cancelStoryGeneration(...args),
  getStoryGeneration: (...args: unknown[]) => getStoryGeneration(...args),
  getStoryPreview: () => Promise.resolve(previewStoryGraph),
  startStorySession: vi.fn(),
}));

function generatedTask(status: StoryGenerationTask["status"] = "succeeded"): StoryGenerationTask {
  return {
    artifactHashes: {},
    assumptions: ["以三幕结构展开"],
    cancelRequested: false,
    completedStages: ["foundation", "characters", "narrative"],
    cost: { estimatedTokens: 1200, inputChars: 2400, outputChars: 1200, requests: 3 },
    createdAt: 1,
    currentStage: status === "succeeded" ? "complete" : "narrative",
    draftPath: status === "succeeded" ? "draft.json" : "",
    error: null,
    id: "generation-1",
    options: { templateId: "campus.txt" },
    repairAttempts: 0,
    resourceCatalog: {},
    status,
    synopsis: "校园谜案",
    updatedAt: 2,
    validation: {
      castFailureNodeIds: [],
      endingCoverage: 1,
      endingNodeIds: ["truth"],
      exploredStates: 18,
      issues: [],
      reachableEndingIds: ["truth"],
      reachableNodeIds: ["start", "truth"],
      sourceHash: "sha256",
      valid: true,
    },
  };
}

describe("StoryGeneratorPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("generates a draft and previews assumptions and validation", async () => {
    startStoryGeneration.mockResolvedValue(generatedTask());
    renderPage();

    fireEvent.change(await screen.findByRole("combobox", { name: "故事模板" }), { target: { value: "campus.txt" } });
    expect(screen.getByRole("textbox", { name: "剧情梗概" })).toHaveValue("调查废弃校舍");
    const startButton = screen.getByRole("button", { name: "开始生成" });
    await waitFor(() => expect(startButton).toBeEnabled());
    fireEvent.click(startButton);

    await waitFor(() =>
      expect(startStoryGeneration).toHaveBeenCalledWith(
        expect.objectContaining({ resourceCatalog: { backgrounds: ["旧校舍"] } }),
        expect.anything(),
      ),
    );
    expect(await screen.findByText("以三幕结构展开")).toBeInTheDocument();
    expect(screen.getByText("已通过确定性校验")).toBeInTheDocument();
    expect(screen.getByText(/可达结局 100%/)).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "剧本图" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /自由对话 寻找旧日线索/ }));
    expect(screen.getByText("在旧教室自由调查，讨论信中的秘密。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "运行剧本" })).toBeEnabled();
  });

  it("resumes a failed task from its checkpoint", async () => {
    startStoryGeneration.mockResolvedValue(generatedTask("failed"));
    resumeStoryGeneration.mockResolvedValue(generatedTask());
    renderPage();

    fireEvent.change(await screen.findByRole("combobox", { name: "故事模板" }), { target: { value: "campus.txt" } });
    const startButton = screen.getByRole("button", { name: "开始生成" });
    await waitFor(() => expect(startButton).toBeEnabled());
    fireEvent.click(startButton);
    fireEvent.click(await screen.findByRole("button", { name: "从断点继续" }));

    await waitFor(() => expect(resumeStoryGeneration).toHaveBeenCalledWith("generation-1", expect.anything()));
    expect(await screen.findByText("已通过确定性校验")).toBeInTheDocument();
  });

  it("restores the saved task after leaving the page", async () => {
    sessionStorage.setItem("shinsekai.story-generation.task", "generation-1");
    getStoryGeneration.mockResolvedValue(generatedTask());
    renderPage();
    expect(await screen.findByRole("button", { name: "运行剧本" })).toBeEnabled();
    expect(getStoryGeneration).toHaveBeenCalledWith("generation-1");
  });

  it("cannot generate before a template is selected", async () => {
    renderPage();
    expect(await screen.findByRole("button", { name: "开始生成" })).toBeDisabled();
    expect(startStoryGeneration).not.toHaveBeenCalled();
  });

  it("does not allow an invalid draft to run", async () => {
    const task = generatedTask();
    task.validation!.valid = false;
    startStoryGeneration.mockResolvedValue(task);
    renderPage();
    fireEvent.change(await screen.findByRole("combobox", { name: "故事模板" }), { target: { value: "campus.txt" } });
    const start = screen.getByRole("button", { name: "开始生成" });
    await waitFor(() => expect(start).toBeEnabled());
    fireEvent.click(start);
    expect(await screen.findByRole("button", { name: "运行剧本" })).toBeDisabled();
  });
});
