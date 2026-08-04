"""
主爬虫协调器 - 整合所有爬虫并执行完整流程
用法: python main.py [--platform bilibili|douyin|all] [--max-items 10] [--keywords keyword1 keyword2]
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from bilibili_crawler import BilibiliCrawler
from douyin_crawler import DouyinCrawler
from downloader import Downloader
from parser import process_downloaded_file, CHART_DIR
from indexer import generate_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


PLATFORMS = {
    "bilibili": BilibiliCrawler,
    "douyin": DouyinCrawler,
}


def run_crawler(platform: str, keywords: list, max_items: int, cookie: str = "") -> list:
    """运行指定平台爬虫"""
    if platform not in PLATFORMS:
        logger.error(f"未知平台: {platform}")
        return []

    crawler_cls = PLATFORMS[platform]
    crawler = crawler_cls(cookie=cookie)

    logger.info(f"=== 启动 {platform} 爬虫 (关键词: {keywords}, 最多: {max_items}) ===")

    try:
        results = crawler.crawl(keywords, max_items=max_items)
        logger.info(f"{platform} 爬虫发现 {len(results)} 个资源")
        return results
    finally:
        crawler.close()


def process_results(results: list, download: bool = True) -> dict:
    """处理爬取结果：下载 + 解析 + 存储"""
    stats = {"total": len(results), "downloaded": 0, "skipped": 0, "failed": 0, "manual": 0}

    if download and results:
        dl = Downloader()
        downloaded_dirs = []

        for i, result in enumerate(results):
            logger.info(f"[{i+1}/{len(results)}] 处理: {result.get('metadata', {}).get('title', '未知')}")

            links = result.get("download_links", [])
            if not links:
                stats["skipped"] += 1
                continue

            dl_results = dl.download_all(links)

            for dl_result in dl_results:
                if dl_result["status"] == "success" and dl_result.get("save_path"):
                    try:
                        source_info = {
                            "platform": result.get("platform", "unknown"),
                            "url": result.get("resource", {}).get("url", ""),
                            "uploader": result.get("resource", {}).get("uploader", ""),
                        }

                        parsed = process_downloaded_file(dl_result["save_path"], source_info)
                        downloaded_dirs.append(parsed["chart_dir"])
                        stats["downloaded"] += 1
                        logger.info(f"  ✓ 已存储: {parsed['meta']['title']}")
                    except Exception as e:
                        logger.error(f"  ✗ 解析失败: {e}")
                        stats["failed"] += 1
                elif dl_result["status"] == "manual_required":
                    stats["manual"] += 1
                    logger.info(f"  ⚠ 需要手动下载: {dl_result['url']}")
                else:
                    stats["failed"] += 1

        dl.cleanup()

    return stats


def main():
    parser = argparse.ArgumentParser(description="ADOFAI 社区谱子爬虫")
    parser.add_argument("--platform", "-p", choices=["bilibili", "douyin", "all"], default="all",
                        help="爬虫平台 (默认: all)")
    parser.add_argument("--max-items", "-n", type=int, default=10,
                        help="每个爬虫最大结果数 (默认: 10)")
    parser.add_argument("--keywords", "-k", nargs="+",
                        help="自定义搜索关键词")
    parser.add_argument("--no-download", action="store_true",
                        help="仅搜索，不下载")
    parser.add_argument("--index-only", action="store_true",
                        help="仅重新生成索引")
    parser.add_argument("--cookie", "-c", default="",
                        help="Cookie for 认证")

    args = parser.parse_args()

    if args.index_only:
        generate_index()
        return

    keywords = args.keywords or [
        "冰与火之舞 谱子",
        "ADOFAI 自制谱",
        "冰与火之舞 adofai 下载",
    ]

    platforms_to_run = list(PLATFORMS.keys()) if args.platform == "all" else [args.platform]

    all_results = []
    for platform in platforms_to_run:
        results = run_crawler(platform, keywords, args.max_items, args.cookie)
        all_results.extend(results)

    logger.info(f"\n=== 爬取完成，共发现 {len(all_results)} 个资源 ===")

    if not args.no_download and all_results:
        logger.info("\n=== 开始下载与处理 ===")
        stats = process_results(all_results, download=True)
        logger.info(f"\n📊 下载统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")

    generate_index()

    logger.info("\n✅ 完成！")


if __name__ == "__main__":
    main()
