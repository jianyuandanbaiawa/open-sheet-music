"""
下载器 - 从下载链接下载文件并保存到临时目录
"""

import os
import re
import time
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("downloader")


SUPPORTED_DOWNLOAD_TYPES = {
    "adofai", "zip", "rar", "7z", "baidu_pan",
    "google_drive", "github_release", "cowtransfer",
    "aliyundrive", "quark", "unknown",
}

PAN_URL_PATTERNS = {
    "baidu_pan": r"https?://pan\.baidu\.com/s/[^\s]+",
    "google_drive": r"https?://drive\.google\.com/[^\s]+",
    "cowtransfer": r"https?://(?:www\.)?cowtransfer\.com/[^\s]+",
    "aliyundrive": r"https?://(?:www\.)?aliyundrive\.com/[^\s]+",
    "quark": r"https?://(?:www\.)?quark\.cn/s/[^\s]+",
}


class Downloader:
    """谱子资源下载器"""

    def __init__(self, download_dir: Optional[str] = None, timeout: int = 60):
        self.download_dir = download_dir or tempfile.mkdtemp(prefix="adofai_download_")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })

    def download(self, url: str, filename: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        下载文件，返回 (保存路径, 状态信息)
        状态: success / skipped / failed / manual_required
        """
        url_lower = url.lower()

        if any(pattern in url_lower for pattern in [
            "pan.baidu.com", "drive.google.com", "cowtransfer",
            "aliyundrive.com", "quark.cn",
        ]):
            return None, "manual_required"

        if "github.com" in url_lower and "releases/download" in url_lower:
            return self._download_github_release(url)

        return self._direct_download(url, filename)

    def _direct_download(self, url: str, filename: Optional[str] = None) -> Tuple[Optional[str], str]:
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True, allow_redirects=True)
            response.raise_for_status()

            if not filename:
                content_disposition = response.headers.get("Content-Disposition", "")
                match = re.search(r'filename[*]?=["\']?([^"\';\r\n]+)', content_disposition)
                if match:
                    filename = match.group(1)
                else:
                    filename = url.split("/")[-1] or "downloaded_file"

            filename = self._sanitize_filename(filename)
            save_path = os.path.join(self.download_dir, filename)

            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192 * 8):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size and downloaded % (8192 * 64) == 0:
                        pct = (downloaded / total_size) * 100
                        logger.info(f"  下载进度: {pct:.1f}% ({downloaded}/{total_size})")

            size_kb = os.path.getsize(save_path) / 1024
            logger.info(f"下载完成: {filename} ({size_kb:.1f} KB)")
            return save_path, "success"

        except requests.RequestException as e:
            logger.error(f"下载失败 [{url}]: {e}")
            return None, "failed"

    def _download_github_release(self, url: str) -> Tuple[Optional[str], str]:
        return self._direct_download(url)

    def _sanitize_filename(self, filename: str) -> str:
        if not filename:
            return "downloaded_file"

        for char in '<>:"/\\|?*':
            filename = filename.replace(char, "_")

        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200 - len(ext)] + ext

        return filename

    def download_all(self, download_links: List[Dict]) -> List[Dict]:
        """
        批量下载，返回下载结果列表
        """
        results = []

        for link in download_links:
            url = link.get("url", "")
            filename = link.get("filename")
            link_type = link.get("type", "unknown")

            if not url:
                continue

            if link_type in ("baidu_pan", "google_drive", "cowtransfer", "aliyundrive", "quark"):
                logger.info(f"需要手动下载: {url} ({link_type})")
                results.append({
                    "url": url,
                    "status": "manual_required",
                    "save_path": None,
                    "message": f"需要从 {link_type} 手动下载",
                })
                continue

            save_path, status = self.download(url, filename)
            results.append({
                "url": url,
                "status": status,
                "save_path": save_path,
                "type": link_type,
            })

            time.sleep(0.5)

        return results

    def cleanup(self):
        if os.path.exists(self.download_dir):
            import shutil
            shutil.rmtree(self.download_dir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup()


def is_cloud_storage_url(url: str) -> Optional[str]:
    """检测是否为网盘链接，返回网盘类型"""
    for name, pattern in PAN_URL_PATTERNS.items():
        if re.match(pattern, url, re.IGNORECASE):
            return name
    return None


if __name__ == "__main__":
    test_urls = [
        "https://github.com/example/repo/releases/download/v1/test.adofai",
        "https://pan.baidu.com/s/1xxxxx",
    ]

    dl = Downloader()
    for url in test_urls:
        cloud = is_cloud_storage_url(url)
        print(f"{url[:50]}... -> 网盘类型: {cloud or '直接下载'}")
    dl.cleanup()
