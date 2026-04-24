# NexusMind 世界模型优化方案（十大方向）

> 更新日期: 2026-04-23
> 基于 **SocioVerse、AgentSociety、OASIS、MOSAIC、Rumor Spreading、Generative Agents、POSIM** 与 *World Models Comprehensive Survey* 的全面代码扫描与论文交叉分析。
> 涉及核心文件: `world_state.py`, `agent_brain.py`, `causal_graph.py`, `run_parallel_simulation.py`, `simulation_runner.py`, `evaluation.py`, `simulation_insight_service.py`

---

## 〇、已完成 vs 原计划对照

| 计划层级 | 计划状态 | 当前实现 |
|----------|----------|----------|
| P0: AgentPrior 编译 | ✅ 已完成 | `agent_brain.py` → `AgentPrior` dataclass |
| P0: AgentCognitiveState | ✅ 已完成 | 5 维认知 + 归因 + 反思 + 立场漂移 |
| P0: 个性化感知 | ✅ 已完成 | `render_personalized_perception()` |
| P1: 因果图谱 | ✅ 已完成 | `causal_graph.py` 模板 + LLM 双层 |
| **P1: Topic State 层** | ❌ **未做** | 宏观仍只有 6 维 macro，无 topic 级粒度 |
| **P1: Profile-aware 聚合** | ⚠️ 部分 | 宏观状态更新仍基于动作统计 + 关键词，未按角色加权 |
| P2: 记忆/反思 | ✅ 部分 | 规则驱动反思已有，LLM 深层反思未做 |
| P2: 可视化 | ⚠️ 边栏 | 无独立世界模型展示视图 |
| P3: 记忆流增强 | ❌ 未做 | 无 Generative Agents 式长期记忆流 |

---

## 一、补充 Topic State 层（原计划第三阶段未完成）

**优先级**: 🔴 高 — 核心架构升级

### 现状问题

`world_state.py` 只维护 6 维 macro 状态（attention, panic, trust, polarization, risk, stability），无法区分**不同话题/叙事线**的独立演化。例如"图书馆事件"和"校园安全讨论"在同一模拟中会混为一谈。

### 论文依据

- **SocioVerse §2.1**: Social Environment 包含 topic-level dynamics，同一场景下不同话题有独立的热度与分歧
- **POSIM**: 公共舆论模拟需要 event/topic 层面的动态状态
- **World Models Survey**: world model 的核心是理解外部 dynamics 并支持未来状态推演

### 建议实现

新增 `TopicState` 数据结构，在 `world_state.py` 中按话题分别追踪状态：

```python
@dataclass
class TopicState:
    topic_id: str                    # 话题标识（LLM 抽取或关键词聚类）
    salience: float = 0.0            # 话题显著度
    uncertainty: float = 0.5         # 信息不确定性
    hostility: float = 0.0          # 敌意浓度
    official_trust: float = 0.5     # 对该话题官方回应的信任
    rumor_pressure: float = 0.0     # 谣言压力
    narrative_divergence: float = 0.0  # 叙事分裂度
```

在 `update_state()` 中用 LLM 抽取当前活跃话题，分话题追踪状态。

### 修改文件

- **[修改]** `backend/app/services/world_state.py` — 新增 `TopicState`，`WorldStateSnapshot` 嵌套保存 `topics: List[TopicState]`
- **[修改]** `backend/app/services/simulation_runner.py` — 每轮写入完整 snapshot 含 topic 数据
- **[修改]** `backend/scripts/run_parallel_simulation.py` — `build_world_state_prompt()` 中增加 topic 级信号

### 价值

让因果图谱可以回答"**哪个子话题**引起了信任下降"而非只有"某轮信任下降"。

---

## 二、Profile-aware 宏观状态聚合

**优先级**: 🔴 高 — 小改动高收益

### 现状问题

`_extract_observations()` 只做动作类型计数 + 关键词匹配，**不区分发帖者的角色和认知状态**。一个机构账号的官方声明和一个普通用户的情绪发泄对 `trust_level` 的影响应该不同，但目前被等权计算。

### 论文依据

- **AgentSociety**: behavior engine 耦合 agent 属性，不同角色对群体动态贡献不同
- **MOSAIC**: 不同角色对信息传播的权重不同
- **SocioVerse**: Social Structure 影响 Social Dynamics

### 建议实现

在 `_compute_state_by_rules()` 中，将每条动作按 `entity_type + influence_weight + stance` 加权：

```python
# 当前（未加权）
neg_ratio = neg_count / max(total, 1)

# 优化（加权）
for action in actions:
    weight = action.get("influence_weight", 1.0)
    entity_type = action.get("entity_type", "individual")
    # 媒体/机构的发言权重 ×2，意见领袖 ×1.5
    if entity_type in {"mediaoutlet", "university", "governmentagency"}:
        weight *= 2.0
    elif action.get("is_opinion_leader"):
        weight *= 1.5
    weighted_neg += weight * neg_score(action["content"])
```

### 修改文件

- **[修改]** `backend/app/services/world_state.py` → `_extract_observations()` 与 `_compute_state_by_rules()`
- **[修改]** `backend/app/services/simulation_runner.py` — 在传递动作数据时附带 agent 的 `entity_type` 和 `influence_weight`

---

## 三、认知衰减与自然遗忘机制

**优先级**: 🔴 高 — 改动极小，立竿见影

### 现状问题

`AgentCognitiveState` 的情绪/风险/信任等值只会被世界状态推动更新（`apply_world_state()`），但**没有自然衰减**。现实中，即使无新刺激，agent 的恐慌也会随时间消退，情绪不会永远维持在高位。

### 论文依据

- **Generative Agents §4.2**: Memory 有 recency decay，越久远的记忆影响越弱
- **POSIM §3.3**: 快信念层 B_evt / B_emo 有时间衰减特性
- **Rumor Spreading**: Agent 的 belief state 在无新曝光时自然衰退

### 建议实现

在 `apply_world_state()` 每轮开始时先执行自然衰减，再做世界状态驱动的更新：

```python
# 情绪自然衰减（无外部刺激时向中位值回归）
DECAY_RATE = 0.05
BASELINE = {
    "emotional_arousal": 0.3,
    "perceived_risk": 0.25,
    "trust_in_authority": 0.5,  # 信任回归较慢
    "trust_in_peers": 0.5,
    "certainty": 0.5,
}

for attr, baseline in BASELINE.items():
    current = getattr(state, attr)
    decayed = current + (baseline - current) * DECAY_RATE
    setattr(state, attr, decayed)
```

### 修改文件

- **[修改]** `backend/app/services/agent_brain.py` → `apply_world_state()` 开头新增衰减逻辑
- 可选：衰减速率可按 `decision_style` 差异化（rational 型衰减更快，emotional 型衰减更慢）

---

## 四、社会影响建模（Agent 间传播追踪）

**优先级**: 🔴 高 — 答辩展示价值大

### 现状问题

当前因果图谱只连接**事件 → 事件**（如 `heat_spike → trust_drop`），没有建模 **Agent → Agent 信息传播**路径。转发/评论行为的**链式传播**未被追踪——无法回答"谁影响了谁"。

### 论文依据

- **SocioVerse §5.1.3**: Information Cascades 是核心社会影响机制
- **Rumor Spreading**: Agent 间的信念传播是核心建模对象，传播图结构决定谣言扩散速度
- **OASIS**: Social network structure affects information flow

### 建议实现

在 `_extract_observations()` 中追踪回复/转发关系构建**影响图**：

```python
@dataclass
class SocialInfluenceEdge:
    source_agent_id: int       # 被转发/引用者
    target_agent_id: int       # 转发/评论者
    interaction_type: str      # repost / comment / quote
    round_num: int
    content_sentiment: str     # positive / negative / neutral
```

新增 `SocialInfluenceTracker`：
- 统计谁影响了谁、哪个角色是传播枢纽
- 识别信息级联路径（A → B → C → D）
- 持久化到 `{sim_dir}/social_influence.jsonl`

### 修改文件

- **[新增]** `backend/app/services/social_influence.py` 或集成到 `causal_graph.py`
- **[修改]** `backend/app/services/world_state.py` → `_extract_observations()` 提取交互关系
- **[修改]** `backend/app/services/simulation_insight_service.py` — 新增影响力网络分析工具

### 价值

报告可以回答"**媒体角色的转发使恐慌从学生群体扩散到公众**"，远超当前"某轮恐慌上升"的粗粒度。

---

## 五、LLM 深层反思（升级 Feature ④）

**优先级**: 🟡 中 — 提升 Agent 可信度

### 现状问题

`_generate_reflection()` 完全基于规则（检测行为一致性、策略-目标冲突等），**不调用 LLM**。反思内容模板化程度高，例如"我注意到自己的情绪变化较大"——believability 有限。

### 论文依据

- **Generative Agents §4.3**: Reflection 需要**高层抽象**能力，是 believable agent 三大支柱之一
- **POSIM §6**: Rational Cognition 本质是让 agent 进行深层自我审视
- **AgentSociety**: Cognition 层包含周期性自我评估

### 建议实现

每 N 轮（如 5-6 轮）对关键 Agent（影响力 Top K）调用一次 LLM 反思：

```python
async def _llm_reflection(brain: AgentBrain, round_num: int) -> str:
    recent = brain.memory_scaffold.get("recent_actions", [])[-5:]
    prompt = f"""你是{brain.entity_name}（{brain.prior.profession}），立场：{brain.prior.stance}。
最近你做了以下事情：
{format_actions(recent)}
你当前情绪唤醒度 {brain.current_state.emotional_arousal:.1f}，
对权威信任 {brain.current_state.trust_in_authority:.1f}。
请用一句话总结你对当前局势的最新看法和下一步打算。"""
    return await call_llm(prompt)
```

**开销控制**:
- 只对 Top 5 影响力 Agent 做 LLM 反思，其余继续用规则
- 反思间隔从 3 轮增加到 5-6 轮
- 使用轻量模型（如 qwen-turbo）而非主模型

### 修改文件

- **[修改]** `backend/app/services/agent_brain.py` → `_generate_reflection()` 增加 LLM 路径
- **[修改]** `backend/scripts/run_parallel_simulation.py` — 异步调用 LLM 反思

---

## 六、滑动窗口多轮事件检测（Hawkes 过程启发）

**优先级**: 🔴 高 — 改动极小，TCS 评分直接提升

### 现状问题

事件检测（`_detect_events()`）只看**相邻两轮的 delta**，无法捕捉**持续多轮的缓慢累积性危机**。例如信任持续微降 5 轮，每轮 delta < 阈值（0.12），但累计下降 0.3——这种"温水煮青蛙"式危机完全被忽略。

Benchmark `case_01` 的 TCS 第 2 阶段（`negative_peak`）得分为 **0**，正是因为峰值由多轮累积形成。

### 论文依据

- **POSIM**: 使用 Hawkes 时序模型捕捉事件间的自激发效应
- **World Models Survey**: World model 应具备预测能力而非仅响应当前 delta

### 建议实现

在 `_detect_events()` 中新增滑动窗口累积检测：

```python
# 滑动窗口累积检测（3-5 轮窗口）
if len(self._state_history) >= 4:
    recent_4 = self._state_history[-4:]
    
    # 持续信任侵蚀
    trust_trend = recent_4[-1].trust_level - recent_4[0].trust_level
    if trust_trend < -0.15:
        events.append(WorldEvent(
            event_id=self._gen_event_id(),
            round_num=curr.round_num,
            timestamp=now,
            event_type="sustained_trust_erosion",
            description=f"信任度持续下滑 ({recent_4[0].trust_level:.2f} → {recent_4[-1].trust_level:.2f}，跨 {len(recent_4)} 轮)",
            severity=min(1.0, abs(trust_trend) * 2),
            affected_variables={"trust_level": trust_trend},
        ))
    
    # 持续恐慌攀升
    panic_trend = recent_4[-1].panic_level - recent_4[0].panic_level
    if panic_trend > 0.15:
        events.append(WorldEvent(
            event_id=self._gen_event_id(),
            round_num=curr.round_num,
            timestamp=now,
            event_type="sustained_panic_rise",
            description=f"负面情绪持续蔓延 ({recent_4[0].panic_level:.2f} → {recent_4[-1].panic_level:.2f}，跨 {len(recent_4)} 轮)",
            severity=min(1.0, panic_trend * 2),
            affected_variables={"panic_level": panic_trend},
        ))

# 危险组合预警（预测性事件）
if curr.attention_level > 0.6 and curr.trust_level < 0.35:
    events.append(WorldEvent(
        event_id=self._gen_event_id(),
        round_num=curr.round_num,
        timestamp=now,
        event_type="secondary_crisis_risk",
        description=f"高关注({curr.attention_level:.2f}) + 低信任({curr.trust_level:.2f}) 组合，二次危机风险升高",
        severity=0.7,
        affected_variables={"attention_level": curr.attention_level, "trust_level": curr.trust_level},
    ))
```

### 修改文件

- **[修改]** `backend/app/services/world_state.py` → `_detect_events()` 新增滑动窗口检测
- **[修改]** `backend/app/services/causal_graph.py` → `CAUSAL_TEMPLATES` 新增对应边类型

---

## 七、认知簇分析与群体涌现检测

**优先级**: 🟡 中 — 答辩展示价值大

### 现状问题

`simulation_insight_service.py` 的 `get_agent_cognition_analysis()` 只做个体级统计（策略转换次数、情绪峰值），**没有群体级涌现分析**。例如"所有 opposing 立场的 Agent 在第 8 轮后集体转为 challenge 策略"这种群体现象无法被自动识别。

### 论文依据

- **SocioVerse §5.1.3**: Group Emergence 是社会模拟核心现象
- **AgentSociety**: 需要从 individual behavior 聚合出 collective pattern
- **World Models Survey §8.3**: 集体行为可解释性

### 建议实现

在 `get_agent_cognition_analysis()` 中新增群体分析：

```python
# 按 stance × entity_type 分组的认知均值演化
def _compute_cognition_clusters(self) -> Dict:
    clusters = defaultdict(lambda: {"count": 0, "emotion_sum": 0, "trust_sum": 0})
    for record in self.cognition_history[-1:]:  # 最后一轮
        for agent in record.get("agents", []):
            key = f"{agent.get('stance', 'unknown')}_{agent.get('entity_type', 'individual')}"
            clusters[key]["count"] += 1
            clusters[key]["emotion_sum"] += agent.get("emotional_arousal", 0)
            clusters[key]["trust_sum"] += agent.get("trust_in_authority", 0.5)
    # 计算均值
    for k, v in clusters.items():
        n = max(v["count"], 1)
        v["emotion_mean"] = round(v["emotion_sum"] / n, 3)
        v["trust_mean"] = round(v["trust_sum"] / n, 3)
    return dict(clusters)

# 群体极化检测
def _detect_group_polarization(self) -> Optional[str]:
    # 两个最大立场簇的情绪/信任差异是否在扩大
    ...

# 涌现事件检测
def _detect_collective_strategy_shift(self) -> List[Dict]:
    # 同一轮 3+ 个同立场 Agent 同时转换策略
    ...
```

### 修改文件

- **[修改]** `backend/app/services/simulation_insight_service.py` → `get_agent_cognition_analysis()` 新增群体分析
- **[修改]** `backend/app/services/causal_graph.py` — 新增群体涌现类型的因果边

---

## 八、世界模型注入的自适应阻尼

**优先级**: 🟡 中 — 改动极小，稳定性提升

### 现状问题

`build_world_state_prompt()` 的注入阈值是**硬编码** `deviation < 0.15`，不随模拟规模、话题类型自适应。100 个 Agent 的模拟和 20 个 Agent 的模拟使用相同阈值，前者的自然涌现信号更强，应该用更高阈值。

### 论文依据

- **POSIM §6 Empathy Paradox**: 注入强度必须精确控制，过强导致 NER 单调放大
- **v6 → v7 教训**: v6 加入"强烈地"强度档和 acute_crisis 放大器，胜率从 61% **下降**到 56%

### 建议实现

```python
def _compute_adaptive_threshold(
    base_threshold: float = 0.15,
    total_agents: int = 30,
    round_num: int = 1,
    polarization: float = 0.3,
) -> float:
    # Agent 数量因子：Agent 越多，自然涌现信号越强，阈值应更高
    agent_factor = max(0.8, min(1.5, total_agents / 30))
    
    # 轮次因子：前 5 轮更保守（让 Agent 先自由表达），后期逐步介入
    round_factor = min(1.0, round_num / 5)
    
    # 极化因子：高极化场景增大阈值（避免世界模型压制自然涌现）
    polarization_factor = 1.0 + max(0, polarization - 0.4) * 0.5
    
    return base_threshold * agent_factor * polarization_factor / max(round_factor, 0.5)
```

### 修改文件

- **[修改]** `backend/scripts/run_parallel_simulation.py` → `build_world_state_prompt()` 中替换硬编码阈值

---

## 九、Benchmark 多案例覆盖与 TCS 峰值修复

**优先级**: 🔴 高 — 科学验证核心短板

### 现状问题

目前只有 `case_01_wuhan_university_library` 一个 benchmark 案例（88.8/100），**缺乏多场景验证**。评委会质疑泛化性。

具体评分弱点：
- **TCS 第 2 阶段**（`negative_peak`）得分为 **0** — 模拟的峰值时机未命中真实数据
- **TPH** = 83.3 — 6 个转折点只命中了 5 个

### 建议行动

**新增 Benchmark 案例**:
- `case_02`: 商业品牌危机事件（如食品安全事件）
- `case_03`: 政策争议事件（如教育改革争议）
- `case_04`: 学术不端/科研伦理事件

**TCS 峰值修复**:
- 降低 `SMOOTHING_FACTOR`（当前 0.3），让状态变化更灵敏
- 在 LLM refine 中对极端信号更敏感
- 方向 ⑥（滑动窗口事件检测）可间接提升 TCS

### 修改文件

- **[新增]** `benchmark/case_02_*/`, `benchmark/case_03_*/` 等案例目录
- **[修改]** `backend/app/services/world_state.py` — 调优 `SMOOTHING_FACTOR` 和 LLM refine prompt

---

## 十、世界模型可学习化（远期方向）

**优先级**: 🟢 低 — 长期技术演进

### 现状问题

所有状态更新公式（权重、系数、阈值）都是**手工调参**：
- `SMOOTHING_FACTOR = 0.3`
- `attention_target = min(1.0, activity_ratio * 0.4)`
- `panic_target = clamp(neg_ratio * 0.6 + keyword_boost * 0.4 ...)`
- `EVENT_THRESHOLDS = {"heat_spike": 0.15, ...}`

无法从数据中学习最优参数组合，每换一个话题类型都可能需要重新调参。

### 论文依据

- **World Models Survey §3**: World model 的核心趋势是从 rule-based 向 learned models 演进
- **AgentSociety**: 使用 LLM 作为隐式世界模型，但 NexusMind 的规则层可以做显式参数学习

### 建议实现（远期）

1. **参数自动调优**: 用 Benchmark 的 TCS/TPH 评分作为目标函数，用 Optuna/Bayesian Optimization 搜索最优参数
2. **轻量 MLP 替代规则层**: 用历史模拟数据训练一个 MLP 替代 `_compute_state_by_rules()` 中的手工公式
3. **在线学习**: 每完成一次有标注的 Benchmark 模拟，更新模型参数

```python
# 远期：用 Optuna 搜索最优世界模型参数
import optuna

def objective(trial):
    smoothing = trial.suggest_float("smoothing", 0.1, 0.5)
    panic_weight = trial.suggest_float("panic_weight", 0.3, 0.8)
    ...
    score = run_benchmark_and_evaluate(smoothing, panic_weight, ...)
    return score["TCS"]

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=100)
```

### 修改文件

- **[新增]** `backend/scripts/optimize_world_model.py` — 参数搜索脚本
- **[修改]** `backend/app/services/world_state.py` — 将硬编码参数抽取为可配置项

---

## 快速改进收益矩阵

| # | 方向 | 改动量 | Benchmark 提升 | 答辩展示 | 论文支撑 |
|---|------|--------|----------------|---------|---------|
| ① | Topic State 层 | 中 | 🔴 高 | 🔴 高 | SocioVerse / POSIM |
| ② | Profile-aware 聚合 | 小 | 🟡 中 | 🟡 中 | AgentSociety / MOSAIC |
| ③ | 认知衰减 | **极小** | 🟡 中 | 🟢 低 | GA / POSIM |
| ④ | 社会网络影响 | 中 | 🟡 中 | 🔴 高 | SocioVerse / Rumor |
| ⑤ | LLM 深层反思 | 小 | 🟢 低 | 🟡 中 | GA §4.3 |
| ⑥ | 滑动窗口事件检测 | **极小** | 🔴 高 (TCS↑) | 🟢 低 | POSIM Hawkes |
| ⑦ | 认知簇涌现 | 小 | 🟢 低 | 🔴 高 | SocioVerse §5.1.3 |
| ⑧ | 自适应阻尼 | **极小** | 🟡 中 | 🟢 低 | POSIM §6 |
| ⑨ | 多 Benchmark | 中 | 🔴 高 | 🔴 高 | — |
| ⑩ | 可学习化 | 大 | 🔴 高 | 🟡 中 | World Models Survey |

---

## 推荐实施路径

### 第一批（1-2 天，极小改动高回报）

1. **⑥ 滑动窗口事件检测** — `_detect_events()` 新增 20 行代码
2. **③ 认知衰减** — `apply_world_state()` 新增 10 行衰减逻辑
3. **⑧ 自适应阻尼** — `build_world_state_prompt()` 替换 1 个阈值

### 第二批（3-5 天，中等改动）

4. **② Profile-aware 聚合** — `_extract_observations()` 加权改造
5. **⑦ 认知簇涌现** — InsightService 新增群体分析方法
6. **⑤ LLM 深层反思** — 对 Top K Agent 增加 LLM 路径

### 第三批（1-2 周，架构升级）

7. **① Topic State 层** — 核心架构升级
8. **④ 社会网络影响** — 新增影响力追踪模块
9. **⑨ 多 Benchmark** — 新增 2-3 个验证案例

### 远期

10. **⑩ 可学习化** — 参数自动搜索与模型化

---

## 论文引用建议

在答辩或文档中，建议按优化方向引用对应论文：

| 优化方向 | 主要引用 |
|----------|---------|
| Topic State / Profile-aware | SocioVerse §2.1, AgentSociety |
| 认知衰减 / 反思 | Generative Agents §4.2-4.3, POSIM §3.3 |
| 社会网络影响 | SocioVerse §5.1.3, Rumor Spreading |
| 事件检测增强 | POSIM Hawkes Process |
| 自适应阻尼 | POSIM §6 Empathy Paradox |
| 可学习化 | World Models Comprehensive Survey §3 |

---

## 一句话总结

**NexusMind 世界模型已完成 AgentPrior + CognitiveState + PersonalizedPerception + CausalGraph 四层架构；下一阶段重点是补 Topic State 层、加 Profile-aware 聚合、增强多轮事件检测与社会网络影响追踪，从"能跑通"升级为"能解释、能预测、能泛化"。**
