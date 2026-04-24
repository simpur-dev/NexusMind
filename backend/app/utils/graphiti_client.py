"""
Graphiti 客户端工具模块

封装 Graphiti + Neo4j 的连接管理和 async/sync 桥接。
封装 Neo4j 图数据库的连接管理。

后端数据库默认使用 Neo4j（Windows 原生支持）。
如需切换数据库，只需修改 _get_driver() 函数即可。

用法:
    from ..utils.graphiti_client import get_graphiti, run_async

    graphiti = get_graphiti("my_graph_id")
    results = run_async(graphiti.search("query"))
"""

import asyncio
import os
import threading
from typing import Any, Optional

from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

from ..config import Config
from .logger import get_logger

# DashScope embedding API 限制单次批量不超过 10 条
DASHSCOPE_EMBEDDING_BATCH_SIZE = 10


class BatchedOpenAIEmbedder(OpenAIEmbedder):
    """分批处理的 Embedder，兼容 DashScope 等有 batch size 限制的 API"""

    async def create_batch(self, input_data: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(input_data), DASHSCOPE_EMBEDDING_BATCH_SIZE):
            chunk = input_data[i:i + DASHSCOPE_EMBEDDING_BATCH_SIZE]
            chunk_results = await super().create_batch(chunk)
            results.extend(chunk_results)
        return results

logger = get_logger('nexusmind.graphiti_client')

# 缓存 Graphiti 实例 (graph_id -> Graphiti)
_instances: dict[str, Graphiti] = {}
_lock = threading.Lock()


def _get_neo4j_driver() -> Neo4jDriver:
    """创建 Neo4j 驱动"""
    return Neo4jDriver(
        uri=Config.NEO4J_URI,
        user=Config.NEO4J_USERNAME,
        password=Config.NEO4J_PASSWORD,
        database=Config.NEO4J_DATABASE,
    )


def _build_llm_client() -> OpenAIGenericClient:
    """创建 LLM 客户端（使用 Chat Completions API，兼容 DashScope 等非 OpenAI 服务）"""
    llm_config = LLMConfig(
        api_key=Config.GRAPHITI_OPENAI_API_KEY,
        base_url=Config.LLM_BASE_URL,
        model=Config.LLM_MODEL_NAME,
        small_model=Config.LLM_MODEL_NAME,
    )
    return OpenAIGenericClient(config=llm_config)


def _build_embedder() -> BatchedOpenAIEmbedder:
    """创建 Embedding 客户端（自动分批，兼容 DashScope 等有 batch 限制的 API）"""
    embedder_config = OpenAIEmbedderConfig(
        embedding_model=Config.EMBEDDING_MODEL,
        api_key=Config.GRAPHITI_OPENAI_API_KEY,
        base_url=Config.LLM_BASE_URL,
    )
    return BatchedOpenAIEmbedder(config=embedder_config)


def get_graphiti(graph_id: str) -> Graphiti:
    """
    获取或创建 Graphiti 实例。
    
    每个 graph_id 对应一个 Graphiti 实例。
    实例会被缓存复用。
    
    Args:
        graph_id: 图谱ID
        
    Returns:
        Graphiti 实例
    """
    with _lock:
        if graph_id not in _instances:
            logger.info(f"创建 Graphiti 实例: graph_id={graph_id}")
            
            # cross_encoder 等组件会从环境变量读取 API key
            if Config.GRAPHITI_OPENAI_API_KEY:
                os.environ['OPENAI_API_KEY'] = Config.GRAPHITI_OPENAI_API_KEY
            if Config.LLM_BASE_URL:
                os.environ['OPENAI_BASE_URL'] = Config.LLM_BASE_URL
            
            driver = _get_neo4j_driver()
            llm_client = _build_llm_client()
            embedder = _build_embedder()
            
            graphiti = Graphiti(
                graph_driver=driver,
                llm_client=llm_client,
                embedder=embedder,
            )
            _instances[graph_id] = graphiti
            
        return _instances[graph_id]


def create_fresh_graphiti(graph_id: str) -> Graphiti:
    """
    创建一个全新的 Graphiti 实例（不缓存），用于需要独立生命周期的场景。
    调用方负责关闭。
    """
    driver = _get_neo4j_driver()
    llm_client = _build_llm_client()
    embedder = _build_embedder()
    return Graphiti(graph_driver=driver, llm_client=llm_client, embedder=embedder)


def remove_instance(graph_id: str):
    """从缓存中移除并关闭 Graphiti 实例"""
    with _lock:
        if graph_id in _instances:
            try:
                run_async(_instances[graph_id].close())
            except Exception as e:
                logger.warning(f"关闭 Graphiti 实例失败: {e}")
            del _instances[graph_id]


def close_all():
    """关闭所有缓存的 Graphiti 实例"""
    with _lock:
        for gid, instance in list(_instances.items()):
            try:
                run_async(instance.close())
            except Exception as e:
                logger.warning(f"关闭 Graphiti 实例 {gid} 失败: {e}")
        _instances.clear()
    logger.info("已关闭所有 Graphiti 实例")


# ---- 共享 Neo4j 异步驱动（连接池复用） ----
_neo4j_async_driver = None
_neo4j_driver_lock = threading.Lock()


def get_neo4j_async_driver():
    """获取共享的 Neo4j AsyncDriver 单例（自带连接池，线程安全）"""
    global _neo4j_async_driver
    with _neo4j_driver_lock:
        if _neo4j_async_driver is None:
            from neo4j import AsyncGraphDatabase
            _neo4j_async_driver = AsyncGraphDatabase.driver(
                Config.NEO4J_URI,
                auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD),
            )
            logger.info("创建共享 Neo4j AsyncDriver（连接池复用）")
    return _neo4j_async_driver


_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_loop_lock = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """确保有一个持久化的后台 event loop（线程安全）。"""
    global _loop, _loop_thread
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()

            def _run_loop():
                asyncio.set_event_loop(_loop)
                _loop.run_forever()

            _loop_thread = threading.Thread(target=_run_loop, daemon=True)
            _loop_thread.start()
    return _loop


def run_async(coro, timeout: float = 30) -> Any:
    """
    在同步上下文中运行 async 协程。

    使用持久化的后台 event loop，保证 Neo4j 等 async 连接
    在多次调用间保持活跃（不会因 loop 关闭而断开）。

    Args:
        coro: 要运行的协程
        timeout: 超时秒数，防止 Neo4j 不可用时无限阻塞（默认 30s）
    """
    loop = _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)


def run_async_batch(coros: list, max_concurrency: int = 3) -> list:
    """
    并发运行多个 async 协程，返回结果列表（保持顺序）。
    
    通过 semaphore 控制最大并发数，避免 DashScope API 限流。
    """
    loop = _ensure_loop()

    async def _gather():
        sem = asyncio.Semaphore(max_concurrency)

        async def _limited(coro):
            async with sem:
                return await coro

        return await asyncio.gather(*[_limited(c) for c in coros])

    future = asyncio.run_coroutine_threadsafe(_gather(), loop)
    return future.result(timeout=120)
