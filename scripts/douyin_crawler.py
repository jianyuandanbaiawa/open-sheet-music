"""
抖音爬虫 - 搜索抖音上的 ADOFAI 谱子分享
注意: 抖音爬虫需要特殊处理（签名、加密等），此为基础框架
"""

import re
import json
import logging
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
from base_crawler import BaseCrawler

logger = logging.getLogger("douyin")


class DouyinCrawler(BaseCrawler):
    PLATFORM_NAME = "douyin"
    BASE_URL = "https://www.douyin.com"
    API_SEARCH = "https://www.douyin.com/search/web/general/full"

    DEFAULT_KEYWORDS = [
        "冰与火之舞 谱子",
        "ADOFAI 自制谱",
        "冰与火之舞 adofai 下载",
    ]

    def __init__(self, cookie: str = "", delay_min: float = 3.0, delay_max: float = 7.0):
        super().__init__(delay_min=delay_min, delay_max=delay_max)
        if cookie:
            self.session.headers.update({"Cookie": cookie})
        self.session.headers.update({
            "Referer": "https://www.douyin.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
        })

    def search(self, keyword: str, max_results: int = 20) -> List[Dict]:
        params = {
            "keyword": keyword,
            "search_channel": "aweme_general",
            "sort_type": 0,
            "publish_time": 0,
            "count": min(max_results, 20),
        }

        url = f"{self.API_SEARCH}"
        response = self._request(url, params=params)

        if not response:
            return []

        try:
            data = response.json()
            results = data.get("data", {}).get("aweme_list", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning("抖音搜索 API 可能需要签名参数，尝试使用网页解析")
            return self._search_web(keyword, max_results)

        items = []
        for item in results[:max_results]:
            aweme_info = item.get("aweme_info", {})
            items.append({
                "title": aweme_info.get("desc", ""),
                "url": f"https://www.douyin.com/video/{aweme_info.get('aweme_id', '')}",
                "aweme_id": aweme_info.get("aweme_id", ""),
                "uploader": aweme_info.get("author", {}).get("nickname", ""),
                "duration": aweme_info.get("duration", 0),
                "description": aweme_info.get("desc", ""),
                "type": "video",
            })

        return items

    def _search_web(self, keyword: str, max_results: int = 20) -> List[Dict]:
        url = f"https://www.douyin.com/search/{keyword}?type=video"
        response = self._request(url)

        if not response:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        items = []

        for script in soup.find_all("script"):
            text = script.string or ""
            if "RENDER_DATA" in text:
                try:
                    json_str = text.split("RENDER_DATA = ")[1].split("</script>")[0]
                    json_str = json_str.encode().decode("unicode_escape")
                    data = json.loads(json_str)
                    items.extend(self._parse_render_data(data))
                except (json.JSONDecodeError, IndexError):
                    pass

        return items[:max_results]

    def _parse_render_data(self, data: Dict) -> List[Dict]:
        items = []
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    aweme_id = value.get("aweme_id", "")
                    if aweme_id:
                        items.append({
                            "title": value.get("desc", ""),
                            "url": f"https://www.douyin.com/video/{aweme_id}",
                            "aweme_id": aweme_id,
                            "uploader": value.get("author", {}).get("nickname", ""),
                            "description": value.get("desc", ""),
                            "type": "video",
                        })
                elif isinstance(value, (dict, list)):
                    items.extend(self._parse_render_data(value))
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    items.extend(self._parse_render_data(item))
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
            r'https?://(?:www\.)?drive\.google\.com/[^\s"\'<>)]+',
            r'https?://github\.com/[^\s"\'<>)]+/releases/download/[^\s"\'<>)]+',
            r'https?://(?:cowtransfer|www\.cowtransfer)\.com/[^\s"\'<>)]+',
            r'https?://(?:www\.)?aliyundrive\.com/[^\s"\'<>)]+',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                url = match.group(0)
                links.append({
                    "url": url,
                    "filename": self._guess_filename(url),
                    "type": self._guess_type(url),
                })

        return links

    def extract_metadata(self, resource_url: str) -> Dict:
        response = self._request(resource_url)
        if not response:
            return {}

        soup = BeautifulSoup(response.text, "lxml")
        title = soup.title.string if soup.title else ""

        title_meta = soup.find("meta", property="og:title")
        if title_meta:
            title = title_meta.get("content", "")

        return {
            "title": title,
            "chart_author": "",
            "platform": "douyin",
            "source_url": resource_url,
        }

    def _guess_filename(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        filename = parsed.path.split("/")[-1] if parsed.path else ""
        return filename or f"douyin_{abs(hash(url)) % 10000}"

    def _guess_type(self, url: str) -> str:
        url_lower = url.lower()
        if ".adofai" in url_lower:
            return "adofai"
        elif ".zip" in url_lower:
            return "zip"
        elif ".rar" in url_lower:
            return "rar"
        elif "pan.baidu.com" in url_lower:
            return "baidu_pan"
        elif "drive.google.com" in url_lower:
            return "google_drive"
        elif "github.com" in url_lower and "releases" in url_lower:
            return "github_release"
        return "unknown"

    def run_default(self, max_items: int = 3) -> List[Dict]:
        return self.crawl(self.DEFAULT_KEYWORDS, max_items=max_items)


if __name__ == "__main__":
    crawler = DouyinCrawler()
    results = crawler.run_default(max_items=2)
    print(f"发现 {len(results)} 个资源")
