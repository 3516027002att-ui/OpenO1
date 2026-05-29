from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class ExecutionMode(str, Enum):
    SINGLE_AGENT = "single_agent"
    AGENT_TEAM = "agent_team"
    BLOCKED = "blocked"


class ExecutionStatus(str, Enum):
    PASS = "pass"
    REPAIR = "repair"
    FAIL = "fail"
    PARTIAL = "partial"


@dataclass(slots=True)
class UserRequest:
    goal: str
    known_conditions: list[str] = field(default_factory=list)
    target_conclusion: str | None = None
    output_format: str | None = None
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskProfile:
    request: UserRequest
    task_type: str = "general"
    complexity_score: int = 1
    needs_tools: bool = False
    needs_reasoning: bool = True
    needs_verification: bool = True
    risks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionDecision:
    mode: ExecutionMode
    reasons: list[str] = field(default_factory=list)
    max_routes: int = 1
    max_parallel_workers: int = 1
    max_repair_rounds: int = 0
    max_verify_rounds: int = 1


@dataclass(slots=True)
class ExecutionResult:
    status: ExecutionStatus
    output: str | None = None
    blockers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReasoningEvent:
    event_type: str
    payload: dict[str, Any]
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class SharedState:
    request: UserRequest
    profile: TaskProfile
    decision: ExecutionDecision
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    claims: list[dict[str, Any]] = field(default_factory=list)
    events: list[ReasoningEvent] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def record_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        self.events.append(ReasoningEvent(event_type=event_type, payload=payload or {}))

    def add_claim(self, claim: str, *, evidence: list[Any] | None = None, assumptions: list[str] | None = None) -> None:
        self.claims.append(
            {
                "claim": claim,
                "evidence": evidence or [],
                "assumptions": assumptions or [],
                "created_at": time.time(),
            }
        )

    def add_blocker(self, blocker: str) -> None:
        if blocker not in self.blockers:
            self.blockers.append(blocker)


class TaskAnalyzer(Protocol):
    def analyze(self, request: UserRequest) -> TaskProfile: ...


class PolicyEngine(Protocol):
    def decide(self, task: TaskProfile) -> ExecutionDecision: ...


class Runtime(Protocol):
    mode: ExecutionMode

    def execute(self, state: SharedState) -> ExecutionResult: ...


class VerifierGate(Protocol):
    def final_check(
        self,
        state: SharedState,
        result: ExecutionResult,
    ) -> ExecutionResult: ...


class TraceLogger(Protocol):
    def start_trace(self, request: UserRequest) -> str: ...

    def log_event(
        self,
        trace_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None: ...

    def end_trace(self, trace_id: str, result: ExecutionResult) -> None: ...


class HeuristicTaskAnalyzer:
    """Small default analyzer for the first executable engine skeleton.

    It is intentionally rule based. The first runtime milestone should validate the
    state-machine loop before depending on an LLM for classification.
    """

    _math_markers = ("求", "证明", "方程", "函数", "积分", "极限", "概率", "AIME", "MATH", "GSM8K")
    _tool_markers = ("代码", "文件", "仓库", "GitHub", "运行", "验证", "计算", "benchmark")
    _risk_markers = ("benchmark", "gpto1", "o1", "金融", "医疗", "法律", "安全", "高风险")
    _complex_markers = ("证明", "推导", "多步骤", "架构", "Agent", "agent", "微调", "benchmark")

    def analyze(self, request: UserRequest) -> TaskProfile:
        text = " ".join(
            [request.goal, request.target_conclusion or "", *request.known_conditions, *request.constraints]
        )
        complexity_score = 1
        if len(text) > 200 or len(request.known_conditions) >= 3:
            complexity_score = 2
        if any(marker in text for marker in self._complex_markers):
            complexity_score += 1
        if len(request.constraints) >= 3:
            complexity_score += 1
        complexity_score = max(1, min(5, complexity_score))

        risks = [marker for marker in self._risk_markers if marker in text]
        task_type = "math" if any(marker in text for marker in self._math_markers) else "general"

        return TaskProfile(
            request=request,
            task_type=task_type,
            complexity_score=complexity_score,
            needs_tools=any(marker in text for marker in self._tool_markers),
            needs_reasoning=True,
            needs_verification=True,
            risks=risks,
        )


class RulePolicyEngine:
    """Default policy that mirrors docs/multi-agent-protocol.md in a minimal form."""

    def decide(self, task: TaskProfile) -> ExecutionDecision:
        if not task.request.goal.strip():
            return ExecutionDecision(
                mode=ExecutionMode.BLOCKED,
                reasons=["empty_goal"],
            )

        reasons: list[str] = []
        if task.complexity_score >= 3:
            reasons.append("complexity_score>=3")
        if task.risks:
            reasons.append("risk_markers_present")
        if task.needs_tools and task.complexity_score >= 2:
            reasons.append("tool_use_with_reasoning")

        if reasons:
            return ExecutionDecision(
                mode=ExecutionMode.AGENT_TEAM,
                reasons=reasons,
                max_routes=min(4, max(2, task.complexity_score)),
                max_parallel_workers=min(4, max(2, task.complexity_score)),
                max_repair_rounds=2,
                max_verify_rounds=3,
            )

        return ExecutionDecision(
            mode=ExecutionMode.SINGLE_AGENT,
            reasons=["low_complexity_single_agent_first"],
            max_routes=1,
            max_parallel_workers=1,
            max_repair_rounds=1 if task.needs_verification else 0,
            max_verify_rounds=1,
        )


class StrictVerifierGate:
    """First-pass ReviewGate.

    This gate does not prove domain correctness yet. It enforces the project-level
    invariant that a successful answer must contain output and must not hide blockers.
    """

    def final_check(self, state: SharedState, result: ExecutionResult) -> ExecutionResult:
        blockers = [*state.blockers, *result.blockers]

        if result.status == ExecutionStatus.PASS and not result.output:
            blockers.append("pass_without_output")
            return ExecutionResult(
                status=ExecutionStatus.FAIL,
                output=result.output,
                blockers=_dedupe(blockers),
                metadata={**result.metadata, "review_gate": "fail"},
            )

        if result.status == ExecutionStatus.PASS and blockers:
            return ExecutionResult(
                status=ExecutionStatus.REPAIR,
                output=result.output,
                blockers=_dedupe(blockers),
                metadata={**result.metadata, "review_gate": "repair"},
            )

        return ExecutionResult(
            status=result.status,
            output=result.output,
            blockers=_dedupe(blockers),
            metadata={**result.metadata, "review_gate": result.status.value},
        )


class InMemoryTraceLogger:
    def __init__(self) -> None:
        self.traces: dict[str, list[dict[str, Any]]] = {}

    def start_trace(self, request: UserRequest) -> str:
        trace_id = str(uuid.uuid4())
        self.traces[trace_id] = [
            {
                "event_type": "trace_started",
                "payload": {"goal": request.goal},
                "created_at": time.time(),
            }
        ]
        return trace_id

    def log_event(self, trace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.traces.setdefault(trace_id, []).append(
            {
                "event_type": event_type,
                "payload": payload,
                "created_at": time.time(),
            }
        )

    def end_trace(self, trace_id: str, result: ExecutionResult) -> None:
        self.log_event(
            trace_id,
            "trace_ended",
            {
                "status": result.status.value,
                "blockers": result.blockers,
            },
        )


class OpenO1Engine:
    """Central state owner for the OpenO1 runtime.

    Agents and runtimes receive SharedState, but state mutation should be recorded
    through the engine-managed event log and later tightened by explicit validators.
    """

    def __init__(
        self,
        *,
        analyzer: TaskAnalyzer | None = None,
        policy: PolicyEngine | None = None,
        runtimes: list[Runtime] | None = None,
        verifier_gate: VerifierGate | None = None,
        trace_logger: TraceLogger | None = None,
    ) -> None:
        self.analyzer = analyzer or HeuristicTaskAnalyzer()
        self.policy = policy or RulePolicyEngine()
        self.verifier_gate = verifier_gate or StrictVerifierGate()
        self.trace_logger = trace_logger or InMemoryTraceLogger()
        self.runtimes: dict[ExecutionMode, Runtime] = {}
        for runtime in runtimes or []:
            self.runtimes[runtime.mode] = runtime

    def run(self, request: UserRequest) -> ExecutionResult:
        trace_id = self.trace_logger.start_trace(request)
        state: SharedState | None = None

        try:
            profile = self.analyzer.analyze(request)
            decision = self.policy.decide(profile)
            state = SharedState(
                request=request,
                profile=profile,
                decision=decision,
                trace_id=trace_id,
            )
            self._record(
                state,
                "task_profiled",
                {
                    "task_type": profile.task_type,
                    "complexity_score": profile.complexity_score,
                    "needs_tools": profile.needs_tools,
                    "risks": profile.risks,
                },
            )
            self._record(
                state,
                "execution_decided",
                {
                    "mode": decision.mode.value,
                    "reasons": decision.reasons,
                    "max_routes": decision.max_routes,
                    "max_parallel_workers": decision.max_parallel_workers,
                    "max_repair_rounds": decision.max_repair_rounds,
                    "max_verify_rounds": decision.max_verify_rounds,
                },
            )

            if decision.mode == ExecutionMode.BLOCKED:
                result = ExecutionResult(
                    status=ExecutionStatus.FAIL,
                    blockers=decision.reasons,
                    metadata={"trace_id": trace_id, "mode": decision.mode.value},
                )
                return self._finish(state, result)

            runtime = self.runtimes.get(decision.mode)
            if runtime is None:
                state.add_blocker(f"runtime_not_registered:{decision.mode.value}")
                result = ExecutionResult(
                    status=ExecutionStatus.FAIL,
                    blockers=state.blockers,
                    metadata={"trace_id": trace_id, "mode": decision.mode.value},
                )
                return self._finish(state, result)

            raw_result = runtime.execute(state)
            self._record(
                state,
                "runtime_completed",
                {
                    "runtime_mode": runtime.mode.value,
                    "status": raw_result.status.value,
                    "blockers": raw_result.blockers,
                },
            )
            return self._finish(state, raw_result)

        except Exception as exc:  # pragma: no cover - defensive boundary for external runtimes.
            result = ExecutionResult(
                status=ExecutionStatus.FAIL,
                blockers=[f"engine_exception:{exc.__class__.__name__}:{exc}"],
                metadata={"trace_id": trace_id},
            )
            if state is not None:
                state.add_blocker(result.blockers[0])
                return self._finish(state, result)
            self.trace_logger.end_trace(trace_id, result)
            return result

    def _record(self, state: SharedState, event_type: str, payload: dict[str, Any]) -> None:
        state.record_event(event_type, payload)
        self.trace_logger.log_event(state.trace_id, event_type, payload)

    def _finish(self, state: SharedState, result: ExecutionResult) -> ExecutionResult:
        checked = self.verifier_gate.final_check(state, result)
        checked.metadata.setdefault("trace_id", state.trace_id)
        checked.metadata.setdefault("mode", state.decision.mode.value)
        checked.metadata.setdefault("event_count", len(state.events))
        checked.metadata.setdefault("claim_count", len(state.claims))
        checked.metadata.setdefault("task_type", state.profile.task_type)
        self._record(
            state,
            "review_gate_completed",
            {
                "status": checked.status.value,
                "blockers": checked.blockers,
            },
        )
        self.trace_logger.end_trace(state.trace_id, checked)
        return checked


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


__all__ = [
    "ExecutionDecision",
    "ExecutionMode",
    "ExecutionResult",
    "ExecutionStatus",
    "HeuristicTaskAnalyzer",
    "InMemoryTraceLogger",
    "OpenO1Engine",
    "PolicyEngine",
    "ReasoningEvent",
    "RulePolicyEngine",
    "Runtime",
    "SharedState",
    "StrictVerifierGate",
    "TaskAnalyzer",
    "TaskProfile",
    "TraceLogger",
    "UserRequest",
    "VerifierGate",
]
