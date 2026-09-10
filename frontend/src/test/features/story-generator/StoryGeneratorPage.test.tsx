import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
const listStories = vi.fn();
const ensureCharacterBriefs = vi.fn();

vi.mock("../../../entities/config/repository", () => ({
  configQueryKey: ["config"],
  getAppConfig: () =>
    Promise.resolve({ ...sampleConfig, system_config: { ...sampleConfig.system_config, story_system_enabled: true } }),
}));
vi.mock("../../../entities/template/repository", () => ({
  templatesQueryKey: ["templates"],
  listTemplates: () => {
    throw new Error("Story mode must not load templates");
  },
}));
vi.mock("../../../entities/character/repository", () => ({
  charactersQueryKey: ["characters"],
  listCharacters: () =>
    Promise.resolve(
      ["小玲", "小明", "小夏", "小雨", "小晴"].map((name) => ({ name, character_setting: `${name}的完整设定` })),
    ),
  ensureCharacterBriefs: (...args: unknown[]) => ensureCharacterBriefs(...args),
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
  storyLibraryQueryKey: ["story-library"],
  listStories: (...args: unknown[]) => listStories(...args),
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
    options: {
      characters: ["小玲"],
      backgroundName: "旧校舍",
      characterPromptMode: "full",
      primaryCharacters: ["小玲"],
    },
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
    localStorage.clear();
    listStories.mockResolvedValue([]);
    ensureCharacterBriefs.mockResolvedValue({ characters: [], generatedNames: [] });
  });

  it("generates a draft and previews assumptions and validation", async () => {
    startStoryGeneration.mockResolvedValue(generatedTask());
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "小玲" }));
    fireEvent.click(screen.getByRole("combobox", { name: "故事背景" }));
    fireEvent.click(screen.getByRole("option", { name: "旧校舍" }));
    expect(screen.queryByRole("combobox", { name: "故事模板" })).not.toBeInTheDocument();
    const startButton = screen.getByRole("button", { name: "开始生成" });
    await waitFor(() => expect(startButton).toBeEnabled());
    fireEvent.click(startButton);

    await waitFor(() =>
      expect(startStoryGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          synopsis: "",
          options: expect.objectContaining({
            characters: ["小玲"],
            backgroundName: "旧校舍",
            characterPromptMode: "full",
            primaryCharacters: ["小玲"],
          }),
        }),
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

  it("shows automatic recovery without requiring a manual resume action", async () => {
    const task = generatedTask("running");
    task.currentStage = "repair";
    task.validation!.valid = false;
    task.recovery = { state: "correcting", attempt: 2, message: "正在根据编译错误自动修复" };
    startStoryGeneration.mockResolvedValue(task);
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "小玲" }));
    const startButton = screen.getByRole("button", { name: "开始生成" });
    await waitFor(() => expect(startButton).toBeEnabled());
    fireEvent.click(startButton);
    expect(await screen.findByText(/正在根据编译错误自动修复/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "从断点继续" })).not.toBeInTheDocument();
    expect(screen.getByText("正在自动修复问题，通过检查后即可游玩")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消生成" })).toBeEnabled();
    expect(resumeStoryGeneration).not.toHaveBeenCalled();
    expect(localStorage.getItem("shinsekai.story-generation.task")).toBe("generation-1");
  });

  it("restores the saved task after leaving the page", async () => {
    localStorage.setItem("shinsekai.story-generation.task", "generation-1");
    getStoryGeneration.mockResolvedValue(generatedTask());
    renderPage();
    expect(await screen.findByRole("button", { name: "运行剧本" })).toBeEnabled();
    expect(getStoryGeneration).toHaveBeenCalledWith("generation-1");
  });

  it("automatically follows a restored background job until it becomes playable", async () => {
    localStorage.setItem("shinsekai.story-generation.task", "generation-1");
    const running = generatedTask("running");
    running.recovery = { state: "resuming", message: "正在自动从已保存的进度继续" };
    getStoryGeneration.mockResolvedValueOnce(running).mockResolvedValue(generatedTask());
    renderPage();
    expect(await screen.findByText(/正在自动从已保存的进度继续/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "运行剧本" }, { timeout: 4000 })).toBeEnabled();
    expect(getStoryGeneration.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(resumeStoryGeneration).not.toHaveBeenCalled();
    expect(startStoryGeneration).not.toHaveBeenCalled();
  });

  it("keeps an explicitly cancelled task stopped after restoring it", async () => {
    localStorage.setItem("shinsekai.story-generation.task", "generation-1");
    const cancelled = generatedTask("cancelled");
    cancelled.cancelRequested = true;
    cancelled.validation!.valid = false;
    getStoryGeneration.mockResolvedValue(cancelled);
    renderPage();
    expect(await screen.findByText("已停止修复，当前剧本尚未通过检查")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "从断点继续" })).not.toBeInTheDocument();
    expect(resumeStoryGeneration).not.toHaveBeenCalled();
    expect(startStoryGeneration).not.toHaveBeenCalled();
  });

  it("cannot generate before a character is selected", async () => {
    renderPage();
    expect(await screen.findByRole("button", { name: "开始生成" })).toBeDisabled();
    expect(startStoryGeneration).not.toHaveBeenCalled();
  });

  it("does not allow an invalid draft to run", async () => {
    const task = generatedTask();
    task.validation!.valid = false;
    startStoryGeneration.mockResolvedValue(task);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "小玲" }));
    const start = screen.getByRole("button", { name: "开始生成" });
    await waitFor(() => expect(start).toBeEnabled());
    fireEvent.click(start);
    expect(await screen.findByRole("button", { name: "运行剧本" })).toBeDisabled();
  });

  it("uses the shared primary character flow and generates secondary briefs", async () => {
    startStoryGeneration.mockResolvedValue(generatedTask());
    renderPage();
    await screen.findByRole("button", { name: "小玲" });
    fireEvent.click(screen.getByRole("button", { name: "全选角色" }));
    expect(screen.getByRole("button", { name: "小玲" })).toHaveClass("template-character-card--selected");
    fireEvent.click(screen.getByRole("button", { name: "开始生成" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "应用主次设置" }));
    await waitFor(() => expect(ensureCharacterBriefs).toHaveBeenCalledWith(["小明", "小夏", "小雨", "小晴"]));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "开始生成" }));
    await waitFor(() =>
      expect(startStoryGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          options: expect.objectContaining({ characterPromptMode: "compact", primaryCharacters: ["小玲"] }),
        }),
        expect.anything(),
      ),
    );
  });

  it("keeps the draft when switching to the existing story library", async () => {
    listStories.mockResolvedValue([
      {
        id: "saved",
        storyPath: "saved/draft.json",
        title: "旧校舍谜案",
        characters: ["小玲"],
        backgrounds: ["旧校舍"],
        historyPath: "data/chat_history/saved",
        currentNodeTitle: "调查教室",
        updatedAt: 2,
      },
    ]);
    renderPage();
    fireEvent.change(await screen.findByRole("textbox", { name: "剧情梗概" }), { target: { value: "我的新故事" } });
    fireEvent.click(screen.getByRole("tab", { name: "已有剧本" }));
    expect(await screen.findByText("旧校舍谜案")).toBeInTheDocument();
    expect(screen.getByText("上次进度：调查教室")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "继续游玩" })).toBeEnabled();
    fireEvent.click(screen.getByRole("tab", { name: "创作新剧本" }));
    expect(screen.getByRole("textbox", { name: "剧情梗概" })).toHaveValue("我的新故事");
  });
});
