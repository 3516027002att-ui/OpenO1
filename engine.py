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
    max_repair_rounds: int = 0


@dataclass(slots=True)
class ExecutionResult:
    status: ExecutionStatus
    output: str | None = None
    blockers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SharedState:
    request: UserRequest
    profile: TaskProfile
    decision: ExecutionDecision
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    claims: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


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


__all__ = [
    "ExecutionDecision",
    "ExecutionMode",
    "ExecutionResult",
    "ExecutionStatus",
    "PolicyEngine",
    "Runtime",
    "SharedState",
    "TaskAnalyzer",
    "TaskProfile",
    "TraceLogger",
    "UserRequest",
    "VerifierGate",
]
