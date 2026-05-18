# OpenO1 Repository Index

OpenO1 是一个推理特化 agent 项目。当前仓库处于规范先行阶段，重点是先固化可审阅、可验证、可迭代的推理工作流，再逐步落地中心引擎代码。

## 当前状态

- 当前唯一项目规范入口：`AGENTS.md`
- 当前尚未创建中心引擎代码。
- 当前尚未创建模块文件。
- 当前短期目标聚焦数学推理。

## 核心目标

终极目标：
- 构建模型无关的推理增强 agent。
- 让任意接入 OpenO1 的模型，在推理任务中尽可能呈现类似 GPT Pro 或 Gemini Deep Think 的 heavy model 行为。

短期目标：
- 从数学推理开始。
- 以本地可部署开源模型为基础。
- 通过轻量微调和固定化推理工作流，使数学 benchmark 表现逐步逼近 `gpto1` 风格能力。

## 规范索引

| 文件 | 作用 |
| --- | --- |
| `AGENTS.md` | OpenO1 项目专属 agent 规则、中心引擎规范、模块协作协议和数学任务质量门禁 |
| `README.md` | 仓库索引与当前状态导航 |

## 架构模块索引

当前架构由 `AGENTS.md` 中的中心引擎规范驱动：

- `Task Intake`：解析题目、目标、约束、输出格式和成功标准。
- `Reasoning Planner`：拆解数学问题并选择候选推导路线。
- `AgentTeam`：生成候选解法、反例、替代路径和审阅意见。
- `Shared Context`：记录题目条件、符号定义、推导状态和结论状态。
- `Math Derivation Checker`：检查代数、逻辑、定义域、边界条件和计算一致性。
- `Review Gate`：判断是否高质量完成、是否允许输出、是否需要继续推理。
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
