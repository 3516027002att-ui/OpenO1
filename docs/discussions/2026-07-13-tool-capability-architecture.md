# 工具能力架构：避免工具臃肿并允许误判恢复

- 日期：2026-07-13
- 类型：架构讨论 / 实现方案 / 决策记录
- 状态：草案

## 背景

OpenO1 希望利用工具调用弥补基础模型在计算、搜索、代码执行、文档处理和形式化验证上的不足。工具数量增加后，系统容易出现 schema 膨胀、工具混淆、依赖膨胀、权限面扩大和路由误判。

本次讨论的目标是让 OpenO1 支持大量工具，同时保持 Agent 当前上下文和核心框架足够轻。

## 核心结论

需要区分三件事：

1. 工具是否安装在运行环境中；
2. 工具是否登记在系统注册表中；
3. 工具完整 schema 是否暴露给当前模型。

真正使 Agent 臃肿的主要是第三项。全局可以安装和注册大量工具，但当前 Agent 只应看到少量基础元工具和当前步骤需要的具体工具。

推荐架构：

```text
Global Tool Repository
        ↓
Capability Catalog
        ↓
Tool Retrieval / Policy
        ↓
Scoped Tool View
        ↓
Current Agent Session
```

## 核心框架只理解能力

中心引擎不应直接依赖 SymPy、pytest、Lean、浏览器或 PDF 工具。上层只请求稳定能力：

```text
math.symbolic_equivalence
math.numerical_validation
code.execution
code.test
research.search
research.source_verify
document.table_extraction
```

具体 provider 可以替换：

```text
math.symbolic_equivalence
├── SymPyProvider
├── SageMathProvider
├── MathematicaProvider
└── RemoteCASProvider
```

这构成 OpenO1 工具系统的“细腰层”。

## Capability Provider 协议

```python
@dataclass(slots=True)
class CapabilityRequest:
    capability: str
    operation: str
    payload: dict[str, Any]
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CapabilityResult:
    status: str
    output: Any = None
    artifacts: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityProvider(Protocol):
    name: str
    capabilities: set[str]

    def can_handle(self, request: CapabilityRequest) -> bool: ...
    def execute(self, request: CapabilityRequest) -> CapabilityResult: ...
```

中心引擎调用能力，不绑定具体工具名：

```python
registry.execute(
    CapabilityRequest(
        capability="code.test",
        operation="run_test_suite",
        payload={"path": "tests/"},
    )
)
```

## 三层工具视图

### 1. 全局工具仓库

保存所有安装的 provider 和 manifest。模型默认看不到完整 schema。

### 2. 能力目录

模型常驻看到的只是很短的分类地图：

```text
research：搜索、网页读取、来源验证
code：代码读取、修改、执行、测试
math：符号计算、数值验证、形式化证明
documents：PDF、Word、表格和幻灯片
repository：Git、Issue、PR、Commit
data：SQL、分析和可视化
```

### 3. 当前任务工具集

中心引擎根据当前 WorkUnit 临时暴露一到数个具体工具的完整 schema。步骤结束后可以收回。

## 常驻元工具

建议控制在 4 到 6 个：

```text
search_capabilities
inspect_tool
request_capability
report_capability_gap
read_artifact
write_artifact
```

含义：

- `search_capabilities`：按目标查询候选能力和工具；
- `inspect_tool`：准备调用时读取某个候选工具的完整 schema；
- `request_capability`：只声明所需能力，由引擎选 provider；
- `report_capability_gap`：无法命名能力时描述尚未解决的目标；
- `read_artifact` / `write_artifact`：访问共享任务空间。

Agent 因此不需要预先记住所有工具。

## ToolManifest 与懒加载

```python
@dataclass(slots=True)
class ToolManifest:
    tool_id: str
    capability: str
    summary: str
    tags: set[str] = field(default_factory=set)
    trust_level: int = 1
    cost_level: int = 1
    latency_level: int = 1
    deterministic: bool = False
    requires_network: bool = False
    requires_sandbox: bool = False
    schema_loader: str = ""
    provider_entrypoint: str = ""
```

启动时只加载 manifest。只有在工具被选择后才动态导入 provider：

```python
provider = registry.load_provider(tool_id)
```

由此降低 Python 启动时间、内存、依赖冲突和插件故障传播。

## 工具发现流程

工具检索不应让模型在数百个工具中裸选：

```text
规则 / 标签 / BM25 / Embedding 召回候选
→ 权限、成本、可信度过滤
→ LLM 或策略层在少量候选中重排
→ 暴露 1 到 3 个完整 schema
```

建议先按一级领域和二级能力收窄，再检索 provider。

## 动态工具视图的误判问题

最危险的是漏选：任务实际需要搜索、执行或验证工具，初始 router 没有开放，Agent 可能在错误能力边界内生成完整但不可信的答案。

因此动态工具视图必须可恢复，不能一次分类后永久封锁其余能力。

推荐闭环：

```text
初始能力判断
→ 窄工具视图
→ Agent 执行
→ Verifier 检测能力缺口
→ REQUEST_CAPABILITY
→ 扩展工具视图
→ 继续执行
```

## 能力缺口 blocker

建议标准化：

```text
missing_current_source
missing_execution_receipt
missing_symbolic_verification
missing_document_access
missing_image_understanding
missing_formal_proof
```

Verifier 发现这类 blocker 时，不应只要求原 Agent“再想想”，而应转换为能力请求。

## 路由状态与扩展策略

```python
class RoutingStatus(str, Enum):
    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"
    INSUFFICIENT_CONTEXT = "insufficient_context"
```

处理规则：

```text
CONFIDENT            → 暴露少量高相关工具
UNCERTAIN            → 扩大候选范围并允许能力申请
INSUFFICIENT_CONTEXT → 先读取上下文、检查 artifact 或请求用户信息
```

工具升级采用“先窄后宽”：

```text
低成本直接检查
→ 补充候选能力
→ 独立 verifier 推荐工具
→ 高成本或形式化工具
```

## 工具层级

```text
Tier 0：核心内置
- schema 校验
- artifact 管理
- 哈希和基础规则

Tier 1：轻量默认插件
- Python runtime
- pytest
- 基础搜索
- 基础文件读取

Tier 2：领域插件
- SymPy
- 静态分析
- SQL
- PDF 结构分析

Tier 3：高成本或实验插件
- Lean
- 浏览器自动化
- 专业仿真
- 重型多模态处理
```

第一版不应追求工具数量，优先跑通 capability protocol 和验证闭环。

## 工具选择策略

Provider 选择考虑：

```text
最低可信等级
最大成本
最大延迟
是否离线
是否需要沙箱
是否允许 fallback
```

低风险任务可以使用廉价检查；高风险任务逐步升级到独立验证或形式化工具。

## 路由评测指标

```python
@dataclass(slots=True)
class RoutingTrace:
    predicted_capabilities: list[str]
    later_requested_capabilities: list[str]
    verifier_required_capabilities: list[str]
    unused_exposed_capabilities: list[str]
    task_outcome: str
```

应统计：

- 漏选率；
- 多选率；
- 因路由导致的失败率；
- 扩展能力后的修复成功率；
- 每个能力带来的真实正确率增益；
- 工具调用延迟和 token 成本。

## 新增工具的门槛

每增加一个工具都应回答：

1. 它解决了现有能力不能解决的什么问题？
2. 它在哪类任务上带来可测量增益？
3. 它增加多少依赖、延迟、权限和维护成本？
4. 是否已有 provider 可以通过新 operation 覆盖，而无需新增工具概念？

## 第一阶段建议

```text
Core
├── schema_checker
├── claim_evidence_checker
├── constraint_checker
├── execution_receipt_checker
├── capability_registry
└── review_gate

Plugins
├── python_runtime
├── pytest_provider
└── sympy_provider
```

Lean 和复杂浏览器自动化先保留接口，不立即实现。

## 风险与边界

- 工具目录本身也可能膨胀，因此 capability taxonomy 要保持稳定。
- Provider 返回结果必须转成统一 artifact、evidence 和 receipt，不能各自为政。
- 动态暴露降低上下文压力，但会增加一次路由和恢复成本。
- Agent 对能力的申请仍可能有误，最终权限和挂载必须由中心引擎裁决。

## 后续行动

1. 定义 `ToolManifest`、`CapabilityRequest`、`CapabilityResult` 和 `CapabilityProvider`。
2. 实现内存版 `CapabilityRegistry` 和按需 provider loader。
3. 常驻只暴露元工具，不暴露全量 provider schema。
4. 将 verifier blocker 接入能力缺口检测与重新路由。
5. 用真实任务 trace 评估漏选率、多选率和工具增益。
