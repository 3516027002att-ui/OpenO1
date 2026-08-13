# Spatiotemporal Composability 对 OpenO1 的启发

> 日期：2026-08-13
> 状态：设计讨论 / 候选架构方向
> 关联：`docs/discussions/2026-08-13-dsh-harness-design-notes.md`

## 核心结论

论文《A Programming Paradigm for Spatiotemporal Composability》及 Cordis 的核心启发，可以概括为三点：

1. Revertible Effects：组件加载后产生的 Tool 注册、listener、timer、service、prompt fragment、后台任务等副作用，应由 Runtime 追踪，并尽量具备统一的撤销 / dispose 语义。
2. Reactive Coeffects：组件显式声明它运行所需要的 service、capability、context、permission 等条件，由 Runtime 动态维护依赖关系，而不是依赖固定 boot order。
3. Harness Graph as Runtime State：Harness 的组件图本身应成为可观察、可修改、可版本化、可回滚的运行时状态。

可以把一个动态组件抽象为：

`Component = Requirements + Effects + Lifecycle`

## 对 OpenO1 的意义

如果 OpenO1 未来允许 Agent 修改自身 Harness，目标不应只停留在改配置或源码后重启。更值得发展的方向，是让 Agent 在任务过程中操作一棵 live Harness graph。

例如：

- 搜索阶段动态加载 research capability；
- 数学证明阶段加载 verifier 并调整 planning strategy；
- 长文档阶段切换 context policy；
- 工具检索效果差时替换 Tool Router；
- 需要并行研究时加载新的 subagent provider；
- 阶段结束后自动卸载 task-scoped capability，并清理对应 effects。

这可以看成一种 runtime metaprogramming：

`Runtime Graph(t) -> mutation -> Runtime Graph(t+1)`

每次变化都应有明确的 owner、dependency、effects、version 和 rollback path。

## Cordis 能解决的范围

Cordis 式 composability 很适合解决 Runtime 一致性问题，例如：

- listener / timer / watcher 泄漏；
- Tool 已卸载但 registry 仍保留旧引用；
- HMR 后新旧实例并存；
- service 替换后 consumer 仍持有旧实例；
- 启动顺序变化导致依赖乱序；
- 子插件卸载不完整；
- config patch 后出现半新半旧状态；
- 后台任务 ownership 不清晰。

但 composability 本身无法判断“新的 Harness 逻辑是否更好”。一个生命周期完全正确的新 Agent Loop，仍然可能在语义上严重退化。因此 OpenO1 还需要独立的 semantic validation、invariant 和 regression check。

## 建议保留稳定恢复层

OpenO1 可以让上层 Harness 高度动态化，但建议保留一个极小且稳定的恢复层，负责：

- mutation supervision；
- snapshot / journal；
- rollback；
- capability / permission boundary；
- invariant checking；
- safe-mode recovery。

Agent 可以动态修改 Planner、Agent Loop、Tool Router、Prompt Assembler、Memory Policy、Context Manager、Subagent Policy、Reasoning Strategy 等上层组件，但恢复层不应被普通 Harness mutation 同时替换。

## 推荐的 Harness Mutation 流程

重要修改可以统一经过：

`propose mutation -> dependency check -> snapshot -> staged mount -> invariant / health check -> atomic switch -> observe -> commit`

失败时执行：

`rollback -> dispose staged effects -> restore previous graph`

其中 revertible effects + reactive coeffects 负责 Runtime 级的一致性；OpenO1 自己的 mutation supervisor 负责更高层的语义检查和退化检测。

## 与现有架构的结合

Capability 可以进一步统一为一个完整运行时单元，包含：

- Host Surface；
- Client Surface；
- Tools；
- Prompt / Context fragments；
- runtime services；
- requirements / coeffects；
- effects / disposer；
- policy / permission；
- execution requirement；
- telemetry；
- invariants；
- UI representation。

Tool / Capability Broker、Context Broker、Execution Broker 可以围绕这一抽象协同工作；未来再增加 Mutation Supervisor 与稳定恢复层。

## 当前记录的候选原则

1. 动态 Harness 组件的副作用应由 Runtime 跟踪，并尽量具有结构化撤销语义。
2. 组件显式声明依赖，Runtime 动态维护依赖满足关系。
3. Harness 的组成结构本身成为可观察、可修改、可版本化、可回滚的运行时状态。
4. Runtime 一致性与 Harness 语义正确性分层处理：前者可借鉴 Cordis，后者需要 OpenO1 自己的验证与恢复机制。
5. OpenO1 的长期目标可以从“源码自修改”推进到“Agent 主动重构 live Harness graph”。
