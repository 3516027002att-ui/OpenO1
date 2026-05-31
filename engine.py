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


class ActionType(str, Enum):
    CALL_MODULE = "call_module"
    RUN_RUNTIME = "run_runtime"
    SPAWN_SUBAGENT = "spawn_subagent"
    WAIT_SUBAGENT = "wait_subagent"
    CANCEL_SUBAGENT = "cancel_subagent"
    MERGE_RESULTS = "merge_results"
    RUN_TESTS = "run_tests"
    RUN_VERIFIER = "run_verifier"
    RUN_LEAN = "run_lean"
    RUN_REPAIR = "run_repair"
    CHECK_GOAL = "check_goal"
    FINAL_REVIEW = "final_review"
    CONTINUE_EXECUTION = "continue_execution"
    REQUEST_USER_INPUT = "request_user_input"
    FINALIZE = "finalize"
    ABORT = "abort"


class ModuleStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    REPAIR_NEEDED = "repair_needed"
    CONTINUE_NEEDED = "continue_needed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(slots=True)
class Budget:
    max_steps: int = 32
    max_subagents: int = 4
    max_tool_calls: int = 32
    max_repair_rounds: int = 2
    max_verify_rounds: int = 3
    max_seconds: float | None = None
    token_budget: int | None = None


@dataclass(slots=True)
class UserRequest:
    goal: str
    known_conditions: list[str] = field(default_factory=list)
    target_conclusion: str | None = None
    output_format: str | None = None
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    background_context: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    budget: Budget | None = None


@dataclass(slots=True)
class Action:
    action_type: ActionType
    target: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_call_id: str | None = None
    reason: str | None = None
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class TaskProfile:
    request: UserRequest
    task_type: str = "general"
    complexity_score: int = 1
    needs_tools: bool = False
    needs_reasoning: bool = True
    needs_verification: bool = True
    risks: list[str] = field(default_factory=list)

    requires_decomposition: bool = False
    requires_subagents: bool = False
    requires_formal_verification: bool = False
    requires_tool_use: bool = False
    requires_long_context: bool = False
    success_criteria: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionDecision:
    mode: ExecutionMode
    reasons: list[str] = field(default_factory=list)
    max_routes: int = 1
    max_parallel_workers: int = 1
    max_repair_rounds: int = 0
    max_verify_rounds: int = 1
    initial_actions: list[Action] = field(default_factory=list)


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
class Artifact:
    artifact_id: str
    kind: str
    content: Any
    producer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class ArtifactStore(Protocol):
    def put(
        self,
        kind: str,
        content: Any,
        *,
        producer: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact: ...

    def get(self, artifact_id: str) -> Artifact | None: ...

    def list(self, *, kind: str | None = None) -> list[Artifact]: ...


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}

    def put(
        self,
        kind: str,
        content: Any,
        *,
        producer: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        artifact = Artifact(
            artifact_id=str(uuid.uuid4()),
            kind=kind,
            content=content,
            producer=producer,
            metadata=metadata or {},
        )
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        return self._artifacts.get(artifact_id)

    def list(self, *, kind: str | None = None) -> list[Artifact]:
        artifacts = list(self._artifacts.values())
        if kind is None:
            return artifacts
        return [artifact for artifact in artifacts if artifact.kind == kind]


@dataclass(slots=True)
class ModuleResult:
    module_name: str
    status: ModuleStatus
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_call_id: str | None = None
    state_patch: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    confidence: float | None = None
    completion_delta: float | None = None
    budget_used: dict[str, Any] = field(default_factory=dict)
    next_actions: list[Action] = field(default_factory=list)
    output: str | None = None
    execution_result: ExecutionResult | None = None


@dataclass(slots=True)
class SharedState:
    request: UserRequest
    profile: TaskProfile
    decision: ExecutionDecision
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    plan: dict[str, Any] | None = None
    subtasks: list[dict[str, Any]] = field(default_factory=list)
    active_agents: list[dict[str, Any]] = field(default_factory=list)
    completed_agents: list[dict[str, Any]] = field(default_factory=list)
    failed_agents: list[dict[str, Any]] = field(default_factory=list)

    claims: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    artifact_store: ArtifactStore = field(default_factory=InMemoryArtifactStore)

    lean_checks: list[dict[str, Any]] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    review_records: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    events: list[ReasoningEvent] = field(default_factory=list)
    action_queue: list[Action] = field(default_factory=list)
    action_history: list[Action] = field(default_factory=list)

    final_answer: str | None = None
    completion_status: str = "running"
    scratch: dict[str, Any] = field(default_factory=dict)
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

    def enqueue(self, action: Action) -> None:
        self.action_queue.append(action)


class TaskAnalyzer(Protocol):
    def analyze(self, request: UserRequest) -> TaskProfile: ...


class PolicyEngine(Protocol):
    def decide(self, task: TaskProfile) -> ExecutionDecision: ...


class Runtime(Protocol):
    mode: ExecutionMode

    def execute(self, state: SharedState) -> ExecutionResult: ...


class EngineModule(Protocol):
    name: str
    is_reentrant: bool

    def execute(self, state: SharedState, action: Action) -> ModuleResult: ...


class TaskDecomposer(Protocol):
    name: str

    def decompose(self, state: SharedState) -> ModuleResult: ...


class SubagentPolicy(Protocol):
    name: str

    def allocate(self, state: SharedState) -> ModuleResult: ...


class SubagentRuntime(Protocol):
    name: str

    def execute_subagent(self, state: SharedState, action: Action) -> ModuleResult: ...


class ResultMerger(Protocol):
    name: str

    def merge(self, state: SharedState, action: Action) -> ModuleResult: ...


class GoalManager(Protocol):
    name: str

    def check_goal(self, state: SharedState, action: Action) -> ModuleResult: ...


class PromptBuilder(Protocol):
    name: str

    def build_prompt(self, state: SharedState, action: Action) -> ModuleResult: ...


class ConstraintEngine(Protocol):
    name: str

    def check_constraints(self, state: SharedState, action: Action) -> ModuleResult: ...


class LeanVerifier(Protocol):
    name: str

    def verify_lean(self, state: SharedState, action: Action) -> ModuleResult: ...


class DomainVerifier(Protocol):
    name: str

    def verify_domain(self, state: SharedState, action: Action) -> ModuleResult: ...


class RepairPlanner(Protocol):
    name: str

    def plan_repair(self, state: SharedState, action: Action) -> ModuleResult: ...


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


class Scheduler(Protocol):
    def next_action(self, state: SharedState) -> Action | None: ...


class FifoScheduler:
    """Small deterministic scheduler.

    It keeps the engine flexible without hiding policy in the engine itself.
    More advanced schedulers can rank actions by risk, budget, subagent progress,
    goal gaps, or user-selected subagent strength.
    """

    def next_action(self, state: SharedState) -> Action | None:
        if not state.action_queue:
            return None
        best_index = min(
            range(len(state.action_queue)),
            key=lambda index: (state.action_queue[index].priority, state.action_queue[index].created_at),
        )
        return state.action_queue.pop(best_index)


class ModuleRegistry:
    def __init__(self, modules: list[EngineModule] | None = None) -> None:
        self._modules: dict[str, EngineModule] = {}
        for module in modules or []:
            self.register(module)

    def register(self, module: EngineModule) -> None:
        self._modules[module.name] = module

    def get(self, name: str) -> EngineModule | None:
        return self._modules.get(name)

    def names(self) -> list[str]:
        return sorted(self._modules)


class HeuristicTaskAnalyzer:
    """Small default analyzer for the first executable engine skeleton.

    It is intentionally rule based. The first runtime milestone should validate the
    state-machine loop before depending on an LLM for classification.
    """

    _math_markers = ("求", "证明", "方程", "函数", "积分", "极限", "概率", "AIME", "MATH", "GSM8K")
    _tool_markers = ("代码", "文件", "仓库", "GitHub", "运行", "验证", "计算", "benchmark", "测试", "Lean")
    _risk_markers = ("benchmark", "gpto1", "o1", "金融", "医疗", "法律", "安全", "高风险")
    _complex_markers = ("证明", "推导", "多步骤", "架构", "Agent", "agent", "微调", "benchmark", "subagent")
    _formal_markers = ("Lean", "形式化", "定理证明", "formal")

    def analyze(self, request: UserRequest) -> TaskProfile:
        text = " ".join(
            [
                request.goal,
                request.target_conclusion or "",
                *request.known_conditions,
                *request.constraints,
                *request.background_context,
            ]
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
        needs_tools = any(marker in text for marker in self._tool_markers)

        return TaskProfile(
            request=request,
            task_type=task_type,
            complexity_score=complexity_score,
            needs_tools=needs_tools,
            needs_reasoning=True,
            needs_verification=True,
            risks=risks,
            requires_decomposition=complexity_score >= 3,
            requires_subagents=complexity_score >= 3 or bool(risks),
            requires_formal_verification=any(marker in text for marker in self._formal_markers),
            requires_tool_use=needs_tools,
            requires_long_context=len(text) > 800,
            success_criteria=[request.target_conclusion] if request.target_conclusion else [],
        )


class RulePolicyEngine:
    """Default policy that chooses an initial action plan.

    The policy remains intentionally small. It decides whether the default route is
    single-agent or agent-team, then lets the scheduler and module next_actions keep
    the workflow dynamic and reentrant.
    """

    def decide(self, task: TaskProfile) -> ExecutionDecision:
        if not task.request.goal.strip():
            return ExecutionDecision(
                mode=ExecutionMode.BLOCKED,
                reasons=["empty_goal"],
                initial_actions=[Action(action_type=ActionType.ABORT, reason="empty_goal")],
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
                "payload": {"goal": request.goal, "request_id": request.request_id},
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
    """Central state owner and dynamic action scheduler for OpenO1.

    The engine defines protocol, state, artifacts, module registration, action
    scheduling, and ReviewGate boundaries. It does not implement task decomposition,
    subagent reasoning, Lean proving, prompt engineering, or domain-specific review.
    Those capabilities should be registered as reentrant modules.
    """

    _DEFAULT_ACTION_TARGETS: dict[ActionType, str] = {
        ActionType.SPAWN_SUBAGENT: "SubagentRuntime",
        ActionType.MERGE_RESULTS: "ResultMerger",
        ActionType.RUN_TESTS: "TestRunner",
        ActionType.RUN_VERIFIER: "DomainVerifier",
        ActionType.RUN_LEAN: "LeanVerifier",
        ActionType.RUN_REPAIR: "RepairPlanner",
        ActionType.CHECK_GOAL: "GoalManager",
        ActionType.CONTINUE_EXECUTION: "TaskDecomposer",
    }

    def __init__(
        self,
        *,
        analyzer: TaskAnalyzer | None = None,
        policy: PolicyEngine | None = None,
        runtimes: list[Runtime] | None = None,
        modules: list[EngineModule] | None = None,
        scheduler: Scheduler | None = None,
        verifier_gate: VerifierGate | None = None,
        trace_logger: TraceLogger | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.analyzer = analyzer or HeuristicTaskAnalyzer()
        self.policy = policy or RulePolicyEngine()
        self.scheduler = scheduler or FifoScheduler()
        self.verifier_gate = verifier_gate or StrictVerifierGate()
        self.trace_logger = trace_logger or InMemoryTraceLogger()
        self.max_steps = max_steps

        self.runtimes: dict[ExecutionMode, Runtime] = {}
        for runtime in runtimes or []:
            self.runtimes[runtime.mode] = runtime

        self.modules = ModuleRegistry(modules)

    def register_module(self, module: EngineModule) -> None:
        self.modules.register(module)

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
                    "requires_decomposition": profile.requires_decomposition,
                    "requires_subagents": profile.requires_subagents,
                    "requires_formal_verification": profile.requires_formal_verification,
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
                    "initial_actions": [action.action_type.value for action in decision.initial_actions],
                },
            )

            self._seed_actions(state)

            raw_result = self._run_action_loop(state)
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

    def _seed_actions(self, state: SharedState) -> None:
        if state.decision.initial_actions:
            for action in state.decision.initial_actions:
                state.enqueue(action)
            return

        if state.decision.mode == ExecutionMode.BLOCKED:
            state.enqueue(Action(action_type=ActionType.ABORT, reason="execution_blocked"))
            return

        state.enqueue(
            Action(
                action_type=ActionType.RUN_RUNTIME,
                target=state.decision.mode.value,
                reason="default_policy_runtime_entry",
            )
        )

    def _run_action_loop(self, state: SharedState) -> ExecutionResult:
        budget = state.request.budget or Budget()
        max_steps = self.max_steps or budget.max_steps
        started_at = time.time()
        steps = 0
        last_result: ExecutionResult | None = None

        while steps < max_steps:
            if budget.max_seconds is not None and time.time() - started_at > budget.max_seconds:
                state.add_blocker("budget_exceeded:max_seconds")
                break

            action = self.scheduler.next_action(state)
            if action is None:
                break

            steps += 1
            state.action_history.append(action)
            self._record(
                state,
                "action_started",
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "target": action.target,
                    "reason": action.reason,
                },
            )

            if action.action_type == ActionType.ABORT:
                reason = action.reason or "aborted"
                state.add_blocker(reason)
                return ExecutionResult(status=ExecutionStatus.FAIL, blockers=state.blockers)

            if action.action_type == ActionType.REQUEST_USER_INPUT:
                reason = action.reason or "user_input_required"
                state.add_blocker(reason)
                return ExecutionResult(status=ExecutionStatus.PARTIAL, blockers=state.blockers)

            if action.action_type == ActionType.RUN_RUNTIME:
                last_result = self._execute_runtime_action(state, action)
                if last_result.status in {ExecutionStatus.PASS, ExecutionStatus.FAIL, ExecutionStatus.PARTIAL}:
                    return last_result
                continue

            if action.action_type == ActionType.FINALIZE:
                output = action.payload.get("output") or state.final_answer
                return ExecutionResult(
                    status=ExecutionStatus.PASS if output else ExecutionStatus.FAIL,
                    output=output,
                    blockers=[] if output else ["finalize_without_output"],
                )

            module_result = self._execute_module_action(state, action)
            self._apply_module_result(state, action, module_result)

            if module_result.execution_result is not None:
                return module_result.execution_result

            if module_result.output is not None:
                state.final_answer = module_result.output

            if module_result.status == ModuleStatus.FAILED and not module_result.next_actions:
                last_result = ExecutionResult(
                    status=ExecutionStatus.FAIL,
                    output=state.final_answer,
                    blockers=state.blockers or module_result.blockers,
                )
                return last_result

        if steps >= max_steps:
            state.add_blocker("budget_exceeded:max_steps")

        if last_result is not None:
            return last_result

        if state.final_answer:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL if state.blockers else ExecutionStatus.PASS,
                output=state.final_answer,
                blockers=state.blockers,
            )

        if state.blockers:
            return ExecutionResult(status=ExecutionStatus.FAIL, blockers=state.blockers)

        return ExecutionResult(status=ExecutionStatus.FAIL, blockers=["no_terminal_action"])

    def _execute_runtime_action(self, state: SharedState, action: Action) -> ExecutionResult:
        mode_value = action.target or state.decision.mode.value
        try:
            mode = ExecutionMode(mode_value)
        except ValueError:
            state.add_blocker(f"unknown_runtime_mode:{mode_value}")
            return ExecutionResult(status=ExecutionStatus.FAIL, blockers=state.blockers)

        runtime = self.runtimes.get(mode)
        if runtime is None:
            state.add_blocker(f"runtime_not_registered:{mode.value}")
            return ExecutionResult(
                status=ExecutionStatus.FAIL,
                blockers=state.blockers,
                metadata={"trace_id": state.trace_id, "mode": mode.value},
            )

        raw_result = runtime.execute(state)
        self._record(
            state,
            "runtime_completed",
            {
                "runtime_mode": mode.value,
                "status": raw_result.status.value,
                "blockers": raw_result.blockers,
            },
        )
        return raw_result

    def _execute_module_action(self, state: SharedState, action: Action) -> ModuleResult:
        target = action.target or self._DEFAULT_ACTION_TARGETS.get(action.action_type)
        if target is None:
            return ModuleResult(
                module_name="<missing>",
                status=ModuleStatus.FAILED,
                blockers=[f"unsupported_action:{action.action_type.value}"],
                parent_call_id=action.parent_call_id,
            )

        module = self.modules.get(target)
        if module is None:
            return ModuleResult(
                module_name=target,
                status=ModuleStatus.FAILED,
                blockers=[f"module_not_registered:{target}"],
                parent_call_id=action.parent_call_id,
            )

        try:
            return module.execute(state, action)
        except Exception as exc:  # pragma: no cover - external module boundary.
            return ModuleResult(
                module_name=target,
                status=ModuleStatus.FAILED,
                blockers=[f"module_exception:{target}:{exc.__class__.__name__}:{exc}"],
                parent_call_id=action.parent_call_id,
            )

    def _apply_module_result(self, state: SharedState, action: Action, result: ModuleResult) -> None:
        self._record(
            state,
            "module_completed",
            {
                "action_id": action.action_id,
                "module_name": result.module_name,
                "call_id": result.call_id,
                "status": result.status.value,
                "blockers": result.blockers,
                "next_actions": [next_action.action_type.value for next_action in result.next_actions],
            },
        )

        self._merge_state_patch(state, result.state_patch)

        for artifact in result.artifacts:
            state.artifacts.append(artifact)
            state.artifact_store.put(
                artifact.kind,
                artifact.content,
                producer=artifact.producer or result.module_name,
                metadata={**artifact.metadata, "source_artifact_id": artifact.artifact_id},
            )

        state.claims.extend(result.claims)
        state.evidence.extend(result.evidence)

        for blocker in result.blockers:
            state.add_blocker(blocker)

        for next_action in result.next_actions:
            if next_action.parent_call_id is None:
                next_action.parent_call_id = result.call_id
            state.enqueue(next_action)

    def _merge_state_patch(self, state: SharedState, patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if not hasattr(state, key):
                state.scratch[key] = value
                continue

            current_value = getattr(state, key)
            if isinstance(current_value, list):
                if isinstance(value, list):
                    current_value.extend(value)
                else:
                    current_value.append(value)
            elif isinstance(current_value, dict) and isinstance(value, dict):
                current_value.update(value)
            else:
                setattr(state, key, value)

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
        checked.metadata.setdefault("action_count", len(state.action_history))
        checked.metadata.setdefault("artifact_count", len(state.artifacts))
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
    "Action",
    "ActionType",
    "Artifact",
    "ArtifactStore",
    "Budget",
    "ConstraintEngine",
    "DomainVerifier",
    "EngineModule",
    "ExecutionDecision",
    "ExecutionMode",
    "ExecutionResult",
    "ExecutionStatus",
    "FifoScheduler",
    "GoalManager",
    "HeuristicTaskAnalyzer",
    "InMemoryArtifactStore",
    "InMemoryTraceLogger",
    "LeanVerifier",
    "ModuleRegistry",
    "ModuleResult",
    "ModuleStatus",
    "OpenO1Engine",
    "PolicyEngine",
    "PromptBuilder",
    "ReasoningEvent",
    "RepairPlanner",
    "ResultMerger",
    "RulePolicyEngine",
    "Runtime",
    "Scheduler",
    "SharedState",
    "StrictVerifierGate",
    "SubagentPolicy",
    "SubagentRuntime",
    "TaskAnalyzer",
    "TaskDecomposer",
    "TaskProfile",
    "TraceLogger",
    "UserRequest",
    "VerifierGate",
]
