# Agentic Reasoning Control Loop 设计记录

## 1. 定位

模型 API 的基本形态通常仍是一次请求返回一次响应。即使模型已经具备很强的工具使用和 Agentic 能力，长时间推理仍需要外层 runtime 维护状态、执行动作、管理预算并决定何时结束。

OpenO1 的目标不只是让模型持续执行任务，还要把行动组织成推理：搜索用于获得证据，代码用于构造实验，工具结果用于验证或推翻命题，并行 Agent 用于探索相互独立的假设，回滚用于撤销错误前提。

核心原则：

- 模型提交结构化意图、候选命题、研究路线或候选答案。
- harness / center engine 是唯一状态所有者，负责执行工具、记录证据、管理分支、预算和终止。
- 所有行动必须服务于未决问题、命题验证、反例搜索或路线推进。
- Solver 只能申请结束，不能批准结束。
- 工具结果是带边界的证据，不自动等于真理。
- Runtime 应按需增加或删除流程，不能把固定多 Agent 仪式当作永久架构。

## 2. 基本循环

```text
user task
  -> build reasoning state
  -> choose next unresolved target
  -> call model
  -> parse proposed action
  -> execute tool / branch route / update claim / review draft
  -> append bounded evidence to reasoning state
  -> estimate progress and marginal value
  -> continue, backtrack, branch, finalize, or stop
```

在实现上，连续思考由多次模型调用、工具执行和结构化状态更新共同构成：

```python
while not state.done:
    target = controller.choose_target(state)
    context = build_context(state, target)
    action = llm.call(context, tools=tool_schemas)

    observation = runtime.execute(action)
    state.apply(observation)

    if action.type == "draft_final":
        review = review_gate.check(state, action.answer)
        decision = stop_controller.decide(state, action, review)
        if decision.type == "FINAL":
            return action.answer
        state.add_review_feedback(review)

    if budget.exceeded() or state.no_progress_too_long():
        return build_best_effort_answer(state)
```

## 3. 推荐动作枚举

模型每轮输出应解析为中心引擎可处理的动作：

```ts
type EngineAction =
  | { type: "continue_solve"; reason: string; target: ClaimId | SubgoalId }
  | { type: "propose_route"; route: RoutePlan; reason: string }
  | { type: "branch_route"; parent_route_id: string; route: RoutePlan; reason: string }
  | { type: "backtrack"; target: ClaimId | RouteId; reason: string }
  | { type: "tool_call"; tool_name: string; arguments: unknown; reason: string }
  | { type: "request_review"; target: ClaimId | RouteId }
  | { type: "draft_final"; answer: string; confidence: number }
  | { type: "report_blocker"; blocker: Blocker }
```

中心引擎只使用少量硬决策：

```ts
type ControllerDecision =
  | { type: "CONTINUE"; reason: string }
  | { type: "CALL_TOOL"; tool_name: string; arguments: unknown }
  | { type: "BRANCH"; reason: string }
  | { type: "BACKTRACK"; reason: string }
  | { type: "REVIEW"; reason: string }
  | { type: "REVISE"; blockers: Blocker[] }
  | { type: "FINAL"; reason: string }
  | { type: "BEST_EFFORT"; reason: string }
  | { type: "FAIL"; blockers: Blocker[] }
```

## 4. Shared Reasoning State

harness 每轮重新组装上下文，不应把全部聊天历史无差别塞回模型。推荐维护动态研究状态：

```ts
type SharedReasoningState = {
  task: TaskSpec
  open_subgoals: Subgoal[]
  claims: ClaimRecord[]
  hypotheses: HypothesisRecord[]
  routes: RouteRecord[]
  conflicts: ConflictRecord[]
  tool_trace: ToolObservation[]
  failed_attempts: FailedAttempt[]
  review_notes: ReviewNote[]
  blockers: Blocker[]
  final_candidate?: FinalDraft
  budget: BudgetState
  progress: ProgressState
}
```

关键规则：

- `verified` 只能由 Verifier、DomainVerifier 或 ReviewGate 写入。
- `final_candidate` 只是候选答案，不能直接交给用户。
- 工具结果必须记录来源、时间、输入、输出、置信度和局限。
- 被驳回路线、失败实验和重复错误必须保留，避免系统反复进入相同死路。
- 当前上下文只装载与目标命题最相关的状态；完整轨迹保存在外部状态中。

## 5. 工具结果的推理语义

工具调用必须对应明确的认知目的：

```ts
type ToolObservation = {
  tool_name: string
  input: unknown
  output: unknown
  purpose: "collect_evidence" | "find_counterexample" | "test_hypothesis" | "verify_claim" | "inspect_state" | "other"
  result_type: "search" | "symbolic_check" | "numeric_check" | "test" | "proof_check" | "file_edit" | "other"
  confidence?: number
  supports: ClaimId[]
  contradicts: ClaimId[]
  limitations: string[]
  error?: string
}
```

典型边界：

- 符号计算能验证代数展开，但可能忽略定义域。
- 数值测试能发现反例，不能证明恒成立。
- 搜索结果能提供外部证据，仍需判断来源可靠性与时效性。
- 单元测试通过只能说明覆盖用例通过，不能证明程序完全正确。

ReviewGate 必须检查工具结果能够支持什么，也要检查它无法支持什么。

## 6. 路线分叉与回溯

OpenO1 不能只沿一条错误路线持续修补。

建议分叉的情况：

- 存在多个实质不同的假设或解法。
- 当前路线依赖高风险前提。
- 验证结果互相冲突。
- 同一路线多次修复仍无明显进展。
- 新证据打开了不同的搜索空间。

建议回溯的情况：

- 上游关键命题被证伪。
- 工具结果证明问题定义或约束理解错误。
- 当前路线只能通过不断增加未经验证的假设维持。
- 继续投入的预期收益显著低于探索替代路线。

## 7. 终止批准权

OpenO1 的硬原则：

```text
Solver can request final.
Runtime decides final.
```

允许 `FINAL` 的典型条件：

- 原始任务目标已经覆盖。
- 必要子目标已解决，剩余未决项有明确边界说明。
- 无未解决的 fatal / major blocker。
- 关键命题有充分证据或完整推导。
- DomainVerifier 没有阻断项。
- ReviewGate 返回 pass。
- 继续推理的预期收益不足以消耗更多预算。

必须继续、分叉或回溯的典型条件：

- 任务目标没有完全回答。
- 仍有未验证关键命题。
- 工具结果与推导冲突。
- 关键前提被推翻。
- 当前路线连续多轮无实质进展，但仍存在替代路线。
- Reviewer 给出 fatal / major issue。

允许 `BEST_EFFORT` 的典型条件：

- 预算耗尽。
- 所有可行路线均停止进展。
- 外部工具不可用，但仍能说明已验证与未验证边界。
- 问题本身超出当前模型和 runtime 的可解决范围。

`BEST_EFFORT` 必须明确说明已完成部分、未完成部分、阻断原因和可信边界。

## 8. Review Severity

```ts
type ReviewSeverity = "fatal" | "major" | "minor" | "style"
```

- `fatal`：禁止 FINAL，必须回溯、修复或失败。
- `major`：通常禁止 FINAL，除非预算耗尽并进入 BEST_EFFORT。
- `minor`：按任务重要性决定是否继续。
- `style`：不应阻断 FINAL。

## 9. 数学推理默认门槛

- 变量定义一致。
- 关键代数步骤经过符号验证或可审查推导。
- 最终答案代回原条件或形成逻辑闭环。
- 检查定义域、边界值和特殊值。
- 检查漏根、增根、除以零和偷换条件。
- 证明类题目不能把数值验证当作完整证明。

## 10. 与其他规范的关系

- `docs/multi-agent-protocol.md` 规定 AgentTeam 的通信、路线、验证和 ReviewGate。
- 本文档规定中心引擎如何把模型的 Agentic 动作组织成长期推理循环。
- AgentTeam 只是可选执行策略，不能绕过 Shared Reasoning State、ToolTrace、ReviewGate 或 StopController。
- 当单模型已经能够可靠完成某个环节时，应减少无收益的角色拆分和额外调用。

## 11. 一句话原则

> **Turn agentic capability into reasoning capability.**

```text
hypothesize -> act -> observe -> verify -> branch/backtrack -> synthesize
```
