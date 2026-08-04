"""
测试脚本 - 验证解析器和索引器
用法: python scripts/test.py
"""

import sys
import os
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CHARTS_DIR = SCRIPT_DIR.parent / "charts"

sys.path.insert(0, str(SCRIPT_DIR))


def test_parse_adofai():
    print("=" * 50)
    print("测试 1: 解析 .adofai 文件")

    from parser import parse_adofai_file

    adofai_files = list(CHARTS_DIR.glob("*/chart.adofai"))
    if not adofai_files:
        print("  ⚠ 未找到 .adofai 文件")
        return False

    for f in adofai_files:
        try:
            parsed = parse_adofai_file(str(f))
            settings = parsed.get("settings", {})
            print(f"  ✓ {f.parent.name}: {settings.get('song', '?')} - {settings.get('artist', '?')}")
            print(f"    难度: Lv.{settings.get('difficulty', '?')}, BPM: {settings.get('bpm', '?')}")
        except Exception as e:
            print(f"  ✗ {f}: 解析失败 - {e}")
            return False

    return True


def test_scan_charts():
    print("\n" + "=" * 50)
    print("测试 2: 扫描谱子目录")

    from parser import list_all_charts

    charts = list_all_charts()
    print(f"  共发现 {len(charts)} 个谱子:")
    for c in charts:
        print(f"    - [{c.get('id', '?')}] {c.get('title', '?')} by {c.get('chart_author', '?')}")

    return len(charts) > 0


def test_indexer():
    print("\n" + "=" * 50)
    print("测试 3: 生成索引")

    from indexer import generate_index

    index = generate_index()
    print(f"  ✓ 索引生成成功: {index['total_charts']} 个谱子")
    print(f"    更新时间: {index['last_updated']}")

    index_file = CHARTS_DIR / "index.json"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if saved["total_charts"] == index["total_charts"]:
            print("  ✓ 索引文件验证通过")
        else:
            print(f"  ✗ 索引文件不匹配: {saved['total_charts']} vs {index['total_charts']}")
            return False

    return True


def test_process_file():
    print("\n" + "=" * 50)
    print("测试 4: 处理谱子文件")

    from parser import process_downloaded_file

    adofai_files = list(CHARTS_DIR.glob("*/chart.adofai"))
    if not adofai_files:
        print("  ⚠ 未找到可处理的文件")
        return True

    test_file = adofai_files[0]
    source_info = {"platform": "test", "url": "", "uploader": "tester"}

    try:
        result = process_downloaded_file(str(test_file), source_info)
        print(f"  ✓ 处理成功: {result['meta']['title']}")
        print(f"    存储路径: {result['chart_dir']}")
    except Exception as e:
        print(f"  ✗ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_bilibili_import():
    print("\n" + "=" * 50)
    print("测试 5: B站爬虫模块导入")

    try:
        from bilibili_crawler import BilibiliCrawler
        crawler = BilibiliCrawler()
        print(f"  ✓ 模块导入成功")
        print(f"    平台: {crawler.PLATFORM_NAME}")
        print(f"    关键词: {len(crawler.DEFAULT_KEYWORDS)} 个")
        crawler.close()
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    print("冰与火之舞社区谱库 - 集成测试\n")

    tests = [
        ("解析 .adofai 文件", test_parse_adofai),
        ("扫描谱子目录", test_scan_charts),
        ("生成索引", test_indexer),
        ("处理谱子文件", test_process_file),
        ("B站爬虫模块", test_bilibili_import),
    ]

    results = []
    for name, func in tests:
        try:
            passed = func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n  ✗ [{name}] 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 50)
    print("测试结果汇总:")
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status}  {name}")

    passed_count = sum(1 for _, p in results if p)
    print(f"\n通过: {passed_count}/{len(results)}")

    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
