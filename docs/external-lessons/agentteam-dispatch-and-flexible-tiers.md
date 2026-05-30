# AgentTeam 调度与弹性档位学习记录

## 来源

观察对象：

- Antigravity 中 Claude Opus 4.6 调用 subagent 的实际运行截图。
- DeerFlow 2.0 / DeerFlow harness 的档位与 subagent 控制思路。
- AutoGen SelectorGroupChat、CrewAI Crew、AgentScope workflow / plan / handoff、Anthropic effective agents 等 agent harness 经验。

观察日期：2026-05-30

## 一句话结论

OpenO1 的 AgentTeam 不应设计成僵硬流程图，也不应退化成多个 agent 自由聊天。更合适的定位是：由中心引擎维护状态、预算、证据和验证门禁；档位只定义能力边界和预算边界；具体 subagent、路线数量、并发方式、验证强度和续跑策略由 PolicyEngine 根据任务状态动态生成。

## 1. 从 Opus 调用 subagent 记录学到的经验

### 1.1 先侦察，后实现

Opus 面对大型代码工程时没有直接改代码，而是先启动若干 reader 类 subagent，例如：

- Core source reader
- Generator and reranker reader
- Tests and scripts reader

这说明成熟 agent 在大型任务中会先并行建立项目地图，再进入实现阶段。

迁移到 OpenO1：

- 数学推理任务中可先启动侦察型 agent：题意翻译、可用定理、边界条件、反例风险、形式化验证可能性。
- 代码推理任务中可先启动 reader agent：核心源码、测试脚本、配置入口、文档约束。
- 侦察型 agent 的目标不是给最终答案，而是给中心引擎提交结构化状态。

### 1.2 subagent 应有清晰边界

Opus 后续把工作拆给不同 implementer，例如 config / lexicon、engine / reranker、GUI / docs。它不是简单多开助手，而是按文件、模块或职责边界分配任务。

迁移到 OpenO1：

- Worker 最好绑定 route_id、step_id、artifact_scope 或 file_scope。
- 同一条路线的同一 step 不应由多个 Solver 同时修改。
- subagent 任务描述要强调只处理被分配边界内的问题。

### 1.3 主 agent 必须持续调度，不应挂机等待

Opus 运行中多次等待 180/300/600 秒，检查子代理状态、git status、修改文件、测试结果，然后决定继续等待、整合或接管。

迁移到 OpenO1：

- AgentTeamRuntime 应支持时间片调度，而不是一次性等待所有 subagent。
- 每个 subagent 需要状态：running、completed、partial、timeout、cancelled、killed_after_result、failed、needs_retry。
- 中心引擎要能在 subagent 未完全完成时收集 partial result。

### 1.4 主 agent 必须能接管

Opus 在发现 subagent 效率不高或产出不足时，会在主线程直接完成核心修改，并停止等待部分 subagent。

迁移到 OpenO1：

- subagent 是可替换劳动力，不是不可打断权威。
- Coordinator 应能取消、降级、重派或接管 subagent 任务。
- 不能因为某个 subagent 未返回就阻塞整个任务。

### 1.5 完成必须由外部证据确认

Opus 不是只相信 subagent 的“完成”声明，而是查看 diff、读取文件、运行 pytest、修复失败测试、再次验证。

迁移到 OpenO1：

- Worker 自报完成只能作为候选状态。
- ReviewGate 必须基于证据、测试、验证器结果、文件变更、阻断项状态做最终判断。
- goal_completed: true 必须经 CompletionAuditor 二次确认。

### 1.6 subagent 返回应压缩成结构化摘要

Opus 会把子代理结果整理成文件列表、修改摘要、测试结果、失败点和下一步动作。

建议 OpenO1 的 subagent 返回协议至少包含：

```ts
type SubagentReport = {
  agent_id: string
  role: string
  assigned_scope: string
  status: "completed" | "partial" | "timeout" | "failed" | "cancelled"
  claims: ClaimRecord[]
  evidence: Evidence[]
  artifacts_changed: ArtifactRef[]
  blockers: Blocker[]
  remaining_risks: string[]
  recommended_next_actions: string[]
  confidence: number
}
```

## 2. 从 DeerFlow 2.0 学到的档位控制经验

### 2.1 档位不是固定流程，而是能力向量

DeerFlow 2.0 的档位控制可抽象为若干能力开关与预算参数的组合：

- thinking_enabled
- is_plan_mode / planning_enabled
- subagent_enabled
- max_concurrent_subagents

迁移到 OpenO1：

- 档位不应写死成 Planner → 4 Worker → Verifier → Critic。
- 档位应定义能力边界：是否允许规划、是否允许 subagent、是否启用严格审查、是否启用续跑、并发上限是多少。
- 具体执行路线由 PolicyEngine 动态决定。

### 2.2 推荐档位语义

以下只是默认建议，不是硬编码流程：

```yaml
flash:
  thinking_enabled: false
  planning_enabled: false
  subagent_enabled: false
  verifier_strength: light
  continuation_enabled: false

standard:
  thinking_enabled: true
  planning_enabled: optional
  subagent_enabled: false
  verifier_strength: normal
  continuation_enabled: optional

pro:
  thinking_enabled: true
  planning_enabled: true
  subagent_enabled: optional
  verifier_strength: strict
  continuation_enabled: true

ultra:
  thinking_enabled: true
  planning_enabled: true
  subagent_enabled: true
  min_subagents: 1
  max_parallel_subagents: 4
  verifier_strength: strict
  continuation_enabled: true
  critic_enabled: true

research:
  thinking_enabled: true
  planning_enabled: true
  subagent_enabled: true
  max_parallel_subagents: dynamic
  verifier_strength: strict
  continuation_enabled: true
  context_reset_enabled: true
  memory_update_enabled: true
  failure_trace_persistence: true
```

### 2.3 用户档位应优先于系统默认降级

OpenO1 已有重要设计判断：subagent 可以由系统自动选择和动态调度，但 subagent 数量和强度的上限/下限，即档位，应由用户决定。

因此：

- 用户选择 Ultra 时，系统不能因为自判任务简单就完全降级成 Flash。
- 系统可以在 Ultra 内部决定启动哪些类型的 agent，但必须满足该档位的最低强度。
- 用户选择 Flash 时，系统不应擅自开启昂贵的多 agent 搜索，除非安全或正确性要求必须升级并向用户说明。

### 2.4 并发上限必须代码层控制

DeerFlow 的经验说明，并发不能只靠 prompt 提醒。OpenO1 应使用 BudgetManager / Middleware 硬限制：

- max_concurrent_subagents
- max_total_agents
- max_rounds
- max_repair_rounds
- max_verify_rounds
- max_runtime_seconds
- max_no_progress_rounds

Prompt 可以建议模型不要过度派发，但真正限制必须在代码层执行。

## 3. 从 AutoGen / CrewAI / AgentScope / Anthropic 学到的通用经验

### 3.1 agent description 是调度接口

AutoGen SelectorGroupChat 的启发是：agent 的名称和描述会直接影响调度。OpenO1 中每个 agent 需要有可路由描述，而不仅是“Worker 1”。

建议：

```ts
type AgentDescriptor = {
  role: string
  capabilities: string[]
  preferred_inputs: string[]
  forbidden_actions: string[]
  output_schema: string
  cost_profile: "low" | "medium" | "high"
  risk_profile: "low" | "medium" | "high"
}
```

### 3.2 CrewAI 的经验：Crew 应包含 Agents、Tasks、Process 和 Manager

AgentTeam 不应只是 agent 列表，还应包含：

- agents：可用角色与能力。
- tasks：拆出来的任务单元。
- process：顺序、层级、动态调度或混合流程。
- manager：中心调度器。
- callbacks：step/task 完成后的审计或记录。
- memory/cache：外部状态与成本优化策略。

迁移到 OpenO1：

```ts
type AgentTeamSpec = {
  level: ReasoningLevel
  agents: AgentDescriptor[]
  tasks: AgentTaskSpec[]
  process_policy: ProcessPolicy
  budget: AgentBudget
  tool_groups: ToolGroupPolicy
  callbacks: TeamCallback[]
  review_gate: ReviewGatePolicy
}
```

### 3.3 AgentScope 的经验：事件流、状态隔离、工具组、权限、workspace

OpenO1 应继续吸收 AgentScope 的 runtime 工程经验：

- Message 和 Event 分离。
- Agent 尽量无状态，状态归中心引擎。
- 工具按阶段分组暴露，避免 schema 污染上下文。
- 权限分层，尤其是本地命令、文件修改、网络访问。
- Workspace 隔离与可复现。
- Middleware 承担检查、审阅、继续策略和 trace 记录。

需要坚持的边界：

- 不把多 agent 自由对话当作能力来源。
- 不把自然语言摘要当作数学证明状态。
- 不把工具调用成功当作推理正确。

### 3.4 Anthropic 的经验：workflow 与 agent 要区分

Anthropic 的有效 agent 经验可转化为 OpenO1 的判断：

- Workflow：代码路径预定义，适合可控、低风险、可重复任务。
- Agent：模型动态决定流程，适合开放任务，但需要更强预算和审阅。
- Orchestrator-workers：适合复杂代码、研究、多文件任务。
- Evaluator-optimizer：适合证明修复、测试修复、答案润色、反例驱动改进。
- Parallelization：适合独立路线、独立审查、独立反例搜索。

OpenO1 应允许在同一任务中混合 workflow 和 agent：固定门禁 + 动态分派。

## 4. 对现有多 Agent 协议的修正

原先协议中出现的“Planner 生成 2-4 条路线”只能作为默认建议，不能成为硬规则。

更准确的表述应是：

Planner 根据任务状态、用户档位、预算、可并行性和不确定性生成适量候选路线。候选路线数量可以为 1，也可以随复杂度、风险、验证失败、用户档位或探索需求动态扩展。协议不固定路线数，只要求每条路线可验证、可比较、可回滚。

同理，AgentTeam 的流程也不应固定为每次都启动 Planner、Worker、Verifier、Critic、Solver、Synthesizer。角色应被视为能力槽：

- 简单任务：MainAgent + Verifier。
- 中等任务：Planner + Worker + Verifier。
- 高风险任务：多 Worker + Critic + Solver + ReviewGate。
- 长期工程任务：GoalRuntime + EvidenceCollector + CompletionAuditor + ContinuationBuilder。

## 5. 推荐新增核心对象

```ts
type ReasoningLevel = {
  name: "flash" | "standard" | "pro" | "ultra" | "research" | string
  thinking_enabled: boolean
  planning_enabled: boolean | "optional"
  subagent_enabled: boolean | "optional"
  min_subagents: number
  max_parallel_subagents: number
  verifier_strength: "light" | "normal" | "strict"
  continuation_enabled: boolean
  critic_enabled: boolean
  context_reset_enabled: boolean
  memory_update_enabled: boolean
}
```

```ts
type ProcessPolicy = {
  mode: "single" | "sequential" | "hierarchical" | "orchestrator_workers" | "evaluator_optimizer" | "dynamic"
  allow_dynamic_agent_creation: boolean
  allow_parallel_routes: boolean
  allow_main_agent_takeover: boolean
  require_evidence_before_completion: boolean
}
```

```ts
type AgentTaskSpec = {
  task_id: string
  role_hint: string
  scope: string
  inputs: ArtifactRef[]
  expected_output_schema: string
  dependencies: string[]
  timeout_seconds: number
  can_return_partial: boolean
}
```

## 6. 近期可转化任务

1. 在 `engine.py` 中增加 `ReasoningLevel` / `ReasoningLevelProfile`。
2. 把 `ExecutionDecision` 中固定的 max_routes、max_parallel_workers 扩展为由 level + task profile + budget 共同决定。
3. 新增 `AgentTeamRuntime` 最小原型，先使用 mock agent 验证流程。
4. 新增 `SubagentReport` 和 `AgentTaskSpec` 数据结构。
5. 新增 `SubagentState`，区分 completed、partial、timeout、cancelled、killed_after_result、failed。
6. 新增 `CompletionAuditor`，拒绝只靠 worker 自报完成。
7. 新增 `ContinuationBuilder`，在未完成但预算未耗尽时生成下一轮最小任务。
8. 修改 `docs/multi-agent-protocol.md`，把固定路线数改为弹性路线数，把固定流程改为能力槽和 policy 决策。

## 7. 当前结论

OpenO1 应该学习强 agent 的调度行为，但不要把这种行为写死成单一流程。真正应该固化的是：中心状态所有权、结构化事件、证据边界、验证门禁、预算控制、失败可追踪、未完成可续跑。真正应该保持弹性的是：路线数量、agent 类型、并发方式、工具组、修复轮数和是否接管。