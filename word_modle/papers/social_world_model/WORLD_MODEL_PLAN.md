# NexusMind 世界模型优化方案

> 更新日期：2026-05-05  
> 适用阶段：当前项目已具备完整演示链路，后续优化应优先服务比赛答辩、真实案例验证和滚动决策闭环。  
> 当前原则：先保证“已完成能力讲得清、证据拿得出、演示稳定”，再做架构扩展。

---

## 一、当前能力基线

当前 NexusMind 已经不是早期“世界模型实验版”，而是具备完整产品链路的原型系统：

```text
材料接入 → 事实基线 → 事件图谱 → Agent 建模 → 双平台推演
       → 六维世界状态 → 因果链 → ReportAgent → Benchmark 评估
```

### 1.1 已完成能力

| 模块 | 当前状态 | 主要文件 |
|---|---|---|
| 材料接入 | 支持文件、文本、网络抓取和分阶段追加 | `incident.py`, `web_scraper.py`, `text_processor.py` |
| 事实基线 | 支持 Baseline Snapshot、基线重建和差异对比 | `models/baseline.py`, `api/incident.py` |
| 事件图谱 | Graphiti + Neo4j 构建图谱，支持 GraphRAG / VectorRAG | `graph_builder.py`, `graph_tools.py`, `vector_store.py` |
| Agent 画像 | 生成 OASIS Profile、AgentPrior、AgentCognitiveState | `oasis_profile_generator.py`, `agent_brain.py` |
| 多智能体推演 | CAMEL / OASIS 双平台模拟，记录动作和状态 | `simulation_runner.py`, `run_parallel_simulation.py` |
| 世界状态 | 六维状态、TopicState、阶段先验、现实校准、事件检测 | `world_state.py` |
| 因果链 | 模板匹配 + 状态验证 + 可选 LLM 推断 | `causal_graph.py` |
| 报告引擎 | ReACT ReportAgent 调用多工具生成报告 | `report_agent.py`, `simulation_insight_service.py` |
| Benchmark | TCS / TPH / KAC / EOA 真实案例评分 | `benchmark/scoring.py` |
| 前端展示 | 五步流程、世界状态 Hero、因果链、事件时间线 | `Step3Simulation.vue`, `components/WorldState/` |

### 1.2 当前验证证据

| 证据 | 状态 |
|---|---|
| Case 01 武汉大学图书馆争议 | `benchmark_score_sim656a_v5.json`：99.3 / A |
| Case 02 华中农业大学学术不端举报 | `benchmark_score.json`：100.0 / A |
| 内部 A/B 世界模型验证脚本 | 保留在 `backend/tests/llm_validation_large.py`，建议作为研发参考，不作为主展示证据 |
| 分阶段回测脚本 | `tests/incident_phased_test/`，用于验证材料追加和基线重建流程 |

---

## 二、优化优先级总览

后续优化建议不再按“论文复现完整度”排序，而按“比赛展示价值 + 项目可信度 + 实际功能闭环”排序。

| 优先级 | 方向 | 目标 |
|---|---|---|
| P0 | 多案例验证与准实时案例方案 | 让评委相信系统不是单案例演示 |
| P0 | Benchmark 可视化与报告证据卡 | 让验证结果在前端或报告中更容易被看到 |
| P0 | 现实滚动校准链路打磨 | 强化“早期种子材料 → 追加材料 → 更新预测”定位 |
| P1 | 分支对比与干预方案展示 | 展示不同处置策略的轨迹差异 |
| P1 | 世界模型前端可视化增强 | 增强六维状态、因果链和事件流的展示冲击力 |
| P1 | Agent 群体认知与角色簇分析 | 从个体 Agent 走向群体解释 |
| P2 | TopicState 对外暴露与话题级因果 | 从宏观六维状态细化到子话题演化 |
| P2 | Profile-aware 状态聚合 | 让官方、媒体、学生、公众等角色影响权重不同 |
| P3 | 参数学习与自动调优 | 用 Benchmark 数据反向优化世界模型参数 |

---

## 三、P0：多案例验证与准实时案例方案

### 现状

项目已有 `benchmark/` 验证框架，case_01 和 case_02 已产生较好的评分结果。case_03 目录已存在，但仍需补齐运行结果和评分文件。

### 建议目标

1. **历史案例验证**：至少整理 3 个已完结真实案例，统一输出 `evaluation_result.json` 和 `benchmark_score.json`。
2. **准实时案例验证**：选择一个近期发生、后续结果已逐步公开的案例，只用早期材料输入系统，冻结输入窗口，等现实后续发生后再对照。
3. **多知识等级对比**：延续 Tier A / Tier B / Tier C 思路，展示信息充分程度对推演质量的影响。

### 价值

这比单纯展示“系统能跑”更有说服力，可以回答：

- 系统是不是只对一个案例有效？
- 早期信息不足时表现如何？
- 材料逐步补充后，预测是否能滚动改善？

### 涉及文件

- `benchmark/scoring.py`
- `benchmark/case_01_wuhan_university_library/`
- `benchmark/case_02_huazhong_agricultural_university_academic_misconduct/`
- `benchmark/case_03_jiangxi_industry_vocational_college_food_safety/`
- `tests/incident_phased_test/`

---

## 四、P0：Benchmark 可视化与报告证据卡

### 现状

Benchmark 数据和评分脚本存在，但前端主流程没有正式展示入口。此前尝试过首页卡片，但容易干扰现有视觉和答辩视频，因此不建议强行放首页。

### 推荐方案

更稳妥的方式是把 Benchmark 作为“报告侧证据”或“独立验证页”：

1. **报告页小证据块**  
   在 `Step4Report.vue` 报告完成后，显示“真实案例验证指标说明”，但不写夸张大分数。

2. **独立 `/evaluation` 或 `/benchmark` 页面**  
   注册 `EvaluationView.vue`，用于答辩时单独打开展示多案例对比。

3. **报告导出附录**  
   在报告 Markdown 或答辩材料中引用 `benchmark_score.json`，作为可复核证据。

### 推荐文案

```text
Benchmark 验证框架通过 TCS、TPH、KAC、EOA 四项指标，对推演趋势、关键拐点、主体覆盖和事件顺序进行真实案例对照。
```

### 涉及文件

- `frontend/src/views/EvaluationView.vue`
- `frontend/src/api/evaluation.js`
- `frontend/src/components/Step4Report.vue`
- `backend/app/api/evaluation.py`

---

## 五、P0：现实滚动校准链路打磨

### 现状

当前项目已经具备事件工作台和预测分支 API：

- 材料追加
- 基线重建
- 基线差异对比
- ForecastRun 创建
- 现实校准 `recalibrate`
- 分支对比 `compare`

但这些能力在答辩时需要用更清楚的叙事串起来。

### 建议优化

1. 在事件工作台中明确展示“当前基线版本”和“上一次基线变化”。
2. 将 `recalibrate` 的结果命名为“校准后预测 v2 / v3”，方便评委理解。
3. 对每次新增材料，自动生成一句“本轮新增事实改变了哪些判断”。
4. 在报告中加入“本报告基于第 N 版事实基线”的说明。

### 涉及文件

- `backend/app/api/incident.py`
- `backend/app/api/forecast.py`
- `backend/app/models/baseline.py`
- `backend/app/models/forecast_run.py`
- `frontend/src/views/IncidentWorkspaceView.vue`

---

## 六、P1：分支对比与干预方案展示

### 现状

后端有 `forecast/compare` 和干预计划字段，项目中也有 `intervention_library.py`。当前答辩最容易讲清楚的是 A/B 处置策略对比。

### 建议展示方式

| 分支 | 处置策略 | 展示指标 |
|---|---|---|
| Base | 不额外干预或常规回应 | 风险曲线、信任曲线、事件数量 |
| Intervention A | 早期透明说明 | 信任修复、风险下降速度 |
| Intervention B | 延迟回应或强硬回应 | 二次争议、极化压力 |

### 价值

这能把系统从“预测工具”提升为“决策辅助工具”：

> 不只是告诉你未来可能怎样，而是比较不同处置动作会带来什么差异。

### 涉及文件

- `backend/app/api/forecast.py`
- `backend/app/services/intervention_library.py`
- `frontend/src/views/IncidentWorkspaceView.vue`
- `frontend/src/components/WorldState/WorldStateHero.vue`

---

## 七、P1：世界模型前端可视化增强

### 现状

当前 Step3 已经使用：

- `WorldStateHero.vue`
- `CausalGraphView.vue`
- `EventTimeline.vue`
- `AgentActionCard.vue`

比旧文档中“只有边栏面板”的状态更完整。

### 后续增强

1. 六维状态折线图：展示每一轮 `attention / panic / trust / polarization / risk / stability`。
2. 因果链力导向图：用 D3 展示事件节点和因果边。
3. 事件时间线高亮：将关键转折点和 Benchmark TPH 对齐。
4. 报告页引用世界状态：让报告结论能跳转到对应轮次证据。

### 涉及文件

- `frontend/src/components/WorldState/`
- `frontend/src/components/Step3Simulation.vue`
- `frontend/src/components/Step4Report.vue`

---

## 八、P1：Agent 群体认知与角色簇分析

### 现状

`AgentBrain` 已实现：

- `AgentPrior`
- `AgentCognitiveState`
- 目标显著性
- 策略选择
- 立场漂移
- 规则反思
- 个性化世界状态感知

`SimulationInsightService` 已有 `get_agent_cognition_analysis()`，可以服务 ReportAgent。

### 后续增强

1. 按角色类型聚合认知状态：学生、媒体、学校、公众等。
2. 识别群体策略转移：观望、核验、质疑、澄清、稳定等策略的占比变化。
3. 将群体认知变化与世界状态曲线对齐。
4. 在报告中加入“哪类群体最先发生信任变化 / 情绪升高”。

### 价值

把报告从“宏观状态变化”推进到“哪些群体推动了变化”。

---

## 九、P2：TopicState 对外暴露与话题级因果

### 现状

`world_state.py` 中已经有 `TopicState` 和 `_update_topic_states()`，能追踪活跃关键词和主导话题切换。但这部分目前更多是内部状态，前端和报告中的呈现还不够突出。

### 后续增强

1. 在世界状态 API 中返回当前 Top Topic 状态。
2. 把话题切换事件写入事件时间线。
3. 在因果链中区分“哪个话题导致信任下降 / 极化上升”。
4. 在报告中增加“议题迁移分析”。

### 涉及文件

- `backend/app/services/world_state.py`
- `backend/app/api/simulation.py`
- `backend/app/services/simulation_insight_service.py`
- `frontend/src/components/WorldState/EventTimeline.vue`

---

## 十、P2：Profile-aware 状态聚合

### 现状

世界状态更新已支持动作统计、关键词、阶段先验、平滑和 LLM 修正，但不同角色对状态的影响权重仍可进一步细化。

### 建议方向

1. 官方、媒体、当事人、普通公众使用不同影响权重。
2. Opinion leader 的转发和评论赋予更高传播影响。
3. 将 Agent 的 `stance`、`authority_trust`、`risk_tolerance` 引入状态聚合。
4. 将影响权重写入评估报告，增强可解释性。

### 价值

更接近现实舆论场：同一句话由不同主体发出，对信任和风险的影响不同。

---

## 十一、P3：参数学习与自动调优

### 现状

世界状态更新目前以规则和阈值为主，例如平滑系数、事件检测阈值、阶段先验等。这种方式可解释性强，但跨案例泛化仍依赖调参。

### 远期方向

1. 用 Benchmark 分数作为目标函数，自动搜索世界模型参数。
2. 针对不同事件类型保存参数模板。
3. 将多案例运行结果积累为轻量训练数据。
4. 在保持可解释性的前提下，用学习化模块替代部分手工阈值。

### 风险

这个方向不适合作为当前比赛前的核心工作，因为成本高、验证周期长。建议作为论文或后续版本路线。

---

## 十二、推荐实施路径

### 比赛前优先

1. 补齐 case_03 运行结果和 Benchmark 评分。
2. 准备一个准实时验证案例方案。
3. 在报告或单独页面中展示 Benchmark 指标，不强行塞回首页。
4. 整理一张架构图和一张闭环图。
5. 保证 Demo 视频中的五步流程稳定。

### 比赛后短期

1. 打磨 ForecastRun 分支对比可视化。
2. 增强世界状态趋势图。
3. 将 Agent 群体认知分析写入报告。
4. 暴露 TopicState 到前端和报告。

### 中长期

1. 角色加权状态聚合。
2. 多案例参数调优。
3. 更完整的准实时滚动验证框架。
4. 世界模型参数可学习化。

---

## 十三、一句话总结

**当前 NexusMind 世界模型已经完成“可运行闭环”：六维社会状态、Agent 认知、事件检测、因果链、报告工具和 Benchmark 验证都已具备；下一阶段重点不是再堆概念，而是把多案例验证、滚动校准、分支对比和前端可视化做得更稳定、更容易被评委看懂。**
