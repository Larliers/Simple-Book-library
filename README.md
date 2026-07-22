# 简易图书馆（Simple Book Library）

[中文](README.md) | [English](README.en.md)

在 Windows 上管理个人藏书与本地文件的桌面工具：把 PDF / EPUB / HTML / Markdown / FB2 / DOCX、漫画图片文件夹与 CBZ、TXT 小说扫进统一书库，用封面网格浏览，双击用系统默认程序打开。

## 适合谁用

- 想集中管理本机 PDF、EPUB、HTML、Markdown、FB2、DOCX、漫画文件夹/CBZ、TXT 小说
- 希望按目录扫描入库，而不是一个个手动添加文件
- 需要标签、书单、收藏，以及给 TXT 配置导入规则（从文件名或正文提取信息）

## 能做什么

| 分区 | 支持内容 | 你可以做什么 |
|------|----------|--------------|
| **Library** | PDF、EPUB、HTML/HTM、Markdown、FB2/FB2.ZIP、DOCX | 网格/列表浏览、右侧详情、标签、搜索；封面优先内嵌图，否则标题占位卡 |
| **Comic** | 含图片的**叶子文件夹**（jpg / jpeg / png / webp / gif / bmp / tiff）与 **CBZ** | 文件夹或 CBZ 各算一本；标题取文件夹名/文件名；GIF 取首帧；可选瀑布流或分页 |
| **Text Novel** | TXT（自动探测 UTF-8 / GBK 等编码） | 列表浏览、正文预览、自定义导入规则链 |
| **Collections** | — | 自定义书单 |
| **Favorites** | 图书 + 漫画 | 统一收藏入口 |
| **Settings** | — | 路径与扫描、字体、缩略图、错误日志等 |

### 导入

1. 在设置里分别指定 Library / Comic / Text 的根目录。
2. 触发扫描后，程序会递归入库（目录级导入，**不支持**拖入单个文件）。
3. 自动提取能拿到的标题、作者等信息，并生成封面缩略图。

补充说明：

- Library 扫描深度可调（约 1–3 层）。
- Library 文档类：HTML/HTM、Markdown、FB2/FB2.ZIP、DOCX 与 PDF/EPUB 一样走 Library 扫描与封面缓存；HTML/Markdown 取本地内嵌图或标题占位卡（不做浏览器整页渲染）。
- 漫画：含 jpg/jpeg/png/webp/gif/bmp/tiff 的**叶子文件夹**，以及 **CBZ** 压缩包，各识别为一本；标题用文件夹名或 CBZ 文件名；GIF 封面取**首帧**；先快速占位再后台压缩缩略图。**仍不支持** CBR 等其它压缩包。
- TXT：扫描时自动探测编码（UTF-8、GBK/GB18030、Big5 等）；可在 Settings 选择「文本编码偏好」（简体优先 / 繁体优先 / 自动，默认简体优先）；按你配置的**文本规则**从文件名或正文提取标题、作者、系列、标签；小说进入 Text Novel，不混进 Library 主列表。重扫时按与 Library 相同的指纹策略（Settings「指纹比对策略」，**新装默认 Quick**/前 4MB；Fast 仅比大小与修改时间，可能漏检内容变更）跳过未变更文件（Text 无封面要求）。
- Settings「路径与扫描」页同时管理根目录与扫描/缩略图任务（不再分两个导航项）。
- **目录级扫描策略**（可选）：在「路径与扫描」开启「分配扫描策略至不同路径」后，可为每个 Library / Comic / Text 根目录单独指定策略（未指定则继承全局）。关闭该开关时，所有根目录统一使用全局策略（Library/Text 用「指纹比对策略」；漫画用「漫画扫描策略」），但已保存的各目录覆盖值会保留。Library/Text 覆盖：`Fast` / `Quick` / `Strict`；漫画覆盖：`目录快照（快速）` / `每次完整重扫（严格）`——后者会禁用文件夹快照短路并重读旁注 TXT。
- 漫画同名：同一漫画根目录下标题（文件夹名）冲突时，可在 Settings 选择策略（默认跳过新人；也可都留或保留较新）。
- 源文件失踪：会记入错误日志，并从库中删除对应记录。
- 同名同扩展、路径不同：跳过导入并写入错误日志。

### 浏览与打开

- **单击**：选中，右侧看详情。
- **双击**：用系统默认关联程序打开（需本机已安装对应阅读器）。
- 顶部搜索：Library 可用 `title:` / `author:` / `tag:` 前缀；Text Novel 有独立过滤。
- 封面样式可在设置中调节（如选中边框等）。

### 文本规则（TXT）

在设置的 Rules 中打开规则面板，可：

- 增删改导入规则链，并实时预览效果  
- 使用内置模板 / 常用正则  
- 保存后，后续 Text 扫描按新规则提取元数据  

### 数据存在哪

都在本机，不上传云端：

| 位置 | 用途 |
|------|------|
| `src/sql/library.db` | 书库数据库 |
| `img_preview/`（默认） | 封面缩略图缓存；可在 Settings → 路径与扫描中指定其他目录，并选择自动迁移 / 仅更新索引 / 仅切换 |
| `src/Scan_error_logs/` | 扫描冲突、缺失删除等问题日志 |
| `src/fonts/` | 可选自定义字体（设置里可重新加载） |

## 环境要求

- **系统**：Windows 10 / 11（主要支持平台）
- **Python**：推荐 **3.10.6**（与依赖锁定一致；需 3.10+）
- **界面语言**：简体中文为主

## 安装与启动

```powershell
# 1. 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动（无控制台黑窗）
.\.venv\Scripts\pythonw.exe src\main.py
```

也可在项目根目录自建快捷方式「启动 简易图书馆.lnk」，指向上面的 `pythonw.exe` 与 `src\main.py`（该快捷方式不纳入版本库）。

### 可选：打包成 exe

```powershell
.\scripts\build_nuitka.ps1          # 独立目录
.\scripts\build_nuitka.ps1 -Onefile # 单文件
```

产物在 `build/nuitka/`。

### 可选：开发自检

```powershell
pip install -r requirements-dev.txt
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m pytest src/tests -q

# 检查 PDF 引擎是否可用（退出码 0 = 正常）
.\.venv\Scripts\python.exe src\main.py --check-pymupdf
```

## 使用前请知晓

- 只支持**配置根目录后扫描**，不能拖单个文件入库。
- 漫画分区支持**图片文件夹**与 **CBZ**；仍不支持 CBR 等其它压缩包。
- 打开图书依赖本机已安装的默认程序（PDF 阅读器、看图软件等）。
- 扫描与缩略图生成同一时间只跑一类后台任务，大库首次扫描可能较久。
- 若未安装 / 不可用 PyMuPDF：PDF 仍可入库，但可能缺少详细元数据与封面，并给出提示。

## 更多文档

- 源码结构说明：[`src_construction.md`](src_construction.md)
- UI 设计稿：`Simple-Book-library-Dev_Document/UI/新UI/`

## 许可证

见仓库内声明；第三方依赖遵循各自许可证。
