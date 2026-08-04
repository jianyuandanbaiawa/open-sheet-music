"""
B站爬虫 MVP
通过 B站搜索 API 和视频/动态页面抓取 ADOFAI 谱子资源
"""

import re
import json
import logging
from typing import List, Dict, Optional
from urllib.parse import urlencode, urljoin, quote

from bs4 import BeautifulSoup
from base_crawler import BaseCrawler

logger = logging.getLogger("bilibili")


class BilibiliCrawler(BaseCrawler):
    PLATFORM_NAME = "bilibili"
    BASE_URL = "https://www.bilibili.com"
    API_SEARCH = "https://api.bilibili.com/x/web-interface/search/type"
    API_VIDEO = "https://api.bilibili.com/x/web-interface/view"
    API_DYNAMIC = "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail"

    DEFAULT_KEYWORDS = [
        "冰与火之舞 谱子",
        "ADOFAI 自制谱",
        "冰与火之舞 自制谱 下载",
        "ADOFAI chart download",
        "冰与火之舞 adofai",
    ]

    def __init__(self, cookie: str = "", delay_min: float = 2.0, delay_max: float = 5.0):
        super().__init__(delay_min=delay_min, delay_max=delay_max)
        if cookie:
            self.session.headers.update({"Cookie": cookie})

    def search(self, keyword: str, max_results: int = 20) -> List[Dict]:
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": 1,
            "page_size": min(max_results, 42),
            "order": "totalrank",
        }

        url = f"{self.API_SEARCH}?{urlencode(params)}"
        response = self._request(url)

        if not response:
            return []

        try:
            data = response.json()
            results = data.get("data", {}).get("result", [])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析 B站搜索结果失败: {e}")
            return []

        items = []
        for item in results[:max_results]:
            title = re.sub(r"<[^>]+>", "", item.get("title", ""))
            items.append({
                "title": title,
                "url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                "bvid": item.get("bvid", ""),
                "uploader": item.get("author", ""),
                "duration": item.get("duration", ""),
                "play_count": item.get("play", 0),
                "description": item.get("description", ""),
                "pubdate": item.get("pubdate", 0),
                "type": "video",
            })

        return items

    def get_download_links(self, resource_url: str) -> List[Dict]:
        links = []

        bvid_match = re.search(r"bilibili\.com/(video| BV)(\w+)", resource_url)
        if not bvid_match:
            return links

        bvid = bvid_match.group(2)
        api_url = f"{self.API_VIDEO}?bvid={bvid}"
        response = self._request(api_url)

        if not response:
            return links

        try:
            data = response.json().get("data", {})
        except (json.JSONDecodeError, KeyError):
            return links

        pages = data.get("pages", [])
        for page in pages:
            page_url = f"{resource_url}?p={page.get('page', 1)}"
            page_links = self._extract_from_page(page_url)
            links.extend(page_links)

        if not links:
            desc = data.get("desc", "")
            desc_links = self._extract_links_from_text(desc)
            links.extend(desc_links)

        return links

    def _extract_from_page(self, page_url: str) -> List[Dict]:
        links = []
        response = self._request(page_url)
        if not response:
            return links

        soup = BeautifulSoup(response.text, "lxml")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True)

            if self._is_chart_download(href, text):
                links.append({
                    "url": href,
                    "filename": text or self._guess_filename(href),
                    "type": self._guess_type(href),
                })

        links.extend(self._extract_links_from_text(response.text))
        return links

    def _extract_links_from_text(self, text: str) -> List[Dict]:
        links = []
        patterns = [
            r'https?://[^\s"\'<>)]+\.(?:adofai|zip|rar|7z)',
            r'https?://pan\.baidu\.com/[^\s"\'<>)]+',
            r'https?://(?:www\.)?drive\.google\.com/[^\s"\'<>)]+',
            r'https?://github\.com/[^\s"\'<>)]+/releases/download/[^\s"\'<>)]+',
            r'https?://(?:cowtransfer|www\.cowtransfer)\.com/[^\s"\'<>)]+',
            r'https?://(?:www\.)?aliyundrive\.com/[^\s"\'<>)]+',
            r'https?://(?:www\.)?quark\.cn/s/[^\s"\'<>)]+',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                url = match.group(0)
                link_type = self._guess_type(url)
                links.append({
                    "url": url,
                    "filename": self._guess_filename(url),
                    "type": link_type,
                })

        return links

    def _is_chart_download(self, href: str, text: str) -> bool:
        chart_keywords = ["谱", "chart", "adofai", "下载", "download", "zip", "rar"]
        href_lower = href.lower()
        text_lower = text.lower()

        if any(kw in text_lower for kw in chart_keywords):
            return True
        if any(ext in href_lower for ext in [".adofai", ".zip", ".rar", ".7z"]):
            return True

        return False

    def _guess_filename(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path
        filename = path.split("/")[-1] if path else ""
        if filename and "." in filename:
            return filename
        return f"download_{abs(hash(url)) % 10000}.dat"

    def _guess_type(self, url: str) -> str:
        url_lower = url.lower()
        if ".adofai" in url_lower:
            return "adofai"
        elif ".zip" in url_lower:
            return "zip"
        elif ".rar" in url_lower:
            return "rar"
        elif ".7z" in url_lower:
            return "7z"
        elif "pan.baidu.com" in url_lower:
            return "baidu_pan"
        elif "drive.google.com" in url_lower:
            return "google_drive"
        elif "github.com" in url_lower and "releases" in url_lower:
            return "github_release"
        else:
            return "unknown"

    def extract_metadata(self, resource_url: str) -> Dict:
        bvid_match = re.search(r"bilibili\.com/video/(\w+)", resource_url)
        if not bvid_match:
            return {}

        bvid = bvid_match.group(1)
        api_url = f"{self.API_VIDEO}?bvid={bvid}"
        response = self._request(api_url)

        if not response:
            return {}

        try:
            data = response.json().get("data", {})
        except (json.JSONDecodeError, KeyError):
            return {}

        title = data.get("title", "")
        desc = data.get("desc", "")

        song, artist = self._parse_title(title)
        difficulty = self._extract_difficulty(title, desc)

        return {
            "title": song,
            "artist": artist,
            "chart_author": data.get("owner", {}).get("name", ""),
            "difficulty": difficulty,
            "bvid": bvid,
            "view_count": data.get("stat", {}).get("view", 0),
            "like_count": data.get("stat", {}).get("like", 0),
            "upload_date": data.get("pubdate", 0),
            "description": desc,
        }

    def _parse_title(self, title: str) -> tuple:
        title = re.sub(r"【[^】]*】", "", title).strip()
        title = re.sub(r"\[[^\]]*\]", "", title).strip()

        separators = [" - ", " — ", " ~ ", "｜", "|"]
        for sep in separators:
            if sep in title:
                parts = title.split(sep, 1)
                return parts[0].strip(), parts[1].strip()

        return title, ""

    def _extract_difficulty(self, title: str, desc: str) -> int:
        text = f"{title} {desc}"
        difficulty_patterns = [
            r"(?:难度|difficulty|lv|level)\s*[:：]?\s*(\d+)",
            r"lv?\s*(\d{1,2})\s*[,.，。]?\s*(?:难度|diff)",
            r"(\d{1,2})\s*(?:级|星)",
        ]

        for pattern in difficulty_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def run_default(self, max_items: int = 5) -> List[Dict]:
        """运行默认关键词的爬取"""
        return self.crawl(self.DEFAULT_KEYWORDS, max_items=max_items)


if __name__ == "__main__":
    import sys

    max_items = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    print(f"启动 B站爬虫 (最多 {max_items} 条)...")
    crawler = BilibiliCrawler()

    results = crawler.run_default(max_items=max_items)

    print(f"\n共发现 {len(results)} 个谱子资源:")
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        print(f"  {i}. [{meta.get('title', '未知')}] by {meta.get('chart_author', '未知')}")
        for dl in r.get("download_links", []):
            print(f"     ↳ {dl['url'][:80]}... [{dl['type']}]")
