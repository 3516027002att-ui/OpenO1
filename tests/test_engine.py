from engine import (
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    OpenO1Engine,
    SharedState,
    UserRequest,
)


class EchoRuntime:
    mode = ExecutionMode.SINGLE_AGENT

    def execute(self, state: SharedState) -> ExecutionResult:
        state.add_claim("echo runtime completed", evidence=[{"type": "mock"}], assumptions=[])
        return ExecutionResult(status=ExecutionStatus.PASS, output=f"done: {state.request.goal}")


class TeamRuntime:
    mode = ExecutionMode.AGENT_TEAM

    def execute(self, state: SharedState) -> ExecutionResult:
        state.add_claim("team runtime completed", evidence=[{"type": "mock"}], assumptions=[])
        return ExecutionResult(status=ExecutionStatus.PASS, output="team done")


def test_engine_runs_single_agent_path() -> None:
    engine = OpenO1Engine(runtimes=[EchoRuntime()])

    result = engine.run(UserRequest(goal="summarize a short note"))

    assert result.status == ExecutionStatus.PASS
    assert result.output == "done: summarize a short note"
    assert result.metadata["mode"] == ExecutionMode.SINGLE_AGENT.value
    assert result.metadata["claim_count"] == 1
    assert result.metadata["event_count"] >= 3


def test_engine_routes_complex_task_to_agent_team() -> None:
    engine = OpenO1Engine(runtimes=[TeamRuntime()])

    result = engine.run(UserRequest(goal="证明一个多步骤数学推导并验证每一步"))

    assert result.status == ExecutionStatus.PASS
    assert result.output == "team done"
    assert result.metadata["mode"] == ExecutionMode.AGENT_TEAM.value
    assert result.metadata["task_type"] == "math"


def test_engine_fails_when_runtime_is_missing() -> None:
    engine = OpenO1Engine(runtimes=[])

    result = engine.run(UserRequest(goal="summarize a short note"))

    assert result.status == ExecutionStatus.FAIL
    assert "runtime_not_registered:single_agent" in result.blockers
    assert result.metadata["mode"] == ExecutionMode.SINGLE_AGENT.value


def test_review_gate_rejects_pass_without_output() -> None:
    class EmptyRuntime:
        mode = ExecutionMode.SINGLE_AGENT

        def execute(self, state: SharedState) -> ExecutionResult:
            return ExecutionResult(status=ExecutionStatus.PASS, output=None)

    engine = OpenO1Engine(runtimes=[EmptyRuntime()])

    result = engine.run(UserRequest(goal="summarize a short note"))

    assert result.status == ExecutionStatus.FAIL
    assert "pass_without_output" in result.blockers
