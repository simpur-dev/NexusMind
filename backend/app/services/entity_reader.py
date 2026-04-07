"""
实体读取与过滤服务
从 Graphiti + FalkorDB 图谱中读取节点，筛选出符合预定义实体类型的节点
"""

import time
from typing import Dict, Any, List, Optional, Set, Callable, TypeVar
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger
from ..utils.graphiti_client import run_async, get_neo4j_async_driver

logger = get_logger('nexusmind.entity_reader')

# 用于泛型返回类型
T = TypeVar('T')


@dataclass
class EntityNode:
    """实体节点数据结构"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    # 相关的边信息
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    # 相关的其他节点信息
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }
    
    def get_entity_type(self) -> Optional[str]:
        """获取实体类型（排除默认的Entity标签）"""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """过滤后的实体集合"""
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class EntityReader:
    """
    实体读取与过滤服务（使用 Graphiti + FalkorDB）
    
    主要功能：
    1. 从图谱读取所有节点
    2. 筛选出符合预定义实体类型的节点（Labels不只是Entity的节点）
    3. 获取每个实体的相关边和关联节点信息
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # api_key 参数保留用于接口兼容，Graphiti 使用 FalkorDB 本地连接
        pass
    
    def _call_with_retry(
        self, 
        func: Callable[[], T], 
        operation_name: str,
        max_retries: int = 3,
        initial_delay: float = 2.0
    ) -> T:
        """带重试机制的API调用"""
        last_exception = None
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"{operation_name} 第 {attempt + 1} 次尝试失败: {str(e)[:100]}, "
                        f"{delay:.1f}秒后重试..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"{operation_name} 在 {max_retries} 次尝试后仍失败: {str(e)}")
        
        raise last_exception
    
    def _fetch_from_neo4j(self, graph_id: str = ""):
        """直接通过 Neo4j Cypher 获取所有节点和边，按 group_id 过滤"""
        async def _query():
            driver = get_neo4j_async_driver()
            gid_filter = "WHERE n.group_id = $gid OR n.group_id IS NULL" if graph_id else ""
            node_result = await driver.execute_query(
                f"MATCH (n:Entity) {gid_filter} "
                "RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary, "
                "n.created_at AS created_at",
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
                "a.uuid AS src_uuid, b.uuid AS tgt_uuid",
                gid=graph_id,
                database_=Config.NEO4J_DATABASE,
            )
            return node_result.records, edge_result.records

        return run_async(_query())

    def _infer_entity_types(self, node_records, edge_records) -> dict:
        """
        推断每个节点的 entity type。
        
        策略：
        1. 识别 ontology 类型定义节点（summary 含 '属性:' 模式）
        2. 通过边连接关系传播类型到实例节点
        3. 通过 summary 关键词匹配兜底
        """
        node_summaries = {}
        for rec in node_records:
            name = rec["name"] or ""
            node_summaries[name] = rec["summary"] or ""

        # 识别类型定义节点
        type_names = set()
        for name, summary in node_summaries.items():
            if summary and "属性:" in summary and len(summary) > 30:
                type_names.add(name)

        # 通过边传播类型
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

        # summary 关键词兜底
        for name, summary in node_summaries.items():
            if name in type_names or name in node_type_map:
                continue
            for tn in type_names:
                if tn.lower() in summary.lower():
                    node_type_map[name] = tn
                    break

        return {"type_names": type_names, "node_type_map": node_type_map}

    def _get_labels(self, name: str, type_info: dict) -> List[str]:
        """根据推断结果返回节点 labels"""
        if name in type_info["type_names"]:
            return ["Entity", name]
        entity_type = type_info["node_type_map"].get(name)
        if entity_type:
            return ["Entity", entity_type]
        return ["Entity"]

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        获取图谱的所有节点（直接 Neo4j Cypher 查询 + entity type 推断）
        """
        logger.info(f"获取图谱 {graph_id} 的所有节点...")
        try:
            node_records, edge_records = self._fetch_from_neo4j(graph_id)
        except Exception as e:
            logger.warning(f"获取节点失败: {e}")
            return []

        type_info = self._infer_entity_types(node_records, edge_records)

        nodes_data = []
        for rec in node_records:
            name = rec["name"] or ""
            nodes_data.append({
                "uuid": str(rec["uuid"] or ""),
                "name": name,
                "labels": self._get_labels(name, type_info),
                "summary": rec["summary"] or "",
                "attributes": {},
            })

        logger.info(f"共获取 {len(nodes_data)} 个节点")
        return nodes_data

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """
        获取图谱的所有边（直接 Neo4j Cypher 查询）
        """
        logger.info(f"获取图谱 {graph_id} 的所有边...")
        try:
            _, edge_records = self._fetch_from_neo4j(graph_id)
        except Exception as e:
            logger.warning(f"获取边失败: {e}")
            return []

        edges_data = []
        for rec in edge_records:
            edges_data.append({
                "uuid": str(rec["uuid"] or ""),
                "name": rec["name"] or rec["rel_type"] or "",
                "fact": rec["fact"] or "",
                "source_node_uuid": str(rec["source_uuid"] or rec["src_uuid"] or ""),
                "target_node_uuid": str(rec["target_uuid"] or rec["tgt_uuid"] or ""),
                "attributes": {},
            })

        logger.info(f"共获取 {len(edges_data)} 条边")
        return edges_data
    
    def get_node_edges(self, node_uuid: str, graph_id: str = "") -> List[Dict[str, Any]]:
        """
        获取指定节点的所有相关边
        
        Args:
            node_uuid: 节点UUID
            graph_id: 图谱ID（Graphiti 需要通过 graph_id 获取实例）
            
        Returns:
            边列表
        """
        if not graph_id:
            logger.warning(f"get_node_edges: 未提供 graph_id，无法获取节点边")
            return []
        
        try:
            all_edges = self.get_all_edges(graph_id)
            return [
                e for e in all_edges 
                if e["source_node_uuid"] == node_uuid or e["target_node_uuid"] == node_uuid
            ]
        except Exception as e:
            logger.warning(f"获取节点 {node_uuid} 的边失败: {str(e)}")
            return []
    
    def filter_defined_entities(
        self, 
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> FilteredEntities:
        """
        筛选出符合预定义实体类型的节点
        
        筛选逻辑：
        - 如果节点的Labels只有一个"Entity"，说明这个实体不符合我们预定义的类型，跳过
        - 如果节点的Labels包含除"Entity"和"Node"之外的标签，说明符合预定义类型，保留
        
        Args:
            graph_id: 图谱ID
            defined_entity_types: 预定义的实体类型列表（可选，如果提供则只保留这些类型）
            enrich_with_edges: 是否获取每个实体的相关边信息
            
        Returns:
            FilteredEntities: 过滤后的实体集合
        """
        logger.info(f"开始筛选图谱 {graph_id} 的实体...")
        
        # 获取所有节点
        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)
        
        # 获取所有边（用于后续关联查找）
        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []
        
        # 构建节点UUID到节点数据的映射
        node_map = {n["uuid"]: n for n in all_nodes}
        
        # 筛选符合条件的实体
        filtered_entities = []
        entity_types_found = set()
        
        for node in all_nodes:
            labels = node.get("labels", [])
            
            # 筛选逻辑：优先使用除"Entity"和"Node"之外的标签
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]
            
            # 如果指定了预定义类型，检查是否匹配
            if defined_entity_types and custom_labels:
                matching_labels = [l for l in custom_labels if l in defined_entity_types]
                if not matching_labels:
                    continue
                entity_type = matching_labels[0]
            elif custom_labels:
                entity_type = custom_labels[0]
            else:
                # 无自定义标签时，使用通用类型（不跳过）
                entity_type = "Entity"
            
            entity_types_found.add(entity_type)
            
            # 创建实体节点对象
            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )
            
            # 获取相关边和节点
            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()
                
                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])
                
                entity.related_edges = related_edges
                
                # 获取关联节点的基本信息
                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append({
                            "uuid": related_node["uuid"],
                            "name": related_node["name"],
                            "labels": related_node["labels"],
                            "summary": related_node.get("summary", ""),
                        })
                
                entity.related_nodes = related_nodes
            
            filtered_entities.append(entity)
        
        logger.info(f"筛选完成: 总节点 {total_count}, 符合条件 {len(filtered_entities)}, "
                   f"实体类型: {entity_types_found}")
        
        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )
    
    def get_entity_with_context(
        self, 
        graph_id: str, 
        entity_uuid: str
    ) -> Optional[EntityNode]:
        """
        获取单个实体及其完整上下文（边和关联节点）
        
        Args:
            graph_id: 图谱ID
            entity_uuid: 实体UUID
            
        Returns:
            EntityNode或None
        """
        try:
            # 获取所有节点和边
            all_nodes = self.get_all_nodes(graph_id)
            node_map = {n["uuid"]: n for n in all_nodes}
            
            # 找到目标节点
            node = node_map.get(entity_uuid)
            if not node:
                return None
            
            # 获取节点的边
            edges = self.get_node_edges(entity_uuid, graph_id=graph_id)
            
            # 处理相关边和节点
            related_edges = []
            related_node_uuids = set()
            
            for edge in edges:
                if edge["source_node_uuid"] == entity_uuid:
                    related_edges.append({
                        "direction": "outgoing",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "target_node_uuid": edge["target_node_uuid"],
                    })
                    related_node_uuids.add(edge["target_node_uuid"])
                else:
                    related_edges.append({
                        "direction": "incoming",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "source_node_uuid": edge["source_node_uuid"],
                    })
                    related_node_uuids.add(edge["source_node_uuid"])
            
            # 获取关联节点信息
            related_nodes = []
            for related_uuid in related_node_uuids:
                if related_uuid in node_map:
                    related_node = node_map[related_uuid]
                    related_nodes.append({
                        "uuid": related_node["uuid"],
                        "name": related_node["name"],
                        "labels": related_node["labels"],
                        "summary": related_node.get("summary", ""),
                    })
            
            return EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=node["labels"],
                summary=node["summary"],
                attributes=node["attributes"],
                related_edges=related_edges,
                related_nodes=related_nodes,
            )
            
        except Exception as e:
            logger.error(f"获取实体 {entity_uuid} 失败: {str(e)}")
            return None
    
    def get_entities_by_type(
        self, 
        graph_id: str, 
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        """
        获取指定类型的所有实体
        
        Args:
            graph_id: 图谱ID
            entity_type: 实体类型（如 "Student", "PublicFigure" 等）
            enrich_with_edges: 是否获取相关边信息
            
        Returns:
            实体列表
        """
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities


