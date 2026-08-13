# No Blind Delegation：Parent-visible Subagent Observability

> 日期：2026-08-13  
> 状态：设计讨论 / 候选架构方向

## 背景

在 Claude Code 一类 agent harness 中，parent/main agent 对 subagent 的运行过程可能只有很弱的可见性：任务被委派后，parent 往往只能等待最终返回，难以及时知道 subagent 当前阶段、是否卡住、是否跑偏、是否反复重试、正在使用什么工具、是否需要额外资源或已经产出关键中间结果。

OpenO1 应明确避免这种 black-box delegation。

## 核心原则

**No blind delegation.**

任何长期运行的 subagent 都不能成为 parent 的黑盒。Parent 至少必须拥有：

- 生命周期观测；
- 进度观测；
- 阻塞通知；
- 关键中间结果获取；
- 中途干预；
- 暂停 / 恢复；
- 取消；
- 预算与能力调整。

## Subagent 作为 Runtime 一等对象

Subagent 不应只被建模为一次“调用并等待返回”的函数，而应拥有可持续查询的运行时 Handle，例如：

- `id`；
- `goal`；
- `state`；
- `current_phase`；
- `last_activity`；
- `last_progress_at`；
- `current_tool`；
- `progress_summary`；
- `blocker`；
- `budget_used`；
- `artifacts / partial_results`；
- `parent_id`。

建议至少存在如下高层状态：

`CREATED -> RUNNING -> WAITING_TOOL / WAITING_PARENT / BLOCKED / PAUSED -> COMPLETED / FAILED / CANCELLED`

## Parent 获取状态的两种方式

### Pull：主动查询

Parent 可随时执行类似 `inspect_subagent(id)` 的操作，获取：

- 是否仍在运行；
- 当前阶段；
- 最近一次有效进展；
- 当前工具；
- 阻塞原因；
- 预算消耗；
- 已产出的中间结果和 artifact。

### Push：事件推送

Subagent 或 Runtime 在关键状态变化时主动发出结构化事件，例如：

- `progress`；
- `blocked`；
- `needs_input`；
- `milestone`；
- `tool_failure`；
- `budget_warning`；
- `partial_result`；
- `completed`。

Runtime 决定哪些事件需要立即送给 parent，哪些只进入状态存储供按需查询，避免 subagent 事件流把 main context 淹没。

## Subagent 的向上通信

Subagent 应拥有主动向 parent 求助和汇报的结构化通道，例如：

- `report_progress()`；
- `request_help()`；
- `request_resource()`；
- `escalate_blocker()`；
- `submit_partial_result()`。

Parent 则应能够在 subagent 运行中：

- steer / reprioritize；
- pause / resume；
- cancel；
- change budget；
- grant / revoke capability；
- request checkpoint / partial answer。

因此 parent-child agent 关系应是持续的双向通信关系，而不是单向派工。

## 可观测性边界

Parent 能看到 subagent 的运行状态，不意味着读取 subagent 的完整内部 reasoning。

OpenO1 应明确分成三层：

1. **Subagent private cognition**：subagent 自己的完整工作上下文、内部搜索分支、Reasoning Tree；
2. **Runtime observability**：状态、工具、进度、阻塞、资源消耗、错误、产物；
3. **Parent-visible summary**：Runtime 根据重要性筛选后提供给 parent 的短摘要和事件。

这样既能避免把多个 subagent 的大量内部 token 倒回 main context，也能保证 main 对整体任务拥有足够的控制力。

## 统一 Task / Actor Tree

OpenO1 可以进一步把 Agent、Subagent、Tool execution、Background task 统一建模为 Runtime 中的 `TaskNode` / `Actor`：

```text
Main Agent
├── Research Agent
│   ├── Web Task
│   └── PDF Task
├── Coding Agent
│   └── Test Task
└── Verifier Agent
```

每个节点统一拥有：

- lifecycle；
- owner / parent；
- state；
- events；
- resource usage；
- artifacts；
- intervention surface。

Runtime 内部保留完整任务树；main 可以观察和操作这棵树；用户 UI 只展示经过筛选的高层状态，不直接暴露内部 Reasoning Tree。

## 与 OpenO1 其他设计的结合

该原则可以直接连接此前的几项设计：

- Host / Client 双 Surface：parent-visible state 属于 Host 内部控制面，用户只看到筛选后的 Client state；
- Agent 状态 UI：用户可以看到 subagent 高层状态，但不看到内部认知树；
- Cordis 式 Runtime：利用 lifecycle、ownership、event bus、dependency 与 cleanup 机制维护 task tree；
- Fail-fast invariant：检测 orphan task、非法 parent-child 关系、失联 subagent、长时间无进展、错误状态迁移；
- Budget accounting：parent 可以按 agent / task 分配、监控并调整资源。

## 当前结论

Subagent 越自主、运行越久，parent 对 delegation 的运行时控制越重要。否则会出现一种反直觉退化：subagent 能力越强，main 反而越失去对整个任务的认知与控制。

因此 **No blind delegation** 应作为 OpenO1 Runtime 的候选架构原则：所有长期运行的 subagent 都必须对 parent 提供结构化状态、事件、阻塞信息、中间结果以及运行中干预能力。
