# 可验证委托协议与 subagent 可信交付

- 日期：2026-07-09
- 类型：架构讨论 / 决策记录
- 状态：草案

## 背景

OpenO1 的目标不是只做数学推理特化，而是从一开始设计成完整的通用推理框架。当前架构设想包含主 agent、subagent、共享上下文、自动检查数学推导、Review Gate 与继续推理判断。

本次讨论聚焦一个核心问题：主 agent 派发任务给 subagent 后，如何判断 subagent 所说的“完成了”是否可信。

## 核心问题

最简单的二级结构是：主 agent 派一个 subagent 去执行子任务，subagent 完成后返回结果。此时主 agent 面临两难：

1. 如果直接相信 subagent，主 agent 就是在赌博，因为它没有独立信息源验证 subagent 的产出。
2. 如果不相信 subagent，主 agent 必须完整阅读子任务产出，甚至重新检查代码、文档或推导，这会抵消 subagent 隔离中间过程、保持主上下文干净的优势。

因此，问题不应设计成“主 agent 是否相信 subagent”，而应设计成：

> subagent 交付的结果，能不能被低成本验证、抽查、复现、回滚、继续加工？

## 讨论结论

subagent 的价值不是替主 agent 思考，而是替主 agent 产生可验证的中间资产。

主 agent 不应该依赖 subagent 的自然语言报告来建立信任。自然语言报告只能作为导航，可信依据应来自 artifact、测试结果、引用位置、符号检查、diff、日志摘要和可复现脚本。

OpenO1 需要的不是“更聪明地相信 subagent”，而是一套：

> 可验证委托协议（verifiable delegation protocol）

也可以称为：

> 任务交付-验证-合并协议

它要回答三个问题：

1. subagent 干了什么？
2. 结果为什么可信？
3. 主 agent 要不要继续投入预算？

## 核心设计原则

### 1. 上下文里放索引，不放全文

主 agent 不应该吞掉 subagent 的完整日志和完整中间过程。完整材料应存入 artifact store，主上下文只保留索引、摘要、风险点和验证结果。

### 2. 主 agent 看摘要，validator 看规则

主 agent 负责调度、裁决和预算分配；validator 负责按规则检查结果是否满足验收标准。

主 agent 的主要动作应收敛为：

```text
accept / reject / ask_revision / escalate / run_deeper_check
```

### 3. subagent 交付结构化结果，而不是一句“完成了”

subagent 的结果必须包含任务目标、验收标准对应关系、关键断言、证据引用、风险点、验证结果和未解决问题。

### 4. 共享任务空间，但不共享全部 token

OpenO1 不应设计成所有 agent 共享一个巨大上下文。更合理的结构是：所有 agent 共享同一个任务空间，但只按需读取与当前决策相关的最小上下文。

### 5. reviewer 不能只是主观打分

reviewer 不应只评价“回答好不好”。它应使用 checklist 审查：是否回答原问题、是否漏约束、是否有未经验证断言、是否把猜测说成事实、数学步骤是否有不可逆操作、代码是否真的运行、搜索结论是否有来源支持。

## 建议协议结构

### WorkUnit

```text
WorkUnit:
  id
  parent_id
  objective
  acceptance_criteria
  context_refs
  output_schema
  budget
  risk_level
```

### ResultPackage

```text
ResultPackage:
  workunit_id
  answer
  artifact_refs
  claim_graph
  evidence_map
  check_results
  unresolved_questions
  confidence_by_claim
```

### ReviewReport

```text
ReviewReport:
  passed
  failed_items
  suspicious_items
  required_revisions
  recommended_next_agent
```

## 分层架构

### 第一层：执行层

subagent 负责实际工作，例如解题、搜索、写代码、推导、生成文档。

其输出必须是结构化交付包，而不是自然语言完成声明。

### 第二层：验证层

validator 不负责重做完整任务，而是检查结果是否满足验收条件。

不同任务类型对应不同 validator：

- 数学任务：检查公式变形、边界条件、数值代入、特殊值、维度一致性、平方增根、除以零、必要条件与充分条件混淆。
- 代码任务：运行测试、lint、类型检查、最小复现。
- 搜索任务：检查引用、来源可信度、结论是否过度外推、冲突来源是否处理。
- 文档任务：检查格式、目录、结构、约束覆盖、输出规范。

### 第三层：调度与裁决层

主 agent 负责读取验证摘要和高风险片段，决定接受、返工、升级或继续检查。

只有在 reviewer 与 subagent 发生冲突、验证结果不稳定、或者任务风险等级较高时，主 agent 才拉取完整 trace。

## 数学任务示例

subagent 不应该只交付：

```text
已经证明完成。
```

而应交付：

```text
结论：x = ...

关键等式：
1. ...
2. ...
3. ...

每一步变形类型：
- 展开
- 移项
- 因式分解
- 代入
- 两边同除非零项

需要验证的风险点：
- 第 4 步除以 a-b，要求 a ≠ b
- 第 7 步平方，可能引入增根
- 最后结果需要代回原方程
```

validator 可以针对这些风险点进行规则化检查，而不必完全复现 subagent 的全部思考过程。

## 信任分级

建议对 subagent 交付结果设置分级：

```text
Level 0: 纯自然语言，不能直接采纳
Level 1: 有结构化摘要，但无证据
Level 2: 有证据引用，可人工抽查
Level 3: 有自动验证结果
Level 4: 可复现、可回放、可测试
Level 5: 形式化验证或强约束验证
```

主 agent 只允许自动合并 Level 3 以上的结果。Level 0 和 Level 1 只能当草稿，不能当事实。

## 对 OpenO1 的架构意义

“人月不可换”在 agent 系统里同样成立。agent 数量越多，主 agent 需要判断的产出总量越大，主 agent 的判断带宽会成为瓶颈。

真正能扩展的不是 agent 数量，而是可验证接口。

没有接口，十个 subagent 只是十个不可信的自然语言输出源；有接口，十个 subagent 才是十个可审计的工作单元。

因此，OpenO1 的核心抽象可以进一步收敛为：

```text
Task = 目标 + 验收标准
Agent = 生成候选 artifact
Validator = 检查 artifact
Reviewer = 判断是否需要继续
Orchestrator = 分配预算和合并结果
Memory = 存储可复用经验，不污染当前上下文
```

## 后续行动

1. 在 OpenO1 中定义 `WorkUnit`、`ResultPackage`、`ReviewReport` 的最小 schema。
2. 先针对数学推理任务实现一个最小 validator。
3. 让每个 subagent 输出验收标准对应表：`pass / fail / partial`。
4. 将完整 trace 与 artifact 放入外部存储，主上下文只保留索引和摘要。
5. 在 Review Gate 中加入信任等级判断，低于 Level 3 的结果不得自动合并。
6. 后续再扩展到代码、搜索、文档和投资分析等任务类型。
