# OpenO1 — Agentic Reasoning Runtime

OpenO1 是一个开放、模型无关的 **Agentic Reasoning Runtime**。

项目的核心目标是把模型不断增强的工具使用、长期行动、并行探索与环境反馈能力，转化为可持续推进、可验证、可回溯的推理能力。模型在单次调用中的表现，不等于它在一个长期运行系统中的最终能力；OpenO1 研究如何让开源模型用额外时间、行动和反馈扩大问题解决上限，持续压缩与最前沿推理系统之间的差距。

OpenO1 不绑定某个固定模型，也不把固定的 Solver–Critic–Judge、多 Agent 辩论或机械反思当作永久架构。具体策略应随基础模型能力变化而演化，已经被模型内化的流程应当简化或删除。

## 当前状态

- 当前顶层项目规范入口：`AGENTS.md`
- 当前多 Agent 调度细则：`docs/multi-agent-protocol.md`
- 当前 harness 工具循环与终止控制设计：`docs/harness-control-loop.md`
- 当前上下文生命周期设计：`docs/context-lifecycle.md`
- 当前外部项目学习记录：`docs/external-project-lessons.md`
- 当前讨论记录目录：`docs/discussions/`
- 当前中心引擎骨架：`engine.py`
- 当前中心引擎冒烟测试：`tests/test_engine.py`
- 当前尚未形成完整运行时代码模块。
- 当前短期验证场景聚焦数学推理。

## 核心命题

- **模型能力前沿会持续移动。** 过去需要前沿模型长时间思考的问题，会逐渐被开源模型快速解决；与此同时，人们会继续提出更困难的问题。
- **Agentic 能力也是推理资源。** 搜索、写代码、运行实验、调用工具、维护长期状态、并行探索和根据反馈修正路线，都可以成为外部化思考的一部分。
- **额外计算需要被组织。** 多调用、多 Agent 和更长上下文本身不会自动带来更强推理，关键在于如何分配时间、维护证据、管理分支、验证结论和停止无效探索。
- **Runtime 应随模型一起变强。** OpenO1 的价值应来自能力乘数效应，而不是长期修补某一代模型的弱点。

## 核心目标

长期目标：

- 构建模型无关的 Agentic Reasoning Runtime。
- 将时间、工具、并行路线、外部反馈和环境交互组织成长期推理过程。
- 维护动态的论证与研究状态，包括事实、假设、证据、反例、冲突、失败路线和未决问题。
- 在数学、代码、形式证明、科学计算和研究分析等适合外部验证的任务上，扩大开源模型的问题解决上限。
- 以可复现实验衡量 OpenO1 对模型能力的实际增益，不承诺普通模型必然等同最前沿模型。

短期目标：

- 从数学推理开始验证 Agentic Reasoning Runtime。
- 以本地可部署开源模型为主要实验对象。
- 建立可插拔的规划、路线探索、工具调用、验证、回溯、预算和终止机制。
- 对比模型直接回答与 OpenO1 长时运行后的准确率、成本、稳定性和可验证性。
- 逐步扩展到代码推理、形式证明、科学计算和开放研究任务。

## 设计原则

- **按需组织，不固定演戏。** Agent、工具、路线和审阅步骤只在预期有收益时启用。
- **独立探索优先于角色数量。** 多 Agent 的价值来自不同假设、证据来源和错误分布，不来自角色名称本身。
- **行动必须服务推理。** 搜索、代码执行、符号计算和文件操作应产生可引用的证据、反例或状态变化。
- **中心引擎拥有状态。** 模型提交结构化意图与候选结论，中心引擎负责执行、记录、预算、回滚和终止。
- **失败路线也是资产。** 被否定的假设、无效工具结果和重复错误必须进入研究状态，避免系统循环浪费计算。
- **允许删除旧机制。** 当基础模型已经内化某项流程时，OpenO1 应通过简化 harness 降低成本，而不是维护永久仪式。

## 规范索引

| 文件 | 作用 |
| --- | --- |
| `AGENTS.md` | OpenO1 项目专属 agent 规则、中心引擎规范、模块协作协议和数学任务质量门禁 |
| `docs/multi-agent-protocol.md` | 多 Agent 通信、升级、并发调度、路线评分、修复循环、Review Gate 与停止条件 |
| `docs/harness-control-loop.md` | 记录 harness 如何把一次请求一次响应的模型 API 组织成多轮工具推理、状态回填、审阅和终止控制循环 |
| `docs/context-lifecycle.md` | 长任务上下文更新、外部记忆、压缩、Context Pack、Context Reset、恢复与缓存成本策略 |
| `docs/external-project-lessons.md` | 记录从外部项目、论文和框架中学到的可迁移设计与不应照搬之处 |
| `docs/discussions/` | 保存项目推进过程中的重要讨论记录，用于架构决策回溯和后续实现参考 |
| `README.md` | 仓库定位、索引与当前状态导航 |

## 代码索引

| 文件 | 作用 |
| --- | --- |
| `engine.py` | 最小中心引擎骨架，包含 TaskAnalyzer、PolicyEngine、Runtime、VerifierGate、TraceLogger 与 `OpenO1Engine.run()` 编排流程 |
| `tests/test_engine.py` | 中心引擎冒烟测试，覆盖单 Agent 路径、复杂任务升级、缺 runtime 失败与 ReviewGate 基础拦截 |

## 架构模块索引

当前架构由 `AGENTS.md` 中的中心引擎规范驱动：

- `Task Intake`：解析问题、目标、约束、输出格式和成功标准。
- `Reasoning Planner`：构造研究计划、拆分未决问题并提出候选推理路线。
- `AgentTeam`：按需探索相互独立的假设、解法、反例和验证路径。
- `Shared Reasoning State`：记录事实、命题、证据、假设、冲突、失败路线、风险和结论状态。
- `Domain Verifier`：按任务领域接入专用验证器；第一阶段实现数学推理验证。
- `Review Gate`：判断关键结论是否得到支持、任务是否完成、是否需要继续探索。
- `Harness Control Loop`：组织模型动作、工具结果、路线分叉、回溯、预算分配和终止决策。
- `Benchmark / Eval`：围绕 AIME、MATH、GSM8K 等可复现题集记录运行时增益和计算成本。

## 评测原则

- benchmark 结论必须基于可复现实验记录。
- 不允许用少量手工样例替代正式 benchmark 结论。
- 必须保留模型直接回答的 baseline，分离基础模型能力与 runtime 增益。
- 必须同时记录准确率、token、时间、工具调用、失败率和运行配置。
- 所有“压缩与前沿模型差距”相关描述都必须表达为目标或实验假设，不能表达为已达成事实。

## 一句话愿景

> **Turn agentic capability into reasoning capability.**
>
> 把会行动的模型，组织成会长时间思考的系统。

## OpenContext 语义索引状态

截至当前记录，`oc index status` / `oc index build` 因 embedding API key 未配置而无法运行：

```text
Error: API key not configured. Set OPENAI_API_KEY or configure in ~/.opencontext/config.toml
```

配置好 `EMBEDDING_API_KEY` 或 `OPENAI_API_KEY` 后，可在仓库根目录重新执行：

```powershell
oc index build
oc index status
```
