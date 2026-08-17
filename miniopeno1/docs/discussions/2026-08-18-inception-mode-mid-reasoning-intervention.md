# Inception Mode：推理中途的状态条件干预

> 日期：2026-08-18  
> 状态：MiniOpenO1 核心候选机制 / 高优先级研究方向  
> 来源：用户提供的社交媒体截图，内容转述 llama.cpp 作者 Georgi Gerganov（@ggerganov）关于 “Inception Mode” 的思路；同时参考 llama.cpp 当前公开的 reasoning-budget 实现，以确认“推理过程中强制注入消息 / 强制结束 reasoning”的底层机制已经可以在采样器层实现。

## 核心想法

传统 Prompt Engineering 主要控制模型“开始思考之前看到了什么”。

Inception Mode 更值得关注的地方，是它把干预点移动到了模型**已经开始推理以后**：当模型沿着某条思路运行了一段时间，却出现迟迟不行动、重复空想、没有补充证据、没有调用工具等状态时，Harness 可以直接在推理流中插入一个新的“念头”，让模型把它当作自己当前思路的一部分继续生成。

截图中的典型例子是：

> 我是不是想太久了？先去收集更多任务信息。

这类插入不是单纯限制 reasoning budget。它更像一种**运行时元认知干预（runtime metacognitive intervention）**：Harness 根据模型当前状态判断“它现在最需要想起什么”，再把一个很短的 steering thought 注入当前推理轨迹。

---

## 为什么这对 MiniOpenO1 特别重要

MiniOpenO1 的目标，是使用简化版 Harness 配合后训练，让现有小模型获得更强的：

- 工具调用能力；
- 自主性；
- 发散性思维；
- 世界知识联系能力；
- 在开放任务中主动补信息、验证和推进任务的能力。

小模型的一个典型问题，是它们未必“不知道工具存在”，而是经常在已经拥有工具的情况下继续语言内推理：

- 想很久却不搜索；
- 明明缺信息却继续猜；
- 已经陷入局部思路，却不会主动换方向；
- 知道应该调用工具，但行动触发不稳定；
- reasoning budget 被消耗在低价值循环里。

因此，Inception Mode 可以成为 MiniOpenO1 中连接 **Harness Engineering** 与 **Post-training** 的关键桥梁：先让 Harness 在运行时替模型补上缺失的元认知触发，再把这些成功干预产生的轨迹反过来用于训练，让模型逐渐学会自己产生这些念头。

可以把它理解为：

**Harness 先充当模型的“外置元认知系统”，再把有效行为蒸馏回模型。**

---

## 与 reasoning budget 的关系

llama.cpp 当前公开的 reasoning-budget 机制已经提供了几个重要原语：

1. 在 reasoning block 内计数 token；
2. budget 耗尽后进入 forcing 状态；
3. 可以强制生成一段预设 token（`forced_tokens`）；
4. 可以在 forced message 后结束 reasoning；
5. 支持运行时手动把 sampler 从 COUNTING 切换到 FORCING。

相关实现：

- https://github.com/ggml-org/llama.cpp/blob/master/common/reasoning-budget.h
- https://github.com/ggml-org/llama.cpp/blob/master/common/reasoning-budget.cpp
- https://github.com/ggml-org/llama.cpp/blob/master/common/common.h

这说明底层的“生成到一半时改变模型接下来看到的 token 序列”并不需要重新发起一次完整请求。

但 MiniOpenO1 应该把这个机制进一步泛化：

**Reasoning Budget 解决“什么时候让模型停止想”；Inception Mode 解决“模型想到一半时，下一秒最好想起什么”。**

因此不要把 Inception Mode 实现成单纯的 token 上限功能。

---

## MiniOpenO1 中建议抽象成一等原语

建议新增一个类似 `Reasoning Intervention` / `Thought Injection` 的 Harness 原语。

它至少包含四个部分：

### 1. State Observer

持续观察模型运行状态，但不需要理解完整隐式思维，只需要提取可操作信号，例如：

- 已消耗 reasoning token；
- 距离上一次 tool call 的 token 数；
- 是否连续多轮没有新增外部信息；
- 是否出现语义重复；
- 是否反复提出相同假设；
- 是否长时间停留在 plan 而没有 action；
- 是否存在高不确定性但没有搜索；
- 是否已经拥有可用工具却一直不调用；
- 是否出现明显局部最优 / 单一路径锁死。

### 2. Intervention Policy

根据状态选择要注入的“念头”。

第一版不要追求复杂，可以从有限的 intervention bank 开始：

- `SEARCH_TRIGGER`：我是不是缺少外部信息？先搜索。
- `TOOL_TRIGGER`：有没有工具可以直接验证，而不是继续推测？
- `STOP_LOOP`：我是不是在重复同一条思路？
- `DIVERGENCE_TRIGGER`：先生成几条完全不同的解释路径。
- `CHECK_ASSUMPTION`：当前结论依赖了哪些未经验证的假设？
- `REPLAN`：当前路线没有进展，重新规划下一步。
- `MEMORY_RECALL`：是否有已有知识、历史任务状态或上下文可以调用？
- `EXECUTION_TRIGGER`：计划已经足够，开始执行下一步。

后续可以让一个很小的 policy model / classifier 根据 trace 选择 intervention 类型。

### 3. Injection Engine

把 intervention 插入当前生成轨迹。

需要注意：

- 尽量在句子、换行、reasoning segment 等安全边界注入；
- 注入内容应非常短，避免抢占模型本身的推理；
- 注入后继续原生成，不强制立刻结束；
- 不同模型需要适配其 reasoning 格式和 chat template；
- 注入内容应与模型自身的语言风格兼容，避免明显的“外部命令感”。

### 4. Outcome Evaluator

每次 intervention 都必须记录结果，否则它最终会退化成新的 Prompt Engineering 猜谜游戏。

至少记录：

- intervention 前状态；
- 注入类型和文本；
- 注入位置；
- 注入后多少 token 内发生 tool call / search / replan；
- 是否获得新的外部证据；
- 是否结束重复循环；
- 任务最终质量；
- token / latency / cost 变化。

这样才能回答一个真正重要的问题：

> 哪一种“中途念头”，在什么状态下，对什么模型最有效？

---

## 最重要的训练闭环

MiniOpenO1 不应长期依赖 Harness 替模型“打断思路”。更有价值的路线是把 Inception Mode 变成数据生成器。

建议形成以下闭环：

1. 小模型自然运行；
2. State Observer 检测低效状态；
3. Harness 注入 intervention；
4. 如果 intervention 让模型产生更好的下一步行为，则保存该 trace；
5. 把“需要外部提醒才会做出的正确行为”转成后训练数据；
6. 训练后重新测试模型是否能在没有 injection 时自主产生相同的元认知转折；
7. 只有仍然失败的状态继续由 Harness 托底。

这非常符合 MiniOpenO1 的定位：

**Harness 不是最终能力本身，而是训练小模型自主性的脚手架。**

长期理想状态是：随着训练推进，同一类 intervention 的触发率不断下降，因为原先需要 Harness 提醒的行为已经被模型内化。

---

## 与普通 System Prompt 的本质区别

如果把“遇到不确定信息就搜索”“不要空想太久”全部写进 system prompt，会出现两个问题：

1. 这些规则从第一 token 起就一直占据上下文；
2. 模型在真正陷入局部状态时，早期规则的行为约束可能已经变弱。

Inception Mode 的价值在于**状态条件 + 时间位置**。

同一句话：

> 先检查是否缺少外部信息。

放在 system prompt 里，只是长期规则；放在模型已经连续推理 1000 token、仍未调用搜索工具的那个瞬间，它就变成了一次针对当前失败状态的控制动作。

因此 MiniOpenO1 研究重点应该从“哪句话最有效”进一步转向：

**什么状态 + 什么时机 + 什么 intervention + 什么模型 = 更好的下一步行动。**

---

## 风险与约束

这个机制也很容易被用坏。

### 过度干预

如果频繁注入，模型可能：

- 失去长链深思能力；
- 过早调用工具；
- 形成机械化行为；
- 发散刚开始就被打断；
- 被 Harness 的先验限制在固定策略中。

因此建议至少加入：

- cooldown；
- 单次任务最大 intervention 次数；
- 最小 reasoning 长度；
- intervention confidence threshold；
- 同类 intervention 去重；
- 对高质量持续推理设置保护区间。

### 干预内容本身可能错误

Harness 不能假设自己的元判断永远正确。

因此注入文本最好采用“触发检查”而不是“强制结论”。例如优先：

> 我是不是缺少证据？先检查一下。

而不是：

> 当前结论一定错了，立刻搜索。

前者仍然把最终判断权交给模型。

---

## 第一版 MVP

MiniOpenO1 第一版不需要复杂的 learned controller。

可以先实现三个 deterministic trigger：

1. **Long-think-no-tool**：reasoning 超过阈值且没有 tool call -> 注入 `SEARCH_TRIGGER / TOOL_TRIGGER`；
2. **Semantic-loop**：检测到高重复推理 -> 注入 `STOP_LOOP / REPLAN`；
3. **Plan-without-action**：已经输出明确计划但迟迟不执行 -> 注入 `EXECUTION_TRIGGER`。

然后只做一件事：记录干预前后行为差异。

如果这三个简单 trigger 都能明显提高小模型的工具使用率、任务完成率或降低无效 reasoning token，Inception Mode 就值得继续扩展成完整的 learned intervention policy。

---

## 当前结论

把这一方向列为 MiniOpenO1 的高价值核心研究点。

它和 MiniOpenO1 的后训练目标高度契合，因为它同时提供：

- 一个低成本 Harness 能力增强手段；
- 一个可以观察模型失败状态的实验接口；
- 一个自动生成“正确元认知转折”训练数据的方法；
- 一个衡量自主性是否真正被模型内化的指标。

后续重点不是只复刻 llama.cpp 的 reasoning budget，而是研究一个更一般的问题：

> **能否通过对生成中途状态的识别与最小干预，让小模型逐步学会在正确的时间自己产生正确的下一步念头？**
