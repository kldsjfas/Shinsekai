import { useId, useMemo, useState } from "react";
import type { StoryGraph } from "../../../shared/platform/storyPreviewTypes";
import { layoutStoryGraph, NODE_HEIGHT, NODE_WIDTH } from "./layout";
import "./StoryGraphView.css";

const nodeLabels = { limited_turn_node: "限轮剧情", free_chat_node: "自由对话", ending_node: "结局" };

export function StoryGraphView({ graph }: { graph: StoryGraph }) {
  const [selectedId, setSelectedId] = useState(graph.startNodeId);
  const [zoom, setZoom] = useState(1);
  const marker = useId().replace(/:/g, "");
  const layout = useMemo(() => layoutStoryGraph(graph), [graph]);
  const selected = graph.nodes.find((node) => node.id === selectedId) ?? graph.nodes[0];
  const title = (id: string) => graph.nodes.find((node) => node.id === id)?.title ?? id;
  const edges = layout.nodes.flatMap((node) => {
    const targets = new Set((node.transitions ?? []).map((item) => item.to));
    if (node.defaultTo) targets.add(node.defaultTo);
    return [...targets].flatMap((id) => {
      const target = layout.nodes.find((item) => item.id === id);
      if (!target) return [];
      const x = node.x + NODE_WIDTH,
        y = node.y + NODE_HEIGHT / 2;
      const endY = target.y + NODE_HEIGHT / 2;
      const path =
        target.x > node.x
          ? `M ${x} ${y} C ${x + 36} ${y}, ${target.x - 36} ${endY}, ${target.x - 6} ${endY}`
          : `M ${x} ${y} C ${x + 50} ${y - 100}, ${target.x - 40} ${endY - 100}, ${target.x - 6} ${endY}`;
      return [
        <path
          key={`${node.id}-${id}`}
          d={path}
          markerEnd={`url(#${marker})`}
          className={node.id === selected?.id ? "selected" : ""}
        >
          <title>
            {node.title} → {target.title}
          </title>
        </path>,
      ];
    });
  });
  return (
    <section className="story-generator-card" aria-labelledby="story-graph-title">
      <div className="story-generator-section-heading">
        <div>
          <h2 id="story-graph-title">剧本图</h2>
          <p>选择节点查看剧情与跳转条件。箭头表示可进入的下一段剧情。</p>
        </div>
        <div className="story-graph__zoom" role="group" aria-label="图缩放">
          <button type="button" aria-label="缩小" disabled={zoom <= 0.5} onClick={() => setZoom(zoom - 0.25)}>
            −
          </button>
          <button type="button" aria-label="重置缩放" onClick={() => setZoom(1)}>
            {Math.round(zoom * 100)}%
          </button>
          <button type="button" aria-label="放大" disabled={zoom >= 1.5} onClick={() => setZoom(zoom + 0.25)}>
            +
          </button>
        </div>
      </div>
      <div className="story-graph__scroll" tabIndex={0} role="region" aria-label="剧情节点关系图">
        <div style={{ width: layout.width * zoom, height: layout.height * zoom }}>
          <div
            className="story-graph__canvas"
            style={{ width: layout.width, height: layout.height, transform: `scale(${zoom})` }}
          >
            <svg width={layout.width} height={layout.height} aria-hidden="true">
              <defs>
                <marker
                  id={marker}
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
                </marker>
              </defs>
              {edges}
            </svg>
            {layout.nodes.map((node) => (
              <button
                type="button"
                key={node.id}
                className={`story-graph__node story-graph__node--${node.type}`}
                style={{ left: node.x, top: node.y, width: NODE_WIDTH, height: NODE_HEIGHT }}
                aria-pressed={selected?.id === node.id}
                onClick={() => setSelectedId(node.id)}
              >
                <small>
                  {node.id === graph.startNodeId ? "起点 · " : ""}
                  {nodeLabels[node.type]}
                </small>
                <strong>{node.title || node.id}</strong>
              </button>
            ))}
          </div>
        </div>
      </div>
      {selected && (
        <article className="story-graph__detail" aria-label="节点详情">
          <h3>{selected.title}</h3>
          <p>{selected.instruction || "故事在此结束。"}</p>
          {selected.background && <p>地点：{selected.background}</p>}
          {selected.maxRounds !== undefined && <p>最多 {selected.maxRounds} 轮对话</p>}
          <ul>
            {selected.transitions?.map((transition, index) => (
              <li key={`${transition.to}-${index}`}>
                {transition.when} →{" "}
                <button className="story-graph__link" type="button" onClick={() => setSelectedId(transition.to)}>
                  {title(transition.to)}
                </button>
              </li>
            ))}
          </ul>
          {selected.defaultTo && <p>达到轮数上限时，默认进入：{title(selected.defaultTo)}</p>}
        </article>
      )}
    </section>
  );
}
