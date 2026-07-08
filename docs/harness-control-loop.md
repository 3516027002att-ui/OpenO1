# Harness Control Loop 设计记录

## 1. 背景

模型 API 的基本形态是一次请求返回一次响应。OpenO1 不能假设模型会在单次 API 调用中持续运行、自动执行工具或自行保存工作状态。

OpenO1 的多步推理、工具调用和继续修正，必须由外层 harness / center engine 驱动。模型只在每一轮根据当前上下文输出下一步意图；真正的工具执行、状态维护、预算控制和终止批准由中心引擎完成。

核心原则：

- 模型不是执行器；模型只提交结构化意图、候选结论或候选答案。
- harness 是唯一状态所有者，负责把工具结果、审阅意见和任务状态写回 Shared Context。
- Solver 只能申请结束，不能批准结束。
- 最终输出必须经过 ReviewGate / StopController 放行。
- 工具结果是证据，不自动等于真理；必须记录其适用范围和局限。

## 2. 基本循环

```text
user task
  -> build context
  -> call model once
  -> parse model action
  -> execute tool / update state / review draft
  -> append observation to Shared Context
  -> call model again
  -> repeat until FINAL / BEST_EFFORT / FAIL
```

在实现上，这不是一次 API 调用中的连续思考，而是多次 API 调用之间由 harness 维持连续性。

```python
while not state.done:
    context = build_context(state)
    action = llm.call(context, tools=tool_schemas)

    if action.type == "tool_call":
        result = tool_executor.run(action.tool_name, action.arguments)
        state.add_tool_observation(result)
        continue

    if action.type == "draft_final":
        review = review_gate.check(state, action.answer)
        decision = stop_controller.decide(state, action, review)

        if decision.type == "FINAL":
            return action.answer

        state.add_review_feedback(review)
        continue

    if budget.exceeded() or state.no_progress_too_long():
        return build_best_effort_answer(state)
```

## 3. 推荐动作枚举

模型每轮输出不应是自由文本，而应解析为中心引擎可处理的动作：

```ts
type EngineAction =
  | { type: "continue_solve"; reason: string; target?: string }
  | { type: "tool_call"; tool_name: string; arguments: unknown; reason: string }
  | { type: "draft_final"; answer: string; confidence: number }
  | { type: "request_review"; target: string }
  | { type: "report_blocker"; blocker: Blocker }
```

中心引擎的控制决策建议使用更少、更硬的状态：

```ts
type ControllerDecision =
  | { type: "CONTINUE_SOLVE"; reason: string }
  | { type: "CALL_TOOL"; tool_name: string; arguments: unknown }
  | { type: "REVIEW"; reason: string }
  | { type: "REVISE"; blockers: Blocker[] }
  | { type: "FINAL"; reason: string }
  | { type: "BEST_EFFORT"; reason: string }
  | { type: "FAIL"; blockers: Blocker[] }
```

## 4. Shared Context 最小字段

harness 每轮重新组装上下文，不应把全部聊天历史无脑塞回模型。推荐维护结构化状态：

```ts
type SharedContext = {
  task: TaskSpec
  open_subgoals: Subgoal[]
  claims: ClaimRecord[]
  tool_trace: ToolObservation[]
  review_notes: ReviewNote[]
  blockers: Blocker[]
  selected_route_id?: string
  final_candidate?: FinalDraft
  budget: BudgetState
  progress: ProgressState
}
```

关键规则：

- `verified` 只能由 Verifier / DomainVerifier / ReviewGate 写入。
- `final_candidate` 只是候选答案，不能直接交给用户。
- 工具调用结果必须写入 `tool_trace`，并标注来源、时间、输入、输出、置信度和局限。
- 被驳回路线、失败工具结果、重复错误也要记录，避免模型反复走同一个坑。

## 5. 工具结果的语义

工具结果必须作为带边界的证据处理。

例如：

```ts
type ToolObservation = {
  tool_name: string
  input: unknown
  output: unknown
  result_type: "search" | "symbolic_check" | "numeric_check" | "test" | "proof_check" | "file_edit" | "other"
  confidence?: number
  supports: ClaimId[]
  limitations: string[]
  error?: string
}
```

示例限制：

- 符号计算能验证代数展开，但不一定处理定义域。
- 数值测试能发现反例，但不能证明恒成立。
- 搜索结果能提供外部证据，但需要来源可靠性判断。
- 单元测试通过只能说明覆盖用例通过，不能证明程序完全正确。

因此 ReviewGate 不能只检查“有没有工具结果”，还必须检查“工具结果能证明什么、不能证明什么”。

## 6. 终止批准权

OpenO1 的硬原则：

```text
Solver can request final.
Harness decides final.
```

即：Solver / Worker / MainAgent 可以提交 `draft_final`，但不能直接输出给用户。中心引擎必须把候选答案送入 ReviewGate 和 StopController。

允许 FINAL 的典型条件：

- 原始任务目标已经明确覆盖。
- `open_subgoals` 为空，或剩余项被标记为非必要并说明原因。
- 无未解决的 fatal / major blocker。
- 关键 claim 已验证，或者明确说明无法验证的边界。
- DomainVerifier 没有阻断项。
- ReviewGate 返回 pass。
- 继续推理的边际收益不足以消耗更多预算。

必须继续或修复的典型条件：

- 任务目标没有完全回答。
- 仍有未验证关键 claim。
- 工具结果与推导冲突。
- 出现定义域、边界条件、漏解、增根、变量不一致等高危问题。
- Reviewer 给出 fatal / major issue。
- 预算仍允许，且继续有明确修复方向。

允许 BEST_EFFORT 的典型条件：

- 预算耗尽。
- 多轮无进展。
- 所有路线都有不可修复阻断项。
- 外部工具不可用，但可以给出清晰的已验证/未验证边界。

BEST_EFFORT 必须明确说明：已完成部分、未完成部分、阻断原因、可信边界和下一步建议。

## 7. Review Severity

ReviewGate / Critic 输出的问题必须分级，避免无限打磨：

```ts
type ReviewSeverity = "fatal" | "major" | "minor" | "style"
```

处理建议：

- `fatal`：禁止 FINAL，必须修复或失败。
- `major`：通常禁止 FINAL，除非预算耗尽并进入 BEST_EFFORT。
- `minor`：可以按任务重要性决定是否继续。
- `style`：不应阻断 FINAL。

## 8. 数学推理默认门槛

数学场景下，结束条件应更硬：

- 变量定义一致。
- 关键代数步骤经过符号验证或人工可审查推导。
- 最终答案已代回原条件或形成逻辑闭环。
- 检查定义域、边界值、特殊值。
- 检查是否漏根、增根、除以零、偷换条件。
- 证明类题目不能把数值验证当作完整证明。

## 9. 与 multi-agent-protocol 的关系

本文档补充 `docs/multi-agent-protocol.md`：

- `multi-agent-protocol.md` 规定 AgentTeam 的角色、路线、验证和 ReviewGate。
- 本文档规定中心引擎如何把“一次请求一次响应”的模型 API 组织成多轮工具推理循环。
- 任何 AgentTeam 输出都必须落入本文档的 harness 控制循环，不能绕过 Shared Context、ToolTrace、ReviewGate 或 StopController。

## 10. 一句话原则

OpenO1 不是让模型在单次调用里变成 heavy model，而是用 harness 把普通模型组织进一个可审阅、可验证、可修复、可终止的推理外骨骼。

```text
reason -> tool -> observe -> revise -> review -> final
```
