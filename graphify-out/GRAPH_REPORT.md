# Graph Report - .  (2026-07-18)

## Corpus Check
- Corpus is ~3,417 words - fits in a single context window. You may not need a graph.

## Summary
- 175 nodes · 284 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 28 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- External Lessons AgentScope
- Runtime Trace SharedState
- Policy Analysis Pipeline
- Context Lifecycle Memory
- Engine Core and Tests
- Review Gate Benchmarks
- Middleware Pipeline
- Multi-Agent Roles
- Math Tool Groups
- Workspace Types
- VerifierResult Orphan

## God Nodes (most connected - your core abstractions)
1. `SharedState` - 16 edges
2. `ExecutionResult` - 15 edges
3. `UserRequest` - 14 edges
4. `OpenO1Engine` - 13 edges
5. `EchoRuntime` - 9 edges
6. `TeamRuntime` - 9 edges
7. `OpenO1` - 8 edges
8. `通用推理受控状态机` - 8 edges
9. `Memory Update` - 8 edges
10. `Verifier` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Review Gate` --semantically_similar_to--> `ReviewGate`  [INFERRED] [semantically similar]
  README.md → docs/multi-agent-protocol.md
- `VerifierGate` --semantically_similar_to--> `VerifierGateMiddleware`  [INFERRED] [semantically similar]
  README.md → docs/external-lessons/agentscope.md
- `Task Intake` --semantically_similar_to--> `TaskSpec`  [INFERRED] [semantically similar]
  README.md → docs/context-lifecycle.md
- `Shared Context` --semantically_similar_to--> `SharedContext`  [INFERRED] [semantically similar]
  README.md → docs/multi-agent-protocol.md
- `Domain Verifier` --semantically_similar_to--> `DomainVerifier`  [INFERRED] [semantically similar]
  README.md → docs/multi-agent-protocol.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **上下文生命周期闭环** — docs_context_lifecycle_taskspec, docs_context_lifecycle_working_context, docs_context_lifecycle_taskcommit, docs_context_lifecycle_memory_update, docs_context_lifecycle_compression_review, docs_context_lifecycle_context_pack, docs_context_lifecycle_context_reset, docs_context_lifecycle_rehydrate [EXTRACTED 1.00]
- **多 Agent 默认推理流水线** — docs_multi_agent_protocol_mainagent, docs_multi_agent_protocol_planner, docs_multi_agent_protocol_worker, docs_multi_agent_protocol_verifier, docs_multi_agent_protocol_supervisor, docs_multi_agent_protocol_critic, docs_multi_agent_protocol_solver, docs_multi_agent_protocol_reviewgate, docs_multi_agent_protocol_synthesizer [EXTRACTED 1.00]
- **AgentScope 可迁移 runtime 设计模式** — docs_external_lessons_agentscope_message_event_separation, docs_external_lessons_agentscope_stateless_agent, docs_external_lessons_agentscope_tool_group, docs_external_lessons_agentscope_permission_system, docs_external_lessons_agentscope_middleware, docs_external_lessons_agentscope_workspace, docs_external_lessons_agentscope_service_boundary [EXTRACTED 1.00]

## Communities (11 total, 1 thin omitted)

### Community 0 - "External Lessons AgentScope"
Cohesion: 0.06
Nodes (34): 缓存与成本策略优先级, 上下文生命周期与外部记忆设计, Agent Runtime / Harness, AgentScope 学习记录, ContinueDecisionEvent, Message 与 Event 分离, 不把 ReAct loop 当作 o1 推理核心, 权限系统 (+26 more)

### Community 1 - "Runtime Trace SharedState"
Cohesion: 0.13
Nodes (12): Any, _dedupe(), ExecutionResult, InMemoryTraceLogger, 执行具体推理任务的运行环境。      一个 Runtime 对应一种 ExecutionMode（如 SINGLE_AGENT、AGENT_TEAM）。, 内存中的 TraceLogger 默认实现，数据进程内有效、重启后丢失。      适用于开发和单次测试。生产环境应替换为持久化实现。, Runtime 执行完成后产生的结果，经 VerifierGate 审查后返回给调用方。, 一次推理过程中的结构化事件记录，用于审计和回溯。      事件类型（event_type）由引擎或 Agent 定义，payload 携带具体数据。 (+4 more)

### Community 2 - "Policy Analysis Pipeline"
Cohesion: 0.09
Nodes (19): ExecutionDecision, HeuristicTaskAnalyzer, PolicyEngine, 分析 UserRequest，产出 TaskProfile。      默认实现 HeuristicTaskAnalyzer 基于关键词规则，     业, 根据 TaskProfile 决定执行模式。      默认实现 RulePolicyEngine 按复杂度阈值规则决策，     业务方可替换为更复杂的, 最终质量门禁：审查 ExecutionResult 是否符合项目级不变量。      不通过时可返回 REPAIR（需修复）或 FAIL（不可修复）。, 追踪日志记录器，记录一次完整推理的所有事件。      默认实现 InMemoryTraceLogger 存在内存中，     业务方可替换为持久化或远程, Small default analyzer for the first executable engine skeleton.      It is in (+11 more)

### Community 3 - "Context Lifecycle Memory"
Cohesion: 0.14
Nodes (18): Compression Review, Context Pack, Context Reset, 通过 Context Pack 实现可编辑上下文, 外部记忆, Memory Type: artifact_ref, Memory Type: claim, Memory Type: fact (+10 more)

### Community 4 - "Engine Core and Tests"
Cohesion: 0.27
Nodes (16): ExecutionMode, ExecutionStatus, OpenO1Engine, OpenO1 中心引擎模块。  本模块是推理状态机的核心骨架，定义了： - 数据模型：UserRequest、TaskProfile、ExecutionD, PolicyEngine 决定的执行模式。, Central state owner for the OpenO1 runtime.      Agents and runtimes receive S, 用户提交的原始任务请求，由入口层解析后传入引擎。, UserRequest (+8 more)

### Community 5 - "Review Gate Benchmarks"
Cohesion: 0.19
Nodes (14): DomainVerifier, MathDomainVerifier, ReviewGate, ReviewGateDecision, Synthesizer, AgentTeam, AIME, Benchmark / Eval (+6 more)

### Community 6 - "Middleware Pipeline"
Cohesion: 0.15
Nodes (13): ContinuePolicyMiddleware, Middleware, ReviewerMiddleware, StepCheckMiddleware, TraceMiddleware, VerifierGateMiddleware, engine.py, OpenO1Engine (+5 more)

### Community 7 - "Multi-Agent Roles"
Cohesion: 0.24
Nodes (10): Critic, EscalationDecision, MainAgent, Planner, RouteScore, 默认单 Agent 起步, Solver, Supervisor (+2 more)

### Community 8 - "Math Tool Groups"
Cohesion: 0.29
Nodes (7): BasicMathTools, ControlTools, CounterexampleTools, FormalVerifierTools, ProofPlanningTools, ReviewTools, Tool Group

### Community 9 - "Workspace Types"
Cohesion: 0.33
Nodes (6): BenchmarkWorkspace, DockerProofWorkspace, ExperimentWorkspace, LocalMathWorkspace, MathWorkspace, Workspace

## Knowledge Gaps
- **39 isolated node(s):** `AGENTS.md`, `TaskAnalyzer`, `PolicyEngine`, `Runtime`, `TraceLogger` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OpenO1` connect `External Lessons AgentScope` to `Review Gate Benchmarks`, `Middleware Pipeline`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `ReviewGate` connect `Review Gate Benchmarks` to `Context Lifecycle Memory`, `Middleware Pipeline`, `Multi-Agent Roles`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `通用推理受控状态机` connect `Review Gate Benchmarks` to `External Lessons AgentScope`, `Context Lifecycle Memory`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `SharedState` (e.g. with `EchoRuntime` and `TeamRuntime`) actually correct?**
  _`SharedState` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ExecutionResult` (e.g. with `EchoRuntime` and `TeamRuntime`) actually correct?**
  _`ExecutionResult` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `UserRequest` (e.g. with `EchoRuntime` and `TeamRuntime`) actually correct?**
  _`UserRequest` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `OpenO1Engine` (e.g. with `EchoRuntime` and `TeamRuntime`) actually correct?**
  _`OpenO1Engine` has 2 INFERRED edges - model-reasoned connections that need verification._