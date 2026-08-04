"""
爬虫基类 - 提供通用的爬虫功能
所有平台爬虫继承此类
"""

import time
import random
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Generator
from urllib.parse import urljoin, urlparse

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crawler")


class BaseCrawler(ABC):
    """爬虫基类"""

    PLATFORM_NAME = "base"
    BASE_URL = ""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]

    def __init__(self, delay_min: float = 2.0, delay_max: float = 5.0):
        self.session = requests.Session()
        self.delay_min = delay_min
        self.delay_max = delay_max
        self._seen_ids = set()

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def _sleep(self):
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)

    def _request(self, url: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        try:
            kwargs.setdefault("headers", self.headers)
            response = self.session.request(method, url, timeout=15, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.warning(f"请求失败 [{url}]: {e}")
            return None

    @abstractmethod
    def search(self, keyword: str, max_results: int = 20) -> List[Dict]:
        """
        搜索谱子资源
        返回: [{"title": "", "url": "", "uploader": "", "duration": "", ...}]
        """
        pass

    @abstractmethod
    def get_download_links(self, resource_url: str) -> List[Dict]:
        """
        从资源页面提取下载链接
        返回: [{"url": "", "filename": "", "type": "adofai|zip|rar|..."}]
        """
        pass

    @abstractmethod
    def extract_metadata(self, resource_url: str) -> Dict:
        """
        提取资源元数据
        返回: {"title": "", "artist": "", "chart_author": "", "difficulty": 0, ...}
        """
        pass

    def crawl(self, keywords: List[str], max_items: int = 10) -> List[Dict]:
        """
        完整爬取流程
        """
        results = []

        for keyword in keywords:
            logger.info(f"[{self.PLATFORM_NAME}] 搜索: {keyword}")

            try:
                search_results = self.search(keyword, max_results=max_items)
            except Exception as e:
                logger.error(f"搜索异常: {e}")
                continue

            for item in search_results:
                if len(results) >= max_items:
                    break

                try:
                    item_id = self._make_item_id(item.get("url", ""))
                    if item_id in self._seen_ids:
                        continue
                    self._seen_ids.add(item_id)

                    download_links = self.get_download_links(item["url"])
                    if not download_links:
                        logger.info(f"跳过无下载链接的资源: {item.get('title', '')}")
                        self._sleep()
                        continue

                    metadata = self.extract_metadata(item["url"])
                    if not metadata:
                        metadata = item

                    results.append({
                        "platform": self.PLATFORM_NAME,
                        "resource": item,
                        "download_links": download_links,
                        "metadata": metadata,
                    })

                    self._sleep()
                except Exception as e:
                    logger.error(f"处理资源异常 [{item.get('url', '')}]: {e}")
                    continue

            if len(results) >= max_items:
                break

            self._sleep()

        return results

    def _make_item_id(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
