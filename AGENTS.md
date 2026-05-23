# AGENTS.md - OpenO1 规则与规范

## 0. 继承关系
- 基础规则继承全局文件：`C:\Users\ASUS\.codex\AGENTS.md`
- 冲突时以本文件（OpenO1 项目专属规则）为准。

## 1. 项目愿景与目标
- **终极目标**：构建模型无关的通用推理增强 Agent，通过流程（AgentTeam、共享上下文、自动推理检查、Review Gate）及部分自动化程序，实现类似 heavy model 的推理过程。
- **短期目标**：先以数学推理作为验证场景，基于本地开源模型，通过微调和工作流提升 AIME、MATH、GSM8K 表现。
- **底线红线**：不承诺虚高能力；不用关闭校验、跳过审阅、吞掉失败来制造表面成功；一切进展必须基于可复现的实验/benchmark，严禁主观感受代指能力。

## 2. 架构规范 (中心引擎与模块)
中心引擎是唯一种标与任务编排者，负责调度子模块并管理 `Shared Context`。
- **子模块约束**：不能直接改写任务目标、共享结论或最终答案，只能向中心引擎提交结构化中间结论。
- **多 Agent 调度细则**：见 `docs/multi-agent-protocol.md`。该文档定义通信协议、升级条件、并发调度、路线评分、修复循环、Review Gate 与停止条件。
- **核心模块职责**：
  1. **Task Intake**：解析任务目标、已知条件、目标结论、格式与约束。
  2. **Reasoning Planner**：拆解任务，制定候选推理路线与验证计划。
  3. **AgentTeam**：按分工协作。角色包括：Planner、Worker、Verifier、Supervisor、Critic、Solver、Synthesizer。
  4. **Shared Context**：共享事实层。结论格式须包含 `claim` (内容), `status` (待验证/已验证/被推翻/需要复查), `source` (来源), `evidence` (依据), `risk` (风险)。
  5. **Domain Verifier**：按任务领域检查推理链。第一阶段实现数学推理验证；后续扩展到代码、研究、规划等领域。
  6. **Review Gate**：质量门禁。确认目标已达、无未处理跳步、数学检查无阻断、格式正确才允许输出。失败时必须退回继续推理或报告根本原因。
  7. **Benchmark / Eval**：记录模型、配置及 AIME/MATH/GSM8K 表现，对比工作流前后差异。

## 3. 协作与质量协议
- **工作流顺序**：中心引擎 Intake -> MainAgent 单 Agent 初判 -> Verifier 首验 -> 必要时升级 AgentTeam -> Domain Verifier -> Review Gate。
- **数学质量要求**：
  - 变量定义一致，无逻辑/代数跳步，必须检查定义域、边界值与特殊值。
  - 严禁：将“看起来合理”视作证明、隐瞒关键推导错误、使用 benchmark 外的散点样例宣称整体能力。

## 4. 本仓库额外实施规则
- **Git 同步**：每次修改项目文件后，**必须**将变更 commit 并推送 (push) 到 GitHub。
- **异常处理**：若非 Git 仓库、无 remote、缺少凭据或推送失败，必须在回复中明确说明阻断原因。

## 5. 当前阶段默认假设
- 本文件是当前顶层项目规范；多 Agent 细则见 `docs/multi-agent-protocol.md`。当前暂不创建中心引擎运行时代码。
- 短期目标以 AIME、MATH、GSM8K 作为核心验收指标。
- 所有“逼近 gpto1”的描述只能作为实验假设或目标，不可作为已达成事实。

## 6. 框架规范
主体引擎的功能为：
1. 接收任务目标、已知条件、目标结论、格式与约束。
2. 将目标任务发送给 MainAgent，并引导 MainAgent 分析任务类型、难度、是否需要工具辅助、是否需要推理、是否需要验证、是否需要启动 AgentTeam。
3. 默认单 Agent 起步；若初判复杂度高或首次验证失败，则升级为多 Agent。
4. 复杂任务由 Planner 生成 2-4 条候选路线，Worker 并发独立尝试，Verifier 逐步评分，Supervisor 选择候选路线，Critic 找漏洞，Solver 修复，Verifier 再验，通过后由 Synthesizer 输出。
5. Agent 超过预算、修复无进展或 Review Gate 未放行时必须停止并报告阻断原因。
