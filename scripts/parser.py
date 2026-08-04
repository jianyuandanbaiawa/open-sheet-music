"""
ADOFAI 谱子解析器
支持 .adofai 文件解析和压缩包（zip/rar/7z）解压
"""

import json
import os
import re
import hashlib
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import rarfile
    HAS_RAR = True
except ImportError:
    HAS_RAR = False

try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False


CHART_DIR = Path(__file__).resolve().parent.parent / "charts"
SUPPORTED_AUDIO = {".mp3", ".ogg", ".wav", ".flac"}
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}


def parse_adofai_file(file_path: str) -> Dict:
    """
    解析 .adofai 文件
    注意: adofai 文件并非严格的 JSON，需要容错处理
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    result = {}
    try:
        settings_match = re.search(
            r'"settings"\s*:\s*(\{[^}]*"[^"]*"\s*:\s*"[^"]*"[^}]*\})',
            content, re.DOTALL
        )
        if settings_match:
            settings_str = settings_match.group(1)
            result["settings"] = json.loads(settings_str)
    except (json.JSONDecodeError, Exception):
        result["settings"] = {}

    path_data_match = re.search(r'"pathData"\s*:\s*"([^"]*)"', content)
    if path_data_match:
        result["pathData"] = path_data_match.group(1)

    return result


def extract_archive(archive_path: str, extract_to: Optional[str] = None) -> str:
    """
    解压压缩包，返回解压目录路径
    """
    archive_path = Path(archive_path)
    suffix = archive_path.suffix.lower()

    if extract_to is None:
        extract_to = tempfile.mkdtemp(prefix="adofai_extract_")

    extract_path = Path(extract_to)
    extract_path.mkdir(parents=True, exist_ok=True)

    if suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_path)
    elif suffix == ".rar":
        if not HAS_RAR:
            raise ImportError("需要安装 rarfile: pip install rarfile")
        with rarfile.RarFile(archive_path) as rf:
            rf.extractall(extract_path)
    elif suffix == ".7z":
        if not HAS_7Z:
            raise ImportError("需要安装 py7zr: pip install py7zr")
        with py7zr.SevenZipFile(str(archive_path), "r") as sz:
            sz.extractall(path=str(extract_path))
    elif suffix in (".tar", ".gz", ".bz2"):
        shutil.unpack_archive(str(archive_path), str(extract_path))
    else:
        raise ValueError(f"不支持的压缩格式: {suffix}")

    return str(extract_path)


def find_chart_files(directory: str) -> Dict[str, List[str]]:
    """
    在目录中查找谱子相关文件
    返回 {"adofai": [...], "audio": [...], "image": [...], "mapinfo": [...]}
    """
    result = {"adofai": [], "audio": [], "image": [], "mapinfo": []}
    dir_path = Path(directory)

    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            name_lower = file.lower()

            if ext == ".adofai":
                result["adofai"].append(file_path)
            elif ext in SUPPORTED_AUDIO:
                result["audio"].append(file_path)
            elif ext in SUPPORTED_IMAGES:
                result["image"].append(file_path)
            elif "mapinfo" in name_lower or "info" in name_lower:
                result["mapinfo"].append(file_path)

    return result


def generate_chart_id(content: str) -> str:
    """
    根据谱子内容生成唯一 ID
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def process_downloaded_file(file_path: str, source_info: Optional[Dict] = None) -> Dict:
    """
    处理下载的文件（adofai 或压缩包），移动到 charts 目录
    返回处理结果字典
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    temp_dir = None
    chart_files = {"adofai": [], "audio": [], "image": [], "mapinfo": []}

    if ext in ARCHIVE_EXTENSIONS:
        temp_dir = extract_archive(str(file_path))
        chart_files = find_chart_files(temp_dir)
    elif ext == ".adofai":
        chart_files["adofai"] = [str(file_path)]
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    if not chart_files["adofai"]:
        raise FileNotFoundError("未找到 .adofai 谱子文件")

    adofai_path = chart_files["adofai"][0]
    parsed = parse_adofai_file(adofai_path)

    settings = parsed.get("settings", {})
    chart_id = generate_chart_id(open(adofai_path, "r", encoding="utf-8", errors="ignore").read())

    chart_dir = CHART_DIR / chart_id
    chart_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(adofai_path, chart_dir / "chart.adofai")

    meta = {
        "id": chart_id,
        "title": settings.get("song", "未知曲目"),
        "artist": settings.get("artist", "未知艺术家"),
        "chart_author": settings.get("author", "未知"),
        "difficulty": settings.get("difficulty", 0),
        "bpm": settings.get("bpm", 120),
        "version": settings.get("version", 1),
        "source": source_info or {},
        "download_date": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tags": [],
    }

    for audio_path in chart_files["audio"]:
        src = Path(audio_path)
        shutil.copy2(audio_path, chart_dir / f"music{src.suffix}")
        meta["music_file"] = f"music{src.suffix}"
        break

    for img_path in chart_files["image"]:
        src = Path(img_path)
        if src.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            shutil.copy2(img_path, chart_dir / f"preview{src.suffix}")
            meta["preview_file"] = f"preview{src.suffix}"
            break

    with open(chart_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "chart_id": chart_id,
        "chart_dir": str(chart_dir),
        "meta": meta,
        "files": chart_files,
    }


def list_all_charts() -> List[Dict]:
    """
    列出所有已存储的谱子
    """
    charts = []
    if not CHART_DIR.exists():
        return charts

    for item in CHART_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            meta_path = item / "meta.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        charts.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    pass

    charts.sort(key=lambda x: x.get("download_date", ""), reverse=True)
    return charts


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python parser.py <adofai_file_or_archive>")
        sys.exit(1)

    file_path = sys.argv[1]
    source_info = {
        "platform": "manual",
        "url": "",
        "uploader": "user",
    }

    try:
        result = process_downloaded_file(file_path, source_info)
        print(f"✓ 谱子已处理: {result['meta']['title']}")
        print(f"  ID: {result['chart_id']}")
        print(f"  存储路径: {result['chart_dir']}")
    except Exception as e:
        print(f"✗ 处理失败: {e}")
        sys.exit(1)
