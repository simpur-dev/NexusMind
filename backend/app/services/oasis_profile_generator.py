"""
OASIS Agent Profile生成器
将图谱中的实体转换为OASIS模拟平台所需的Agent Profile格式

优化改进：
1. 调用图谱检索功能二次丰富节点信息
2. 优化提示词生成非常详细的人设
3. 区分个人实体和抽象群体实体
"""

import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from ..utils.graphiti_client import get_graphiti, run_async
from .entity_reader import EntityNode, EntityReader

logger = get_logger('nexusmind.oasis_profile')


@dataclass
class OasisAgentProfile:
    """OASIS Agent Profile数据结构"""
    # 通用字段
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str
    
    # 可选字段 - Reddit风格
    karma: int = 1000
    
    # 可选字段 - Twitter风格
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    
    # 额外人设信息
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    
    # 认知字段（基于论文 §3.1 Profile + §3.3 Planning）
    # 内部目标：Agent 的行为驱动力
    internal_goals: List[str] = field(default_factory=list)
    # 效用权重：Agent 对不同维度的重视程度 [0,1]
    utility_weights: Dict[str, float] = field(default_factory=lambda: {
        "self_interest": 0.5,      # 自身利益
        "social_conformity": 0.3,  # 从众倾向
        "truth_seeking": 0.5,      # 求真倾向
        "emotional_expression": 0.5, # 情绪表达
    })
    # 初始立场倾向 [-1.0 强烈反对, 0 中立, 1.0 强烈支持]
    initial_stance: float = 0.0
    # 情绪倾向 [-1.0 极度悲观, 0 中性, 1.0 极度乐观]
    emotional_tendency: float = 0.0
    # 受影响敏感度 [0.0 不受影响, 1.0 极易受影响]
    susceptibility: float = 0.5
    
    # 分阶段记忆知识门控（Phased Knowledge Gating）
    # P2-P5 的事件记忆片段，在模拟运行时按阶段解锁注入
    # 格式: {"P2_media": "...", "P3_official": "...", "P4_secondary": "...", "P5_resolution": "..."}
    persona_memory_phases: Dict[str, str] = field(default_factory=dict)
    
    # 来源实体信息
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def to_reddit_format(self) -> Dict[str, Any]:
        """转换为Reddit平台格式"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS 库要求字段名为 username（无下划线）
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }
        
        # 添加额外人设信息（如果有）
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        if self.internal_goals:
            profile["internal_goals"] = self.internal_goals
        profile["utility_weights"] = self.utility_weights
        profile["initial_stance"] = self.initial_stance
        profile["emotional_tendency"] = self.emotional_tendency
        profile["susceptibility"] = self.susceptibility
        if self.persona_memory_phases:
            profile["persona_memory_phases"] = self.persona_memory_phases
        
        return profile
    
    def to_twitter_format(self) -> Dict[str, Any]:
        """转换为Twitter平台格式"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS 库要求字段名为 username（无下划线）
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }
        
        # 添加额外人设信息
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        if self.internal_goals:
            profile["internal_goals"] = self.internal_goals
        profile["utility_weights"] = self.utility_weights
        profile["initial_stance"] = self.initial_stance
        profile["emotional_tendency"] = self.emotional_tendency
        profile["susceptibility"] = self.susceptibility
        if self.persona_memory_phases:
            profile["persona_memory_phases"] = self.persona_memory_phases
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为完整字典格式"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "internal_goals": self.internal_goals,
            "utility_weights": self.utility_weights,
            "initial_stance": self.initial_stance,
            "emotional_tendency": self.emotional_tendency,
            "susceptibility": self.susceptibility,
            "persona_memory_phases": self.persona_memory_phases,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    OASIS Profile生成器
    
    将图谱中的实体转换为OASIS模拟所需的Agent Profile
    
    优化特性：
    1. 调用图谱检索功能获取更丰富的上下文
    2. 生成非常详细的人设（包括基本信息、职业经历、性格特征、社交媒体行为等）
    3. 区分个人实体和抽象群体实体
    """
    
    # MBTI类型列表
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]
    
    # 常见国家列表
    COUNTRIES = [
        "China", "US", "UK", "Japan", "Germany", "France", 
        "Canada", "Australia", "Brazil", "India", "South Korea"
    ]
    
    # 后续阶段关键词（P2-P5），用于 knowledge_level 过滤
    # 当 knowledge_level != "full" 时，包含这些词的 context 条目将被剔除
    LATE_STAGE_KEYWORDS = [
        "撤销处分", "二审", "判决", "复核", "百余处", "不规范",
        "问责", "整改", "通报", "PTSD", "胜诉", "驳回",
        "暂停招生", "书面检查", "制度反思", "维持原判",
        "调查结果", "官方声明", "官方回应", "司法进展",
    ]

    # 个人类型实体（需要生成具体人设）
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure", 
        "expert", "faculty", "official", "journalist", "activist"
    ]
    
    # 群体/机构类型实体（需要生成群体代表人设）
    GROUP_ENTITY_TYPES = [
        "university", "governmentagency", "organization", "ngo", 
        "mediaoutlet", "company", "institution", "group", "community"
    ]
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key_unused: Optional[str] = None,
        graph_id: Optional[str] = None,
        knowledge_level: str = "full"
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Graphiti 用于检索丰富上下文
        self.graph_id = graph_id
        
        # knowledge_level 控制信息泄漏等级
        # "full"      : 传统模式，context 不过滤（Tier A）
        # "p1_only"   : 过滤掉含 P2-P5 关键词的 context 条目（Tier B）
        # "identity"  : 只保留实体身份属性，零事件信息（Tier C）
        self.knowledge_level = knowledge_level
        
        # 熔断器：连续 N 次图谱检索失败后自动跳过，避免 Neo4j 不可用时阻塞整个后端
        self._graph_search_failures = 0
        self._graph_search_circuit_open = False
        self._GRAPH_FAILURE_THRESHOLD = 3
    
    def generate_profile_from_entity(
        self, 
        entity: EntityNode, 
        user_id: int,
        use_llm: bool = True
    ) -> OasisAgentProfile:
        """
        从图谱实体生成OASIS Agent Profile
        
        Args:
            entity: 实体节点
            user_id: 用户ID（用于OASIS）
            use_llm: 是否使用LLM生成详细人设
            
        Returns:
            OasisAgentProfile
        """
        entity_type = entity.get_entity_type() or "Entity"
        
        # 基础信息
        name = entity.name
        user_name = self._generate_username(name)
        
        # 构建上下文信息
        context = self._build_entity_context(entity)
        
        if use_llm:
            # 使用LLM生成详细人设
            profile_data = self._generate_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context
            )
        else:
            # 使用规则生成基础人设
            profile_data = self._generate_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes
            )
        
        # 后验校验：非 full 模式下自动剥离泄漏的后续阶段信息
        profile_data = self._validate_no_leakage(profile_data, name)
        
        # 解析认知字段（带容错）
        raw_weights = profile_data.get("utility_weights", {})
        default_weights = {"self_interest": 0.5, "social_conformity": 0.3, "truth_seeking": 0.5, "emotional_expression": 0.5}
        utility_weights = {}
        for k, dv in default_weights.items():
            try:
                v = float(raw_weights.get(k, dv))
                utility_weights[k] = max(0.0, min(1.0, v))
            except (TypeError, ValueError):
                utility_weights[k] = dv
        
        def _clamp(val, lo, hi, default):
            try:
                return max(lo, min(hi, float(val)))
            except (TypeError, ValueError):
                return default
        
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession") or self._derive_profession(entity_type),
            interested_topics=profile_data.get("interested_topics", []),
            internal_goals=profile_data.get("internal_goals", []),
            utility_weights=utility_weights,
            initial_stance=_clamp(profile_data.get("initial_stance", 0.0), -1.0, 1.0, 0.0),
            emotional_tendency=_clamp(profile_data.get("emotional_tendency", 0.0), -1.0, 1.0, 0.0),
            susceptibility=_clamp(profile_data.get("susceptibility", 0.5), 0.0, 1.0, 0.5),
            persona_memory_phases=profile_data.get("persona_memory_phases", {}),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )
    
    # 实体类型 → 职业/角色 映射
    ENTITY_TYPE_PROFESSION_MAP = {
        "Student": "学生",
        "Professor": "大学教授",
        "University": "高等院校",
        "GovernmentAgency": "政府机构",
        "MediaOutlet": "媒体机构",
        "Alumni": "校友",
        "Parent": "学生家长",
        "Ngo": "非政府组织",
        "Organization": "社会组织",
        "Person": "公民",
        "Company": "企业",
        "Celebrity": "公众人物",
        "Journalist": "记者",
        "Lawyer": "律师",
        "Doctor": "医生",
        "Official": "政府官员",
        "Executive": "企业高管",
        "School": "学校",
        "Hospital": "医疗机构",
        "EducationPractitioner": "教育工作者",
    }

    def _derive_profession(self, entity_type: str) -> str:
        """根据实体类型推导职业/角色描述"""
        return self.ENTITY_TYPE_PROFESSION_MAP.get(entity_type, entity_type)

    def _generate_username(self, name: str) -> str:
        """生成用户名"""
        # 移除特殊字符，转换为小写
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        # 添加随机后缀避免重复
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"
    
    def _search_graph_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        使用 Graphiti 图谱搜索功能获取实体相关的丰富信息
        
        Args:
            entity: 实体节点对象
            
        Returns:
            包含facts, node_summaries, context的字典
        """
        entity_name = entity.name
        
        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }
        
        if not self.graph_id:
            logger.debug(f"跳过图谱检索：未设置graph_id")
            return results
        
        # 熔断器：连续多次失败后跳过图谱检索，避免 Neo4j 不可用时反复超时
        if self._graph_search_circuit_open:
            return results
        
        comprehensive_query = f"关于{entity_name}的所有信息、活动、事件、关系和背景"
        
        try:
            graphiti = get_graphiti(self.graph_id)
            
            # 搜索边（事实/关系）
            edge_results = run_async(graphiti.search(comprehensive_query, num_results=30))
            
            all_facts = set()
            if edge_results:
                for edge in edge_results:
                    fact = getattr(edge, 'fact', '') or ""
                    if fact:
                        all_facts.add(fact)
            results["facts"] = list(all_facts)
            
            # 搜索节点
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
            node_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
            node_config.limit = 20
            
            try:
                node_results = run_async(graphiti._search(
                    query=comprehensive_query,
                    config=node_config,
                ))
                
                all_summaries = set()
                if hasattr(node_results, 'nodes') and node_results.nodes:
                    for node in node_results.nodes:
                        summary = getattr(node, 'summary', '') or ""
                        name = getattr(node, 'name', '') or ""
                        if summary:
                            all_summaries.add(summary)
                        if name and name != entity_name:
                            all_summaries.add(f"相关实体: {name}")
                results["node_summaries"] = list(all_summaries)
            except Exception as e:
                logger.debug(f"节点搜索失败: {e}")
            
            # 构建综合上下文
            context_parts = []
            if results["facts"]:
                context_parts.append("事实信息:\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("相关实体:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)
            
            logger.info(f"图谱检索完成: {entity_name}, 获取 {len(results['facts'])} 条事实, {len(results['node_summaries'])} 个相关节点")
            # 成功时重置失败计数
            self._graph_search_failures = 0
            
        except Exception as e:
            self._graph_search_failures += 1
            if self._graph_search_failures >= self._GRAPH_FAILURE_THRESHOLD:
                self._graph_search_circuit_open = True
                logger.warning(
                    f"图谱检索连续失败 {self._graph_search_failures} 次，熔断器开启，"
                    f"后续实体将跳过图谱检索（Neo4j 可能未运行）"
                )
            else:
                logger.warning(f"图谱检索失败 ({entity_name}): {e}")
        
        return results
    
    def _contains_late_stage_info(self, text: str) -> bool:
        """检查文本是否包含后续阶段（P2-P5）关键词"""
        if not text:
            return False
        return any(kw in text for kw in self.LATE_STAGE_KEYWORDS)

    def _filter_context_lines(self, section_text: str) -> str:
        """过滤掉包含后续阶段关键词的 context 行（用于 p1_only 模式）"""
        lines = section_text.split("\n")
        filtered = []
        for line in lines:
            if line.startswith("###"):
                filtered.append(line)
            elif not self._contains_late_stage_info(line):
                filtered.append(line)
        result = "\n".join(filtered)
        # 如果一个 section 只剩标题没内容，也去掉
        clean_lines = [l for l in result.split("\n") if l.strip()]
        if len(clean_lines) <= 1 and clean_lines and clean_lines[0].startswith("###"):
            return ""
        return result

    def _validate_no_leakage(self, profile_data: dict, entity_name: str) -> dict:
        """后验校验：检查生成的 persona/bio 是否泄漏后续阶段信息
        
        如果检测到泄漏，自动剥离含泄漏关键词的句子（而非重新生成，节省 API）
        """
        if self.knowledge_level == "full":
            return profile_data
        
        leaked_fields = {}
        for field_name in ["persona", "bio"]:
            text = profile_data.get(field_name, "")
            if not text:
                continue
            found_kw = [kw for kw in self.LATE_STAGE_KEYWORDS if kw in text]
            if found_kw:
                leaked_fields[field_name] = found_kw
        
        if not leaked_fields:
            return profile_data
        
        logger.warning(f"[Leakage] {entity_name}: 检测到信息泄漏 {leaked_fields}，正在自动剥离")
        
        for field_name in leaked_fields:
            text = profile_data[field_name]
            # 按句子拆分（中文句号、逗号断句太细，用句号/分号/感叹号/问号）
            import re
            sentences = re.split(r'(?<=[。！？；\n])', text)
            clean_sentences = []
            stripped_count = 0
            for s in sentences:
                if self._contains_late_stage_info(s):
                    stripped_count += 1
                else:
                    clean_sentences.append(s)
            
            profile_data[field_name] = "".join(clean_sentences)
            logger.info(f"[Leakage] {entity_name}.{field_name}: 剥离 {stripped_count} 句含后续信息的内容")
        
        return profile_data

    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        构建实体的完整上下文信息
        
        包括：
        1. 实体本身的边信息（事实）
        2. 关联节点的详细信息
        3. 图谱混合检索到的丰富信息
        
        受 self.knowledge_level 控制：
        - "full": 不过滤（Tier A）
        - "p1_only": 过滤掉含 P2-P5 关键词的条目（Tier B）
        - "identity": 只保留实体名称和类型，零事件信息（Tier C）
        """
        # Tier C: 只返回身份信息
        if self.knowledge_level == "identity":
            entity_type = entity.get_entity_type() or "Entity"
            return f"实体名称: {entity.name}\n实体类型: {entity_type}\n（盲测模式：不提供事件相关上下文）"

        is_filtered = (self.knowledge_level == "p1_only")
        filtered_count = 0  # 统计被过滤掉的条目数

        context_parts = []
        
        # 1. 添加实体属性信息
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    line = f"- {key}: {value}"
                    if is_filtered and self._contains_late_stage_info(str(value)):
                        filtered_count += 1
                        continue
                    attrs.append(line)
            if attrs:
                context_parts.append("### 实体属性\n" + "\n".join(attrs))
        
        # 2. 添加相关边信息（事实/关系）
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:  # 不限制数量
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")
                
                if fact:
                    if is_filtered and self._contains_late_stage_info(fact):
                        filtered_count += 1
                        continue
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (相关实体)")
                    else:
                        relationships.append(f"- (相关实体) --[{edge_name}]--> {entity.name}")
            
            if relationships:
                context_parts.append("### 相关事实和关系\n" + "\n".join(relationships))
        
        # 3. 添加关联节点的详细信息
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:  # 不限制数量
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")
                
                # p1_only: 跳过 summary 中含后续信息的节点
                if is_filtered and self._contains_late_stage_info(node_summary):
                    filtered_count += 1
                    continue
                
                # 过滤掉默认标签
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""
                
                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")
            
            if related_info:
                context_parts.append("### 关联实体信息\n" + "\n".join(related_info))
        
        # 4. 使用图谱检索获取更丰富的信息
        search_results = self._search_graph_for_entity(entity)
        
        if search_results.get("facts"):
            # 去重：排除已存在的事实
            new_facts = [f for f in search_results["facts"] if f not in existing_facts]
            if is_filtered:
                before = len(new_facts)
                new_facts = [f for f in new_facts if not self._contains_late_stage_info(f)]
                filtered_count += (before - len(new_facts))
            if new_facts:
                context_parts.append("### 图谱检索到的事实信息\n" + "\n".join(f"- {f}" for f in new_facts[:15]))
        
        if search_results.get("node_summaries"):
            summaries = search_results["node_summaries"]
            if is_filtered:
                before = len(summaries)
                summaries = [s for s in summaries if not self._contains_late_stage_info(s)]
                filtered_count += (before - len(summaries))
            if summaries:
                context_parts.append("### 图谱检索到的相关节点\n" + "\n".join(f"- {s}" for s in summaries[:10]))
        
        if is_filtered and filtered_count > 0:
            logger.info(f"[KnowledgeFilter] {entity.name}: p1_only 模式过滤掉 {filtered_count} 条含后续阶段信息的 context 条目")
        
        return "\n\n".join(context_parts)
    
    def _is_individual_entity(self, entity_type: str) -> bool:
        """判断是否是个人类型实体"""
        return entity_type.lower() in self.INDIVIDUAL_ENTITY_TYPES
    
    def _is_group_entity(self, entity_type: str) -> bool:
        """判断是否是群体/机构类型实体"""
        return entity_type.lower() in self.GROUP_ENTITY_TYPES
    
    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        """
        使用LLM生成非常详细的人设
        
        根据实体类型区分：
        - 个人实体：生成具体的人物设定
        - 群体/机构实体：生成代表性账号设定
        """
        
        is_individual = self._is_individual_entity(entity_type)
        
        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )

        # 尝试多次生成，直到成功或达到最大重试次数
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # 每次重试降低温度
                    # 不设置max_tokens，让LLM自由发挥
                )
                
                content = response.choices[0].message.content
                
                # 检查是否被截断（finish_reason不是'stop'）
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"LLM输出被截断 (attempt {attempt+1}), 尝试修复...")
                    content = self._fix_truncated_json(content)
                
                # 尝试解析JSON
                try:
                    result = json.loads(content)
                    
                    # 验证必需字段
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name}是一个{entity_type}。"
                    
                    return result
                    
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON解析失败 (attempt {attempt+1}): {str(je)[:80]}")
                    
                    # 尝试修复JSON
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result
                    
                    last_error = je
                    
            except Exception as e:
                logger.warning(f"LLM调用失败 (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(1 * (attempt + 1))  # 指数退避
        
        logger.warning(f"LLM生成人设失败（{max_attempts}次尝试）: {last_error}, 使用规则生成")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes
        )
    
    def _fix_truncated_json(self, content: str) -> str:
        """修复被截断的JSON（输出被max_tokens限制截断）"""
        import re
        
        # 如果JSON被截断，尝试闭合它
        content = content.strip()
        
        # 计算未闭合的括号
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # 检查是否有未闭合的字符串
        # 简单检查：如果最后一个引号后没有逗号或闭合括号，可能是字符串被截断
        if content and content[-1] not in '",}]':
            # 尝试闭合字符串
            content += '"'
        
        # 闭合括号
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """尝试修复损坏的JSON"""
        import re
        
        # 1. 首先尝试修复被截断的情况
        content = self._fix_truncated_json(content)
        
        # 2. 尝试提取JSON部分
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # 3. 处理字符串中的换行符问题
            # 找到所有字符串值并替换其中的换行符
            def fix_string_newlines(match):
                s = match.group(0)
                # 替换字符串内的实际换行符为空格
                s = s.replace('\n', ' ').replace('\r', ' ')
                # 替换多余空格
                s = re.sub(r'\s+', ' ', s)
                return s
            
            # 匹配JSON字符串值
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)
            
            # 4. 尝试解析
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                # 5. 如果还是失败，尝试更激进的修复
                try:
                    # 移除所有控制字符
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    # 替换所有连续空白
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except:
                    pass
        
        # 6. 尝试从内容中提取部分信息
        bio_match = re.search(r'"bio"\s*:\s*"([^"]*)"', content)
        persona_match = re.search(r'"persona"\s*:\s*"([^"]*)', content)  # 可能被截断
        
        bio = bio_match.group(1) if bio_match else (entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}")
        persona = persona_match.group(1) if persona_match else (entity_summary or f"{entity_name}是一个{entity_type}。")
        
        # 如果提取到了有意义的内容，标记为已修复
        if bio_match or persona_match:
            logger.info(f"从损坏的JSON中提取了部分信息")
            return {
                "bio": bio,
                "persona": persona,
                "_fixed": True
            }
        
        # 7. 完全失败，返回基础结构
        logger.warning(f"JSON修复失败，返回基础结构")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name}是一个{entity_type}。"
        }
    
    def _get_system_prompt(self, is_individual: bool) -> str:
        """获取系统提示词（根据 knowledge_level 调整约束强度）"""
        base_prompt = (
            "你是社交媒体用户画像生成专家。生成详细、真实的人设用于舆论模拟,最大程度还原已有现实情况。"
            "必须返回有效的JSON格式，所有字符串值不能包含未转义的换行符。使用中文。"
        )
        
        if self.knowledge_level == "full":
            # Tier A: 传统模式，允许完整信息
            base_prompt += (
                "\n\n【关键约束 - 分阶段知识门控】persona字段中的'个人记忆/机构记忆'部分，"
                "只能包含事件最初曝光/爆发期的信息（事件起因、初始爆料、初始反应）。"
                "后续阶段的信息（媒体跟进、官方通报、法院判决、公众质疑、最终定性等）"
                "必须放入 persona_memory_phases 的对应阶段字段中，不能提前写入 persona。"
            )
        elif self.knowledge_level == "p1_only":
            # Tier B: 严格 P1-only 门控
            base_prompt += (
                "\n\n【严格约束 - P1-only 知识门控（Tier B 评测模式）】"
                "\n⚠️ 这是一个信息控制实验。你所看到的上下文已经过过滤，只包含事件初始阶段的信息。"
                "\n\n绝对禁止在 persona 和 bio 中出现以下任何后续阶段信息："
                "\n- 官方通报、调查结果、复核结论"
                "\n- 法院判决、二审结果、诉讼驳回"
                "\n- 处分撤销、问责处分、整改措施"
                "\n- PTSD诊断、制度反思、暂停招生"
                "\n- 任何「已知结果」类表述"
                "\n\n如果上下文中仍残留后续信息（过滤可能不完美），你必须主动忽略它。"
                "\npersona 只能描述：该人物的身份、性格、初始立场、事件起因的初始认知。"
                "\nbio 只能描述：该人物的身份标签，不能包含任何事件进展或结果。"
                "\npersona_memory_phases 中的 P2-P5 记忆仍需正常生成（从你的世界知识中推断合理内容）。"
            )
        else:
            # Tier C: 盲测模式，零事件信息
            base_prompt += (
                "\n\n【盲测模式 - Tier C】"
                "\n你只会收到实体的身份信息（名称、类型），没有任何事件相关上下文。"
                "\n请根据实体类型生成合理的通用人设（性格、职业背景、社交媒体行为特征）。"
                "\npersona 和 bio 中不能出现任何具体事件信息。"
                "\npersona_memory_phases 留空。"
            )
        
        return base_prompt
    
    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """构建个人实体的详细人设提示词（分阶段知识门控版）
        
        核心改进（Phased Knowledge Gating）：
        - persona 字段仅包含 P1 阶段知识（事件曝光/爆发期）
        - persona_memory_phases 字段包含 P2-P5 阶段的记忆片段
        - 模拟运行时按阶段解锁记忆，避免 Agent 一开始就知道全部信息
        
        论文依据：
        - Generative Agents: 信息通过时间释放自然传播
        - SocioVerse §2.1: Agent 感知受限于当前环境状态
        """
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "无"
        context_str = context[:3000] if context else "无额外上下文"
        
        return f"""为实体生成详细的社交媒体用户人设,最大程度还原已有现实情况。

实体名称: {entity_name}
实体类型: {entity_type}
实体摘要: {entity_summary}
实体属性: {attrs_str}

上下文信息:
{context_str}

请生成JSON，包含以下字段:

1. bio: 社交媒体简介，200字（**重要：bio 只能包含人物身份标签和基本特征，禁止包含事件进展、调查结果、判决等后续信息**）
2. persona: 详细人设描述（2000字的纯文本），需包含:
   - 基本信息（年龄、职业、教育背景、所在地）
   - 人物背景（重要经历、与事件的关联、社会关系）
   - 性格特征（MBTI类型、核心性格、情绪表达方式）
   - 社交媒体行为（发帖频率、内容偏好、互动风格、语言特点）
   - 立场观点（对话题的态度、可能被激怒/感动的内容）
   - 独特特征（口头禅、特殊经历、个人爱好）
   - 个人记忆（**极其重要的限制**：只能包含事件最初曝光/爆发阶段的信息！
     即：事件起因、初始爆料、当事人最初反应。
     **禁止包含**：后续媒体跟进报道、官方通报结果、法院判决、公众二次质疑、
     事件最终定性等后续发展信息。这些将在后续阶段逐步释放。）
3. age: 年龄数字（必须是整数）
4. gender: 性别，必须是英文: "male" 或 "female"
5. mbti: MBTI类型（如INTJ、ENFP等）
6. country: 国家（使用中文，如"中国"）
7. profession: 职业
8. interested_topics: 感兴趣话题数组
9. internal_goals: 内部目标数组（2-4个简短目标，如"保护同学权益"、"维护学校声誉"、"获取关注度"等）
10. utility_weights: 效用权重对象，包含四个数值字段(0.0-1.0):
    - self_interest: 自身利益重视程度
    - social_conformity: 从众倾向
    - truth_seeking: 求真倾向
    - emotional_expression: 情绪表达倾向
11. initial_stance: 对核心话题的立场（-1.0强烈反对到1.0强烈支持，0为中立）
12. emotional_tendency: 情绪基调（-1.0极度悲观到1.0极度乐观，0为中性）
13. susceptibility: 受外界影响的敏感度（0.0不受影响到1.0极易受影响）
14. persona_memory_phases: 分阶段记忆知识（**非常重要**），是一个对象，包含以下4个阶段的事件记忆片段:
    - P2_media: 第2阶段（扩散期）解锁的记忆，内容关于：媒体开始关注报道、舆论开始扩散、该人物可能接收到的外界反馈。以第二人称"你"的视角撰写，100-200字。
    - P3_official: 第3阶段（官方回应期）解锁的记忆，内容关于：官方声明、调查结果、司法进展、该人物对官方回应的反应。以第二人称撰写，100-200字。
    - P4_secondary: 第4阶段（二次传播期）解锁的记忆，内容关于：公众质疑、深度追问、二次争议、该人物的立场变化。以第二人称撰写，100-200字。
    - P5_resolution: 第5阶段（收敛期）解锁的记忆，内容关于：后续发展、制度反思、最终定性、该人物的最终态度。以第二人称撰写，100-200字。

重要:
- 所有字段值必须是字符串或数字，不要使用换行符
- persona必须是一段连贯的文字描述，**只能包含事件初始阶段的信息**
- persona_memory_phases中的每个值都是一段文字，以"你"开头，描述该阶段解锁的新信息
- 使用中文（除了gender字段必须用英文male/female）
- 内容要与实体信息保持一致
- age必须是有效的整数，gender必须是"male"或"female"
- internal_goals必须是字符串数组
- utility_weights中每个值必须是0.0到1.0的浮点数
- initial_stance和emotional_tendency必须是-1.0到1.0的浮点数
- susceptibility必须是0.0到1.0的浮点数
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """构建群体/机构实体的详细人设提示词（分阶段知识门控版）"""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "无"
        context_str = context[:3000] if context else "无额外上下文"
        
        return f"""为机构/群体实体生成详细的社交媒体账号设定,最大程度还原已有现实情况。

实体名称: {entity_name}
实体类型: {entity_type}
实体摘要: {entity_summary}
实体属性: {attrs_str}

上下文信息:
{context_str}

请生成JSON，包含以下字段:

1. bio: 官方账号简介，200字，专业得体（**重要：bio 只能包含机构身份和职能描述，禁止包含事件进展、调查结果、处分决定等后续信息**）
2. persona: 详细账号设定描述（2000字的纯文本），需包含:
   - 机构基本信息（正式名称、机构性质、成立背景、主要职能）
   - 账号定位（账号类型、目标受众、核心功能）
   - 发言风格（语言特点、常用表达、禁忌话题）
   - 发布内容特点（内容类型、发布频率、活跃时间段）
   - 立场态度（对核心话题的官方立场、面对争议的处理方式）
   - 特殊说明（代表的群体画像、运营习惯）
   - 机构记忆（**极其重要的限制**：只能包含事件最初曝光/爆发阶段的信息！
     即：事件起因、初始争议、机构的初始公开立场。
     **禁止包含**：后续官方通报结果、司法判决、制度改革等后续发展。）
3. age: 固定填30（机构账号的虚拟年龄）
4. gender: 固定填"other"（机构账号使用other表示非个人）
5. mbti: MBTI类型，用于描述账号风格，如ISTJ代表严谨保守
6. country: 国家（使用中文，如"中国"）
7. profession: 机构职能描述
8. interested_topics: 关注领域数组
9. internal_goals: 机构目标数组（2-4个，如"维护机构形象"、"引导舆论"、"信息透明化"等）
10. utility_weights: {{"self_interest": 0.3, "social_conformity": 0.2, "truth_seeking": 0.7, "emotional_expression": 0.2}}（机构通常理性、重视真实性）
11. initial_stance: 对核心话题的官方立场（-1.0到1.0）
12. emotional_tendency: 情绪基调（机构通常偏中性，接近0.0）
13. susceptibility: 受外界影响敏感度（机构通常偏低，0.1-0.3）
14. persona_memory_phases: 分阶段记忆知识（**非常重要**），是一个对象，包含以下4个阶段的机构动态记忆:
    - P2_media: 第2阶段（扩散期）解锁的记忆：媒体报道扩散后，该机构面临的舆论压力、接到的问询等。以"你们机构"视角撰写，100-200字。
    - P3_official: 第3阶段（官方回应期）解锁的记忆：该机构发布的官方声明、调查结果、配合的司法进展。100-200字。
    - P4_secondary: 第4阶段（二次传播期）解锁的记忆：公众质疑后的二次回应、补充说明、舆情应对。100-200字。
    - P5_resolution: 第5阶段（收敛期）解锁的记忆：制度整改、后续跟进、事件收尾。100-200字。

重要:
- 所有字段值必须是字符串或数字，不允许null值
- persona必须是一段连贯的文字描述，不要使用换行符，**只能包含事件初始阶段信息**
- persona_memory_phases中的每个值都是一段文字，描述该阶段解锁的机构新动态
- 使用中文（除了gender字段必须用英文"other"）
- age必须是整数30，gender必须是字符串"other"
- 机构账号发言要符合其身份定位

重要（数值格式要求）:
- internal_goals必须是字符串数组
- utility_weights中每个值必须是0.0到1.0的浮点数
- initial_stance和emotional_tendency必须是-1.0到1.0的浮点数
- susceptibility必须是0.0到1.0的浮点数"""
    
    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用规则生成基础人设"""
        
        # 根据实体类型生成不同的人设
        entity_type_lower = entity_type.lower()
        
        if entity_type_lower in ["student", "alumni"]:
            return {
                "bio": f"{entity_type} with interests in academics and social issues.",
                "persona": f"{entity_name} is a {entity_type.lower()} who is actively engaged in academic and social discussions. They enjoy sharing perspectives and connecting with peers.",
                "age": random.randint(18, 30),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": "Student",
                "interested_topics": ["Education", "Social Issues", "Technology"],
                "internal_goals": ["保护同学权益", "话题参与与表达"],
                "utility_weights": {"self_interest": 0.5, "social_conformity": round(random.uniform(0.3, 0.7), 2), "truth_seeking": round(random.uniform(0.3, 0.6), 2), "emotional_expression": round(random.uniform(0.4, 0.8), 2)},
                "initial_stance": round(random.uniform(-0.5, 0.5), 2),
                "emotional_tendency": round(random.uniform(-0.3, 0.3), 2),
                "susceptibility": round(random.uniform(0.4, 0.8), 2),
            }
        
        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return {
                "bio": f"Expert and thought leader in their field.",
                "persona": f"{entity_name} is a recognized {entity_type.lower()} who shares insights and opinions on important matters. They are known for their expertise and influence in public discourse.",
                "age": random.randint(35, 60),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(["ENTJ", "INTJ", "ENTP", "INTP"]),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_attributes.get("occupation", "Expert"),
                "interested_topics": ["Politics", "Economics", "Culture & Society"],
                "internal_goals": ["传播专业见解", "影响公共议题"],
                "utility_weights": {"self_interest": 0.4, "social_conformity": 0.2, "truth_seeking": 0.8, "emotional_expression": 0.3},
                "initial_stance": round(random.uniform(-0.3, 0.3), 2),
                "emotional_tendency": round(random.uniform(-0.1, 0.2), 2),
                "susceptibility": round(random.uniform(0.1, 0.3), 2),
            }
        
        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return {
                "bio": f"Official account for {entity_name}. News and updates.",
                "persona": f"{entity_name} is a media entity that reports news and facilitates public discourse. The account shares timely updates and engages with the audience on current events.",
                "age": 30,  # 机构虚拟年龄
                "gender": "other",  # 机构使用other
                "mbti": "ISTJ",  # 机构风格：严谨保守
                "country": "中国",
                "profession": "Media",
                "interested_topics": ["General News", "Current Events", "Public Affairs"],
                "internal_goals": ["客观报道事实", "吸引受众关注"],
                "utility_weights": {"self_interest": 0.3, "social_conformity": 0.2, "truth_seeking": 0.7, "emotional_expression": 0.2},
                "initial_stance": 0.0,
                "emotional_tendency": 0.0,
                "susceptibility": 0.15,
            }
        
        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return {
                "bio": f"Official account of {entity_name}.",
                "persona": f"{entity_name} is an institutional entity that communicates official positions, announcements, and engages with stakeholders on relevant matters.",
                "age": 30,  # 机构虚拟年龄
                "gender": "other",  # 机构使用other
                "mbti": "ISTJ",  # 机构风格：严谨保守
                "country": "中国",
                "profession": entity_type,
                "interested_topics": ["Public Policy", "Community", "Official Announcements"],
                "internal_goals": ["维护机构形象", "信息透明化"],
                "utility_weights": {"self_interest": 0.4, "social_conformity": 0.2, "truth_seeking": 0.6, "emotional_expression": 0.1},
                "initial_stance": 0.3,
                "emotional_tendency": 0.1,
                "susceptibility": 0.1,
            }
        
        else:
            # 默认人设
            return {
                "bio": entity_summary[:150] if entity_summary else f"{entity_type}: {entity_name}",
                "persona": entity_summary or f"{entity_name} is a {entity_type.lower()} participating in social discussions.",
                "age": random.randint(25, 50),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_type,
                "interested_topics": ["General", "Social Issues"],
                "internal_goals": ["参与讨论", "表达观点"],
                "utility_weights": {"self_interest": 0.5, "social_conformity": round(random.uniform(0.2, 0.6), 2), "truth_seeking": round(random.uniform(0.3, 0.7), 2), "emotional_expression": round(random.uniform(0.3, 0.7), 2)},
                "initial_stance": round(random.uniform(-0.5, 0.5), 2),
                "emotional_tendency": round(random.uniform(-0.3, 0.3), 2),
                "susceptibility": round(random.uniform(0.3, 0.7), 2),
            }
    
    def set_graph_id(self, graph_id: str):
        """设置图谱ID用于图谱检索"""
        self.graph_id = graph_id
    
    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit",
        existing_profiles: Optional[List] = None
    ) -> List[OasisAgentProfile]:
        """
        批量从实体生成Agent Profile（支持并行生成）
        
        Args:
            entities: 实体列表
            use_llm: 是否使用LLM生成详细人设
            progress_callback: 进度回调函数 (current, total, message)
            graph_id: 图谱ID，用于图谱检索获取更丰富上下文
            parallel_count: 并行生成数量，默认5
            realtime_output_path: 实时写入的文件路径（如果提供，每生成一个就写入一次）
            output_platform: 输出平台格式 ("reddit" 或 "twitter")
            existing_profiles: 已有的 profiles 列表（用于续生成时跳过已有实体）
            
        Returns:
            Agent Profile列表
        """
        import concurrent.futures
        from threading import Lock
        
        # 设置graph_id用于图谱检索
        if graph_id:
            self.graph_id = graph_id
        
        # 构建已有 profiles 的名称集合，用于跳过已生成的实体
        existing_names = set()
        existing_map = {}  # name -> profile data
        if existing_profiles:
            for ep in existing_profiles:
                name = ep.get('name') or ep.get('user_name') or ''
                if name:
                    existing_names.add(name.lower())
                    existing_map[name.lower()] = ep
            logger.info(f"续生成模式：已有 {len(existing_names)} 个 profiles，将跳过对应实体")
        
        total = len(entities)
        profiles = [None] * total  # 预分配列表保持顺序
        completed_count = [0]  # 使用列表以便在闭包中修改
        skipped_count = 0  # 续生成时跳过的实体数
        lock = Lock()
        
        # 保留旧 profiles 的原始数据（dict 格式），用于写文件时合并
        preserved_profiles_data = list(existing_profiles) if existing_profiles else []
        # 已保留的 profile 名称集合（用于去重合并）
        preserved_names = set(n for n in existing_names)  # copy
        
        # 实时写入文件的辅助函数
        def save_profiles_realtime():
            """实时保存已生成的 profiles 到文件（合并旧 profiles + 新 profiles）"""
            if not realtime_output_path:
                return
            
            with lock:
                # 过滤出本次新生成的 profiles
                new_profiles = [p for p in profiles if p is not None]
                if not new_profiles and not preserved_profiles_data:
                    return
                
                try:
                    if output_platform == "reddit":
                        # 合并：旧 profiles（dict）+ 新 profiles（转 dict）
                        new_data = [p.to_reddit_format() for p in new_profiles]
                        # 去重：如果新生成的 profile 名字与旧的重复，用新的替换旧的
                        new_names = set()
                        for p in new_data:
                            name = (p.get('name') or '').lower()
                            if name:
                                new_names.add(name)
                        merged = [p for p in preserved_profiles_data
                                  if (p.get('name') or '').lower() not in new_names]
                        merged.extend(new_data)
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(merged, f, ensure_ascii=False, indent=2)
                    else:
                        # Twitter CSV 格式
                        import csv
                        new_data = [p.to_twitter_format() for p in new_profiles]
                        merged = list(preserved_profiles_data) + new_data
                        if merged:
                            fieldnames = list(merged[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(merged)
                except Exception as e:
                    logger.warning(f"实时保存 profiles 失败: {e}")
        
        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """生成单个profile的工作函数"""
            entity_type = entity.get_entity_type() or "Entity"
            
            # 续生成：跳过已有 profile 的实体
            if entity.name and entity.name.lower() in existing_names:
                return idx, None, "skipped"
            
            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm
                )
                
                # 实时输出生成的人设到控制台和日志
                self._print_generated_profile(entity.name, entity_type, profile)
                
                return idx, profile, None
                
            except Exception as e:
                logger.error(f"生成实体 {entity.name} 的人设失败: {str(e)}")
                # 创建一个基础profile
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=entity.summary or f"A participant in social discussions.",
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)
        
        logger.info(f"开始并行生成 {total} 个Agent人设（并行数: {parallel_count}）...")
        print(f"\n{'='*60}")
        print(f"开始生成Agent人设 - 共 {total} 个实体，并行数: {parallel_count}")
        print(f"{'='*60}\n")
        
        # 使用线程池并行执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # 提交所有任务
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"
                
                try:
                    result_idx, profile, error = future.result()
                    
                    # 跳过已有 profile 的实体
                    if error == "skipped":
                        with lock:
                            completed_count[0] += 1
                        continue
                    
                    profiles[result_idx] = profile
                    
                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]
                    
                    # 实时写入文件（合并旧 + 新）
                    save_profiles_realtime()
                    
                    if progress_callback:
                        generated = len([p for p in profiles if p is not None])
                        total_with_existing = generated + len(preserved_profiles_data)
                        progress_callback(
                            total_with_existing, 
                            total, 
                            f"已完成 {total_with_existing}/{total}: {entity.name}（{entity_type}）"
                        )
                    
                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} 使用备用人设: {error}")
                    else:
                        generated = len([p for p in profiles if p is not None])
                        total_with_existing = generated + len(preserved_profiles_data)
                        logger.info(f"[{total_with_existing}/{total}] 成功生成人设: {entity.name} ({entity_type})")
                        
                except Exception as e:
                    logger.error(f"处理实体 {entity.name} 时发生异常: {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in social discussions.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    # 实时写入文件（即使是备用人设）
                    save_profiles_realtime()
        
        print(f"\n{'='*60}")
        print(f"人设生成完成！共生成 {len([p for p in profiles if p])} 个Agent")
        print(f"{'='*60}\n")
        
        return profiles
    
    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """实时输出生成的人设到控制台（完整内容，不截断）"""
        separator = "-" * 70
        
        # 构建完整输出内容（不截断）
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else '无'
        
        output_lines = [
            f"\n{separator}",
            f"[已生成] {entity_name} ({entity_type})",
            f"{separator}",
            f"用户名: {profile.user_name}",
            f"",
            f"【简介】",
            f"{profile.bio}",
            f"",
            f"【详细人设】",
            f"{profile.persona}",
            f"",
            f"【基本属性】",
            f"年龄: {profile.age} | 性别: {profile.gender} | MBTI: {profile.mbti}",
            f"职业: {profile.profession} | 国家: {profile.country}",
            f"兴趣话题: {topics_str}",
            separator
        ]
        
        output = "\n".join(output_lines)
        
        # 只输出到控制台（避免重复，logger不再输出完整内容）
        print(output)
    
    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        保存Profile到文件（根据平台选择正确格式）
        
        OASIS平台格式要求：
        - Twitter: CSV格式
        - Reddit: JSON格式
        
        Args:
            profiles: Profile列表
            file_path: 文件路径
            platform: 平台类型 ("reddit" 或 "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)
        
        # 保存分阶段记忆知识到独立文件（Phased Knowledge Gating）
        self._save_persona_phases(profiles, file_path)
    
    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        保存Twitter Profile为CSV格式（符合OASIS官方要求）
        
        OASIS Twitter要求的CSV字段：
        - user_id: 用户ID（根据CSV顺序从0开始）
        - name: 用户真实姓名
        - username: 系统中的用户名
        - user_char: 详细人设描述（注入到LLM系统提示中，指导Agent行为）
        - description: 简短的公开简介（显示在用户资料页面）
        
        user_char vs description 区别：
        - user_char: 内部使用，LLM系统提示，决定Agent如何思考和行动
        - description: 外部显示，其他用户可见的简介
        """
        import csv
        
        # 确保文件扩展名是.csv
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入OASIS要求的表头
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)
            
            # 写入数据行
            for idx, profile in enumerate(profiles):
                # user_char: 完整人设（bio + persona），用于LLM系统提示
                user_char = profile.bio
                if profile.persona and profile.persona != profile.bio:
                    user_char = f"{profile.bio} {profile.persona}"
                # 处理换行符（CSV中用空格替代）
                user_char = user_char.replace('\n', ' ').replace('\r', ' ')
                
                # description: 简短简介，用于外部显示
                description = profile.bio.replace('\n', ' ').replace('\r', ' ')
                
                row = [
                    idx,                    # user_id: 从0开始的顺序ID
                    profile.name,           # name: 真实姓名
                    profile.user_name,      # username: 用户名
                    user_char,              # user_char: 完整人设（内部LLM使用）
                    description             # description: 简短简介（外部显示）
                ]
                writer.writerow(row)
        
        logger.info(f"已保存 {len(profiles)} 个Twitter Profile到 {file_path} (OASIS CSV格式)")
    
    def _save_persona_phases(self, profiles: List[OasisAgentProfile], file_path: str):
        """保存分阶段记忆知识到独立 JSON 文件（Phased Knowledge Gating）
        
        生成 persona_phases.json，格式:
        {
            "0": {"P2_media": "...", "P3_official": "...", ...},
            "1": {"P2_media": "...", ...},
            ...
        }
        
        此文件与平台无关，Twitter/Reddit 模拟均可读取。
        """
        phases_data = {}
        for idx, profile in enumerate(profiles):
            if profile.persona_memory_phases:
                phases_data[str(profile.user_id)] = profile.persona_memory_phases
        
        if not phases_data:
            logger.info("无分阶段记忆知识，跳过 persona_phases.json")
            return
        
        phases_path = os.path.join(os.path.dirname(file_path), "persona_phases.json")
        with open(phases_path, 'w', encoding='utf-8') as f:
            json.dump(phases_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存 {len(phases_data)} 个 Agent 的分阶段记忆知识到 {phases_path}")
    
    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        标准化gender字段为OASIS要求的英文格式
        
        OASIS要求: male, female, other
        """
        if not gender:
            return "other"
        
        gender_lower = gender.lower().strip()
        
        # 中文映射
        gender_map = {
            "男": "male",
            "女": "female",
            "机构": "other",
            "其他": "other",
            # 英文已有
            "male": "male",
            "female": "female",
            "other": "other",
        }
        
        return gender_map.get(gender_lower, "other")
    
    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        保存Reddit Profile为JSON格式
        
        使用与 to_reddit_format() 一致的格式，确保 OASIS 能正确读取。
        必须包含 user_id 字段，这是 OASIS agent_graph.get_agent() 匹配的关键！
        
        必需字段：
        - user_id: 用户ID（整数，用于匹配 initial_posts 中的 poster_agent_id）
        - username: 用户名
        - name: 显示名称
        - bio: 简介
        - persona: 详细人设
        - age: 年龄（整数）
        - gender: "male", "female", 或 "other"
        - mbti: MBTI类型
        - country: 国家
        """
        data = []
        for idx, profile in enumerate(profiles):
            # 使用与 to_reddit_format() 一致的格式
            item = {
                "user_id": profile.user_id if profile.user_id is not None else idx,  # 关键：必须包含 user_id
                "username": profile.user_name,
                "name": profile.name,
                "bio": profile.bio[:150] if profile.bio else f"{profile.name}",
                "persona": profile.persona or f"{profile.name} is a participant in social discussions.",
                "karma": profile.karma if profile.karma else 1000,
                "created_at": profile.created_at,
                # OASIS必需字段 - 确保都有默认值
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": profile.country if profile.country else "中国",
            }
            
            # 可选字段
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics
            
            data.append(item)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存 {len(profiles)} 个Reddit Profile到 {file_path} (JSON格式，包含user_id字段)")
    
    # 保留旧方法名作为别名，保持向后兼容
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[已废弃] 请使用 save_profiles() 方法"""
        logger.warning("save_profiles_to_json已废弃，请使用save_profiles方法")
        self.save_profiles(profiles, file_path, platform)

