"""
伪实体清洗器

在图谱实体进入模拟之前，过滤掉：
1. 抽象概念节点（"学术诚信"、"舆论"、"教育"等）
2. 本体定义节点（schema 中的类型名节点，如 "Student"、"University"）
3. 低质量节点（空名称、过短名称、无信息节点）

与 graph_builder.py 的 CHINESE_EXTRACTION_INSTRUCTIONS 黑名单对齐。
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 抽象概念黑名单（精确匹配，不区分大小写）
# 与 graph_builder.CHINESE_EXTRACTION_INSTRUCTIONS 的 ❌ 列表对齐
# ──────────────────────────────────────────────────────────────
ABSTRACT_CONCEPT_BLACKLIST: Set[str] = {
    # ── 教育/学术 ──
    "学术诚信", "学术", "诚信", "校园氛围", "校园", "教学", "教育",
    "招生", "海外留学", "留学", "课程", "考试", "学位", "论文",
    "科研", "学科", "专业", "培养", "教学质量", "学风",
    # ── 抽象主题/概念 ──
    "职业", "分歧", "行动呼吁", "多样性", "公平性", "包容性",
    "舆论", "情绪", "观点", "态度", "趋势", "价值观",
    "争议", "热点", "话题", "事件", "现象", "问题",
    "发展", "改革", "创新", "传统", "文化", "历史",
    "未来", "方向", "目标", "战略", "规划",
    # ── 制度/政策 ──
    "政策", "法规", "制度", "措施", "方案", "计划",
    "法律", "条例", "规定", "通知", "文件", "档案",
    # ── 情感/态度 ──
    "支持", "反对", "质疑", "批评", "赞扬", "愤怒",
    "焦虑", "恐慌", "期待", "失望", "信任", "怀疑",
    # ── 行为/过程 ──
    "调查", "研究", "分析", "讨论", "辩论", "投票",
    "抗议", "请愿", "举报", "维权", "申诉",
    # ── 英文抽象词 ──
    "education", "policy", "opinion", "sentiment", "controversy",
    "diversity", "equity", "inclusion", "trend", "topic",
    "integrity", "culture", "reform", "innovation", "development",
}

# 本体类型定义节点的 summary 特征（用于检测 schema 节点）
_SCHEMA_SUMMARY_PATTERNS = [
    "属性:",
    "attributes:",
    "实体类型",
    "entity type",
]


def is_pseudo_entity(
    node_name: str,
    node_labels: List[str],
    node_summary: str = "",
    ontology_type_names: Optional[Set[str]] = None,
) -> bool:
    """
    判断一个节点是否为伪实体（不应进入模拟）

    Args:
        node_name: 节点名称
        node_labels: 节点标签列表
        node_summary: 节点摘要
        ontology_type_names: 本体中定义的实体类型名集合（如 {"Student", "University"}）

    Returns:
        True 表示是伪实体，应被过滤
    """
    if not node_name or not node_name.strip():
        return True

    name = node_name.strip()

    # 规则 1：名称过短（单个汉字或单个英文字母）
    if len(name) <= 1:
        return True

    # 规则 2：精确匹配黑名单
    if name in ABSTRACT_CONCEPT_BLACKLIST or name.lower() in ABSTRACT_CONCEPT_BLACKLIST:
        logger.debug(f"伪实体(黑名单): '{name}'")
        return True

    # 规则 3：本体类型定义节点
    #   - 节点名精确匹配 ontology 的某个 type name
    #   - 且 summary 含有 schema 描述特征
    if ontology_type_names and name in ontology_type_names:
        summary_lower = (node_summary or "").lower()
        for pattern in _SCHEMA_SUMMARY_PATTERNS:
            if pattern.lower() in summary_lower:
                logger.debug(f"伪实体(本体定义节点): '{name}'")
                return True

    # 规则 4：只有默认标签且无有效摘要的节点
    custom_labels = [l for l in node_labels if l not in ("Entity", "Node")]
    if not custom_labels and not node_summary:
        logger.debug(f"伪实体(无类型无摘要): '{name}'")
        return True

    # 规则 5：名称全是标点符号或特殊字符
    if re.fullmatch(r'[\s\W_]+', name):
        logger.debug(f"伪实体(特殊字符): '{name}'")
        return True

    return False


def clean_entities(
    entities: List[Any],
    ontology: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    """
    批量清洗实体列表，移除伪实体。

    Args:
        entities: EntityNode 列表（需有 name, labels, summary 属性）
        ontology: 本体定义字典（可选，用于检测本体类型定义节点）

    Returns:
        清洗后的实体列表
    """
    # 提取 ontology 中的类型名
    ontology_type_names: Set[str] = set()
    if ontology:
        for et in ontology.get("entity_types", []):
            type_name = et.get("name", "")
            if type_name:
                ontology_type_names.add(type_name)

    before_count = len(entities)
    cleaned = []
    removed_names = []

    for entity in entities:
        name = getattr(entity, "name", "") or ""
        labels = getattr(entity, "labels", []) or []
        summary = getattr(entity, "summary", "") or ""

        if is_pseudo_entity(name, labels, summary, ontology_type_names):
            removed_names.append(name)
        else:
            cleaned.append(entity)

    removed_count = before_count - len(cleaned)
    if removed_count > 0:
        logger.info(
            f"伪实体清洗: {before_count} -> {len(cleaned)} "
            f"(移除 {removed_count} 个: {removed_names[:10]}"
            f"{'...' if len(removed_names) > 10 else ''})"
        )

    return cleaned


def clean_node_dicts(
    nodes: List[Dict[str, Any]],
    ontology: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    批量清洗节点字典列表（用于 graph_builder 等直接操作 dict 的场景）

    Args:
        nodes: 节点字典列表（需有 "name", "labels", "summary" 键）
        ontology: 本体定义字典

    Returns:
        清洗后的节点字典列表
    """
    ontology_type_names: Set[str] = set()
    if ontology:
        for et in ontology.get("entity_types", []):
            type_name = et.get("name", "")
            if type_name:
                ontology_type_names.add(type_name)

    before_count = len(nodes)
    cleaned = []

    for node in nodes:
        name = node.get("name", "") or ""
        labels = node.get("labels", []) or []
        summary = node.get("summary", "") or ""

        if not is_pseudo_entity(name, labels, summary, ontology_type_names):
            cleaned.append(node)

    removed_count = before_count - len(cleaned)
    if removed_count > 0:
        logger.info(f"伪实体清洗(dict): {before_count} -> {len(cleaned)} (移除 {removed_count} 个)")

    return cleaned
