# 简化剧情节点协议

剧情由少量节点组成。节点描述“这一段演什么”和“满足什么情况后去哪里”，
对白与跳转判断由同一次场景 LLM 调用完成。

## 节点类型

- `limited_turn_node`：最多演出 `maxRounds` 轮。可以提前跳转；到达上限时必须
  输出目标节点，或者由运行时采用 `defaultTo`。
- `free_chat_node`：不限轮数。每轮可以留在当前节点，也可以跳转。
- `ending_node`：剧情终点，不包含跳转。

一轮表示一次用户输入及其对应的完整 LLM 对白输出，不是单条人物台词。

## YAML 示例

```yaml
startNodeId: school-gate

nodes:
  - id: school-gate
    title: 旧校舍门口
    type: limited_turn_node
    instruction: |
      绫邀请玩家调查旧校舍。表现她的紧张，并透露钥匙的来历。
    maxRounds: 3
    transitions:
      - to: school-lobby
        when: 玩家愿意进入旧校舍
      - to: leave-school
        when: 玩家明确拒绝或决定离开
    defaultTo: school-lobby

  - id: school-lobby
    title: 旧校舍大厅
    type: free_chat_node
    instruction: |
      玩家可以和绫自由调查、交谈。不要替玩家作出决定。
    transitions:
      - to: leave-school
        when: 玩家明确表示离开旧校舍

  - id: leave-school
    title: 离开旧校舍
    type: ending_node
```

`when` 是提供给 LLM 的自然语言，不是条件表达式。运行时不会解释它，只校验
LLM 返回的目标是否出现在当前节点的 `transitions` 中。

## 场景输出

```json
{
  "dialogue": [
    {
      "characterId": "ling",
      "text": "如果准备好了，我们就进去吧。",
      "emotion": "紧张而坚定"
    }
  ],
  "nextNodeId": "school-lobby"
}
```

留在当前节点时，`nextNodeId` 为 `null`。不要使用特殊人物名表达跳转，也不要
把节点 ID 写进台词字段。

## 运行时约束

1. 服务端只接受当前节点 `transitions[].to` 中声明的目标。
2. 每次成功生成后，当前节点的轮次加一。
3. 进入新节点时，轮次重置为零。
4. `limited_turn_node` 到达上限但没有返回目标时，采用 `defaultTo`；没有默认
   目标则拒绝该输出并要求 LLM 修复。
5. 新节点不能定义 `choices` 或 `freeformIntents`。

旧节点字段目前只用于读取既有剧情工程。AI 剧情生成器只应产生本文格式。
