# 模型训练分布与 subagent 委派策略学习记录

## 来源

观察对象：用户提供的文章截图，主题为 Codex、Claude Code、Cursor 在 subagent 委派策略上的差异。

观察日期：2026-05-31

## 前提说明

本文是逆向工程式分析，不是三家内部设计文档。它基于公开资料、产品行为、system prompt / 工具描述、文档描述和可观察运行方式推断。结论不应当作确定事实，但设计思路对 OpenO1 有参考价值。

## 一句话结论

Subagent 策略不应该照搬任何一家。OpenO1 应根据接入模型的训练分布、工具调用可靠性、上下文管理能力、元决策能力、用户档位和任务风险，动态决定“谁来判断是否委派、何时委派、委派给谁、是否等待、如何回收结果”。

## 1. subagent 解决的真实问题

Subagent 的核心价值首先是上下文隔离。

一个 agent 在推进任务时，经常要做大量探索性工作：搜索代码库、读取大量文件、运行命令、查看 stack trace、分析日志、试错。这些中间产物对当前步骤有用，但对后续步骤常常是噪声。如果全部塞进主对话，容易造成：

- context pollution：上下文污染。
- context rot：上下文腐烂。
- Lost in the Middle：模型忽略中间关键事实。
- 主线被一次性日志、搜索结果、编译输出污染。

Subagent 的直接解法是：把脏活交给独立 context window，主线只接收干净摘要、证据和下一步建议。

Subagent 还带来附带好处：

- 并行：多个 subagent 可同时工作。
- 权限隔离：subagent 可以限制只读或限制工具权限。
- 成本控制：探索型 subagent 可以使用更便宜模型。
- 错误隔离：subagent 崩溃不污染主对话。
- 多 agent 桥梁：主 agent + 若干 subagent 是单 agent 走向 multi-agent 的桥梁。

## 2. 三家产品的不同路线

### 2.1 Codex：用户显式触发，模型不主动创建

文章判断：Codex 的公开定位接近“不会自动创建 subagent，只有用户明确要求时才使用”。触发方式偏向直接在 prompt 中写明，例如要求并行委派或启动若干 agent。

可能原因：

- Codex 的强化学习目标更偏真实编码任务：精确遵循指令、执行、跑测试、直到通过。
- 在这种训练目标下，让模型自己决定是否创建 subagent 会带来奖励归因模糊。
- 任务成功后，很难区分成功来自 subagent 决策、代码质量、测试策略还是执行路径。
- 过多“每一步都能选择自己做或委派”的自由度会让行为空间膨胀，RL 更难收敛。

迁移判断：Codex-like 模型更适合把委派决策从模型行为空间中移除，由用户显式触发或 harness 触发。模型主要优化“写出正确代码、遵循指令、跑通测试”。

### 2.2 Claude Code：模型主动判断，默认会用

文章判断：Claude Code 更倾向让模型主动判断何时使用 subagent。其核心思想与“Context as scarce resource”一致：把上下文视为稀缺资源，subagent、摘要、压缩、sidechain 都是管理稀缺资源的手段。

可能原因：

- Anthropic 更重视“values over rules”：用好的判断力引导行为，而不是完全依赖僵硬规则。
- Claude 的训练中可能包含“何时委派、何时自己做、何时压缩上下文、何时回收摘要”的元决策能力。
- Opus 类模型在决定是否使用 subagent 时，本质上是在做资源管理决策。

迁移判断：Claude-like 模型可以允许模型建议主动委派，但仍要由 BudgetManager、ReviewGate 和 EvidenceCollector 做外部约束。

### 2.3 Cursor：模型判断，但产品层强引导

文章判断：Cursor 的核心场景是同时接入多家模型，包括 Claude、GPT、Gemini 和第三方模型。它不能假设每个接入模型都学会了“何时主动创建 subagent”这种元能力。

因此 Cursor 的策略更像：

- 通过 system prompt 中的 Task 工具描述强引导模型。
- 写清楚什么场景该用、什么场景不该用。
- 预定义固定 subagent 角色，例如 explore、shell、browser-use 等。
- 降低对模型自主委派判断力的依赖。

迁移判断：对多模型平台来说，固定角色 + 详细工具描述 + harness 审批，比完全开放动态 subagent 更稳。尤其对第三方模型和本地弱模型，不能假设它们拥有良好的委派判断力。

## 3. 同一件事的不同层面

工具格式适配和 subagent 委派适配，本质上都是 harness 逆向适配模型训练分布。

工具格式层面：

- 有的模型更适合 patch。
- 有的模型更适合 string replace。
- 有的模型更适合 JSON tool call。
- 有的模型更适合自然语言计划后再由 harness 转换。

委派策略层面：

- 有的模型适合用户显式触发。
- 有的模型适合 harness 自动触发。
- 有的模型可以提出委派建议。
- 少数强模型可以被允许在预算内主动委派。

因此，harness 抽象的尽头是：逆向适配每个模型的训练分布，而不是强行让所有模型执行同一种 agent 策略。

## 4. OpenO1 的设计原则

### 4.1 不要假设所有模型都像 Claude 一样会主动委派

OpenO1 的短期目标是接入本地可部署开源模型，通过固定化推理工作流和微调提升数学推理表现。因此不能假设模型天然具备：

- 判断什么时候该委派。
- 判断该委派给什么角色。
- 判断是否等待 subagent。
- 判断 subagent 结果是否可靠。
- 判断是否需要接管。

这些能力应优先由 harness 实现，再逐步通过训练数据迁移给模型。

### 4.2 委派决策分三层

第一层：硬策略层。

由代码决定。用户选择的档位、任务风险、预算、工具权限、上下文污染风险都会进入 PolicyEngine。比如 Ultra 档至少触发一定强度的并行审查；Flash 档默认不启动昂贵 subagent。

第二层：模型建议层。

模型可以建议启动 reader、verifier、critic、counterexample searcher 或 solver，但建议必须经过 PolicyEngine 审批。

第三层：训练适配层。

系统记录每个模型是否擅长主动委派、是否容易过度委派、是否容易逃避委派、是否适合当 Coordinator、是否更适合当 Worker / Verifier / Critic。

## 5. 推荐新增核心对象

```ts
type ModelCapabilityProfile = {
  model_id: string
  instruction_following: number
  tool_call_reliability: number
  delegation_judgment: number
  context_management: number
  self_verification: number
  long_horizon_planning: number
  prefers_explicit_delegation: boolean
  can_coordinate_agent_team: boolean
  can_be_worker: boolean
  can_be_verifier: boolean
  can_be_critic: boolean
}
```

```ts
type ModelAdaptationPolicy = {
  delegation_control: "user_explicit" | "harness_triggered" | "model_suggested" | "model_autonomous"
  tool_format_preference: "patch" | "string_replace" | "json_tool_call" | "natural_language"
  subagent_role_style: "fixed_roles" | "dynamic_roles" | "hybrid"
  context_strategy: "main_context_heavy" | "subagent_isolation" | "context_pack_reset"
  verification_dependency: "external_strict" | "model_assisted" | "light"
}
```

```ts
type DelegationDecision = {
  source: "user" | "harness" | "model_suggestion" | "model_autonomous"
  approved: boolean
  reason: string
  required_level: ReasoningLevel
  selected_roles: string[]
  expected_context_benefit: number
  expected_cost: number
  risk: "low" | "medium" | "high"
}
```

## 6. 不同模型的推荐默认策略

### 6.1 Codex-like 模型

默认策略：

- delegation_control: user_explicit 或 harness_triggered。
- 不让模型自主创建 subagent。
- 模型主要负责局部实现、测试修复、按指令执行。
- 委派由用户档位、任务复杂度或外部 harness 触发。

### 6.2 Claude-like 模型

默认策略：

- delegation_control: model_suggested，可在高档位局部放宽到 model_autonomous。
- 允许模型建议 reader / verifier / critic。
- 必须有预算、超时、证据收集和 ReviewGate。
- 重点利用其上下文管理和资源管理判断力。

### 6.3 Cursor-compatible 第三方模型

默认策略：

- delegation_control: harness_triggered 或 model_suggested。
- subagent_role_style: fixed_roles 或 hybrid。
- system prompt / tool schema 写清楚角色边界、使用场景和禁止事项。
- 降低对模型自主委派能力的依赖。

### 6.4 本地弱模型

默认策略：

- 不让它担任 Coordinator。
- 更适合做 Worker、Candidate Solver、Local Verifier、格式转换器。
- 委派、路线选择、是否接管、是否继续由 harness 决定。
- 输出必须结构化，且由更强 Verifier / 规则验证器审查。

## 7. 对 OpenO1 微调的启发

OpenO1 未来如果要训练自己的本地模型，不应一开始就要求模型学会所有元决策。

更稳妥的训练路线：

1. 先训练局部能力：按指定 route_id / step_id 输出候选推理步骤。
2. 再训练验证能力：识别不合法变形、缺失假设、边界条件。
3. 再训练结构化报告能力：输出 SubagentReport、VerifierResult、CritiqueRecord。
4. 再训练委派建议能力：什么时候建议 reader、critic、verifier、counterexample search。
5. 最后才训练 Coordinator 级能力：动态创建 agent team、分配任务、接管失败 subagent。

## 8. 近期可转化任务

1. 新增 `ModelCapabilityProfile` 数据结构。
2. 新增 `ModelAdaptationPolicy` 数据结构。
3. 在 `PolicyEngine.decide()` 中同时考虑 task profile、reasoning level、model profile。
4. 把 subagent 委派模式拆成 user_explicit、harness_triggered、model_suggested、model_autonomous。
5. 给本地模型默认设置为 harness_triggered，不让其直接担任 Coordinator。
6. 给高档位任务加入 context pollution risk 评估：当搜索、日志、文件读取会污染主上下文时，优先使用隔离 subagent。
7. 为训练数据增加标签：委派是否必要、委派对象、委派收益、是否过度委派、是否本可主 agent 完成。
8. 将“模型建议委派但 harness 拒绝/批准”的记录保存进 trace，作为未来训练元决策能力的数据。

## 9. 当前结论

OpenO1 不应追求让所有模型都像 Claude 一样主动委派。更正确的方向是：根据模型能力画像、用户档位、任务复杂度、上下文污染风险和预算状态，动态选择委派策略。

真正成熟的 harness 不是让所有模型走同一条路，而是为不同模型套上不同外壳：让 Codex-like 模型专注执行，让 Claude-like 模型发挥资源管理判断，让 Cursor-compatible 模型接受强 prompt / 固定角色引导，让本地弱模型先做可验证的局部 worker。