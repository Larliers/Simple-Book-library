# Simple Book Library

本地桌面书库管理工具，基于 **Python 3.10+** 与 **PySide6 (Qt)**。面向个人藏书场景：扫描目录、提取元数据、生成封面缩略图，并提供 Library / 漫画 / 文本小说等分区浏览。

## 功能概览

| 模块 | 支持格式 | 说明 |
|------|----------|------|
| **Library** | PDF、EPUB | 网格/列表视图、右侧详情栏、标签与书单 |
| **Comic** | 图片文件夹（jpg/png/webp 等） | 叶子目录识别、封面快扫 + 后台压缩缩略图 |
| **Text Novel** | TXT | 独立列表页、正文预览、可配置导入规则链 |
| **Collections** | — | 自定义书单，支持网格/列表与详情 |
| **Favorites** | PDF/EPUB + 漫画收藏 | 统一收藏入口，排序可持久化 |
| **Settings** | — | 路径、扫描策略、字体、缩略图维护、错误日志 |

### 导入与扫描

- **导入粒度**：目录级（不支持单文件拖入）。
- **Library 根目录**：递归扫描 PDF/EPUB，深度 1–3 层可配；提取标题/作者/出版社/语言，生成 WebP 缩略图。
- **Comic 根目录**：识别含图片的叶子文件夹；首图占位复制，压缩缩略图可后台并行生成。
- **Text 根目录**：按规则链从文件名或正文提取标题、作者、系列、标签；TXT 不进入 Library 主列表。
- **缺失治理**：源文件/文件夹不存在时写入 `src/Scan_error_logs` 并硬删除库内记录。
- **重名冲突**：同名同扩展名且路径不同则跳过导入，并记录到错误日志。
- **PyMuPDF 降级**：`fitz` 不可用时 PDF 仍入库（标题兜底），跳过元数据与缩略图并给出聚合 warning。

### 浏览与交互

- 单击选中并在右侧详情栏查看信息；双击用系统默认程序打开。
- 顶部搜索：Library 支持 `title:` / `author:` / `tag:` 前缀；Text Novel 页独立过滤。
- 封面网格采用 **cover-only** 无壳层样式，选中边框可在设置中调节。
- 漫画页支持瀑布流/分页（全局二选一），按文件夹修改时间或名称排序。

### 数据与文件

| 路径 | 用途 |
|------|------|
| `src/sql/library.db` | SQLite 书库数据库 |
| `src/sql/scan_report.json` | 最近一次扫描摘要 |
| `img_preview/` | 缩略图缓存（按资源类型与 original/compressed 分目录） |
| `src/Scan_error_logs/` | 扫描冲突、缺失删除、图片处理失败等日志 |
| `src/fonts/` | 可选自定义字体（Settings 中 Reload Fonts） |

## 环境要求

- Windows 10/11（主要开发与打包目标）
- Python **3.10.6**（推荐，与依赖锁定版本一致）
- 虚拟环境 + `requirements.txt` 固定版本（含 `PySide6==6.6.1`、`PyMuPDF==1.24.10`）

## 快速开始

```powershell
# 1. 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
.\.venv\Scripts\pythonw.exe src\main.py
```

可选：在项目根目录放置 `启动 简易图书馆.lnk`，指向上述 `pythonw.exe` 与 `src\main.py`（该文件已被 `.gitignore` 忽略）。

### 验证 PyMuPDF

```powershell
.\.venv\Scripts\python.exe src\main.py --check-pymupdf
# 退出码 0 表示可用
```

## 打包（Nuitka）

```powershell
.\scripts\build_nuitka.ps1          # standalone
.\scripts\build_nuitka.ps1 -Onefile # 单文件 exe
```

输出目录：`build/nuitka/`。脚本会打包 `src/assets`、i18n 文案与 PyMuPDF 原生模块。

## 测试

```powershell
pip install pytest
.\.venv\Scripts\python.exe -m pytest src/tests/ -q
```

覆盖 Text 规则引擎、漫画预览流水线、PDF 降级、UI smoke 等回归用例。

## 项目结构（简）

```
src/
├── main.py              # 应用入口
├── bookhub/
│   ├── library/         # 扫描、SQLite、缩略图、Text 规则
│   └── ui/              # Qt 主窗口、页面、对话框、组件
├── tests/               # 回归测试
└── sql/                 # 运行时数据库（.gitkeep 占位）
```

完整结构说明见 [`src_construction.md`](src_construction.md)。

## 已知限制

- 不支持单文件导入，仅支持配置根目录后扫描。
- 外部打开依赖系统默认关联程序。
- 当前 UI 文案以中文（`zh-cn`）为主。
- 扫描与缩略图任务互斥：同一时刻只跑一种后台任务。

## 开发文档

- Agent 规范与留档：`Agent-rule/`
- UI 设计范本：`Simple-Book-library-Dev_Document/UI/新UI/`

## 许可证

见仓库内各文件声明；第三方依赖遵循各自许可证。
