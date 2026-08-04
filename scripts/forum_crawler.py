"""
通用爬虫 - 支持从各大论坛、博客、个人网站抓取 ADOFAI 谱子
支持自定义种子 URL 列表
"""

import re
import json
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from base_crawler import BaseCrawler

logger = logging.getLogger("forum")


class ForumCrawler(BaseCrawler):
    PLATFORM_NAME = "forum"

    DEFAULT_SEEDS = [
        "https://www.bilibili.com/tag/536999999999999",
        "https://tieba.baidu.com/f?kw=iceandfire",
    ]

    DEFAULT_KEYWORDS = [
        "冰与火之舞 谱子 下载",
        "ADOFAI chart download",
        "冰与火之舞 自制谱 百度网盘",
    ]

    def __init__(self, seeds: Optional[List[str]] = None, delay_min: float = 3.0, delay_max: float = 6.0):
        super().__init__(delay_min=delay_min, delay_max=delay_max)
        self.seeds = seeds or self.DEFAULT_SEEDS
        self._visited = set()

    def search(self, keyword: str, max_results: int = 20) -> List[Dict]:
        items = []
        search_urls = self._build_search_urls(keyword)

        for search_url in search_urls:
            if len(items) >= max_results:
                break

            response = self._request(search_url)
            if not response:
                continue

            soup = BeautifulSoup(response.text, "lxml")

            for a_tag in soup.find_all("a", href=True):
                href = urljoin(search_url, a_tag["href"])
                text = a_tag.get_text(strip=True)

                if self._is_candidate(href, text):
                    items.append({
                        "title": text or "未知",
                        "url": href,
                        "uploader": "",
                        "description": "",
                        "type": "forum",
                    })

                    if len(items) >= max_results:
                        break

            self._sleep()

        return items

    def _build_search_urls(self, keyword: str) -> List[str]:
        encoded = __import__("urllib.parse").quote(keyword)
        return [
            f"https://www.google.com/search?q={encoded}+filetype:adofai",
            f"https://www.google.com/search?q={encoded}+filetype:zip+intitle:adofai",
            f"https://search.bilibili.com/article?keyword={encoded}",
        ]

    def _is_candidate(self, url: str, text: str) -> bool:
        url_lower = url.lower()
        text_lower = text.lower()

        if any(ext in url_lower for ext in [".adofai", ".zip", ".rar", ".7z"]):
            return True

        keywords = ["谱", "chart", "adofai", "下载", "download", "自制谱", "冰与火"]
        if any(kw in text_lower for kw in keywords) and len(text) > 4:
            return True

        return False

    def get_download_links(self, resource_url: str) -> List[Dict]:
        links = []
        response = self._request(resource_url)
        if not response:
            return links

        text = response.text
        patterns = [
            (r'https?://[^\s"\'<>)]+\.(?:adofai)', "adofai"),
            (r'https?://[^\s"\'<>)]+\.(?:zip)', "zip"),
            (r'https?://[^\s"\'<>)]+\.(?:rar)', "rar"),
            (r'https?://[^\s"\'<>)]+\.(?:7z)', "7z"),
            (r'https?://pan\.baidu\.com/[^\s"\'<>)]+', "baidu_pan"),
            (r'https?://(?:www\.)?aliyundrive\.com/[^\s"\'<>)]+', "aliyundrive"),
            (r'https?://(?:www\.)?quark\.cn/s/[^\s"\'<>)]+', "quark"),
            (r'https?://github\.com/[^\s"\'<>)]+/releases/download/[^\s"\'<>)]+', "github_release"),
        ]

        for pattern, link_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                url = match.group(0)
                links.append({
                    "url": url,
                    "filename": self._guess_filename(url),
                    "type": link_type,
                })

        return links

    def extract_metadata(self, resource_url: str) -> Dict:
        response = self._request(resource_url)
        if not response:
            return {}

        soup = BeautifulSoup(response.text, "lxml")
        title = soup.title.string if soup.title else ""

        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""

        return {
            "title": title,
            "description": description,
            "source_url": resource_url,
            "platform": "forum",
        }

    def _guess_filename(self, url: str) -> str:
        parsed = urlparse(url)
        filename = parsed.path.split("/")[-1] if parsed.path else ""
        return filename or f"download_{abs(hash(url)) % 10000}"

    def run_default(self, max_items: int = 3) -> List[Dict]:
        return self.crawl(self.DEFAULT_KEYWORDS, max_items=max_items)


if __name__ == "__main__":
    crawler = ForumCrawler()
    results = crawler.run_default(max_items=2)
    print(f"发现 {len(results)} 个资源")
