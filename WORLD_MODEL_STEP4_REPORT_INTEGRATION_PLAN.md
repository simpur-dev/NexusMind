# 世界模型 × Step4 报告生成 串联方案

> 目标：把 `Step3` 的世界模型推演结果真正接入 `Step4` 报告生成，使报告从“基于图谱的模拟总结”升级为“基于世界模型证据链的高校品牌声誉决策报告”。
>
> 该方案基于对现有代码的定向扫描形成，重点覆盖：`world_state.py`、`causal_graph.py`、`evaluation.py`、`report_agent.py`、`report.py`、`simulation.py`、`Step4Report.vue`。

---

## 一、结论先行

当前项目中，**世界模型已经闭环跑通**，但**没有真正进入 Step4 的报告生成主链路**。

### 现状判断

- `backend/app/services/world_state.py`
  - 已具备 6 维世界状态、事件检测、状态历史持久化、注入事件消费、因果推断触发。
- `backend/app/services/causal_graph.py`
  - 已具备因果边推断与持久化。
- `backend/app/services/evaluation.py`
  - 已具备对模拟结果的只读量化评估能力：情感时序、行为多样性、状态演化、影响力分析。
- `backend/app/api/simulation.py`
  - 已暴露 `world-state / events / causal-graph` 等读取接口。
- `backend/app/services/report_agent.py`
  - 当前仅使用 `insight_forge / panorama_search / quick_search / interview_agents` 四类工具。
  - 大纲规划和章节 prompt 仍以“未来预测报告”为中心，且明确写了：
    - “不是对现实世界现状的分析”
    - “聚焦于未来会怎样”
  - 这与当前比赛目标存在根本偏差。
- `frontend/src/components/Step4Report.vue`
  - 已具备良好的报告生成容器、章节实时展示、工具调用日志展示能力。
  - 但当前右侧日志和工具结果组件只适配图谱检索类工具，没有世界模型/评估/决策支持的可视化容器。

### 根本问题

Step4 现在的报告是：

- **图谱先验 + Agent 采访 + LLM 组织**

而不是：

- **图谱先验 + 世界模型后验 + 量化评估 + 因果链 + Agent 证词 + 决策推演**

因此它当前更像“模拟叙述报告”，而不是“高校品牌声誉诊断与决策支持报告”。

---

## 二、比赛目标下的正确报告定位

根据当前项目目标，报告不应仅服务武汉大学，而应面向**高校舆情演进与品牌声誉分析的一般化场景**。

因此 Step4 生成的最终报告必须满足：

- **系统评估品牌声誉现状**
- **揭示潜在风险与机会**
- **提供数据驱动的决策支持**
- **适配高校通用分析框架，个案数据可替换**

### 报告必须整合的 4 类能力

- **查询引擎**
  - 事实梳理
  - 事件时间线
  - 关键主体识别

- **媒体引擎**
  - 形象标签解构
  - 叙事框架识别
  - 舆论扩散结构

- **洞察引擎**
  - 民意量化
  - 世界状态演化
  - 情绪/信任/极化变化

- **分析论坛**
  - 多证据综合研判
  - 风险与机会识别
  - 治理与战略沟通建议

---

## 三、总体改造思路

核心思路是：

**保留现有 ReportAgent 的 ReACT 结构，但将它的“信息来源”从图谱主导，升级为“图谱先验 + 世界模型后验 + 量化评估 + 决策摘要”的混合证据链。**

### 目标架构

```text
Step3 模拟运行
  ├─ world_state_history.jsonl
  ├─ events.jsonl
  ├─ causal_edges.jsonl
  ├─ twitter/actions.jsonl
  ├─ reddit/actions.jsonl
  └─ world_state_current.json
           │
           ▼
SimulationEvaluator / WorldStateEngine / CausalGraphEngine
           │
           ▼
SimulationInsightService   ← 新增：统一聚合世界模型与模拟证据
  ├─ 当前状态诊断
  ├─ 状态演化摘要
  ├─ 关键转折点
  ├─ 因果链
  ├─ Agent 行为证据
  ├─ 量化评估摘要
  └─ 决策支持简报
           │
           ▼
ReportAgent
  ├─ 大纲规划（基于世界模型+评估）
  ├─ 章节生成（强制使用世界模型工具）
  ├─ 风险/机会/建议归纳
  └─ 证据索引输出
           │
           ▼
ReportManager
  ├─ full_report.md
  ├─ decision_brief.json        ← 新增
  ├─ evidence_index.json        ← 新增
  ├─ world_model_summary.json   ← 新增
  └─ report_quality.json        ← 新增（可选）
           │
           ▼
Step4Report.vue
  ├─ 报告正文
  ├─ 决策摘要卡片
  ├─ 世界模型证据概览
  ├─ 风险/机会矩阵
  └─ 工具调用与证据链日志
```

---

## 四、代码扫描后的关键断点

## 4.1 ReportAgent 的断点

文件：`backend/app/services/report_agent.py`

### 当前问题 1：工具链不含世界模型与评估工具

当前 `_define_tools()` 中只有：

- `insight_forge`
- `panorama_search`
- `quick_search`
- `interview_agents`

缺失：

- 世界状态摘要
- 状态演化摘要
- 关键事件与转折点
- 因果链追踪
- 量化评估摘要
- 决策支持摘要
- 原始动作证据搜索

### 当前问题 2：规划 prompt 方向错误

当前 `PLAN_SYSTEM_PROMPT` / `PLAN_USER_PROMPT_TEMPLATE` 强调：

- “未来预测报告”
- “不是对现实世界现状的分析”
- “未来会怎样”

这会直接导致 Step4 输出偏成：

- 模拟叙述
- 未来情景描述
- 风险趋势总结

而不会自然收敛到：

- 品牌声誉现状评估
- 风险/机会识别
- 传播治理建议

### 当前问题 3：章节生成只要求“调工具”，但不要求“调对工具”

当前 `_generate_section_react()` 只控制：

- 每章最少 3 次工具调用
- 最多 5 次工具调用
- 混合使用不同工具

但没有控制：

- 必须使用至少 1 个世界模型工具
- 必须使用至少 1 个量化评估工具
- 必须引用至少 1 条世界状态/事件/因果证据
- 建议类章节必须使用决策支持工具

这会导致 LLM 即使“满足次数”，也可能只在图谱上打转。

---

## 4.2 世界模型与评估层已经具备可接入能力

### 已有世界模型产物

文件：`backend/app/services/world_state.py`

已提供：

- `state_history_path = world_state_history.jsonl`
- `events_path = events.jsonl`
- `current_state`
- `state_history`
- `events`
- `causal_graph`

### 已有世界模型接口

文件：`backend/app/api/simulation.py`

已暴露：

- `GET /api/simulation/{simulation_id}/world-state`
- `GET /api/simulation/{simulation_id}/events`
- `GET /api/simulation/{simulation_id}/causal-graph`

这些接口已经足够支撑报告层读取世界模型产物。

### 已有量化评估能力

文件：`backend/app/services/evaluation.py`

`SimulationEvaluator` 已提供：

- `generate_report()`
- `get_sentiment_timeline()`
- `get_behavior_diversity()`
- `get_state_evolution()`
- `get_influence_analysis()`

其输入直接来自：

- `world_state_history.jsonl`
- `events.jsonl`
- `twitter/actions.jsonl`
- `reddit/actions.jsonl`

因此，**最省成本的接入方式**不是重写算法，而是把这些已有能力聚合成 ReportAgent 可调用的工具。

---

## 4.3 Step4 前端已有可复用容器

文件：`frontend/src/components/Step4Report.vue`

当前已有：

- 左侧章节实时渲染
- 右侧时间线 / 工具调用日志 / 工具结果展示
- 已完成章节折叠
- PDF 导出

这说明 Step4 前端不需要推倒重来，只需要：

- 新增顶部决策摘要区
- 新增世界模型工具结果展示组件
- 新增风险/机会/建议卡片
- 新增证据链索引视图

即可完成升级。

---

## 五、建议新增的中间层：SimulationInsightService

为了避免把太多“读文件 + 聚合 + 格式化”逻辑塞进 `report_agent.py`，建议新增一个服务：

- `backend/app/services/simulation_insight_service.py`

### 职责定位

它是一个**只读聚合服务**，专门把模拟结果整理成 ReportAgent 易消费的结构化证据。

### 输入来源

- `SimulationRunner.get_or_restore_world_state_engine(simulation_id)`
- `SimulationEvaluator(simulation_id)`
- `actions.jsonl`
- `twitter_profiles.json` / `reddit_profiles.json`
- 必要时使用 `GraphToolsService` 补充图谱先验

### 设计原则

- **优先读取本地 JSONL / SQLite / 文件系统证据**
- **Neo4j 图谱作为背景先验，不作为最终报告的唯一事实来源**
- **所有输出同时提供 JSON 结构 和 LLM 友好的文本结构**
- **每条结论都带来源字段**

### 建议提供的方法

#### 1. `get_report_context_bundle(simulation_id)`

返回统一总览：

```json
{
  "simulation_id": "sim_xxx",
  "current_world_state": {},
  "state_summary": "...",
  "key_events": [],
  "top_causal_chains": [],
  "evaluation_summary": {},
  "top_agents": [],
  "risk_signals": [],
  "opportunity_signals": []
}
```

#### 2. `get_world_model_brief(simulation_id, focus)`

返回：

- 当前 6 维状态
- 最近 5 轮变化趋势
- 最显著异常维度
- 对品牌声誉的解释文本

#### 3. `get_turning_points_and_causal_chains(simulation_id)`

返回：

- Top 转折点
- 每个转折点对应事件描述
- 关键因果链（cause → effect）
- 对声誉影响方向（损害/修复/争议加剧）

#### 4. `get_reputation_scorecard(simulation_id)`

基于世界模型和评估结果，生成品牌声誉评分卡。

建议新增 4 个报告级指标：

- `reputation_health_score`
- `risk_escalation_score`
- `trust_recovery_score`
- `polarization_pressure_score`

##### 参考映射公式（建议实现）

```text
Reputation Health Score
= 0.28 * trust_level
+ 0.20 * stability_level
+ 0.16 * (1 - panic_level)
+ 0.14 * (1 - risk_level)
+ 0.12 * (1 - polarization_level)
+ 0.10 * (1 - negative_dominant_ratio)

Risk Escalation Score
= 0.24 * attention_level
+ 0.22 * panic_level
+ 0.18 * polarization_level
+ 0.18 * risk_level
+ 0.10 * (1 - trust_level)
+ 0.08 * event_density
```

这些公式不是现有代码中的事实，而是本方案建议新增的“报告层指标”。

#### 5. `get_decision_support_brief(simulation_id)`

这是整个串联方案的核心输出。

返回结构建议为：

```json
{
  "diagnosis": {
    "overall_status": "高压脆弱/修复中/相对稳定",
    "summary": "..."
  },
  "top_risks": [
    {
      "title": "信任塌缩风险",
      "severity": "high",
      "urgency": "24h",
      "evidence_refs": ["WM-03", "EV-02", "AG-01"],
      "explanation": "..."
    }
  ],
  "top_opportunities": [
    {
      "title": "透明回应窗口",
      "confidence": 0.78,
      "evidence_refs": ["WM-07", "EV-04"],
      "explanation": "..."
    }
  ],
  "recommended_actions": {
    "within_24h": [],
    "within_72h": [],
    "within_2_weeks": []
  },
  "communication_strategy": [],
  "uncertainty_notes": []
}
```

#### 6. `search_simulation_evidence(simulation_id, query, ...)`

支持从真实模拟产物中检索证据：

- actions
- 事件
- 状态变化
- agent 语句
- 关键轮次

这会成为 ReportAgent 最重要的新工具之一。

---

## 六、ReportAgent 的后端改造方案

## 6.1 工具层改造

文件：`backend/app/services/report_agent.py`

建议新增工具：

### 第一组：世界模型工具

- `world_model_brief`
  - 获取当前世界状态 + 最近趋势
- `state_evolution_analysis`
  - 获取峰值/谷值/波动率/转折点
- `causal_chain_analysis`
  - 获取关键事件因果链
- `world_event_timeline`
  - 获取重大事件时间线

### 第二组：模拟证据工具

- `simulation_evidence_search`
  - 在动作日志/事件/状态中检索具体证据
- `agent_quote_pack`
  - 返回与某议题最相关的 Agent 原始发言和行为样本
- `platform_diff_analysis`
  - 对 Twitter / Reddit 做平台差异分析

### 第三组：决策支持工具

- `reputation_scorecard`
  - 返回品牌声誉评分卡
- `decision_support_brief`
  - 返回风险/机会/建议摘要
- `intervention_window_analysis`
  - 返回最佳回应窗口和沟通优先级

### 第四组：量化评估工具

- `evaluation_summary`
  - 综合评估摘要
- `sentiment_timeline`
  - 情绪变化趋势
- `behavior_diversity`
  - 群体行为结构
- `influence_analysis`
  - 影响力分布与关键 Agent

### 保留的现有工具

- `insight_forge`
- `panorama_search`
- `quick_search`
- `interview_agents`

### 角色分工建议

- 图谱工具：回答“已有事实基础是什么”
- 世界模型工具：回答“推演中发生了什么”
- 评估工具：回答“变化有多明显”
- 决策工具：回答“下一步该怎么做”

---

## 6.2 大纲规划层改造

### 当前问题

当前 `plan_outline()` 使用的 prompt 是“未来预测报告”逻辑。

### 建议改造为“高校品牌声誉决策报告”

建议将大纲规划改为**半模板驱动**，而不是完全自由生成。

### 建议固定 5 章结构

#### 章节 1：品牌声誉现状诊断
输出：

- 当前品牌声誉总体判断
- 当前世界状态对声誉的映射
- 主要压力源

#### 章节 2：舆情演进与关键转折分析
输出：

- 关键事件时间线
- 转折点识别
- 因果链解释

#### 章节 3：公众认知与媒体叙事解构
输出：

- 主要群体反应
- 媒体/平台差异
- 高传播内容与主导叙事

#### 章节 4：潜在风险与修复机会识别
输出：

- 风险矩阵
- 机会窗口
- 不确定性与预警信号

#### 章节 5：决策建议与战略沟通方案
输出：

- 24h / 72h / 2周行动建议
- 治理与沟通双轨方案
- 成效监测指标

### 可选附加章节

如果模拟数据丰富，可允许生成：

- `附录：关键证据链与方法说明`

### 规划阶段需要额外注入的上下文

`plan_outline()` 不应只拿 `graph_tools.get_simulation_context()`。

而应注入：

- 图谱背景上下文
- 当前状态摘要
- 主要转折点
- 评估摘要
- 决策评分卡

从而让 LLM 在“规划大纲”阶段就知道：

- 这不是普通的未来预测报告
- 这是需要支撑高校决策的品牌声誉报告

---

## 6.3 章节生成层改造

文件：`backend/app/services/report_agent.py`

### 当前问题

`_generate_section_react()` 只对“工具调用次数”做约束，不对“工具类型覆盖率”做约束。

### 建议新增：章节级工具覆盖规则

为不同章节配置不同的必选工具组。

#### 章节 1：品牌声誉现状诊断
至少调用：

- `reputation_scorecard`
- `world_model_brief`
- `evaluation_summary`

#### 章节 2：演进与转折分析
至少调用：

- `world_event_timeline`
- `causal_chain_analysis`
- `simulation_evidence_search`

#### 章节 3：公众认知与媒体叙事
至少调用：

- `agent_quote_pack`
- `platform_diff_analysis`
- `influence_analysis`

#### 章节 4：风险与机会识别
至少调用：

- `decision_support_brief`
- `state_evolution_analysis`
- `evaluation_summary`

#### 章节 5：策略建议
至少调用：

- `decision_support_brief`
- `intervention_window_analysis`
- `simulation_evidence_search`

### 建议新增：证据标签机制

每个工具返回的数据都附上 `evidence_id`，例如：

- `WM-01` 世界模型状态摘要
- `EV-03` 评估峰值转折点
- `CG-02` 因果链条
- `AG-04` Agent 原话
- `AC-09` 动作日志证据

报告中建议使用轻量证据标记，例如：

```text
校方信任度在第 8-12 轮出现持续性下滑，说明公众对权威信息的接受度明显下降 [WM-03][EV-02]。
```

这会显著提升：

- 可解释性
- 比赛答辩说服力
- 前端证据链可视化能力

### 建议新增：建议章节的输出模板约束

策略建议类章节禁止只写空泛建议，必须输出：

- 建议动作
- 目标对象
- 执行时机
- 预期作用
- 证据依据
- 若不执行的潜在后果

例如：

```text
建议：在 24 小时内发布“事实澄清 + 流程透明”双层回应。
对象：宣传部门 + 事件处置专班
目标：阻断恐慌上升与信任继续下滑
依据：[WM-05][CG-03][AG-02]
若不执行：高关注 + 低信任状态可能继续推高极化
```

---

## 七、让世界模型显著提升“准确性”的机制

要让报告准确，不是简单把世界模型 JSON 塞进 prompt，而是要建立“多证据校验”机制。

## 7.1 三层证据融合

### 层 1：图谱先验

回答：

- 现实背景是什么
- 关键主体有哪些
- 原始事实脉络是什么

### 层 2：模拟后验

回答：

- 在当前设定下，Agent 实际做了什么
- 世界状态如何演化
- 哪些关键事件触发了变化

### 层 3：量化校验

回答：

- 变化是否足够显著
- 哪些指标达到了峰值
- 风险是否集中在少数节点或持续扩散

### 准确性规则

报告中的每一个“判断句”都尽量满足：

- 至少有 1 个世界模型/评估证据
- 最好再有 1 个 Agent 或平台行为证据

例如：

- “信任受损”不能只来自 LLM 常识，应来自：
  - trust_level 下降
  - 事件或因果链说明
  - Agent 对官方信息质疑的言论样本

---

## 八、让世界模型显著提升“前瞻性”的机制

世界模型的真正价值，不是复述已发生事件，而是识别**未来走向与决策窗口**。

## 8.1 使用“趋势 + 加速度 + 转折密度”判断未来风险

建议在 `SimulationInsightService` 中新增以下分析：

- 最近 3 轮状态斜率
- 最近 5 轮状态波动性
- 关键转折点密度
- 高严重度事件的聚集程度

### 用法示例

- `attention ↑ + panic ↑ + trust ↓`
  - 说明进入高曝光、高情绪、低信任阶段
  - 前瞻含义：进入 reputational damage acceleration zone

- `attention 高位但 panic ↓ + stability ↑`
  - 说明仍在关注中，但窗口开始出现
  - 前瞻含义：适合进入修复型沟通阶段

## 8.2 输出“预警信号”而非只输出结论

报告里需要增加一类内容：

- 哪些信号若继续维持 2-3 轮，会导致进一步恶化
- 哪些信号若出现反转，说明修复机会到来

这能让报告从“分析结果”升级为“预警工具”。

## 8.3 Phase 2：接入 A/B 场景对比

如果希望进一步强化前瞻性，建议在第二阶段把 Step4 接入“干预方案对比”。

例如对同一高校事件生成：

- 场景 A：沉默/迟回应
- 场景 B：快速透明回应
- 场景 C：权威背书 + 学生沟通

然后在报告中输出：

- 不同干预路径下的风险曲线变化
- 哪种策略更能提升 trust、抑制 panic、降低 polarization

这会让 Step4 从“分析报告”升级为：

- **决策演练报告**
- **干预方案评估报告**

---

## 九、让报告切实支持决策的机制

比赛场景下，Step4 的最终价值不在“写得像报告”，而在“能让管理者知道下一步怎么做”。

## 9.1 决策输出必须分时间窗口

建议固定输出：

### 24 小时内

- 先做什么
- 谁来做
- 目标是什么

### 72 小时内

- 如何稳定情绪
- 如何提升信任
- 如何压制谣言扩散

### 2 周内

- 如何做制度修复叙事
- 如何完成议题收口与形象重建

## 9.2 决策输出必须分角色

建议报告中将建议按执行主体分组：

- 校宣传 / 舆情团队
- 学校管理层
- 学工系统
- 学术/业务主管部门
- 法务/纪律/调查相关部门

## 9.3 决策输出必须分目标

建议每条建议标明目标：

- 降低恐慌
- 修复信任
- 降低极化
- 稳定议题结构
- 争取机会窗口

这 5 个目标都能直接映射到世界模型 6 维状态。

---

## 十、Step4 前端改造方案

文件：`frontend/src/components/Step4Report.vue`

## 10.1 顶部增加“决策摘要区”

在当前报告头部下方新增卡片区：

- 当前品牌声誉状态
- 风险升级评分
- 修复机会评分
- 当前主风险
- 最佳干预窗口

建议展示形式：

- 评分条
- 状态标签（高压脆弱 / 风险积累 / 修复中 / 稳定）
- 一句话摘要

## 10.2 左侧保留报告正文，新增“证据锚点”能力

每个章节内可以增加：

- 风险标签
- 证据标签
- 点击证据编号时，右侧自动定位到对应工具结果或证据卡

## 10.3 右侧工作流时间线升级为“证据工作台”

当前右侧已经是很好的容器，可以扩展成以下三类视图切换：

- **日志视图**：保留当前时间线
- **证据视图**：结构化展示 WM / EV / CG / AG 结果
- **决策视图**：展示风险/机会/建议卡片

## 10.4 为新增工具补充结构化展示组件

当前已有：

- `InterviewDisplay`
- `InsightDisplay`
- `PanoramaDisplay`
- `QuickSearchDisplay`

建议新增：

- `WorldModelDisplay`
- `StateEvolutionDisplay`
- `CausalChainDisplay`
- `DecisionBriefDisplay`
- `EvaluationSummaryDisplay`

这些组件可以直接挂在 `tool_result` 的分支里，不需要改动整体框架。

## 10.5 新增“报告产物文件”的读取能力

建议 Step4 额外读取：

- `decision_brief.json`
- `evidence_index.json`
- `world_model_summary.json`

这可以通过新增报告 API 实现，例如：

- `GET /api/report/{report_id}/decision-brief`
- `GET /api/report/{report_id}/evidence-index`
- `GET /api/report/{report_id}/world-model-summary`

如果想少改 API，也可以先把这三份 JSON 合并进 `meta.json`。

---

## 十一、推荐的最小可行改造（MVP）

如果目标是**最快让 Step4 从“没连上”变成“连上且有效”**，建议分两阶段。

## 阶段 A：最小闭环（优先实现）

### 目标

让报告生成至少能消费：

- 世界状态摘要
- 状态演化摘要
- 因果链
- 评估摘要
- 决策摘要

### 需要改的文件

- `backend/app/services/report_agent.py`
- `backend/app/services/evaluation.py`
- `backend/app/services/world_state.py`（只读扩展即可）
- `backend/app/api/report.py`
- `frontend/src/components/Step4Report.vue`
- `frontend/src/api/report.js`

### 建议新增文件

- `backend/app/services/simulation_insight_service.py`

### 最小新增工具

- `world_model_brief`
- `state_evolution_analysis`
- `causal_chain_analysis`
- `evaluation_summary`
- `decision_support_brief`

### 最小新增产物

- `decision_brief.json`
- `world_model_summary.json`

### 阶段 A 完成后的效果

- ReportAgent 不再只写“未来会怎样”
- Step4 可以输出“当前声誉状态 + 风险 + 建议”
- 报告与世界模型真正串联起来

## 阶段 B：强化答辩表现（第二优先级）

### 目标

- 提升证据链可解释性
- 提升可视化戏剧性
- 提升决策演练能力

### 内容

- 证据标签体系
- 风险/机会矩阵
- A/B 干预方案对比
- 证据点击跳转
- 决策建议卡片化展示

---

## 十二、验收标准

该方案落地后，至少满足以下标准：

## 12.1 代码层验收

- `ReportAgent` 新增世界模型/评估/决策支持工具
- `plan_outline()` 不再只依赖图谱上下文
- `_generate_section_react()` 支持章节级必选工具组
- `ReportManager` 能持久化决策简报和证据索引
- `Step4Report.vue` 能展示世界模型与决策结果

## 12.2 报告质量验收

- 报告至少包含：
  - 品牌声誉现状
  - 演进与转折
  - 风险与机会
  - 决策建议
- 章节中存在来自世界模型/评估的明确证据
- 建议不再空泛，而是包含：动作、时机、目标、依据、后果
- 武汉大学案例可以直接输出一份“答辩可讲”的品牌声誉决策报告

## 12.3 比赛价值验收

答辩时可以明确说：

- 我们不是只做了一个多智能体模拟器
- 而是做了一个面向高校舆情演进与品牌声誉治理的**AI 决策支持系统**
- 世界模型让系统从“事件复现”升级为“趋势识别 + 风险预警 + 干预建议”
- Step4 是整个系统“把推演结果转化为治理决策”的关键落点

---

## 十三、最终建议

如果只做一件最有价值的事情，我建议优先做：

### **新增 `SimulationInsightService`，并把它接入 `ReportAgent` 的大纲规划与章节工具链。**

原因：

- 不需要推翻现有架构
- 能直接复用已完成的世界模型与评估代码
- 能最明显提升报告的准确性、前瞻性和决策支持价值
- 能直接补上目前最关键的国赛短板：**报告证据链与决策支撑不足**

---

## 十四、一句话总结

当前 Step4 报告生成的核心问题，不是“写得不够漂亮”，而是**它还没有把 Step3 世界模型推演结果转化为可验证、可追踪、可执行的决策证据链**。

本方案的核心，就是让 Step4 从：

- **图谱驱动的未来预测报告**

升级为：

- **世界模型驱动的高校品牌声誉决策报告**
