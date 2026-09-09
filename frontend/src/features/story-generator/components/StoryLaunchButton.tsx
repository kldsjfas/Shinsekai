import { Button } from "../../../shared/ui";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { chatQueryKey, getChatRuntimeStatus, getChatSnapshot, launchChat } from "../../../entities/chat/repository";
import { startStorySession } from "../../../entities/story/repository";
import type { ChatSnapshot, StoryGenerationTask, TemplateSummary } from "../../../shared/platform/types";
import { showChatSurface } from "../../../shared/desktop/chatWindow";
import { TRANSPARENT_BACKGROUND_NAME } from "../../../shared/constants";
import { ChatInitializationDialog } from "../../chat-startup/ChatInitializationDialog";
import { useChatInitialization } from "../../chat-startup/useChatInitialization";

export function StoryLaunchButton({
  task,
  template,
  disabled,
}: {
  task: StoryGenerationTask;
  template?: TemplateSummary;
  disabled: boolean;
}) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const init = useChatInitialization();
  const [error, setError] = useState("");
  const launched = useRef<ChatSnapshot | null>(null);
  const launch = async () => {
    if (!template || init.initializationPending) return;
    setError("");
    try {
      const snapshot = await init.runChatInitialization(async (options) => {
        const status = await getChatRuntimeStatus();
        if (!launched.current && status.state !== "idle") throw new Error("请先结束当前聊天，再运行剧本。");
        if (launched.current && status.state !== "idle") {
          const current = await getChatSnapshot();
          if (status.state === "closing" || current.sessionId !== launched.current.sessionId) {
            throw new Error("当前聊天已发生变化，请先结束当前聊天再重试。");
          }
        }
        if (!launched.current || status.state === "idle") {
          launched.current = await launchChat(
            {
              templateId: template.id,
              templateName: template.name,
              characters: [],
              backgroundName: TRANSPARENT_BACKGROUND_NAME,
              historyPath: "",
              resetHistory: true,
            },
            options,
          );
        }
        const story = await startStorySession(task.draftPath);
        return { ...launched.current, ...story };
      });
      client.setQueryData(chatQueryKey, snapshot);
      await showChatSurface({ navigate, snapshot });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };
  return (
    <>
      <Button
        variant="primary"
        type="button"
        disabled={disabled || !template || init.initializationPending}
        onClick={() => void launch()}
      >
        {init.initializationPending ? "正在启动…" : "运行剧本"}
      </Button>
      {error && (
        <p className="story-generator-error" role="alert">
          {error}
        </p>
      )}
      <ChatInitializationDialog
        error={init.initializationError}
        onClose={init.closeInitialization}
        open={init.initializationOpen}
        pending={init.initializationPending}
        task={init.initializationTask}
      />
    </>
  );
}
