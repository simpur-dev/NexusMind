"""
模拟配置智能生成器
使用LLM根据模拟需求、文档内容、图谱信息自动生成细致的模拟参数
实现全程自动化，无需人工设置参数

采用分步生成策略，避免一次性生成过长内容导致失败：
1. 生成时间配置
2. 生成事件配置
3. 分批生成Agent配置
4. 生成平台配置
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from .entity_reader import EntityNode, EntityReader
from .agent_brain import create_agent_brain_profile

logger = get_logger('nexusmind.simulation_config')

# 中国作息时间配置（北京时间）
CHINA_TIMEZONE_CONFIG = {
    # 深夜时段（几乎无人活动）
    "dead_hours": [0, 1, 2, 3, 4, 5],
    # 早间时段（逐渐醒来）
    "morning_hours": [6, 7, 8],
    # 工作时段
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    # 晚间高峰（最活跃）
    "peak_hours": [19, 20, 21, 22],
    # 夜间时段（活跃度下降）
    "night_hours": [23],
    # 活跃度系数
    "activity_multipliers": {
        "dead": 0.05,      # 凌晨几乎无人
        "morning": 0.4,    # 早间逐渐活跃
        "work": 0.7,       # 工作时段中等
        "peak": 1.5,       # 晚间高峰
        "night": 0.5       # 深夜下降
    }
}


@dataclass
class AgentActivityConfig:
    """单个Agent的活动配置"""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    
    # 活跃度配置 (0.0-1.0)
    activity_level: float = 0.5  # 整体活跃度
    
    # 发言频率（每小时预期发言次数）
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    
    # 活跃时间段（24小时制，0-23）
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    
    # 响应速度（对热点事件的反应延迟，单位：模拟分钟）
    response_delay_min: int = 5
    response_delay_max: int = 60
    
    # 情感倾向 (-1.0到1.0，负面到正面)
    sentiment_bias: float = 0.0
    
    # 立场（对特定话题的态度）
    stance: str = "neutral"  # supportive, opposing, neutral, observer
    
    # 影响力权重（决定其发言被其他Agent看到的概率）
    influence_weight: float = 1.0
    
    # Agent Brain 认知层配置（由 agent_brain 模块自动生成）
    brain_profile: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class TimeSimulationConfig:
    """时间模拟配置（基于中国人作息习惯）"""
    # 模拟总时长（模拟小时数）
    total_simulation_hours: int = 72  # 默认模拟72小时（3天）
    
    # 每轮代表的时间（模拟分钟）- 默认60分钟（1小时），加快时间流速
    minutes_per_round: int = 60
    
    # 每小时激活的Agent数量范围
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20
    
    # 高峰时段（晚间19-22点，中国人最活跃的时间）
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5
    
    # 低谷时段（凌晨0-5点，几乎无人活动）
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05  # 凌晨活跃度极低
    
    # 早间时段
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4
    
    # 工作时段
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """事件配置"""
    # 初始事件（模拟开始时的触发事件）
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    
    # 定时事件（在特定时间触发的事件）
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # 热点话题关键词
    hot_topics: List[str] = field(default_factory=list)
    
    # 舆论引导方向
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """平台特定配置"""
    platform: str  # twitter or reddit
    
    # 推荐算法权重
    recency_weight: float = 0.4  # 时间新鲜度
    popularity_weight: float = 0.3  # 热度
    relevance_weight: float = 0.3  # 相关性
    
    # 病毒传播阈值（达到多少互动后触发扩散）
    viral_threshold: int = 10
    
    # 回声室效应强度（相似观点聚集程度）
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """完整的模拟参数配置"""
    # 基础信息
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    
    # 时间配置
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    
    # Agent配置列表
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    
    # 事件配置
    event_config: EventConfig = field(default_factory=EventConfig)
    
    # 平台配置
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None
    
    # LLM配置
    llm_model: str = ""
    llm_base_url: str = ""
    
    # 生成元数据
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # LLM的推理说明
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    模拟配置智能生成器
    
    使用LLM分析模拟需求、文档内容、图谱实体信息，
    自动生成最佳的模拟参数配置
    
    采用分步生成策略：
    1. 生成时间配置和事件配置（轻量级）
    2. 分批生成Agent配置（每批10-20个）
    3. 生成平台配置
    """
    
    # 上下文最大字符数
    MAX_CONTEXT_LENGTH = 50000
    # 每批生成的Agent数量
    AGENTS_PER_BATCH = 30
    
    # 各步骤的上下文截断长度（字符数）
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # 时间配置
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # 事件配置
    ENTITY_SUMMARY_LENGTH = 300          # 实体摘要
    AGENT_SUMMARY_LENGTH = 300           # Agent配置中的实体摘要
    ENTITIES_PER_TYPE_DISPLAY = 20       # 每类实体显示数量
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
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
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        agent_profiles: Optional[List[Any]] = None,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
        智能生成完整的模拟配置（分步生成）
        
        Args:
            simulation_id: 模拟ID
            project_id: 项目ID
            graph_id: 图谱ID
            simulation_requirement: 模拟需求描述
            document_text: 原始文档内容
            entities: 过滤后的实体列表
            enable_twitter: 是否启用Twitter
            enable_reddit: 是否启用Reddit
            progress_callback: 进度回调函数(current_step, total_steps, message)
            
        Returns:
            SimulationParameters: 完整的模拟参数
        """
        logger.info(f"开始智能生成模拟配置: simulation_id={simulation_id}, 实体数={len(entities)}")
        
        # 计算总步骤数
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # 时间配置 + 事件配置 + N批Agent + 平台配置
        current_step = 0
        
        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")
        
        # 1. 构建基础上下文信息
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )
        
        reasoning_parts = []
        
        # ========== 步骤1+2: 并行生成时间配置和事件配置 ==========
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        report_progress(1, "并行生成时间配置和事件配置...")
        num_entities = len(entities)
        
        with ThreadPoolExecutor(max_workers=2) as pool:
            ft_time = pool.submit(self._generate_time_config, context, num_entities)
            ft_event = pool.submit(self._generate_event_config, context, simulation_requirement, entities)
            time_config_result = ft_time.result()
            event_config_result = ft_event.result()
        
        time_config = self._parse_time_config(time_config_result, num_entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"时间配置: {time_config_result.get('reasoning', '成功')}")
        reasoning_parts.append(f"事件配置: {event_config_result.get('reasoning', '成功')}")
        
        # ========== 步骤3-N: 并行生成Agent配置 ==========
        report_progress(2, f"并行生成 {len(entities)} 个Agent配置...")
        all_agent_configs = []
        
        # 构建 profile_map: agent_id -> profile 对象，供 brain_profile 生成使用
        profile_map: Dict[int, Any] = {}
        if agent_profiles:
            for profile in agent_profiles:
                pid = profile.get("user_id") if isinstance(profile, dict) else getattr(profile, "user_id", None)
                if pid is not None:
                    profile_map[int(pid)] = profile
        
        if num_batches <= 1:
            # 只有1批，直接生成
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=entities,
                start_idx=0,
                simulation_requirement=simulation_requirement,
                profile_map=profile_map,
            )
            all_agent_configs.extend(batch_configs)
        else:
            # 多批并行生成
            with ThreadPoolExecutor(max_workers=min(num_batches, 4)) as pool:
                futures = {}
                for batch_idx in range(num_batches):
                    start_idx = batch_idx * self.AGENTS_PER_BATCH
                    end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
                    batch_entities = entities[start_idx:end_idx]
                    ft = pool.submit(
                        self._generate_agent_configs_batch,
                        context=context,
                        entities=batch_entities,
                        start_idx=start_idx,
                        simulation_requirement=simulation_requirement,
                        profile_map=profile_map,
                    )
                    futures[ft] = batch_idx
                
                batch_results = [None] * num_batches
                for ft in as_completed(futures):
                    idx = futures[ft]
                    batch_results[idx] = ft.result()
                
                for br in batch_results:
                    if br:
                        all_agent_configs.extend(br)
        
        reasoning_parts.append(f"Agent配置: 成功生成 {len(all_agent_configs)} 个")
        
        # ========== 为初始帖子和定时事件分配发布者 Agent ==========
        logger.info("为初始帖子和定时事件分配合适的发布者 Agent...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        scheduled_count = len([e for e in event_config.scheduled_events if e.get("poster_agent_id") is not None])
        reasoning_parts.append(f"初始帖子分配: {assigned_count} 个帖子已分配发布者")
        if scheduled_count > 0:
            reasoning_parts.append(f"定时事件分配: {scheduled_count} 个分阶段事件已分配发布者")
        
        # ========== 最后一步: 生成平台配置（LLM推理） ==========
        report_progress(total_steps, "LLM推理生成平台配置...")
        twitter_config = None
        reddit_config = None
        
        platform_result = self._generate_platform_config(context, enable_twitter, enable_reddit)
        reasoning_parts.append(f"平台配置: {platform_result.get('reasoning', '成功')}")
        
        if enable_twitter:
            tw = platform_result.get("twitter", {})
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=self._clamp(tw.get("recency_weight", 0.4), 0.05, 0.9),
                popularity_weight=self._clamp(tw.get("popularity_weight", 0.3), 0.05, 0.9),
                relevance_weight=self._clamp(tw.get("relevance_weight", 0.3), 0.05, 0.9),
                viral_threshold=max(1, min(100, int(tw.get("viral_threshold", 10)))),
                echo_chamber_strength=self._clamp(tw.get("echo_chamber_strength", 0.5), 0.0, 1.0),
            )
        
        if enable_reddit:
            rd = platform_result.get("reddit", {})
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=self._clamp(rd.get("recency_weight", 0.3), 0.05, 0.9),
                popularity_weight=self._clamp(rd.get("popularity_weight", 0.4), 0.05, 0.9),
                relevance_weight=self._clamp(rd.get("relevance_weight", 0.3), 0.05, 0.9),
                viral_threshold=max(1, min(100, int(rd.get("viral_threshold", 15)))),
                echo_chamber_strength=self._clamp(rd.get("echo_chamber_strength", 0.6), 0.0, 1.0),
            )
        
        # 构建最终参数
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )
        
        logger.info(f"模拟配置生成完成: {len(params.agent_configs)} 个Agent配置")
        
        return params
    
    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """构建LLM上下文，截断到最大长度"""
        
        # 实体摘要
        entity_summary = self._summarize_entities(entities)
        
        # 构建上下文
        context_parts = [
            f"## 模拟需求\n{simulation_requirement}",
            f"\n## 实体信息 ({len(entities)}个)\n{entity_summary}",
        ]
        
        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # 留500字符余量
        
        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(文档已截断)"
            context_parts.append(f"\n## 原始文档内容\n{doc_text}")
        
        return "\n".join(context_parts)
    
    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """生成实体摘要"""
        lines = []
        
        # 按类型分组
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)
        
        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)}个)")
            # 使用配置的显示数量和摘要长度
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ... 还有 {len(type_entities) - display_count} 个")
        
        return "\n".join(lines)
    
    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """带重试的LLM调用，包含JSON修复逻辑"""
        import re
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # 每次重试降低温度
                    # 不设置max_tokens，让LLM自由发挥
                )
                
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # 检查是否被截断
                if finish_reason == 'length':
                    logger.warning(f"LLM输出被截断 (attempt {attempt+1})")
                    content = self._fix_truncated_json(content)
                
                # 尝试解析JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失败 (attempt {attempt+1}): {str(e)[:80]}")
                    
                    # 尝试修复JSON
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    
                    last_error = e
                    
            except Exception as e:
                logger.warning(f"LLM调用失败 (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_error or Exception("LLM调用失败")
    
    def _fix_truncated_json(self, content: str) -> str:
        """修复被截断的JSON"""
        content = content.strip()
        
        # 计算未闭合的括号
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # 检查是否有未闭合的字符串
        if content and content[-1] not in '",}]':
            content += '"'
        
        # 闭合括号
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """尝试修复配置JSON"""
        import re
        
        # 修复被截断的情况
        content = self._fix_truncated_json(content)
        
        # 提取JSON部分
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # 移除字符串中的换行符
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)
            
            try:
                return json.loads(json_str)
            except:
                # 尝试移除所有控制字符
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass
        
        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """生成时间配置"""
        # 使用配置的上下文截断长度
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]
        
        # 计算最大允许值（80%的agent数）
        max_agents_allowed = max(1, int(num_entities * 0.9))
        
        prompt = f"""基于以下模拟需求，生成时间模拟配置。

{context_truncated}

## 任务
请生成时间配置JSON。

### 基本原则（仅供参考，需根据具体事件和参与群体灵活调整）：
- 用户群体为中国人，需符合北京时间作息习惯
- 凌晨0-5点几乎无人活动（活跃度系数0.05）
- 早上6-8点逐渐活跃（活跃度系数0.4）
- 工作时间9-18点中等活跃（活跃度系数0.7）
- 晚间19-22点是高峰期（活跃度系数1.5）
- 23点后活跃度下降（活跃度系数0.5）
- 一般规律：凌晨低活跃、早间渐增、工作时段中等、晚间高峰
- **重要**：以下示例值仅供参考，你需要根据事件性质、参与群体特点来调整具体时段
  - 例如：学生群体高峰可能是21-23点；媒体全天活跃；官方机构只在工作时间
  - 例如：突发热点可能导致深夜也有讨论，off_peak_hours 可适当缩短

### 返回JSON格式（不要markdown）

示例：
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "针对该事件的时间配置说明"
}}

字段说明：
- total_simulation_hours (int): 模拟总时长，24-168小时，突发事件短、持续话题长
- minutes_per_round (int): 每轮时长，30-120分钟，建议60分钟
- agents_per_hour_min (int): 每小时最少激活Agent数（取值范围: 1-{max_agents_allowed}）
- agents_per_hour_max (int): 每小时最多激活Agent数（取值范围: 1-{max_agents_allowed}）
- peak_hours (int数组): 高峰时段，根据事件参与群体调整
- off_peak_hours (int数组): 低谷时段，通常深夜凌晨
- morning_hours (int数组): 早间时段
- work_hours (int数组): 工作时段
- reasoning (string): 简要说明为什么这样配置"""

        system_prompt = "你是社交媒体模拟专家。返回纯JSON格式，时间配置需符合中国人作息习惯。"
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"时间配置LLM生成失败: {e}, 使用默认配置")
            return self._get_default_time_config(num_entities)
    
    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """获取默认时间配置（中国人作息）"""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # 每轮1小时，加快时间流速
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "使用默认中国人作息配置（每轮1小时）"
        }
    
    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """解析时间配置结果，并验证agents_per_hour值不超过总agent数"""
        # 获取原始值
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))
        
        # 验证并修正：确保不超过总agent数
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) 超过总Agent数 ({num_entities})，已修正")
            agents_per_hour_min = max(1, num_entities // 10)
        
        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) 超过总Agent数 ({num_entities})，已修正")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)
        
        # 确保 min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max，已修正为 {agents_per_hour_min}")
        
        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 72),
            minutes_per_round=result.get("minutes_per_round", 60),  # 默认每轮1小时
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,  # 凌晨几乎无人
            morning_hours=result.get("morning_hours", [6, 7, 8]),
            morning_activity_multiplier=0.4,
            work_hours=result.get("work_hours", list(range(9, 19))),
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )
    
    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        """将数值限制在指定范围内"""
        return max(low, min(high, float(value)))
    
    def _generate_platform_config(
        self,
        context: str,
        enable_twitter: bool,
        enable_reddit: bool
    ) -> Dict[str, Any]:
        """使用LLM推理生成平台推荐算法配置"""
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]
        
        platforms_desc = []
        if enable_twitter:
            platforms_desc.append("twitter（广场/信息流平台，类似微博）")
        if enable_reddit:
            platforms_desc.append("reddit（话题/社区平台，类似知乎/贴吧）")
        
        prompt = f"""基于以下模拟需求，为社交平台推荐算法生成配置参数。

{context_truncated}

## 需要配置的平台
{chr(10).join(f"- {p}" for p in platforms_desc)}

## 任务
请根据事件性质、传播特点和参与群体，推理生成每个平台的推荐算法参数。

### 参数说明
- **recency_weight** (0.05-0.9): 时效性权重。突发热点事件应更高（让最新内容优先展示），慢热话题可降低
- **popularity_weight** (0.05-0.9): 热度权重。容易引发群体共鸣的事件应提高（让热门帖子更多曝光），理性讨论型可降低
- **relevance_weight** (0.05-0.9): 相关性权重。专业性强的话题应提高（让相关内容聚合），泛化话题可降低
- **viral_threshold** (1-100): 病毒传播阈值（帖子获得多少互动后触发扩散推荐）。情绪化事件应降低（更容易传播），理性讨论应提高
- **echo_chamber_strength** (0.0-1.0): 回音室效应强度。观点极化严重的事件应提高（模拟观点聚集），需要多元声音的场景应降低

注意：
- 三个权重(recency + popularity + relevance)无需严格加和为1，系统会自动归一化
- twitter（广场型）通常更注重时效性和病毒传播，阈值更低
- reddit（社区型）通常更注重热度和深度讨论，回音室效应更强
- 请根据**具体事件特征**调整，不要使用通用默认值

### 返回JSON格式（不要markdown）
{{
    "twitter": {{
        "recency_weight": 0.45,
        "popularity_weight": 0.30,
        "relevance_weight": 0.25,
        "viral_threshold": 8,
        "echo_chamber_strength": 0.4
    }},
    "reddit": {{
        "recency_weight": 0.25,
        "popularity_weight": 0.40,
        "relevance_weight": 0.35,
        "viral_threshold": 18,
        "echo_chamber_strength": 0.65
    }},
    "reasoning": "简要说明为什么这样配置（结合事件特点）"
}}"""

        system_prompt = "你是社交媒体推荐算法和舆情传播专家。根据具体事件特征推理生成平台参数，返回纯JSON。"
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"平台配置LLM生成失败: {e}, 使用默认配置")
            return {
                "twitter": {
                    "recency_weight": 0.4,
                    "popularity_weight": 0.3,
                    "relevance_weight": 0.3,
                    "viral_threshold": 10,
                    "echo_chamber_strength": 0.5
                },
                "reddit": {
                    "recency_weight": 0.3,
                    "popularity_weight": 0.4,
                    "relevance_weight": 0.3,
                    "viral_threshold": 15,
                    "echo_chamber_strength": 0.6
                },
                "reasoning": "LLM推理失败，使用默认配置"
            }
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """生成事件配置（分阶段信息释放）
        
        核心改进：将信息按5阶段释放，而非一次性灌入全部信息。
        - initial_posts: 仅包含第1阶段（事件曝光/爆发期）的信息
        - scheduled_events: 包含第2-5阶段的定时释放帖子，按 trigger_round 触发
        
        论文依据：
        - SocioVerse §2.1: Social Environment 按时间线释放事件
        - OASIS: 平台信息流算法控制可见性
        - Generative Agents: 信息通过时间释放自然传播
        """
        
        # 获取可用的实体类型列表，供 LLM 参考
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))
        
        # 为每种类型列出代表性实体名称
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # 使用配置的上下文截断长度
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f"""基于以下模拟需求，生成**分阶段信息释放**的事件配置。

模拟需求: {simulation_requirement}

{context_truncated}

## 可用实体类型及示例
{type_info}

## 分阶段信息释放规则（非常重要）

模拟分为5个阶段，每个阶段约占总轮数的20%：
- **P1（第1-20%轮）**: 事件曝光/爆发期 —— 只释放事件的起因、初始争议
- **P2（第21-40%轮）**: 扩散期 —— 释放媒体报道、舆论扩散信息
- **P3（第41-60%轮）**: 官方回应期 —— 释放官方声明、调查结果、司法进展
- **P4（第61-80%轮）**: 二次传播期 —— 释放公众质疑、深度追问、二次争议
- **P5（第81-100%轮）**: 收敛期 —— 释放后续发展、制度反思、总结性内容

**关键约束**：
1. initial_posts **只能包含 P1 阶段的信息**（事件起因、初始爆料、当事人初始反应）
2. P2-P5 的信息必须放入 scheduled_events，通过 trigger_round_pct 指定触发时机
3. 每个阶段的帖子内容**不能提前泄露后续阶段的信息**
4. 例如：P1 的帖子不能提到"法院判决"、"官方通报结果"等后续才发生的事

## 任务
请生成事件配置JSON：
- 提取热点话题关键词
- 描述舆论发展方向
- 设计 initial_posts（仅P1）和 scheduled_events（P2-P5）
- **每个帖子必须指定 poster_type**，从可用实体类型中选择

返回JSON格式（不要markdown）：
{{
    "hot_topics": ["关键词1", "关键词2", ...],
    "narrative_direction": "<舆论发展方向描述>",
    "initial_posts": [
        {{"content": "P1阶段的帖子内容（仅事件起因/初始争议）", "poster_type": "实体类型"}},
        ...
    ],
    "scheduled_events": [
        {{"content": "P2阶段的帖子内容", "poster_type": "实体类型", "trigger_round_pct": 25, "phase": "P2", "phase_description": "扩散期"}},
        {{"content": "P3阶段的帖子内容", "poster_type": "实体类型", "trigger_round_pct": 45, "phase": "P3", "phase_description": "官方回应期"}},
        {{"content": "P4阶段的帖子内容", "poster_type": "实体类型", "trigger_round_pct": 65, "phase": "P4", "phase_description": "二次传播期"}},
        {{"content": "P5阶段的帖子内容", "poster_type": "实体类型", "trigger_round_pct": 85, "phase": "P5", "phase_description": "收敛期"}},
        ...
    ],
    "reasoning": "<简要说明分阶段设计的理由>"
}}

**注意**: 
- trigger_round_pct 是触发轮次占总轮数的百分比（0-100），例如25表示在总轮数的25%时触发
- 每个阶段可以有多个帖子（不同角色的视角）
- poster_type 必须从上面的"可用实体类型"中精确选择"""

        system_prompt = "你是舆论分析与信息传播专家。你需要将事件信息按时间线分阶段释放，确保每个阶段只包含该阶段应该出现的信息，不能提前泄露后续发展。返回纯JSON格式。注意 poster_type 必须精确匹配可用实体类型。"
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"事件配置LLM生成失败: {e}, 使用默认配置")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "scheduled_events": [],
                "reasoning": "使用默认配置"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """解析事件配置结果（含分阶段定时事件）"""
        scheduled_events = result.get("scheduled_events", [])
        # 校验每个 scheduled_event 必须包含 trigger_round_pct
        validated_events = []
        for evt in scheduled_events:
            if not isinstance(evt, dict):
                continue
            pct = evt.get("trigger_round_pct")
            if pct is None:
                logger.warning(f"scheduled_event 缺少 trigger_round_pct，跳过: {evt.get('content', '')[:50]}")
                continue
            try:
                evt["trigger_round_pct"] = int(pct)
            except (ValueError, TypeError):
                logger.warning(f"trigger_round_pct 不是有效整数: {pct}，跳过")
                continue
            validated_events.append(evt)
        
        if validated_events:
            logger.info(f"解析到 {len(validated_events)} 个分阶段定时事件 (P2-P5)")
        
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=validated_events,
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _match_agent_for_poster_type(
        self,
        poster_type: str,
        agents_by_type: Dict[str, List[AgentActivityConfig]],
        type_aliases: Dict[str, List[str]],
        used_indices: Dict[str, int],
        agent_configs: List[AgentActivityConfig],
    ) -> int:
        """根据 poster_type 匹配最合适的 agent_id"""
        poster_type_lower = poster_type.lower()
        matched_agent_id = None
        
        # 1. 直接匹配
        if poster_type_lower in agents_by_type:
            agents = agents_by_type[poster_type_lower]
            idx = used_indices.get(poster_type_lower, 0) % len(agents)
            matched_agent_id = agents[idx].agent_id
            used_indices[poster_type_lower] = idx + 1
        else:
            # 2. 使用别名匹配
            for alias_key, aliases in type_aliases.items():
                if poster_type_lower in aliases or alias_key == poster_type_lower:
                    for alias in aliases:
                        if alias in agents_by_type:
                            agents = agents_by_type[alias]
                            idx = used_indices.get(alias, 0) % len(agents)
                            matched_agent_id = agents[idx].agent_id
                            used_indices[alias] = idx + 1
                            break
                if matched_agent_id is not None:
                    break
        
        # 3. 如果仍未找到，使用影响力最高的 agent
        if matched_agent_id is None:
            logger.warning(f"未找到类型 '{poster_type}' 的匹配 Agent，使用影响力最高的 Agent")
            if agent_configs:
                sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                matched_agent_id = sorted_agents[0].agent_id
            else:
                matched_agent_id = 0
        
        return matched_agent_id
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
        为初始帖子和定时事件分配合适的发布者 Agent
        
        根据每个帖子的 poster_type 匹配最合适的 agent_id
        """
        if not event_config.initial_posts and not event_config.scheduled_events:
            return event_config
        
        # 按实体类型建立 agent 索引
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        # 类型映射表（处理 LLM 可能输出的不同格式）
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        # 记录每种类型已使用的 agent 索引，避免重复使用同一个 agent
        used_indices: Dict[str, int] = {}
        
        # --- 分配 initial_posts ---
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "Unknown")
            matched_agent_id = self._match_agent_for_poster_type(
                poster_type, agents_by_type, type_aliases, used_indices, agent_configs
            )
            updated_posts.append({
                "content": post.get("content", ""),
                "poster_type": poster_type,
                "poster_agent_id": matched_agent_id
            })
            logger.info(f"初始帖子分配: poster_type='{poster_type}' -> agent_id={matched_agent_id}")
        
        event_config.initial_posts = updated_posts
        
        # --- 分配 scheduled_events ---
        updated_events = []
        for evt in event_config.scheduled_events:
            poster_type = evt.get("poster_type", "Unknown")
            matched_agent_id = self._match_agent_for_poster_type(
                poster_type, agents_by_type, type_aliases, used_indices, agent_configs
            )
            updated_evt = {
                "content": evt.get("content", ""),
                "poster_type": poster_type,
                "poster_agent_id": matched_agent_id,
                "trigger_round_pct": evt.get("trigger_round_pct", 50),
                "phase": evt.get("phase", ""),
                "phase_description": evt.get("phase_description", ""),
            }
            updated_events.append(updated_evt)
            logger.info(
                f"定时事件分配: phase={updated_evt['phase']}, "
                f"trigger_pct={updated_evt['trigger_round_pct']}%, "
                f"poster_type='{poster_type}' -> agent_id={matched_agent_id}"
            )
        
        event_config.scheduled_events = updated_events
        return event_config
    
    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str,
        profile_map: Optional[Dict[int, Any]] = None,
    ) -> List[AgentActivityConfig]:
        """分批生成Agent配置"""
        
        # 构建实体信息（使用配置的摘要长度）
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[:summary_len] if e.summary else ""
            })
        
        prompt = f"""基于以下信息，为每个实体生成社交媒体活动配置。

模拟需求: {simulation_requirement}

## 实体列表
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## 任务
为每个实体生成活动配置，注意：
- **时间符合中国人作息**：凌晨0-5点几乎不活动，晚间19-22点最活跃
- **官方机构**（University/GovernmentAgency）：活跃度低(0.1-0.3)，工作时间(9-17)活动，响应慢(60-240分钟)，影响力高(2.5-3.0)
- **媒体**（MediaOutlet）：活跃度中(0.4-0.6)，全天活动(8-23)，响应快(5-30分钟)，影响力高(2.0-2.5)
- **个人**（Student/Person/Alumni）：活跃度高(0.6-0.9)，主要晚间活动(18-23)，响应快(1-15分钟)，影响力低(0.8-1.2)
- **公众人物/专家**：活跃度中(0.4-0.6)，影响力中高(1.5-2.0)

返回JSON格式（不要markdown）：
{{
    "agent_configs": [
        {{
            "agent_id": <必须与输入一致>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <发帖频率>,
            "comments_per_hour": <评论频率>,
            "active_hours": [<活跃小时列表，考虑中国人作息>],
            "response_delay_min": <最小响应延迟分钟>,
            "response_delay_max": <最大响应延迟分钟>,
            "sentiment_bias": <-1.0到1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <影响力权重>
        }},
        ...
    ]
}}"""

        system_prompt = "你是社交媒体行为分析专家。返回纯JSON，配置需符合中国人作息习惯。"
        
        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent配置批次LLM生成失败: {e}, 使用规则生成")
            llm_configs = {}
        
        # 构建AgentActivityConfig对象
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # 如果LLM没有生成，使用规则生成
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=cfg.get("active_hours", list(range(9, 23))),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0),
                brain_profile=create_agent_brain_profile(
                    agent_id=agent_id,
                    entity_name=entity.name,
                    entity_type=entity.get_entity_type() or "Unknown",
                    entity_summary=entity.summary or "",
                    simulation_requirement=simulation_requirement,
                    activity_config=cfg,
                    profile=profile_map.get(agent_id) if profile_map else None,
                ),
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """基于规则生成单个Agent配置（中国人作息）"""
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        
        if entity_type in ["university", "governmentagency", "ngo"]:
            # 官方机构：工作时间活动，低频率，高影响力
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),  # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # 媒体：全天活动，中等频率，高影响力
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),  # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            # 专家/教授：工作+晚间活动，中等频率
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),  # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # 学生：晚间为主，高频率
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # 上午+晚间
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            # 校友：晚间为主
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  # 午休+晚间
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            # 普通人：晚间高峰
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # 白天+晚间
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
    

