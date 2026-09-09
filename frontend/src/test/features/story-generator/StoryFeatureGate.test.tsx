import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StoryFeatureGate } from "../../../features/story-generator/components/StoryFeatureGate";
import { sampleConfig } from "../../../shared/platform/sampleData";

const { getAppConfig, saveSystemConfig } = vi.hoisted(() => ({ getAppConfig: vi.fn(), saveSystemConfig: vi.fn() }));
vi.mock("../../../entities/config/repository", () => ({ configQueryKey: ["config"], getAppConfig, saveSystemConfig }));
function renderGate() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <StoryFeatureGate>
        <p>创作工作区</p>
      </StoryFeatureGate>
    </QueryClientProvider>,
  );
}
describe("story feature activation", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getAppConfig.mockResolvedValue(sampleConfig);
  });
  it("waits for explicit activation and a successful config refresh", async () => {
    saveSystemConfig.mockImplementation(async () => {
      getAppConfig.mockResolvedValue({
        ...sampleConfig,
        system_config: { ...sampleConfig.system_config, story_system_enabled: true },
      });
    });
    renderGate();
    expect(screen.queryByText("创作工作区")).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "启用剧本模式" }));
    expect(await screen.findByText("创作工作区")).toBeVisible();
    expect(saveSystemConfig).toHaveBeenCalledWith({ ...sampleConfig.system_config, story_system_enabled: true });
  });
  it("shows save failure without unlocking generation", async () => {
    saveSystemConfig.mockRejectedValue(new Error("设置写入失败"));
    renderGate();
    fireEvent.click(await screen.findByRole("button", { name: "启用剧本模式" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("设置写入失败");
    expect(screen.queryByText("创作工作区")).not.toBeInTheDocument();
  });
});
