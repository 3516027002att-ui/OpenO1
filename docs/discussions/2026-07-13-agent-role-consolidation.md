# Agent 分工收敛：职责、角色与运行实体的分离

- 日期：2026-07-13
- 类型：架构讨论 / 实现方案 / 决策记录
- 状态：草案

## 背景

OpenO1 当前协议中包含 Coordinator、MainAgent、Planner、Worker、Verifier、Supervisor、Critic、Solver、Synthesizer、ReviewGate 和 BudgetManager 等角色。这些职责大多确实存在，但如果每个职责都落成独立 Agent、独立 prompt、独立会话和独立代码类，系统会迅速出现组织结构膨胀。

本次讨论聚焦：如何保留完整职责，同时减少运行时角色数量、上下文交接、状态转移和维护成本。

## 核心结论

OpenO1 需要很多职责，但只需要少数稳定的 Agent Runtime。

必须区分：

```text
职责：系统必须完成什么工作
角色：一次调用采用什么工作立场
运行实体：真正占用模型调用、上下文和状态的 session
```

不能默认采用：

```text
一个职责 = 一个角色 = 一个独立 Agent = 一个独立类
```

建议收敛为：

```text
Orchestrator：确定性代码
Producer Runtime：产生或修改候选结果
Evaluator Runtime：判断、审查、比较并生成 blocker
Composer Runtime：按需合成最终输出
ReviewGate / Budget / 权限：确定性代码
```

## 分工过多的主要问题

### 交接损耗

每次 Agent 交接都要重新传递目标、约束、路线、artifact、blocker 和预算。多次摘要会产生约束丢失、语义漂移和修复对象定位错误。

### 协议 token 膨胀

大量预算消耗在 Agent 之间解释“我做了什么”，而非解决原始问题。

### 责任边界变复杂

Verifier、Critic 和 Supervisor 可能重复发现同一问题；Solver 修改后原计划可能失效；Synthesizer 遇到冲突又没有修复权限。

### 状态机边数爆炸

角色越多，成功、失败、部分完成、请求工具、请求升级、返工和预算耗尽之间的转移组合越多，难以测试和复现。

### 消融困难

同时引入多个角色后，很难判断 benchmark 增益来自独立审查、第二次采样、修复循环还是单纯增加计算量。

## 推荐运行时映射

| 逻辑职责 | 运行时实现 |
| --- | --- |
| Coordinator | Orchestrator 确定性代码 |
| MainAgent | Producer / `initial_attempt` |
| Planner | Producer / `plan` |
| Worker | Producer / `execute_step` 或 `explore_route` |
| Solver | Producer / `repair` |
| Verifier | Evaluator / `verify` |
| Critic | Evaluator / `adversarial_critique` |
| Supervisor | Evaluator / `compare_routes` 或确定性排序 |
| Synthesizer | Composer，可选 |
| ReviewGate | 确定性硬门禁 |
| BudgetManager | 确定性预算控制器 |

## Producer Runtime

Producer 的共同特征是创建或修改候选 artifact。

```python
class ProducerMode(str, Enum):
    INITIAL_ATTEMPT = "initial_attempt"
    PLAN = "plan"
    EXECUTE_STEP = "execute_step"
    EXPLORE_ROUTE = "explore_route"
    REPAIR = "repair"
```

Planner、Worker 和 Solver 可以共享 runtime、工具接入和结果协议，只通过 mode、目标和写入范围区分。

## Evaluator Runtime

Evaluator 读取 artifact，输出判断、评分、证据检查和 blocker，默认不能直接修改候选结果。

```python
class EvaluatorMode(str, Enum):
    VERIFY = "verify"
    ADVERSARIAL_CRITIQUE = "adversarial_critique"
    COMPARE_ROUTES = "compare_routes"
    CHECK_GOAL = "check_goal"
    CHECK_CONSTRAINTS = "check_constraints"
    AUDIT_OUTPUT = "audit_output"
```

`VERIFY` 和 `ADVERSARIAL_CRITIQUE` 在认知任务上保持区别：

- Verify：判断当前结果能否通过；
- Critique：主动寻找反例、边界遗漏和隐含假设。

它们可以共享代码 runtime，但使用不同 checklist、采样参数和 context pack。

确定性检查不应交给 LLM Evaluator，例如 schema 完整性、artifact 是否存在、退出码、预算和必要字段。

## Composer Runtime

Composer 只在以下情况按需启用：

- 多路线或多子任务需要合并；
- 最终结构复杂；
- 需要把技术 artifact 转成用户可读输出；
- 需要统一引用和认知状态表达。

简单任务可以直接使用 Producer 草稿，再交给 Output Auditor。

Composer 只能读取已放行 claim、evidence、assumption 和 limitation，输出后必须再次审计，防止新增推论或抹去不确定性。

## 确定性控制组件

### Orchestrator

负责唯一状态所有权、action 调度、模块权限、trace 和状态合并。LLM 可以提出下一步建议，但最终动作由 PolicyEngine 决定。

### ReviewGate

消费结构化 VerificationReport 并做硬裁决：

```text
高危 blocker      → repair / fail
必要检查 unknown  → repair
必要标准未覆盖    → fail
全部硬门槛通过    → pass
```

### BudgetController

负责最大步骤、Agent 数、验证轮次、修复轮次、token、时间和无进展停止。

### Tool Router

模型可以参与候选能力重排，但注册、权限、成本限制和最终挂载由代码控制。

## RoleSpec

```python
@dataclass(slots=True)
class RoleSpec:
    runtime_type: str
    mode: str
    objective: str
    read_scopes: set[str]
    write_scopes: set[str]
    allowed_capabilities: set[str]
    output_schema: str
    independent_context: bool = False
```

统一调用：

```python
result = agent_runtime.run(
    work_unit=work_unit,
    role_spec=role_spec,
    context_pack=context_pack,
)
```

## 新建 session 还是切换 mode

### 值得新建独立 session

- 需要独立上下文，避免继承原 Producer 的盲点；
- 权限边界不同；
- 需要并行探索；
- 需要不同模型或采样配置；
- 需要沙箱或故障隔离。

### 只需切换 mode

- 输入输出结构相同；
- 工具权限相同；
- 都在修改同一类 artifact；
- 不要求独立视角；
- 不需要并发；
- 失败处理逻辑相同。

通用规则：

```text
同一 artifact 的连续修改 → 复用 Producer session
需要独立判断            → 新建 Evaluator session
需要路线多样性          → 新建并行 Producer session
只改变工作目标          → 切换 mode
权限或隔离边界变化      → 新建 session
```

## 不同复杂度的执行流程

### 低复杂度

```text
Producer(initial_attempt)
→ Evaluator(verify)
→ ReviewGate
→ 输出
```

### 中等复杂度

```text
Producer(plan + execute)
→ Evaluator(verify)
→ Producer(repair)
→ Evaluator(verify)
→ ReviewGate
```

### 多路线

```text
多个 Producer(explore_route) 并发
→ Evaluator(verify each)
→ Evaluator(compare_routes)
→ Producer(repair selected route)
→ Evaluator(verify)
→ Composer
→ Output Auditor
→ ReviewGate
```

### 高风险

```text
Producer
→ Deterministic Checks
→ Evaluator(verify)
→ 独立 Evaluator(adversarial_critique)
→ Domain Tool
→ ReviewGate
```

## Supervisor 的处理

Supervisor 很容易成为只增加一次总结的虚职。路线选择优先由确定性规则完成：

```text
排除存在高危 blocker 的路线
→ 比较目标对齐、步骤有效性、证据质量和成本
```

只有路线之间存在难以量化的语义冲突时，才调用 Evaluator 的 `compare_routes` 模式。

## 对本地小模型的意义

本地小模型通常更难稳定执行复杂组织协议、长上下文角色边界和多层 JSON。过多角色会把一个难问题拆成多个彼此依赖的难问题。

更适合小模型的闭环：

```text
明确任务
→ 生成候选
→ 工具验证
→ 根据具体 blocker 修复
→ 再验证
```

OpenO1 应更像受控 harness，少做模拟公司式角色扮演。

## 角色与交接预算

```python
@dataclass(slots=True)
class AgentBudget:
    max_active_sessions: int = 3
    max_producers: int = 3
    max_evaluators: int = 2
    max_role_transitions: int = 6
    max_handoffs: int = 4
```

每次 handoff 要检查：

1. 是否带来新的独立信息；
2. 是否改变权限、工具或上下文；
3. 当前 runtime 切换 mode 是否已经足够。

没有新增独立信息的 handoff 应优先删除。

## 研究与评测要求

消融实验应分别比较：

```text
单次 Producer
+ 自检
+ 独立 Evaluator
+ 修复循环
+ 多路线 Producer
+ Critique 模式
+ Composer
```

同时记录准确率、token、延迟、交接次数、修复成功率和错误类型，避免把单纯增加计算量误认为架构收益。

## 后续行动

1. 保留现有逻辑角色表，但增加运行时映射。
2. 实现 `ProducerMode`、`EvaluatorMode` 和统一 `RoleSpec`。
3. 将 Coordinator、ReviewGate 和 BudgetManager 固化为普通代码服务。
4. 第一阶段只实现 Producer、Evaluator 两种常用 runtime，Composer 保持可选。
5. 为 trace 增加 `session_count`、`handoff_count` 和 `role_transition_count`。
