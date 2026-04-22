"""
Report Agent服务
使用LLM实现ReACT模式的模拟报告生成

功能：
1. 根据模拟需求和图谱信息生成报告
2. 先规划目录结构，然后分段生成
3. 每段采用ReACT多轮思考与反思模式
4. 支持与用户对话，在对话中自主调用检索工具
"""

import os
import json
import time
import re
import threading
import concurrent.futures
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .graph_tools import (
    GraphToolsService, 
    SearchResult, 
    InsightForgeResult, 
    PanoramaResult,
    InterviewResult
)

logger = get_logger('nexusmind.report_agent')


class ReportLogger:
    """
    Report Agent 详细日志记录器
    
    在报告文件夹中生成 agent_log.jsonl 文件，记录每一步详细动作。
    每行是一个完整的 JSON 对象，包含时间戳、动作类型、详细内容等。
    """
    
    def __init__(self, report_id: str):
        """
        初始化日志记录器
        
        Args:
            report_id: 报告ID，用于确定日志文件路径
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """确保日志文件所在目录存在"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """获取从开始到现在的耗时（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        记录一条日志
        
        Args:
            action: 动作类型，如 'start', 'tool_call', 'llm_response', 'section_complete' 等
            stage: 当前阶段，如 'planning', 'generating', 'completed'
            details: 详细内容字典，不截断
            section_title: 当前章节标题（可选）
            section_index: 当前章节索引（可选）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # 追加写入 JSONL 文件
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """记录报告生成开始"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": "报告生成任务开始"
            }
        )
    
    def log_planning_start(self):
        """记录大纲规划开始"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "开始规划报告大纲"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """记录规划时获取的上下文信息"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "获取模拟上下文信息",
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """记录大纲规划完成"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "大纲规划完成",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """记录章节生成开始"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"开始生成章节: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """记录 ReACT 思考过程"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": f"ReACT 第{iteration}轮思考"
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """记录工具调用"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": f"调用工具: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """记录工具调用结果（完整内容，不截断）"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # 完整结果，不截断
                "result_length": len(result),
                "message": f"工具 {tool_name} 返回结果"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """记录 LLM 响应（完整内容，不截断）"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # 完整响应，不截断
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM 响应 (工具调用: {has_tool_calls}, 最终答案: {has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """记录章节内容生成完成（仅记录内容，不代表整个章节完成）"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # 完整内容，不截断
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"章节 {section_title} 内容生成完成"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        记录章节生成完成

        前端应监听此日志来判断一个章节是否真正完成，并获取完整内容
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"章节 {section_title} 生成完成"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """记录报告生成完成"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "报告生成完成"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """记录错误"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": f"发生错误: {error_message}"
            }
        )


class ReportConsoleLogger:
    """
    Report Agent 控制台日志记录器
    
    将控制台风格的日志（INFO、WARNING等）写入报告文件夹中的 console_log.txt 文件。
    这些日志与 agent_log.jsonl 不同，是纯文本格式的控制台输出。
    """
    
    def __init__(self, report_id: str):
        """
        初始化控制台日志记录器
        
        Args:
            report_id: 报告ID，用于确定日志文件路径
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """确保日志文件所在目录存在"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """设置文件处理器，将日志同时写入文件"""
        import logging
        
        # 创建文件处理器
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # 使用与控制台相同的简洁格式
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # 添加到 report_agent 相关的 logger
        loggers_to_attach = [
            'nexusmind.report_agent',
            'nexusmind.graph_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # 避免重复添加
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """关闭文件处理器并从 logger 中移除"""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'nexusmind.report_agent',
                'nexusmind.graph_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """析构时确保关闭文件处理器"""
        self.close()


class ReportStatus(str, Enum):
    """报告状态"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "description": self.description
        }

    def to_markdown(self, level: int = 2) -> str:
        """转换为Markdown格式"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """报告大纲"""
    title: str
    summary: str
    sections: List[ReportSection]
    core_concepts: List[str] = None
    
    def __post_init__(self):
        if self.core_concepts is None:
            self.core_concepts = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "core_concepts": self.core_concepts or [],
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """完整报告"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Prompt 模板常量
# ═══════════════════════════════════════════════════════════════

# ── 工具描述 ──

TOOL_DESC_INSIGHT_FORGE = """\
【深度洞察检索 - 强大的检索工具】
这是我们强大的检索函数，专为深度分析设计。它会：
1. 自动将你的问题分解为多个子问题
2. 从多个维度检索模拟图谱中的信息
3. 整合语义搜索、实体分析、关系链追踪的结果
4. 返回最全面、最深度的检索内容

【使用场景】
- 需要深入分析某个话题
- 需要了解事件的多个方面
- 需要获取支撑报告章节的丰富素材

【返回内容】
- 相关事实原文（可直接引用）
- 核心实体洞察
- 关系链分析"""

TOOL_DESC_PANORAMA_SEARCH = """\
【广度搜索 - 获取全貌视图】
这个工具用于获取模拟结果的完整全貌，特别适合了解事件演变过程。它会：
1. 获取所有相关节点和关系
2. 区分当前有效的事实和历史/过期的事实
3. 帮助你了解舆情是如何演变的

【使用场景】
- 需要了解事件的完整发展脉络
- 需要对比不同阶段的舆情变化
- 需要获取全面的实体和关系信息

【返回内容】
- 当前有效事实（模拟最新结果）
- 历史/过期事实（演变记录）
- 所有涉及的实体"""

TOOL_DESC_QUICK_SEARCH = """\
【简单搜索 - 快速检索】
轻量级的快速检索工具，适合简单、直接的信息查询。

【使用场景】
- 需要快速查找某个具体信息
- 需要验证某个事实
- 简单的信息检索

【返回内容】
- 与查询最相关的事实列表"""

TOOL_DESC_INTERVIEW_AGENTS = """\
【深度采访 - 真实Agent采访（双平台）】
调用OASIS模拟环境的采访API，对正在运行的模拟Agent进行真实采访！
这不是LLM模拟，而是调用真实的采访接口获取模拟Agent的原始回答。
默认在Twitter和Reddit两个平台同时采访，获取更全面的观点。

功能流程：
1. 自动读取人设文件，了解所有模拟Agent
2. 智能选择与采访主题最相关的Agent（如学生、媒体、官方等）
3. 自动生成采访问题
4. 调用 /api/simulation/interview/batch 接口在双平台进行真实采访
5. 整合所有采访结果，提供多视角分析

【使用场景】
- 需要从不同角色视角了解事件看法（学生怎么看？媒体怎么看？官方怎么说？）
- 需要收集多方意见和立场
- 需要获取模拟Agent的真实回答（来自OASIS模拟环境）
- 想让报告更生动，包含"采访实录"

【返回内容】
- 被采访Agent的身份信息
- 各Agent在Twitter和Reddit两个平台的采访回答
- 关键引言（可直接引用）
- 采访摘要和观点对比

【重要】需要OASIS模拟环境正在运行才能使用此功能！"""

# ── 世界模型工具描述 ──

TOOL_DESC_WORLD_MODEL_BRIEF = """\
【世界模型状态简报】
获取模拟世界的六维状态全景：关注度、恐慌度、信任度、极化度、风险等级、稳定性。
包含当前状态值、最近趋势（上升/下降/稳定）、最显著异常维度、情绪分布。

【使用场景】
- 需要了解模拟结束时的宏观态势
- 需要写"当前状态诊断"类内容
- 需要引用具体的信任度/风险等级等数值"""

TOOL_DESC_STATE_EVOLUTION = """\
【状态演化分析】
分析六维状态在整个模拟过程中的演化轨迹：峰值/谷值时刻、波动率、初始→最终变化量、关键转折点事件。

【使用场景】
- 需要描述"事态如何发展"的完整脉络
- 需要识别拐点（信任度骤降/恐慌激增的时刻）
- 需要写趋势预测类内容"""

TOOL_DESC_CAUSAL_CHAIN = """\
【因果链分析】
返回模拟中推断出的因果关系：事件A→导致→事件B，包含因果强度和推断依据。
按因果强度排序，展示最重要的因果链。

【使用场景】
- 需要解释"为什么会出现这种状态"
- 需要写机制诊断类内容
- 需要追溯风险的根源"""

TOOL_DESC_EVALUATION_SUMMARY = """\
【量化评估摘要】
聚合模拟的量化评估结果：情感分析（平均/峰值/负面主导比）、行为多样性（基尼系数、活跃比）、
状态演化（波动率）、影响力分析（Top影响力Agent）。

【使用场景】
- 需要引用量化数据支撑论点
- 需要写行为分析/影响力分析类内容
- 需要呈现表格化的评估数据"""

TOOL_DESC_REPUTATION_SCORECARD = """\
【综合态势评分卡】
基于世界模型六维状态计算四项综合评分：
- 综合健康评分（声誉总体状况）
- 风险升级评分（事态恶化可能性）
- 信任修复潜力（修复空间大小）
- 极化压力评分（群体对立程度）
并给出整体状态判定（高压脆弱/风险积累/修复中/相对稳定）。

【使用场景】
- 需要对整体态势下判断
- 需要写核心判断/结论类内容
- 需要量化的评分数据"""

TOOL_DESC_DECISION_SUPPORT = """\
【决策支持简报】
综合评分卡+事件+趋势+因果链，自动生成：
- 主要风险信号（及严重等级）
- 机会窗口（及置信度）
- 分阶段行动建议（24h内/72h内/2周内）

【使用场景】
- 需要写决策建议/行动方案类内容
- 需要识别风险和机会
- 需要给出可操作的建议"""

TOOL_DESC_EVIDENCE_SEARCH = """\
【模拟证据检索】
在模拟产出的所有数据中搜索特定话题的证据：
搜索范围包括事件流、Agent行为日志、因果边证据、Agent认知轨迹。

【使用场景】
- 需要为某个论点找到具体的模拟证据
- 需要查找特定 Agent或特定话题的行为记录
- 需要引用具体的模拟事件或Agent发言"""

TOOL_DESC_AGENT_COGNITION = """\
【Agent认知动态分析】
分析模拟中所有Agent的群体认知演变：
- 情绪激活度轨迹与峰值事件
- 策略转换统计（观望→质疑→宣传等）
- 对权威/同侪信任演变
- 群体分化趋势与代表性Agent状态

【使用场景】
- 分析舆论参与者的心理的转变规律
- 识别关键信任崩塌或情绪引爆点
- 为声誉修复/危机管理提供行为证据
- 与世界模型宏观数据交叉印证"""

# ── 大纲规划 prompt ──

PLAN_SYSTEM_PROMPT = """\
你是一个「未来预测报告」的撰写专家，拥有对模拟世界的「上帝视角」——你可以洞察模拟中每一位Agent的行为、言论和互动。

【核心理念】
我们构建了一个模拟世界，并向其中注入了特定的「模拟需求」作为变量。模拟世界的演化结果，就是对未来可能发生情况的预测。你正在观察的不是"实验数据"，而是"未来的预演"。

【你的任务】
撰写一份「未来预测报告」，回答：
1. 在我们设定的条件下，未来发生了什么？
2. 各类Agent（人群）是如何反应和行动？
3. 这个模拟揭示了哪些值得关注的未来趋势和风险？

【报告定位】
- ✅ 这是一份基于模拟的未来预测报告，揭示"如果这样，未来会怎样"
- ✅ 聚焦于预测结果：事件走向、群体反应、涌现现象、潜在风险
- ✅ 模拟世界中的Agent言行就是对未来人群行为的预测
- ❌ 不是对现实世界现状的分析
- ❌ 不是泛泛而谈的舆情综述

【章节数量与结构】
- 最少5个章节，最多8个章节
- 每个章节内部可使用 ### 子节来组织论证层次
- 章节标题使用中文编号，例如："一、情景设定与分析边界""二、核心判断"
- 报告应形成完整的分析闭环，建议覆盖以下维度（可根据实际情况调整）：
  1. 情景设定与分析边界（明确本报告的视角与方法边界）
  2. 核心判断（2-4条凝练结论）
  3. 决策/机制诊断（拆解"为什么会这样"）
  4. 群体反应图谱（各类群体如何解读、行动）
  5. 风险结构识别（当前策略的隐性风险）
  6. 趋势预测（短/中/长期演化路径）
  7. 决策建议（若希望改善需要做什么）
  8. 结论（收束全文核心论断）
- 使用冷静、克制、分析性的语言，像政策分析师而非咨询顾问
- 避免咨询话术（"穿透式诊断""赤字""塌方"等夸张标签）和编造数据

【核心概念要求】
- 为整份报告提炼1-3个贯穿全文的核心分析概念（如"被动合规型止损""程序正义饱和""澄清过剩与共情赤字"）
- 这些概念应在摘要中引入，在各章节中反复引用和深化
- 概念命名要精准、可理解，避免堆砌术语

【章节描述要求】
- 每个章节的 description 必须包含 2-3 个明确的分析问题（以问号结尾），这些问题将指导章节撰写
- description 还应说明该章节的分析视角和期望的论证深度
- 相邻章节之间应有清晰的逻辑递进关系（如：现象→原因→影响→对策）

请输出JSON格式的报告大纲，格式如下：
{
    "title": "报告标题",
    "summary": "报告摘要（一段话，80-150字，概括核心预测发现与关键判断，用**粗体**标注核心概念）",
    "core_concepts": ["核心概念1", "核心概念2"],
    "sections": [
        {
            "title": "一、章节标题",
            "description": "章节核心任务描述。本章需回答：1. 问题一？2. 问题二？3. 问题三？分析视角：xxx"
        }
    ]
}

注意：sections数组最少5个，最多8个元素！"""

PLAN_USER_PROMPT_TEMPLATE = """\
【预测场景设定】
我们向模拟世界注入的变量（模拟需求）：{simulation_requirement}

【模拟世界规模】
- 参与模拟的实体数量: {total_nodes}
- 实体间产生的关系数量: {total_edges}
- 实体类型分布: {entity_types}
- 活跃Agent数量: {total_entities}

【模拟预测到的部分未来事实样本】
{related_facts_json}

{world_model_context}

请以「上帝视角」审视这个未来预演：
1. 在我们设定的条件下，未来呈现出了什么样的状态？
2. 各类人群（Agent）是如何反应和行动的？
3. 这个模拟揭示了哪些值得关注的未来趋势？

根据预测结果，设计最合适的报告章节结构。

【再次提醒】报告章节数量：最少5个，最多8个，形成完整分析闭环。章节标题使用中文编号（一、二、三…）。"""

# ── 章节生成 prompt ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
你是一个「未来预测报告」的撰写专家，正在撰写报告的一个章节。

报告标题: {report_title}
报告摘要: {report_summary}
贯穿全文的核心概念: {core_concepts}
预测场景（模拟需求）: {simulation_requirement}

当前要撰写的章节: {section_title}
章节写作指引: {section_description}

═══════════════════════════════════════════════════════════════
【核心理念】
═══════════════════════════════════════════════════════════════

模拟世界是对未来的预演。我们向模拟世界注入了特定条件（模拟需求），
模拟中Agent的行为和互动，就是对未来人群行为的预测。

你的任务是：
- 揭示在设定条件下，未来发生了什么
- 预测各类人群（Agent）是如何反应和行动的
- 发现值得关注的未来趋势、风险和机会

❌ 不要写成对现实世界现状的分析
✅ 要聚焦于"未来会怎样"——模拟结果就是预测的未来

═══════════════════════════════════════════════════════════════
【⚠️ 写作质量要求 - 这是区分优秀报告与普通报告的关键】
═══════════════════════════════════════════════════════════════

一、分析纵深（每个分析点必须达到三层纵深，不能停留在事实罗列）：
1. **现象层**：模拟中观察到了什么（引用Agent言行或数据）
2. **解释层**：这意味着什么（公众/群体如何解读、背后的逻辑是什么）
3. **推论层**：由此推出什么判断（对信任/风险/决策的含义）

示例：
  现象："多数Agent将校方决策标签化为'司法判了我才动'"
  → 解释：这说明公众将校方行为解码为被动合规而非主动纠错
  → 推论：因此校方修复了结果，却没有修复人们对其治理能力的预期

二、语句通顺与连贯性（极其重要！）：
1. **段落间必须有逻辑过渡**：每段开头应自然承接上一段的结论，不能突然跳到新话题。
   使用过渡句如"在此基础上""与此形成对比的是""值得注意的是""进一步观察发现"等。
2. **禁止碎片化罗列**：不要写成孤立的要点堆砌，每个分析段落应包含完整的论证链
   （观察→分析→结论），段落之间要有因果或递进关系。
3. **句子必须完整通顺**：避免半句话断开、主谓不搭配、成分残缺。
   每个句子都应独立成立，可以被大声朗读而不觉得别扭。
4. **避免口语化和套话**：不要使用"总的来说""不难看出""毫无疑问"等空洞套话，
   用具体分析替代笼统判断。
5. **控制列表使用**：列表不应超过5项，且每项应有实质内容（不少于一句完整的话）。
   当列表过长时，改为分段论述。

三、章节写作指引对照：
上方"章节写作指引"中列出了本章节需要回答的核心问题。
你的章节内容必须逐一覆盖这些问题，确保每个问题都有基于模拟数据的实质性回答。
如果某个问题的数据不足，明确说明而非回避。

四、概念贯穿：
在本章节中应自然引用或回扣上述"核心概念"，使全文形成统一的分析框架。
不需要每段都提，但关键论点应与核心概念形成呼应。

═══════════════════════════════════════════════════════════════
【最重要的规则 - 必须遵守】
═══════════════════════════════════════════════════════════════

1. 【调用工具观察模拟世界】
   - 你正在以「上帝视角」观察未来的预演
   - 所有内容必须来自工具返回的模拟数据，禁止使用你自己的知识
   - 每个章节调用 3–7 次工具，根据实际需要选择最相关的工具
   - 如果工具返回的信息已充分，不需要为了凑数而继续调用

2. 【必须引用Agent的原始言行】
   - Agent的发言和行为是对未来人群行为的预测
   - 在报告中使用引用格式展示这些预测，例如：
     > "某类人群会表示：原文内容..."
   - 这些引用是模拟预测的核心证据

3. 【语言一致性 - 引用内容必须翻译为报告语言】
   - 工具返回的内容可能包含英文或中英文混杂的表述
   - 如果模拟需求和材料原文是中文的，报告必须全部使用中文撰写
   - 当你引用工具返回的英文或中英混杂内容时，必须将其翻译为流畅的中文后再写入报告
   - 翻译时保持原意不变，确保表述自然通顺
   - 这一规则同时适用于正文和引用块（> 格式）中的内容

4. 【忠实呈现预测结果】
   - 报告内容必须反映模拟世界中的代表未来的模拟结果
   - 不要添加模拟中不存在的信息
   - 如果某方面信息不足，如实说明

═══════════════════════════════════════════════════════════════
【⚠️ 格式规范 - 极其重要！】
═══════════════════════════════════════════════════════════════

【章节格式规则】
- ❌ 禁止使用 # 或 ## 标题（章节主标题由系统自动添加）
- ❌ 禁止在内容开头重复章节标题
- ✅ 可以使用 ### 编号子节来组织论证层次，例如 "### 1. 子节标题"
- ✅ 使用**粗体**、段落分隔、引用、列表来组织内容
- ✅ 善用 Markdown 表格呈现多维对比（群体对比、指标对比、策略对比等）

【正确示例】
```
基于现有通报内容与世界模型推演结果，本报告形成以下核心判断。

### 1. 当前策略实现的是"程序止损"，不是"信任重建"

校方通过撤销处分、发布复核结论，完成了对争议的程序性收束。但问题在于，
**程序被纠正，并不等于关系被修复**。

> "我们不是反对纠错，是反对纠错只发生在法院盖章之后。"

| 群体 | 主导认知 | 主要情绪 | 对信任修复的含义 |
|------|----------|----------|------------------|
| 在校学生 | 认可纠错，不信任机制 | 焦虑、疏离 | 程序信任受损 |
| 校友 | 支持纠偏，要求制度回应 | 失望、监督 | 外部压力持续 |

### 2. 司法认可并未自动转化为校方信任

这意味着司法终局只提供了"不得不改"的外部约束，
却没有为学校赢得"愿意相信你已经学会改"的声誉资本。
```

【错误示例】
```
## 执行摘要          ← 错误！不要用 ## 标题
# 一、首发阶段       ← 错误！不要用 # 标题

本章节分析了...
```

═══════════════════════════════════════════════════════════════
【可用检索工具】（每章节调用3-7次）
═══════════════════════════════════════════════════════════════

{tools_description}

【工具使用建议 - 请混合使用不同工具，不要只用一种】
- insight_forge: 深度洞察分析，自动分解问题并多维度检索事实和关系
- panorama_search: 广角全景搜索，了解事件全貌、时间线和演变过程
- quick_search: 快速验证某个具体信息点
- interview_agents: 采访模拟Agent，获取不同角色的第一人称观点和真实反应
- world_model_brief: 获取世界模型六维状态全景（信任度、极化度等当前值和趋势）
- state_evolution_analysis: 获取状态演化轨迹（峰值、谷值、转折点）
- causal_chain_analysis: 获取因果关系链（事件A→导致→事件B）
- reputation_scorecard: 获取综合态势评分卡（健康/风险/修复/极化四维评分）
- decision_support_brief: 获取决策支持简报（风险、机会、分阶段建议）
- evaluation_summary: 获取量化评估摘要（情感、行为、影响力分析）
- simulation_evidence_search: 在模拟数据中检索特定话题的证据
- agent_cognition_analysis: 分析Agent群体认知动态（情绪轨迹、策略转换、信任演变）

═══════════════════════════════════════════════════════════════
【工作流程】
═══════════════════════════════════════════════════════════════

每次回复你只能做以下两件事之一（不可同时做）：

选项A - 调用工具：
输出你的思考，然后用以下格式调用一个工具：
<tool_call>
{{"name": "工具名称", "parameters": {{"参数名": "参数值"}}}}
</tool_call>
系统会执行工具并把结果返回给你。你不需要也不能自己编写工具返回结果。

选项B - 输出最终内容：
当你已通过工具获取了足够信息，以 "Final Answer:" 开头输出章节内容。

⚠️ 严格禁止：
- 禁止在一次回复中同时包含工具调用和 Final Answer
- 禁止自己编造工具返回结果（Observation），所有工具结果由系统注入
- 每次回复最多调用一个工具

═══════════════════════════════════════════════════════════════
【章节内容要求】
═══════════════════════════════════════════════════════════════

1. 内容必须基于工具检索到的模拟数据
2. 引用模拟Agent原声或工具返回的关键文本作为论据
3. 使用Markdown格式：
   - 可以使用 ### 编号子节组织论证层次（如 "### 1. 子节标题"）
   - 使用 **粗体文字** 标记重点概念
   - 使用列表（-或1.2.3.）组织要点
   - 善用表格（| 格式）呈现多维对比
   - 使用空行分隔不同段落
   - ❌ 禁止使用 # 或 ## 标题（由系统添加）
4. 【引用格式规范 - 必须单独成段】
   引用必须独立成段，前后各有一个空行，不能混在段落中：

   ✅ 正确格式：
   ```
   校方的回应被认为缺乏实质内容。

   > "校方的应对模式在瞬息万变的社交媒体环境中显得僵化和迟缓。"

   这一评价反映了公众的普遍不满。
   ```

   ❌ 错误格式：
   ```
   校方的回应被认为缺乏实质内容。> "校方的应对模式..." 这一评价反映了...
   ```
5. 保持与其他章节的逻辑连贯性
6. 【避免重复】仔细阅读下方已完成的章节内容，不要重复描述相同的信息
7. 【标题规则】❌ 禁止 # 和 ## ✅ 允许 ### 编号子节（如 "### 1. 子节标题"）
8. 【善用表格】对比群体、维度、策略时，优先使用 Markdown 表格呈现
9. 【语言风格】冷静、克制、分析性，像政策分析师而非咨询顾问。避免夸张修辞和情绪化标签。
10. 【来源规范】正文中禁止出现工具名称（如 insight_forge、panorama_search 等）、
   fact/evt 编号、采访索引等内部标识。引用数据时统一写为"来源：模拟数据"或"来源：Agent采访"。
11. 【禁止编造】如果工具返回的信息不足以支撑某个论点，直接说明"当前数据不足"，
   不要自行补充百分比、金额、阈值、时间窗口或外部案例。只引用工具实际返回的内容。"""

SECTION_USER_PROMPT_TEMPLATE = """\
已完成的章节内容（请仔细阅读，避免重复）：
{previous_content}

═══════════════════════════════════════════════════════════════
【当前任务】撰写章节: {section_title}
═══════════════════════════════════════════════════════════════

【重要提醒】
1. 仔细阅读上方已完成的章节，避免重复相同的内容！
2. 开始前先调用工具获取模拟数据，根据实际需要选择最相关的工具
3. 报告内容必须来自工具返回的数据，不要使用自己的知识
4. Final Answer 中禁止出现工具名称、fact/evt 编号、采访索引等内部标识
5. 如果工具返回的信息不足，直接说明“当前数据不足”，不要自行编造数据

【⚠️ 格式警告 - 必须遵守】
- ❌ 不要使用 # 或 ## 标题（由系统添加）
- ❌ 不要写"{section_title}"作为开头
- ✅ 可以使用 ### 编号子节组织论证（如 "### 1. 子节标题"）
- ✅ 善用表格呈现多维对比

请开始：
1. 首先思考（Thought）这个章节需要什么信息
2. 然后调用工具（Action）获取模拟数据
3. 收集足够信息后输出 Final Answer"""

# ── ReACT 循环内消息模板 ──

REACT_OBSERVATION_TEMPLATE = """\
Observation（检索结果）:

═══ 工具 {tool_name} 返回 ═══
{result}

═══════════════════════════════════════════════════════════════
已调用工具 {tool_calls_count}/{max_tool_calls} 次（已用: {used_tools_str}）{unused_hint}
- 如果信息充分：以 "Final Answer:" 开头输出章节内容（必须引用上述原文）
- Final Answer 中禁止出现工具名称（insight_forge、panorama_search 等）、fact/evt 编号、采访索引等内部标识
- 如果需要更多信息：调用一个工具继续检索
═══════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "【注意】你只调用了{tool_calls_count}次工具，至少需要{min_tool_calls}次。"
    "请再调用工具获取更多模拟数据，然后再输出 Final Answer。{unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "当前只调用了 {tool_calls_count} 次工具，至少需要 {min_tool_calls} 次。"
    "请调用工具获取模拟数据。{unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "工具调用次数已达上限（{tool_calls_count}/{max_tool_calls}），不能再调用工具。"
    '请立即基于已获取的信息，以 "Final Answer:" 开头输出章节内容。'
)

REACT_UNUSED_TOOLS_HINT = "\n💡 你还没有使用过: {unused_list}，建议尝试不同工具获取多角度信息"

REACT_FORCE_FINAL_MSG = "已达到工具调用限制，请直接输出 Final Answer: 并生成章节内容。"

# ── 全文润色 prompt ──

POLISH_SYSTEM_PROMPT = """\
你是一位顶级的政策分析报告编辑，正在对一份已完成的「未来预测报告」进行最终润色。

【你的任务】
对全文进行最后一轮编辑优化，提升报告的整体质量。你需要：

1. **语句通顺性（最高优先级）**：
   - 逐句检查主谓搭配、成分完整性，修正病句和半截话
   - 确保每个句子独立朗读时自然通顺，没有生硬拼接感
   - 修复因机器生成导致的不自然表述（如主语缺失、指代不明、语序混乱）
   - 长句拆短：超过60字的句子考虑拆分为两个短句，避免嵌套过深

2. **段落衔接与逻辑连贯**：
   - 每段开头必须自然承接上一段的结论或观点，不能突然跳到新话题
   - 补充必要的过渡句（如"在此基础上""与此形成对比的是""进一步观察发现"）
   - 检查段与段之间是否存在逻辑断裂，如有则补充过渡性分析
   - 章节之间的衔接：前一章节的结论应在后一章节的开篇有所呼应

3. **概念一致性**：检查核心分析概念在各章节中的使用是否一致，术语表述是否统一

4. **论证纵深**：如果某处只有现象描述而缺乏分析推论，补充"这意味着…""由此可以判断…"等推论层

5. **消除口语化和套话**：
   - 删除或改写"总的来说""不难看出""毫无疑问""众所周知""显而易见"等空洞套话
   - 将"很大程度上""在某种意义上"等模糊表述替换为更具体的分析性表述
   - 消除咨询话术和夸张修辞（如"穿透式诊断""赤字""塌方"等标签化表述）

6. **引用质量**：确保引用块（> 格式）前后有空行、与正文分离，引用内容有分析价值

7. **重复消除**：不同章节间如果存在高度相似的论述、相同引用或雷同结论，合并或删除重复部分

8. **列表优化**：
   - 超过5项的列表改为分段论述
   - 每个列表项必须有实质内容（不少于一句完整的话），删除"详见下文""略"等无效项
   - 避免通篇碎片化罗列，确保列表前后有总结性段落

9. **格式规范**：
   - 章节标题为 ## 格式
   - 子节标题为 ### 格式
   - 不应出现 #### 或更深层级
   - 消除多余空行（连续3个以上空行→2个）
   - 确保表格表头和列数对齐

【绝对禁止】
- ❌ 不要添加任何新的事实、数据、引用或案例（你没有数据源）
- ❌ 不要改变任何实质性结论或判断方向
- ❌ 不要删除完整的章节或子节
- ❌ 不要添加工具名称、fact/evt编号等内部标识
- ❌ 不要编造百分比、金额、时间窗口等数据

【输出要求】
直接输出润色后的完整报告 Markdown 文本（从 # 标题 开始），不要添加任何解释性前言或后记。"""

POLISH_USER_PROMPT = """\
以下是需要润色的完整报告：

{report_content}

请按以下优先级逐项执行润色（不要跳过任何一项）：

1. 【通顺性】逐句朗读检查，修正所有主谓不搭配、成分残缺、语序混乱的句子
2. 【衔接性】检查每个段落的开头是否自然承接上段结论，补充缺失的过渡句
3. 【去套话】删除"总的来说""不难看出""毫无疑问"等空洞表述，替换为具体分析
4. 【去重复】跨章节检查是否有雷同论述或相同引用，合并或删除
5. 【格式】确保引用块前后有空行，表格列数对齐，无多余空行

直接输出润色后的完整 Markdown 报告。"""

# ── Chat prompt ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
你是一个简洁高效的模拟预测助手。

【背景】
预测条件: {simulation_requirement}

【已生成的分析报告】
{report_content}

【规则】
1. 优先基于上述报告内容回答问题
2. 直接回答问题，避免冗长的思考论述
3. 仅在报告内容不足以回答时，才调用工具检索更多数据
4. 回答要简洁、清晰、有条理
5. 无论模拟环境状态如何，都必须正常回答用户问题。不要主动告知用户环境状态或拒绝对话
6. 即使某些工具不可用，也可以用报告内容和其他可用工具来回答

【可用工具】（仅在需要时使用，最多调用1-2次）
{tools_description}

【工具调用格式】
<tool_call>
{{"name": "工具名称", "parameters": {{"参数名": "参数值"}}}}
</tool_call>

【回答风格】
- 简洁直接，不要长篇大论
- 使用 > 格式引用关键内容
- 优先给出结论，再解释原因"""

CHAT_OBSERVATION_SUFFIX = "\n\n请简洁回答问题。"


# ═══════════════════════════════════════════════════════════════
# ReportAgent 主类
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - 模拟报告生成Agent

    采用ReACT（Reasoning + Acting）模式：
    1. 规划阶段：分析模拟需求，规划报告目录结构
    2. 生成阶段：逐章节生成内容，每章节可多次调用工具获取信息
    3. 反思阶段：检查内容完整性和准确性
    """
    
    # 最大工具调用次数（每个章节）
    MAX_TOOL_CALLS_PER_SECTION = 7
    
    # 最大反思轮数
    MAX_REFLECTION_ROUNDS = 3
    
    # 对话中的最大工具调用次数
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        graph_tools: Optional[GraphToolsService] = None
    ):
        """
        初始化Report Agent
        
        Args:
            graph_id: 图谱ID
            simulation_id: 模拟ID
            simulation_requirement: 模拟需求描述
            llm_client: LLM客户端（可选）
            graph_tools: 图谱工具服务（可选）
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        
        self.llm = llm_client or LLMClient()
        self.graph_tools = graph_tools or GraphToolsService()
        
        # 世界模型洞察服务（如果有模拟数据）
        self.insight_service = None
        if simulation_id:
            try:
                from .simulation_insight_service import SimulationInsightService
                self.insight_service = SimulationInsightService(simulation_id)
                logger.info(f"SimulationInsightService 初始化成功: {simulation_id}")
            except Exception as e:
                logger.warning(f"SimulationInsightService 初始化失败（世界模型工具不可用）: {e}")
        
        # 工具定义
        self.tools = self._define_tools()
        
        # 日志记录器（在 generate_report 中初始化）
        self.report_logger: Optional[ReportLogger] = None
        # 控制台日志记录器（在 generate_report 中初始化）
        self.console_logger: Optional[ReportConsoleLogger] = None
        
        logger.info(f"ReportAgent 初始化完成: graph_id={graph_id}, simulation_id={simulation_id}")
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """定义可用工具"""
        base_tools = {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "你想深入分析的问题或话题",
                    "report_context": "当前报告章节的上下文（可选，有助于生成更精准的子问题）"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "搜索查询，用于相关性排序",
                    "include_expired": "是否包含过期/历史内容（默认True）"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "搜索查询字符串",
                    "limit": "返回结果数量（可选，默认10）"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "采访主题或需求描述（如：'了解学生对宿舍甲醛事件的看法'）",
                    "max_agents": "最多采访的Agent数量（可选，默认5，最大10）"
                }
            },
        }
        
        # 如果世界模型服务可用，注册世界模型工具
        if self.insight_service:
            world_model_tools = {
                "world_model_brief": {
                    "name": "world_model_brief",
                    "description": TOOL_DESC_WORLD_MODEL_BRIEF,
                    "parameters": {}
                },
                "state_evolution_analysis": {
                    "name": "state_evolution_analysis",
                    "description": TOOL_DESC_STATE_EVOLUTION,
                    "parameters": {}
                },
                "causal_chain_analysis": {
                    "name": "causal_chain_analysis",
                    "description": TOOL_DESC_CAUSAL_CHAIN,
                    "parameters": {}
                },
                "evaluation_summary": {
                    "name": "evaluation_summary",
                    "description": TOOL_DESC_EVALUATION_SUMMARY,
                    "parameters": {}
                },
                "reputation_scorecard": {
                    "name": "reputation_scorecard",
                    "description": TOOL_DESC_REPUTATION_SCORECARD,
                    "parameters": {}
                },
                "decision_support_brief": {
                    "name": "decision_support_brief",
                    "description": TOOL_DESC_DECISION_SUPPORT,
                    "parameters": {}
                },
                "simulation_evidence_search": {
                    "name": "simulation_evidence_search",
                    "description": TOOL_DESC_EVIDENCE_SEARCH,
                    "parameters": {
                        "query": "搜索关键词或话题",
                        "limit": "返回结果数量（可选，默认15）"
                    }
                },
                "agent_cognition_analysis": {
                    "name": "agent_cognition_analysis",
                    "description": TOOL_DESC_AGENT_COGNITION,
                    "parameters": {}
                },
            }
            base_tools.update(world_model_tools)
        
        return base_tools
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        执行工具调用
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            report_context: 报告上下文（用于InsightForge）
            
        Returns:
            工具执行结果（文本格式）
        """
        logger.info(f"执行工具: {tool_name}, 参数: {parameters}")
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.graph_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # 广度搜索 - 获取全貌
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.graph_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # 简单搜索 - 快速检索
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.graph_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # 深度采访 - 调用真实的OASIS采访API获取模拟Agent的回答（双平台）
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.graph_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            # ========== 向后兼容的旧工具（内部重定向到新工具） ==========
            
            elif tool_name == "search_graph":
                # 重定向到 quick_search
                logger.info("search_graph 已重定向到 quick_search")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.graph_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.graph_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # 重定向到 insight_forge，因为它更强大
                logger.info("get_simulation_context 已重定向到 insight_forge")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.graph_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            # ========== 世界模型工具 ==========
            
            elif tool_name == "world_model_brief":
                if not self.insight_service:
                    return "世界模型数据不可用（模拟尚未完成或数据缺失）"
                result = self.insight_service.get_world_model_brief()
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            elif tool_name == "state_evolution_analysis":
                if not self.insight_service:
                    return "世界模型数据不可用"
                result = self.insight_service.get_state_evolution_analysis()
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            elif tool_name == "causal_chain_analysis":
                if not self.insight_service:
                    return "因果图谱数据不可用"
                result = self.insight_service.get_causal_chain_analysis()
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            elif tool_name == "evaluation_summary":
                if not self.insight_service:
                    return "评估数据不可用"
                result = self.insight_service.get_evaluation_summary()
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            elif tool_name == "reputation_scorecard":
                if not self.insight_service:
                    return "世界模型数据不可用"
                result = self.insight_service.get_reputation_scorecard()
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            elif tool_name == "decision_support_brief":
                if not self.insight_service:
                    return "决策支持数据不可用"
                result = self.insight_service.get_decision_support_brief()
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            elif tool_name == "simulation_evidence_search":
                if not self.insight_service:
                    return "模拟证据数据不可用"
                query = parameters.get("query", "")
                limit = parameters.get("limit", 15)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.insight_service.search_simulation_evidence(query, limit=limit)
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            elif tool_name == "agent_cognition_analysis":
                if not self.insight_service:
                    return "Agent认知数据不可用"
                result = self.insight_service.get_agent_cognition_analysis()
                return result.get("text", json.dumps(result, ensure_ascii=False))
            
            else:
                available = ", ".join(self.tools.keys())
                return f"未知工具: {tool_name}。请使用以下工具之一: {available}"
                
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}")
            return f"工具执行失败: {str(e)}"
    
    # 合法的工具名称集合，用于裸 JSON 兜底解析时校验
    VALID_TOOL_NAMES = {
        "insight_forge", "panorama_search", "quick_search", "interview_agents",
        "world_model_brief", "state_evolution_analysis", "causal_chain_analysis",
        "evaluation_summary", "reputation_scorecard", "decision_support_brief",
        "simulation_evidence_search", "agent_cognition_analysis",
    }

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        从LLM响应中解析工具调用

        支持的格式（按优先级）：
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. 裸 JSON（响应整体或单行就是一个工具调用 JSON）
        """
        tool_calls = []

        # 格式1: XML风格（标准格式）
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # 格式2: 兜底 - LLM 直接输出裸 JSON（没包 <tool_call> 标签）
        # 只在格式1未匹配时尝试，避免误匹配正文中的 JSON
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # 响应可能包含思考文字 + 裸 JSON，尝试提取最后一个 JSON 对象
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """校验解析出的 JSON 是否是合法的工具调用"""
        # 支持 {"name": ..., "parameters": ...} 和 {"tool": ..., "params": ...} 两种键名
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # 统一键名为 name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    @staticmethod
    def _normalize_section_output(content: str) -> str:
        """清洗章节输出中残留的内部标识（工具名、fact/evt 编号、采访索引等）"""
        if not content:
            return content

        text = content

        # 1. 括号内包含工具名 → 替换为通用来源标签
        tool_label_map = [
            (r'[（(][^）)]*(?:insight_forge|panorama_search|quick_search)[^）)]*[）)]', '（来源：模拟数据）'),
            (r'[（(][^）)]*interview_agents[^）)]*[）)]', '（来源：Agent采访）'),
        ]
        for pattern, replacement in tool_label_map:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 2. 正文中残留的裸工具名 → 替换为通用表述
        bare_tool_map = {
            'insight_forge': '深度检索',
            'panorama_search': '全景搜索',
            'quick_search': '快速检索',
            'interview_agents': 'Agent采访',
        }
        for raw, label in bare_tool_map.items():
            text = re.sub(rf'\b{raw}\b', label, text, flags=re.IGNORECASE)

        # 3. fact_xxx / evt_xxx 编号
        text = re.sub(r'\b(?:fact|evt)_[A-Za-z0-9_]+\b', '', text)

        # 4. 采访索引（如 "采访索引3"）
        text = re.sub(r'(?:采访索引|索引)\s*\d+', '', text)

        # 5. 连续重复来源标签去重
        text = re.sub(r'（来源：([^）]+)）(?:\s*（来源：\1）)+', r'（来源：\1）', text)

        # 6. 修复引用块格式：确保 > 引用块前后有空行
        lines = text.split('\n')
        fixed_lines = []
        for idx, line in enumerate(lines):
            is_quote = line.strip().startswith('>')
            prev_is_blank = (idx == 0) or (fixed_lines and fixed_lines[-1].strip() == '')
            if is_quote and not prev_is_blank and fixed_lines:
                fixed_lines.append('')
            fixed_lines.append(line)
            # 引用块后面如果紧跟非空行，也加空行
            if is_quote and idx + 1 < len(lines):
                next_line = lines[idx + 1].strip()
                if next_line and not next_line.startswith('>'):
                    fixed_lines.append('')
        text = '\n'.join(fixed_lines)

        # 7. 清除残留的空来源标签，如 （来源：） ()
        text = re.sub(r'[（(]来源：\s*[）)]', '', text)

        # 8. 清除口语化套话开头（如段首 "总的来说，""不难看出，"）
        cliches = [
            r'(?m)^总的来说[，,]\s*',
            r'(?m)^不难看出[，,]\s*',
            r'(?m)^毫无疑问[，,]\s*',
            r'(?m)^众所周知[，,]\s*',
            r'(?m)^显而易见[，,]\s*',
        ]
        for pattern in cliches:
            text = re.sub(pattern, '', text)

        # 9. 清理多余空白
        text = re.sub(r'[ \t]{2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _polish_full_report(self, markdown_content: str) -> str:
        """
        对组装后的完整报告进行 LLM 全局润色
        
        修复跨章节的概念不一致、逻辑衔接、重复论述、格式问题等。
        不添加新事实，只优化表达。
        
        Args:
            markdown_content: 组装后的原始 Markdown 报告
            
        Returns:
            润色后的 Markdown 报告
        """
        logger.info("开始全文润色...")
        
        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": POLISH_SYSTEM_PROMPT},
                    {"role": "user", "content": POLISH_USER_PROMPT.format(
                        report_content=markdown_content
                    )}
                ],
                temperature=0.2,
                max_tokens=16384
            )
            
            if response and len(response.strip()) > len(markdown_content) * 0.5:
                # 润色结果有效（长度至少为原文的50%，防止截断或空返回）
                polished = response.strip()
                # 确保以 # 开头（去掉LLM可能添加的前言）
                if not polished.startswith('#'):
                    hash_idx = polished.find('\n#')
                    if hash_idx >= 0:
                        polished = polished[hash_idx + 1:]
                    else:
                        # LLM 没有按要求返回，使用原文
                        logger.warning("润色结果未以 # 开头，使用原始报告")
                        return markdown_content
                
                logger.info(f"全文润色完成: {len(markdown_content)} → {len(polished)} 字符")
                return polished
            else:
                logger.warning("润色结果无效（为空或过短），使用原始报告")
                return markdown_content
                
        except Exception as e:
            logger.error(f"全文润色失败: {e}，使用原始报告")
            return markdown_content

    def _get_tools_description(self, exclude_interview: bool = False) -> str:
        """生成工具描述文本
        
        Args:
            exclude_interview: 是否排除 interview_agents 工具（模拟环境未运行时排除）
        """
        desc_parts = ["可用工具："]
        for name, tool in self.tools.items():
            if exclude_interview and name == "interview_agents":
                continue
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  参数: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        规划报告大纲
        
        使用LLM分析模拟需求，规划报告的目录结构
        
        Args:
            progress_callback: 进度回调函数
            
        Returns:
            ReportOutline: 报告大纲
        """
        logger.info("开始规划报告大纲...")
        
        if progress_callback:
            progress_callback("planning", 0, "正在分析模拟需求...")
        
        # 首先获取模拟上下文
        context = self.graph_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, "正在生成报告大纲...")
        
        # 获取世界模型上下文（如果可用）
        world_model_context = ""
        if self.insight_service:
            try:
                bundle = self.insight_service.get_report_context_bundle()
                world_model_context = bundle.get("text", "")
                if world_model_context:
                    logger.info(f"世界模型上下文已注入大纲规划（{len(world_model_context)} 字符）")
            except Exception as e:
                logger.warning(f"获取世界模型上下文失败: {e}")
        
        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
            world_model_context=world_model_context,
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, "正在解析大纲结构...")
            
            # 解析大纲
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content="",
                    description=section_data.get("description", "")
                ))
            
            outline = ReportOutline(
                title=response.get("title", "模拟分析报告"),
                summary=response.get("summary", ""),
                sections=sections,
                core_concepts=response.get("core_concepts", [])
            )
            
            if progress_callback:
                progress_callback("planning", 100, "大纲规划完成")
            
            logger.info(f"大纲规划完成: {len(sections)} 个章节")
            return outline
            
        except Exception as e:
            logger.error(f"大纲规划失败: {str(e)}")
            # 返回默认大纲（5个章节，作为fallback）
            return ReportOutline(
                title="未来预测报告",
                summary="基于模拟预测的未来趋势与风险分析",
                sections=[
                    ReportSection(title="一、情景设定与分析边界", description="本报告的分析视角、方法边界与模拟世界的基本设定。本章需回答：1. 模拟世界的核心变量和边界条件是什么？2. 哪些因素在模拟范围内、哪些不在？"),
                    ReportSection(title="二、核心判断", description="凝练2-4条核心结论。本章需回答：1. 模拟揭示的最重要发现是什么？2. 这些发现对决策者意味着什么？"),
                    ReportSection(title="三、群体反应图谱", description="各类群体如何解读和行动。本章需回答：1. 不同群体的主导认知和情绪反应有何差异？2. 哪些群体的反应最具影响力？"),
                    ReportSection(title="四、风险结构与趋势预测", description="当前策略的隐性风险与演化路径。本章需回答：1. 最大的潜在风险是什么？2. 短/中/长期可能的演化路径是什么？"),
                    ReportSection(title="五、决策建议与结论", description="可执行的建议与全文收束。本章需回答：1. 若希望改善，优先应采取哪些措施？2. 如何在不同时间窗口内分步行动？")
                ]
            )
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        使用ReACT模式生成单个章节内容
        
        ReACT循环：
        1. Thought（思考）- 分析需要什么信息
        2. Action（行动）- 调用工具获取信息
        3. Observation（观察）- 分析工具返回结果
        4. 重复直到信息足够或达到最大次数
        5. Final Answer（最终回答）- 生成章节内容
        
        Args:
            section: 要生成的章节
            outline: 完整大纲
            previous_sections: 之前章节的内容（用于保持连贯性）
            progress_callback: 进度回调
            section_index: 章节索引（用于日志记录）
            
        Returns:
            章节内容（Markdown格式）
        """
        logger.info(f"ReACT生成章节: {section.title}")
        
        # 记录章节开始日志
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        # 获取核心概念（如果大纲中有）
        core_concepts_str = ""
        if hasattr(outline, 'core_concepts') and outline.core_concepts:
            core_concepts_str = "、".join(outline.core_concepts)
        else:
            core_concepts_str = "（由你根据报告摘要提炼）"
        
        # 获取章节写作指引（大纲中的 description）
        section_description = section.description or "（无额外指引，请根据章节标题自行规划写作重点）"
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            core_concepts=core_concepts_str,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            section_description=section_description,
            tools_description=self._get_tools_description(),
        )

        # 构建用户prompt - 每个已完成章节各传入最大4000字
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # 每个章节最多4000字
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "（这是第一个章节）"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT循环
        tool_calls_count = 0
        max_iterations = 10  # 最大迭代轮数（含重试截断的余量）
        min_tool_calls = 3  # 最少工具调用次数
        conflict_retries = 0  # 工具调用与Final Answer同时出现的连续冲突次数
        used_tools = set()  # 记录已调用过的工具名
        all_tools = set(self.tools.keys())

        # 报告上下文，用于InsightForge的子问题生成
        report_context = f"章节标题: {section.title}\n模拟需求: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"深度检索与撰写中 ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})"
                )
            
            # 调用LLM
            response = self.llm.chat(
                messages=messages,
                temperature=0.25,
                max_tokens=16384
            )

            # 检查 LLM 返回是否为 None（API 异常或内容为空）
            if response is None:
                logger.warning(f"章节 {section.title} 第 {iteration + 1} 次迭代: LLM 返回 None")
                # 如果还有迭代次数，添加消息并重试
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "（响应为空）"})
                    messages.append({"role": "user", "content": "请继续生成内容。"})
                    continue
                # 最后一次迭代也返回 None，跳出循环进入强制收尾
                break

            logger.debug(f"LLM响应: {response[:200]}...")

            # 解析一次，复用结果
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── 冲突处理：LLM 同时输出了工具调用和 Final Answer ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"章节 {section.title} 第 {iteration+1} 轮: "
                    f"LLM 同时输出工具调用和 Final Answer（第 {conflict_retries} 次冲突）"
                )

                if conflict_retries <= 2:
                    # 前两次：丢弃本次响应，要求 LLM 重新回复
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "【格式错误】你在一次回复中同时包含了工具调用和 Final Answer，这是不允许的。\n"
                            "每次回复只能做以下两件事之一：\n"
                            "- 调用一个工具（输出一个 <tool_call> 块，不要写 Final Answer）\n"
                            "- 输出最终内容（以 'Final Answer:' 开头，不要包含 <tool_call>）\n"
                            "请重新回复，只做其中一件事。"
                        ),
                    })
                    continue
                else:
                    # 第三次：降级处理，截断到第一个工具调用，强制执行
                    logger.warning(
                        f"章节 {section.title}: 连续 {conflict_retries} 次冲突，"
                        "降级为截断执行第一个工具调用"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # 记录 LLM 响应日志
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── 情况1：LLM 输出了 Final Answer ──
            if has_final_answer:
                # 工具调用次数不足，拒绝并要求继续调工具
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"（这些工具还未使用，推荐用一下他们: {', '.join(unused_tools)}）" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # 提取 Final Answer 内容
                final_answer = response.split("Final Answer:")[-1].strip()
                
                # 检测 max_tokens 截断导致 Final Answer 内容为空
                if len(final_answer) < 50:
                    logger.warning(
                        f"章节 {section.title}: Final Answer 内容过短（{len(final_answer)} 字符），"
                        "可能被 max_tokens 截断，要求 LLM 直接输出章节内容"
                    )
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "你的 Final Answer 内容被截断了（可能是输出长度不够）。\n"
                            "请不要再写 Thought，直接以 'Final Answer:' 开头输出完整的章节正文内容。\n"
                            "不需要任何分析过程，直接输出 Markdown 格式的章节正文。"
                        ),
                    })
                    continue
                
                # 正常结束
                final_answer = self._normalize_section_output(final_answer)
                logger.info(f"章节 {section.title} 生成完成（工具调用: {tool_calls_count}次）")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── 情况2：LLM 尝试调用工具 ──
            if has_tool_calls:
                # 工具额度已耗尽 → 明确告知，要求输出 Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # 只执行第一个工具调用
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM 尝试调用 {len(tool_calls)} 个工具，只执行第一个: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # 构建未使用工具提示
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── 情况3：既没有工具调用，也没有 Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # 工具调用次数不足，推荐未用过的工具
                unused_tools = all_tools - used_tools
                unused_hint = f"（这些工具还未使用，推荐用一下他们: {', '.join(unused_tools)}）" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # 工具调用已足够，LLM 输出了内容但没带 "Final Answer:" 前缀
            # 直接将这段内容作为最终答案，不再空转
            logger.info(f"章节 {section.title} 未检测到 'Final Answer:' 前缀，直接采纳LLM输出作为最终内容（工具调用: {tool_calls_count}次）")
            final_answer = self._normalize_section_output(response.strip())

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # 达到最大迭代次数，强制生成内容
        logger.warning(f"章节 {section.title} 达到最大迭代次数，强制生成")
        messages.append({
            "role": "user",
            "content": (
                "已达到工具调用限制。请不要再写 Thought 分析过程，"
                "直接以 'Final Answer:' 开头输出完整的章节正文内容。"
                "只输出 Markdown 格式的章节正文，不需要任何前置分析。"
            )
        })
        
        # 强制收尾最多重试2次（防止再次被截断）
        for force_attempt in range(2):
            response = self.llm.chat(
                messages=messages,
                temperature=0.25,
                max_tokens=16384
            )

            if response is None:
                logger.error(f"章节 {section.title} 强制收尾时 LLM 返回 None")
                final_answer = f"（本章节生成失败：LLM 返回空响应，请稍后重试）"
                break
            elif "Final Answer:" in response:
                final_answer = response.split("Final Answer:")[-1].strip()
            else:
                final_answer = response.strip()
            
            if len(final_answer) >= 50:
                break
            
            logger.warning(
                f"章节 {section.title} 强制收尾第{force_attempt+1}次: "
                f"内容过短（{len(final_answer)}字符），再次要求"
            )
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": "内容太短或被截断。请直接输出完整章节正文，不要写Thought。"
            })
        else:
            if len(final_answer) < 50:
                logger.error(f"章节 {section.title} 多次强制收尾仍为空，标记生成失败")
                final_answer = f"（本章节内容生成不完整，请重新生成报告）"
        
        final_answer = self._normalize_section_output(final_answer)
        
        # 记录章节内容生成完成日志
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        生成完整报告（分章节实时输出）
        
        每个章节生成完成后立即保存到文件夹，不需要等待整个报告完成。
        文件结构：
        reports/{report_id}/
            meta.json       - 报告元信息
            outline.json    - 报告大纲
            progress.json   - 生成进度
            section_01.md   - 第1章节
            section_02.md   - 第2章节
            ...
            full_report.md  - 完整报告
        
        Args:
            progress_callback: 进度回调函数 (stage, progress, message)
            report_id: 报告ID（可选，如果不传则自动生成）
            
        Returns:
            Report: 完整报告
        """
        import uuid
        
        # 如果没有传入 report_id，则自动生成
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # 已完成的章节标题列表（用于进度追踪）
        completed_section_titles = []
        
        try:
            # 初始化：创建报告文件夹并保存初始状态
            ReportManager._ensure_report_folder(report_id)
            
            # 初始化日志记录器（结构化日志 agent_log.jsonl）
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # 初始化控制台日志记录器（console_log.txt）
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, "初始化报告...",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # 阶段1: 规划大纲
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, "开始规划报告大纲...",
                completed_sections=[]
            )
            
            # 记录规划开始日志
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, "开始规划报告大纲...")
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline
            
            # 记录规划完成日志
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # 保存大纲到文件
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, f"大纲规划完成，共{len(outline.sections)}个章节",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(f"大纲已保存到文件: {report_id}/outline.json")
            
            # 阶段2: 分批并行生成章节
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # 保存内容用于上下文
            progress_lock = threading.Lock()  # 保护进度更新的并发安全
            
            PARALLEL_BATCH_SIZE = 1  # 串行生成，保证逻辑连贯
            
            def _generate_one_section(i: int, section, snapshot_previous: List[str]):
                """并行任务：生成单个章节并返回结果"""
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                with progress_lock:
                    ReportManager.update_progress(
                        report_id, "generating", base_progress,
                        f"正在生成章节: {section.title} ({section_num}/{total_sections})",
                        current_section=section.title,
                        completed_sections=list(completed_section_titles)
                    )
                    if progress_callback:
                        progress_callback(
                            "generating", base_progress,
                            f"正在生成章节: {section.title} ({section_num}/{total_sections})"
                        )
                
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=snapshot_previous,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage,
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                return i, section, section_content
            
            # 将章节分成多个批次，每批内并行，批间串行
            for batch_start in range(0, total_sections, PARALLEL_BATCH_SIZE):
                batch_end = min(batch_start + PARALLEL_BATCH_SIZE, total_sections)
                batch_items = list(range(batch_start, batch_end))
                
                # 快照当前已完成的章节内容，同批内共享相同上下文
                snapshot = list(generated_sections)
                
                logger.info(
                    f"开始并行生成第 {batch_start+1}-{batch_end} 章节 "
                    f"(共 {total_sections} 章节, 批大小 {len(batch_items)})"
                )
                
                if len(batch_items) == 1:
                    # 单章节直接生成，无需线程池
                    _, section, content = _generate_one_section(
                        batch_items[0], outline.sections[batch_items[0]], snapshot
                    )
                    batch_results = [(batch_items[0], section, content)]
                else:
                    # 多章节并行生成
                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch_items)) as executor:
                        futures = {
                            executor.submit(
                                _generate_one_section, idx, outline.sections[idx], snapshot
                            ): idx
                            for idx in batch_items
                        }
                        batch_results = []
                        for future in concurrent.futures.as_completed(futures):
                            batch_results.append(future.result())
                    
                    # 按章节顺序排列结果
                    batch_results.sort(key=lambda x: x[0])
                
                # 收集本批结果（按顺序）
                for idx, section, section_content in batch_results:
                    section_num = idx + 1
                    section.content = section_content
                    generated_sections.append(f"## {section.title}\n\n{section_content}")
                    
                    ReportManager.save_section(report_id, section_num, section)
                    completed_section_titles.append(section.title)
                    
                    full_section_content = f"## {section.title}\n\n{section_content}"
                    if self.report_logger:
                        self.report_logger.log_section_full_complete(
                            section_title=section.title,
                            section_index=section_num,
                            full_content=full_section_content.strip()
                        )
                    
                    logger.info(f"章节已保存: {report_id}/section_{section_num:02d}.md")
                    
                    base_progress = 20 + int((idx / total_sections) * 70)
                    ReportManager.update_progress(
                        report_id, "generating",
                        base_progress + int(70 / total_sections),
                        f"章节 {section.title} 已完成",
                        current_section=None,
                        completed_sections=completed_section_titles
                    )
            
            # 阶段3: 组装完整报告
            if progress_callback:
                progress_callback("generating", 95, "正在组装完整报告...")
            
            ReportManager.update_progress(
                report_id, "generating", 95, "正在组装完整报告...",
                completed_sections=completed_section_titles
            )
            
            # 使用ReportManager组装完整报告
            raw_content = ReportManager.assemble_full_report(report_id, outline)
            
            # 阶段4: LLM全文润色
            if progress_callback:
                progress_callback("generating", 97, "正在进行全文润色...")
            ReportManager.update_progress(
                report_id, "generating", 97, "正在进行全文润色...",
                completed_sections=completed_section_titles
            )
            
            polished_content = self._polish_full_report(raw_content)
            report.markdown_content = polished_content
            
            # 如果润色后内容有变化，覆盖写入文件
            if polished_content != raw_content:
                full_path = ReportManager._get_report_markdown_path(report_id)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(polished_content)
                logger.info(f"润色后报告已覆盖写入: {full_path}")
            
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # 计算总耗时
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # 记录报告完成日志
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # 保存最终报告
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "报告生成完成",
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, "报告生成完成")
            
            logger.info(f"报告生成完成: {report_id}")
            
            # 关闭控制台日志记录器
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(f"报告生成失败: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e)
            
            # 记录错误日志
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # 保存失败状态
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"报告生成失败: {str(e)}",
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # 忽略保存失败的错误
            
            # 关闭控制台日志记录器
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        与Report Agent对话
        
        在对话中Agent可以自主调用检索工具来回答问题
        
        Args:
            message: 用户消息
            chat_history: 对话历史
            
        Returns:
            {
                "response": "Agent回复",
                "tool_calls": [调用的工具列表],
                "sources": [信息来源]
            }
        """
        logger.info(f"Report Agent对话: {message[:50]}...")
        
        chat_history = chat_history or []
        
        # 获取已生成的报告内容
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # 限制报告长度，避免上下文过长
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [报告内容已截断] ..."
        except Exception as e:
            logger.warning(f"获取报告内容失败: {e}")
        
        # 检查模拟环境是否存活，决定是否包含 interview_agents 工具
        env_alive = False
        try:
            from .simulation_runner import SimulationRunner
            env_alive = SimulationRunner.check_env_alive(self.simulation_id)
        except Exception:
            pass
        
        tools_desc = self._get_tools_description(exclude_interview=not env_alive)
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "（暂无报告）",
            tools_description=tools_desc,
        )

        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        
        # 过滤掉历史中包含"模拟环境已停止"等错误回复，避免LLM模仿旧错误模式
        _toxic_patterns = ["模拟环境已停止", "返回 Step 3", "重启模拟环境", "无法调用工具", "无法执行"]
        clean_history = []
        for h in chat_history[-10:]:
            if h.get("role") == "assistant" and any(p in h.get("content", "") for p in _toxic_patterns):
                continue  # 跳过包含旧错误的assistant消息
            clean_history.append(h)
        
        # 添加历史对话
        for h in clean_history:
            messages.append(h)
        
        # 添加用户消息
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT循环（简化版）
        tool_calls_made = []
        max_iterations = 2  # 减少迭代轮数
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # 解析工具调用
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # 没有工具调用，直接返回响应
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # 执行工具调用（限制数量）
            tool_results = []
            for call in tool_calls[:1]:  # 每轮最多执行1次工具调用
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # 限制结果长度
                })
                tool_calls_made.append(call)
            
            # 将结果添加到消息
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']}结果]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # 达到最大迭代，获取最终响应
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # 清理响应
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    报告管理器
    
    负责报告的持久化存储和检索
    
    文件结构（分章节输出）：
    reports/
      {report_id}/
        meta.json          - 报告元信息和状态
        outline.json       - 报告大纲
        progress.json      - 生成进度
        section_01.md      - 第1章节
        section_02.md      - 第2章节
        ...
        full_report.md     - 完整报告
    """
    
    # 报告存储目录
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """确保报告根目录存在"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """获取报告文件夹路径"""
        return os.path.join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """确保报告文件夹存在并返回路径"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """获取报告元信息文件路径"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """获取完整报告Markdown文件路径"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """获取大纲文件路径"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """获取进度文件路径"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """获取章节Markdown文件路径"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """获取 Agent 日志文件路径"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """获取控制台日志文件路径"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        获取控制台日志内容
        
        这是报告生成过程中的控制台输出日志（INFO、WARNING等），
        与 agent_log.jsonl 的结构化日志不同。
        
        Args:
            report_id: 报告ID
            from_line: 从第几行开始读取（用于增量获取，0 表示从头开始）
            
        Returns:
            {
                "logs": [日志行列表],
                "total_lines": 总行数,
                "from_line": 起始行号,
                "has_more": 是否还有更多日志
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # 保留原始日志行，去掉末尾换行符
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 已读取到末尾
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        获取完整的控制台日志（一次性获取全部）
        
        Args:
            report_id: 报告ID
            
        Returns:
            日志行列表
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        获取 Agent 日志内容
        
        Args:
            report_id: 报告ID
            from_line: 从第几行开始读取（用于增量获取，0 表示从头开始）
            
        Returns:
            {
                "logs": [日志条目列表],
                "total_lines": 总行数,
                "from_line": 起始行号,
                "has_more": 是否还有更多日志
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # 跳过解析失败的行
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # 已读取到末尾
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        获取完整的 Agent 日志（用于一次性获取全部）
        
        Args:
            report_id: 报告ID
            
        Returns:
            日志条目列表
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        保存报告大纲
        
        在规划阶段完成后立即调用
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"大纲已保存: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        保存单个章节

        在每个章节生成完成后立即调用，实现分章节输出

        Args:
            report_id: 报告ID
            section_index: 章节索引（从1开始）
            section: 章节对象

        Returns:
            保存的文件路径
        """
        cls._ensure_report_folder(report_id)

        # 构建章节Markdown内容 - 清理可能存在的重复标题
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # 保存文件
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"章节已保存: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        清理章节内容
        
        1. 移除内容开头与章节标题重复的Markdown标题行
        2. 将所有 ### 及以下级别的标题转换为粗体文本
        
        Args:
            content: 原始内容
            section_title: 章节标题
            
        Returns:
            清理后的内容
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 检查是否是Markdown标题行
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # 检查是否是与章节标题重复的标题（全文范围移除）
                normalized_title = section_title.replace(' ', '').replace('　', '').strip()
                normalized_text = title_text.replace(' ', '').replace('　', '').strip()
                if normalized_text == normalized_title:
                    skip_next_empty = True
                    continue
                
                # ### 及以下保留（允许子节结构），# 和 ## 转为粗体
                if level >= 3:
                    cleaned_lines.append(stripped)
                else:
                    cleaned_lines.append(f"**{title_text}**")
                    cleaned_lines.append("")  # 添加空行
                continue
            
            # 如果上一行是被跳过的标题，且当前行为空，也跳过
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # 移除开头的空行
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # 移除开头的分隔线
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # 同时移除分隔线后的空行
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        更新报告生成进度
        
        前端可以通过读取progress.json获取实时进度
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """获取报告生成进度"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        获取已生成的章节列表
        
        返回所有已保存的章节文件信息
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 从文件名解析章节索引
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        组装完整报告
        
        从已保存的章节文件组装完整报告，并进行标题清理
        """
        folder = cls._get_report_folder(report_id)
        
        # 构建报告头部
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # 按顺序读取所有章节文件
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # 后处理：清理整个报告的标题问题
        md_content = cls._post_process_report(md_content, outline)
        
        # 保存完整报告
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"完整报告已组装: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        后处理报告内容
        
        1. 移除重复的标题
        2. 保留报告主标题(#)和章节标题(##)，移除其他级别的标题(###, ####等)
        3. 清理多余的空行和分隔线
        
        Args:
            content: 原始报告内容
            outline: 报告大纲
            
        Returns:
            处理后的内容
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # 收集大纲中的所有章节标题
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 检查是否是标题行
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # 检查是否是重复标题（在连续5行内出现相同内容的标题）
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # 跳过重复标题及其后的空行
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # 标题层级处理：
                # - # (level=1) 只保留报告主标题
                # - ## (level=2) 保留章节标题
                # - ### 及以下 (level>=3) 转换为粗体文本
                
                if level == 1:
                    if title == outline.title:
                        # 保留报告主标题
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # 章节标题错误使用了#，修正为##
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # 其他一级标题转为粗体
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # 保留章节标题
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # 非章节的二级标题转为粗体
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # ### 及以下级别的标题保留（允许子节结构）
                    processed_lines.append(line)
                    prev_was_heading = True
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # 跳过标题后紧跟的分隔线
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # 标题后只保留一个空行
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # 清理连续的多个空行（保留最多2个）
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """保存报告元信息和完整报告"""
        cls._ensure_report_folder(report.report_id)
        
        # 保存元信息JSON
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 保存大纲
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # 保存完整Markdown报告
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"报告已保存: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """获取报告"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # 兼容旧格式：检查直接存储在reports目录下的文件
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建Report对象
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', ''),
                    description=s.get('description', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # 如果markdown_content为空，尝试从full_report.md读取
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """根据模拟ID获取报告"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 新格式：文件夹
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # 兼容旧格式：JSON文件
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """列出报告"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # 新格式：文件夹
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # 兼容旧格式：JSON文件
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # 按创建时间倒序
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """删除报告（整个文件夹）"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # 新格式：删除整个文件夹
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"报告文件夹已删除: {report_id}")
            return True
        
        # 兼容旧格式：删除单独的文件
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
