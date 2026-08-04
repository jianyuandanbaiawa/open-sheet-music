# 冰与火之舞社区谱库 (ADOFAI Chart Hub)

[![Stars](https://img.shields.io/badge/⭐-Stars-blue)](https://github.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Charts](https://img.shields.io/badge/Charts-0-orange)](charts/)

一个为 **冰与火之舞 (A Dance of Fire and Ice / ADOFAI)** 社区玩家打造的谱子收集与分享平台。

## ✨ 特性

- 📂 **结构化存储**：每个谱子独立文件夹，包含 `.adofai` 文件、音乐、预览图和元数据
- 🕷️ **多平台爬虫**：支持从 B站、抖音、快手、各大论坛/博客自动抓取公开谱子
- 🌐 **GitHub Pages**：精美的在线浏览页面，支持搜索、分类、预览
- 🤖 **自动化**：GitHub Actions 定时自动爬取新谱子
- 🏷️ **元数据管理**：完整的谱子信息（曲名、作者、难度、BPM、来源等）

## 📁 目录结构

```
open-sheet-music/
├── charts/                  # 谱子存储
│   ├── index.json           # 全量谱子索引（自动生成）
│   └── <曲目ID>/            # 每个谱子唯一标识
│       ├── chart.adofai     # 核心谱面文件
│       ├── music.mp3        # 音乐文件
│       ├── preview.jpg      # 预览图
│       └── meta.json        # 元数据
├── scripts/                 # 爬虫与工具
│   ├── base_crawler.py      # 爬虫基类
│   ├── bilibili_crawler.py  # B站爬虫
│   ├── douyin_crawler.py    # 抖音爬虫
│   ├── downloader.py        # 下载器
│   ├── parser.py            # 谱子解析器
│   └── indexer.py           # 索引生成器
├── docs/                    # GitHub Pages
│   ├── index.html           # 首页
│   ├── css/style.css        # 样式
│   └── js/app.js            # 交互
└── .github/workflows/       # CI/CD
    └── crawler.yml          # 定时爬取工作流
```

## 🚀 快速开始

### 浏览谱子

访问 [GitHub Pages](https://.github.io/open-sheet-music/) 浏览所有谱子。

### 本地运行爬虫

```bash
# 安装依赖
pip install -r scripts/requirements.txt

# 运行指定平台爬虫
python scripts/bilibili_crawler.py
python scripts/douyin_crawler.py

# 重新生成索引
python scripts/indexer.py
```

### 使用 GitHub Actions

在仓库 Settings → Secrets 中按需添加：
- `BILIBILI_COOKIE`（可选，用于更高频率的请求）
- `GITHUB_TOKEN`（自动提供，用于提交更新）

Actions 会每日自动运行爬虫并更新谱子索引。

## 📝 谱子规范

### .adofai 文件结构

```adofai
{
  "settings": {
    "version": 1,
    "artist": "艺术家",
    "song": "曲目名",
    "author": "谱师",
    "difficulty": 10,
    "bpm": 120,
    "volume": 100
  },
  "actions": [...],
  "pathData": "R300R300R300R300"
}
```

### 元数据 (meta.json)

```json
{
  "id": "sha256-hash",
  "title": "曲目名",
  "artist": "艺术家",
  "chart_author": "谱师",
  "difficulty": 10,
  "bpm": 120,
  "source": {
    "platform": "bilibili",
    "url": "https://...",
    "uploader": "上传者"
  },
  "download_date": "2026-08-04",
  "tags": ["官方", "自制"]
}
```

## ⚙️ 平台状态

| 平台 | 状态 | 说明 |
|------|------|------|
| 📺 B站 | ✅ 可用 | 主要爬取来源，搜索 API 相对稳定 |
| 🎵 抖音 | ⚠️ 基础框架 | 需要 Cookie 和签名处理，功能有限 |
| ⚡ 快手 | ⚠️ 基础框架 | 待完善签名和反爬处理 |
| 💬 论坛/博客 | 🧪 实验性 | 使用通用搜索引擎发现下载链接 |

> **注意**: 抖音和快手爬虫目前仅为框架代码，由于这些平台有严格的反爬机制（签名校验、设备指纹等），需要额外处理才能正常工作。建议主要使用 B站爬虫。

## ⚖️ 免责声明

- 本仓库仅收录**公开可下载**的谱子资源
- 所有谱子版权归原作者所有
- 如涉及侵权请提交 Issue 要求删除
- 爬虫设置了合理的请求频率限制，避免对目标网站造成压力
- 请尊重原作者署名权，转载时注明来源

## 🤝 贡献

欢迎提交 Issue 和 PR！

- 🐛 报告 Bug → Issues
- ✨ 新功能建议 → Discussions
- 🕷️ 新增爬虫 → PR

## 📄 License

MIT License
