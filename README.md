# OpenO1 Repository Index

OpenO1 是一个通用推理受控状态机项目。当前仓库处于规范先行与最小中心引擎骨架并行落地阶段，重点是先固化可审阅、可验证、可迭代的多 Agent 推理工作流，再逐步扩展运行时代码。

## 当前状态

- 当前顶层项目规范入口：`AGENTS.md`
- 当前多 Agent 调度细则：`docs/multi-agent-protocol.md`
- 当前 harness 工具循环与终止控制设计：`docs/harness-control-loop.md`
- 当前上下文生命周期设计：`docs/context-lifecycle.md`
- 当前外部项目学习记录：`docs/external-project-lessons.md`
- 当前中心引擎骨架：`engine.py`
- 当前中心引擎冒烟测试：`tests/test_engine.py`
- 当前尚未创建完整运行时代码模块。
- 当前短期验证场景聚焦数学推理。

## 核心目标

终极目标：
- 构建模型无关的通用推理增强 agent。
- 让任意接入 OpenO1 的模型，在推理任务中尽可能呈现类似 GPT Pro 或 Gemini Deep Think 的 heavy model 行为。

短期目标：
- 从数学推理开始验证通用推理状态机。
- 以本地可部署开源模型为基础。
- 通过轻量微调和固定化推理工作流，使数学 benchmark 表现逐步逼近 `gpto1` 风格能力。

## 规范索引

| 文件 | 作用 |
| --- | --- |
| `AGENTS.md` | OpenO1 项目专属 agent 规则、中心引擎规范、模块协作协议和数学任务质量门禁 |
| `docs/multi-agent-protocol.md` | 多 Agent 通信、升级、并发调度、路线评分、修复循环、Review Gate 与停止条件 |
| `docs/harness-control-loop.md` | 记录 harness 如何把一次请求一次响应的模型 API 组织成多轮工具推理、状态回填、审阅和终止控制循环 |
| `docs/context-lifecycle.md` | 长任务上下文更新、外部记忆、压缩、Context Pack、Context Reset、恢复与缓存成本策略 |
| `docs/external-project-lessons.md` | 记录从外部项目、论文和框架中学到的可迁移设计与不应照搬之处 |
| `README.md` | 仓库索引与当前状态导航 |

## 代码索引

| 文件 | 作用 |
| --- | --- |
| `engine.py` | 最小中心引擎骨架，包含 TaskAnalyzer、PolicyEngine、Runtime、VerifierGate、TraceLogger 与 `OpenO1Engine.run()` 编排流程 |
| `tests/test_engine.py` | 中心引擎冒烟测试，覆盖单 Agent 路径、复杂任务升级、缺 runtime 失败与 ReviewGate 基础拦截 |

## 架构模块索引

当前架构由 `AGENTS.md` 中的中心引擎规范驱动：

- `Task Intake`：解析题目、目标、约束、输出格式和成功标准。
- `Reasoning Planner`：拆解任务并选择候选推理路线。
- `AgentTeam`：生成候选路线、反例、替代路径、验证结果和审阅意见。
- `Shared Context`：记录任务目标、路线、步骤、证据、假设、风险和结论状态。
- `Domain Verifier`：按任务领域接入专用验证器；第一阶段实现数学推理验证。
- `Review Gate`：判断是否高质量完成、是否允许输出、是否需要继续推理。
- `Harness Control Loop`：把模型输出的工具调用意图、工具结果、候选答案、审阅结果和预算状态组织成可继续、可回滚、可终止的引擎循环。
- `Benchmark / Eval`：围绕 AIME、MATH、GSM8K 等可复现题集记录表现。

## 评测原则

- benchmark 结论必须基于可复现实验记录。
- 不允许用少量手工样例替代正式 benchmark 结论。
- 所有“逼近 gpto1”相关描述都必须表达为目标或实验假设，不能表达为已达成事实。

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
