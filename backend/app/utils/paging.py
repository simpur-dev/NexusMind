"""分页读取工具（已弃用）。

已迁移到 Graphiti + Neo4j，不再需要此模块。
保留文件以避免其他地方的残留导入报错。

请使用 graphiti_client.py 中的工具函数替代。
"""

from .logger import get_logger

logger = get_logger('nexusmind.paging')


def fetch_all_nodes(*args, **kwargs):
    """已弃用：请使用 graphiti_client 替代"""
    logger.warning("fetch_all_nodes 已弃用，请使用 Graphiti 替代")
    return []


def fetch_all_edges(*args, **kwargs):
    """已弃用：请使用 graphiti_client 替代"""
    logger.warning("fetch_all_edges 已弃用，请使用 Graphiti 替代")
    return []
