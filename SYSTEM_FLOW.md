# NexusMind 系统完整流程图

> 基于代码全量扫描生成，覆盖前端 → API → 后端服务 → 子进程 → 数据存储全链路

---

## 一、全局架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户浏览器 (localhost:3000)                    │
│                                                                      │
│  Home.vue ──→ Process.vue ──→ SimGraphPage.vue / EvaluationView.vue │
│               ┌─────────────────────────────────────────────┐        │
│               │  Step1    Step2    Step3    Step4    Step5   │        │
│               │ 图谱构建  环境搭建  世界模型  报告生成  深度互动│        │
│               └─────────────────────────────────────────────┘        │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ Axios (Vite proxy /api → :5001)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Flask 后端 (localhost:5001)                         │
│                                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ graph_bp │  │simulation_bp │  │report_bp │  │evaluation_bp │    │
│  │ /api/    │  │ /api/        │  │ /api/    │  │ /api/        │    │
│  │ graph/*  │  │ simulation/* │  │ report/* │  │ evaluation/* │    │
│  └────┬─────┘  └──────┬───────┘  └────┬─────┘  └──────┬───────┘    │
│       │               │               │               │             │
│  ┌────▼────────────────▼───────────────▼───────────────▼──────────┐ │
│  │                    Backend Services 层                          │ │
│  │  OntologyGenerator  │ SimulationManager  │ ReportAgent         │ │
│  │  GraphBuilderService│ SimulationRunner   │ ReportManager       │ │
│  │  WebScraperService  │ OasisProfileGen    │ GraphTools          │ │
│  │  EntityReader/Clean │ SimConfigGenerator │ EvaluationFramework │ │
│  │  VectorStore        │ WorldStateEngine   │                     │ │
│  │  TextProcessor      │ CausalGraphEngine  │                     │ │
│  │  FileParser         │ SimulationIPC      │                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
└────────┬────────────────────┬───────────────────────┬───────────────┘
         │                    │                       │
         ▼                    ▼                       ▼
┌──────────────┐  ┌─────────────────────┐  ┌────────────────────┐
│   Neo4j      │  │ OASIS 子进程         │  │ 本地文件系统        │
│ (Graphiti)   │  │ (run_parallel_      │  │ data/projects/     │
│ bolt://7687  │  │  simulation.py)     │  │ data/simulations/  │
└──────────────┘  └─────────────────────┘  │ data/reports/      │
                                           └────────────────────┘
```

---

## 二、五步流程详细链路

### Step 1：图谱构建（Graph Build）

```
┌──────────────────────────────────────────────────────────────────┐
│ 前端: Step1GraphBuild.vue                                        │
│                                                                   │
│  [用户输入]                                                       │
│   ├─ 上传文件（PDF/MD/TXT）+ 模拟需求描述                         │
│   ├─ 或：输入关键词（网络搜索模式）                                │
│   └─ 或：上传文件 + 关键词（混合模式）                             │
└──────────┬────────────────────────────────┬───────────────────────┘
           │                                │
    [文件上传模式]                     [网络搜索模式]
           │                                │
           ▼                                ▼
┌─────────────────────┐         ┌─────────────────────────┐
│ POST /api/graph/    │         │ POST /api/graph/        │
│  ontology/generate  │         │  ontology/generate-from │
│ (multipart/form)    │         │  -web (JSON)            │
└─────────┬───────────┘         └────────────┬────────────┘
          │                                  │
          ▼                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│ 后端处理链（同步）                                                │
│                                                                   │
│  1. ProjectManager.create_project()     → 创建项目目录            │
│  2. FileParser.extract_text()           → 提取文档文本            │
│  3. TextProcessor.preprocess_text()     → 文本预处理              │
│  4. [可选] WebScraperService            → 网络抓取 + 相关性过滤   │
│     .search_to_document_texts()           (中文优化，官方源优先)   │
│  5. ProjectManager.save_extracted_text() → 保存合并文本           │
│  6. OntologyGenerator.generate()        → LLM 生成本体定义        │
│     ├─ entity_types: [Student, Media, Official, ...]              │
│     └─ edge_types: [KNOWS, REPORTS, RESPONDS_TO, ...]            │
│  7. ProjectManager.save_project()       → 持久化项目状态          │
│                                                                   │
│  返回: project_id + ontology + analysis_summary                   │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼ 用户确认本体后，点击"构建图谱"
┌──────────────────────────────────────────────────────────────────┐
│ POST /api/graph/build  { project_id }                            │
│                                                                   │
│ → 启动后台 Thread（异步）                                         │
│                                                                   │
│  1. TextProcessor.split_text()          → 文本分块               │
│  2. GraphBuilderService.create_graph()  → 在 Neo4j 创建图空间    │
│  3. builder.set_ontology()              → 设置 Prescribed Ontology│
│  4. builder.add_text_batches()          → Graphiti 逐块抽取       │
│     ├─ LLM 实体识别 + 关系抽取                                   │
│     └─ 写入 Neo4j（节点 + 边）                                   │
│  5. builder.tag_graph_data()            → 标记图谱数据归属        │
│  6. VectorStore.store_chunks()          → 构建向量 RAG 索引       │
│  7. builder.get_graph_data()            → 读取图谱统计            │
│                                                                   │
│  前端轮询: GET /api/graph/task/{task_id}                          │
│  完成返回: graph_id + node_count + edge_count                     │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  前端自动创建模拟实例
                  POST /api/simulation/create
                  → simulation_id
                  → 跳转 Step 2
```

### Step 2：环境搭建（Environment Setup）

```
┌──────────────────────────────────────────────────────────────────┐
│ 前端: Step2EnvSetup.vue                                          │
│                                                                   │
│  [展示]                                                           │
│   ├─ 图谱实体列表（从 /api/simulation/entities/{graph_id}）       │
│   ├─ 实时 Agent Profile 卡片（轮询 profiles/realtime）            │
│   ├─ 实时模拟配置预览（轮询 config/realtime）                     │
│   └─ 模拟轮数设置（max_rounds）                                   │
└──────────┬───────────────────────────────────────────────────────┘
           │ 点击"开始准备"
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ POST /api/simulation/prepare  { simulation_id }                  │
│                                                                   │
│ → 启动后台 Thread（异步，4 阶段）                                 │
│                                                                   │
│  阶段 1 — 读取图谱实体 (0-20%)                                   │
│  ├─ EntityReader.filter_defined_entities()                        │
│  │   └─ 从 Neo4j 读取实体 → Prescribed Ontology 过滤             │
│  └─ EntityCleaner.clean_entities()                                │
│      └─ 伪实体清洗（去除抽象概念）                                │
│                                                                   │
│  阶段 2 — 生成 Agent 人设 (20-70%)                                │
│  ├─ OasisProfileGenerator.generate_profiles()                     │
│  │   ├─ LLM 为每个实体生成人设（支持并行 5 路）                   │
│  │   ├─ 扩展字段: internal_goal, utility_weights,                 │
│  │   │   risk_tolerance, authority_trust,                         │
│  │   │   emotion_sensitivity, is_opinion_leader                   │
│  │   └─ 保存: {sim_dir}/twitter_profiles.json                    │
│  │            {sim_dir}/reddit_profiles.json                      │
│  └─ 前端轮询 /profiles/realtime 实时展示已生成的 Agent 卡片       │
│                                                                   │
│  阶段 3 — 生成模拟配置 (70-90%)                                   │
│  ├─ SimulationConfigGenerator.generate_config()                   │
│  │   ├─ LLM 智能生成: 时间线、初始事件、Agent 行为概率             │
│  │   └─ 保存: {sim_dir}/simulation_config.json                    │
│  └─ 前端轮询 /config/realtime 实时展示配置                         │
│                                                                   │
│  阶段 4 — 准备脚本 (90-100%)                                     │
│  └─ 复制 run_parallel_simulation.py 等脚本到模拟目录               │
│                                                                   │
│  前端轮询: POST /api/simulation/prepare/status                    │
│  完成后: 用户点击"开始推演" → 跳转 Step 3                         │
└──────────────────────────────────────────────────────────────────┘
```

### Step 3：世界模型推演（Simulation + World Model）

```
┌──────────────────────────────────────────────────────────────────┐
│ 前端: Step3Simulation.vue + WorldStatePanel.vue（右侧边栏）       │
│                                                                   │
│  [实时展示]                                                       │
│   ├─ 模拟进度条（轮次/时间）                                      │
│   ├─ Agent 动作流（实时发帖/评论/转发）                            │
│   ├─ 世界状态 6 维指标条（attention/panic/trust/...）              │
│   ├─ 关键事件时间线                                               │
│   ├─ 因果链列表                                                   │
│   └─ 上帝模式事件注入表单                                         │
└──────────┬───────────────────────────────────────────────────────┘
           │ 自动/手动触发
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ POST /api/simulation/start                                       │
│ { simulation_id, platform: "parallel", max_rounds }              │
│                                                                   │
│  SimulationRunner.start_simulation()                              │
│   ├─ 初始化 WorldStateEngine(sim_dir)                            │
│   ├─ 初始化 _round_action_buffers[sim_id] = []                  │
│   ├─ subprocess.Popen( run_parallel_simulation.py )              │
│   │   └─ env: PYTHONUTF8=1, HF_HUB_OFFLINE=1                   │
│   └─ 启动监控线程 _monitor_simulation()                          │
└──────────────────────────────────────────────────────────────────┘
           │
           │ 分为 Flask 主进程 和 OASIS 子进程两条并行线
           │
     ┌─────┴─────┐
     ▼           ▼
```

#### 子进程：OASIS 双平台并行模拟

```
┌──────────────────────────────────────────────────────────────────┐
│ 子进程: run_parallel_simulation.py                                │
│                                                                   │
│  初始化阶段:                                                      │
│  ├─ 读取 simulation_config.json                                  │
│  ├─ patch_oasis_environment()                                     │
│  │   └─ monkey-patch SocialEnvironment.to_text_prompt             │
│  │       → 每个 Agent 观察环境时自动注入世界状态                   │
│  ├─ patch_agent_memory_limit(window_size=20)                     │
│  │   └─ 限制 Agent 记忆窗口，防止内存爆炸                         │
│  └─ 构建 _agent_role_map（agent_id → stance 映射）               │
│                                                                   │
│  并行启动:                                                        │
│  ┌──────────────────────────────────────────────────────┐        │
│  │              asyncio.gather(                          │        │
│  │  ┌─────────────────┐      ┌─────────────────┐       │        │
│  │  │ Twitter 模拟环境 │      │ Reddit 模拟环境  │       │        │
│  │  │ (SocialPlatform) │      │ (SocialPlatform) │       │        │
│  │  │                  │      │                  │       │        │
│  │  │ Agent 1..N       │      │ Agent 1..M       │       │        │
│  │  │ 发帖/评论/转发/  │      │ 发帖/评论/投票/  │       │        │
│  │  │ 点赞/关注        │      │ 点赞/关注        │       │        │
│  │  └────────┬─────────┘      └────────┬─────────┘       │        │
│  │           │                         │                 │        │
│  │           └──────────┬──────────────┘                 │        │
│  │                      ▼                                │        │
│  │         twitter/actions.jsonl                         │        │
│  │         reddit/actions.jsonl                          │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                   │
│  每轮主循环 (for round_num in range(total_rounds)):               │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  ① read_world_state(sim_dir)                              │   │
│  │     └─ 读取 world_state_current.json（Flask 主进程写入）   │   │
│  │                                                            │   │
│  │  ② 保存前两轮状态用于二阶趋势检测                          │   │
│  │     _prev_world_state_data / _prev2_world_state_data       │   │
│  │                                                            │   │
│  │  ③ _current_world_state_data = ws_data                     │   │
│  │     _current_world_state_prompt = build_world_state_prompt()│  │
│  │                                                            │   │
│  │  ④ 计算活跃 Agent（基于模拟时钟 + 活跃度）                 │   │
│  │     get_active_agents_for_round()                          │   │
│  │                                                            │   │
│  │  ⑤ env.step(actions)                                       │   │
│  │     └─ Agent 决策时调用 to_text_prompt()                   │   │
│  │        └─ 被 patched 的方法注入世界状态                     │   │
│  │           └─ build_world_state_prompt(ws_data, agent_role)  │   │
│  │              ├─ 阻尼检测：deviation < 0.15 → 不注入        │   │
│  │              ├─ 差异化感知：按 stance 过滤维度/事件          │   │
│  │              ├─ 定性描述（不暴露数值，防鹦鹉学舌）          │   │
│  │              └─ v7 POSIM RC 风格（客观观察，非指令）         │   │
│  │                                                            │   │
│  │  ⑥ 记录动作到 actions.jsonl                                │   │
│  │  ⑦ 记录 round_end 事件                                     │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  模拟结束后:                                                      │
│  ├─ 写入 simulation_end 事件到 actions.jsonl                     │
│  └─ 进入 IPC 等待命令模式（支持 Interview / 事件注入 / 关闭）    │
└──────────────────────────────────────────────────────────────────┘
```

#### Flask 主进程：监控线程 + 世界状态引擎

```
┌──────────────────────────────────────────────────────────────────┐
│ Flask 监控线程: _monitor_simulation() — 每 2 秒轮询              │
│                                                                   │
│  while process.alive():                                           │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  ① 读取 twitter/actions.jsonl（增量，记录 file_position） │   │
│  │  ② 读取 reddit/actions.jsonl （增量）                     │   │
│  │     └─ 两个平台的动作混合追加到同一个 buffer               │   │
│  │        _round_action_buffers[sim_id].append(action_data)   │   │
│  │                                                            │   │
│  │  ③ 检测到 round_end 事件时:                                │   │
│  │     ├─ 更新轮次/时间统计                                   │   │
│  │     ├─ ws_engine.update_state(round_num, buffer)           │   │
│  │     │   ├─ _extract_observations(actions)                  │   │
│  │     │   │   └─ 统计帖子/评论/转发/点赞数                   │   │
│  │     │   │   └─ 中文情绪关键词匹配                          │   │
│  │     │   ├─ _update_baseline(observations)                  │   │
│  │     │   ├─ _compute_state_by_rules()                       │   │
│  │     │   │   └─ 计算 6 维状态（带 EMA 平滑）                │   │
│  │     │   ├─ [每 5 轮] _refine_state_by_llm()                │   │
│  │     │   │   └─ LLM 深层语义判断                            │   │
│  │     │   ├─ _consume_injected_events()                      │   │
│  │     │   │   └─ 读取上帝模式注入的事件队列                   │   │
│  │     │   ├─ _detect_events()                                │   │
│  │     │   │   └─ 检测: heat_spike, sentiment_shift,          │   │
│  │     │   │            trust_drop, polarization_surge,       │   │
│  │     │   │            stabilization                         │   │
│  │     │   ├─ _append_state() → world_state_history.jsonl     │   │
│  │     │   ├─ _append_event() → events.jsonl                  │   │
│  │     │   └─ CausalGraphEngine.infer_causal_edges()          │   │
│  │     │       └─ 推断: triggered / amplified / suppressed    │   │
│  │     │       └─ 写入: causal_edges.jsonl                    │   │
│  │     │                                                      │   │
│  │     └─ _write_world_state_for_subprocess()                 │   │
│  │         ├─ 构造 payload（6维状态 + summary_text + events） │   │
│  │         └─ 原子写入: tmp → os.replace → ws_current.json    │   │
│  │                                                            │   │
│  │  ④ 检测到 simulation_end:                                  │   │
│  │     └─ 标记平台完成，检查是否所有平台都完成                 │   │
│  │                                                            │   │
│  │  ⑤ _save_run_state(state) → run_state.json                │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  前端轮询接口:                                                    │
│  ├─ GET /{sim_id}/run-status         → 进度/轮次/状态            │
│  ├─ GET /{sim_id}/run-status/detail  → 最近动作                  │
│  ├─ GET /{sim_id}/world-state        → 世界状态历史              │
│  ├─ GET /{sim_id}/events             → 世界事件时间线            │
│  ├─ GET /{sim_id}/causal-graph       → 因果图谱                  │
│  └─ POST /inject-event               → 上帝模式事件注入          │
└──────────────────────────────────────────────────────────────────┘
```

#### 世界模型反馈闭环（汇总）

```
  ┌────────────────────────────────────────────────────────────┐
  │                    世界模型反馈闭环                         │
  │                                                            │
  │   ┌─────────┐    actions.jsonl     ┌──────────────────┐   │
  │   │ Twitter │──────────────────────▶│                  │   │
  │   │ Agents  │                      │  Flask 监控线程   │   │
  │   └─────────┘                      │                  │   │
  │   ┌─────────┐    actions.jsonl     │  混合 buffer     │   │
  │   │ Reddit  │──────────────────────▶│       │          │   │
  │   │ Agents  │                      └───────┼──────────┘   │
  │   └─────────┘                              │              │
  │        ▲                                   ▼              │
  │        │                      WorldStateEngine            │
  │        │                      .update_state()             │
  │        │                              │                   │
  │        │                              ▼                   │
  │        │                   world_state_current.json       │
  │        │                        (原子写入)                │
  │        │                              │                   │
  │        │                              ▼                   │
  │        │                   read_world_state()             │
  │        │                              │                   │
  │        │                              ▼                   │
  │        │                build_world_state_prompt()         │
  │        │                   ├─ 阻尼过滤                    │
  │        │                   ├─ 差异化感知（按 stance）      │
  │        │                   └─ v7 POSIM RC 风格            │
  │        │                              │                   │
  │        │                              ▼                   │
  │        └──── patch_oasis_environment() ◄──────────────┘   │
  │              注入 Agent prompt                             │
  │              影响下一轮决策                                 │
  └────────────────────────────────────────────────────────────┘
```

### Step 4：报告生成（Report Generation）

```
┌──────────────────────────────────────────────────────────────────┐
│ 前端: Step4Report.vue                                            │
│                                                                   │
│  [展示]                                                           │
│   ├─ Agent 执行日志（ReACT 思考链）                               │
│   ├─ 控制台输出（工具调用日志）                                   │
│   ├─ 分章节实时渲染（Markdown）                                   │
│   └─ 报告完成后支持 PDF 导出                                     │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ POST /api/report/generate  { simulation_id }                     │
│                                                                   │
│ → 启动后台 Thread（异步）                                         │
│                                                                   │
│  ReportAgent( graph_id, simulation_id, simulation_requirement )  │
│  .generate_report()                                               │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  ReACT 循环（多轮推理）                                    │   │
│  │                                                            │   │
│  │  可用工具:                                                 │   │
│  │  ├─ search_graph()    → GraphRAG 图谱搜索                 │   │
│  │  ├─ search_vector()   → VectorRAG 向量检索                │   │
│  │  ├─ get_statistics()  → 图谱统计                           │   │
│  │  ├─ get_actions()     → 模拟动作历史                       │   │
│  │  ├─ get_timeline()    → 按轮次汇总时间线                   │   │
│  │  ├─ get_agent_stats() → Agent 统计                         │   │
│  │  ├─ get_world_state() → 世界状态历史                       │   │
│  │  └─ get_evaluation()  → 量化评估数据                       │   │
│  │                                                            │   │
│  │  生成流程:                                                 │   │
│  │  1. 规划报告结构（章节列表）                                │   │
│  │  2. 并行生成各章节（LLM + 工具调用）                       │   │
│  │  3. 反思修正（reflection rounds）                           │   │
│  │  4. 合并完整报告（Markdown）                                │   │
│  │  5. 保存: {report_dir}/report.md                           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  前端轮询接口:                                                    │
│  ├─ POST /generate/status         → 生成进度                     │
│  ├─ GET  /{report_id}/sections    → 已生成章节列表               │
│  ├─ GET  /{report_id}/agent-log   → Agent 执行日志（增量）       │
│  └─ GET  /{report_id}/console-log → 控制台日志（增量）           │
└──────────────────────────────────────────────────────────────────┘
```

### Step 5：深度互动（Deep Interaction）

```
┌──────────────────────────────────────────────────────────────────┐
│ 前端: Step5Interaction.vue                                       │
│                                                                   │
│  [功能]                                                           │
│   ├─ 与 Report Agent 自由对话（追问报告细节）                     │
│   ├─ Agent 采访（单个 / 批量 / 全局）                             │
│   └─ 模拟图谱浏览（SimGraphPage.vue）                             │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 交互 API:                                                        │
│                                                                   │
│  POST /api/report/chat                                           │
│  { simulation_id, message, chat_history }                        │
│  └─ ReportAgent.chat() → LLM 对话 + 工具调用                    │
│                                                                   │
│  POST /api/simulation/interview                                  │
│  { simulation_id, agent_id, prompt }                             │
│  └─ IPC → 子进程 ParallelIPCHandler                             │
│     └─ 在存活的 OASIS 环境中直接与 Agent 对话                    │
│     └─ 支持: 单平台 / 双平台同时采访                             │
│                                                                   │
│  POST /api/simulation/interview/batch                            │
│  { simulation_id, interviews: [{agent_id, prompt}] }             │
│  └─ 批量采访（按平台分组并行）                                    │
│                                                                   │
│  POST /api/simulation/interview/all                              │
│  { simulation_id, prompt }                                        │
│  └─ 全局采访（相同问题问所有 Agent）                              │
│                                                                   │
│  GET /api/simulation/{sim_id}/sim-graph                          │
│  └─ 从 Neo4j 查询 SimAgent + SimAction 节点与关系                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 三、辅助功能链路

### 量化评估（Evaluation）

```
┌──────────────────────────────────────────────────────────────────┐
│ 前端: EvaluationView.vue  (路由: /evaluation/:simulationId)      │
│                                                                   │
│  GET /api/evaluation/{sim_id}/report     → 完整评估报告           │
│  GET /api/evaluation/{sim_id}/sentiment  → 情感时序数据           │
│  GET /api/evaluation/{sim_id}/diversity  → 行为多样性指标         │
│  GET /api/evaluation/{sim_id}/state-evolution → 世界状态演化      │
│  GET /api/evaluation/{sim_id}/influence  → 影响力分析             │
│                                                                   │
│  后端: EvaluationFramework                                        │
│  └─ 只读分析，从 actions.jsonl + world_state_history.jsonl 提取   │
│     ├─ 情感分布时间线                                             │
│     ├─ 行为多样性（action_type 分布 + agent 参与度）              │
│     ├─ 状态峰值/谷值/转折点                                      │
│     └─ 影响力网络（谁的帖子获得最多互动）                         │
└──────────────────────────────────────────────────────────────────┘
```

### 上帝模式事件注入

```
┌──────────────────────────────────────────────────────────────────┐
│ POST /api/simulation/inject-event                                │
│ { simulation_id, event_type, description, severity,              │
│   affected_variables: {attention_level: +0.2, ...} }             │
│                                                                   │
│  1. 写入 {sim_dir}/injected_events.json 队列                    │
│  2. 下一轮 WorldStateEngine._consume_injected_events() 消费      │
│     ├─ 将 affected_variables 增量应用到当前状态                   │
│     └─ 转换为 WorldEvent 记录                                    │
│  3. 更新后的状态写入 world_state_current.json                    │
│  4. 子进程下一轮读取 → 注入 Agent prompt → 影响行为               │
└──────────────────────────────────────────────────────────────────┘
```

### 历史项目恢复

```
┌──────────────────────────────────────────────────────────────────┐
│ 前端: Home.vue → HistoryDatabase.vue                             │
│                                                                   │
│  GET /api/simulation/history                                      │
│  └─ 返回所有历史模拟（带项目详情、步骤状态）                      │
│                                                                   │
│  恢复逻辑:                                                        │
│  ├─ 有 report_id → 跳转 Step 4/5                                │
│  ├─ runner_status=completed → 跳转 Step 4                        │
│  ├─ runner_status=running → 跳转 Step 3                          │
│  ├─ status=ready → 跳转 Step 3                                   │
│  └─ 否则 → 跳转 Step 2                                          │
│                                                                   │
│  Flask 启动时 reattach:                                           │
│  └─ SimulationRunner.reattach_running_simulations()              │
│     └─ 扫描 run_state.json，PID 活着 → 接管监控线程              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 四、数据流与文件系统

```
data/
├── projects/
│   └── proj_xxxx/
│       ├── project.json              # 项目元数据（名称/状态/本体/文件列表）
│       ├── extracted_text.txt        # 合并后的文档文本
│       ├── vector_store/             # VectorRAG FAISS 索引
│       └── uploads/                  # 上传的原始文件
│
├── simulations/
│   └── sim_xxxx/
│       ├── simulation_state.json     # 模拟元数据
│       ├── twitter_profiles.json     # Twitter Agent 人设
│       ├── reddit_profiles.json      # Reddit Agent 人设
│       ├── simulation_config.json    # LLM 生成的完整配置
│       │
│       │── run_state.json            # 运行时状态（轮次/PID/完成标志）
│       ├── simulation.log            # 主进程日志
│       │
│       ├── twitter/
│       │   ├── actions.jsonl         # Twitter 动作日志
│       │   └── twitter_simulation.db # OASIS SQLite 数据库
│       ├── reddit/
│       │   ├── actions.jsonl         # Reddit 动作日志
│       │   └── reddit_simulation.db  # OASIS SQLite 数据库
│       │
│       ├── world_state_current.json  # 当前世界状态（共享文件，原子写）
│       ├── world_state_history.jsonl # 完整世界状态历史
│       ├── events.jsonl              # 世界事件时间线
│       ├── causal_edges.jsonl        # 因果图谱边
│       ├── injected_events.json      # 上帝模式注入事件队列
│       │
│       └── ipc/                      # IPC 通信目录
│           ├── commands/             # 主进程 → 子进程命令
│           ├── responses/            # 子进程 → 主进程响应
│           └── env_status.json       # 环境存活状态
│
├── reports/
│   └── report_xxxx/
│       ├── report.json               # 报告元数据
│       ├── report.md                 # 完整报告（Markdown）
│       ├── sections/                 # 分章节内容
│       ├── agent_log.jsonl           # ReACT Agent 执行日志
│       └── console_log.txt           # 控制台输出
│
└── tasks/
    └── task_xxxx.json                # 异步任务状态
```

---

## 五、完整 API 清单

### /api/graph（图谱蓝图）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ontology/generate` | 上传文件 + 生成本体 |
| POST | `/ontology/generate-from-web` | 网络搜索 + 生成本体 |
| POST | `/build` | 启动图谱构建（异步） |
| GET | `/task/{task_id}` | 查询任务状态 |
| GET | `/tasks` | 列出所有任务 |
| GET | `/data/{graph_id}` | 获取图谱数据 |
| DELETE | `/delete/{graph_id}` | 删除图谱 |
| GET | `/project/{project_id}` | 获取项目详情 |
| GET | `/project/list` | 列出所有项目 |
| DELETE | `/project/{project_id}` | 删除项目 |
| POST | `/project/{project_id}/reset` | 重置项目状态 |

### /api/simulation（模拟蓝图）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/create` | 创建模拟实例 |
| POST | `/prepare` | 准备模拟环境（异步） |
| POST | `/prepare/status` | 查询准备进度 |
| POST | `/start` | 启动模拟运行 |
| POST | `/stop` | 停止模拟 |
| GET | `/{sim_id}` | 获取模拟状态 |
| DELETE | `/{sim_id}` | 删除模拟 |
| GET | `/list` | 列出所有模拟 |
| GET | `/history` | 历史模拟列表（带项目详情） |
| GET | `/{sim_id}/profiles` | 获取 Agent Profile |
| GET | `/{sim_id}/profiles/realtime` | 实时获取生成中的 Profile |
| GET | `/{sim_id}/config` | 获取模拟配置 |
| GET | `/{sim_id}/config/realtime` | 实时获取生成中的配置 |
| GET | `/{sim_id}/config/download` | 下载配置文件 |
| GET | `/{sim_id}/run-status` | 运行实时状态 |
| GET | `/{sim_id}/run-status/detail` | 运行详细状态 |
| GET | `/{sim_id}/actions` | Agent 动作历史 |
| GET | `/{sim_id}/timeline` | 按轮次汇总时间线 |
| GET | `/{sim_id}/agent-stats` | Agent 统计 |
| GET | `/{sim_id}/posts` | 帖子列表 |
| GET | `/{sim_id}/comments` | 评论列表（Reddit） |
| GET | `/{sim_id}/world-state` | 世界状态历史 |
| GET | `/{sim_id}/events` | 世界事件时间线 |
| GET | `/{sim_id}/causal-graph` | 因果图谱 |
| GET | `/{sim_id}/sim-graph` | 模拟知识图谱 |
| POST | `/inject-event` | 上帝模式事件注入 |
| POST | `/interview` | 单个 Agent 采访 |
| POST | `/interview/batch` | 批量采访 |
| POST | `/interview/all` | 全局采访 |
| POST | `/interview/history` | 采访历史 |
| POST | `/env-status` | 环境存活状态 |
| POST | `/close-env` | 关闭模拟环境 |
| POST | `/generate-profiles` | 独立生成 Profile |
| GET | `/script/{name}/download` | 下载运行脚本 |

### /api/report（报告蓝图）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generate` | 生成报告（异步） |
| POST | `/generate/status` | 查询生成进度 |
| GET | `/{report_id}` | 获取报告详情 |
| GET | `/by-simulation/{sim_id}` | 按模拟 ID 获取报告 |
| GET | `/list` | 列出所有报告 |
| GET | `/{report_id}/download` | 下载报告（Markdown） |
| DELETE | `/{report_id}` | 删除报告 |
| POST | `/chat` | 与 Report Agent 对话 |
| GET | `/{report_id}/progress` | 生成进度（实时） |
| GET | `/{report_id}/sections` | 已生成章节列表 |
| GET | `/{report_id}/section/{idx}` | 单个章节内容 |
| GET | `/{report_id}/agent-log` | Agent 执行日志 |
| GET | `/{report_id}/agent-log/stream` | 完整 Agent 日志 |
| GET | `/{report_id}/console-log` | 控制台日志 |
| GET | `/{report_id}/console-log/stream` | 完整控制台日志 |
| GET | `/check/{sim_id}` | 检查报告状态 |
| POST | `/tools/search` | 图谱搜索（调试） |
| POST | `/tools/statistics` | 图谱统计（调试） |

### /api/evaluation（评估蓝图）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/simulations` | 列出可评估的模拟 |
| GET | `/{sim_id}/report` | 完整评估报告 |
| GET | `/{sim_id}/sentiment` | 情感时序数据 |
| GET | `/{sim_id}/diversity` | 行为多样性指标 |
| GET | `/{sim_id}/state-evolution` | 世界状态演化 |
| GET | `/{sim_id}/influence` | 影响力分析 |

---

## 六、前端组件映射

```
路由层
├── / → Home.vue
│   └── HistoryDatabase.vue           # 历史项目列表
│
├── /process/:projectId → Process.vue  # 主流程容器
│   ├── Step1GraphBuild.vue           # 图谱构建
│   ├── Step2EnvSetup.vue             # 环境搭建
│   ├── Step3Simulation.vue           # 世界模型推演
│   │   └── WorldStatePanel.vue       # 右侧世界模型边栏
│   │       ├── WorldStateHero.vue    # 6 维指标可视化
│   │       ├── EventTimeline.vue     # 事件时间线
│   │       ├── AgentActionCard.vue   # Agent 动作卡片
│   │       ├── CausalGraphView.vue   # 因果图谱
│   │       └── SimGraphView.vue      # 模拟图谱
│   ├── Step4Report.vue               # 报告生成
│   ├── Step5Interaction.vue          # 深度互动
│   └── GraphPanel.vue                # 左侧知识图谱面板（D3.js）
│
├── /sim-graph/:simulationId → SimGraphPage.vue  # 模拟图谱独立页
│
└── /evaluation/:simulationId → EvaluationView.vue  # 量化评估独立页
```
