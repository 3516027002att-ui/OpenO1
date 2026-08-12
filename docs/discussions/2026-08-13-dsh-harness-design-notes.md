# DSH 启发的 Harness 架构设计方向

> 日期：2026-08-13  
> 状态：设计讨论 / 候选架构方向  
> 来源：对《DeepSeek Harness（DSH）深度技术架构与生态反推报告》的分析。该报告本身包含逆向推断，因此以下内容记录的是值得 OpenO1 吸收的设计思想，不将其中对 DSH 内部实现的推断视为已证实事实。

## 背景

DSH 的公开/残留架构信息里，有几项设计对 OpenO1 很有参考价值：

1. Host / Client 双 Surface；
2. Prompt 插件化；
3. Agent 运行状态直接成为 UI 的一部分；
4. 在模块边界广泛采用 fail-fast invariant；
5. 使用类似 Cordis 的插件 Runtime，而不只是一层简单插件 API。

这些方向可以与 OpenO1 已有的动态工具、上下文、长期任务状态和自主 Agent 运行时结合。

---

## 1. Host / Client 双 Surface

插件或能力不应只暴露后端工具接口。可以把同一项能力拆成两个明确 Surface：

### Host Surface

负责模型和运行时侧能力，例如：

- Tool 注册与调用；
- System Prompt / Context 注入；
- 文件、网络、代码执行等运行时资源；
- 生命周期管理；
- 权限、策略与 capability gating；
- telemetry / tracing hook；
- 与 Agent Loop、Task State、Context Broker 的交互。

### Client Surface

负责用户可见与交互侧能力，例如：

- 工具调用展示；
- Agent 当前状态；
- 任务树、分支、subagent 状态；
- 运行日志和证据；
- 结构化结果组件；
- 插件自定义 UI；
- 用户中途干预、批准、取消或修改任务。

### 对 OpenO1 的意义

能力可以成为一个贯穿模型、运行时和 UI 的一等对象，而不只是 `tool schema + handler`。

理想的 Capability 单元可以包含：

- model interface；
- runtime implementation；
- prompt/context fragments；
- policy / permission；
- lifecycle；
- telemetry；
- UI representation。

这样 Tool Broker / Capability Broker 加载一项能力时，可以一次性装载其完整行为，而不需要在 tools、prompt、frontend、logging 等位置分别维护同一功能。

---

## 2. Prompt 插件化

避免长期维护一个不断膨胀的全局 system prompt。

Prompt 应被拆成可注册、可排序、可启停、可追踪来源的片段，例如：

- core runtime prompt；
- capability-specific prompt；
- tool usage instruction；
- safety / permission instruction；
- task-specific context；
- skill instruction；
- project instruction。

每个 capability / plugin 可以随自身生命周期注册对应 prompt fragment：

- 插件加载 -> 对应工具与 prompt 同时出现；
- 插件卸载 -> 工具与 prompt 同时移除；
- 能力未加载 -> 不占用上下文；
- Prompt section 保留明确来源和优先级，便于冲突诊断。

### 与现有 OpenO1 思路的结合

Capability Broker 不只返回 tool schema，还可以返回一个完整 capability package：

`tool schema + runtime + prompt fragment + policy + UI + telemetry hook`

这样动态工具加载和动态上下文加载可以统一到同一套能力模型中。

---

## 3. Agent 运行状态成为 UI 的一部分

长期自主 Agent 不能只在后台运行，然后最终吐出一个结果。其运行状态本身应成为产品界面的核心对象。

建议 UI 原生展示至少以下信息：

- 当前 Goal；
- 当前 Phase / Step；
- 正在调用的 Tool；
- 当前活跃分支；
- subagent / worker 状态；
- 已完成与未决任务；
- Context 使用量；
- Input / Output token；
- Cache hit；
- Tool / model latency；
- 当前预算和累计成本；
- 重试次数与最近错误；
- 最近一次产生实质进展的时间；
- 最近新增的证据、结论或状态变化；
- 是否正在等待用户、工具、外部资源或其他 agent。

### 目标

让用户能够区分：

- 模型仍在有效推进；
- 正在等待工具；
- 正在重复无效循环；
- 进入错误恢复；
- Context / budget 接近限制；
- 任务已经实质停滞。

Agent 自主性越高，observability 越应该是一等功能。OpenO1 的长时间任务、分支、回溯和计算分配尤其需要这一层。

---

## 4. Fail-fast invariant

在 Agent Runtime 中，应尽量在模块边界立即发现非法状态，而不是让错误状态被后续步骤继续传播。

建议为关键模块建立统一 invariant / assertion 机制，覆盖：

- Tool schema 与调用参数；
- capability 注册；
- Context / Prompt section；
- Task / Branch / Step 状态转换；
- parent-child agent 关系；
- permission 与资源边界；
- checkpoint / restore；
- plugin lifecycle；
- execution environment；
- tool result 格式；
- telemetry event；
- budget accounting。

### 原则

错误应尽可能在最靠近根因的位置暴露。

不要依赖大量隐式 fallback 把非法状态继续带入 Agent Loop。长链条 Agent 中，一个被悄悄吞掉的小错误可能在几十步之后演变为难以定位的“幽灵状态”。

Fail-fast 与显式错误恢复应同时存在：

- invariant 负责尽早暴露不变量破坏；
- recovery policy 决定该错误能否重试、回滚、降级、切换工具或请求用户干预。

---

## 5. Cordis 式插件 Runtime

OpenO1 未来如果插件和 capability 数量增多，仅有 `register_tool()` 级别的插件 API 很可能不够。

更合适的方向是设计或采用一个真正的插件 Runtime，处理：

- plugin context isolation；
- caller / ownership tracking；
- scoped event bus；
- dependency graph；
- lifecycle；
- hot reload；
- cleanup / disposal；
- async task ownership；
- state consistency；
- telemetry attribution；
- error boundary；
- capability dependency；
- Host / Client 两侧对应关系。

### 为什么重要

长期运行的 Agent 会遇到普通插件框架很少处理的问题：

- 一个异步工具返回时插件已经卸载或升级；
- 某个事件到底属于哪个插件 / agent / task；
- 热加载后旧 Context 是否仍可继续执行；
- 谁创建了一个后台任务，谁负责清理；
- 同一 capability 被多个 agent 并发使用时如何隔离状态；
- 出现泄漏、死循环或异常时如何定位 owner。

因此未来 OpenO1 的 Plugin / Capability 系统应优先考虑“运行时语义”，不要只定义插件接口。

---

## 6. 可以形成的统一抽象

上述五点最终可以收敛成一个更完整的 Capability Runtime：

```text
Capability
├── Host Surface
│   ├── Tools
│   ├── Prompt / Context
│   ├── Runtime services
│   ├── Policy / Permission
│   └── Lifecycle
├── Client Surface
│   ├── UI components
│   ├── State view
│   └── User interventions
├── Observability
│   ├── Trace
│   ├── Metrics
│   └── Ownership / Caller
└── Invariants
    ├── Boundary validation
    └── Recovery policy
```

这可以作为 Tool Broker、Context Broker、Execution Broker、Skill 系统和前端 UI 之间更高一级的统一抽象。

---

## 7. 当前结论

这五项设计均值得在 OpenO1 后续架构中优先保留：

- **Host / Client 双 Surface**：把模型能力、运行时实现和 UI 表现统一起来；
- **Prompt 插件化**：让上下文随 capability 动态组合，并保持来源可追踪；
- **Agent 状态 UI 化**：把长期自主 Agent 的 observability 做成产品能力；
- **Fail-fast invariant**：尽早阻断非法状态传播，配合显式恢复策略；
- **Cordis 式插件 Runtime**：为生命周期、隔离、caller tracking、热加载和长期异步任务提供基础设施。

当前将其记录为架构候选方向。等 OpenO1 进入新的 Runtime / Plugin / UI 重构阶段时，应重新审视并决定哪些部分升级为正式架构约束。