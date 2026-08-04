"""
索引生成器 - 扫描 charts 目录并生成全量索引
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
CHARTS_DIR = SCRIPT_DIR.parent / "charts"
INDEX_FILE = CHARTS_DIR / "index.json"


def scan_charts() -> List[Dict]:
    """扫描所有谱子目录，收集元数据"""
    charts = []

    if not CHARTS_DIR.exists():
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        return charts

    for item in sorted(CHARTS_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            meta_path = item / "meta.json"
            adofai_path = item / "chart.adofai"

            if not meta_path.exists():
                continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告: 读取 {meta_path} 失败: {e}", file=sys.stderr)
                continue

            chart_entry = {
                "id": meta.get("id", item.name),
                "title": meta.get("title", "未知曲目"),
                "artist": meta.get("artist", ""),
                "chart_author": meta.get("chart_author", ""),
                "difficulty": meta.get("difficulty", 0),
                "bpm": meta.get("bpm", 120),
                "version": meta.get("version", 1),
                "download_date": meta.get("download_date", ""),
                "source": meta.get("source", {}),
                "tags": meta.get("tags", []),
                "has_music": meta.get("music_file") is not None or any(
                    (item / f).exists() for f in ["music.mp3", "music.ogg", "music.wav"]
                ),
                "has_preview": meta.get("preview_file") is not None or any(
                    (item / f).exists() for f in ["preview.jpg", "preview.png", "preview.jpeg"]
                ),
                "file_path": f"charts/{item.name}/chart.adofai",
            }

            if adofai_path.exists():
                file_size = adofai_path.stat().st_size
                chart_entry["file_size"] = file_size

            charts.append(chart_entry)

    charts.sort(key=lambda x: x.get("download_date", ""), reverse=True)
    return charts


def generate_index() -> Dict:
    """生成完整索引"""
    print("扫描谱子目录...")
    charts = scan_charts()
    print(f"找到 {len(charts)} 个谱子")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    index = {
        "version": "1.0",
        "last_updated": now,
        "total_charts": len(charts),
        "charts": charts,
    }

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"索引已生成: {INDEX_FILE}")
    print(f"共 {len(charts)} 个谱子")

    _print_stats(charts)
    return index


def _print_stats(charts: List[Dict]):
    if not charts:
        print("  (暂无谱子)")
        return

    platforms = {}
    difficulties = {}
    artists = {}

    for c in charts:
        platform = c.get("source", {}).get("platform", "unknown")
        platforms[platform] = platforms.get(platform, 0) + 1

        diff = c.get("difficulty", 0)
        difficulties[diff] = difficulties.get(diff, 0) + 1

        artist = c.get("artist", "未知")
        artists[artist] = artists.get(artist, 0) + 1

    print("\n📊 统计信息:")
    print(f"  平台分布: {platforms}")
    print(f"  难度分布: {difficulties}")

    if len(artists) <= 10:
        print(f"  艺术家: {artists}")


def get_index() -> Dict:
    """读取现有索引"""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "last_updated": "", "total_charts": 0, "charts": []}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="生成谱子索引")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--json", help="直接输出 JSON")
    args = parser.parse_args()

    index = generate_index()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"已导出到: {args.output}")

    if args.json:
        print(json.dumps(index, ensure_ascii=False, indent=2))
