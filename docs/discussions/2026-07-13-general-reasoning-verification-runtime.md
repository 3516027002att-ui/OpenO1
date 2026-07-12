# 通用推理的任务契约、验证计划与双重门禁

- 日期：2026-07-13
- 类型：架构讨论 / 实现方案 / 决策记录
- 状态：草案

## 背景

OpenO1 的验证能力不能长期依赖一段通用 reviewer prompt。对于通用推理，诸如“有没有回答原问题”“有没有遗漏约束”“断言是否有证据”“代码是否实际运行”等问题，需要被编译成结构化、可执行、可追踪的验证任务。

本次讨论的核心目标是把自然语言任务转换为任务契约，再把验证要求转换为 `CheckSpec`，由确定性检查器、语义 Evaluator 和领域工具共同执行。

## 核心结论

OpenO1 的通用推理闭环应为：

```text
UserRequest
→ TaskContract
→ WorkUnit / ResultPackage
→ VerificationPlan
→ Universal Checks
→ Domain Checks
→ EvidenceGate
→ DraftSynthesizer
→ OutputAuditor
→ OutputGate
→ Final Answer
```

关键思想：

1. 用户请求先被编译为明确的目标、成功标准和约束。
2. Agent 的结果必须声明覆盖了哪些标准，并为最终断言绑定证据。
3. 不同验证问题由不同执行器处理，无法确认时必须返回 `UNKNOWN`。
4. 推理结果通过一次证据门禁后，最终文字还要通过输出门禁。
5. Review Gate 依据结构化验证报告做确定性裁决，不依赖平均分掩盖高危失败。

## 任务契约

建议引入：

```python
@dataclass(slots=True)
class Criterion:
    id: str
    description: str
    required: bool = True
    severity: str = "high"


@dataclass(slots=True)
class Constraint:
    id: str
    description: str
    severity: str = "high"


@dataclass(slots=True)
class TaskContract:
    goal: str
    criteria: list[Criterion]
    constraints: list[Constraint]
    capabilities: set[str]
```

Agent 交付结果必须包含：

```python
criterion_coverage = {
    "C1": ["claim-1", "claim-2"],
    "C2": ["artifact-code-1"],
}

constraint_satisfaction = {
    "K1": "pass",
    "K2": "partial",
}
```

这使得“有没有回答问题”和“有没有遗漏约束”具备可检查对象。

## 断言、证据与认知状态

建议定义受控认知状态：

```python
class EpistemicStatus(str, Enum):
    VERIFIED = "verified"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"
    UNKNOWN = "unknown"
```

并将断言、证据、标准覆盖统一装入 `ResultPackage`：

```python
@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    kind: str
    origin: str
    artifact_id: str | None = None
    locator: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ClaimRecord:
    claim_id: str
    text: str
    epistemic_status: EpistemicStatus
    evidence_ids: list[str]
    criterion_ids: list[str]
    assumptions: list[str]
    is_final: bool = False


@dataclass(slots=True)
class ResultPackage:
    claims: list[ClaimRecord]
    evidence: list[EvidenceRecord]
    criterion_coverage: dict[str, list[str]]
    constraint_satisfaction: dict[str, str]
    artifact_ids: list[str]
```

模型可以报告置信度，但不能自行把断言升级为 `VERIFIED`。可信验证状态只能由验证器或受控工具写入。

## 验证问题如何落地

| 问题 | 主要数据 | 执行方式 |
| --- | --- | --- |
| 是否回答原问题 | `Criterion`、覆盖映射 | 结构检查 + 语义检查 |
| 是否遗漏约束 | `Constraint`、满足状态 | 逐条硬门槛 |
| 是否有无证据断言 | Claim-Evidence 图 | 确定性图检查 + 语义支持检查 |
| 是否把猜测写成事实 | `epistemic_status` | 受控渲染 + 输出审计 |
| 数学步骤是否合法 | 结构化 MathStep | SymPy、数值检查、Lean 或数学 Evaluator |
| 代码是否实际运行 | ExecutionReceipt | 受控 runtime 生成凭证 |
| 搜索结论是否有来源 | Claim-Source 映射 | 引用覆盖、来源质量和语义蕴含检查 |

## VerificationPlan

基础检查应适用于所有任务：

```text
- goal_coverage
- constraint_coverage
- claim_support
- epistemic_calibration
- internal_consistency
```

领域检查根据任务能力动态追加：

```text
math            → math_validity
code_execution  → execution_receipt
web_research    → source_grounding
document        → document_structure_check
```

建议结构：

```python
@dataclass(slots=True)
class CheckSpec:
    check_id: str
    executor: str
    severity: str
    required: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CheckResult:
    check_id: str
    status: str  # pass / fail / unknown / skipped
    severity: str
    findings: list[str]
    evidence_ids: list[str]
    repair_actions: list[str]
```

## 代码运行凭证

Agent 的自然语言声明“测试已通过”不能作为可信证据。必须由引擎控制的 runtime 生成：

```python
EvidenceRecord(
    evidence_id="exec-001",
    kind="execution_receipt",
    origin="engine_tool",
    artifact_id="stdout-001",
    metadata={
        "command": "pytest -q",
        "exit_code": 0,
        "duration_seconds": 2.41,
        "working_directory": "/workspace/OpenO1",
        "commit_sha": "...",
        "stdout_artifact_id": "stdout-001",
        "stderr_artifact_id": "stderr-001",
    },
)
```

`origin="engine_tool"` 必须由中心引擎写入，Agent 无权伪造。

## 双重门禁

### EvidenceGate

检查：

- 必要标准是否被覆盖；
- 必要约束是否满足；
- 最终断言是否有可信证据；
- 领域验证是否通过；
- 是否存在未解决高危 blocker；
- 高风险必需检查是否为 `UNKNOWN`。

### OutputGate

检查：

- 最终回答是否真正对准原任务；
- 是否遗漏输出格式与用户约束；
- 是否新增未在 ResultPackage 中出现的断言；
- 是否抹去了假设、范围和不确定性；
- 是否与已经放行的证据和结论一致。

约束关系：

```text
final_claims ⊆ verified_or_explicitly_qualified_claims
```

## Review Gate 裁决规则

高危 `FAIL` 和高危 `UNKNOWN` 都不得自动放行：

```python
if high_risk_failures:
    return "repair"

if required_high_risk_unknowns:
    return "repair"

if missing_required_criteria:
    return "fail"

return "pass"
```

评分可以帮助路线排序，但不能抵消硬失败。

## 对当前 engine.py 的最小修改

建议先增加：

```python
@dataclass(slots=True)
class SharedState:
    ...
    task_contract: TaskContract | None = None
    result_package: ResultPackage | None = None
    verification_plan: list[CheckSpec] = field(default_factory=list)
    verification_report: VerificationReport | None = None
    final_draft: str | None = None
```

新增动作：

```text
COMPILE_TASK_CONTRACT
BUILD_VERIFICATION_PLAN
RUN_UNIVERSAL_CHECKS
RUN_DOMAIN_CHECKS
SYNTHESIZE_DRAFT
AUDIT_FINAL_OUTPUT
```

第一阶段可先创建：

```text
verification.py
tests/test_verification.py
```

## 首批测试

1. 必要 criterion 未覆盖，必须进入 `repair`。
2. 最终 claim 无可信 evidence，必须进入 `repair`。
3. Agent 自称测试通过但缺少 runtime receipt，必须进入 `repair`。
4. 高危检查返回 `UNKNOWN`，不得自动通过。
5. Synthesizer 添加未在 ResultPackage 中出现的新断言，输出门禁必须拦截。
6. 低风险可选检查失败时允许带限制条件输出，不应伪装为完全验证。

## 风险与边界

- 结构化字段完整不代表语义真实，仍需语义支持检查。
- 语义 Evaluator 也会误判，因此高风险结论应尽量引入独立证据或确定性工具。
- schema 过于复杂会压垮小模型，早期只实现最小字段集。
- `UNKNOWN` 不能被当成 `PASS`，但也不能一律当作不可修复失败。

## 后续行动

1. 从 `TaskContract`、`ClaimRecord`、`EvidenceRecord`、`CheckSpec` 四个最小结构开始。
2. 实现目标覆盖、约束覆盖、证据存在性和执行凭证四类确定性检查。
3. 将当前 `StrictVerifierGate` 升级为消费 `VerificationReport` 的硬门禁。
4. 后续再接入数学、代码、搜索和文档领域验证器。
