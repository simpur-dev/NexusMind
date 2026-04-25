# NexusMind 高校突发舆情应急处置 · 完整操作手册

> 本手册基于 NexusMind 系统全部已实现能力编写，每一步均映射到真实的 API 端点、后端服务和前端入口。
> 适用场景：高校在接到/发现突发舆情后，使用本系统辅助态势研判、推演预测和处置决策。

---

## 全流程概览

```
  ┌───────────────────────────────────────────────────────────────────────┐
  │                       事件生命周期闭环                                  │
  │                                                                       │
  │  T+0min       T+10min        T+30min        T+1h         T+2h+       │
  │  ┌────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌─────┐     │
  │  │录入 │────▶│基线  │────▶│推演  │────▶│决策  │────▶│报告 │     │
  │  │种子 │     │建模  │     │预测  │     │简报  │     │生成 │     │
  │  └────┘     └──────┘     └──────┘     └──────┘     └─────┘     │
  │     │            │            │             │           │           │
  │     │            ▼            ▼             ▼           │           │
  │     │       ┌──────┐    ┌──────┐     ┌──────┐         │           │
  │     │       │图谱  │    │比较  │     │执行  │         │           │
  │     │       │重建  │    │分支  │     │动作  │         │           │
  │     │       └──────┘    └──────┘     └──────┘         │           │
  │     │                                    │              │           │
  │     │◀──────── 新材料进入 ◀───────────────┘              │           │
  │     │            （滚动循环）                              │           │
  └───────────────────────────────────────────────────────────────────────┘
```

---

## 第一阶段：事件录入（T+0 ~ T+10min）

### 目标
在最短时间内将已知信息录入系统，让 AI 形成第一版态势判断。

### 操作方式

#### 方式 A：通过首页创建（适合有原始文件的情况）

1. 打开首页 `http://localhost:3000/`
2. 选择**"文件上传"**或**"网络抓取"**
3. 上传种子材料（PDF/MD/TXT）或输入搜索关键词
4. 填写**模拟提示词**（事件背景描述 + 想回答的决策问题）
5. 点击启动 → 系统自动执行：
   - 文本提取（`TextProcessor`）
   - 本体生成（`OntologyGenerator` → LLM 识别实体类型和关系类型）
   - 图谱构建（`GraphBuilder` → 实体抽取、关系抽取、向量化存储）
6. 完成后进入 `/process/:projectId` 五步流程，或直接跳转工作台

```
后端链路：
  POST /api/graph/ontology/generate
    → TextProcessor.extract_text()
    → OntologyGenerator.generate_ontology()
  POST /api/graph/build
    → GraphBuilder.build_graph()
    → VectorStore.add_documents()
```

#### 方式 B：直接进入事件工作台（适合快速启动）

1. 调用轻量创建接口或使用已有项目
2. 进入 `http://localhost:3000/incident/:projectId`
3. 若项目已有文本，系统**自动引导**：
   - 检测到工作台无材料但项目有 extracted_text
   - 自动调用 Bootstrap 导入为第一批材料
   - 可选：自动触发基线重建

```
后端链路：
  POST /api/incident/project/create            ← 创建项目
  POST /api/incident/project/<id>/bootstrap    ← 自动导入种子
```

#### 方式 C：网络搜索（无现有文件时）

如果事发后仅有零散信息，可用 Tavily 搜索引擎自动抓取公开舆情：
- 首页选择"网络抓取"模式
- 输入关键词（如"XX大学 XX事件"）
- 系统自动搜索中文舆情优先域名（知乎/微博/澎湃/央视/凤凰等 20+ 来源）
- 抓取结果作为种子材料写入项目

```
后端链路：
  POST /api/graph/ontology/generate-from-web
    → WebScraper.search_and_extract()
    → 搜索结果 → 文本合并 → 本体生成
```

### 时间要求
- 文件上传方式：**3-5 分钟**（含上传 + 本体 + 图谱）
- 网络抓取方式：**5-8 分钟**（含搜索 + 提取 + 本体 + 图谱）
- 工作台直接启动：**< 1 分钟**

---

## 第二阶段：事实基线建立（T+10min ~ T+20min）

### 目标
让系统形成结构化的"当前事实认知"，包括已确认事实、关键主体、核心风险等。

### 操作步骤

1. 在事件工作台左栏确认材料已导入（材料时间线显示条目）
2. 点击**"重建"**按钮（或系统在引导后自动执行）
3. 系统自动执行：
   - 收集全部材料文本（`MaterialManager.get_combined_text()`）
   - 调用 LLM 提取结构化信息（`_llm_analyze_materials()`）
   - 生成 BaselineSnapshot（v1, v2, ...）
   - **同步触发异步图谱重建**：合并全部材料 → `GraphBuilderService` 重建图谱 + `VectorStore` 重建向量索引
4. 工作台实时显示图谱重建进度条

### LLM 自动提取的 8 个维度

| 字段 | 含义 | 示例 |
|------|------|------|
| `current_stage` | 事件所处阶段 | 爆发期 / 发酵期 / 平台期 / 消退期 / 二次爆发 |
| `confirmed_facts` | 已确认事实列表 | "X月X日，某某发布举报信…" |
| `unconfirmed_claims` | 未确认说法 | "网传…（待核实）" |
| `key_actors` | 关键主体 | 举报人、当事人、校方、教育部… |
| `key_topics` | 核心话题 | 师德师风、学术不端、权力制约… |
| `open_questions` | 待解答问题 | "调查进展？""处分是否合理？" |
| `current_risks` | 当前风险 | "舆情升级""学生二次伤害"… |
| `recommended_monitoring_signals` | 建议监测信号 | "教育部官网""涉事论文撤稿状态"… |

```
后端链路：
  POST /api/incident/project/<id>/baseline/rebuild
    → MaterialManager.get_combined_text()
    → _llm_analyze_materials() [LLMClient, temperature=0.3]
    → BaselineManager.create_baseline()
    → 异步：GraphBuilderService 重建图谱 + VectorStore 重建索引
    → 返回 { baseline, graph_task_id }
    → 轮询 GET /api/graph/task/<graph_task_id> 查看图谱进度
```

### 输出验证
- 左栏基线列表出现 **v1**，显示阶段标签（如"发酵期"）和时间
- 点击基线展开详情：查看已确认事实（前 5 条）、关键主体标签（前 8 个）、风险列表（前 3 条）
- 图谱重建进度条走完后，新材料的实体/关系已纳入图谱
- **关键检查**：确认事实是否准确？主体识别是否完整？风险是否合理？

---

## 第三阶段：多智能体推演模拟（T+20min ~ T+1h）

### 目标
创建预测分支，让系统用 Multi-Agent 模拟推演舆情未来走势。

### 操作步骤

1. 在工作台中栏点击**"新建分支"**
2. 输入分支名称（如"基线预测 v1"），自动关联当前选中基线
3. 系统创建 ForecastRun → 关联底层 Simulation
4. 点击**"准备"**按钮：
   - 从基线材料中提取实体
   - LLM 生成各 Agent 画像（`OasisProfileGenerator`）
     - 每个 Agent 有：名称、职业、MBTI、价值观、立场
     - 画像来源于图谱中的真实实体关系
   - 生成模拟配置（`SimulationConfigGenerator`）
     - Twitter 平台 + Reddit 平台双通道仿真
     - 环境参数、Agent 数量、交互规则
   - 写入运行目录
5. 准备完成后**输入模拟轮数**，点击**"启动"**：
   - `SimulationRunner` 按指定轮数运行多轮模拟
   - 每一轮（round）中所有 Agent 自主决策发帖/评论/转发
   - `WorldStateEngine` 每轮计算 6 维世界状态
   - `CausalGraphEngine` 追踪事件因果链
   - 实时状态回写到每个 Agent 的 prompt

### 6 维世界状态模型

```
                    ┌────────────┐
          ┌────────▶│ attention  │ 关注度/热度
          │         │  level     │
          │         └────────────┘
          │         ┌────────────┐
          ├────────▶│  panic     │ 恐慌/负面情绪
  每轮    │         │  level     │
  Agent   │         └────────────┘
  行为    │         ┌────────────┐
  ──────▶├────────▶│  trust     │ 信任度
  信号    │         │  level     │
  提取    │         └────────────┘
          │         ┌────────────┐
          ├────────▶│polarization│ 极化程度
          │         │  level     │
          │         └────────────┘
          │         ┌────────────┐
          ├────────▶│   risk     │ 综合风险
          │         │  level     │
          │         └────────────┘
          │         ┌────────────┐
          └────────▶│ stability  │ 系统稳定性
                    │  level     │
                    └────────────┘
```

### Agent 大脑决策模型

每个 Agent（`AgentBrain`）在每轮都会接收：
- 自身画像（背景、立场、价值观）
- 当前世界状态（6 维）
- 最近可见的帖子/评论
- 自身社交网络关系

然后决策：是否发帖？内容是什么？是否转发/评论？立场是否改变？

```
后端链路：
  POST /api/forecast/run/create                    ← 创建分支
  POST /api/incident/project/<id>/forecast/create  ← 工作台创建分支（关联基线）
  POST /api/forecast/run/<id>/prepare              ← 准备模拟环境（异步）
  GET  /api/forecast/run/<id>/status               ← 轮询准备/运行进度
  POST /api/forecast/run/<id>/start                ← 启动推演（可指定 rounds）
```

---

## 第四阶段：态势研判与决策输出（T+1h ~ T+2h）

### 目标
从模拟结果中提取可行动的决策建议。**所有决策数据均感知当前选中基线**——切换不同基线（如"发酵期"vs"爆发期"），展示内容会实质性变化。

### 4.1 查看当前态势（基线感知）

工作台中栏显示 6 维状态条形图。当选中不同基线时，系统根据基线阶段自动调整世界状态展示：
- 爆发期 → 关注度↑ 恐慌↑ 信任↓ 风险↑
- 发酵期 → 极化↑ 关注度↑ 稳定性↓
- 消退期 → 关注度↓ 恐慌↓ 稳定性↑ 信任↑

### 4.2 获取结构化决策简报（基线感知）

点击右栏**"获取决策简报"**，系统传入 `baseline_id` 生成全部基线感知的决策数据。切换基线后**自动刷新**：

#### 当前态势诊断（`current_diagnosis`）
- 整体状态评估（良好/警戒/危险）
- 6 维状态精确值 + 近期趋势方向

#### 推荐动作 Top-3（`recommended_actions`）

系统内置 **8 种高校舆情干预动作模板**，根据当前世界状态 + **基线阶段加成** 自动匹配最优 Top-3：

| 动作模板 | 类型 | 适用时机 |
|----------|------|---------|
| 发布初步回应 | response | 事件曝光初期 0-6h，信息真空时 |
| 发布完整通报 | response | 初步回应后 12-48h，事实调查完成后 |
| 启动第三方调查 | investigation | 公众对自查不信任时 |
| 召开说明会/恳谈会 | communication | 中期，情绪有所回落但仍有疑虑 |
| 暂缓回应 12 小时 | response | 事实不清、仓促回应风险 > 沉默风险 |
| 暂停涉事人员资格 | suspension | 涉事人员在岗持续刺激情绪 |
| 启动制度整改说明 | reform | 收尾期，公众期待根源性改进 |
| 组织权威背书与专家评估 | communication | 公众不信任当事方单方面说法时 |

**阶段加成机制（`STAGE_ACTION_BOOST`）**：不同阶段对动作有大幅加分/减分，确保推荐排序差异化。例如：
- **爆发期** → 初步回应(+0.5)、暂缓回应(+0.3)；制度整改(-0.3)
- **发酵期** → 完整通报(+0.4)、第三方调查(+0.3)；暂缓回应(-0.4)
- **消退期** → 制度整改(+0.5)、权威背书(+0.3)；初步回应(-0.5)

每个推荐包含：
- **why_now**：为什么此刻适合
- **expected_effects**：预期正面效果
- **possible_side_effects**：潜在副作用
- **required_prerequisites**：前置条件
- **monitoring_metrics**：执行后监测什么
- **estimated_delay_hours**：效果显现时间
- **state_effects**：对 6 维状态的量化影响
- **confidence**：置信度评分

#### 不作为风险评估（`no_action_risk`）——基线感知

综合世界状态 + 基线阶段 + 基线已识别风险数量计算：
- **风险评分** 0~100%（阶段加成：爆发期+25%，发酵期+15%，二次爆发+30%）
- **具体原因列表**：包含状态数据（如"信任度仅 31%"）+ 阶段风险（如"事件处于爆发期，不回应将严重损害公信力"）+ 基线风险（如"基线识别 5 项风险需应对"）
- **建议**：强烈建议立即行动 / 建议 24h 内行动 / 可观望但需持续监测

#### 预测路径（`forecast_paths`）——阶段感知

三种路径对比，每条路径包含丰富中文描述：

| 路径 | 内容字段 |
|------|---------|
| 自然演化（不干预） | `risk_level`(高/中/低) + `description` + `key_changes`(关键变化列表) + `outcome` + `probability`(可能性) |
| 积极干预 | 同上 |
| 保守应对 | 同上 |

路径的**可能性评估**会根据基线阶段差异化：
- 爆发期 → 积极干预可能性"较大"，自然演化可能性"较小"
- 消退期 → 三种路径可能性相对均衡

#### 监测信号（`monitoring_signals`）——基线感知

三重来源的监测信号：
1. **世界状态信号**：信任度低于安全线、恐慌持续上升、极化过高、关注度快速上升、稳定性不足
2. **阶段特定信号**：
   - 爆发期 → "密切监测舆情扩散速度""关注官方回应时效（黄金6小时）"
   - 发酵期 → "监测二次传播渠道和意见领袖动态""关注极化趋势和对立阵营形成"
   - 消退期 → "关注长尾效应和制度改进落实"
3. **基线风险信号**：将基线识别的风险条目转化为高优先级监测项

```
后端链路：
  GET /api/forecast/run/<id>/decision-brief?baseline_id=bl_xxx
    → 加载基线上下文（current_stage, confirmed_facts, current_risks, ...）
    → SimulationInsightService.get_structured_decision_brief(baseline_context)
    → InterventionLibrary.recommend_actions(current_state, stage)  [阶段加成]
    → _assess_no_action_risk(state, trends, baseline_risks, stage)
    → _extrapolate_forecast_paths(state, trends, stage)
    → _derive_monitoring_signals(state, trends, baseline_risks, stage)

  GET /api/forecast/run/<id>/recommend-actions
    → InterventionLibrary.recommend_actions()
```

### 4.3 干预方案评估（可选）

如果决策者想评估特定组合动作的效果：

1. 选择多个动作模板
2. 系统计算组合效果（`evaluate_intervention_plan`）：
   - 各动作独立效果
   - 组合后 6 维状态预期变化
   - 冲突检测（若两个动作对同一变量方向相反则告警）
   - 投射新状态

```
后端链路：
  GET  /api/forecast/interventions                    ← 查看全部模板
  POST /api/forecast/run/<id>/evaluate-interventions  ← 评估组合效果
```

---

## 第五阶段：分支对比推演（T+2h ~ T+4h）

### 目标
对"不同动作方案"创建平行预测分支，量化比较效果差异。

### 操作步骤

1. 基于同一基线创建多个分支：
   - 分支 A：发布初步回应 + 暂停涉事人员
   - 分支 B：暂缓回应 12 小时 + 启动第三方调查
   - 分支 C：不干预（对照组）
2. 每个分支独立执行 prepare → start → 运行模拟
3. 运行完成后，调用分支对比接口：

```
后端链路：
  POST /api/forecast/compare
    body: { "run_ids": ["run_a", "run_b", "run_c"] }
    → 对比各分支的 WorldState 终态
    → 输出各维度差异 + 综合排名
```

对比结果展示在工作台中栏"预测路径"区域，直观看到：
- 哪个方案的 trust_level 恢复最好
- 哪个方案的 risk_level 降到最低
- 哪个方案的整体评分最优

---

## 第六阶段：现实进展追踪与滚动更新（T+6h ~ 持续）

### 目标
事件持续发展时，持续喂入新信息，系统滚动更新判断。

### 滚动循环步骤

```
 新材料 ──▶ 追加材料 ──▶ 重建基线(v2) ──▶ 图谱更新 ──▶ 切换基线 ──▶ 新决策简报
    ▲            │                              │                          │
    │            └── 基线 Diff ──▶ 校准预测 ────┘                          │
    │                                                                      │
    └──────────────────── 持续循环 ◀───────────────────────────────────────┘
```

#### 6.1 追加新材料

```
操作：工作台左栏 → "追加材料"
  - 上传新文件（官方通报 PDF、媒体报道截图转文字等）
  - 或手动输入文本（粘贴最新消息）

后端：POST /api/incident/project/<id>/materials/append
```

#### 6.2 重建基线 + 图谱自动更新

```
操作：工作台左栏 → "重建" 按钮
  - LLM 重新分析全部材料（旧 + 新），生成新版本基线（v2, v3, ...）
  - 同步触发图谱异步重建（合并全部材料 → GraphBuilder → VectorStore）
  - 前端显示图谱重建进度条，重建按钮禁用直到完成

后端：POST /api/incident/project/<id>/baseline/rebuild
  → 返回 { baseline, graph_task_id }
  → 轮询 GET /api/graph/task/<graph_task_id> 查看图谱进度
```

#### 6.3 切换基线查看差异

```
操作：点击左栏不同版本基线，工作台自动切换视角：
  - 当前态势 → 按新基线阶段调整展示
  - 决策简报 → 自动刷新（推荐动作、不作为风险、监测信号全部差异化）
  - 预测路径 → 可能性评估随阶段变化

对比操作：
  后端：POST /api/incident/project/<id>/baseline/diff
    body: { "baseline_a_id": "bl_v1", "baseline_b_id": "bl_v2" }
    返回：新增事实、移除事实、阶段变化、主体变化
```

#### 6.4 校准预测

若之前有进行中的预测分支，新基线进入后可做现实校准：

```
后端：POST /api/forecast/run/<id>/recalibrate
  - 对比新旧基线 Diff
  - 生成 reality_patch 应用到 WorldStateEngine
  - 创建新的 ForecastRun（类型 = recalibrated）
  - 原分支标记为 superseded
```

---

## 第七阶段：深度交互与报告归档（按需）

### 7.1 与模拟角色对话

进入 `/process/:projectId?step=5`（第 5 步深度互动）：
- 选择任意 Agent（如"举报学生""校方发言人""围观网民"）
- 以第一人称对话，了解该角色视角下的态势感知
- Agent 回复严格基于其画像和模拟行为历史，不编造
- 支持**批量采访**和**全员采访**（相同问题同时发给多个/全部 Agent）

```
后端链路：
  POST /api/simulation/interview          ← 单个 Agent 采访
  POST /api/simulation/interview/batch    ← 批量采访
  POST /api/simulation/interview/all      ← 全员采访
  POST /api/simulation/interview/history  ← 查看历史
    → system_prompt 包含角色画像 + 背景知识 + 历史发言
    → temperature=0.4, max_tokens=512
    → 严禁编造不在资料中的信息
```

### 7.2 与报告助手对话

选择 Report Agent 对话，可追问：
- "当前最大的风险是什么？"
- "如果明天校方不回应会怎样？"
- "帮我拟一份对外通报的要点"

```
后端链路：
  POST /api/report/chat
    → ReportAgent 使用图谱搜索 + 世界状态作为上下文
```

### 7.3 生成完整报告（基线感知 · 归档/汇报用）

```
操作：工作台顶栏 → "导出报告" → "前往报告生成"
  - 自动携带当前选中基线 ID 跳转到 /process/:id?step=4&baseline_id=bl_xxx
  - Step4Report 自动触发报告生成（传入 baseline_id）
  - ReportAgent 在规划大纲和生成章节时感知基线上下文
    （已确认事实、识别风险、关键行动者、核心议题、事件阶段）
  - 不同基线生成不同内容的报告

后端链路：
  POST /api/report/generate
    body: { simulation_id, baseline_id, force_regenerate }
    → 加载基线上下文 → 追加到 simulation_requirement
    → ReportAgent（分章节 ReACT 模式 + 全文润色）
  GET  /api/report/<id>/progress     ← 实时进度
  GET  /api/report/<id>/sections     ← 分章节获取（实时输出）
  GET  /api/report/<id>/agent-log    ← Agent 执行日志
  GET  /api/report/<id>/console-log  ← 控制台日志
  GET  /api/report/<id>/download     ← 下载 Markdown
```

---

## 速查：按时间节点的操作清单

### T+0min（事件发生）
- [ ] 收集已知信息（截图、文件、链接）
- [ ] 打开 NexusMind，上传种子材料或输入关键词
- [ ] 填写事件背景描述

### T+10min（材料入库）
- [ ] 确认材料已导入工作台
- [ ] 触发基线重建（同时自动更新图谱）
- [ ] 等待图谱重建进度条完成
- [ ] 检查基线摘要：事实、主体、风险是否准确

### T+20min（推演启动）
- [ ] 创建预测分支（自动关联当前基线）
- [ ] 准备 → 输入轮数 → 启动模拟
- [ ] 等待推演完成（约 15-30min）

### T+1h（第一轮决策）
- [ ] 获取决策简报（自动传入当前基线）
- [ ] 查看推荐动作 Top-3（阶段敏感排序）
- [ ] 评估不作为风险（含阶段加成）
- [ ] 查看三种路径预测（含关键变化 + 可能性）
- [ ] 查看监测信号（含阶段特定信号）
- [ ] 确定第一步处置行动

### T+2h ~ T+6h（分支对比 + 报告）
- [ ] 为不同方案创建分支推演
- [ ] 对比各方案结果
- [ ] 选定最优方案
- [ ] 导出报告（携带当前基线 → 报告内容差异化）

### T+6h+（滚动追踪）
- [ ] 每当有新进展，追加材料
- [ ] 重建基线（自动更新图谱）
- [ ] 切换基线查看差异（决策简报自动刷新）
- [ ] 校准预测分支
- [ ] 循环直到事件结束

---

## 速查：全部 API 端点一览

### 项目 & 材料（incident.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/incident/project/create` | 轻量创建项目 |
| POST | `/api/incident/project/<id>/materials/append` | 追加材料 |
| GET | `/api/incident/project/<id>/materials` | 材料时间线 |
| GET | `/api/incident/project/<id>/materials/<mid>` | 单条材料详情 |
| POST | `/api/incident/project/<id>/bootstrap` | 自动导入种子 |
| GET | `/api/incident/project/<id>/overview` | 工作台概览 |

### 基线（incident.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/incident/project/<id>/baseline/rebuild` | 重建基线 + 异步图谱更新 |
| GET | `/api/incident/project/<id>/baseline/current` | 当前基线 |
| GET | `/api/incident/project/<id>/baseline/history` | 历史版本 |
| POST | `/api/incident/project/<id>/baseline/diff` | 版本对比 |
| DELETE | `/api/incident/project/<id>/baseline/<bl_id>` | 删除基线 |

### 预测分支（forecast.py + incident.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/forecast/run/create` | 创建分支 |
| POST | `/api/incident/project/<id>/forecast/create` | 工作台创建分支（关联基线） |
| GET | `/api/incident/project/<id>/forecast/list` | 工作台分支列表 |
| GET | `/api/incident/project/<id>/forecast/<run_id>` | 单个分支详情 |
| POST | `/api/forecast/run/<id>/prepare` | 准备模拟 |
| POST | `/api/forecast/run/<id>/start` | 启动推演 |
| GET | `/api/forecast/run/<id>/status` | 运行状态 |
| POST | `/api/forecast/run/<id>/recalibrate` | 现实校准 |
| POST | `/api/forecast/compare` | 分支对比 |
| POST | `/api/incident/project/<id>/forecast/compare` | 工作台分支对比 |

### 决策支持（forecast.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/forecast/interventions` | 干预模板库（8 种） |
| POST | `/api/forecast/run/<id>/evaluate-interventions` | 评估动作组合 |
| GET | `/api/forecast/run/<id>/decision-brief?baseline_id=` | 决策简报（基线感知） |
| GET | `/api/forecast/run/<id>/recommend-actions` | 推荐动作 |

### 图谱 & 本体（graph.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/graph/project/<id>` | 获取项目详情 |
| GET | `/api/graph/project/list` | 项目列表 |
| DELETE | `/api/graph/project/<id>` | 删除项目 |
| POST | `/api/graph/project/<id>/reset` | 重置项目状态 |
| POST | `/api/graph/ontology/generate` | 上传文件生成本体 |
| POST | `/api/graph/ontology/generate-from-web` | 网络搜索生成本体 |
| POST | `/api/graph/build` | 构建知识图谱 |
| GET | `/api/graph/data/<graph_id>` | 获取图谱数据 |
| DELETE | `/api/graph/delete/<graph_id>` | 删除图谱 |
| POST | `/api/graph/graph/<graph_id>/annotate` | 追加实体标注 |
| GET | `/api/graph/task/<task_id>` | 查询任务状态 |

### 模拟管理（simulation.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/simulation/create` | 创建模拟 |
| POST | `/api/simulation/prepare` | 准备模拟（LLM 智能配置） |
| POST | `/api/simulation/prepare/status` | 准备进度 |
| POST | `/api/simulation/start` | 启动模拟运行 |
| POST | `/api/simulation/stop` | 停止模拟 |
| GET | `/api/simulation/<id>` | 获取模拟状态 |
| DELETE | `/api/simulation/<id>` | 删除模拟 |
| GET | `/api/simulation/list` | 列出所有模拟 |
| GET | `/api/simulation/history` | 历史模拟（含项目详情） |
| GET | `/api/simulation/<id>/run-status` | 运行实时状态 |
| GET | `/api/simulation/<id>/run-status/detail` | 运行详细状态 |

### 模拟数据（simulation.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/simulation/<id>/profiles` | Agent 画像 |
| GET | `/api/simulation/<id>/profiles/realtime` | 实时 Agent 画像 |
| GET | `/api/simulation/<id>/config` | 模拟配置 |
| GET | `/api/simulation/<id>/config/realtime` | 实时模拟配置 |
| GET | `/api/simulation/<id>/actions` | Agent 动作历史 |
| GET | `/api/simulation/<id>/timeline` | 按轮次汇总时间线 |
| GET | `/api/simulation/<id>/agent-stats` | Agent 统计 |
| GET | `/api/simulation/<id>/posts` | 帖子数据 |
| GET | `/api/simulation/<id>/comments` | 评论数据 |
| GET | `/api/simulation/<id>/world-state` | 世界状态历史 |
| GET | `/api/simulation/<id>/events` | 世界事件时间线 |
| GET | `/api/simulation/<id>/causal-graph` | 因果图谱 |
| GET | `/api/simulation/entities/<graph_id>` | 图谱实体 |

### 模拟交互（simulation.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/simulation/interview` | 采访单个 Agent |
| POST | `/api/simulation/interview/batch` | 批量采访 |
| POST | `/api/simulation/interview/all` | 全员采访 |
| POST | `/api/simulation/interview/history` | 采访历史 |
| POST | `/api/simulation/inject-event` | 事件注入（上帝视角） |
| POST | `/api/simulation/env-status` | 模拟环境状态 |
| POST | `/api/simulation/close-env` | 关闭模拟环境 |

### 报告（report.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/report/generate` | 生成报告（支持 baseline_id） |
| POST | `/api/report/generate/status` | 生成进度 |
| GET | `/api/report/<id>` | 报告详情 |
| GET | `/api/report/<id>/progress` | 实时进度 |
| GET | `/api/report/<id>/sections` | 分章节获取 |
| GET | `/api/report/<id>/section/<idx>` | 单章节内容 |
| GET | `/api/report/<id>/download` | 下载 Markdown |
| DELETE | `/api/report/<id>` | 删除报告 |
| GET | `/api/report/<id>/agent-log` | Agent 执行日志 |
| GET | `/api/report/<id>/console-log` | 控制台日志 |
| GET | `/api/report/by-simulation/<sim_id>` | 按模拟查报告 |
| GET | `/api/report/check/<sim_id>` | 报告状态检查 |
| GET | `/api/report/list` | 全部报告列表 |
| POST | `/api/report/chat` | 报告助手对话 |

### 评估（evaluation.py）
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/evaluation/simulations` | 可评估模拟列表 |
| GET | `/api/evaluation/<id>/report` | 完整评估报告 |
| GET | `/api/evaluation/<id>/sentiment` | 情感时序数据 |
| GET | `/api/evaluation/<id>/diversity` | 行为多样性指标 |
| GET | `/api/evaluation/<id>/state-evolution` | 世界状态演化摘要 |
| GET | `/api/evaluation/<id>/benchmark` | Benchmark 三级评分 |
| GET | `/api/evaluation/<id>/influence` | 影响力分析 |

---

## 核心技术能力映射

| 能力 | 实现文件 | 说明 |
|------|---------|------|
| 文本提取 | `text_processor.py` | PDF/MD/TXT → 纯文本 |
| 网络搜索 | `web_scraper.py` | Tavily API 搜索 20+ 中文源 |
| 本体生成 | `ontology_generator.py` | LLM 自动识别实体/关系类型 |
| 图谱构建 | `graph_builder.py` | 实体抽取 + 关系抽取 + 向量化 |
| 向量存储 | `vector_store.py` | 语义检索 |
| Agent 画像 | `oasis_profile_generator.py` | LLM 生成仿真角色 |
| 模拟配置 | `simulation_config_generator.py` | 双平台仿真参数 |
| Agent 决策 | `agent_brain.py` | 每轮自主发帖/评论/转发 |
| 模拟运行 | `simulation_runner.py` | 多轮 Multi-Agent 仿真 |
| 世界状态 | `world_state.py` | 6 维状态计算引擎 |
| 因果推断 | `causal_graph.py` | 事件因果链追踪 |
| 决策简报 | `simulation_insight_service.py` | 基线感知评分卡 + 风险 + 推荐 |
| 干预模板 | `intervention_library.py` | 8 种高校舆情处置模板 + 阶段加成 |
| 报告生成 | `report_agent.py` | 基线感知长报告 Agent（分章节 + 润色） |
| 图谱记忆 | `graph_memory_updater.py` | 模拟结果写回图谱（默认关） |
| 实体清洗 | `entity_cleaner.py` | 去重、标准化 |
| 图谱工具 | `graph_tools.py` | 搜索、统计、路径查询 |
| 模拟评估 | `evaluation_service.py` | 情感分析 + 多样性 + Benchmark |
