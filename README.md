# 简易图书馆（Simple Book Library）

**v2.1.0** · [中文](README.md) | [English](README.en.md) · [GitHub Releases](https://github.com/Larliers/Simple-Book-library/releases)

在 Windows 上管理个人藏书与本地文件的桌面工具。把 PDF / EPUB / HTML / Markdown / FB2 / DOCX、漫画图片文件夹与 CBZ、TXT 小说扫进统一书库，用封面网格浏览，双击用系统默认程序打开。界面基于 **Qt WebEngine** 玻璃拟态 SPA，可在 **Glass / 蒸汽波（Vaporwave）** 两套皮肤间切换。

## v2.1.0 新特性

- **Settings → General → 关于**：显示当前版本，一键检查 GitHub 最新 Release；有新版本时弹窗引导浏览器打开下载页
- **双 UI 皮肤**：Settings → Appearance 可在 Glass 与 Vaporwave 间切换（需重启应用后生效）；蒸汽波含独立 day/night 变体与本地 woff2 字体
- **CBZ 双击打开优化**：解压全部图片页到阅读缓存后，用系统默认看图软件打开第一页
- **蒸汽波排版修复**：生产 DOM 与 Glass 皮肤布局对齐，设置页 / 弹窗 / Toast / Text Rules 均可正常显示

## 适合谁用

- 想集中管理本机 PDF、EPUB、HTML、Markdown、FB2、DOCX、漫画文件夹/CBZ、TXT 小说
- 希望按目录扫描入库，而不是一个个手动添加文件
- 需要标签、书单、收藏，以及给 TXT 配置导入规则（从文件名或正文提取信息）
- 大书库需要增量扫描、可配置指纹策略与视口虚拟化渲染

## 能做什么

| 分区 | 支持内容 | 你可以做什么 |
|------|----------|--------------|
| **Library** | PDF、EPUB、HTML/HTM、Markdown、FB2/FB2.ZIP、DOCX | 网格/列表浏览、右侧详情、标签、搜索；封面优先内嵌图，否则标题占位卡 |
| **Comic** | 含图片的**叶子文件夹**（jpg / jpeg / png / webp / gif / bmp / tiff）与 **CBZ** | 文件夹或 CBZ 各算一本；瀑布流或分页；GIF 取首帧 |
| **Text Novel** | TXT（自动探测 UTF-8 / GBK 等编码） | 列表浏览、正文预览、自定义导入规则链 |
| **Collections** | — | 自定义书单 |
| **Favorites** | 图书 + 漫画 | 统一收藏入口 |
| **Settings** | — | 路径与扫描、外观与主题、缩略图缓存、错误日志、检查更新 |

### 导入与扫描

1. 在 **Settings → 路径与扫描** 分别指定 Library / Comic / Text 的根目录。
2. 触发扫描后递归入库（**目录级导入**，不支持拖入单个文件）。
3. 自动提取标题、作者等信息，并生成封面缩略图。

补充说明：

- **指纹比对策略**（Settings → General）：新装默认 **Quick**（读前 4MB）；可选 Fast（仅 size+mtime，可能漏检内容变更）或 Strict（整文件 SHA256）。Library / Text 重扫时跳过未变更文件。
- **目录级扫描策略**（可选）：开启「分配扫描策略至不同路径」后，可为每个根目录单独指定策略；关闭时全局策略生效，已保存的覆盖值仍保留。
- **漫画扫描**：目录快照（快速）或每次完整重扫（严格）；同名冲突可选跳过新人 / 都留 / 保留较新。
- **TXT 编码偏好**：简体优先 / 繁体优先 / 自动；配合文本规则从文件名或正文提取元数据。
- **缩略图缓存**：默认 `img_preview/`，可在 Settings 指定其他目录（自动迁移 / 仅改索引 / 仅切换）。
- 源文件失踪会记入错误日志并从库中删除；同名同扩展、路径不同会跳过并写日志。

### 浏览与打开

- **单击**：选中，右侧看详情。
- **双击**：用系统默认关联程序打开。
- 顶部搜索：Library 支持 `title:` / `author:` / `tag:` 前缀。
- 大列表采用视口虚拟化，可调每行封面数与缓冲屏数。

### 文本规则（TXT）

Settings → 路径与扫描 → 文本根目录旁 **Rules**，可编辑导入规则链、实时预览、使用内置模板与常用正则。

### 外观

- **Glass**：默认玻璃拟态皮肤。
- **Vaporwave**：霓虹蒸汽波皮肤（切换后需重启）。
- **日/夜主题**：可按本地时间自动切换，或手动指定。

### 数据存在哪

| 位置 | 用途 |
|------|------|
| **开发态** | |
| `src/sql/library.db` | 书库数据库 |
| `img_preview/`（默认） | 封面缩略图缓存 |
| `src/Scan_error_logs/` | 扫描冲突、缺失删除等日志 |
| `src/fonts/` | 可选自定义字体 |
| **打包版（exe 同级）** | |
| `sql/library.db` | 书库数据库 |
| `img_preview/` | 封面缩略图缓存 |
| `Scan_error_logs/` | 扫描冲突、缺失删除等日志 |

升级时请保留上述三个用户数据目录，仅替换 `main.exe` 及同目录程序文件。

## 环境要求

- **系统**：Windows 10 / 11
- **Python**：推荐 **3.10.6**（3.10+；与依赖锁定一致）
- **界面语言**：简体中文为主（部分 Settings 文案有英文回退）

## 安装与启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\pythonw.exe src\main.py
```

## 打包成 exe

```powershell
.\scripts\build_nuitka.ps1          # 独立目录（推荐）
.\scripts\build_nuitka.ps1 -Onefile # 单文件
.\scripts\pack_release.ps1          # 改名 + 预建数据目录 + 打 zip
```

产物：`build/nuitka/main.dist/`（原始构建）；`build/release/Simple-Book-library-v{版本}-win64.zip`（发行包）。首次编译 Nuitka 会自动下载 MinGW 编译器，耗时较长。

## 一键 Release（GitHub Actions）

1. 打开仓库 **Actions → Release → Run workflow**
2. 选择 bump 类型（`patch` / `minor` / `major`）
3. 工作流会自动：递增版本 → 提交 → 打 tag → Nuitka 构建 → 打包 zip → 创建 GitHub Release

Release tag（如 `v2.1.2`）须与 `APP_VERSION`（如 `2.1.2`）一致，否则「检查更新」会误报。

## 开发自检

```powershell
pip install -r requirements-dev.txt
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m pytest src/tests -q
.\.venv\Scripts\python.exe src\main.py --check-pymupdf
```

## 使用前请知晓

- 只支持**配置根目录后扫描**，不能拖单个文件入库。
- 漫画支持**图片文件夹**与 **CBZ**；不支持 CBR 等其它压缩包。
- 打开文件依赖本机默认程序（PDF 阅读器、看图软件等）。
- 扫描与缩略图任务互斥；大库首次扫描可能较久。
- PyMuPDF 不可用时 PDF 仍可入库，但元数据与封面可能不完整。

## 更多文档

- 源码结构：[`src_construction.md`](src_construction.md)
- UI 设计稿：`Simple-Book-library-Dev_Document/UI/`

## 许可证

见仓库内声明；第三方依赖遵循各自许可证。
