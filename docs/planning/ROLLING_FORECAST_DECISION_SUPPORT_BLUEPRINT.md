# NexusMind 滚动预测与决策辅助改造蓝图

## 1. 文档目的

本文档对应当前项目的主目标：

- 在高校舆情发生的第一时间，输入当下已知种子材料
- 基于当前信息进行未来演化预测
- 随现实进展持续补充材料，滚动更新判断
- 将系统输出作为下一步处置动作的重要参考
- 支持对不同动作方案进行分支推演与比较

本文档不是 Benchmark 优化文档，也不是盲测方案文档，而是面向“真实高校舆情工作流”的产品与工程改造蓝图。

---

## 2. 当前系统现状与代码映射

### 2.1 当前主流程已经具备的能力

当前系统已经形成一条完整的单次推演链路：

- 输入材料并生成本体
  - `backend/app/api/graph.py`
  - 路由：`/api/graph/ontology/generate`
- 构建图谱
  - `backend/app/api/graph.py`
  - 路由：`/api/graph/build`
  - 服务：`backend/app/services/graph_builder.py`
- 创建/准备/启动模拟
  - `backend/app/api/simulation.py`
  - 路由：`/api/simulation/create`
  - 路由：`/api/simulation/prepare`
  - 路由：`/api/simulation/start`
  - 服务：`backend/app/services/simulation_manager.py`
  - 服务：`backend/app/services/simulation_runner.py`
- 世界状态、事件、因果链输出
  - `backend/app/services/world_state.py`
  - `backend/app/services/causal_graph.py`
  - `backend/app/api/simulation.py`
- 决策支持简报与长报告
  - `backend/app/services/simulation_insight_service.py`
  - `backend/app/services/report_agent.py`
  - `backend/app/api/report.py`

这说明：系统已经具备“首轮输入材料 -> 建模 -> 推演 -> 分析”的原型能力。

### 2.2 当前系统最接近真实目标的模块

- `world_state.py`
  - 已有 6 维世界状态，是系统中最接近“态势推演内核”的模块
- `simulation_insight_service.py`
  - 已有评分卡、风险/机会、决策支持简报，是最接近“行动参考”的模块
- `simulation.py` 中的 `inject-event`
  - 已有动态外部变量注入入口，是“干预模拟”雏形

### 2.3 当前系统与真实目标不匹配的核心点

#### 1) 材料输入是“一次性”的，不是“滚动式”的

- `Project` 当前只维护单个：
  - `graph_id`
  - `simulation_id`
  - `report_id`
- `ProjectManager.save_extracted_text()` 也是单文本汇总覆盖模式
- 当前没有明确的“给已有项目持续追加材料”的标准 API

#### 2) 图谱构建是“整图构建”，不是“增量校准”

- `/api/graph/build` 的默认心智模型仍然是重新构图
- `graph_builder.py` 有 `add_text_batches()`，但尚未形成“产品级增量更新闭环”

#### 3) 模拟支持续跑，但不等于“现实校准后继续预测”

- 当前 `resume=true` 更偏向从已有轮次继续跑
- 但没有标准流程做到：
  - 新材料进入
  - 事实基线更新
  - Agent 认知校准
  - 世界状态回填/修正
  - 再继续预测

#### 4) 决策支持已存在，但建议仍偏通用

- `simulation_insight_service.py -> get_decision_support_brief()`
- 当前建议主要是阈值驱动的通用动作
- 还缺少：
  - 方案 A/B/C 对比
  - 每个动作的预期收益与副作用
  - 支持证据与监测指标
  - 与本案当前阶段深度绑定的动作序列

#### 5) 前端是线性流程，不是持续工作的事件工作台

当前主入口：

- `frontend/src/views/Process.vue`
- `frontend/src/components/Step1GraphBuild.vue`
- `frontend/src/components/Step2EnvSetup.vue`
- `frontend/src/components/Step3Simulation.vue`
- `frontend/src/components/Step4Report.vue`
- `frontend/src/components/Step5Interaction.vue`

这套结构适合“跑一遍 demo”，不适合“每天多次补材料、刷新判断、比较动作方案”。

---

## 3. 目标产品形态

目标产品不应再是单次五步流程，而应是一个长期存在的“事件工作台”。

### 3.1 理想闭环

- 输入当前已知材料
- 生成当前事实基线
- 推演未来 24h / 72h / 1 周
- 输出推荐动作 A / B / C
- 人选择一个动作做研判
- 系统评估动作影响
- 现实出现新进展后补材料
- 系统更新基线并重新预测
- 持续循环直到事件结束

### 3.2 产品最小核心对象

系统应围绕以下对象组织，而不再只围绕单个 `simulation_id`：

- `Project`
  - 事件容器
- `MaterialEntry`
  - 每一次新增材料
- `BaselineSnapshot`
  - 当前事实基线快照
- `ForecastRun`
  - 一次预测运行/预测分支
- `InterventionOption`
  - 一种候选动作方案
- `DecisionBrief`
  - 针对当前局面的结构化决策输出

---

## 4. 最低风险的总体改造策略

为了尽量复用现有代码、降低改造成本，建议采取以下原则：

- 保留 `Process.vue` 作为演示/比赛入口
- 新增“事件工作台”视图，而不是直接推翻现有 5 步流程
- 保留现有 `ProjectManager` 文件持久化方式，先不引入数据库迁移
- 保留 `uploads/simulations/<simulation_id>` 作为底层运行目录
- 在 `project` 维度上新增“材料、基线、预测分支”的目录与元数据
- Benchmark 与知识门控保留在验证层，不再主导主链路

---

## 5. 后端改造蓝图

## 5.1 数据持久化改造

### 5.1.1 现状问题

当前 `backend/app/models/project.py` 中的 `Project` 结构是“单项目 + 单图谱 + 单模拟 + 单报告”模型，无法承载滚动事件过程。

### 5.1.2 建议目录结构

在现有项目目录下新增结构：

```text
uploads/projects/<project_id>/
  project.json
  files/
  extracted_text.txt
  materials/
    manifest.json
    raw/
      <material_id>_<filename>
    extracted/
      <material_id>.txt
  baselines/
    <baseline_id>.json
  forecast_runs/
    <run_id>.json
  decision_briefs/
    <run_id>.json
```

### 5.1.3 建议新增元数据模型

优先建议新增 3 个 manager/model 文件，而不是继续把所有逻辑塞进 `project.py`：

- `backend/app/models/material.py`
- `backend/app/models/baseline.py`
- `backend/app/models/forecast_run.py`

如果追求最低成本，也可以先在 `project.py` 中加 manager，但中长期仍建议拆出。

### 5.1.4 建议新增字段

对 `Project` 增加：

- `current_baseline_id`
- `active_run_id`
- `materials_count`
- `last_material_at`
- `incident_mode`  
  值建议：`demo_workflow | rolling_workspace`

`MaterialEntry` 建议字段：

- `material_id`
- `project_id`
- `source_type`  
  `file | web | manual | official_notice | media_report | social_post`
- `title`
- `source_url`
- `source_time`
- `ingested_at`
- `saved_filename`
- `extracted_text_path`
- `credibility`
- `tags`
- `summary`
- `used_in_baseline_ids`

`BaselineSnapshot` 建议字段：

- `baseline_id`
- `project_id`
- `based_on_material_ids`
- `created_at`
- `current_stage`
- `confirmed_facts`
- `unconfirmed_claims`
- `key_actors`
- `key_topics`
- `open_questions`
- `current_risks`
- `recommended_monitoring_signals`
- `previous_baseline_id`

`ForecastRun` 建议字段：

- `run_id`
- `project_id`
- `baseline_id`
- `parent_run_id`
- `branch_type`  
  `base | intervention_a | intervention_b | intervention_c`
- `branch_label`
- `simulation_id`
- `graph_id`
- `status`
- `forecast_horizon_hours`
- `created_at`
- `completed_at`
- `intervention_plan`
- `summary`

---

## 5.2 材料与基线 API 改造

### 5.2.1 当前问题

`backend/app/api/graph.py` 目前主要解决：

- 首次上传
- 首次本体生成
- 首次构图

缺少“滚动输入”相关 API。

### 5.2.2 建议新增路由模块

推荐新增：

- `backend/app/api/incident.py`

不要继续把滚动材料逻辑堆到 `graph.py`，否则会让 `graph.py` 同时承载：

- 项目管理
- 上传
- 本体
- 构图
- 增量材料
- 基线版本

复杂度会继续上升。

### 5.2.3 建议新增接口

#### 材料接入

- `POST /api/incident/project/<project_id>/materials/append`
  - 上传新增文件/手工文本/网页链接
  - 返回新增 `material_id[]`

- `GET /api/incident/project/<project_id>/materials`
  - 返回材料时间线

- `GET /api/incident/project/<project_id>/materials/<material_id>`
  - 返回单条材料详情

#### 基线管理

- `POST /api/incident/project/<project_id>/baseline/rebuild`
  - 基于选定材料重建当前事实基线

- `GET /api/incident/project/<project_id>/baseline/current`
  - 获取当前基线

- `GET /api/incident/project/<project_id>/baseline/history`
  - 获取历史基线版本

- `POST /api/incident/project/<project_id>/baseline/diff`
  - 对比两个基线版本，输出新增事实/变化事实/争议点变化

### 5.2.4 涉及文件

- `backend/app/api/incident.py` 新增
- `backend/app/models/project.py` 小改
- `backend/app/models/material.py` 新增
- `backend/app/models/baseline.py` 新增
- `backend/app/utils/file_parser.py` 复用
- `backend/app/services/text_processor.py` 复用

---

## 5.3 图谱改造蓝图

### 5.3.1 当前问题

`backend/app/services/graph_builder.py` 已支持 `add_text_batches()`，但当前产品流程没有明确的“增量导入材料”入口。

### 5.3.2 改造目标

图谱层要从“整图一次性构建”改成“两种模式并存”：

- `full_build`
- `incremental_patch`

### 5.3.3 建议新增能力

在 `GraphBuilderService` 中增加：

- `add_material_batches(graph_id, materials, batch_size, progress_callback)`
- `tag_material_data(graph_id, material_id, source_time, source_type)`
- `reindex_material_chunks(graph_id, material_id, chunks)`

### 5.3.4 图谱检索必须增加来源可追溯信息

图谱节点/边应尽量带上：

- `project_id`
- `material_id`
- `source_type`
- `source_time`
- `baseline_version`

否则后续在决策界面无法回答：

- 这个判断来自哪批材料
- 是昨天的事实还是刚追加的材料
- 这条关系是不是旧推断

### 5.3.5 建议新增图谱接口

如果不单独放在 `incident.py`，也至少要扩展：

- `POST /api/graph/project/<project_id>/refresh`
  - 参数：`mode = incremental | rebuild`
  - 参数：`material_ids[]`

### 5.3.6 涉及文件

- `backend/app/services/graph_builder.py`
- `backend/app/api/graph.py`
- `backend/app/services/vector_store.py`

---

## 5.4 模拟与预测分支改造

### 5.4.1 当前问题

当前 `simulation.py` / `simulation_manager.py` 更偏“生成一个模拟并运行”，核心主键是 `simulation_id`。

对于滚动预测场景，真正需要的是：

- 一个项目下可以有多个预测分支
- 每个预测分支绑定一个事实基线版本
- 每个分支可以有不同干预方案

### 5.4.2 建议新增路由模块

推荐新增：

- `backend/app/api/forecast.py`

不要继续把这些逻辑塞到 `simulation.py`，因为该文件已经非常大，且当前职责已过载。

### 5.4.3 建议新增接口

#### 预测分支

- `POST /api/forecast/run/create`
  - 输入：`project_id`, `baseline_id`, `branch_type`, `branch_label`
  - 输出：`run_id`

- `POST /api/forecast/run/<run_id>/prepare`
  - 复用现有 prepare 逻辑，但输入改为 `baseline_id`

- `POST /api/forecast/run/<run_id>/start`
  - 启动该预测分支

- `POST /api/forecast/run/<run_id>/recalibrate`
  - 当新增材料进入后，对当前运行的事实基线做校准

- `GET /api/forecast/run/<run_id>`
  - 返回分支元信息 + 关联 `simulation_id`

#### 分支比较

- `POST /api/forecast/compare`
  - 输入：`run_ids[]`
  - 输出：趋势对比、风险对比、建议差异、关键变量差异

### 5.4.4 对现有 `SimulationManager` 的改造要求

当前：

- `prepare_simulation()` 直接依赖 `document_text`
- `create_simulation()` 主要按 `project_id + knowledge_level` 复用

建议改成：

- `prepare_simulation(..., baseline_id, run_id)`
- `create_simulation(..., baseline_id=None, parent_run_id=None, branch_label=None)`

并让 `prepare` 阶段优先读取：

- 当前基线中的事实摘要
- 当前基线中的关键主体/关键话题
- 当前基线绑定的有效材料集合

而不是无差别读取项目全部 `document_text`。

### 5.4.5 对 `SimulationRunner` 的改造要求

当前：

- `resume` 是从旧轮次继续跑

建议增加：

- `recalibrate_from_baseline(run_id, baseline_id)`
- `fork_from_run(parent_run_id, intervention_plan)`

底层做法建议：

- 旧分支保持不变，避免覆盖历史结论
- 新校准后产生新 `run_id`
- 原 run 作为历史版本保留

即：

- `继续跑` 只用于同一事实前提下延长预测
- `校准后再预测` 必须创建新预测分支

### 5.4.6 涉及文件

- `backend/app/api/forecast.py` 新增
- `backend/app/services/simulation_manager.py`
- `backend/app/services/simulation_runner.py`
- `backend/app/models/forecast_run.py` 新增

---

## 5.5 世界状态与现实校准改造

### 5.5.1 当前问题

`world_state.py` 当前强项是：

- 根据 Agent 动作更新世界状态
- 检测事件
- 推断因果

弱点是：

- 缺少“现实进展回填”接口
- 缺少“事实层 vs 预测层”的显式区分

### 5.5.2 目标

世界状态应支持 3 类输入：

- Agent 行为驱动的自然演化
- 干预动作注入
- 现实新材料带来的事实校准

### 5.5.3 建议新增能力

在 `world_state.py` 中增加：

- `apply_reality_patch(baseline_snapshot)`
- `derive_state_patch_from_baseline_diff(prev_baseline, next_baseline)`
- `estimate_confidence_by_material_coverage()`

### 5.5.4 建议新增字段

世界状态与事件记录增加：

- `run_id`
- `branch_id`
- `state_source`  
  `simulated | injected | recalibrated`
- `confidence`

### 5.5.5 解释

这样做的好处是：

- 可以看清楚哪些变化是系统自己推出来的
- 哪些变化是现实材料反向校准带来的
- 为“预测偏差分析”提供依据

### 5.5.6 涉及文件

- `backend/app/services/world_state.py`
- `backend/app/services/causal_graph.py`

---

## 5.6 决策支持改造

### 5.6.1 当前问题

`simulation_insight_service.py -> get_decision_support_brief()` 已经能输出：

- 风险
- 机会
- 分阶段建议

但当前建议仍然：

- 较通用
- 不具备动作分支对比
- 与具体材料/事实证据的绑定还不够强

### 5.6.2 改造目标

将当前“简报”升级为“结构化行动建议引擎”。

### 5.6.3 建议新增输出结构

`DecisionBrief` 至少应包含：

- `current_diagnosis`
- `top_risks`
- `top_opportunities`
- `recommended_actions`
- `action_alternatives`
- `supporting_evidence`
- `monitoring_signals`
- `no_action_risk`
- `forecast_paths`

### 5.6.4 推荐动作的结构化字段

每个动作建议都应包含：

- `action_id`
- `title`
- `why_now`
- `target_groups`
- `expected_effects`
- `possible_side_effects`
- `required_prerequisites`
- `supporting_evidence_refs`
- `monitoring_metrics`
- `confidence`

### 5.6.5 动作模板库

建议新增一个动作模板层，而不是只靠文本建议：

例如高校舆情场景模板：

- 发布初步回应
- 发布完整通报
- 启动第三方调查
- 召开说明会
- 暂缓回应 12h / 24h
- 暂停涉事人员相关资格/权限
- 启动制度整改说明
- 组织权威背书与专家评估

这些模板先映射到：

- `trust_level`
- `panic_level`
- `polarization_level`
- `attention_level`

再由模拟与世界状态引擎继续外推。

### 5.6.6 涉及文件

- `backend/app/services/simulation_insight_service.py`
- `backend/app/api/forecast.py` 或 `backend/app/api/simulation.py`
- 新增 `backend/app/services/intervention_library.py`

---

## 5.7 报告系统定位调整

### 5.7.1 当前问题

`report_agent.py` 功能很强，但当前默认位置过高。

对于真实高校舆情场景，高频需求不应该先是长报告，而应是：

- 当前态势卡
- 未来路径预测卡
- 推荐动作卡
- 分支比较卡

### 5.7.2 建议定位

将 `report_agent.py` 调整为：

- `导出模式`
- `归档模式`
- `汇报材料模式`

不要作为高频主入口。

### 5.7.3 建议改法

- 保留 `backend/app/api/report.py`
- 保留 `report_agent.py`
- 但前端默认不在主工作台里自动触发长报告生成
- 只在需要对外汇报/比赛展示时点击“导出完整报告”

---

## 5.8 图谱记忆更新的重新定位

### 5.8.1 当前问题

`graph_memory_updater.py` 当前会把模拟中的 Agent 行为写回图谱。

这对实验展示有价值，但对滚动预测的真实场景有一个大风险：

- 混淆真实材料与模拟衍生内容

### 5.8.2 建议策略

#### MVP 阶段

- 默认关闭 `enable_graph_memory_update`
- 不让模拟行为污染事实图谱

#### V2 阶段

如果要保留，必须做隔离：

- 写入独立 `memory_graph_id`
- 或为所有模拟写入内容打上：
  - `source = simulation`
  - `run_id`
  - `branch_id`
  - `excluded_from_fact_baseline = true`

### 5.8.3 结论

该模块应保留，但在真实决策工作流中：

- **不应作为默认主链路能力**

---

## 6. 前端改造蓝图

## 6.1 总体策略

- 保留 `Process.vue` 作为演示模式
- 新增“事件工作台”视图作为真实工作入口

### 6.1.1 建议新增视图

- `frontend/src/views/IncidentWorkspaceView.vue`

### 6.1.2 路由建议

新增：

- `/incident/:projectId`

用于承载长期工作的事件空间。

---

## 6.2 工作台布局建议

建议采用三栏或两栏工作台：

### 左栏：材料与事实层

- 材料时间线
- 当前材料批次
- 事实基线
- 基线版本 diff

### 中栏：态势与预测层

- 当前世界状态
- 未来 24h / 72h / 1 周预测路径
- 关键风险变量折线图
- 分支对比结果

### 右栏：动作与决策层

- 推荐动作 Top 3
- 动作 A/B/C 比较
- 支持证据
- 监测信号
- 导出报告入口

---

## 6.3 前端组件拆分建议

建议新增以下组件：

- `frontend/src/components/incident/MaterialsTimelinePanel.vue`
- `frontend/src/components/incident/BaselineSnapshotPanel.vue`
- `frontend/src/components/incident/BaselineDiffDrawer.vue`
- `frontend/src/components/incident/ForecastRunPanel.vue`
- `frontend/src/components/incident/ForecastComparePanel.vue`
- `frontend/src/components/incident/DecisionBriefPanel.vue`
- `frontend/src/components/incident/InterventionPlannerPanel.vue`
- `frontend/src/components/incident/MonitoringSignalsPanel.vue`

### 复用建议

当前 Step 组件可复用其中一部分逻辑：

- `Step1GraphBuild.vue`
  - 抽出上传/本体/图谱构建相关子逻辑
- `Step3Simulation.vue`
  - 抽出世界状态图表与模拟运行状态图表
- `Step4Report.vue`
  - 降级为“导出报告抽屉”
- `Step5Interaction.vue`
  - 改为“分析师问答侧栏”

---

## 6.4 前端 API 层改造

### 6.4.1 当前 API 分布

- `frontend/src/api/graph.js`
- `frontend/src/api/simulation.js`
- `frontend/src/api/report.js`
- `frontend/src/api/evaluation.js`

### 6.4.2 建议新增 API 文件

为了避免 `graph.js` / `simulation.js` 继续膨胀，建议新增：

- `frontend/src/api/incident.js`
- `frontend/src/api/forecast.js`

### 6.4.3 incident.js 建议方法

- `appendMaterials(projectId, formData)`
- `listMaterials(projectId)`
- `getCurrentBaseline(projectId)`
- `rebuildBaseline(projectId, data)`
- `diffBaselines(projectId, data)`

### 6.4.4 forecast.js 建议方法

- `createForecastRun(data)`
- `prepareForecastRun(runId, data)`
- `startForecastRun(runId, data)`
- `recalibrateForecastRun(runId, data)`
- `compareForecastRuns(data)`
- `getDecisionBrief(runId)`
- `evaluateInterventions(runId, data)`

---

## 7. 对现有功能的取舍建议

## 7.1 保留但降级到“验证层/展示层”

- Benchmark 三层评分
  - `benchmark/`
  - `frontend/src/api/evaluation.js`
- 知识门控 `knowledge_level`
- 全量长报告自动生成

这些模块继续保留，但不应再成为主工作台的核心动作。

## 7.2 保留但重命名/弱化技术暴露

- Twitter / Reddit 双平台仿真

底层可以保留，但前端表达建议改成：

- 传播场域 A / B
- 讨论层 / 社交层
- 开放舆论层 / 深度讨论层

避免用户心智被技术设定带偏。

## 7.3 默认隐藏到高级设置

- `enable_graph_memory_update`
- `post_sim_graph_import`
- 原始 `inject-event` 的变量级参数

这些更适合高级用户或研发调试。

---

## 8. 推荐实施顺序

## Phase 1：滚动材料闭环 MVP

### 目标

让同一 `project_id` 支持多次追加材料，并生成版本化基线。

### 需要修改/新增的文件

- `backend/app/models/project.py`
- `backend/app/models/material.py` 新增
- `backend/app/models/baseline.py` 新增
- `backend/app/api/incident.py` 新增
- `frontend/src/api/incident.js` 新增
- `frontend/src/views/IncidentWorkspaceView.vue` 新增
- `frontend/src/components/incident/MaterialsTimelinePanel.vue` 新增
- `frontend/src/components/incident/BaselineSnapshotPanel.vue` 新增

### 完成标志

- 一个项目可追加多批材料
- 每批材料可追溯
- 可查看当前基线和历史基线

---

## Phase 2：预测分支与校准闭环

### 目标

让“新增材料后重新预测”变成标准动作，而不是人工重新跑一遍。

### 需要修改/新增的文件

- `backend/app/models/forecast_run.py` 新增
- `backend/app/api/forecast.py` 新增
- `backend/app/services/simulation_manager.py`
- `backend/app/services/simulation_runner.py`
- `backend/app/services/world_state.py`
- `frontend/src/api/forecast.js` 新增
- `frontend/src/components/incident/ForecastRunPanel.vue` 新增
- `frontend/src/components/incident/ForecastComparePanel.vue` 新增

### 完成标志

- 同一事件下可创建多个预测分支
- 新材料进入后可生成新的校准分支
- 可比较两个预测分支的结果差异

---

## Phase 3：干预动作与动作对比

### 目标

把“上帝视角事件注入”升级成真正的“行动方案评估”。

### 需要修改/新增的文件

- `backend/app/services/intervention_library.py` 新增
- `backend/app/services/simulation_insight_service.py`
- `backend/app/api/forecast.py`
- `frontend/src/components/incident/InterventionPlannerPanel.vue` 新增
- `frontend/src/components/incident/DecisionBriefPanel.vue` 新增

### 完成标志

- 支持动作 A/B/C 创建分支
- 每个动作给出收益、风险、副作用、证据、监测指标
- 可以推荐当前最优动作

---

## Phase 4：报告与比赛能力重定位

### 目标

保留展示能力，但不干扰主链路。

### 需要修改/新增的文件

- `frontend/src/components/Step4Report.vue`
- `frontend/src/components/Step5Interaction.vue`
- `frontend/src/views/Process.vue`
- `backend/app/services/report_agent.py`

### 完成标志

- 长报告改为导出模式
- 工作台以决策卡片为主，不以长文为主
- Benchmark 保持独立展示入口

---

## 9. 验收标准

完成本蓝图后，系统至少应满足以下业务验收标准：

- 同一项目可以连续追加 3 次以上新材料，且每次不丢历史记录
- 每次追加材料后都能生成新的基线版本和版本 diff
- 用户可以看到“当前事实基线”和“上一版本基线”的差异
- 系统可以基于新基线重新生成预测分支，而不是只能从旧轮次 resume
- 用户可以创建至少 2 个不同干预方案分支并比较结果
- 每个建议动作都有支撑证据、风险、副作用和监测信号
- 模拟内容不会默认污染事实图谱
- 长报告不再阻塞主工作流

---

## 10. 最终建议

### 10.1 立刻开始做的事

优先顺序建议如下：

1. 先做材料时间线与基线版本化
2. 再做预测分支与校准
3. 然后做干预动作 A/B/C 比较
4. 最后重整长报告与比赛层展示

### 10.2 不建议现在优先做的事

- 继续扩大 Benchmark 体系复杂度
- 继续强化盲测/门控在主产品流程中的权重
- 继续让长报告成为主入口
- 默认开启模拟写回事实图谱

### 10.3 这份蓝图的核心原则

从现在开始，NexusMind 的主产品逻辑应从：

- “单次跑完的演示流程”

转为：

- “围绕事件持续更新、持续预测、持续辅助决策的工作台”

---

## 11. 与当前代码的最小冲突实施方案

如果希望尽量少改已有系统，推荐如下策略：

- 保留现有 `Process.vue` 与 Step1~5 作为 `Demo Mode`
- 新增 `IncidentWorkspaceView.vue` 作为 `Ops Mode`
- 保留 `ProjectManager` 文件存储方式，不上数据库
- 新增 `incident.py` / `forecast.py` 两个 API 模块
- 禁止 Phase 1 直接重写现有 `simulation.py`
- `report_agent.py` 暂不重构，只调整触发位置

这是最稳、成本最低、最不容易把现有 demo 跑坏的路线。
