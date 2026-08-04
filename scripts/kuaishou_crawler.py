"""
快手爬虫 - 基础框架
待完善: 快手 API 需要特殊签名处理
"""

import re
import json
import logging
from typing import List, Dict
from base_crawler import BaseCrawler

logger = logging.getLogger("kuaishou")


class KuaishouCrawler(BaseCrawler):
    PLATFORM_NAME = "kuaishou"
    BASE_URL = "https://www.kuaishou.com"

    DEFAULT_KEYWORDS = [
        "冰与火之舞 谱子",
        "ADOFAI 自制谱",
    ]

    def __init__(self, cookie: str = "", delay_min: float = 3.0, delay_max: float = 6.0):
        super().__init__(delay_min=delay_min, delay_max=delay_max)
        if cookie:
            self.session.headers.update({"Cookie": cookie})

    def search(self, keyword: str, max_results: int = 20) -> List[Dict]:
        url = f"{self.BASE_URL}/search"
        response = self._request(url, params={"keyword": keyword})

        if not response:
            return []

        items = []
        try:
            data = response.json()
            results = data.get("data", {}).get("results", [])
            for r in results[:max_results]:
                items.append({
                    "title": r.get("title", ""),
                    "url": f"https://www.kuaishou.com/short-video/{r.get('id', '')}",
                    "uploader": r.get("user_name", ""),
                    "description": r.get("description", ""),
                })
        except (json.JSONDecodeError, KeyError):
            pass

        return items

    def get_download_links(self, resource_url: str) -> List[Dict]:
        links = []
        response = self._request(resource_url)
        if not response:
            return links

        text = response.text
        patterns = [
            r'https?://[^\s"\'<>)]+\.(?:adofai|zip|rar|7z)',
            r'https?://pan\.baidu\.com/[^\s"\'<>)]+',
            r'https?://(?:www\.)?aliyundrive\.com/[^\s"\'<>)]+',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                links.append({
                    "url": match.group(0),
                    "filename": "download",
                    "type": "unknown",
                })

        return links

    def extract_metadata(self, resource_url: str) -> Dict:
        return {"platform": "kuaishou", "source_url": resource_url}

    def run_default(self, max_items: int = 3) -> List[Dict]:
        return self.crawl(self.DEFAULT_KEYWORDS, max_items=max_items)
