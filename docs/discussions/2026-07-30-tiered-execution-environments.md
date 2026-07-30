# 分级能力授权与执行环境

- 日期：2026-07-30
- 类型：架构讨论 / 实现方案 / 决策记录
- 状态：已采纳
- 关联记录：`2026-07-13-tool-capability-architecture.md`

## 背景

传统 Coding Agent 往往为每个 Agent 或用户绑定完整 Linux VM / 容器。该方案通用性高，但会同时扩大常驻成本、启动延迟、凭据暴露面、文件系统权限和基础设施复杂度。许多研究、搜索、资料读取、数据库查询、轻量计算和工具组合任务并不需要完整操作系统。

camelAI 在 2026-07-28 发布的工程文章中展示了另一种实现：Agent loop 常驻 Cloudflare Durable Object，项目文件存放在 SQLite 与 R2，常见操作通过显式方法和 V8 isolate 执行；构建应用、运行 Notebook 等确实依赖 Linux 的任务，临时启动 Cloudflare Sandbox 容器，完成后关闭。

来源：

- https://camelai.com/blog/our-coding-agent-runs-in-a-cloudflare-durable-object-not-a-vm
- https://github.com/qaml-ai/camelAI

该案例验证了一个重要方向：Agent 可以长期持有任务状态和能力接口，无需长期占有一台机器。Linux 继续作为按需执行资源存在。

## 核心决策

OpenO1 采用“能力优先、执行环境逐级升级”的架构。

模型只声明当前步骤需要的能力、操作、输入和约束。中心运行时通过 Capability Broker 与 Execution Broker 决定具体 provider、执行层级、权限、预算、挂载和生命周期。

默认不给主 Agent 或 Subagent 分配完整 Linux 环境。只有当前能力无法在较轻层级完成，并且升级理由通过策略检查后，系统才申请更重的执行环境。

```text
Model / Agent
     ↓ capability request
Context Broker / Tool Broker
     ↓ resolved capability
Capability Broker
     ↓ provider candidates
Execution Broker
     ↓ policy + cost + risk + runtime requirements
Tier 0 Tool/API
Tier 1 Isolate
Tier 2 Ephemeral Container
Tier 3 Persistent Environment
```

现有 Context Broker / Tool Broker 后续扩展为以下职责组合：

- Context Broker：检索并注入当前步骤需要的上下文、Skill、记忆、项目资料和 Tool Card。
- Tool Broker：按需加载少量工具 schema，避免把全量 MCP、Tool 与 Skill 塞进上下文。
- Capability Broker：将抽象能力请求映射到可替换 provider。
- Execution Broker：选择执行环境，控制权限、挂载、凭据、预算、生命周期和执行回执。

## 执行环境分级

### Tier 0：直接 Tool / MCP / API

适用任务：

- 搜索与网页读取；
- GitHub、数据库、邮件、日历等结构化连接器操作；
- 文件读取、知识检索和已有 artifact 访问；
- 远程符号计算、验证器和领域 API；
- 不需要运行任意代码的确定性操作。

特征：

- 默认层级；
- 无通用 shell；
- 仅暴露明确 schema；
- 凭据由 Broker 保存并代为认证；
- 最低启动成本和最小权限面。

### Tier 1：轻量 Isolate

适用任务：

- JavaScript / Python 轻量计算；
- 数据清洗、转换与聚合；
- 多个 Tool/API 的受控组合；
- 小规模脚本、规则检查和格式转换；
- 无需安装系统依赖的代码执行。

特征：

- 毫秒级或低延迟启动；
- 短生命周期；
- 默认禁止任意网络、系统调用和宿主文件访问；
- 只挂载当前步骤所需 artifact；
- 通过显式方法访问外部连接，凭据不进入沙箱。

### Tier 2：短生命周期容器

适用任务：

- 安装依赖；
- 编译、测试和运行项目；
- 启动临时服务；
- 浏览器自动化；
- 需要 Linux 工具链、包管理器或较高内存的任务；
- Notebook、数据库执行环境和复杂代码验证。

特征：

- 按任务启动，完成后销毁；
- 使用临时工作区或受控项目快照；
- 网络、挂载、CPU、内存和运行时间均由策略显式限制；
- 输出通过 artifact、diff、日志和 execution receipt 回传；
- 不因 Agent 空闲而继续占用计算资源。

### Tier 3：持久开发环境

适用任务：

- 超长编码任务；
- 大型仓库与多服务系统；
- 需要长期缓存、增量编译或复杂交互状态的工作；
- 多轮运行中频繁使用同一重型环境，并且重建成本明显过高的任务。

特征：

- 仅在 trace 证明有必要时启用；
- 绑定任务或项目，不绑定某个 Agent 身份；
- 有明确租期、休眠、快照、回收和预算策略；
- 权限仍受 Execution Broker 管理；
- 必须支持暂停、恢复、审计和最终回收。

## 升级与降级规则

执行环境采用“从轻到重、任务结束后回收”的策略：

```text
Tier 0 尝试
→ 能力缺口或验证失败
→ 形成结构化升级请求
→ Execution Broker 审批
→ Tier 1 / Tier 2 / Tier 3
→ 收集回执与 artifact
→ 关闭或降级环境
```

升级请求至少应包含：

```ts
type ExecutionRequest = {
  capability: string
  operation: string
  reason: string
  inputs: ArtifactRef[]
  required_runtime?: "api" | "isolate" | "linux_container" | "persistent"
  filesystem: {
    read: string[]
    write: string[]
  }
  network: {
    mode: "deny" | "allowlist" | "open_with_approval"
    allowlist?: string[]
  }
  secrets: string[]
  limits: {
    max_runtime_seconds: number
    max_cpu?: number
    max_memory_mb?: number
    max_output_mb?: number
  }
}
```

Execution Broker 可以：

- 批准请求；
- 使用更轻 provider 完成同一能力；
- 缩小网络、文件和凭据权限后批准；
- 要求人工确认；
- 拒绝请求并返回可恢复 blocker。

Agent 的偏好不能单独构成升级理由。缺少执行回执、需要编译、需要系统依赖、现有层级连续失败等可作为有效依据。

## Agent 与执行环境的关系

Agent、Subagent 和执行环境是两个独立维度。

- 启动 Subagent 不自动创建沙箱。
- 搜索、审阅、规划、反例检查和资料读取型 Subagent 通常停留在 Tier 0。
- 轻量计算型 Worker 可以申请 Tier 1。
- 编译、测试和项目运行型 Worker 按需申请 Tier 2。
- Tier 3 面向长期任务或项目工作区，由多个 Agent 在权限控制下轮流使用。
- 多个 Agent 可以读取同一逻辑 workspace；写入使用文件范围、分支、租约或合并门禁避免冲突。
- Agent 被取消、超时或替换后，其拥有的临时执行资源必须由中心运行时回收。

## 文件系统与 artifact 原则

OpenO1 不要求所有任务共享一个可变 POSIX 文件系统。任务状态应优先保存为可恢复的数据与 artifact：

- 原始输入；
- 工作文件；
- 代码快照；
- patch / diff；
- 测试日志；
- 执行回执；
- 证据与验证结果；
- 失败路线和 blocker。

Tier 1、Tier 2 和 Tier 3 只获得当前任务所需的受控视图。环境销毁前，必须把需要保留的变化同步回 artifact store 或版本库。

第一阶段无需照搬 Durable Object、SQLite 与 R2。它们属于 camelAI 的具体基础设施选择。OpenO1 先定义稳定的 Workspace / Artifact / Execution 接口，底层可以使用本地文件、对象存储、Git、数据库或其他 provider。

## 权限与安全约束

- 凭据默认留在 Broker 或连接器侧，不直接写入模型生成的代码和文件。
- 网络默认关闭；确需联网时使用域名或服务 allowlist。
- 文件挂载遵循最小范围和最小权限。
- 高风险操作需要策略批准或人工确认。
- 每次执行记录输入、环境层级、provider、权限、资源消耗、输出、退出状态和日志摘要。
- 工具调用成功只证明动作执行，不证明结论正确；关键结果仍需 Verifier / Review Gate 检查。
- Capability API 本身是新的安全边界，需要审计方法权限、参数校验、数据外泄和 prompt injection 风险。

## 与工具能力架构的衔接

`ToolManifest` 后续增加执行相关元数据：

```python
@dataclass(slots=True)
class ExecutionProfile:
    minimum_tier: int = 0
    preferred_tier: int = 0
    requires_linux: bool = False
    requires_network: bool = False
    supports_ephemeral: bool = True
    supports_persistent: bool = False
    credential_mode: str = "brokered"
    filesystem_scope: str = "artifact_only"
```

Capability Provider 继续向中心引擎暴露统一能力协议。provider 内部可以调用远程 API、isolate、短生命周期容器或持久环境，模型无需绑定具体基础设施。

工具检索和执行环境选择应分开评估：

```text
需要什么能力？
→ 哪个 provider 能完成？
→ 该 provider 最低需要什么执行环境？
→ 当前风险和预算是否允许？
```

## 实现顺序

第一阶段优先实现可工作的两端：

1. Tier 0：现有 Tool / MCP / API 与 Capability Registry。
2. Tier 2：本地或远程短生命周期容器，支持代码执行、依赖安装、测试和日志回传。
3. 定义 ExecutionRequest、ExecutionPlan、ExecutionReceipt 和 artifact 同步协议。
4. 在 trace 中记录层级选择、升级原因、运行时间、成本和结果。

第二阶段加入 Tier 1 isolate，承接大量无需完整 Linux 的轻量代码执行。

第三阶段根据真实 trace 决定是否实现 Tier 3 持久环境，以及哪些任务值得承担其复杂度。持久环境不能成为默认路径。

## 评测指标

应长期统计：

- 各执行层级的调用比例；
- Tier 0 / Tier 1 直接完成率；
- 升级率与无效升级率；
- 升级后的修复成功率；
- 启动延迟、运行时间和总成本；
- 每类任务所需的最低可靠层级；
- 权限拒绝与人工确认次数；
- 环境泄漏、未回收和 artifact 丢失率；
- 相同任务在完整 Linux 与分级执行方案下的成功率差异。

## 风险与边界

- 显式能力集合过窄时，Agent 会遇到无法自救的能力缺口，因此必须保留 `report_capability_gap` 与逐级升级机制。
- 过度封装可能降低通用性；能力目录应根据真实失败 trace 扩展，避免凭空预建大量方法。
- 小模型可能在受控能力集合中表现更稳定，但这一点需要 OpenO1 自己评测。
- camelAI 报告的数量级成本下降缺少统一基准，不能直接作为 OpenO1 的成本预测。
- Linux 仍是重要后备执行环境；本决策针对长期绑定完整环境造成的浪费和权限扩张。
- OpenO1 不依赖 Cloudflare。Durable Object、R2、Code Mode 与 Sandbox SDK 只作为外部实现案例。

## 已采纳原则

1. 默认不给任何 Agent 或 Subagent 分配完整 Linux 沙箱。
2. 模型声明能力需求，Broker 决定工具、provider 和执行环境。
3. 优先使用明确 Tool/API，其次使用轻量 isolate，再使用短生命周期容器。
4. 持久环境只服务于有证据支持的长期复杂任务。
5. 凭据、网络、文件挂载、预算和生命周期由中心运行时控制。
6. 重型环境完成任务后立即回收，需保留的状态同步为 artifact 或版本记录。
7. 执行成功必须生成可审计回执，关键结论继续经过验证门禁。
