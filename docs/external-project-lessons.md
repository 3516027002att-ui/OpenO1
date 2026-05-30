# OpenO1 外部项目学习记录

## 文档定位

本文档用于长期记录 OpenO1 从其他开源项目、论文、工程框架、agent runtime、验证系统和推理框架中学到的可迁移设计。

它不是资料摘抄，也不是项目收藏列表。它的目标是把外部项目中的经验转化为 OpenO1 可执行的设计约束、模块候选、风险提示和后续任务。

## 项目级协作规矩

之后在 GPT 项目页面中的任何聊天里，只要讨论或分析了外部项目、论文、框架、工具链，并且发现对 OpenO1 有借鉴价值，就应该优先沉淀到本文档，或在本文档中追加一个条目。

记录时必须区分三类内容：

- 外部项目已经明确实现的事实。
- 对 OpenO1 的迁移判断。
- 仍需实验验证的假设。

不得把外部项目的宣传口径直接当成 OpenO1 的结论。尤其是涉及推理能力、benchmark、数学能力、o1 风格能力、heavy model 行为时，必须保持“目标、假设、实验结果”三者分离。

## 推荐记录格式

每次新增记录时，建议使用以下结构：

- 项目名称和来源链接。
- 观察日期。
- 项目定位。
- 对 OpenO1 可取之处。
- 不应照搬之处。
- 可以转化为 OpenO1 的模块或任务。
- 仍需验证的问题。

## 已记录项目

| 日期 | 外部项目 | 主要启发 | 对应 OpenO1 方向 |
| --- | --- | --- | --- |
| 2026-05-26 | AgentScope | event/message 分离、workspace、middleware、tool group、permission、service 化 | ReasoningEventLog、ProofStateContext、VerifierGate、MathWorkspace |
| 2026-05-30 | OpenCode / opencoder / Cline / OpenHands | goal 不应只是 prompt；需要代码层 goal loop、状态词、审阅器、续跑机制 | GoalRuntime、CompletionAuditor、ContinuationBuilder、StopController |
| 2026-05-30 | Opus subagent 记录 / DeerFlow 2.0 / AutoGen / CrewAI / AgentScope / Anthropic | AgentTeam 应是弹性调度状态机；档位定义能力边界而非固定流程；subagent 需要结构化报告、证据门禁、超时接管和续跑 | ReasoningLevel、AgentTeamRuntime、SubagentReport、AgentTaskSpec、ProcessPolicy、BudgetManager |

## AgentScope 摘要

来源：https://github.com/agentscope-ai/agentscope

AgentScope 更接近 production-ready agent runtime 或 agent harness，而不是数学推理增强算法本身。它的价值不在于直接让模型变聪明，而在于把 agent 的运行过程做成可观测、可恢复、可控、可部署的工程骨架。

对 OpenO1 的核心启发：

- 建立 ReasoningEventLog，记录推理、验证、审阅和继续决策。
- Agent 尽量无状态，状态归中心引擎管理。
- 上下文压缩要改造成证明状态压缩，不能照搬普通自然语言摘要。
- 工具应按任务阶段分组激活，而不是一次性暴露全部工具。
- 权限系统是本地 agent 安全运行的基础。
- Review Gate 适合做成中间件，而不是最后的口头自检。
- Workspace 抽象适合 OpenO1 的本地验证环境。
- 后期应保留 service 化边界，方便同一套推理框架接入不同模型。

不应照搬：

- 不要把多 agent 自由对话当作能力来源。
- 不要把普通 ReAct loop 当作 o1 风格推理核心。
- 不要把自然语言 summary 当作数学证明状态。
- 不要把工具调用成功等同于推理正确。
- 不要把工程成熟度误认为模型推理能力提升。

近期可转化任务：

1. 定义 ReasoningEvent 数据结构。
2. 定义 ReasoningEventLog 追加式日志。
3. 定义 ProofState。
4. 定义 VerifierResult。
5. 实现最小 VerifierGate。
6. 实现 MathWorkspace，先接入 Python 或 SymPy，再扩展到 Lean。
7. 实现 ReviewGate。

## Goal 模式与长期任务闭环摘要

观察日期：2026-05-30

参考对象：OpenCode、opencoder、Cline、OpenHands。

### 外部项目已经明确呈现的事实

- OpenCode 的 command/custom command 更接近 prompt template。它可以把固定模板发给 LLM，并指定 agent 执行，但这类机制本身不保证长期目标完成。
- OpenCode 本体具备 agentic loop 和 steps 限制；当没有 steps 限制时，循环可以持续到模型选择停止或用户中断；达到 steps 后会总结已完成与剩余工作。这说明它有工具循环，但完成语义仍然高度依赖模型自身停止判断。
- opencoder 通过 orchestrator、planner、builder 三类 agent 形成 Plan → Build → Commit/Push → Repeat 的循环，并使用类似 READY_FOR_NEXT_TASK 的状态词进行交接。它已经接近“状态词驱动续跑”，但主要强约束仍写在 agent prompt 中。
- Cline 的 attempt_completion 把“任务完成”变成一个显式工具调用，优于普通自然语言总结；但它仍然主要依赖模型自报完成。
- OpenHands 更接近完整 agent runtime。它的核心价值在 controller、state、event stream、budget、iteration、delegate、stuck detection 等外部控制结构。

### 对 OpenO1 的迁移判断

OpenO1 的 goal 不应该定义为“更强的提示词”。Goal 应该定义为由外部状态机控制的长期任务闭环。模型负责执行、报告状态、提出下一步；是否完成、是否继续、是否需要审阅，应由 harness 根据结构化状态、测试证据、文件变更和审阅结果决定。

核心原则：

- 未完成不应自然结束。
- 完成不能只靠模型口头声明。
- goal_completed: false 必须触发下一轮。
- goal_completed: true 必须经过 verifier/auditor 二次确认。
- 停止原因必须结构化记录，包括 OUTPUT_LIMIT、TOOL_LIMIT、CONTEXT_LIMIT、BLOCKED、SELF_STOP、PARTIAL_PROGRESS 等。
- 续跑 prompt 不应简单重复原始 prompt，应由上一轮结果、未完成项、证据、失败原因和下一步最小任务生成。

### 建议的 OpenO1 模块

- GoalRuntime：负责 goal 生命周期和循环控制。
- GoalState：记录目标、验收标准、当前完成度、剩余任务、预算、轮次、阻塞原因。
- StatusParser：解析模型输出中的机器可读状态块。
- CompletionAuditor：独立审阅完成度，不直接相信 worker 自报。
- EvidenceCollector：收集 git diff、测试结果、日志、运行结果、文件状态。
- ContinuationBuilder：根据审阅结果生成下一轮接力 prompt。
- StopController：决定继续、完成、暂停、失败或请求用户介入。

### 推荐状态块协议草案

```text
<O1_STATUS>
state: INCOMPLETE | COMPLETED | BLOCKED | NEED_USER | FAILED
goal_completed: false
completion_score: 0.42
stop_reason: OUTPUT_LIMIT | TOOL_LIMIT | CONTEXT_LIMIT | BLOCKED | SELF_STOP | PARTIAL_PROGRESS
finished_items:
- ...
unfinished_items:
- ...
evidence:
- tests_run: ...
- files_changed: ...
next_minimal_task: ...
next_prompt: ...
</O1_STATUS>
```

### 推荐运行循环草案

```python
while budget.remaining():
    result = worker.run(current_prompt)
    status = status_parser.parse(result.text)
    evidence = evidence_collector.collect(repo, tests, logs)

    audit = completion_auditor.verify(
        goal=goal,
        criteria=acceptance_criteria,
        worker_status=status,
        evidence=evidence,
    )

    if status.goal_completed and audit.passed:
        return VERIFIED_COMPLETED

    if audit.blocked:
        return BLOCKED_WITH_REPORT

    current_prompt = continuation_builder.build(
        goal=goal,
        previous_result=result,
        audit=audit,
        unfinished_items=audit.unfinished_items,
        next_minimal_task=audit.next_task,
    )

return BUDGET_EXHAUSTED_WITH_HANDOFF
```

### 不应照搬之处

- 不要把 OpenCode custom command 等同于真正 goal runtime。
- 不要只靠 prompt 里的“NEVER STOP”实现长期任务，因为模型仍可能因 token、tool、上下文、时间、策略或自我总结而停下。
- 不要只使用 READY_FOR_NEXT_TASK 这类单一状态词；应使用结构化状态块，保留停止原因、证据和下一步计划。
- 不要只靠 attempt_completion 证明任务完成；必须加入外部审阅和可验证证据。

### 近期可转化任务

1. 在 OpenO1 中新增 GoalRuntime 最小原型。
2. 定义 O1_STATUS 结构化输出协议。
3. 在每轮 worker 结束后强制解析 O1_STATUS。
4. 当 state 为 INCOMPLETE 且预算未耗尽时，自动生成 continuation prompt 并续跑。
5. 增加 CompletionAuditor，先使用规则检查和模型审阅结合的方式。
6. 接入 EvidenceCollector，至少收集 git diff、测试命令输出、错误日志和文件变更摘要。
7. 给 GoalRuntime 增加单元测试：模型明确说“未完成”时，必须触发下一轮；模型说“完成”但测试失败时，必须拒绝完成。

## AgentTeam 调度与弹性档位摘要

观察日期：2026-05-30

详细记录：`docs/external-lessons/agentteam-dispatch-and-flexible-tiers.md`

参考对象：Antigravity 中 Opus 调用 subagent 的实际记录、DeerFlow 2.0、AutoGen、CrewAI、AgentScope、Anthropic effective agents。

### 对 OpenO1 的迁移判断

OpenO1 的 AgentTeam 不应设计成固定流程图，也不应退化成多个 agent 自由聊天。更合适的定位是：由中心引擎维护状态、预算、证据和验证门禁；档位只定义能力边界和预算边界；具体 subagent、路线数量、并发方式、验证强度和续跑策略由 PolicyEngine 根据任务状态动态生成。

关键原则：

- Opus 的价值不只是“会启动 subagent”，更在于它会先侦察、再实现、边等待边检查、必要时接管、最后用测试和 diff 做外部验证。
- DeerFlow 2.0 的档位经验说明，档位应是 thinking、planning、subagent、并发上限、验证强度、续跑能力等能力向量组合，而不是固定工作流。
- AutoGen 的经验说明，agent name / description 是调度接口，OpenO1 需要 AgentDescriptor。
- CrewAI 的经验说明，AgentTeam 应包含 agents、tasks、process、manager、callbacks、memory/cache 和 review gate，而不仅是 agent 列表。
- AgentScope 的经验说明，事件流、状态隔离、工具组、权限、workspace 和 middleware 是可控 runtime 的基础。
- Anthropic 的经验说明，workflow 与 agent 应区分；OpenO1 可以采用固定门禁 + 动态分派的混合模式。

### 对现有协议的修正

原先协议中出现的“Planner 生成 2-4 条路线”只能作为默认建议，不能成为硬规则。

更准确的表述是：Planner 根据任务状态、用户档位、预算、可并行性和不确定性生成适量候选路线。候选路线数量可以为 1，也可以随复杂度、风险、验证失败、用户档位或探索需求动态扩展。协议不固定路线数，只要求每条路线可验证、可比较、可回滚。

真正应该固化的是：中心状态所有权、结构化事件、证据边界、验证门禁、预算控制、失败可追踪、未完成可续跑。

真正应该保持弹性的是：路线数量、agent 类型、并发方式、工具组、修复轮数和是否接管。

### 近期可转化任务

1. 在 `engine.py` 中增加 `ReasoningLevel` / `ReasoningLevelProfile`。
2. 把 `ExecutionDecision` 中固定的 max_routes、max_parallel_workers 扩展为由 level + task profile + budget 共同决定。
3. 新增 `AgentTeamRuntime` 最小原型，先使用 mock agent 验证流程。
4. 新增 `SubagentReport` 和 `AgentTaskSpec` 数据结构。
5. 新增 `SubagentState`，区分 completed、partial、timeout、cancelled、killed_after_result、failed。
6. 新增 `CompletionAuditor`，拒绝只靠 worker 自报完成。
7. 新增 `ContinuationBuilder`，在未完成但预算未耗尽时生成下一轮最小任务。
8. 修改 `docs/multi-agent-protocol.md`，把固定路线数改为弹性路线数，把固定流程改为能力槽和 policy 决策。
