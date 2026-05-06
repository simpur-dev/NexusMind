# NexusMind 世界模型工作进展

> 更新时间：2026-05-05  
> 项目定位：基于社会世界模型的多智能体舆情推演与决策辅助系统  
> 当前状态：已形成“材料接入—图谱构建—Agent 建模—态势推演—报告生成—Benchmark 验证”的完整演示链路。

---

## 一、当前项目定位

NexusMind 当前不应被表述为“纯盲测预测系统”，而应表述为：

> 用户在公共事件早期提交当前已知种子材料，系统据此构建事实基线和数字社会沙盘，推演未来可能走势；随着现实事件继续发展，用户继续追加材料，系统滚动重建基线、校准预测分支，并输出新的决策简报。

这个定位更符合当前代码能力，也更适合答辩：

- 输入来源可追溯
- 推演过程可观察
- 报告结果可解释
- 真实案例可评分
- 新材料可滚动更新

---

## 二、论文与技术来源

项目吸收了以下方向的思想，建议表述为“基于多篇社会模拟与世界模型论文的工程化整合与扩展”。

| 来源 | 在 NexusMind 中的对应能力 |
|---|---|
| SocioVerse / Social World Model | 社会环境、宏观状态、群体动态、个性化上下文 |
| CAMEL-AI OASIS | 双平台社交互动模拟底座 |
| AgentSociety | Agent 画像、认知状态、群体行为建模 |
| Generative Agents | 记忆、反思、行为可信度启发 |
| POSIM / 公共舆论模拟 | 立场漂移、风险感知、理性认知、舆论反馈 |
| World Models Survey | 世界模型作为外部状态理解与未来状态推演框架 |

论文原件在：

```text
word_modle/papers/social_world_model/paper/
```

---

## 三、核心模块进展

| 层级 | 状态 | 说明 |
|---|---|---|
| 前端五步流程 | ✅ 已完成 | Home → Process，包含图谱、建模、推演、报告、追问 |
| 事件工作台 | ✅ 已完成 | 支持材料追加、基线版本、预测分支和阶段性研判 |
| 图谱构建 | ✅ 已完成 | Graphiti + Neo4j + GraphRAG / VectorRAG |
| Agent 画像 | ✅ 已完成 | OASIS Profile + AgentPrior + AgentCognitiveState |
| 模拟运行 | ✅ 已完成 | SimulationRunner 管理 OASIS 子进程、状态、日志和恢复 |
| 世界状态引擎 | ✅ 已完成 | 六维状态、TopicState、阶段先验、事件检测、现实校准 |
| 因果图谱引擎 | ✅ 已完成 | triggered / amplified / suppressed / correlated |
| 世界模型 API | ✅ 已完成 | `world-state`、`events`、`causal-graph`、`inject-event` |
| 前端世界状态展示 | ✅ 已完成 | `WorldStateHero`、`CausalGraphView`、`EventTimeline` |
| ReportAgent | ✅ 已完成 | ReACT 工具链，调用图谱、世界模型、评估和证据检索 |
| Benchmark | ✅ 已完成基础框架 | TCS / TPH / KAC / EOA 评分脚本与多案例目录 |
| Docker 部署 | ✅ 已具备 | `Dockerfile` + `docker-compose.yml` |

---

## 四、世界模型实现要点

### 4.1 WorldStateEngine

文件：

```text
backend/app/services/world_state.py
```

已实现：

- `WorldStateSnapshot` 六维状态
- `WorldEvent` 世界事件
- `TopicState` 话题级状态追踪
- 阶段先验 `STAGE_PRIORS`
- 自然衰减和平滑更新
- 规则 + LLM 辅助判断
- 滑动窗口趋势事件检测
- 外部事件注入
- 现实校准 `apply_reality_patch`
- JSONL 持久化

六维状态包括：

```text
attention_level / panic_level / trust_level
polarization_level / risk_level / stability_level
```

### 4.2 AgentBrain

文件：

```text
backend/app/services/agent_brain.py
```

已实现：

- `AgentPrior`
- `AgentCognitiveState`
- 目标显著性计算
- 策略选择
- 立场漂移压力
- 规则反思
- 个性化世界状态感知 `render_personalized_perception`

这部分已经属于当前已完成能力，答辩时可以作为 Agent 认知建模的实现证据。

### 4.3 CausalGraphEngine

文件：

```text
backend/app/services/causal_graph.py
```

已实现：

- 基于事件类型模板匹配潜在因果边
- 通过状态变量变化验证因果关系
- 支持可选 LLM 补充推断
- 因果边持久化到 `causal_edges.jsonl`
- 关系类型包括：

```text
triggered / amplified / suppressed / correlated
```

### 4.4 SimulationInsightService

文件：

```text
backend/app/services/simulation_insight_service.py
```

为 ReportAgent 提供：

- `world_model_brief`
- `state_evolution_analysis`
- `causal_chain_analysis`
- `evaluation_summary`
- `reputation_scorecard`
- `decision_support_brief`
- `simulation_evidence_search`
- `agent_cognition_analysis`

这让报告不只是 LLM 生成，而是有可调用的模拟证据工具。

---

## 五、前端展示进展

当前前端已经具备比较完整的演示链路。

### 5.1 主流程

| 页面 / 组件 | 状态 |
|---|---|
| `Home.vue` | 登录后启动页与事件材料入口 |
| `Process.vue` | 五步式舆情推演流程 |
| `Step1GraphBuild.vue` | 事件图谱生成 |
| `Step2EnvSetup.vue` | 群体环境建模 |
| `Step3Simulation.vue` | 舆情态势推演与世界模型展示 |
| `Step4Report.vue` | 决策简报生成 |
| `Step5Interaction.vue` | 智能追问研判 |
| `IncidentWorkspaceView.vue` | 事件工作台、滚动材料和预测分支 |

### 5.2 世界模型组件

```text
frontend/src/components/WorldState/
├── WorldStateHero.vue
├── CausalGraphView.vue
├── EventTimeline.vue
├── AgentActionCard.vue
└── SimGraphView.vue
```

当前展示重点应表述为：

> Step3 已经有世界状态、因果链和事件时间线展示；后续可继续增强折线图、Benchmark 对齐和多分支对比视图。

---

## 六、验证进展

### 6.1 Benchmark 评分框架

文件：

```text
benchmark/scoring.py
```

指标：

| 指标 | 权重 | 含义 |
|---|---:|---|
| TCS | 35% | 趋势一致性 |
| TPH | 25% | 转折点命中率 |
| KAC | 20% | 关键主体覆盖 |
| EOA | 20% | 事件顺序准确性 |

### 6.2 当前可展示案例

| 案例 | 文件 | 分数 |
|---|---|---:|
| 武汉大学图书馆争议 | `benchmark_score_sim656a_v5.json` | 99.3 / A |
| 华中农业大学学术不端举报 | `benchmark_score.json` | 100.0 / A |

### 6.3 内部 A/B 验证

`backend/tests/llm_validation_large_result.json` 中保留了历史世界模型 A/B 验证结果。当前 JSON 显示：

- Judge 票：B = 12，A = 6
- 多数决：B = 3，A = 3
- `overall_win_rate`：53.125

因此内部 A/B 验证不宜作为当前主展示结论。更稳妥的表述是：

> 项目保留了世界模型内部消融验证脚本，但比赛答辩主证据优先采用真实案例 Benchmark。

---

## 七、当前最适合答辩展示的证据链

```text
1. 输入材料
   └─ docs/cases/ 或 benchmark/seed_materials/

2. 模拟产物
   └─ backend/uploads/simulations/<sim_id>/
      ├─ simulation_config.json
      ├─ world_state_history.jsonl
      ├─ events.jsonl
      ├─ causal_edges.jsonl
      ├─ reddit/actions.jsonl
      └─ twitter/actions.jsonl

3. 报告产物
   └─ backend/uploads/reports/<report_id>/full_report.md

4. Benchmark 结果
   └─ benchmark/<case>/evaluation_result.json
   └─ benchmark/<case>/benchmark_score.json
```

对于 case_02，当前可引用：

```text
simulation: sim_b277466c5398
report: report_cf535f98cef0
benchmark total: 100.0 / A
```

---

## 八、遗留任务与优先级

| 优先级 | 任务 | 原因 |
|---|---|---|
| P0 | 补齐 case_03 Benchmark 运行结果 | 增强多案例可信度 |
| P0 | 设计准实时验证案例方案 | 突出早期材料预测能力 |
| P0 | 准备 Benchmark 证据页或报告附录 | 避免评委问“分数在哪” |
| P1 | 分支对比可视化 | 展示决策辅助价值 |
| P1 | 六维状态折线图和事件对齐 | 提升世界模型展示效果 |
| P1 | Agent 群体认知聚类分析 | 解释“哪些群体推动变化” |
| P2 | TopicState 对外展示 | 支持话题级推演解释 |
| P3 | 参数自动调优 | 长期优化方向 |

---

## 九、答辩推荐说法

### 不建议说

```text
我们已经能准确预测真实未来。
我们完整复现了某一篇论文。
内部消融结果已经足以单独证明系统一定更好。
```

### 建议说

```text
我们把真实事件材料转化为可推演的数字社会沙盘。
系统支持早期种子材料输入，并能随着现实新材料出现滚动更新预测。
世界模型让系统不只记录 Agent 发言，还能追踪关注度、信任、风险、极化等宏观状态。
Benchmark 用真实案例验证趋势、转折点、主体覆盖和事件顺序，证明系统能够抓住事件演化主线。
```

---

## 十、一句话总结

**NexusMind 当前已经完成以社会世界模型为核心的工程闭环：从现实材料进入，到图谱、Agent、推演、状态、因果、报告和 Benchmark 验证全部打通；下一阶段重点是多案例验证、准实时滚动预测和分支对比展示。**
