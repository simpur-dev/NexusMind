"""
网络搜索服务：根据关键词自动抓取公开舆情信息作为种子材料。

使用 Tavily Search API（专为 AI Agent 设计的搜索引擎），
返回干净的文本摘要，无需自行解析 HTML。

环境变量：
    TAVILY_API_KEY: Tavily API 密钥（https://tavily.com 免费注册）
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 中文新闻/舆情优先域名
CHINESE_PREFERRED_DOMAINS = [
    "zhihu.com",
    "weibo.com",
    "baidu.com",
    "sina.com.cn",
    "sohu.com",
    "163.com",
    "qq.com",
    "thepaper.cn",
    "36kr.com",
    "jiemian.com",
    "caixin.com",
    "people.com.cn",
    "xinhuanet.com",
    "chinanews.com.cn",
    "guancha.cn",
    "huxiu.com",
    "ifeng.com",
    "bilibili.com",
    "douban.com",
    "toutiao.com",
]


def _contains_chinese(text: str) -> bool:
    """检测字符串中是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


class WebScraperService:
    """网络搜索与内容抓取服务"""

    def __init__(self):
        self.api_key = os.environ.get("TAVILY_API_KEY", "")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY 未设置，网络搜索功能不可用")

    def is_available(self) -> bool:
        """检查服务是否可用（API Key 已配置）"""
        return bool(self.api_key)

    def _single_search(
        self,
        client,
        query: str,
        max_results: int = 8,
        search_depth: str = "advanced",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        topic: str = "general",
        include_answer: bool = False,
    ) -> Dict[str, Any]:
        """执行单次 Tavily 搜索"""
        search_params = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "topic": topic,
            "include_answer": include_answer,
        }
        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains

        return client.search(**search_params)

    def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        topic: str = "general",
        simulation_requirement: str = "",
    ) -> Dict[str, Any]:
        """
        执行网络搜索，返回结构化结果。
        
        对中文查询自动执行多轮搜索策略：
        1. 在中文站点上搜索原始 query
        2. 使用 query + simulation_requirement 组合搜索
        3. 去重合并结果

        Args:
            query: 搜索关键词（支持中文）
            max_results: 最大返回结果数（默认 10）
            search_depth: 搜索深度，"basic" 或 "advanced"
            include_domains: 限定搜索域名列表（可选）
            exclude_domains: 排除域名列表（可选）
            topic: 搜索主题类型，"general" 或 "news"
            simulation_requirement: 模拟需求描述（可选，用于增强搜索相关性）

        Returns:
            搜索结果字典
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "TAVILY_API_KEY 未配置，请在 .env 中设置",
                "results": [],
            }

        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self.api_key)

            is_chinese = _contains_chinese(query)
            all_results = []
            seen_urls = set()
            answer = ""

            def _merge(items):
                for item in items:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": item.get("title", ""),
                            "url": url,
                            "content": item.get("content", ""),
                            "score": item.get("score", 0.0),
                        })

            if is_chinese:
                # ── 轮次 1：中文站点搜索（带 include_domains）──
                cn_domains = include_domains or CHINESE_PREFERRED_DOMAINS
                logger.info(f"[中文搜索-轮次1] query='{query}', 中文域名限定, max={max_results}")
                try:
                    resp1 = self._single_search(
                        client, query=query,
                        max_results=max_results,
                        search_depth=search_depth,
                        include_domains=cn_domains,
                        topic="general",
                        include_answer=True,
                    )
                    _merge(resp1.get("results", []))
                    answer = resp1.get("answer", "")
                except Exception as e:
                    logger.warning(f"中文域名搜索失败，回退到通用搜索: {e}")

                # ── 轮次 2：带模拟需求的精准搜索 ──
                if simulation_requirement:
                    # 截取需求前50字组合查询
                    req_short = simulation_requirement[:50].strip()
                    combined_query = f"{query} {req_short}"
                    logger.info(f"[中文搜索-轮次2] query='{combined_query}', 通用搜索")
                    try:
                        resp2 = self._single_search(
                            client, query=combined_query,
                            max_results=max_results,
                            search_depth=search_depth,
                            topic="general",
                            include_answer=not answer,
                        )
                        _merge(resp2.get("results", []))
                        if not answer:
                            answer = resp2.get("answer", "")
                    except Exception as e:
                        logger.warning(f"组合搜索失败: {e}")

                # ── 轮次 3：新闻搜索补充时效性内容 ──
                if len(all_results) < max_results:
                    logger.info(f"[中文搜索-轮次3] query='{query}', 新闻搜索补充")
                    try:
                        resp3 = self._single_search(
                            client, query=query,
                            max_results=max_results - len(all_results),
                            search_depth="basic",
                            topic="news",
                        )
                        _merge(resp3.get("results", []))
                    except Exception as e:
                        logger.warning(f"新闻搜索失败: {e}")

            else:
                # ── 非中文：单次搜索 ──
                logger.info(f"执行网络搜索: query='{query}', max_results={max_results}")
                resp = self._single_search(
                    client, query=query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                    topic=topic,
                    include_answer=True,
                )
                _merge(resp.get("results", []))
                answer = resp.get("answer", "")

            logger.info(f"搜索完成: 共 {len(all_results)} 条去重结果")

            return {
                "success": True,
                "query": query,
                "results": all_results,
                "answer": answer,
                "total_results": len(all_results),
                "search_time": datetime.now().isoformat(),
            }

        except ImportError:
            logger.error("tavily-python 未安装，请运行: uv add tavily-python")
            return {
                "success": False,
                "error": "tavily-python 未安装",
                "results": [],
            }
        except Exception as e:
            logger.error(f"网络搜索失败: {str(e)}")
            return {
                "success": False,
                "error": f"搜索失败: {str(e)}",
                "results": [],
            }

    def search_to_document_texts(
        self,
        query: str,
        max_results: int = 8,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        搜索并将结果转换为文档文本列表，可直接传入 OntologyGenerator.generate()。

        Returns:
            {
                "success": True/False,
                "document_texts": ["text1", "text2", ...],
                "all_text": "合并后的全文",
                "sources": [{"title": str, "url": str}],
                "answer": str,
                "error": str (if failed),
            }
        """
        search_result = self.search(query=query, max_results=max_results, **kwargs)

        if not search_result["success"]:
            return {
                "success": False,
                "document_texts": [],
                "all_text": "",
                "sources": [],
                "error": search_result.get("error", "搜索失败"),
            }

        results = search_result["results"]
        if not results:
            return {
                "success": False,
                "document_texts": [],
                "all_text": "",
                "sources": [],
                "error": f"未找到与 '{query}' 相关的内容",
            }

        document_texts = []
        sources = []
        all_text_parts = []

        for item in results:
            title = item.get("title", "未知来源")
            url = item.get("url", "")
            content = item.get("content", "").strip()

            if not content:
                continue

            # 每条结果作为一个独立的 "文档"
            doc_text = f"【{title}】\n来源: {url}\n\n{content}"
            document_texts.append(doc_text)
            sources.append({"title": title, "url": url})
            all_text_parts.append(f"\n\n=== {title} ({url}) ===\n{content}")

        # 如果有 Tavily 的摘要回答，也作为文档加入
        answer = search_result.get("answer", "")
        if answer:
            summary_doc = f"【AI 综合摘要】\n搜索词: {query}\n\n{answer}"
            document_texts.insert(0, summary_doc)
            all_text_parts.insert(0, f"\n\n=== AI 综合摘要 ===\n{answer}")

        all_text = "".join(all_text_parts)

        logger.info(
            f"搜索结果已转换为文档: {len(document_texts)} 篇, "
            f"总字符数 {len(all_text)}"
        )

        return {
            "success": True,
            "document_texts": document_texts,
            "all_text": all_text,
            "sources": sources,
            "answer": answer,
            "total_sources": len(sources),
        }
