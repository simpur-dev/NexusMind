# NexusMind 世界模型化改造方案

> 基于 **SocioVerse、AgentSociety、GenSim、OASIS、MOSAIC、Rumor Spreading、Generative Agents、POSIM** 与 *"World Models Survey"* 的统一视角，结合本项目现有 OASIS + `WorldStateEngine` 架构定制。

---

## 一、论文统一后的世界模型定义

论文系统梳理后，本项目的 world model 不应只等于 `world_state.py` 里的全局 6 维状态，而应由四个相互耦合的层组成：

| 层级 | 论文依据 | 在 NexusMind 中的含义 |
|------|----------|----------------------|
| **Agent Prior / Persona Layer** | SocioVerse、MOSAIC、POSIM | `reddit_profiles.json` 中的人设、兴趣、立场、效用权重等稳定先验；这些字段必须持续参与模拟，而不是只作为首次 role-play 文本 |
| **Agent Cognitive State Layer** | POSIM、Rumor Spreading、Generative Agents | agent 在运行时对事件的 `belief / emotion / trust / attention / reflection` 等动态内部状态 |
| **Macro / Topic State Layer** | SocioVerse、AgentSociety、World Models Survey | 群体级环境状态、话题热度、叙事分裂、风险变化等外部世界 |
| **Personalized Perception Layer** | OASIS、MOSAIC | 同一外部世界对不同 agent 的渲染结果不同；agent 看到什么、如何理解，不应对所有人完全一致 |

### 1. 论文一致支持的核心闭环

```text
Profile / Persona P_i
    ↓ compile
Prior_i
    ↓
Perception_i^t = Render(W_t, T_t, C_i^t, Prior_i)
    ↓
Belief / Emotion Update C_i^{t+1}
    ↓
Action_i^t
    ↓ aggregate
Macro / Topic State (W_{t+1}, T_{t+1})
```

其中：

- **`W_t`**：宏观世界状态
- **`T_t`**：话题/叙事状态
- **`C_i^t`**：agent 认知状态

这意味着真正的 world model 不是单个全局 JSON，而是 **macro + topic + per-agent cognition** 的耦合系统。

### 2. 对 NexusMind 的直接含义

- **[人设定位]** `reddit_profiles.json` 生成的人设不是附属信息，而是 world model 的微观参数来源。
- **[共享快照]** 当前 `world_state_current.json` 不应只承载全局态摘要，后续应扩展为共享的 world-model snapshot，至少包含 `macro_state`、`topic_state` 与轻量 `agent_cognitive_state`。
- **[因果图谱顺序]** 因果图谱不宜前置；若没有个体认知层，只能解释“行为之后热度变了”，难以解释“哪类 agent 推动了叙事扩散”。
- **[宏观状态角色]** 现有 6 维状态仍有价值，但其角色应从“完整世界模型”调整为“宏观聚合层”。

---

## 二、现状诊断与核心缺口

| 模块 | 当前实现 | 论文对齐情况 | 主要问题 |
|------|----------|--------------|----------|
| **人设生成** | `oasis_profile_generator.py` 已生成 `internal_goals`、`utility_weights`、`initial_stance`、`emotional_tendency`、`susceptibility` 等字段 | 与 SocioVerse / POSIM / MOSAIC 的 persona 思想基本一致 | 这些字段仍主要停留在 profile JSON，尚未被编译成运行时微观参数 |
| **宏观世界状态** | `WorldStateEngine` 已实现 6 维状态、历史记录、文件 IPC 反馈闭环 | 与 Environment State 思想部分一致 | 目前主要依赖动作摘要和规则统计，对“谁在发声、以何种认知状态发声”建模不足 |
| **个性化感知** | `run_parallel_simulation.py` 已有基于 `entity_type/stance` 的轻量差异化 world-state prompt | 与 OASIS / MOSAIC 的 personalized perception 方向一致，但深度不够 | 差异化尚未接入 `reddit_profiles.json` 中更丰富的人设字段 |
| **个体认知状态** | 暂无显式 `belief / emotion / trust / attention` 状态层 | 与 POSIM / Rumor / Generative Agents 差距大 | 缺少“agent 如何理解世界”的运行时建模 |
| **记忆/反思** | `graph_memory_updater.py` 主要记录行为写入图谱 | 与 Generative Agents 的 memory/reflection 只局部对齐 | 缺少 reflection 与认知更新闭环 |
| **社会影响追踪** | `causal_edges.jsonl` 已有文件占位，但暂无论文一致的 micro→macro 因果解释层 | 与 SocioVerse / POSIM / World Model 可解释性要求不一致 | 需要建立在 agent cognition + topic state 之上，而不是只对宏观曲线连边 |

基于以上诊断，当前最需要优先补的不是更复杂的宏观指标，而是以下四项：

1. **Persona Prior Compiler**：把 profile 文本编译为可计算先验
2. **Agent Cognitive State**：显式维护 per-agent belief / emotion / trust / attention
3. **Personalized Perception**：让同一世界状态对不同 agent 呈现不同解释
4. **Profile-aware Aggregation**：让宏观状态更新考虑角色、立场、易感性差异

第二优先级再做：

5. **Causal Graph / Social Influence Tracking**
6. **Reflection / Evaluation Ladder / Visualization**

---

## 三、分阶段实施方案

> 实施顺序按论文思想重排：**先把 agent 人设编译为可计算先验，再补个体认知状态与个性化感知，最后再做因果图谱与解释层**。  
> 原因是：若没有 micro-level cognition，宏观因果图谱只能解释“帖子之后发生了什么”，不能解释“为什么是这类人推动了传播”。

### 第一阶段：Persona Prior Compiler（P0）

**论文依据**：

- SocioVerse / AgentSociety：profile 是行为引擎输入，而不是一次性 prompt 装饰
- MOSAIC / POSIM：persona 需要转换为稳定的 role identity 与心理先验
- OASIS：profile 还应影响 perception / recommendation，而非只影响 action wording

**目标**：把 `reddit_profiles.json` 与 `simulation_config.json` 编译成可计算的 `AgentPrior` 映射，作为模拟运行期的微观先验层。

**建议结构**：

- **[稳定身份]** `name`、`source_entity_type`、`role_type`
- **[兴趣偏好]** `interested_topics`
- **[目标价值]** `internal_goals`、`utility_weights`
- **[认知先验]** `initial_stance`、`emotional_tendency`、`susceptibility`
- **[行为配置映射]** 来自 `simulation_config.json` 的活跃度/影响力等平台配置，统一放入 `config_traits`

**建议修改文件**：

- **[修改]** `backend/app/services/oasis_profile_generator.py` — 保持现有人设字段稳定、可校验、可序列化
- **[建议新增]** `backend/app/services/agent_prior.py` — 编译 profile + config 到 `AgentPrior` 映射
- **[修改]** `backend/scripts/run_parallel_simulation.py` — 启动时加载 prior map

**建议产物**：

- `{sim_dir}/agent_priors.json`

**落地原则**：

- **[不新增重型推理]** 第一版不增加新的逐 agent LLM 调用，只做字段归一化与衍生特征编译
- **[先用已有字段]** 优先消费当前已经存在的 `internal_goals`、`utility_weights`、`initial_stance`、`emotional_tendency`、`susceptibility`

### 第二阶段：Agent 认知状态 + 个性化感知（P0，前移）

**论文依据**：

- POSIM：显式维护 `belief / desire / intention`
- Rumor Spreading：显式记录 agent 对 rumor / topic 的 belief
- OASIS / MOSAIC：环境感知必须个性化
- Generative Agents：perception → memory → reflection → action 是完整闭环

**目标**：新增最小可行的 `AgentCognitiveState`，让 agent 不再只是“带人设发帖”，而是“带内部状态理解世界并行动”。

**建议维护的状态**：

- **[话题信念]** `topic_beliefs: Dict[str, float]`
- **[情绪唤起]** `emotion_arousal: float`
- **[信任对象]** `trust_targets: Dict[str, float]`
- **[注意力焦点]** `attention_focus: List[str]`
- **[高层反思]** `last_reflection: str`
- **[更新时间]** `updated_round: int`

**建议修改文件**：

- **[建议新增]** `backend/app/services/agent_cognition.py` — 维护 per-agent 认知状态更新逻辑
- **[修改]** `backend/app/services/simulation_runner.py` — 在 `round_end` 后从动作日志更新活跃 agent 的认知状态
- **[修改]** `backend/scripts/run_parallel_simulation.py` — 在 `build_world_state_prompt()` 中联合 `AgentPrior + AgentCognitiveState` 生成 personalized perception

**共享状态文件策略**：

- **[沿用现有文件]** 继续使用 `world_state_current.json`
- **[扩展 schema]** 新增 `macro_state`、`topic_state`、`agent_cognitive_state` 三部分
- **[保持现有 monkey-patch]** 仍通过 `patch_oasis_environment()` 注入 prompt，不推翻当前 OASIS 接入路径

**首版个性化渲染规则**：

- **[高易感性]** `susceptibility` 高的 agent，更强调不确定性和情绪化信号
- **[高求真倾向]** `utility_weights.truth_seeking` 高的 agent，更强调证据缺口和事实澄清
- **[机构/媒体角色]** 更强调稳定、澄清、程序与权威信息
- **[话题不匹配]** 与 `interested_topics` 低相关的 topic，降低感知权重

**建议产物**：

- `{sim_dir}/agent_cognitive_current.json`
- `{sim_dir}/agent_cognitive_history.jsonl`

### 第三阶段：宏观世界状态 / 话题状态重构（P1）

**论文依据**：

- SocioVerse / AgentSociety：环境不仅是总热度，还包含 social environment 与 behavior engine 的耦合结果
- POSIM：公共舆论模拟需要 event/topic 层面的动态状态
- World Models Survey：world model 的核心是理解外部 dynamics 并支持未来状态推演

**目标**：保留现有 6 维宏观状态，但把它下沉为 `macro_state`，同时补上更贴近公共舆论事件的 `topic_state`。

**建议状态分层**：

| 层级 | 建议字段 | 说明 |
|------|----------|------|
| **Macro State** | `attention`、`panic`、`trust`、`polarization`、`risk`、`stability` | 保留现有 6 维，继续服务 dashboard 与全局反馈 |
| **Topic State** | `salience`、`uncertainty`、`hostility`、`official_trust`、`rumor_pressure`、`narrative_divergence` | 面向事件/叙事推演，更贴近公共舆论模拟语义 |

**核心改造点**：

- **[聚合输入升级]** 从“动作文本 + 全局统计”升级为“动作文本 + agent prior + agent cognition”
- **[群体摘要升级]** LLM refine prompt 不只看动作摘要，还看角色分布、立场簇、belief shift 摘要
- **[事件检测升级]** `WorldEvent` 不只描述热度变化，还描述话题级别的叙事转折

**建议修改文件**：

- **[修改]** `backend/app/services/world_state.py` — 从单一 6 维状态引擎扩展为 `macro_state + topic_state` 聚合器
- **[修改]** `backend/app/services/simulation_runner.py` — 每轮写入完整 snapshot 到共享文件与历史文件

**建议产物**：

- 继续沿用 `{sim_dir}/world_state_history.jsonl`，但改为嵌套保存 `macro_state` 与 `topic_state`
- 继续沿用 `{sim_dir}/events.jsonl`

### 第四阶段：社会影响追踪与因果图谱（P1）

**论文依据**：

- SocioVerse：社会影响包含 information cascades、opinion dynamics、group emergence
- POSIM：需要从 mechanism → phenomenon → statistics 逐层解释
- World Models Survey：世界模型不仅要表达现状，还要支持更强的可解释预测

**目标**：构建真正的 micro→macro 解释层，回答“什么人、以什么信念状态、通过什么动作路径，触发了哪类叙事变化”。

**第一版因果边建议**：

| 类型 | 示例 |
|------|------|
| `triggered` | `official_response` → `official_trust` 上升 |
| `amplified` | 高易感群体的负面转发 → `hostility` 放大 |
| `shifted` | 媒体澄清 → 某一簇 agent 的 `topic_beliefs` 反转 |
| `suppressed` | 机构声明 → susceptible cluster 的 `rumor_pressure` 下降 |

**建议修改文件**：

- **[建议新增]** `backend/app/services/causal_graph.py`
- **[修改]** `backend/app/api/simulation.py` — 暴露 `world-state / events / causal-graph` 查询接口

**前提说明**：

- **[必须后置]** 这一阶段必须建立在 `AgentPrior + AgentCognitiveState + TopicState` 已存在的基础上
- **[避免伪解释]** 若仍只有宏观曲线，因果图谱会退化成“帖子后面热度升高”的表面连边

**建议产物**：

- `{sim_dir}/causal_edges.jsonl`

### 第五阶段：记忆反思、评估与可视化（P2）

**论文依据**：

- Generative Agents：memory / reflection / planning 是 believable agent 的关键链路
- POSIM：机制层、现象层、统计层的 validation ladder
- World Models Survey：world model 最终要同时支持理解与预测

**目标**：让系统不只“能跑”，还要“能解释、能展示、能评估”。

**建议内容**：

- **[记忆反思]** 在 `agent_cognition.py` 或 `graph_memory_updater.py` 中加入定期反思摘要，更新 `last_reflection`
- **[机制层评估]** 记录曝光、激活、belief shift、群体差异
- **[现象层评估]** 记录 cascade、polarization、official response 效果
- **[统计层评估]** 对比宏观曲线、topic 曲线与真实事件证据或人工标注
- **[可视化]** 前端展示 macro/topic state、belief cluster、事件时间线、因果链

**建议后端接口**：

| 接口 | 返回内容 |
|------|---------|
| `GET /simulation/<id>/world-state` | 当前 world-model snapshot + 历史 |
| `GET /simulation/<id>/events` | 事件时间线 |
| `GET /simulation/<id>/causal-graph` | 因果边列表 |
| `GET /simulation/<id>/agent-cognition` | 认知状态摘要 / cluster 统计 |

**建议前端组件**：

1. **世界状态仪表盘** — `macro_state + topic_state` 卡片与趋势图
2. **认知簇视图** — 按角色/立场/易感性聚类展示 belief shift
3. **事件时间线** — 关键事件与叙事转折
4. **因果链视图** — 从事件、群体或状态变量出发查看影响路径
5. **评估面板** — mechanism / phenomenon / statistics 三层指标

---

## 四、文件清单与优先级

### P0 — 必做（让 agent 人设真正进入 world model）

| 操作 | 文件 | 作用 |
|------|------|------|
| 建议新增 | `backend/app/services/agent_prior.py` | 编译 `reddit_profiles.json + simulation_config.json` 为结构化 prior |
| 建议新增 | `backend/app/services/agent_cognition.py` | 维护 per-agent `belief / emotion / trust / attention` |
| 修改 | `backend/scripts/run_parallel_simulation.py` | 读取 prior / cognition，并渲染 personalized perception |
| 修改 | `backend/app/services/simulation_runner.py` | 在 `round_end` 后更新认知状态并写入共享 world-model snapshot |
| 修改 | `backend/app/services/world_state.py` | 从单一 6 维状态引擎扩展为 `macro_state + topic_state` 聚合器 |

### P1 — 强烈建议做（解释层与因果层）

| 操作 | 文件 | 作用 |
|------|------|------|
| 建议新增 | `backend/app/services/causal_graph.py` | 构建 micro→macro 因果解释层 |
| 修改 | `backend/app/api/simulation.py` | 暴露 `world-state / events / causal-graph / agent-cognition` API |
| 修改 | `backend/app/services/oasis_profile_generator.py` | 强化现有人设字段的稳定性、默认值与可校验性 |

### P2 — 建议做（可视化与评估）

| 操作 | 文件 | 作用 |
|------|------|------|
| 建议新增 | `frontend/src/components/WorldStatePanel.vue` | 展示 `macro_state + topic_state` |
| 建议新增 | `frontend/src/components/AgentCognitionPanel.vue` | 展示 belief cluster / role cluster |
| 修改 | `frontend/src/views/SimulationRunView.vue` | 集成 world model 可视化与评估面板 |

### P3 — 可后做（增强项）

| 操作 | 说明 |
|------|------|
| 记忆反思增强 | 在 `graph_memory_updater.py` 或 `agent_cognition.py` 中加入周期性 reflection |
| 角色分化增强 | 逐步补充媒体、机构、意见领袖等特殊角色建模 |
| 组织结构增强 | 若后续需要，再引入更复杂的层次/组织关系 |

---

## 五、论文引用建议

在答辩或文档中，更建议使用“多论文统一框架”的说法，而不是只引用单篇综述：

> 本系统的世界模型化改造综合吸收了多篇社会模拟研究的共同思想：SocioVerse 与 AgentSociety 将社会模拟理解为 **用户/agent 建模、社会环境建模、行为引擎耦合** 的统一系统；OASIS 与 MOSAIC 强调 **动态环境与个性化感知**；Rumor Spreading 与 POSIM 强调 **agent belief state 的显式建模**；Generative Agents 强调 **perception → memory → reflection → planning → action** 的内部闭环；World Models Survey 则将 world model 归纳为 **对外部 dynamics 的理解与对未来状态的推演能力**。基于这些论文，本项目将 world model 从单一宏观状态机，升级为 **persona prior + agent cognitive state + macro/topic state + personalized perception** 的耦合系统。

建议优先引用的论文方向：

- **[总体框架]** SocioVerse、AgentSociety
- **[平台与环境]** OASIS、MOSAIC、GenSim
- **[认知与信念]** POSIM、Rumor Spreading、Generative Agents
- **[世界模型总定义]** *World Models Survey*

---

## 六、一句话总结

**把 NexusMind 从“全局 `world_state` + persona prompt”的系统，升级为“persona prior + agent cognitive state + macro/topic state + personalized perception”的耦合社会世界模型；先补微观认知，再做宏观解释，才符合论文思想。**
