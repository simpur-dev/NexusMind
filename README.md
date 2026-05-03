# NexusMind

> 基于社会世界模型的多智能体舆情推演与决策辅助系统  
> Multi-Agent Public Opinion Simulation and Decision Support Powered by a Social World Model

<div align="center">

<img src="./static/image/NexusMind_logo.png" alt="NexusMind Logo" width="72%"/>

[![GitHub Stars](https://img.shields.io/github/stars/666ghj/NexusMind?style=flat-square&color=DAA520)](https://github.com/666ghj/NexusMind/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/666ghj/NexusMind?style=flat-square)](https://github.com/666ghj/NexusMind/network)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square)](./package.json)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-4581C3?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com/)

[中文文档](./README.md) · [English](./README-EN.md)

</div>

---

## 1. 项目简介

**NexusMind** 是一套以**社会世界模型**为核心的多智能体舆情推演与决策辅助系统。系统以现实公共事件中的种子材料为起点，自动完成事实理解、知识图谱构建、Agent 社会生成、舆情态势推演、世界状态追踪、因果链分析与决策报告生成。

社会世界模型用于刻画公共事件所处的动态社会环境：它不仅关注“谁说了什么”，还持续追踪关注度、公众信任、情绪压力、立场极化、综合风险和系统稳定性等状态变量。多类 Agent 会在信息广场和话题社区中发帖、评论、转发、搜索与互动；这些行为会改变世界状态，而世界状态又会反馈影响后续 Agent 行为，从而形成“个体行为—群体涌现—社会态势—决策响应”的闭环推演。

与传统舆情系统不同，NexusMind 不只是对已有材料进行摘要、分类或情感分析，而是尝试在可控数字社会中模拟事件的发展过程，提前识别可能出现的扩散趋势、风险拐点、关键影响因素和干预窗口。

一句话概括：

> **NexusMind 是一个由社会世界模型驱动、能随着事件发展持续更新的公共事件数字沙盘。**

当前项目重点面向：

- **高校舆情与品牌声誉治理**：模拟举报、通报、媒体报道和公众讨论的演化过程，辅助识别声誉风险、信任拐点与修复策略。
- **公共安全与应急管理**：模拟自然灾害、校园安全、公共卫生等事件中的人群情绪、信息扩散和社会动态，优化应急预案与响应节奏。
- **舆情风险预警**：实时监测并模拟网络舆情的传播路径和演变趋势，提前识别潜在的次生风险、极化风险和信任危机。
- **政策沟通与组织治理**：模拟不同回应方式、信息披露节奏和资源配置方案的效果，为组织治理和公共沟通提供决策参考。
- **计算机设计大赛展示**：围绕真实案例展示“材料接入—社会世界建模—多智能体推演—决策辅助”的完整 AI 实践闭环。

---

## 2. 核心价值

### 2.1 从静态分析到动态推演

多数舆情分析工具回答的是：“已经发生了什么？”  
NexusMind 更进一步回答：

- 接下来可能如何扩散？
- 哪些节点可能成为风险拐点？
- 哪些主体、话题和信息会放大影响？
- 不同处置策略可能带来什么收益和副作用？

### 2.2 从文本摘要到社会世界模型

系统不仅抽取文本中的实体、关系和事件，还会持续维护宏观社会状态，包括关注度、公众信任、情绪压力、立场极化、综合风险和系统稳定性。Agent 的行为会改变世界状态，世界状态又会通过反馈机制影响后续 Agent 行为。

### 2.3 从一次性报告到滚动决策

真实公共事件不会在一次分析后结束。NexusMind 支持随着现实新材料出现持续追加材料、重建事实基线、创建预测分支和更新决策简报，形成滚动研判闭环。

---

## 3. 系统总览

```text
现实种子材料
   │
   ▼
文本解析 / 网络抓取 / 分阶段追加
   │
   ▼
事实基线 Baseline Snapshot
   │
   ▼
知识图谱 + 向量检索 GraphRAG / VectorRAG
   │
   ▼
Agent 社会构建：身份、人设、认知先验、平台参数
   │
   ▼
信息广场 + 话题社区双平台推演
   │
   ▼
社会世界模型：六维状态、事件流、因果链、反馈闭环
   │
   ▼
报告生成 / 量化评估 / 决策简报 / 分支对比
```

---

## 4. 社会世界模型

社会世界模型是 NexusMind 当前版本的核心。它用于表示事件环境如何在 Agent 行为、外部信息和群体反馈中持续演化。

### 4.1 六维宏观状态

| 状态变量 | 中文含义 | 作用 |
|---|---|---|
| `attention_level` | 舆论关注度 | 衡量事件热度和讨论规模 |
| `panic_level` | 情绪压力 | 衡量负面情绪、焦虑和恐慌扩散 |
| `trust_level` | 公众信任 | 衡量公众对组织、权威或官方回应的信任 |
| `polarization_level` | 立场极化 | 衡量群体分歧和对立强度 |
| `risk_level` | 综合风险 | 综合刻画事件升级、次生风险和治理压力 |
| `stability_level` | 系统稳定性 | 衡量舆论环境是否趋于收敛和平稳 |

### 4.2 状态更新机制

每轮推演结束后，系统会从 Agent 行为中提取观测信号，例如：

- 发帖、评论、转发、点赞、搜索和关注行为
- 活跃 Agent 数量
- 关键词和话题变化
- 情感分布
- 平台行为差异
- 事件触发和状态突变

随后通过规则层、平滑机制、自然衰减、话题状态和事件检测生成新的世界状态快照，并持久化为 JSONL 数据。

### 4.3 反馈闭环

世界状态不是只用于展示。系统会将宏观状态压缩为中性、非指令式的环境观察信息，通过模拟子进程注入 Agent 所感知的环境，使 Agent 后续行为受到社会态势影响。

为避免过度操控，系统采用阻尼机制：只有当状态偏离基线达到阈值时才注入环境观察，从而保持 Agent 行为的自主性。

相关实现：

- `backend/app/services/world_state.py`
- `backend/app/services/causal_graph.py`
- `backend/scripts/run_parallel_simulation.py`
- `backend/app/services/simulation_runner.py`
- `frontend/src/components/WorldState/`

---

## 5. 论文启发与工程化实现

NexusMind 的社会世界模型和 Agent 认知机制参考了多智能体社会仿真、世界模型、公共舆情传播和可信 Agent 方向的多篇前沿研究，并进行了工程化实现。

| 研究方向 | 工程化映射 |
|---|---|
| Social World Model | 将社会环境拆分为结构、动态和个性化感知 |
| Agent Society Simulation | 将 Agent 属性、情绪、认知状态与行为生成耦合 |
| Public Opinion Simulation | 引入公共舆论中的信念、情绪、立场漂移和理性干预思想 |
| Social Media Simulation | 复用多平台社交互动机制，支持发帖、评论、转发、搜索等行为 |
| Rumor / Information Spreading | 关注信息级联、群体扩散和传播路径 |
| Generative Agents | 引入记忆、反思和可置信行为的结构化脚手架 |
| World Models | 将环境状态、未来演化和决策支持统一建模 |

这些思想不是停留在文档中，而是映射到了可运行代码：

- `agent_brain.py`：AgentPrior、AgentCognitiveState、记忆和策略脚手架
- `world_state.py`：六维世界状态、事件检测、Topic State 和状态衰减
- `causal_graph.py`：事件因果边和因果链推断
- `run_parallel_simulation.py`：世界状态对 Agent 环境感知的注入
- `simulation_insight_service.py`：状态演化、风险机会、评分卡和决策简报

---

## 6. Agent 认知架构

系统中的 Agent 不再只是静态角色设定，而是具备可计算认知结构。

### 6.1 AgentPrior

AgentPrior 描述 Agent 的长期先验：

- 身份类型和职业角色
- 初始立场
- 核心目标
- 关注话题
- 风险容忍度
- 权威信任和同伴信任
- 从众性、表达欲和易感性
- 决策风格

### 6.2 AgentCognitiveState

AgentCognitiveState 描述每轮变化的认知状态：

- 注意焦点
- 情绪唤醒
- 感知风险
- 信息确定性
- 权威信任变化
- 同伴信任变化
- 当前目标显著性
- 最近策略和反思提示

### 6.3 个性化感知

同一个宏观世界状态，对不同 Agent 会产生不同感知。例如：

- 机构类 Agent 更关注稳定性、信任和风险。
- 媒体类 Agent 更关注热度、信息变化和传播价值。
- 学生或普通公众 Agent 更容易受到同伴反馈、情绪压力和立场分化影响。

相关实现：

- `backend/app/services/agent_brain.py`
- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_runner.py`

---

## 7. 产品工作流

### 7.1 五步主链路

| 阶段 | 名称 | 说明 |
|---|---|---|
| Step 1 | 事件图谱生成 | 从材料中抽取实体、关系和事件线索，构建知识图谱 |
| Step 2 | 群体环境建模 | 生成 Agent 画像、认知先验、平台配置和模拟参数 |
| Step 3 | 舆情态势推演 | Agent 在信息广场和话题社区交互，世界模型追踪态势变化 |
| Step 4 | 结果报告生成 | ReportAgent 调用图谱、Agent、世界模型和评估工具生成报告 |
| Step 5 | 深度交互 | 与 Agent 或报告智能体进行追问和解释 |

### 7.2 事件工作台

事件工作台用于真实事件的持续跟踪：

- 路由：`/incident/:projectId`
- 前端：`frontend/src/views/IncidentWorkspaceView.vue`
- 后端：`backend/app/api/incident.py`

支持能力：

- 持续追加材料
- 生成和切换事实基线版本
- 查看材料时间线
- 重建基线图谱
- 创建预测分支
- 对比不同干预方案
- 导出阶段性报告

---

## 8. 核心模块

### 8.1 材料接入与知识图谱

- 支持 PDF、Markdown、TXT 等文件材料
- 支持 Tavily 网络搜索抓取公开信息
- LLM 自动生成 Prescribed Ontology
- Graphiti + Neo4j 构建知识图谱
- 实体清洗、伪实体过滤和实体类型标注
- Neo4j 向量索引用于语义召回

相关文件：

- `backend/app/services/text_processor.py`
- `backend/app/services/ontology_generator.py`
- `backend/app/services/graph_builder.py`
- `backend/app/services/entity_cleaner.py`
- `backend/app/services/vector_store.py`

### 8.2 多智能体社会推演

- 基于 CAMEL-AI OASIS 的社交平台模拟
- 支持信息广场和话题社区双平台
- 支持发帖、评论、转发、点赞、搜索、关注等动作
- 每轮记录 Agent 行为、平台状态和世界状态
- 支持停止、续跑、重启和历史数据恢复

相关文件：

- `backend/app/services/simulation_runner.py`
- `backend/app/services/simulation_manager.py`
- `backend/scripts/run_parallel_simulation.py`
- `frontend/src/components/Step3Simulation.vue`

### 8.3 因果链与世界事件

- 自动检测世界状态显著变化
- 记录关键世界事件
- 推断事件间因果边
- 支持因果链追踪和可视化

相关文件：

- `backend/app/services/causal_graph.py`
- `frontend/src/components/WorldState/CausalGraphView.vue`
- `frontend/src/components/WorldState/EventTimeline.vue`

### 8.4 ReportAgent 报告引擎

ReportAgent 使用 ReACT 多轮推理模式，可调用多类工具生成结构化报告。

| 工具类别 | 工具 |
|---|---|
| 图谱检索 | `insight_forge`、`panorama_search`、`quick_search` |
| Agent 采访 | `interview_agents` |
| 世界模型 | `world_model_brief`、`state_evolution_analysis` |
| 因果分析 | `causal_chain_analysis` |
| 量化评估 | `evaluation_summary` |
| 态势评分 | `reputation_scorecard` |
| 决策支持 | `decision_support_brief` |
| 证据检索 | `simulation_evidence_search` |
| 认知分析 | `agent_cognition_analysis` |

相关文件：

- `backend/app/services/report_agent.py`
- `backend/app/services/simulation_insight_service.py`
- `backend/app/api/report.py`

---

## 9. 量化评估与 Benchmark

系统提供事后量化评估与真实案例对照验证。

### 9.1 评估内容

- 情感演化时序
- Agent 行为多样性
- 世界状态峰值、谷值、波动率和转折点
- 影响力 Agent 分析
- 因果图谱统计
- 世界模型反馈环统计

### 9.2 Benchmark 指标

| 指标 | 全称 | 权重 | 含义 |
|---|---|---:|---|
| TCS | Trend Consistency Score | 35% | 模拟走势与现实阶段方向是否一致 |
| TPH | Turning Point Hit Rate | 25% | 是否命中关键现实转折点 |
| KAC | Key Actor Coverage | 20% | 关键主体是否被图谱、Agent 与报告覆盖 |
| EOA | Event Order Accuracy | 20% | 模拟事件顺序与现实参考链是否一致 |

### 9.3 典型案例结果

Case 01 高校舆情案例当前记录：

| 模式 | TCS | TPH | KAC | EOA | 总分 |
|---|---:|---:|---:|---:|---:|
| Tier A / Full | 100.0 | 100.0 | 100.0 | 96.4 | **99.3 / A** |
| Tier B / Gated | 80.0 | 50.0 | 100.0 | 86.7 | **77.8 / B** |
| Tier C / Blind | 50.0 | 33.3 | 77.8 | 66.7 | **54.7 / C** |

该对照说明：更完整的事实图谱和上下文能够显著提升趋势一致性、关键拐点命中率和事件顺序准确度；当信息被限制或盲测时，系统仍能捕捉部分传播趋势，但深层转折和角色归因会明显下降。

相关文件：

- `benchmark/scoring.py`
- `benchmark/case_01_wuhan_university_library/`
- `backend/app/services/evaluation.py`
- `backend/app/api/evaluation.py`
- `frontend/src/api/evaluation.js`

---

## 10. 技术架构

| 层级 | 技术与模块 |
|---|---|
| 前端 | Vue 3、Vite、D3.js、可视化组件 |
| 后端 | Flask 3.x、REST API、本地文件持久化、异步任务管理 |
| 图谱层 | Graphiti、Neo4j、GraphRAG、VectorRAG |
| 模拟层 | CAMEL-AI OASIS、双平台社交互动模拟 |
| 世界模型 | WorldStateEngine、CausalGraphEngine、AgentBrain、SimulationInsightService |
| 报告层 | ReACT ReportAgent、多工具调用、Markdown/HTML/PDF 导出 |
| 评估层 | Benchmark scoring、情感/行为/影响力/状态演化分析 |

核心目录：

```text
NexusMind/
├── frontend/                         # Vue 3 + Vite 前端
│   └── src/
│       ├── views/                    # Home / Process / IncidentWorkspace / SimGraph
│       ├── components/               # 五步流程组件与世界模型组件
│       └── api/                      # graph / simulation / report / evaluation / incident API
├── backend/
│   ├── app/
│   │   ├── api/                      # Flask REST API
│   │   ├── services/                 # 图谱、模拟、世界模型、报告、评估核心逻辑
│   │   ├── models/                   # Project / Material / Baseline / ForecastRun
│   │   └── utils/                    # LLM、Graphiti、文件解析、日志等工具
│   ├── scripts/
│   │   └── run_parallel_simulation.py # OASIS 子进程与世界状态注入
│   └── uploads/                      # 本地运行数据、模拟日志、报告产物
├── benchmark/                        # 真实案例评测与评分脚本
├── docs/                             # 使用手册、比赛材料、案例资料与报告归档
│   ├── cases/                        # 真实案例材料与阶段时间线
│   │   ├── huazhong_agricultural_university/
│   │   └── wuhan_university/
│   ├── competition/                  # 比赛演示脚本与分镜文档
│   ├── manuals/                      # 使用手册
│   ├── planning/                     # 产品规划与蓝图
│   └── reports/                      # 外部报告与中间解析结果
├── word_modle/papers/                # 社会世界模型论文分析与规划文档
├── static/image/                     # README 图片与演示素材
└── docker-compose.yml
```

---

## 11. 快速开始

### 11.1 环境要求

| 组件 | 推荐版本 |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| Neo4j | 5.x |
| npm | 9+ |

### 11.2 环境变量

在项目根目录创建 `.env`：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j

# 可选：网络搜索
TAVILY_API_KEY=your_tavily_api_key
```

如本地 Neo4j 使用自定义端口，只需同步修改 `NEO4J_URI`。

### 11.3 安装依赖

```bash
# 根目录依赖 + 前端依赖
npm run setup

# 后端依赖（使用 uv）
npm run setup:backend
```

也可以手动安装：

```bash
cd frontend
npm install

cd ../backend
pip install -r requirements.txt
```

### 11.4 启动服务

```bash
# 根目录一键启动前后端
npm run dev
```

或分开启动：

```bash
# 后端
cd backend
python run.py

# 前端
cd frontend
npm run dev
```

默认地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:5001`
- Neo4j Browser：`http://localhost:7474`
- Neo4j Bolt：`bolt://localhost:7687`

### 11.5 Docker Compose 启动

如果希望使用容器方式同时启动 Neo4j 与 NexusMind：

```bash
docker compose up -d
```

`docker-compose.yml` 会读取根目录 `.env`。其中 `NEO4J_USERNAME` 和 `NEO4J_PASSWORD` 会用于初始化 Neo4j 容器的账号密码。

---

## 12. 比赛演示建议

用于计算机设计大赛时，建议不要逐个讲按钮，而是围绕真实事件的持续演化展开。

推荐主线：

1. **现实种子接入**：上传第一阶段材料，说明系统可从早期有限信息起跑。
2. **事实与图谱构建**：展示实体、关系和事件线索如何被结构化。
3. **舆情态势推演**：展示 Agent 在信息广场和话题社区中交互，社会世界模型跟踪六维状态。
4. **世界模型解释**：强调系统不是总结已有材料，而是在模拟扩散趋势、风险拐点和关键影响因素。
5. **事件工作台滚动更新**：追加后续材料，生成新基线和预测分支。
6. **决策支持输出**：展示风险、机会、推荐行动和证据链。

核心表达：

> 我们不是只对事件做一次静态分析，而是随着事件不断演化，持续更新事实基线、图谱理解、社会状态和决策判断。

---

## 13. 开源与致谢

NexusMind 的实现离不开开源生态和相关学术研究：

- 感谢 **CAMEL-AI OASIS** 提供多智能体社交仿真基础。
- 感谢 **Graphiti / Neo4j** 为知识图谱和检索层提供基础能力。
- 感谢 Vue、Flask、D3、OpenAI SDK 等开源项目。
- 社会世界模型与 Agent 认知设计参考了 Social World Model、Agent Society Simulation、Public Opinion Simulation、Generative Agents、World Models 等方向的研究成果。

本项目遵循 `AGPL-3.0` 开源许可。若基于本项目进行二次开发或部署，请遵守相应开源协议。
