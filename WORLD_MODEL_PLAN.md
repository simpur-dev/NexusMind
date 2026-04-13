# NexusMind 世界模型化改造方案

> 基于论文 *"From Individual to Society: A Survey on Social Simulation Driven by LLM-based Agents"* (Mou et al., ACM Computing Surveys, 2026) 的理论框架，结合本项目现有代码定制。

---

## 一、理论对标：论文框架 vs 本项目现状

论文将 LLM 驱动的社会模拟拆为三层（Individual → Scenario → Society），每层有明确的架构要素。下表是当前项目的对标分析：

### 1. Individual Simulation 层（§3）

| 论文要素 | 论文描述 | 本项目现状 | 差距 |
|---------|---------|-----------|------|
| **Profile** | 人设构建（描述/对话型），支持 LLM 生成 | ✅ `oasis_profile_generator.py` 已实现 LLM 生成人设，含 internal_goals + utility_weights | ✅ 已补齐 |
| **Memory** | 短期记忆 + 长期记忆，支持写入/检索/反思 | ⚠️ `graph_memory_updater.py` 仅做行为写入图谱，无记忆检索/反思 | 缺少 **记忆反思(reflection)** 和 **记忆检索影响决策** |
| **Planning** | 共情规划 + 主观规划（基于内部状态驱动） | ❌ 无。Agent 行为完全由 OASIS 引擎 + persona prompt 驱动 | 缺少 **目标驱动的规划层** |
| **Action** | 与环境的直接交互（对话/行为） | ✅ OASIS 平台已实现发帖/评论/点赞/转发等动作 | 基本满足 |

### 2. Scenario Simulation 层（§4）

| 论文要素 | 论文描述 | 本项目现状 | 差距 |
|---------|---------|-----------|------|
| **Environment Configuration** | 场景基本信息、目标、外部资源 | ✅ `simulation_config_generator.py` 用 LLM 生成配置 | 基本满足 |
| **Environment State** | 运行时环境即时状态，影响 Agent 决策 | ✅ `WorldStateEngine` 6维状态 + 文件IPC反馈闭环 + monkey-patch注入Agent prompt | ✅ 已实现 |
| **Environment History** | 历史状态积累，Agent 可回溯 | ✅ `world_state_history.jsonl` 持久化状态序列 + `events.jsonl` 事件流 | ✅ 已实现 |
| **Role** | 通信者/执行者/导演三类角色 | ⚠️ 所有 Agent 同质化，无功能分化 | 缺少 **特殊角色**（如观察者、干预者） |
| **Organization** | 层次/扁平/动态组织结构 | ❌ 无组织结构 | 暂不优先 |
| **Communication** | 受限通信协议 | ⚠️ 依赖 OASIS 平台机制 | 基本满足 |

### 3. Society Simulation 层（§5）

| 论文要素 | 论文描述 | 本项目现状 | 差距 |
|---------|---------|-----------|------|
| **Composition** | 人口组成多样性，含离群者建模 | ⚠️ 有实体多样性，但无 **意见领袖/离群者** 特殊建模 | 需补 |
| **Network** | 社交网络结构（线上/线下） | ⚠️ 依赖 OASIS 内置的平台关注机制 | 基本满足 |
| **Social Influence** | 信息级联、观点动力学、群体涌现 | ❌ **完全缺失**。无法追踪影响传播链 | **核心缺口** |
| **Evaluation (Macro)** | 宏观指标：传播规模、观点分布趋势 | ❌ 无宏观评估指标 | 需补 |

---

## 二、核心结论：本项目要补什么

基于上述对标，本项目要真正成为"世界模型"，**最关键的三个缺口**是：

1. **Environment State（环境状态层）** — 论文 §4.1.1 State
2. **Social Influence Tracking（社会影响追踪）** — 论文 §5.1.3
3. **Agent Internal Goal & Planning（Agent 目标与规划）** — 论文 §3.1.3

次要缺口：
4. Memory Reflection（记忆反思）
5. Macro-level Evaluation（宏观评估）
6. Special Role Modeling（特殊角色建模）

---

## 三、分阶段实施方案

### 第一阶段：环境状态引擎（World State Engine）

**论文依据**：§4.1.1 指出 "environment states record instant information from the environment during the scenario. They directly influence the agents' decision-making and behavior."

**目标**：让系统每轮产出一个可量化的世界状态快照。

#### 新增文件
- `backend/app/services/world_state.py`

#### 数据结构

```python
@dataclass
class WorldStateSnapshot:
    """世界状态快照 — 对应论文 §4.1.1 Environment State"""
    round_num: int
    timestamp: str
    
    # 核心状态变量（6 维）
    attention_level: float      # 关注度/热度 [0, 1]
    panic_level: float          # 恐慌/负面情绪 [0, 1]
    trust_level: float          # 对权威的信任度 [0, 1]
    polarization_level: float   # 立场极化程度 [0, 1]
    risk_level: float           # 综合风险等级 [0, 1]
    stability_level: float      # 系统稳定性 [0, 1]
    
    # 观测信号（用于推导状态变量）
    total_posts: int = 0
    total_comments: int = 0
    total_reposts: int = 0
    active_agent_count: int = 0
    top_keywords: List[str] = field(default_factory=list)
    sentiment_distribution: Dict[str, float] = field(default_factory=dict)  # positive/negative/neutral


@dataclass 
class WorldEvent:
    """世界事件 — 对应论文 §5.1.3 Social Influence 中的信息级联"""
    event_id: str
    round_num: int
    timestamp: str
    event_type: str     # topic_outbreak / heat_spike / sentiment_shift / 
                        # official_response / trust_drop / stabilization
    description: str
    severity: float     # [0, 1]
    source_actions: List[str] = field(default_factory=list)  # 触发该事件的动作 ID
    affected_variables: Dict[str, float] = field(default_factory=dict)  # 对状态变量的影响量


class WorldStateEngine:
    """世界状态引擎"""
    
    def update_state(self, round_num: int, actions: List[AgentAction], 
                     prev_state: Optional[WorldStateSnapshot]) -> WorldStateSnapshot:
        """基于本轮动作和上一轮状态，计算新的世界状态"""
        ...
    
    def detect_events(self, prev_state: WorldStateSnapshot, 
                      curr_state: WorldStateSnapshot, 
                      actions: List[AgentAction]) -> List[WorldEvent]:
        """检测本轮是否发生了关键事件"""
        ...
    
    def get_state_summary_for_agents(self, state: WorldStateSnapshot) -> str:
        """生成可注入 Agent prompt 的状态摘要文本"""
        ...
```

#### 状态更新逻辑（规则 + LLM 混合）

第一版采用**规则为主、LLM 为辅**的策略：

1. **规则层**（快速、确定性）：
   - `attention_level` ← 本轮发帖数/评论数相对均值的偏移
   - `panic_level` ← 负面关键词占比 + 转发加速度
   - `polarization_level` ← 正面与负面 sentiment 比例的方差

2. **LLM 层**（每 N 轮调用一次，做深层判断）：
   - 输入：本轮动作摘要 + 上一轮状态
   - 输出：`trust_level`、`risk_level`、`stability_level` 的调整量
   - 同时输出：是否触发关键事件

#### 挂载点
- **`simulation_runner.py` → `_read_action_log()`**：在 `round_end` 事件处触发 `world_state_engine.update_state()`
- **`simulation_runner.py` → `_monitor_simulation()`**：每轮保存状态到 `world_state_history.jsonl`
- **`SimulationRunState.to_dict()`**：增加 `current_world_state` 字段

#### 持久化
- `{sim_dir}/world_state_history.jsonl` — 每轮一行，JSONL 格式
- `{sim_dir}/events.jsonl` — 关键事件记录

---

### 第二阶段：动态因果图谱 MVP（Causal Event Graph）

**论文依据**：§5.1.3 指出社会影响包含 "information cascades"、"opinion dynamics"、"group emergence"，且 §8.3 Challenge (3) 明确指出 "LLM interpretability poses difficulty: the black-box nature of LLMs makes it hard to provide rigorous causal explanations for individual behaviors or collective outcomes"。

**目标**：让系统能表达"什么事件导致了什么状态变化"，提供**可解释性**。

#### 新增文件
- `backend/app/services/causal_graph.py`

#### 数据结构

```python
@dataclass
class CausalEdge:
    """因果边"""
    source_event_id: str        # 原因事件
    target_event_id: str        # 结果事件
    relation_type: str          # triggered / amplified / suppressed / shifted
    strength: float             # 因果强度 [0, 1]
    evidence: str               # 推断依据（文本）
    round_num: int
    timestamp: str


class CausalGraphEngine:
    """动态因果图谱引擎"""
    
    def infer_causal_edges(self, events: List[WorldEvent], 
                           state_history: List[WorldStateSnapshot]) -> List[CausalEdge]:
        """从事件序列和状态变化中推断因果关系"""
        ...
    
    def get_causal_chain(self, event_id: str) -> List[CausalEdge]:
        """获取某个事件的因果链条"""
        ...
    
    def get_influence_path(self, from_round: int, to_round: int) -> Dict:
        """获取两轮之间的影响传播路径"""
        ...
```

#### 因果推断逻辑

第一版只做**三类因果边**：

| 类型 | 触发条件 | 示例 |
|------|---------|------|
| `triggered` | 事件 A 发生后 1-2 轮内出现事件 B，且 B 的 affected_variables 与 A 相关 | `topic_outbreak` → `heat_spike` |
| `amplified` | 状态变量在事件后加速上升 | `influencer_repost` → `panic_level` 加速 |
| `suppressed` | 状态变量在事件后显著下降 | `official_response` → `panic_level` 下降 |

#### 持久化
- `{sim_dir}/causal_edges.jsonl`

#### 挂载点
- 在 `WorldStateEngine.detect_events()` 之后调用 `CausalGraphEngine.infer_causal_edges()`
- API: 新增 `GET /simulation/<id>/causal-graph` 接口

---

### 第三阶段：Agent 认知升级（Goal-Driven Agent）

**论文依据**：
- §3.1.3 Planning: "subjective planning involves an agent acting based on its own thoughts and feelings, in line with its role or identity"
- §3.1.2 Memory Reflection: "agents can synthesize fragmented experiences into coherent knowledge"
- §5.1.1 Composition: "outliers, i.e., individuals with highly distinct attributes, often exert significant influence"

**目标**：让 Agent 从"有人设的语言角色"升级为"有目标、有偏好、可评分的认知体"。

#### 修改文件
- `backend/app/services/oasis_profile_generator.py`

#### 扩展 OasisAgentProfile

```python
# 新增字段（追加到现有 OasisAgentProfile）
internal_goal: str = ""              # 内部目标（如 "扩大自身影响力"、"维护校园稳定"）
utility_weights: Dict[str, float] = field(default_factory=dict)
    # 示例: {"influence": 0.4, "safety": 0.3, "conformity": 0.2, "truth": 0.1}
risk_tolerance: float = 0.5         # 风险容忍度 [0, 1]
authority_trust: float = 0.5        # 对权威信任度 [0, 1]
emotion_sensitivity: float = 0.5    # 情绪敏感度 [0, 1]
is_opinion_leader: bool = False     # 是否为意见领袖（对应论文 outlier modeling）
```

#### Profile 生成 Prompt 改造

在 `generate_profile_from_entity()` 的 LLM prompt 中增加：

```
除了基本人设外，请为该角色生成以下认知属性：
1. internal_goal: 该角色在社交讨论中的核心目标（一句话）
2. utility_weights: 该角色在行动时的价值权重分配（influence/safety/conformity/truth，总和为 1）
3. risk_tolerance: 该角色愿意承担多大的社会风险（0-1）
4. authority_trust: 该角色对官方/权威信息的信任程度（0-1）
5. emotion_sensitivity: 该角色受情绪化内容影响的程度（0-1）
6. is_opinion_leader: 该角色是否具备意见领袖特征（true/false）
```

#### Agent 评分机制（轻量版 RLAIF）

每轮结束后，基于世界状态变化和 Agent 行为，给每个活跃 Agent 一个 `round_score`：

```python
@dataclass
class AgentRoundScore:
    agent_id: int
    round_num: int
    influence_score: float    # 本轮发帖被互动的程度
    goal_alignment: float     # 行为是否符合 internal_goal
    risk_taken: float         # 本轮行为的风险程度
    total_score: float        # 加权总分
```

#### 持久化
- `{sim_dir}/agent_scores.jsonl`

---

### 第四阶段：宏观观测与可视化（Multimodal Observer）

**论文依据**：
- §5.3 Evaluation: "macro-level outcomes show patterns and trends consistent with the real world"
- §8.3 Challenge (3): "developing more transparent and robust approaches at the intersection of LLMs and social science"

**目标**：让前端能展示世界状态演化、事件时间线、因果链。

#### 后端 API 新增

| 接口 | 返回内容 |
|------|---------|
| `GET /simulation/<id>/world-state` | 当前世界状态 + 状态历史列表 |
| `GET /simulation/<id>/events` | 事件时间线 |
| `GET /simulation/<id>/causal-graph` | 因果边列表 |
| `GET /simulation/<id>/agent-scores` | Agent 评分排行 |

#### 前端组件新增

1. **世界状态仪表盘** — 6 个指标的实时卡片 + 雷达图
2. **状态趋势图** — 每轮 6 维状态的折线图
3. **事件时间线** — 按轮次展示关键事件
4. **因果链视图** — 从某个事件出发，展示上下游影响链
5. **Agent 排行榜** — 按影响力/风险/目标达成度排序

---

## 四、文件清单与优先级

### P0 — 必做（世界状态引擎）
| 操作 | 文件 |
|------|------|
| 新建 | `backend/app/services/world_state.py` |
| 修改 | `backend/app/services/simulation_runner.py` — 在 round_end 挂载状态更新 |
| 修改 | `backend/app/services/__init__.py` — 导出新模块 |
| 修改 | `backend/app/api/simulation.py` — 新增 world-state API |

### P1 — 强烈建议做（动态因果图谱 + Agent 认知）
| 操作 | 文件 |
|------|------|
| 新建 | `backend/app/services/causal_graph.py` |
| 修改 | `backend/app/services/oasis_profile_generator.py` — 扩展 profile 字段 |
| 修改 | `backend/app/api/simulation.py` — 新增 causal-graph / events API |

### P2 — 建议做（前端可视化）
| 操作 | 文件 |
|------|------|
| 新建 | `frontend/src/components/WorldStatePanel.vue` |
| 修改 | `frontend/src/views/SimulationRunView.vue` — 集成状态面板 |

### P3 — 可后做
| 操作 | 说明 |
|------|------|
| 记忆反思 | 在 graph_memory_updater 中增加 reflection 逻辑 |
| 宏观评估 | 报告生成时引用世界状态历史 |

---

## 五、论文引用建议

在答辩/文档中可这样引用本论文：

> 本系统的世界模型化改造参考了 Mou et al. (2026) 提出的 "Individual → Scenario → Society" 三层社会模拟框架。在 **Environment State**（§4.1.1）层面，我们实现了多维世界状态引擎，使模拟环境具备可量化的即时状态；在 **Social Influence**（§5.1.3）层面，我们构建了轻量级动态因果图谱，为 LLM 驱动的社会模拟提供可解释的因果链条，回应了论文 §8.3 中提出的 "LLM 可解释性" 挑战；在 **Individual Architecture**（§3.1）层面，我们扩展了 Agent 的认知架构，增加了内部目标与效用权重，使 Agent 行为从 prompt-driven 升级为 goal-driven。

同时可引用的其他论文：
- **Park et al., 2023** [157] — Generative Agents（Agent 架构基线）
- **Gao et al., 2023** [56] — S³ Social-Network Simulation（OASIS 基础）
- **Ha & Schmidhuber, 2018** — World Models（世界模型概念来源）
- **Yang et al., 2024** [256] — OASIS（本项目使用的模拟框架）

---

## 六、一句话总结

**把 NexusMind 从 "GraphRAG + 多 Agent 模拟器" 升级为 "具备环境状态感知、事件因果追踪、目标驱动认知的可解释社会世界模型"，核心改造集中在 4 个本地文件（world_state.py, causal_graph.py, simulation_runner.py, oasis_profile_generator.py），不依赖 Neo4j，全部本地存储。**
