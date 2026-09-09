import { Button } from "../../../shared/ui";
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
    <section className="section">
      <h2 className="section__title">启用剧本模式</h2>
      <p className="section__description">从模板创作有剧情节点和结局的互动故事。生成需要使用已配置的语言模型。</p>
      {config.isPending ? (
        <p className="section__description" role="status">
          正在读取设置…
        </p>
      ) : (
        <Button
          variant="primary"
          disabled={enable.isPending || config.isError}
          onClick={() => enable.mutate()}
          type="button"
        >
          {enable.isPending ? "正在启用…" : "启用剧本模式"}
        </Button>
      )}
      {(enable.error || config.error) && (
        <p className="section__description" role="alert">
          {(enable.error || config.error)?.message}
        </p>
      )}
      {config.isError && (
        <Button type="button" onClick={() => void config.refetch()}>
          重试
        </Button>
      )}
    </section>
  );
}
