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

# 官方/学术/政策源域名
CHINESE_OFFICIAL_DOMAINS = [
    "gov.cn",
    "edu.cn",
    "ac.cn",
    "cnki.net",
    "wanfangdata.com.cn",
    "cssn.cn",
    "people.com.cn",
    "xinhuanet.com",
    "gmw.cn",
    "chinanews.com.cn",
]

# 需要官方源的意图关键词
_OFFICIAL_INTENT_KEYWORDS = re.compile(
    r'未来发展|战略规划|发展方向|十四五|双一流|学科建设|人才引进|'
    r'招生政策|科研成果|发展战略|办学|规划|建设|政策|改革'
)


def _contains_chinese(text: str) -> bool:
    """检测字符串中是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def _extract_subject(query: str) -> str:
    """
    从查询中提取核心主体（如 '武汉大学舆论' → '武汉大学'）。
    用于相关性过滤：搜索结果的 title 或 content 中必须包含该主体。
    """
    # 去掉常见的修饰词/意图词，剩下的就是主体
    noise_words = [
        '的', '以前的', '最近的', '未来', '当前',
        '舆论', '舆情', '新闻', '热点', '争议', '事件', '讨论',
        '发展', '规划', '战略', '建设', '改革', '政策',
        '分析', '研究', '信息', '资料', '数据',
    ]
    subject = query.strip()
    for w in noise_words:
        subject = subject.replace(w, '')
    subject = subject.strip()
    # 如果去完后太短，回退到原 query 的前几个字
    if len(subject) < 2:
        subject = re.sub(r'[的了吗呢吧]', '', query)[:6]
    return subject


def _is_relevant(title: str, content: str, subject: str) -> bool:
    """
    检查搜索结果是否与核心主体相关。
    title 或 content 中必须至少出现一次主体关键词。
    """
    if not subject:
        return True
    text = (title + " " + content).lower()
    return subject.lower() in text


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
                # 提取核心主体用于相关性过滤
                subject = _extract_subject(query)
                logger.info(f"[中文搜索] 核心主体='{subject}', query='{query}'")

                # 判断是否需要官方/学术源
                use_official = bool(_OFFICIAL_INTENT_KEYWORDS.search(query + simulation_requirement))
                
                # 选择域名列表
                if include_domains:
                    cn_domains = include_domains
                elif use_official:
                    cn_domains = CHINESE_OFFICIAL_DOMAINS + CHINESE_PREFERRED_DOMAINS[:5]
                else:
                    cn_domains = CHINESE_PREFERRED_DOMAINS

                # ── 轮次 1：中文站点搜索（带 include_domains）──
                logger.info(f"[中文搜索-轮次1] query='{query}', 域名={'官方+舆情' if use_official else '舆情'}, max={max_results}")
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
                    req_short = simulation_requirement[:50].strip()
                    combined_query = f"{subject} {req_short}"
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

                # ── 轮次 3：新闻搜索补充时效性内容（强制带主体）──
                if len(all_results) < max_results:
                    news_query = f"{subject} 新闻 事件" if subject != query else query
                    logger.info(f"[中文搜索-轮次3] query='{news_query}', 新闻搜索补充")
                    try:
                        resp3 = self._single_search(
                            client, query=news_query,
                            max_results=max_results - len(all_results),
                            search_depth="basic",
                            topic="news",
                        )
                        _merge(resp3.get("results", []))
                    except Exception as e:
                        logger.warning(f"新闻搜索失败: {e}")

                # ── 相关性过滤：丢弃与核心主体无关的结果 ──
                if subject:
                    before = len(all_results)
                    all_results = [
                        r for r in all_results
                        if _is_relevant(r.get("title", ""), r.get("content", ""), subject)
                    ]
                    dropped = before - len(all_results)
                    if dropped > 0:
                        logger.info(f"[相关性过滤] 移除 {dropped} 条与'{subject}'无关的结果")

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
