"""
图谱构建服务
使用 Graphiti + Neo4j 构建知识图谱
"""

import os
import uuid
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, Field, create_model
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..utils.graphiti_client import get_graphiti, create_fresh_graphiti, run_async, run_async_batch, remove_instance, get_neo4j_async_driver
from .text_processor import TextProcessor
from .vector_store import VectorStore


@dataclass
class GraphInfo:
    """图谱信息"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    图谱构建服务
    负责调用 Graphiti + Neo4j 构建知识图谱
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # api_key 参数保留用于兼容，但 Graphiti 使用环境变量中的 OPENAI_API_KEY
        self.task_manager = TaskManager()
        self.vector_store = VectorStore()
    
    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "NexusMind Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3
    ) -> str:
        """
        异步构建图谱
        
        Args:
            text: 输入文本
            ontology: 本体定义（来自接口1的输出）
            graph_name: 图谱名称
            chunk_size: 文本块大小
            chunk_overlap: 块重叠大小
            batch_size: 每批发送的块数量
            
        Returns:
            任务ID
        """
        # 创建任务
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            }
        )
        
        # 在后台线程中执行构建
        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap, batch_size)
        )
        thread.daemon = True
        thread.start()
        
        return task_id
    
    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int
    ):
        """图谱构建工作线程"""
        try:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=5,
                message="开始构建图谱..."
            )
            
            # 1. 创建图谱
            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id,
                progress=10,
                message=f"图谱已创建: {graph_id}"
            )
            
            # 2. 设置本体
            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id,
                progress=15,
                message="本体已设置"
            )
            
            # 3. 文本分块
            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id,
                progress=20,
                message=f"文本已分割为 {total_chunks} 个块"
            )
            
            # 4. 分批发送数据
            episode_uuids = self.add_text_batches(
                graph_id, chunks, batch_size,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=20 + int(prog * 0.4),  # 20-60%
                    message=msg
                )
            )
            
            # 5. 等待图谱处理完成
            self.task_manager.update_task(
                task_id,
                progress=60,
                message="等待图谱处理数据..."
            )
            
            self._wait_for_episodes(
                episode_uuids,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=60 + int(prog * 0.3),  # 60-90%
                    message=msg
                )
            )
            
            # 6. 存储向量 RAG 索引
            self.task_manager.update_task(
                task_id,
                progress=85,
                message="构建向量 RAG 索引..."
            )
            self.vector_store.store_chunks(
                graph_id=graph_id,
                chunks=chunks,
                progress_callback=lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=85 + int(prog * 5),  # 85-90%
                    message=msg
                )
            )
            
            # 7. 获取图谱信息
            self.task_manager.update_task(
                task_id,
                progress=90,
                message="获取图谱信息..."
            )
            
            graph_info = self._get_graph_info(graph_id)
            
            # 完成
            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)
    
    def create_graph(self, name: str) -> str:
        """创建图谱（清理旧数据 → 初始化索引）"""
        graph_id = f"nexusmind_{uuid.uuid4().hex[:16]}"
        
        # 清理旧图谱数据，确保不同项目之间数据隔离
        from neo4j import AsyncGraphDatabase
        async def _clear():
            driver = AsyncGraphDatabase.driver(
                Config.NEO4J_URI,
                auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD),
            )
            try:
                await driver.execute_query(
                    "MATCH (n) DETACH DELETE n",
                    database_=Config.NEO4J_DATABASE,
                )
            finally:
                await driver.close()
        
        run_async(_clear())
        
        graphiti = get_graphiti(graph_id)
        run_async(graphiti.build_indices_and_constraints())
        
        return graph_id
    
    # 中文抽取指令，注入到每个 add_episode 调用
    CHINESE_EXTRACTION_INSTRUCTIONS = (
        "## 语言要求\n"
        "所有提取的实体名称（entity name）和关系名称（edge name / fact）都必须使用简体中文。"
        "如果原文是英文，请将实体名翻译为中文。"
        "例如：'Harvard University' → '哈佛大学'，'Donald Trump' → '唐纳德·特朗普'，'FBI' → '美国联邦调查局'。"
        "关系描述（fact）也使用中文。实体名称应尽量使用完整的中文名称，不要截断。\n\n"
        "## 实体质量要求（极其重要）\n"
        "只提取以下类型的实体——即现实世界中具体存在的、可以在社交媒体上发声或被提及的主体：\n"
        "✅ 可以提取：具体的人名（如'张三'、'马克·扎克伯格'）、具体组织（如'北京大学'、'美国教育部'、'纽约时报'）、"
        "具体平台（如'微博'、'Twitter'）、具体国家/地区（如'美国'、'欧盟'）、具体政党/团体（如'共和党'、'绿色和平'）\n"
        "❌ 绝对不能提取：抽象概念、主题词、话题、情感、态度、趋势、价值观。"
        "以下类型的词语绝对不能作为实体：'学术诚信'、'校园氛围'、'职业'、'教学'、'分歧'、"
        "'行动呼吁'、'多样性'、'公平性'、'包容性'、'舆论'、'情绪'、'观点'、"
        "'政策'、'分歧'、'招生'、'海外留学'、'档案'、'文件'、'调查'、'教育'等。"
        "这些是主题/概念，不是可以独立存在的实体。\n\n"
        "## 判断标准\n"
        "提取实体前请自问：'这个词在现实中是否指一个具体的人、机构或组织？能否有自己的社交媒体账号？'"
        "如果答案是否，则不要提取为实体。"
    )

    @staticmethod
    def _build_pydantic_entity_types(ontology: Dict[str, Any]) -> Dict[str, type]:
        """
        将本体 entity_types 转为 Graphiti 所需的 Pydantic 模型字典。
        每个 key 是实体类型名（PascalCase），value 是动态生成的 BaseModel 子类。
        """
        entity_models: Dict[str, type] = {}
        for entity_def in ontology.get("entity_types", []):
            name = entity_def["name"]
            desc = entity_def.get("description", name)
            fields: Dict[str, Any] = {}
            for attr in entity_def.get("attributes", []):
                attr_name = attr["name"]
                attr_desc = attr.get("description", attr_name)
                fields[attr_name] = (Optional[str], Field(default=None, description=attr_desc))
            model = create_model(name, __doc__=desc, **fields)
            entity_models[name] = model
        return entity_models

    @staticmethod
    def _build_pydantic_edge_types(ontology: Dict[str, Any]):
        """
        将本体 edge_types 转为 Graphiti 所需的 Pydantic 模型字典及 edge_type_map。
        """
        edge_models: Dict[str, type] = {}
        edge_type_map: Dict[tuple, List[str]] = {}
        for edge_def in ontology.get("edge_types", []):
            name = edge_def["name"]
            desc = edge_def.get("description", name)
            fields: Dict[str, Any] = {}
            for attr in edge_def.get("attributes", []):
                attr_name = attr["name"]
                attr_desc = attr.get("description", attr_name)
                fields[attr_name] = (Optional[str], Field(default=None, description=attr_desc))
            model = create_model(name, __doc__=desc, **fields)
            edge_models[name] = model
            for st in edge_def.get("source_targets", []):
                src = st.get("source", "Entity")
                tgt = st.get("target", "Entity")
                key = (src, tgt)
                edge_type_map.setdefault(key, [])
                if name not in edge_type_map[key]:
                    edge_type_map[key].append(name)
        return edge_models, edge_type_map

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """
        设置图谱本体。
        
        使用 Graphiti 的 prescribed ontology（Pydantic 模型）精确约束实体和关系类型，
        并将本体文本作为首个 episode 注入以提供上下文。
        """
        # 构建 Pydantic 模型，缓存在实例上供 add_text_batches 复用
        self._entity_types = self._build_pydantic_entity_types(ontology)
        self._edge_types, self._edge_type_map = self._build_pydantic_edge_types(ontology)
        
        # 仍然构建文本描述用于首个 episode 的上下文
        ontology_text_parts = ["=== 本体定义 (Ontology) ===\n"]
        
        for entity_def in ontology.get("entity_types", []):
            name = entity_def["name"]
            desc = entity_def.get("description", "")
            examples = entity_def.get("examples", [])
            examples_str = ", ".join(examples[:3]) if examples else "无"
            ontology_text_parts.append(
                f"实体类型 [{name}]: {desc}. 示例: {examples_str}"
            )
        
        for edge_def in ontology.get("edge_types", []):
            name = edge_def["name"]
            desc = edge_def.get("description", "")
            source_targets = edge_def.get("source_targets", [])
            st_str = ", ".join([f"{st.get('source', '?')}->{st.get('target', '?')}" for st in source_targets])
            ontology_text_parts.append(
                f"关系类型 [{name}]: {desc}. 连接: {st_str}"
            )
        
        ontology_text = "\n".join(ontology_text_parts)
        
        # 作为首个 episode 注入（带 prescribed 类型约束）
        graphiti = get_graphiti(graph_id)
        run_async(graphiti.add_episode(
            name="ontology_definition",
            episode_body=ontology_text,
            source=EpisodeType.text,
            source_description="知识图谱本体定义",
            reference_time=datetime.now(timezone.utc),
            entity_types=self._entity_types,
            edge_types=self._edge_types,
            edge_type_map=self._edge_type_map,
            custom_extraction_instructions=self.CHINESE_EXTRACTION_INSTRUCTIONS,
        ), timeout=120)
    
    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """
        并发添加文本块到图谱。
        
        每批 batch_size 个 chunk 并发处理（通过 asyncio.gather + semaphore），
        显著减少总耗时。DashScope API 限流由 semaphore 控制。
        
        返回 episode 名称列表（用于跟踪）。
        """
        episode_names = []
        total_chunks = len(chunks)
        graphiti = get_graphiti(graph_id)
        
        # 按 batch_size 分组并发处理
        for batch_start in range(0, total_chunks, batch_size):
            batch_end = min(batch_start + batch_size, total_chunks)
            batch_chunks = chunks[batch_start:batch_end]
            
            if progress_callback:
                progress = batch_start / total_chunks
                progress_callback(
                    f"并发处理第 {batch_start + 1}-{batch_end}/{total_chunks} 个文本块...",
                    progress
                )
            
            # 构建本批次的所有协程
            coros = []
            batch_names = []
            for i, chunk in enumerate(batch_chunks):
                idx = batch_start + i
                episode_name = f"chunk_{idx:04d}"
                batch_names.append(episode_name)
                coros.append(graphiti.add_episode(
                    name=episode_name,
                    episode_body=chunk,
                    source=EpisodeType.text,
                    source_description=f"文档片段 {idx + 1}/{total_chunks}",
                    reference_time=datetime.now(timezone.utc),
                    entity_types=getattr(self, '_entity_types', None),
                    edge_types=getattr(self, '_edge_types', None),
                    edge_type_map=getattr(self, '_edge_type_map', None),
                    custom_extraction_instructions=self.CHINESE_EXTRACTION_INSTRUCTIONS,
                ))
            
            try:
                run_async_batch(coros, max_concurrency=batch_size)
                episode_names.extend(batch_names)
            except Exception as e:
                if progress_callback:
                    progress_callback(
                        f"文本块 {batch_start + 1}-{batch_end} 处理失败: {str(e)}", 0
                    )
                raise
        
        return episode_names
    
    def _wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[Callable] = None,
        timeout: int = 600
    ):
        """
        Graphiti 的 add_episode 是同步处理的（调用完成即处理完成），
        不需要轮询等待。
        此方法保留接口兼容性，直接报告完成。
        """
        total = len(episode_uuids) if episode_uuids else 0
        if progress_callback:
            progress_callback(f"所有 {total} 个文本块已处理完成", 1.0)
    
    def tag_graph_data(self, graph_id: str):
        """构建完成后，给所有节点和边打上 group_id 标记，用于按项目隔离数据"""
        async def _tag():
            driver = get_neo4j_async_driver()
            await driver.execute_query(
                "MATCH (n:Entity) WHERE n.group_id IS NULL OR n.group_id = '' "
                "SET n.group_id = $gid",
                gid=graph_id,
                database_=Config.NEO4J_DATABASE,
            )
            await driver.execute_query(
                "MATCH ()-[r]->() WHERE r.group_id IS NULL OR r.group_id = '' "
                "SET r.group_id = $gid",
                gid=graph_id,
                database_=Config.NEO4J_DATABASE,
            )
        
        run_async(_tag())
    
    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """获取图谱信息"""
        graph_data = self.get_graph_data(graph_id)
        
        entity_types = set()
        for node in graph_data.get("nodes", []):
            for label in node.get("labels", []):
                if label not in ["Entity", "Node"]:
                    entity_types.add(label)

        return GraphInfo(
            graph_id=graph_id,
            node_count=graph_data.get("node_count", 0),
            edge_count=graph_data.get("edge_count", 0),
            entity_types=list(entity_types)
        )
    
    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """
        获取完整图谱数据（直接通过 Neo4j Cypher 查询）。
        
        1. 查询所有 Entity 节点和 RELATES_TO 边
        2. 基于 ontology 类型名和边连接推断每个节点的 entity type
        3. 将 entity type 写入 labels，供前端按类型着色
        """
        async def _fetch():
            driver = get_neo4j_async_driver()
            # 按 group_id 过滤（兼容未标记的旧数据）
            gid_filter = "WHERE n.group_id = $gid OR n.group_id IS NULL" if graph_id else ""
            node_result = await driver.execute_query(
                f"MATCH (n:Entity) {gid_filter} "
                "RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary, "
                "n.group_id AS group_id, n.created_at AS created_at",
                gid=graph_id,
                database_=Config.NEO4J_DATABASE,
            )
            edge_gid = "WHERE r.group_id = $gid OR r.group_id IS NULL" if graph_id else ""
            edge_result = await driver.execute_query(
                f"MATCH (a:Entity)-[r]->(b:Entity) {edge_gid} "
                "RETURN r.uuid AS uuid, r.name AS name, r.fact AS fact, "
                "type(r) AS rel_type, "
                "r.source_node_uuid AS source_uuid, r.target_node_uuid AS target_uuid, "
                "a.name AS source_name, b.name AS target_name, "
                "a.uuid AS src_uuid, b.uuid AS tgt_uuid, "
                "r.created_at AS created_at, r.valid_at AS valid_at, "
                "r.episodes AS episodes",
                gid=graph_id,
                database_=Config.NEO4J_DATABASE,
            )
            # 共现边：同一 Episode 提到的实体对（至少共现2次，上限200条）
            cooccur_result = await driver.execute_query(
                "MATCH (ep)-[:MENTIONS]->(a:Entity), (ep)-[:MENTIONS]->(b:Entity) "
                "WHERE elementId(a) < elementId(b) "
                "WITH a, b, count(ep) AS weight "
                "WHERE weight >= 2 "
                "RETURN a.uuid AS src_uuid, a.name AS src_name, "
                "b.uuid AS tgt_uuid, b.name AS tgt_name, weight "
                "ORDER BY weight DESC LIMIT 200",
                database_=Config.NEO4J_DATABASE,
            )
            return node_result.records, edge_result.records, cooccur_result.records
        
        try:
            node_records, edge_records, cooccur_records = run_async(_fetch())
        except Exception as e:
            import traceback
            traceback.print_exc()
            node_records, edge_records, cooccur_records = [], [], []
        
        # --- 推断 entity type ---
        # 收集所有节点名称
        all_names = set()
        node_summaries = {}
        for rec in node_records:
            name = rec["name"] or ""
            all_names.add(name)
            node_summaries[name] = rec["summary"] or ""
        
        # 识别 type 定义节点（summary 包含 "属性:" 模式，说明是 ontology 类型描述）
        type_names = set()
        for name, summary in node_summaries.items():
            if summary and "属性:" in summary and len(summary) > 30:
                type_names.add(name)
        
        # 通过边关系推断实例节点的类型（实例 → 类型定义节点 的边）
        node_uuid_to_name = {}
        for rec in node_records:
            node_uuid_to_name[rec["uuid"]] = rec["name"] or ""
        
        # 正向 + 反向关系：如果一个实例节点连接到一个类型定义节点，就继承该类型
        node_type_map = {}  # node_name -> entity_type
        for rec in edge_records:
            src = rec["source_name"] or ""
            tgt = rec["target_name"] or ""
            if src in type_names and tgt not in type_names:
                if tgt not in node_type_map:
                    node_type_map[tgt] = src
            elif tgt in type_names and src not in type_names:
                if src not in node_type_map:
                    node_type_map[src] = tgt
        
        # 对未分类节点，尝试从 summary 中匹配类型关键词
        for name in all_names:
            if name in type_names or name in node_type_map:
                continue
            summary = node_summaries.get(name, "")
            for tn in type_names:
                if tn.lower() in summary.lower():
                    node_type_map[name] = tn
                    break
        
        def _get_labels(name: str) -> List[str]:
            if name in type_names:
                return ["Entity", name]
            entity_type = node_type_map.get(name)
            if entity_type:
                return ["Entity", entity_type]
            return ["Entity"]
        
        # --- 构建返回数据 ---
        node_map = {}
        nodes_data = []
        for rec in node_records:
            uuid = str(rec["uuid"] or "")
            name = rec["name"] or ""
            node_map[uuid] = name
            
            created_at = rec["created_at"]
            nodes_data.append({
                "uuid": uuid,
                "name": name,
                "labels": _get_labels(name),
                "summary": rec["summary"] or "",
                "attributes": {},
                "created_at": str(created_at) if created_at else None,
            })
        
        edges_data = []
        for rec in edge_records:
            uuid = str(rec["uuid"] or "")
            # source/target uuid: 优先用边上的属性，回退到匹配的节点 uuid
            source_uuid = str(rec["source_uuid"] or rec["src_uuid"] or "")
            target_uuid = str(rec["target_uuid"] or rec["tgt_uuid"] or "")
            rel_type = rec["rel_type"] or ""
            edge_name = rec["name"] or rel_type
            created_at = rec["created_at"]
            valid_at = rec["valid_at"]
            episodes = rec["episodes"]
            if episodes and not isinstance(episodes, list):
                episodes = [str(episodes)]
            elif episodes:
                episodes = [str(e) for e in episodes]
            
            edges_data.append({
                "uuid": uuid,
                "name": edge_name,
                "fact": rec["fact"] or "",
                "fact_type": rel_type or edge_name,
                "source_node_uuid": source_uuid,
                "target_node_uuid": target_uuid,
                "source_node_name": rec["source_name"] or node_map.get(source_uuid, ""),
                "target_node_name": rec["target_name"] or node_map.get(target_uuid, ""),
                "attributes": {},
                "created_at": str(created_at) if created_at else None,
                "valid_at": str(valid_at) if valid_at else None,
                "invalid_at": None,
                "expired_at": None,
                "episodes": episodes or [],
            })
        
        # --- 共现边：同一文本块提到的实体对 ---
        existing_pairs = set()
        for e in edges_data:
            pair = tuple(sorted([e["source_node_uuid"], e["target_node_uuid"]]))
            existing_pairs.add(pair)
        
        for rec in cooccur_records:
            src_uuid = str(rec["src_uuid"] or "")
            tgt_uuid = str(rec["tgt_uuid"] or "")
            pair = tuple(sorted([src_uuid, tgt_uuid]))
            if pair in existing_pairs or not src_uuid or not tgt_uuid:
                continue
            existing_pairs.add(pair)
            weight = rec["weight"] or 1
            edges_data.append({
                "uuid": f"cooccur_{src_uuid[:8]}_{tgt_uuid[:8]}",
                "name": f"共现({weight})",
                "fact": f"在 {weight} 个文本块中共同出现",
                "fact_type": "CO_OCCURRENCE",
                "source_node_uuid": src_uuid,
                "target_node_uuid": tgt_uuid,
                "source_node_name": rec["src_name"] or node_map.get(src_uuid, ""),
                "target_node_name": rec["tgt_name"] or node_map.get(tgt_uuid, ""),
                "attributes": {"weight": weight},
                "created_at": None,
                "valid_at": None,
                "invalid_at": None,
                "expired_at": None,
                "episodes": [],
            })
        
        # --- 过滤孤立节点（无任何边的节点不显示）---
        connected_uuids = set()
        for e in edges_data:
            connected_uuids.add(e["source_node_uuid"])
            connected_uuids.add(e["target_node_uuid"])
        nodes_data = [n for n in nodes_data if n["uuid"] in connected_uuids]
        
        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }
    
    def delete_graph(self, graph_id: str):
        """删除图谱（清空 Neo4j 中的所有节点和边）"""
        remove_instance(graph_id)
        try:
            graphiti = get_graphiti(graph_id)
            run_async(graphiti.driver.execute_query("MATCH (n) DETACH DELETE n"))
        except Exception:
            pass

