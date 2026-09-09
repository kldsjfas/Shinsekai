import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StoryLaunchButton } from "../../../features/story-generator/components/StoryLaunchButton";
import type { StoryGenerationTask, TemplateSummary } from "../../../shared/platform/types";

const { launchChat, getChatRuntimeStatus, startStorySession, showChatSurface } = vi.hoisted(() => ({
  launchChat: vi.fn(),
  getChatRuntimeStatus: vi.fn(),
  startStorySession: vi.fn(),
  showChatSurface: vi.fn(),
}));
vi.mock("../../../entities/chat/repository", () => ({
  launchChat,
  getChatRuntimeStatus,
  getChatSnapshot: () => Promise.resolve({ sessionId: "session-1" }),
  chatQueryKey: ["chat"],
}));
vi.mock("../../../entities/story/repository", () => ({ startStorySession }));
vi.mock("../../../shared/desktop/chatWindow", () => ({ showChatSurface }));
vi.mock("../../../features/chat-startup/ChatInitializationDialog", () => ({ ChatInitializationDialog: () => null }));

function renderButton() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <StoryLaunchButton
          task={{ draftPath: "story/draft.json" } as StoryGenerationTask}
          template={{ id: "campus.txt", name: "校园" } as TemplateSummary}
          disabled={false}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("story launch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getChatRuntimeStatus.mockResolvedValue({ state: "idle" });
    launchChat.mockResolvedValue({ sessionId: "session-1", runtimeMode: "react" });
    startStorySession.mockResolvedValue({ story: { storyId: "story-1" } });
  });
  it("initializes a fresh history, attaches the generated draft, then opens chat", async () => {
    renderButton();
    fireEvent.click(screen.getByRole("button", { name: "运行剧本" }));
    await waitFor(() => expect(showChatSurface).toHaveBeenCalled());
    expect(launchChat).toHaveBeenCalledWith(
      expect.objectContaining({ templateId: "campus.txt", resetHistory: true }),
      expect.anything(),
    );
    expect(startStorySession).toHaveBeenCalledWith("story/draft.json");
    expect(startStorySession.mock.invocationCallOrder[0]).toBeGreaterThan(launchChat.mock.invocationCallOrder[0]);
  });
  it("does not attach a story to someone else's running chat", async () => {
    getChatRuntimeStatus.mockResolvedValue({ state: "running" });
    renderButton();
    fireEvent.click(screen.getByRole("button", { name: "运行剧本" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("请先结束当前聊天");
    expect(launchChat).not.toHaveBeenCalled();
    expect(startStorySession).not.toHaveBeenCalled();
  });
  it("retries attachment after a failure without creating another history", async () => {
    startStorySession.mockRejectedValueOnce(new Error("立绘尚未准备好"));
    renderButton();
    fireEvent.click(screen.getByRole("button", { name: "运行剧本" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("立绘尚未准备好");
    expect(showChatSurface).not.toHaveBeenCalled();
    getChatRuntimeStatus.mockResolvedValue({ state: "running" });
    fireEvent.click(screen.getByRole("button", { name: "运行剧本" }));
    await waitFor(() => expect(showChatSurface).toHaveBeenCalled());
    expect(launchChat).toHaveBeenCalledTimes(1);
  });
});
