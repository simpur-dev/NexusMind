# NexusMind 世界模型工作进展

> 更新时间：2026-04-18
> 项目定位：计算机设计大赛参赛作品 —— **基于论文的社会世界模型工程复现**
> 当前版本：**v7 (paper-grounded)**

---

## 一、项目定位与论文依据

本项目对以下两篇论文进行工程复现，构建可运行、可验证的社会世界模型：

| # | 论文 | 复现要素 |
|---|------|---------|
| 09 | **POSIM: Public Opinion Simulator with Social-BDI Agents** (2025) | Social-BDI 快慢信念层、Hawkes 时序、Rational Cognition 干预、**Empathy Paradox** 防踩坑 |
| 01 | **SocioVerse: A World Model for Social Simulation** (Fudan, 2025) | Social Environment 三件套：Social Structure / Social Dynamics / Personalized Context |
| 02 | **AgentSociety** (THU, 2025) | Emotion/Needs/Cognition 三层人设 |
| 04 | **OASIS** (CAMEL-AI, 2024) | 模拟底座（本项目使用的引擎）|
| 07 | **World Models Comprehensive Survey** (ACM CSUR 2025) | 宏观分类体系 |

论文原件：`papers/social_world_model/*.pdf`；本地抽取用于分析：`papers/social_world_model/_extracted/*.txt`（已 `.gitignore`）。

---

## 二、整体进度总览

| 层级 | 状态 | 备注 |
|------|------|------|
| 后端 · 世界状态引擎 | ✅ 完成 | `backend/app/services/world_state.py` (36 KB) |
| 后端 · 因果图谱引擎 | ✅ 完成 | `backend/app/services/causal_graph.py` (21 KB) |
| 后端 · 模拟运行挂载 | ✅ 完成 | `backend/app/services/simulation_runner.py` round_end 回调 + JSONL 持久化 |
| 后端 · Agent 认知扩展 | ✅ 完成 | `oasis_profile_generator.py` 扩展 internal_goal / utility_weights / risk_tolerance / authority_trust / emotion_sensitivity / is_opinion_leader |
| 后端 · Prompt 注入层（核心） | ✅ **v7 论文级重写** | `backend/scripts/run_parallel_simulation.py :: build_world_state_prompt` |
| REST API | ✅ 4 接口上线 | `world-state` / `events` / `causal-graph` / `inject-event` |
| 前端 · 世界模型面板 | ⚠️ 边栏版本 | `frontend/src/components/WorldStatePanel.vue` (14.7 KB)，嵌入 Step3 右侧 |
| 前端 · 独立展示视图 | ❌ 未做 | 原计划 P2，**答辩演示关键短板** |
| 单元测试 | ✅ 48 / 48 | `backend/tests/test_world_model.py` |
| 小规模 LLM 验证 | ✅ | `backend/tests/llm_validation_world_model.py` |
| 大规模 LLM 验证 | ✅ **70 % 胜率** | `backend/tests/llm_validation_large.py` 3 topics × 10 agents × 12 rounds × 2 seeds × 3 judges |

---

## 三、后端实现要点（论文映射）

### 3.1 WorldStateEngine — 对应 SocioVerse §2.1 Social Environment

6 维状态向量 + 事件流：

- `attention_level` / `panic_level` / `trust_level`
- `polarization_level` / `risk_level` / `stability_level`

每轮由 simulation_runner 回调，规则 + LLM 混合更新，持久化到
`{sim_dir}/world_state_history.jsonl` 与 `events.jsonl`。

### 3.2 CausalGraphEngine — 对应 Survey §5.1.3 Social Influence

三类因果边：`triggered` / `amplified` / `suppressed`，落盘 `causal_edges.jsonl`，
回应论文 §8.3 关于 "LLM 可解释性" 挑战。

### 3.3 Prompt 注入层（v7 核心）

`build_world_state_prompt()` 将状态向量、两阶趋势、事件流压缩为**可注入 Agent prompt** 的观察句，
通过 `patch_oasis_environment()` monkey-patch 注入 OASIS 的 `SocialEnvironment.to_text_prompt`。

**v7 的论文严格对齐：**

| 论文结论 | v7 对应实现 |
|----------|------------|
| POSIM §6 **Empathy Paradox**：EP priming 使 NER 单调放大（0.844 → 0.878），反向剂量效应 | 全量删除 "情绪扩散/恐慌弥漫" 等代言式措辞；删除 v6 acute_crisis / strong_recovery 放大器；删除 "强烈地" 强度档位 |
| POSIM §6 **Rational Cognition (RC)**：多视角理性分析使 NER 降至 0.571 | 观察句改 RC：`"围绕同一事实目前存在差异较大的多种解读"` `"后续走向依赖于接下来的权威信息"` |
| POSIM §6 **Emotional Regulation (ER)**：让 agent 识别自身情绪 | 维度描述改自我观察型：`"讨论中对不确定因素的担忧占比偏高"` 而非 `"公众情绪紧张"` |
| POSIM §3.3 快慢信念层 B_evt / B_emo (fast) vs B_psy / B_id (slow) | 只影响快层：保持阻尼注入，绝不重写人设 |
| SocioVerse §2.1 Social Dynamics：带时间戳的客观事件 | `_abstract_event` 改事实型：`"已有一份新的正式回应进入讨论"` 而非 `"官方表态正在重塑讨论焦点"` |

---

## 四、版本演进与量化基线

### 4.1 大规模 LLM 验证（3 topics × 10 agents × 12 rounds × 2 seeds × 3 judges = 6 runs × 18 judgments）

| 版本 | 核心变化 | Win Rate | Stability | Recovery | Crisis | Judge 票 (B:A) | 备注 |
|------|---------|----------|-----------|----------|--------|----------------|------|
| v5 | 骨架多形态化 + 二阶趋势 + 去实体锚点 | 61 % | 58 % | 8 % | 8 % | 16 : 2 | 起跳 |
| v6 | 加 "强烈地，" 强度档 + acute/strong 放大分支 | **56 %** ❌ | **33 %** ❌ | 42 % | 17 % | 12 : 6 | **Empathy Paradox 翻车** |
| **v7** | **POSIM RC + SocioVerse Social Dynamics 重写** | **70 %** ✅ | **83 %** | **67 %** | 42 % | 12 : 6 | **目标达成** |

### 4.2 v7 Judge 评分（4 维 × 18 judgments 累加）

| 维度 | A（无 WM）| B（有 WM）| Δ |
|------|-----------|-----------|---|
| emotion_evolution | 72 | **84** | +12 |
| role_differentiation | 83 | **86** | +3 |
| crisis_response | 68 | **87** | +19 |
| naturalness | 64 | **78** | +14 |

### 4.3 量化指标（6 runs 胜负）

| 指标 | A 赢 | B 赢 | tie | B 胜率 |
|------|------|------|-----|--------|
| Avg Sentiment | 0 | 5 | 1 | **92 %** |
| Sentiment Stability | 0 | 4 | 2 | **83 %** |
| Behavior Diversity | 1 | 4 | 1 | **75 %** |
| Recovery Response | 1 | 3 | 2 | **67 %** |
| Crisis Sensitivity | 3 | 2 | 1 | 42 % |

基线结果 JSON：`backend/tests/llm_validation_large_result.json`（已入库）。

---

## 五、前端现状与差距

- ✅ `WorldStatePanel.vue` 已实现：6 指标刻度条 / Current Summary / 关键词标签 / 上帝模式事件注入表单 / 因果链列表
- ⚠️ 位置是 Step3 右侧 320 px 边栏，**答辩时不便突出展示世界模型**
- ❌ 无状态趋势折线图（6 维 × rounds）
- ❌ 无 A/B 并排对比视图（量化结果无可视化）
- ❌ 无因果图力导向图（d3 已在依赖，未使用）
- ❌ 无独立路由（想看 WM 必须先跑完前两步）

---

## 六、已提交/待提交件

### 6.1 已入库（commit `7e111cd` on `backend_heng`）

- `backend/scripts/run_parallel_simulation.py` v7 prompt builder
- `backend/tests/test_world_model.py` 48 项单测
- `backend/tests/llm_validation_large.py` 大规模验证脚本
- `backend/tests/llm_validation_world_model.py` 小规模验证脚本
- `backend/tests/llm_validation_large_result.json` v7 70 % 基线结果
- `.gitignore` 排除论文抽取产物与一次性工具

### 6.2 未入库（本地开发件）

- `backend/tests/_paper_extract.py`（一次性 PDF 抽取工具，已 gitignore）
- `backend/tests/_v7_analysis.py`（本地结果分析脚本）
- `papers/social_world_model/_extracted/*.txt`（PDF 本地抽取，已 gitignore）

---

## 七、遗留任务与比赛优先级

| 级别 | 项 | 对比赛价值 |
|------|----|-----------|
| 🔴 高 | 前端独立 **World Model Observatory** 视图 + 6 维趋势图 + A/B 并排对比 | 答辩演示核心 |
| 🔴 高 | d3 力导向因果图（依赖已在） | 戏剧性可视化 |
| 🟡 中 | OPTIMIZATION_PLAN #9 舆情抓取接入 | 评委明确建议 |
| 🟡 中 | 答辩材料（架构图、3 min demo 脚本、README 章节） | 答辩必需 |
| 🟢 低 | 记忆反思（P3）、宏观评估接入报告 | 超出复现范围 |

---

## 八、一句话总结

NexusMind 世界模型后端已**按 POSIM + SocioVerse 工程化落地**，大规模 LLM 验证 **70 % 胜率** 可被论文依据解释，48 项单测保护；前端展示面仍是本项目离答辩 "高光" 状态的最后一段路。
