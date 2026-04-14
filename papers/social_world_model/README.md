# 社会世界模型相关论文（2023-2025）

> 收集时间：2026-04-14  
> 目的：为 NexusMind 世界模型反馈闭环提供理论支撑

## 核心论文

| # | 文件 | 论文 | 机构 | 年份 | 关键词 |
|---|------|------|------|------|--------|
| 01 | `01_SocioVerse_...` | **SocioVerse: A World Model for Social Simulation Powered by LLM Agents and A Pool of 10 Million Real-World Users** | 复旦大学 | 2025.04 | 社会世界模型, 千万用户池, 四大对齐引擎 |
| 02 | `02_AgentSociety_...` | **AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents** | 清华大学 | 2025.02 | 万人规模, 情感/需求/认知, 城市环境 |
| 03 | `03_GenSim_...` | **GenSim: A General Social Simulation Platform with LLM-based Agents** | 清华大学 | 2024.10 | 通用平台, 10万Agent, 纠错机制 |
| 04 | `04_OASIS_...` | **OASIS: Open Agent Social Interaction Simulations with One Million Agents** | CAMEL-AI | 2024.11 | 百万Agent, Twitter/Reddit, 社交现象复现 |
| 09 | `09_POSIM_...` | **POSIM: Public Opinion Simulator with Social-BDI Agents** | — | 2025.06 | 舆论模拟, BDI认知架构, Hawkes时序, 双向反馈 |

## 环境与传播

| # | 文件 | 论文 | 关键词 |
|---|------|------|--------|
| 05 | `05_MOSAIC_...` | **MOSAIC: Modeling Social AI for Content Dissemination and Regulation** (EMNLP 2025) | 内容传播, 监管, 网络结构验证 |
| 06 | `06_Rumor_Spreading_...` | **Simulating Rumor Spreading in Social Networks using LLM Agents** | 谣言传播, belief state, 网络结构影响 |

## 综述与经典

| # | 文件 | 论文 | 关键词 |
|---|------|------|--------|
| 07 | `07_World_Models_...` | **Understanding World or Predicting Future? A Comprehensive Survey of World Models** (ACM CSUR 2025) | 世界模型综述, 分类体系 |
| 08 | `08_Generative_Agents_...` | **Generative Agents: Interactive Simulacra of Human Behavior** (Stanford, UIST 2023) | 经典开山之作, 25个Agent小镇 |

## 与 NexusMind 的对应关系

| NexusMind 模块 | 对应论文概念 |
|----------------|-------------|
| `WorldStateEngine` | SocioVerse 的 Social Dynamics; POSIM 的 Hawkes 时序引擎 |
| `build_world_state_prompt` + 阻尼注入 | SocioVerse 的 Social Environment → Agent 注入; POSIM 的 Agent-Environment Interaction |
| `patch_oasis_environment` | OASIS 的 `SocialEnvironment.to_text_prompt` 扩展 |
| Agent persona (user_char) | AgentSociety 的 Emotion/Needs/Cognition 三层; POSIM 的 BDI 四层信念 |
| A/B 测试 (--no-world-model) | POSIM 的 Checkpoint 反事实对比; SocioVerse 的消融实验 |

## 推荐阅读顺序

1. **08** Generative Agents — 了解基础范式
2. **04** OASIS — 了解我们使用的底层框架
3. **01** SocioVerse — 最直接的 "社会世界模型" 定义
4. **09** POSIM — 舆情场景最相关，BDI + Hawkes 是重要参考
5. **02** AgentSociety — 大规模 + 认知模型深度设计
6. **07** World Models Survey — 宏观视野，理解 World Model 分类体系
