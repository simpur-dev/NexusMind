"""
实体类型标注服务
图谱构建完成后，用 LLM 批量为未分类节点标注本体类型，
并将结果写入 Neo4j 节点属性 `entity_type`，实现一次标注、多次复用。
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.graphiti_client import run_async, get_neo4j_async_driver

logger = logging.getLogger(__name__)

# 单次 LLM 调用最多分类的实体数（避免 prompt 过长）
BATCH_SIZE = 20


def _build_ontology_description(ontology: Dict[str, Any]) -> Tuple[str, Dict[str, List[str]]]:
    """
    从本体定义构建：
    1. 供 LLM 阅读的类型描述文本
    2. 类型 -> 示例名称映射（用于精准匹配）
    
    Returns:
        (description_text, {type_name: [example_names]})
    """
    lines = []
    example_map: Dict[str, List[str]] = {}
    
    for et in ontology.get("entity_types", []):
        name = et["name"]
        desc = et.get("description", "")
        examples = et.get("examples", [])
        example_map[name] = [e.strip() for e in examples if e.strip()]
        
        ex_str = "、".join(examples[:5]) if examples else "无"
        lines.append(f"- **{name}**: {desc}（示例: {ex_str}）")
    
    return "\n".join(lines), example_map


def _build_description_keywords(ontology: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    从本体类型的中文描述中提取关键词，用于 summary 匹配兜底。
    例如 Student 的描述 "在校本科生或研究生" → ["在校", "本科生", "研究生", "学籍"]
    """
    try:
        import jieba
        has_jieba = True
    except ImportError:
        has_jieba = False
    
    keywords_map: Dict[str, List[str]] = {}
    # 手动定义的高质量关键词（补充 jieba 分词不足）
    manual_keywords = {
        "Student": ["学生", "在校", "本科", "研究生", "硕士", "博士", "学籍", "在读"],
        "Alumnus": ["校友", "毕业", "届"],
        "FacultyMember": ["教授", "副教授", "讲师", "导师", "教师", "博导", "教学科研", "教职"],
        "UniversityAdministrator": ["院长", "副院长", "书记", "副书记", "部长", "主任", "处长", "校长", "行政"],
        "Court": ["法院", "法庭", "审判"],
        "MediaOutlet": ["媒体", "新闻", "记者", "报社", "日报", "微博", "公众号", "澎湃", "央视"],
        "GovernmentAgency": ["教育厅", "教育局", "教育部", "省政府", "市政府", "委员会", "工作委员会", "政府"],
        "MedicalInstitution": ["医院", "医疗", "心理科", "皮肤科", "门诊", "诊所", "附属"],
        "Person": ["人", "个人"],
        "Organization": ["组织", "联盟", "协会", "基金会", "委员会", "小组", "志愿者"],
    }
    
    for et in ontology.get("entity_types", []):
        name = et["name"]
        desc = et.get("description", "")
        
        # 从描述中用 jieba 分词提取（可选）
        desc_keywords = set()
        if desc and has_jieba:
            words = jieba.lcut(desc)
            desc_keywords = {w for w in words if len(w) >= 2}
        
        # 合并手动关键词
        manual = set(manual_keywords.get(name, []))
        keywords_map[name] = list(desc_keywords | manual)
    
    return keywords_map


def match_by_examples(
    node_name: str,
    example_map: Dict[str, List[str]]
) -> Optional[str]:
    """
    用本体示例名精准匹配节点名。
    示例: ontology 定义 Student 的 examples = ["肖某瑫", "杨某媛"]
    → 节点名 "肖某瑫" 直接匹配到 Student
    """
    # 清理节点名中的括号后缀，如 "郭某飞（导师）" → "郭某飞"
    clean_name = re.sub(r'[（(].+?[）)]', '', node_name).strip()
    
    for type_name, examples in example_map.items():
        for ex in examples:
            clean_ex = re.sub(r'[（(].+?[）)]', '', ex).strip()
            if clean_name == clean_ex or node_name == ex:
                return type_name
            # 模糊：示例包含节点名 或 节点名包含示例
            if len(clean_name) >= 2 and (clean_name in clean_ex or clean_ex in clean_name):
                return type_name
    return None


def match_by_description_keywords(
    node_name: str,
    node_summary: str,
    keywords_map: Dict[str, List[str]]
) -> Optional[str]:
    """
    用本体描述关键词匹配节点的 name + summary。
    统计每个类型命中的关键词数量，取最高者。
    """
    text = f"{node_name} {node_summary}".lower()
    best_type = None
    best_score = 0
    
    for type_name, keywords in keywords_map.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_type = type_name
    
    # 至少命中 1 个关键词才算匹配
    return best_type if best_score >= 1 else None


def classify_with_llm(
    untyped_nodes: List[Dict[str, str]],
    ontology_desc: str,
    type_names: List[str],
    llm_client: Optional[LLMClient] = None
) -> Dict[str, str]:
    """
    用 LLM 批量分类未标注的节点。
    
    Args:
        untyped_nodes: [{"name": ..., "summary": ...}, ...]
        ontology_desc: 本体类型描述文本
        type_names: 合法类型名列表
        llm_client: LLM 客户端
        
    Returns:
        {node_name: type_name}
    """
    if not untyped_nodes:
        return {}
    
    client = llm_client or LLMClient()
    results: Dict[str, str] = {}
    
    # 分批处理
    for i in range(0, len(untyped_nodes), BATCH_SIZE):
        batch = untyped_nodes[i:i + BATCH_SIZE]
        
        entities_text = ""
        for idx, node in enumerate(batch, 1):
            summary_short = (node["summary"] or "")[:200]
            entities_text += f'{idx}. 名称: "{node["name"]}"  摘要: "{summary_short}"\n'
        
        valid_names_str = ', '.join(type_names)
        prompt = f"""你是知识图谱实体分类专家。请将以下实体分类到最合适的本体类型。

## 可用的实体类型（只能从以下类型中选择，禁止自创类型）
{ontology_desc}

## 合法类型名（必须严格使用以下之一）
{valid_names_str}

## 待分类的实体
{entities_text}

## 要求
1. 每个实体必须分配到上面「合法类型名」中的某一个，不得使用其他名称
2. 如果是人（个人、学生家属等），使用 Person
3. 如果是组织机构（法规、文件也归入此类），使用 Organization
4. 返回 JSON 格式: {{"entity_name": "TypeName", ...}}

请直接返回 JSON，不要解释。"""

        messages = [
            {"role": "system", "content": "你是一个精确的实体分类系统，只返回 JSON。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            resp = client.chat_json(messages=messages, temperature=0.1, max_tokens=2048)
            
            # 验证并收集结果
            for name, assigned_type in resp.items():
                if assigned_type in type_names:
                    results[name] = assigned_type
                else:
                    # 尝试模糊匹配类型名
                    matched = False
                    for tn in type_names:
                        if tn.lower() == assigned_type.lower():
                            results[name] = tn
                            matched = True
                            break
                    if not matched:
                        # 回退到通用类型而不是跳过
                        fallback = "Organization" if "Organization" in type_names else (
                            "Person" if "Person" in type_names else type_names[0]
                        )
                        results[name] = fallback
                        logger.warning(f"LLM 返回未知类型 '{assigned_type}' for '{name}'，回退到 '{fallback}'")
        except Exception as e:
            logger.error(f"LLM 分类批次 {i//BATCH_SIZE + 1} 失败: {e}")
    
    return results


def annotate_entity_types(
    graph_id: str,
    ontology: Dict[str, Any],
    use_llm: bool = True,
    progress_callback: Optional[callable] = None
) -> Dict[str, str]:
    """
    主入口：为图谱中所有未标注类型的节点标注本体类型。
    
    流程：
    1. 从 Neo4j 读取所有节点
    2. 用示例名精准匹配（零成本）
    3. 用描述关键词匹配（零成本）
    4. 对剩余节点用 LLM 分类（可选）
    5. 将所有结果写回 Neo4j 的 entity_type 属性
    
    Args:
        graph_id: 图谱 ID
        ontology: 项目本体定义（含 entity_types）
        use_llm: 是否使用 LLM 分类无法规则匹配的节点
        progress_callback: 进度回调 (message, progress_0_to_1)
        
    Returns:
        {node_name: assigned_type} 所有标注结果
    """
    entity_types = ontology.get("entity_types", [])
    if not entity_types:
        logger.warning("本体未定义 entity_types，跳过标注")
        return {}
    
    type_names = [et["name"] for et in entity_types]
    
    if progress_callback:
        progress_callback("读取图谱节点...", 0.0)
    
    # ---- 1. 读取所有节点 ----
    async def _fetch_nodes():
        driver = get_neo4j_async_driver()
        gid_filter = ("WHERE n.group_id = $gid OR $gid IN coalesce(n.group_ids, []) "
                      "OR n.group_id IS NULL") if graph_id else ""
        result = await driver.execute_query(
            f"MATCH (n:Entity) {gid_filter} "
            "RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary, "
            "n.entity_type AS entity_type",
            gid=graph_id,
            database_=Config.NEO4J_DATABASE,
        )
        return result.records
    
    records = run_async(_fetch_nodes())
    total = len(records)
    logger.info(f"[标注] 读取到 {total} 个节点")
    
    if total == 0:
        return {}
    
    # ---- 2. 构建匹配工具 ----
    ontology_desc, example_map = _build_ontology_description(ontology)
    
    # 构建关键词匹配工具（jieba 可选）
    try:
        keywords_map = _build_description_keywords(ontology)
    except Exception as e:
        logger.info(f"关键词提取降级（{e}），仅使用手动关键词")
        keywords_map = {}
    
    # ---- 3. 分层匹配 ----
    all_annotations: Dict[str, str] = {}  # uuid -> type
    name_to_type: Dict[str, str] = {}     # name -> type（用于日志）
    untyped_nodes: List[Dict[str, str]] = []
    
    already_typed = 0
    example_matched = 0
    keyword_matched = 0
    
    for rec in records:
        uuid = str(rec["uuid"] or "")
        name = rec["name"] or ""
        summary = rec["summary"] or ""
        stored_type = rec["entity_type"]
        
        # 已有存储类型且合法
        if stored_type and stored_type in type_names:
            all_annotations[uuid] = stored_type
            name_to_type[name] = stored_type
            already_typed += 1
            continue
        
        # 示例名精准匹配
        matched = match_by_examples(name, example_map)
        if matched:
            all_annotations[uuid] = matched
            name_to_type[name] = matched
            example_matched += 1
            continue
        
        # 描述关键词匹配
        if keywords_map:
            matched = match_by_description_keywords(name, summary, keywords_map)
            if matched:
                all_annotations[uuid] = matched
                name_to_type[name] = matched
                keyword_matched += 1
                continue
        
        # 未匹配
        untyped_nodes.append({"uuid": uuid, "name": name, "summary": summary})
    
    logger.info(
        f"[标注] 已标注={already_typed}, 示例匹配={example_matched}, "
        f"关键词匹配={keyword_matched}, 待LLM={len(untyped_nodes)}"
    )
    
    if progress_callback:
        progress_callback(
            f"规则匹配完成: {already_typed + example_matched + keyword_matched}/{total}，"
            f"剩余 {len(untyped_nodes)} 个待 LLM 分类",
            0.4
        )
    
    # ---- 4. LLM 分类 ----
    if use_llm and untyped_nodes:
        if progress_callback:
            progress_callback(f"LLM 分类 {len(untyped_nodes)} 个节点...", 0.5)
        
        llm_results = classify_with_llm(untyped_nodes, ontology_desc, type_names)
        
        llm_matched = 0
        for node in untyped_nodes:
            assigned = llm_results.get(node["name"])
            if assigned:
                all_annotations[node["uuid"]] = assigned
                name_to_type[node["name"]] = assigned
                llm_matched += 1
        
        logger.info(f"[标注] LLM 分类成功: {llm_matched}/{len(untyped_nodes)}")
        
        if progress_callback:
            progress_callback(f"LLM 分类完成: {llm_matched}/{len(untyped_nodes)}", 0.7)
    
    # ---- 5. 写回 Neo4j ----
    if all_annotations:
        if progress_callback:
            progress_callback("写入 Neo4j...", 0.8)
        
        async def _write_types():
            driver = get_neo4j_async_driver()
            # 批量更新：UNWIND 一次性写入所有标注
            annotations_list = [
                {"uuid": uid, "entity_type": etype}
                for uid, etype in all_annotations.items()
            ]
            await driver.execute_query(
                "UNWIND $annotations AS ann "
                "MATCH (n:Entity {uuid: ann.uuid}) "
                "SET n.entity_type = ann.entity_type",
                annotations=annotations_list,
                database_=Config.NEO4J_DATABASE,
            )
        
        run_async(_write_types())
        logger.info(f"[标注] 已写入 {len(all_annotations)} 个节点的 entity_type 到 Neo4j")
    
    if progress_callback:
        progress_callback(
            f"标注完成: 共 {len(all_annotations)}/{total} 个节点已标注类型",
            1.0
        )
    
    # 返回 name -> type 映射（方便调试和日志）
    return name_to_type
