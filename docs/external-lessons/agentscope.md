# AgentScope 学习记录

## 来源

项目：AgentScope

来源：https://github.com/agentscope-ai/agentscope

观察日期：2026-05-26

## 一句话结论

AgentScope 对 OpenO1 的主要价值是 agent runtime 工程骨架，而不是数学推理增强算法。

OpenO1 可以学习它的事件流、状态隔离、工具分组、权限系统、workspace 和 service 化边界，但不能把普通 ReAct loop、多 agent 对话或自然语言摘要当作 o1 风格推理能力来源。

## 项目定位判断

AgentScope 更像 production-ready agent framework 或 agent harness。它关注的是 agent 如何运行、如何调工具、如何持久化状态、如何恢复、如何部署、如何观察运行轨迹。

这类框架解决的是“agent 运行过程是否可控”的问题，不直接解决“模型推理能力是否更强”的问题。

对 OpenO1 来说，这意味着：

- 可以借鉴它的 runtime 结构。
- 不能直接照搬它的推理范式。
- 数学推理增强仍然要依赖 OpenO1 自己的 ProofState、VerifierGate、ReviewGate、失败回滚和继续策略。

## 可取之处一：Message 和 Event 分离

AgentScope 把完整通信消息和流式执行事件区分开。这个设计对 OpenO1 很关键。

OpenO1 不应只记录最终答案，而应把推理过程拆成可审计事件。建议至少定义：

- ReasoningStepEvent：模型提出一个推导步骤。
- ToolCallEvent：模型请求调用工具。
- VerifierCallEvent：系统调用数学验证器或代码验证器。
- VerifierResultEvent：验证器返回通过、失败、反例或未判定。
- ReviewEvent：审阅器判断当前步骤质量。
- ContinueDecisionEvent：中心引擎决定继续、回滚、分支搜索或终止。

迁移到 OpenO1 后，这个设计的价值是：

- 失败可以定位到具体步骤。
- 验证和审阅结果可以进入训练数据。
- 多 agent 协作不再依赖互相聊天，而依赖事件日志和共享状态。
- 后续 benchmark 可以复现每次答案的生成轨迹。

## 可取之处二：Agent 无状态化，状态归中心引擎

AgentScope 的 agent 更像一个 reasoning acting loop engine，而不是最终状态所有者。

OpenO1 应坚持这一点：

- Agent 只提交候选步骤、候选路线、反例、修复建议或审阅意见。
- Agent 不能直接改写最终结论。
- Agent 不能绕过验证器把内容写入 proved context。
- 中心引擎维护 TaskState、ProofState、SharedContext、BudgetState 和 ReviewGate。

这能避免多 agent 系统退化成“多个模型互相聊天”。

OpenO1 的核心不是让 agent 说更多话，而是让每个 agent 只能向状态机提交结构化证据。

## 可取之处三：上下文分层与外部存储

AgentScope 的上下文管理包含近期上下文、摘要和外部存储。这个方向值得学习，但需要数学特化。

普通 agent 可以用自然语言摘要压缩上下文；数学推理不能这样做。因为数学任务中最容易出错的内容往往是：

- 变量定义。
- 量词范围。
- 定义域。
- 边界条件。
- 等价变形的前提。
- 已证明和未证明结论的边界。

OpenO1 的上下文压缩应变成 ProofState compression，而不是 chat summary。建议 ProofState 至少包含：

- problem_statement：原题，原则上不可压缩。
- definitions：符号、变量、范围、约束。
- proved_lemmas：已验证中间结论。
- open_goals：未完成目标。
- failed_attempts：失败路线和失败原因。
- verifier_records：每一步验证记录。
- unsafe_assumptions：模型自行引入但尚未验证的假设。

## 可取之处四：Tool Group

AgentScope 的工具系统支持工具集合和分组暴露。OpenO1 应强烈借鉴。

OpenO1 不应该把所有工具一次性暴露给模型。工具暴露越多，工具 schema 对上下文的污染越重，模型越容易乱选工具。

建议第一阶段设计这些工具组：

- BasicMathTools：Python 计算、SymPy 化简、数值代入。
- CounterexampleTools：边界测试、随机测试、反例搜索。
- FormalVerifierTools：Lean、Z3 或其他形式验证器。
- ProofPlanningTools：目标拆解、lemma 搜索、公式归一化。
- ReviewTools：跳步检查、条件检查、完整性检查。
- ControlTools：回滚、分支比较、继续策略评估。

工具组应由中心引擎按任务阶段开启，而不是由模型自由决定全部工具是否可见。

## 可取之处五：权限系统

AgentScope 的权限系统说明，agent runtime 必须处理“能做什么”和“不能做什么”。

OpenO1 如果未来允许本地 agent 运行命令、改 proof 文件、下载依赖或调用外部服务，就必须有权限层。

建议权限模式：

- PROVE_ONLY：只能读题、推理和调用验证器。
- EXPLORE：可以读文件、搜索 lemma、运行只读命令。
- ACCEPT_PROOF_EDITS：允许修改 proof 文件，但必须先读后写。
- SANDBOX_AUTONOMOUS：只能在隔离沙箱里自主运行。
- HUMAN_CONFIRM：危险命令必须人工确认。

权限系统不是附加功能，而是 OpenO1 可部署性的前提。

## 可取之处六：Middleware

AgentScope 的 middleware 思路适合 OpenO1 的 Review Gate。

OpenO1 不应把质量控制写死在某个 agent prompt 中，而应把它做成可插拔中间件。

建议中间件：

- StepCheckMiddleware：每个推理步骤生成后自动检查。
- VerifierGateMiddleware：未验证步骤不能进入 proved context。
- ReviewerMiddleware：检查跳步、偷换条件、边界遗漏。
- ContinuePolicyMiddleware：根据失败次数、验证状态和预算决定是否继续。
- TraceMiddleware：记录模型调用、工具调用、验证结果和审阅结论。

这会让 OpenO1 的核心从“多 agent 对话”变成“受控推理流水线”。

## 可取之处七：Workspace

AgentScope 的 workspace 抽象适合 OpenO1 未来的本地验证环境。

OpenO1 不应只给 agent 一个裸终端，而应提供可隔离、可审计、可复现的 workspace。

建议 workspace：

- LocalMathWorkspace：本地 Python、SymPy、Lean 环境。
- DockerProofWorkspace：隔离运行 Lean、Z3、Python。
- BenchmarkWorkspace：运行 MATH、GSM8K、AIME、Lean theorem benchmark。
- ExperimentWorkspace：保存模型版本、prompt、事件日志、验证结果和失败原因。

Workspace 的核心目标不是方便模型乱跑命令，而是让每次运行都有边界、有记录、可复现。

## 可取之处八：Service 化边界

AgentScope 的 service 化设计说明，一个成熟 agent 框架需要区分 agent、session、workspace、credential、schedule 和模型绑定。

OpenO1 第一阶段可以先做 CLI 或本地原型，但数据结构上应保留 service 化边界。

尤其要支持：同一个 OpenO1 推理框架，在不同 session 下绑定不同模型。这样才能公平比较本地模型、API 模型、微调模型在同一套 harness 下的表现。

## 不应照搬

OpenO1 不应照搬以下内容：

- 把多 agent 自由对话当作能力来源。
- 把普通 ReAct loop 当作 o1 风格推理核心。
- 把自然语言摘要当作数学证明状态。
- 把工具调用成功等同于推理正确。
- 把工程成熟度误认为模型推理能力提升。

## 可转化为近期任务

建议把 AgentScope 的启发转化为以下 OpenO1 近期任务：

1. 定义 ReasoningEvent 数据结构。
2. 定义 ReasoningEventLog 追加式日志。
3. 定义 ProofState。
4. 定义 VerifierResult。
5. 实现最小 VerifierGate。
6. 实现 MathWorkspace，先接入 Python 或 SymPy。
7. 设计 ReviewGate。
8. 设计 Tool Group 激活策略。
9. 设计权限模式。
10. 为 benchmark 保存可复现 trace。

## 当前结论

AgentScope 对 OpenO1 的启发可以概括为：

OpenO1 应该学习成熟 agent runtime 的工程控制能力，但核心创新必须放在结构化推理、自动验证、失败回滚、审阅门禁和继续策略上。
