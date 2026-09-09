import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { configQueryKey, getAppConfig, saveSystemConfig } from "../../../entities/config/repository";

export function StoryFeatureGate({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const config = useQuery({ queryKey: configQueryKey, queryFn: getAppConfig });
  const enable = useMutation({
    mutationFn: async () => {
      if (!config.data) throw new Error("请先加载设置");
      await saveSystemConfig({ ...config.data.system_config, story_system_enabled: true });
    },
    onSuccess: () => client.invalidateQueries({ queryKey: configQueryKey }),
  });
  if (config.data?.system_config.story_system_enabled) return children;
  return (
    <section className="story-generator-card">
      <h2>启用剧本模式</h2>
      <p>从模板创作有剧情节点和结局的互动故事。生成需要使用已配置的语言模型。</p>
      {config.isPending ? (
        <p role="status">正在读取设置…</p>
      ) : (
        <button disabled={enable.isPending || config.isError} onClick={() => enable.mutate()} type="button">
          {enable.isPending ? "正在启用…" : "启用剧本模式"}
        </button>
      )}
      {(enable.error || config.error) && <p role="alert">{(enable.error || config.error)?.message}</p>}
      {config.isError && (
        <button type="button" onClick={() => void config.refetch()}>
          重试
        </button>
      )}
    </section>
  );
}
