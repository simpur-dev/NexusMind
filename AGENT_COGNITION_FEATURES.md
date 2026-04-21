# Agent 认知四大功能 — 论文证据对照文档

> 生成日期: 2026-04-22  
> 涉及文件: `agent_brain.py`, `run_parallel_simulation.py`, `test_agent_brain.py`  
> 单元测试: **184 项全部通过**（含 35 项新增 Feature ①②③④ 测试）

---

## Feature ① 个性化感知渲染 (Personalized Perception)

### 论文证据

| 论文 | 章节 | 核心论点 | 对应实现 |
|------|------|----------|----------|
| **SocioVerse** | §2.1 Personalized Context | 同一环境对不同 agent 的渲染应不同，基于其社会角色和认知特征 | `render_personalized_perception()` 根据 `susceptibility`, `entity_type`, `conformity`, `risk_tolerance`, `utility_weights` 生成差异化环境信号 |
| **POSIM** | §3.2 BDI Belief Filter | Agents perceive environment signals through their belief lens; B_evt 层过滤外部信息 | 高易感性 Agent 放大不确定性/风险信号，高求真 Agent 强调证据缺口 |
| **OASIS** | Environment Design | 环境状态需以 agent 可感知的方式呈现，不同角色应有不同的信息获取路径 | 机构类 Agent 侧重稳定/秩序信号，媒体类侧重信息流速和线索 |
| **MOSAIC** | Agent Architecture | 多角色社会模拟中 agent 的感知模块应反映其社会功能 | 从众性高的 Agent 接收群体信号，风险厌恶 Agent 接收风险信号 |

### 实现细节

- **方法**: `AgentBrainRuntime.render_personalized_perception(agent_id, ws_data)`
- **注入点**: `run_parallel_simulation.py` → `patch_oasis_environment()` 中 `_patched_to_text_prompt`
- **感知维度**: susceptibility → 不确定性放大 | truth_seeking → 证据缺口 | entity_type → 角色专用信号 | conformity → 群体趋势 | risk_tolerance → 风险预警
- **安全设计**: 无个性化信号时返回空串，不注入噪声

### 测试覆盖 (8 项)

| 测试 | 验证点 |
|------|--------|
| `test_high_susceptibility_sees_uncertainty` | 高易感性 Agent 看到不确定性 |
| `test_high_truth_seeking_sees_evidence_gap` | 高求真 Agent 看到证据缺口 |
| `test_institution_sees_stability` | 机构角色看到稳定/关注度 |
| `test_media_sees_info_flow` | 媒体角色看到信息流 |
| `test_conformist_sees_group_signal` | 高从众 Agent 看到群体信号 |
| `test_risk_averse_sees_risk` | 风险厌恶 Agent 看到风险 |
| `test_no_signal_returns_empty` | 平静状态不注入噪声 |
| `test_unknown_agent_returns_empty` | 未知 Agent 安全降级 |

---

## Feature ② 立场漂移 (Stance Drift)

### 论文证据

| 论文 | 章节 | 核心论点 | 对应实现 |
|------|------|----------|----------|
| **POSIM** | §3.3 慢信念层 B_psy/B_id | 快信念层 (B_evt, B_emo) 累积影响慢信念层 (B_psy, B_id)；立场变化是累积过程，非瞬时翻转 | `_compute_drift_pressure()` 计算累积压力 → `_apply_stance_drift()` 在超过阈值时触发漂移 |
| **Rumor Spreading** | Belief State Model | Belief state 受社会曝光和影响累积变化；个体 susceptibility 调节变化速率 | `susceptibility` 作为压力放大系数 (0.7 + 0.6×susceptibility) |
| **AgentSociety** | Cognition Layer | Cognition 层包含信念更新机制，支持渐进式信念改变 | 累积压力带 0.85 衰减系数，模拟渐进过程 |
| **综述** | §8.3 Social Dynamics | Agent populations should replicate human social dynamics including opinion evolution | `_STANCE_ADJACENCY` 仅允许相邻档位漂移 (supportive↔neutral↔opposing) |

### 实现细节

- **漂移压力公式**:
  ```
  pressure = (emotional_arousal - 0.5) × 0.3
           + (0.5 - trust_in_authority) × 0.35
           + (perceived_risk - 0.4) × 0.2
           + polarization × 0.15
  pressure *= (0.7 + susceptibility × 0.6)
  ```
- **累积与衰减**: `stance_drift_pressure = old × 0.85 + new × 0.15`
- **触发阈值**: `|pressure| >= 0.6` 时允许漂移到相邻立场
- **安全约束**: 只能漂移到 `_STANCE_ADJACENCY` 中的相邻项，不可跳跃
- **漂移后重置**: 压力乘以 0.3，防止连续双跳
- **可追溯**: 每次漂移记录 `attribution_event`，包含 round, old→new, pressure

### 测试覆盖 (10 项)

| 测试 | 验证点 |
|------|--------|
| `test_adjacency_map_completeness` | 三种立场均有邻接定义 |
| `test_adjacency_only_neighbors` | 不可跳跃漂移 |
| `test_drift_pressure_high_emotion_positive` | 高情绪+低信任 → 正压力 |
| `test_drift_pressure_low_emotion_negative` | 低情绪+高信任 → 负压力 |
| `test_susceptibility_amplifies_pressure` | 高易感性放大压力 |
| `test_no_drift_below_threshold` | 低压力不触发 |
| `test_drift_triggers_at_threshold` | 超阈值触发漂移 |
| `test_drift_only_adjacent` | supportive 只能到 neutral |
| `test_drift_records_attribution_event` | 漂移记录归因事件 |
| `test_drift_integrated_in_apply_world_state` | 30 轮压力测试 |
| `test_initial_stance_preserved` | 初始立场记录正确 |

---

## Feature ③ 认知归因链 (Cognitive Attribution)

### 论文证据

| 论文 | 章节 | 核心论点 | 对应实现 |
|------|------|----------|----------|
| **POSIM** | §6 Mechanism Layer | 理性认知需要因果归因：agent 应能追溯"为什么我的状态变了" | 每轮对比 old/new 认知值，delta ≥ 0.08 时记录归因事件，标注 primary driver |
| **World Models Survey** | §8.3 Interpretability | 世界模型应提供可解释的因果链，支持下游分析 | `attribution_events` 列表持久化到 snapshot/summary，供 ReportAgent 检索 |
| **综述** | §8.3 Explainability | Agent 行为可解释性是社会模拟可信度的核心指标 | 每条归因包含 round, dimension, old, new, delta, primary_driver |

### 实现细节

- **驱动映射** (`_DRIVER_MAP`):
  - `emotional_arousal` ← panic_level, attention_level, polarization_level
  - `perceived_risk` ← risk_level, panic_level, trust_level
  - `trust_in_authority` ← trust_level, panic_level
  - `trust_in_peers` ← polarization_level, attention_level
  - `certainty` ← polarization_level, stability_level, panic_level
- **归因阈值**: delta ≥ 0.08 才记录（过滤噪声）
- **窗口限制**: 最多保留 30 条（FIFO）
- **primary_driver 选取**: 距中位值 0.5 偏离最大的世界状态维度

### 测试覆盖 (6 项)

| 测试 | 验证点 |
|------|--------|
| `test_attribution_generated_on_large_change` | 剧烈状态变化产生归因 |
| `test_attribution_has_required_fields` | 归因事件包含完整字段 |
| `test_no_attribution_on_small_change` | 平静状态不产生噪声归因 |
| `test_attribution_cap_at_30` | 50 轮震荡后不超过 30 条 |
| `test_attribution_in_cognition_snapshot` | 快照中包含 attribution_count |
| `test_attribution_in_cognition_summary` | 摘要中包含 attribution_events |

---

## Feature ④ 反思机制 (Reflection)

### 论文证据

| 论文 | 章节 | 核心论点 | 对应实现 |
|------|------|----------|----------|
| **Generative Agents** | §4.3 Reflection | Reflection 是 believable agent 三大支柱之一 (Perception → Memory → **Reflection** → Planning → Action)；周期性高层抽象提升行为一致性 | `trigger_reflection()` 每 3 轮触发；`_generate_reflection()` 分析行为模式、认知变化和策略-目标一致性 |
| **POSIM** | §6 Rational Cognition | 理性认知干预本质上是让 agent 进行自我审视：识别自身情绪-行为错位并校正 | 检测信任-行为错位（低信任+维稳 / 高信任+质疑）|
| **AgentSociety** | Cognition Layer | Cognition 层包含周期性自我评估，agent 对自身行为模式进行元认知 | 检测连续主动/被动模式、认知维度变化趋势 |

### 实现细节

- **触发间隔**: 每 `_REFLECTION_INTERVAL = 3` 轮触发一次（round 0 除外）
- **反思维度**:
  1. **行为一致性**: 连续 N 轮主动发帖 / 被动观望
  2. **认知变化感知**: 近 N 轮内哪些认知维度发生了归因级变化
  3. **策略-目标一致性**: challenge 策略 + 稳定目标 = 张力
  4. **信任-行为错位**: 低信任 + 维稳表达 / 高信任 + 质疑表达
- **存储**: `reflection_log` (state 层，最多 10 条) + `memory_scaffold["reflection_log"]`
- **Prompt 注入**: `render_prompt()` 末尾追加 `近期自我反思: ...`
- **模拟集成**: 两个主循环均在 `record_actions` 后调用 `trigger_reflection`

### 测试覆盖 (9 项)

| 测试 | 验证点 |
|------|--------|
| `test_reflection_not_triggered_at_round_0` | Round 0 不触发 |
| `test_reflection_triggered_at_interval` | 间隔轮次触发 |
| `test_reflection_detects_active_pattern` | 检测连续主动发帖 |
| `test_reflection_detects_passive_pattern` | 检测连续被动观望 |
| `test_reflection_detects_trust_behavior_mismatch` | 检测信任-行为错位 |
| `test_reflection_detects_cognitive_change` | 检测归因级认知变化 |
| `test_reflection_stored_in_state_and_memory` | 反思存储到两层 |
| `test_reflection_cap_at_10` | 反思日志不超过 10 条 |
| `test_reflection_in_render_prompt` | Prompt 中包含反思 |
| `test_no_reflection_without_actions` | 无行动不产生反思 |

---

## 数据流总览

```
世界状态 (ws_data)
    │
    ├─→ apply_world_state()
    │       ├── 认知状态更新 (原有)
    │       ├── Feature ③: 认知归因 → attribution_events[]
    │       └── Feature ②: 立场漂移 → stance_drift_pressure → prior.stance
    │
    ├─→ render_personalized_perception()  ← Feature ①
    │       └── 基于 prior 特征生成差异化环境信号 → Agent prompt
    │
    ├─→ record_actions()
    │       └── 更新 memory_scaffold.recent_actions
    │
    └─→ trigger_reflection()  ← Feature ④
            └── 基于行为+归因+策略生成反思 → reflection_log → Agent prompt

输出链:
    write_cognition_snapshot() → agent_cognition_history.jsonl
    generate_cognition_summary() → agent_cognition_summary.json
        ↓
    SimulationInsightService.get_agent_cognition_analysis()
        ↓
    ReportAgent: agent_cognition_analysis 工具
```

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `agent_brain.py` | 新增方法/函数 | `render_personalized_perception()`, `_compute_drift_pressure()`, `_apply_stance_drift()`, `_generate_reflection()`, `trigger_reflection()` |
| `agent_brain.py` | 扩展数据结构 | `AgentPrior.initial_stance`, `AgentCognitiveState.stance_drift_pressure/attribution_events/reflection_log` |
| `agent_brain.py` | 修改方法 | `apply_world_state()` 集成归因+漂移, `render_prompt()` 集成反思, snapshot/summary 扩展字段 |
| `run_parallel_simulation.py` | 集成调用 | `patch_oasis_environment()` 注入个性化感知, 主循环加 `trigger_reflection()` |
| `test_agent_brain.py` | 新增 35 项测试 | `TestPersonalizedPerception(8)`, `TestStanceDrift(10)`, `TestCognitiveAttribution(6)`, `TestReflection(9)` + 2 helper |
