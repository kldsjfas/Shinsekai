import { useQuery } from "@tanstack/react-query";
import { listStories, storyLibraryQueryKey } from "../../../entities/story/repository";
import { Button } from "../../../shared/ui";
import { StoryLaunchButton } from "./StoryLaunchButton";

export function StoryLibrary({ onCreate }: { onCreate: () => void }) {
  const stories = useQuery({ queryKey: storyLibraryQueryKey, queryFn: listStories, staleTime: 0 });
  return (
    <section className="section">
      <div className="story-library-header">
        <h2 className="section__title">已有剧本</h2>
        <Button disabled={stories.isFetching} onClick={() => void stories.refetch()}>
          刷新
        </Button>
      </div>
      {stories.isPending && <p role="status">正在读取剧本…</p>}
      {stories.isError && (
        <p role="alert" className="story-generator-error">
          {stories.error.message}
        </p>
      )}
      {stories.isSuccess && !stories.data.length && (
        <div>
          <p className="section__description">还没有可游玩的剧本，先创作一个新故事吧。</p>
          <Button variant="primary" onClick={onCreate}>
            创作新剧本
          </Button>
        </div>
      )}
      <div className="story-library-grid">
        {stories.data?.map((story) => (
          <article className="story-library-card" key={story.storyPath}>
            <h3>{story.title}</h3>
            <p className="section__description">{story.characters.join("、") || "剧本人物"}</p>
            <p className="section__description">背景：{story.backgrounds.join("、") || "透明背景"}</p>
            <p>{story.historyPath ? `上次进度：${story.currentNodeTitle || "已保存"}` : "尚未开始游玩"}</p>
            <StoryLaunchButton
              key={`${story.storyPath}-${story.historyPath}`}
              storyPath={story.storyPath}
              historyPath={story.historyPath}
              label={story.historyPath ? "继续游玩" : "开始游玩"}
            />
          </article>
        ))}
      </div>
    </section>
  );
}
