# NexusMind 系统运行流程图

> 本文档为指导老师展示用，完整覆盖系统从用户输入到报告产出的全链路数据流。

---

## 一、系统总览：五步闭环流水线

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NexusMind 群体智能预测引擎                         │
│                                                                         │
│   ① 图谱构建  →  ② 环境搭建  →  ③ 世界模型推演  →  ④ 报告生成  →  ⑤ 深度互动  │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────┐  │
│  │ 种子材料 │→│ Agent世界 │→│ 多轮模拟    │→│ 分析报告 │→│ 人机对话 │  │
│  │→知识图谱 │  │ 环境配置 │  │+世界模型闭环│  │+世界模型 │  │+工具调用 │  │
│  └──────────┘  └──────────┘  └────────────┘  └──────────┘  └─────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、技术架构

```
┌─────────────────────────────┐
│    Frontend (Vue 3 + Vite)  │  Port 3000
│  ┌───────────────────────┐  │
│  │ Process.vue (主流程页) │  │
│  │  ├─ Step1GraphBuild    │  │  图谱构建
│  │  ├─ Step2EnvSetup      │  │  环境搭建
│  │  ├─ Step3Simulation    │  │  世界模型推演
│  │  ├─ Step4Report        │  │  报告生成
│  │  └─ Step5Interaction   │  │  深度互动
│  └───────────────────────┘  │
│  辅助页面:                   │
│  ├─ Home.vue (项目管理)     │
│  ├─ SimGraphPage (模拟图谱) │
│  └─ EvaluationView (评估)   │
└──────────┬──────────────────┘
           │ HTTP REST API (/api/*)
           ▼
┌─────────────────────────────┐
│   Backend (Flask 3.x)       │  Port 5001
│  ┌───────────────────────┐  │
│  │ API Blueprints:       │  │
│  │  /api/graph/*         │──│── 图谱构建 API
│  │  /api/simulation/*    │──│── 模拟管理 API (最大模块, 127KB)
│  │  /api/report/*        │──│── 报告生成 API
│  │  /api/evaluation/*    │──│── 量化评估 API
│  └───────────────────────┘  │
│  ┌───────────────────────┐  │
│  │ Services Layer:       │  │
│  │  OntologyGenerator    │  │  LLM驱动本体生成
│  │  GraphBuilderService  │  │  Graphiti→Neo4j图谱构建
│  │  EntityReader/Cleaner │  │  实体读取与清洗
│  │  OasisProfileGenerator│  │  Agent人设生成
│  │  SimConfigGenerator   │  │  模拟配置生成
│  │  SimulationManager    │  │  模拟生命周期管理
│  │  SimulationRunner     │  │  OASIS子进程调度
│  │  WorldStateEngine     │  │  六维世界状态引擎
│  │  CausalGraphEngine    │  │  因果图谱引擎
│  │  SimInsightService    │  │  世界模型洞察聚合
│  │  ReportAgent          │  │  ReACT报告生成 (11个工具)
│  │  SimulationEvaluator  │  │  量化评估
│  │  VectorStore          │  │  向量RAG索引
│  │  GraphToolsService    │  │  GraphRAG检索
│  │  WebScraperService    │  │  网络舆情抓取
│  └───────────────────────┘  │
└──────────┬──────────────────┘
           │ Bolt Protocol
           ▼
┌─────────────────────────────┐
│  Neo4j Enterprise 5.24      │  Port 7787
│  知识图谱 + 模拟Agent存储    │
└─────────────────────────────┘
```

---

## 三、Step 1 — 图谱构建（知识抽取与结构化）

```
用户操作                           后端处理
────────                           ────────
上传PDF/MD/TXT文件      ──POST──▶  /api/graph/ontology/generate
  +                                    │
输入模拟需求描述                       ▼
(可选: 网络搜索关键词)        ┌──────────────────┐
                              │ 1. FileParser     │ 提取文本
                              │    提取文本内容    │
                              ├──────────────────┤
                              │ 2. WebScraper     │ (可选)
                              │    Tavily网络搜索  │ 抓取舆情
                              ├──────────────────┤
                              │ 3. OntologyGen    │ LLM分析
                              │    LLM生成本体     │ 实体类型+关系类型
                              └────────┬─────────┘
                                       │ 返回 project_id + ontology
                                       ▼
用户确认/编辑本体          ──POST──▶  /api/graph/build
                                       │
                              ┌────────▼─────────┐
                              │ 异步后台任务:       │
                              │                    │
                              │ 1. TextProcessor   │ 文本分块
                              │    分块(500字/块)   │
                              │                    │
                              │ 2. GraphBuilder    │ Graphiti引擎
                              │    ├─ create_graph │ 创建Neo4j图谱
                              │    ├─ set_ontology │ 设置本体约束
                              │    ├─ add_text     │ LLM抽取实体/关系
                              │    └─ tag_data     │ 标记数据归属
                              │                    │
                              │ 3. VectorStore     │ 向量RAG索引
                              │    store_chunks    │ 嵌入+存储
                              └────────┬─────────┘
                                       │
                                       ▼
                              Neo4j 知识图谱
                              ├─ 实体节点 (Entity)
                              ├─ 关系边 (Edge)
                              └─ 事实三元组 (Fact)
```

**关键输出**: `project_id`, `graph_id`, Neo4j中的结构化知识图谱

---

## 四、Step 2 — 环境搭建（Agent世界配置）

```
自动化流程（用户仅需确认参数）
──────────────────────────

/api/simulation/create
        │
        ▼
SimulationManager.create_simulation()
        │
        ▼
┌──────────────────────────────────────────────┐
│  1. EntityReader.filter_defined_entities()    │
│     从Neo4j读取实体 → 过滤+清洗              │
│     (EntityCleaner去除伪实体)                 │
├──────────────────────────────────────────────┤
│  2. EntityTypeAnnotator.annotate()            │
│     LLM标注实体类型 → 识别Agent候选           │
│     (Person/Org/Media → SimAgent)             │
├──────────────────────────────────────────────┤
│  3. OasisProfileGenerator.generate()          │
│     LLM为每个Agent生成详细人设:               │
│     ├─ 姓名、性别、年龄、职业                 │
│     ├─ 性格特征、立场倾向                     │
│     ├─ 社交媒体行为模式                       │
│     └─ 与事件的关系链                         │
│     输出: reddit_profiles.json                │
│           twitter_profiles.csv                │
├──────────────────────────────────────────────┤
│  4. SimConfigGenerator.generate()             │
│     LLM智能生成模拟配置:                      │
│     ├─ max_rounds (模拟轮数)                  │
│     ├─ agent_count (Agent数量)                │
│     ├─ 平台设置 (Twitter/Reddit)              │
│     ├─ 事件注入时间线                         │
│     └─ 环境描述 (模拟背景故事)                │
│     输出: simulation_config.json              │
└──────────────────────────────────────────────┘
        │
        ▼
状态: ready (等待用户点击"开始推演")
```

**关键输出**: `simulation_id`, Agent人设档案, 模拟配置文件

---

## 五、Step 3 — 世界模型推演（核心模拟引擎）

```
用户点击"开始推演"
        │
        ▼
/api/simulation/{id}/run
        │
        ▼
SimulationRunner.start()
        │
        ├─ 启动OASIS子进程 (run_parallel_simulation.py)
        │       │
        │       ▼
        │  ┌─────────────────────────────────────────────────────┐
        │  │              OASIS 多Agent模拟循环                   │
        │  │                                                     │
        │  │  for round in range(max_rounds):                    │
        │  │      │                                              │
        │  │      ├─ 1. 读取世界状态注入 ◄── world_state.json   │
        │  │      │     build_world_state_prompt()                │
        │  │      │     patch_oasis_environment()                 │
        │  │      │     (偏差>0.15时才注入, 中性语言)              │
        │  │      │                                              │
        │  │      ├─ 2. Agent决策与行动                          │
        │  │      │     每个Agent基于人设+记忆+世界状态           │
        │  │      │     在Twitter/Reddit上执行:                   │
        │  │      │     发帖/评论/转发/点赞/搜索...              │
        │  │      │                                              │
        │  │      ├─ 3. 收集本轮行动数据                         │
        │  │      │     actions.jsonl (全部Agent行为)             │
        │  │      │                                              │
        │  │      └─ 4. IPC回传行动数据给主进程 ──────────────┐  │
        │  └─────────────────────────────────────────────────┤──┘
        │                                                    │
        │  ◄── SimulationIPC 接收行动数据 ◄─────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│             WorldStateEngine (主进程, 每轮执行)               │
│                                                             │
│  输入: 本轮所有Agent行动 + 上一轮世界状态                    │
│                                                             │
│  1. LLM分析行动 → 生成事件 (events.jsonl)                   │
│     ├─ 事件类型: 舆论热度变化/信任波动/恐慌爆发/...         │
│     ├─ 影响变量: {attention: +0.05, trust: -0.03, ...}      │
│     └─ 严重程度: 0.0 ~ 1.0                                  │
│                                                             │
│  2. 更新六维状态变量:                                        │
│     ┌──────────────────────────────────────────────┐        │
│     │  attention_level  (舆论关注度)    0.0 ~ 1.0  │        │
│     │  panic_level      (恐慌/负面情绪) 0.0 ~ 1.0  │        │
│     │  trust_level      (公众信任度)    0.0 ~ 1.0  │        │
│     │  polarization     (立场极化度)    0.0 ~ 1.0  │        │
│     │  risk_level       (综合风险等级)  0.0 ~ 1.0  │        │
│     │  stability_level  (系统稳定性)    0.0 ~ 1.0  │        │
│     └──────────────────────────────────────────────┘        │
│                                                             │
│  3. CausalGraphEngine 推断因果关系                           │
│     ├─ 事件→事件 因果边 (causal_edges.jsonl)                │
│     ├─ 关系类型: 直接触发/间接影响/反馈循环/...             │
│     └─ 强度: 0.0 ~ 1.0                                     │
│                                                             │
│  4. 写回世界状态 → world_state.json (供子进程下轮读取)      │
│     world_state_history.jsonl (历史记录)                     │
│                                                             │
│  5. Neo4j持久化:                                             │
│     SimAgent节点 + SimAction节点 + PERFORMED边               │
└─────────────────────────────────────────────────────────────┘

         ┌──── 世界模型闭环 ────┐
         │                      │
   OASIS子进程              主进程
   Agent行动 ──IPC──▶ 世界状态更新
         ▲                  │
         │    world_state   │
         └──── .json ◄──────┘
```

**关键输出**:
- `world_state_history.jsonl` — 每轮六维状态快照
- `events.jsonl` — 系统识别的所有事件
- `causal_edges.jsonl` — 因果关系图谱
- `actions.jsonl` — 全部Agent行为记录
- Neo4j中的SimAgent/SimAction数据

---

## 六、Step 4 — 报告生成（ReACT智能体 + 世界模型增强）

```
/api/report/generate
        │
        ▼
ReportAgent 初始化
├─ GraphToolsService (Neo4j图谱检索)
├─ SimulationInsightService (世界模型洞察)
├─ LLMClient (大语言模型)
└─ 注册 11 个工具
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              Phase 1: 大纲规划 (plan_outline)        │
│                                                     │
│  输入:                                              │
│  ├─ 模拟需求描述                                    │
│  ├─ 图谱统计 (节点数、边数、实体类型)                │
│  ├─ 相关事实 (Top10)                                │
│  └─ 世界模型上下文 ◄── get_report_context_bundle()  │
│       ├─ 六维状态当前值 + 演化趋势                   │
│       ├─ 综合态势评分 (健康/风险/修复潜力/极化)      │
│       ├─ 关键转折点                                  │
│       └─ 因果链摘要                                  │
│                                                     │
│  LLM输出 → JSON大纲:                                │
│  {                                                  │
│    "title": "报告标题",                              │
│    "executive_summary": "核心摘要",                  │
│    "sections": [                                    │
│      {"title": "一、情景设定", "description": "..."},│
│      {"title": "二、核心判断", "description": "..."},│
│      ...                                            │
│    ]                                                │
│  }                                                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│        Phase 2: 逐章节生成 (ReACT循环)               │
│                                                     │
│  for each section in outline:                       │
│      │                                              │
│      ▼                                              │
│  ┌─────────────────────────────────────────┐        │
│  │ ReACT Loop (max 10 iterations):         │        │
│  │                                         │        │
│  │  Thought → 分析需要什么数据              │        │
│  │      │                                  │        │
│  │      ▼                                  │        │
│  │  Action → 调用工具获取数据              │        │
│  │  ┌─────────────────────────────────┐    │        │
│  │  │ 11个可用工具:                    │    │        │
│  │  │                                 │    │        │
│  │  │ 【图谱检索工具】                │    │        │
│  │  │ ① insight_forge    深度分析      │    │        │
│  │  │ ② panorama_search  全景搜索      │    │        │
│  │  │ ③ quick_search     快速检索      │    │        │
│  │  │ ④ interview_agents Agent采访     │    │        │
│  │  │                                 │    │        │
│  │  │ 【世界模型工具】                │    │        │
│  │  │ ⑤ world_model_brief 状态全景    │    │        │
│  │  │ ⑥ state_evolution   演化分析    │    │        │
│  │  │ ⑦ causal_chain      因果链      │    │        │
│  │  │ ⑧ evaluation_summary 量化评估   │    │        │
│  │  │ ⑨ reputation_scorecard 态势评分 │    │        │
│  │  │ ⑩ decision_support   决策支持   │    │        │
│  │  │ ⑪ simulation_evidence 证据检索  │    │        │
│  │  └─────────────────────────────────┘    │        │
│  │      │                                  │        │
│  │      ▼                                  │        │
│  │  Observation → 工具返回数据              │        │
│  │      │                                  │        │
│  │      ▼                                  │        │
│  │  (重复直到信息充足)                      │        │
│  │      │                                  │        │
│  │      ▼                                  │        │
│  │  Final Answer → 输出章节Markdown         │        │
│  └─────────────────────────────────────────┘        │
│      │                                              │
│      ▼ section_XX.md (实时保存)                     │
│                                                     │
│  前端轮询 /api/report/{id}/sections 实时展示        │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│          Phase 3: 全文组装 + LLM润色                 │
│                                                     │
│  1. 拼接: 标题 + 摘要 + 各章节 → full_report.md     │
│  2. LLM全局润色:                                    │
│     ├─ 修复跨章节不一致                              │
│     ├─ 优化逻辑衔接                                 │
│     ├─ 消除重复论述                                  │
│     └─ 不添加新事实, 不改变结论                      │
│  3. 输出最终报告                                     │
└─────────────────────────────────────────────────────┘
```

**关键输出**: 完整Markdown报告（含世界模型量化数据、因果分析、决策建议）

---

## 七、Step 5 — 深度互动（对话式探索）

```
用户提问: "信任度为什么持续下降?"
        │
        ▼
/api/report/chat
        │
        ▼
ReportAgent.chat()
        │
        ▼
┌─────────────────────────────────────┐
│  ReACT对话循环                       │
│                                     │
│  1. LLM理解用户问题                  │
│  2. 自主调用工具检索相关数据          │
│     (同报告生成的11个工具)            │
│  3. 综合数据生成回答                  │
│  4. 返回回答 + 引用来源              │
└─────────────────────────────────────┘
```

---

## 八、数据流总图

```
                    ┌─────────────┐
                    │  PDF/MD/TXT │  种子材料
                    │  + 网络搜索  │
                    └──────┬──────┘
                           │
                    Step 1 │ 图谱构建
                           ▼
                    ┌─────────────┐
                    │  Neo4j      │  知识图谱
                    │  Knowledge  │  实体+关系+事实
                    │  Graph      │
                    └──────┬──────┘
                           │
                    Step 2 │ 环境搭建
                           ▼
              ┌────────────────────────┐
              │  Agent Profiles        │  Agent人设
              │  + Simulation Config   │  + 模拟配置
              └────────────┬───────────┘
                           │
                    Step 3 │ 世界模型推演
                           ▼
    ┌──────────────────────────────────────────────┐
    │                                              │
    │  ┌──────────┐    ┌───────────┐    ┌────────┐│
    │  │ actions   │    │ events    │    │ world  ││
    │  │ .jsonl    │    │ .jsonl    │    │ state  ││
    │  │           │    │           │    │ history││
    │  │ Agent全部 │    │ 系统事件  │    │ .jsonl ││
    │  │ 行为记录  │    │ 识别结果  │    │        ││
    │  └─────┬─────┘    └─────┬─────┘    │ 六维   ││
    │        │                │          │ 状态   ││
    │        │                │          │ 快照   ││
    │        │                │          └───┬────┘│
    │        │                │              │     │
    │        │          ┌─────▼──────┐       │     │
    │        │          │ causal     │       │     │
    │        │          │ edges      │       │     │
    │        │          │ .jsonl     │       │     │
    │        │          │ 因果关系图 │       │     │
    │        │          └─────┬──────┘       │     │
    │        │                │              │     │
    │  ┌─────▼────────────────▼──────────────▼──┐  │
    │  │       SimulationInsightService         │  │
    │  │       (世界模型洞察聚合层)               │  │
    │  │  7个方法汇总模拟数据为结构化摘要         │  │
    │  └────────────────────┬───────────────────┘  │
    └───────────────────────┼──────────────────────┘
                            │
                     Step 4 │ 报告生成
                            ▼
              ┌──────────────────────────┐
              │                          │
              │  ┌─────────────────────┐ │
              │  │   GraphToolsService │ │  Neo4j图谱检索
              │  └──────────┬──────────┘ │
              │             │            │
              │  ┌──────────▼──────────┐ │
              │  │    ReportAgent      │ │  ReACT智能体
              │  │    (11个工具)       │ │  大纲→章节→润色
              │  └──────────┬──────────┘ │
              │             │            │
              │  ┌──────────▼──────────┐ │
              │  │  Markdown Report    │ │  最终报告
              │  └─────────────────────┘ │
              └──────────────┬───────────┘
                             │
                      Step 5 │ 深度互动
                             ▼
              ┌──────────────────────────┐
              │  ReportAgent.chat()      │
              │  对话式工具调用+回答      │
              └──────────────────────────┘
```

---

## 九、关键技术创新点

| 创新点 | 说明 |
|--------|------|
| **世界模型闭环** | Agent行动→事件检测→六维状态更新→反馈注入Agent环境，形成认知-行为-环境闭环 |
| **因果图谱引擎** | 自动推断事件间因果关系，生成可解释的因果链 |
| **Prescribed Ontology** | LLM先生成本体定义，再约束图谱抽取，确保结构化质量 |
| **双路检索 (RAG)** | VectorRAG（语义相似）+ GraphRAG（结构化关系）并行检索 |
| **ReACT报告智能体** | 11个工具的自主推理-行动循环，报告内容100%数据驱动 |
| **世界模型增强报告** | 量化数据（信任度0.20、风险0.28等）直接嵌入分析论证 |

---

## 十、文件目录与核心模块对照

```
NexusMind/
├── frontend/src/
│   ├── components/
│   │   ├── Step1GraphBuild.vue    ← 图谱构建UI
│   │   ├── Step2EnvSetup.vue      ← 环境搭建UI
│   │   ├── Step3Simulation.vue    ← 推演控制UI
│   │   ├── Step4Report.vue        ← 报告展示UI
│   │   ├── Step5Interaction.vue   ← 对话互动UI
│   │   └── WorldState/            ← 世界模型可视化组件
│   ├── views/
│   │   ├── Process.vue            ← 五步主流程页
│   │   └── Home.vue               ← 项目管理首页
│   └── api/                       ← 前端API封装
│
├── backend/
│   ├── app/
│   │   ├── __init__.py            ← Flask工厂 + 蓝图注册
│   │   ├── api/
│   │   │   ├── graph.py           ← Step1: 本体生成+图谱构建
│   │   │   ├── simulation.py      ← Step2+3: 环境搭建+模拟运行
│   │   │   ├── report.py          ← Step4+5: 报告生成+对话
│   │   │   └── evaluation.py      ← 量化评估接口
│   │   ├── services/
│   │   │   ├── ontology_generator.py     ← LLM本体生成
│   │   │   ├── graph_builder.py          ← Graphiti图谱构建
│   │   │   ├── entity_reader.py          ← 实体读取+过滤
│   │   │   ├── entity_cleaner.py         ← 伪实体清洗
│   │   │   ├── oasis_profile_generator.py← Agent人设生成
│   │   │   ├── simulation_config_generator.py ← 模拟配置生成
│   │   │   ├── simulation_manager.py     ← 模拟生命周期
│   │   │   ├── simulation_runner.py      ← OASIS子进程调度
│   │   │   ├── simulation_ipc.py         ← 进程间通信
│   │   │   ├── world_state.py            ← 六维世界状态引擎
│   │   │   ├── causal_graph.py           ← 因果图谱引擎
│   │   │   ├── simulation_insight_service.py ← 世界模型洞察聚合
│   │   │   ├── evaluation.py             ← 量化评估引擎
│   │   │   ├── report_agent.py           ← ReACT报告生成Agent
│   │   │   ├── graph_tools.py            ← GraphRAG检索工具
│   │   │   ├── vector_store.py           ← VectorRAG索引
│   │   │   └── web_scraper.py            ← 网络舆情抓取
│   │   └── models/
│   │       ├── project.py                ← 项目数据模型
│   │       └── task.py                   ← 异步任务模型
│   └── scripts/
│       └── run_parallel_simulation.py    ← OASIS模拟子进程
│
└── word_modle/papers/                    ← 世界模型参考论文
```
