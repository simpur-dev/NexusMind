"""
向量 RAG 存储与检索服务

使用 Neo4j 5.x 内置向量索引，将文档切块的 embedding 存入 Neo4j，
检索时与 GraphRAG（Graphiti 图谱检索）互补，实现双路召回。

核心流程：
1. 图谱构建时：对每个文档 chunk 生成 embedding，存为 DocumentChunk 节点
2. 报告生成时：对查询做 embedding，通过 Neo4j 向量索引检索 top-K 相似片段
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..config import Config
from ..utils.logger import get_logger
from ..utils.graphiti_client import (
    run_async,
    get_neo4j_async_driver,
    _build_embedder,
)

logger = get_logger('nexusmind.vector_store')

# Neo4j 向量索引名称
VECTOR_INDEX_NAME = "document_chunk_embedding"
SIMILARITY_METRIC = "cosine"


@dataclass
class VectorSearchResult:
    """向量检索结果"""
    chunk_text: str
    chunk_index: int
    score: float
    graph_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_text": self.chunk_text,
            "chunk_index": self.chunk_index,
            "score": round(self.score, 4),
            "graph_id": self.graph_id,
        }


class VectorStore:
    """Neo4j 向量存储服务"""

    def __init__(self):
        self._embedder = None

    @property
    def embedder(self):
        """延迟初始化 embedder（复用 Graphiti 的 embedder 配置）"""
        if self._embedder is None:
            self._embedder = _build_embedder()
        return self._embedder

    # ========== 索引管理 ==========

    def ensure_vector_index(self, dimension: int):
        """确保 Neo4j 向量索引存在，不存在则创建。"""
        async def _ensure():
            driver = get_neo4j_async_driver()
            result = await driver.execute_query(
                "SHOW INDEXES YIELD name WHERE name = $name RETURN name",
                name=VECTOR_INDEX_NAME,
                database_=Config.NEO4J_DATABASE,
            )
            if result.records:
                logger.debug(f"向量索引 {VECTOR_INDEX_NAME} 已存在")
                return

            await driver.execute_query(
                f"CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS "
                "FOR (c:DocumentChunk) ON (c.embedding) "
                "OPTIONS {indexConfig: {"
                f"  `vector.dimensions`: {dimension},"
                f"  `vector.similarity_function`: '{SIMILARITY_METRIC}'"
                "}}",
                database_=Config.NEO4J_DATABASE,
            )
            logger.info(f"创建向量索引: {VECTOR_INDEX_NAME}, dimension={dimension}")

        run_async(_ensure())

    # ========== 写入 ==========

    def store_chunks(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 10,
        progress_callback=None,
    ):
        """
        将文档 chunks 生成 embedding 并存入 Neo4j。

        Args:
            graph_id: 图谱 ID（用于数据隔离）
            chunks: 文本块列表
            batch_size: 每批处理的 chunk 数量
            progress_callback: 进度回调 (message, progress_ratio)
        """
        total = len(chunks)
        if total == 0:
            return

        logger.info(f"开始存储 {total} 个文档 chunks 的 embedding (graph_id={graph_id})")
        start_time = time.time()

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_chunks = chunks[batch_start:batch_end]

            if progress_callback:
                progress_callback(
                    f"向量化文档片段 {batch_start + 1}-{batch_end}/{total}...",
                    batch_start / total,
                )

            # 生成 embedding
            embeddings = run_async(self.embedder.create_batch(batch_chunks))

            # 第一批时确保索引存在
            if batch_start == 0 and embeddings:
                self.ensure_vector_index(len(embeddings[0]))

            # 写入 Neo4j
            self._write_batch(graph_id, batch_chunks, embeddings, batch_start)

        elapsed = time.time() - start_time
        logger.info(f"向量存储完成: {total} chunks, 耗时 {elapsed:.1f}s")

    def _write_batch(
        self,
        graph_id: str,
        texts: List[str],
        embeddings: List[List[float]],
        start_index: int,
    ):
        """将一批 chunk 节点写入 Neo4j"""
        async def _write():
            driver = get_neo4j_async_driver()
            for i, (text, emb) in enumerate(zip(texts, embeddings)):
                chunk_idx = start_index + i
                chunk_uuid = f"chunk_{graph_id}_{chunk_idx:04d}"
                await driver.execute_query(
                    "MERGE (c:DocumentChunk {uuid: $uuid}) "
                    "SET c.text = $text, "
                    "    c.embedding = $embedding, "
                    "    c.chunk_index = $chunk_index, "
                    "    c.graph_id = $graph_id",
                    uuid=chunk_uuid,
                    text=text,
                    embedding=emb,
                    chunk_index=chunk_idx,
                    graph_id=graph_id,
                    database_=Config.NEO4J_DATABASE,
                )

        run_async(_write())

    # ========== 检索 ==========

    def search(
        self,
        graph_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[VectorSearchResult]:
        """
        向量语义检索：对 query 做 embedding，在 Neo4j 中检索最相似的文档片段。

        Args:
            graph_id: 图谱 ID
            query: 搜索查询
            top_k: 返回 top-K 结果

        Returns:
            按相似度降序排列的检索结果
        """
        logger.info(f"向量检索: query={query[:50]}..., top_k={top_k}")

        # 生成 query embedding
        query_embedding = run_async(self.embedder.create_batch([query]))[0]

        async def _search():
            driver = get_neo4j_async_driver()
            result = await driver.execute_query(
                "CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding) "
                "YIELD node, score "
                "WHERE node.graph_id = $graph_id "
                "RETURN node.text AS text, node.chunk_index AS chunk_index, score "
                "ORDER BY score DESC",
                index_name=VECTOR_INDEX_NAME,
                top_k=top_k * 2,
                query_embedding=query_embedding,
                graph_id=graph_id,
                database_=Config.NEO4J_DATABASE,
            )
            return result.records

        try:
            records = run_async(_search())
        except Exception as e:
            logger.warning(f"向量检索失败: {e}")
            return []

        results = []
        for rec in records[:top_k]:
            results.append(VectorSearchResult(
                chunk_text=rec["text"] or "",
                chunk_index=rec["chunk_index"] or 0,
                score=float(rec["score"] or 0),
                graph_id=graph_id,
            ))

        logger.info(f"向量检索完成: 找到 {len(results)} 个相关片段")
        return results

    # ========== 清理 ==========

    def delete_chunks(self, graph_id: str):
        """删除指定图谱的所有向量 chunks"""
        async def _delete():
            driver = get_neo4j_async_driver()
            await driver.execute_query(
                "MATCH (c:DocumentChunk {graph_id: $graph_id}) DETACH DELETE c",
                graph_id=graph_id,
                database_=Config.NEO4J_DATABASE,
            )

        run_async(_delete())
        logger.info(f"已删除 graph_id={graph_id} 的向量 chunks")
