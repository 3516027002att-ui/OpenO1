# Heraclitus Runtime Gates：用运行时纪律替代 Prompt 层“劝模型自主”

> 日期：2026-08-14  
> 状态：设计决策 / OpenO1 核心方向

## 背景：UltraCode 实验暴露的问题

在 DeepSeek Harness（DSH）中尝试构造极端激进的 UltraCode 配置：

- 明确要求尽早、并行、递归地委派 subagent；
- subagent 可继续派生 subagent；
- 使用 continuable background delegation；
- 将 subagent 深度限制提高到近似无限；
- 放大并行度、workflow 与迭代预算；
- 通过 persona 反复强调 decomposition、parallel delegation、independent verification。

但实测中，部分模型即使接受这种极强提示，实际调用 subagent 的积极性仍明显偏低，甚至低于默认设置下的 Opus。

这说明一个关键事实：

**“允许模型调用 subagent”与“强烈提示模型调用 subagent”都不能保证模型真正形成积极委派行为。**

Subagent 调用倾向在相当程度上取决于模型本身的 agentic policy prior。Prompt 可以影响倾向，但不能作为 OpenO1 的核心可靠性机制。

## 设计结论

OpenO1 不应把复杂任务的组织能力寄托在一句或一组类似以下的提示上：

- delegate aggressively；
- always decompose first；
- use subagents whenever possible；
- parallelize independent work；
- verify with another agent。

这些可以作为软引导，但不能作为最终控制面。

核心原则改为：

> **模型负责理解问题；Heraclitus 负责迫使这种理解形成组织化执行。**

即：模型拥有 epistemic autonomy，Heraclitus 拥有 organizational authority。

## 两层职责分离

### 模型：Epistemic Autonomy

模型主要负责回答：

- 当前问题到底是什么；
- 有哪些目标与子目标；
- 有哪些未知量；
- 有哪些竞争假设；
- 缺什么证据；
- 哪些结果可以区分不同解释；
- 哪些任务彼此独立；
- 哪些任务存在前置依赖；
- 当前结论的主要不确定性在哪里。

模型可以自由改变自己的问题表示和解释框架。

### Heraclitus：Organizational Authority

Heraclitus 负责根据问题结构决定：

- 是否必须拆分任务；
- 是否必须产生独立认知线程；
- 是否 fan-out 为多个 subagent；
- 哪些任务并行、串行或互相审查；
- 是否增加 adversarial / critic / verifier；
- 是否切换工具、Skill、模型、执行环境或 reasoning mode；
- 是否取消、合并、重排或重新分配已有任务；
- 新证据出现后是否应重构当前 workflow；
- 当前是否允许进入 final。

因此某些关键状态转换不能只是模型可选调用的 Tool，而应成为 Runtime protocol。

## ProblemMap 作为强制入口

对于达到复杂度阈值的任务，OpenO1 不应允许第一轮模型直接回答。

复杂任务首先必须产生结构化 `ProblemMap`，至少包含：

- `objectives`
- `unknowns`
- `hypotheses`
- `evidence_needs`
- `dependencies`
- `independent_branches`
- `verification_needs`
- `risks / uncertainty`

这一阶段可以暂时不给模型 `final` action，必要时甚至不给普通执行工具，先强制形成问题结构。

## Branching Pressure

Heraclitus 可以根据 `ProblemMap` 估计当前任务的 `Branching Pressure`，例如：

- independent branches 数量；
- competing hypotheses 数量；
- 是否需要独立 verifier；
- 是否存在不同信息域 / 工具域；
- 是否存在高风险结论；
- 当前上下文是否过大；
- 单一路线错误的代价是否很高。

当 Branching Pressure 超过阈值时，Runtime 进入 `TEAM_FORMATION` / `FAN_OUT`，而不是等待模型自己“想起来”调用 subagent。

## Delegation 不应完全由模型自由决定

传统 harness：

```text
Model
  -> sees subagent tool
  -> decides whether to call it
```

OpenO1：

```text
Model
  -> produces ProblemMap
  -> Heraclitus detects independent / adversarial branches
  -> Runtime requires FAN_OUT
  -> model may design roles/tasks
  -> Heraclitus instantiates the team
```

模型可以影响“如何委派”，但不能因为自身 delegation prior 偏低而完全跳过应有的独立执行。

必要时，Team Design 也可以进一步弱化：模型只负责产生 Problem Graph，Heraclitus 直接从图结构形成并行拓扑。

## 四个核心 Runtime Gates

### 1. Decomposition Gate

目标：阻止复杂任务直接进入线性执行或 final。

要求：

- 显式形成问题结构；
- 标注目标、未知、假设、依赖与验证需求；
- 无法合理分解时需要给出理由。

### 2. Delegation / Organization Gate

目标：阻止模型因为内生调用倾向弱而一直单 Agent 闷头执行。

触发条件包括但不限于：

- 多个相互独立的工作分支；
- 多个竞争解释；
- 需要独立验证；
- 不同工具 / 环境 / 信息域；
- 高风险或高错误代价结论。

Heraclitus 可强制产生独立 cognition threads / subagents。

### 3. Reorganization Gate

目标：确保 workflow 会随问题状态变化。

每次重要 observation、subagent result、实验结果或新证据出现后，检查：

- 当前 Problem Graph 是否仍成立；
- 当前 Team 是否仍合理；
- 是否应新增 / 终止 / 合并 / 重派 agent；
- 当前工具和能力集合是否仍合适；
- 是否需要切换 reasoning / verification mode；
- 是否需要 backtrack、fork 或重新定义问题。

这对应 Heraclitus 的核心思想：

> **The workflow changes as the problem changes.**

工作流不是开局一次生成的固定 DAG，而是求解过程中持续演化的临时结构。

### 4. Termination Gate

目标：阻止模型因为“感觉差不多了”而提前结束。

模型不能直接决定任务完成，只能 `propose_final`。

Heraclitus / verifier 检查：

- 核心目标是否覆盖；
- 高价值未知是否仍未解决；
- 是否只探索了单一解释；
- 竞争解释是否被比较；
- 关键结论是否有证据；
- 是否存在未处理的矛盾证据；
- 高风险判断是否经过独立验证；
- 新发现是否已反馈到 Problem Graph。

未通过则重新进入执行或重组阶段。

## 自适应干预强度

Heraclitus 不应固定地对所有模型施加同样强度的控制。

原则：

> **模型越自主，Harness 越让路；模型越保守，Harness 越强制。**

如果某个模型天然善于 decomposition、delegation、parallelism、verification，则 Heraclitus 可减少强制转换，只负责审查与边界控制。

如果某模型智力足够但 delegation prior 较弱，则 Heraclitus 应更积极地把问题结构转换成执行结构。

因此 OpenO1 的目标之一是部分补偿不同基础模型在 agentic autonomy 上的差异，而不是假设所有模型都会正确使用同一套工具。

## 与 DSH 的区别

DSH 已经提供了非常强的 subagent 基础设施：后台执行、continuable child、递归派生、并行工具调用、workflow 等。

但在 DSH 中，subagent 最终仍以“模型可选择调用的工具/能力”为主。

OpenO1 的进一步方向：

**把关键认知组织动作提升为 Runtime state transition。**

即：

- DSH：Agent 可以动态生成 / 调用 workflow；
- OpenO1 / Heraclitus：Problem State 改变时，Runtime 可以要求 workflow、Team、Capability Set 随之演化。

## 当前核心判断

UltraCode 的实验说明：

**Prompt-level autonomy 不够可靠。**

OpenO1 不应把核心竞争力押在“写出更强的自主性 prompt”上，而应通过 Runtime protocol 和 Gate，把复杂开放问题所需要的分解、组织、重组、验证、终止纪律外化为可执行机制。

最终目标不是机械地强制多 Agent，而是：

> **强迫模型持续证明当前的问题结构、认知组织和执行结构仍然合理，并在问题变化时重构它们。**
