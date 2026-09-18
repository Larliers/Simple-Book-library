# 本地遗留 Issue 主清单

更新时间：2026-09-16

核验基线：`main` / `b17a34b8a5e0d6ad0a2ac0480636af36c69d25af`，包含核验开始前已有的未提交改动。

范围：诊断、复现、归档；本轮未修复运行时代码，未提交，未 push。
详细证据：`Agent-rule/logs/evidence/2026-09-16-known-issues-audit.md`

> 本文件是唯一主清单。主待办只包含“确认存在”或“部分存在”；已修复/当前未复现项、产品设想和发布事项分别归档。

## 1. 状态与证据口径

- `确认存在`：当前工作树可稳定复现，且有明确根因。
- `部分存在`：风险或代码缺口成立，但只在部分入口复现，或运行压力未触发最终故障。
- `当前不存在`：按当前工作树和指定条件未复现。
- `无法验证`：缺少环境、样本或执行成本不适合本轮。
- `历史过时`：来源描述对应的代码路径已移除或已被当前实现取代。
- `产品候选`：需要产品取舍，不能直接当作缺陷修复。

证据层级：`运行时复现` > `GUI 隔离复现` > `自动测试` > `静态证据` > `历史日志`。运行日志只用于提出候选，不单独证明缺陷。所有复现均使用临时数据库、缓存和虚构资源，未读写真实书库。

## 2. 主待办

### P1

#### [ ] BUG-6：三个整型设置仍可在真实 Qt slot 抛 `ValueError`

- 状态：`部分存在`
- 来源：旧 `bugissue.md`；2026-09-15 Quick Add 收尾日志。
- 影响：异常字符串会中断 `WebAppWindow.apply_setting` 本次设置操作；Repository 自身虽可容错，但调用尚未到达 Repository。
- 当前代码路径：`src/bookhub/ui/web_window.py:392-398`。
- 复现条件：绕过前端约束，分别调用未绑定窗口方法 `apply_setting(..., "comicPageSize"|"viewportBufferScreens"|"gridColumns", "abc")`。
- 期望/实际：期望由 Repository 归一化或回退默认值；实际三项在 slot 内先执行 `int("abc")` 并抛异常。`scanDepth`、`textPreviewChars` 当前已通过。
- 验证命令：使用临时 Repository 构造最小宿主，逐项调用 `WebAppWindow.apply_setting`；回归参考 `python -m pytest -q src/tests/test_repository_orphan_cleanup.py`。
- 证据：5 项中 2 项返回 accepted，3 项稳定得到 `ValueError: invalid literal for int()`。
- 根因：slot 中残留三处预转换，绕过了 Repository 的 `_normalize_*`。
- 修复方向：三项均原值直传 Repository，归一化逻辑只保留一处。
- 验收条件：5 项对非法字符串、`None`、越界数值都不抛异常；持久化值满足既有默认值/边界契约；全量测试通过。

#### [ ] BUG-8：同一 CBZ 每次修改都会遗留旧读取缓存

- 状态：`确认存在`
- 来源：旧 `bugissue.md`。
- 影响：频繁更新的漫画会在 `img_preview/comic/read/` 长期累积完整解压副本。
- 当前代码路径：`src/bookhub/library/formats/cbz.py:51-57,112-118`。
- 复现条件：以同一路径创建 CBZ、读取一次；修改归档并改变 `mtime_ns` 后再读取。
- 期望/实际：期望旧 token 被淘汰或受统一容量/时效策略约束；实际同一源生成两个 token 目录，旧目录仍存在。
- 验证命令：在临时目录两次改写同一 CBZ，并调用 `prepare_cbz_for_external_viewer`，统计 `comic/read/` 子目录。
- 证据：第二次读取后缓存目录数为 2，两个目录均存在。
- 根因：token 包含 `st_mtime_ns`，当前逻辑只校验/重建“当前 token”，从未关联或清理同源旧 token。
- 修复方向：在 marker 中记录规范化源路径，并按源清理旧 token；同时增加全局 TTL/容量上限，避免无界增长。
- 验收条件：同源连续修改后只保留策略允许的版本；其他 CBZ 的有效缓存不被误删；失败清理可容错。

#### [ ] BUG-9：Vaporwave 本地字体 URL 层级错误，Sora/Space Mono 未加载

- 状态：`确认存在`
- 来源：运行日志中的字体 404 候选；本轮 GUI 复核。
- 影响：Vaporwave 实际回退到系统字体，视觉宽度、密度和换行与设计不一致。
- 当前代码路径：`src/bookhub/ui/web/css/skins/vaporwave/fonts.css`；字体实际位于 `src/bookhub/ui/web/fonts/`。
- 复现条件：启动隔离 WebEngine，切换 Vaporwave，等待 `document.fonts.ready` 后检查 `document.fonts.check()`。
- 期望/实际：期望 Sora 和 Space Mono 均为 true；实际两者均为 false。
- 验证命令：在临时 DB 启动当前 `index.html`，执行 `document.fonts.check('16px Sora')` 与 `document.fonts.check('16px "Space Mono"')`。
- 证据：600×749 与 390×844 两次均返回 false；CSS 的 `../../fonts/` 从 `css/skins/vaporwave/` 解析到不存在的 `css/fonts/`。
- 根因：相对 URL 少返回一级，正确资源目录在 `web/fonts/`。
- 修复方向：改为可解析到 `web/fonts/` 的路径，并在双皮肤 WebEngine 测试中断言字体加载状态。
- 验收条件：两种字体在 WebEngine 中返回 true；控制台无字体 404；Glass/Vaporwave 关键视口无排版回归。

### P2

#### [ ] BUG-7：SQLite 未启用 WAL；并发风险成立，但普通压力未复现锁错误

- 状态：`部分存在`
- 来源：旧 ISSUE-003 / BUG-7。
- 影响：扫描、缩略图和 UI 写入峰值重叠时仍有 `database is locked` 风险；本轮不能把“未配置 WAL”直接等同为现存故障。
- 当前代码路径：`src/bookhub/library/repository.py:289-298`。
- 复现条件：临时数据库 8 个线程、每线程 40 次独立写入；使用当前连接工厂。
- 期望/实际：期望明确的并发策略；实际 `journal_mode=delete`，但 320 次写入、约 1.7 秒、0 锁错误。
- 验证命令：临时库并发写循环并读取 `PRAGMA journal_mode`；增加长事务/扫描与缩略图真实重叠后再做高压验收。
- 证据：WAL 确实未配置；普通压力未出现失败，因此只判部分存在。
- 根因：连接仅配置 `foreign_keys` 和 5000ms `busy_timeout`，并发写串行依赖等待，没有显式日志模式/写入队列策略。
- 修复方向：先做贴近真实工作负载的基准，再选择 WAL、批量写或单写者队列；不要只为消除静态告警而改 PRAGMA。
- 验收条件：记录 DELETE 与候选方案的锁错误率/吞吐；迁移、备份和退出流程通过；无新增 `-wal/-shm` 残留问题。

#### [ ] 低-3：`saveTextRules` 在扫描忙碌时仍返回 `scanned=true`

- 状态：`确认存在`
- 来源：旧 `bugissue.md`。
- 影响：规则已保存但扫描未启动时，调用方会收到错误的“已扫描”状态，Toast/后续状态判断可能误导。
- 当前代码路径：`src/bookhub/ui/web_bridge.py:1514-1531`；`src/bookhub/ui/web_window.py:620-634`。
- 复现条件：开启自动扫描，宿主处于已有扫描或缩略图任务中，然后保存 Text Rules。
- 期望/实际：期望返回 `scanned=false` 或明确 `busy`；实际 `start_scan()` 无返回值，Bridge 调用后无条件置 true。
- 验证命令：向 `UiBridge.saveTextRules` 注入拒绝启动的 BusyHost，解析返回 JSON。
- 证据：返回 `{ok:true, scanned:true}`，宿主仅收到一次调用但未接受任务。
- 根因：宿主 API 不暴露是否接受任务，Bridge 把“已调用”当成“已启动”。
- 修复方向：让 `start_scan` 返回 accepted/busy，或由 Bridge 在调用前查询统一任务状态。
- 验收条件：空闲时 true，扫描/缩略图忙时 false 且保留“规则保存成功”语义；前端文案区分保存与扫描。

#### [ ] 低-5：图书详情和打开文件夹每次全表物化并线性查找

- 状态：`确认存在`
- 来源：旧 `bugissue.md`。
- 影响：大书库中 `getDetail` / `openFolder` 延迟随图书总量线性增长，并产生不必要的字典列表。
- 当前代码路径：`src/bookhub/ui/web_bridge.py:963-967`。
- 复现条件：Repository 返回 20,000 条图书，连续查找尾部资源 100 次。
- 期望/实际：期望按 `resource_id` 单行索引查询；实际每次调用 `list_books()` 后 Python 遍历。
- 验证命令：用 20,000 行假 Repository 调用 `_find_book_row` 100 次并计时/统计 `list_books` 调用。
- 证据：100 次约 0.115 秒；算法稳定执行 2,000,000 次比较，真实 SQLite 物化成本尚未计入。
- 根因：Repository 缺少/未使用按 `resource_id` 查询接口。
- 修复方向：增加受索引支持的单行 Repository 查询，并让相关 Bridge 路径复用。
- 验收条件：查询计划命中索引；20k 数据下耗时不随总行数线性增长；详情和打开文件夹行为不变。

#### [ ] OPT-1：标签变更和合集增删改仍广播完整 `resourcesChanged`

- 状态：`确认存在`
- 来源：2026-09-12 标签管理日志；2026-09-15 Quick Add 收尾日志。
- 影响：单条标签或合集元数据变化会重建全部页面 payload，可能造成无关页面重绘、滚动和选择状态抖动。
- 当前代码路径：`src/bookhub/ui/web_bridge.py:1101-1114,1155-1159,1228-1244`。
- 复现条件：分别添加标签、创建合集、重命名合集、删除合集，监听 `resourcesChanged`。
- 期望/实际：期望定向更新受影响详情/目录；实际四种操作各触发一次完整 payload 广播。
- 验证命令：临时 Repository + `UiBridge`，对四项操作分别连接信号计数并解析 payload。
- 证据：四项计数均为 1；`push_resources()` 会序列化完整 `pages`。
- 根因：历史上以全局刷新作为一致性通道；Quick Add 已有定向返回，但普通标签/合集 CRUD 尚未迁移。
- 修复方向：复用 Quick Add 的定向回写 seam；保留兼容信号时仅发送失效范围，不携带全量页面。
- 验收条件：四项操作不广播完整 pages；当前详情、合集页、标签页准确更新；滚动位置和选中项保持。

#### [ ] OPT-2：标签范围切换存在双重失效/加载路径

- 状态：`部分存在`
- 来源：2026-09-12 标签管理日志。
- 影响：位于标签页时，一次范围切换可能发起重复请求；`tagLoading` 全局互斥还可能让第二次加载被静默丢弃，行为依赖 QWebChannel 回调/信号时序。
- 当前代码路径：`src/bookhub/ui/web/js/app.js:412-434,2494-2526`；`src/bookhub/ui/web_bridge.py:1090-1099`。
- 复现条件：在标签页切换任一资源范围；Bridge 回调中主动失效并加载，同时 `push_settings()` 触发 `settingsChanged` 再执行同样逻辑。
- 期望/实际：期望一次用户操作只产生一次最新请求；实际存在两个触发源，静态路径明确，但本轮未稳定捕获两次 Bridge 调用。
- 验证命令：在 Node 行为夹具中 mock `setTagManagerScopes/getTagCatalog/getTagResources` 并记录时序；分别让 callback 早于/晚于 `settingsChanged`。
- 证据：两个处理器都调用 `invalidateTagManager(true)` + `loadCurrentTagPage()`；加载函数由单一 `State.tagLoading` 短路。
- 根因：本地回调与全局设置同步同时拥有刷新职责，且请求锁不是按请求/页面隔离。
- 修复方向：指定唯一刷新拥有者；采用 request id 取消旧请求，不用一个布尔值吞掉新状态。
- 验收条件：每次范围切换恰好一次有效请求；快速连续切换以后一次为准；目录/详情两态都无永久 loading。

### P3

#### [ ] 低-1：`_comic_page_payload` 是未使用实现

- 状态：`确认存在`
- 来源：旧 `bugissue.md`。
- 影响：维护者需同时判断两套近似 payload 逻辑，增加误改风险；无直接用户故障。
- 当前代码路径：`src/bookhub/ui/web_bridge.py:643-650`。
- 复现条件：静态查找 `_comic_page_payload(` 的定义与调用。
- 期望/实际：期望单一路径；实际只有定义，运行时使用 `_comic_page_payload_from_items`。
- 验证命令：对 `src/bookhub` 做符号引用搜索，并运行 Bridge/漫画行为测试。
- 证据：入站调用数为 0。
- 根因：漫画分页重构后旧 rows 适配器未删除。
- 修复方向：确认无外部反射依赖后删除函数。
- 验收条件：漫画主列表、收藏、分页测试全通过；无符号引用。

#### [ ] 低-4：虚拟网格缓存键不含条目身份/版本，存在过期卡片窗口

- 状态：`部分存在`
- 来源：旧 `bugissue.md`。
- 影响：同一挂载实例内，如果可见范围几何不变但条目内容原地变化，`sync()` 会跳过 DOM 重建，短时显示旧标题/封面/状态。
- 当前代码路径：`src/bookhub/ui/web/js/app.js:1159-1188`；列表虚拟化还有同类键 `1335-1349`。
- 复现条件：保持列数、可见起止行和 padding 不变，只替换/修改可见条目后再次触发同一 `sync()`。
- 期望/实际：期望内容变化重建对应卡片；实际 key 只含几何字段。当前大多数生产更新会外层重挂载，因此未证实为稳定用户故障。
- 验证命令：Node DOM 夹具中对同一 mount 原地修改 items，再触发 resize/scroll，比较资源 ID 与文本。
- 证据：缓存键不包含 `item.id`、内容版本或数据世代；生产最小复现尚缺。
- 根因：虚拟化优化把“几何未变”等同为“DOM 数据未变”。
- 修复方向：加入可见 slice 的稳定签名/版本，或数据变化时显式清空 `lastKey`。
- 验收条件：同几何数据替换后可见 DOM 更新；滚动性能无明显回退。

#### [ ] OPT-3：添加任意根目录都会使标签目录失效

- 状态：`确认存在`
- 来源：2026-09-12 标签管理日志。
- 影响：仅登记一个新根目录、尚未扫描出资源时，也会清空并重新请求标签页数据。
- 当前代码路径：`src/bookhub/ui/web_window.py:451`。
- 复现条件：添加 Library/Comic/Text 根目录但关闭自动扫描，监听 `resourcesChanged.tagCatalogInvalidated`。
- 期望/实际：期望只有标签数据实际变化时失效；实际添加根后固定发送 true。
- 验证命令：临时 Repository 调用根目录添加路径，记录一次 push payload；再与完成扫描后的失效信号对比。
- 证据：`add_root` 路径无条件调用 `push_resources(..., tag_catalog_invalidated=True)`。
- 根因：根目录设置变化与资源标签数据变化共用同一宽泛失效策略。
- 修复方向：添加根只推设置；扫描确有资源/标签变更后再失效标签目录。
- 验收条件：关闭自动扫描时添加空根不触发标签请求；扫描完成后标签数据仍及时更新。

## 3. 验证归档：当前不存在或历史过时

| 编号/候选 | 状态 | 当前结论与证据 |
|---|---|---|
| BUG-1 CBZ 路径穿越 | `当前不存在` | `/`、`\`、盘符和 `..` 四类成员均被拒绝，安全成员保留；CBZ 回归测试通过。 |
| BUG-2 根目录通配符误删 | `当前不存在` | 当前使用前缀比较；Library/Comic/Text 含 `%/_` 删除回归测试通过。 |
| BUG-3 Bauhaus 硬编码建议 | `当前不存在` | 搜索 ViewModel 当前测试通过，未发现演示项。 |
| BUG-4 损坏封面复制原图 | `当前不存在` | 损坏输入生成 96×144 PNG 安全占位；回归测试通过。 |
| BUG-5 扫描进度恒 100% | `当前不存在` | Library 事件保留 `total=0` 的 busy 语义；Comic/Text 仍有真实 total。 |
| 低-2 漫画右键收藏后详情不刷新 | `历史过时` | 当前漫画右键菜单已无该收藏入口，旧空回调路径不存在；不是当前缺陷。 |
| ISSUE-007 外部打开静默失败 | `历史过时` | 旧 Widgets 路径已移除；当前 Bridge 失败会发 Toast，Smoke 测试通过。 |
| Text Rules 快速滚动白屏/重载感 | `当前不存在` | Glass/Vaporwave 中第一栏 `scrollTop=260`，连续 20 次 `renderTrBody()` 后仍为 260，overlay 存在、无白屏。 |
| Vaporwave 600px Text Novel 无内部滚动 | `当前不存在` | 600×749：容器高 186、scrollHeight 70520、scrollTop 可达 500；390×844 同样可滚动，且无水平溢出。 |
| 高 DPI 卡片密度 | `无法验证` | 本轮离屏环境未建立多档 Windows 缩放率；旧日志仅为观察，不进入缺陷待办。 |
| `pytest_out.txt` 的 `natsort` 缺失 | `历史过时` | 后续输出及当前全量 pytest 均通过，属于旧环境产物。 |
| Nuitka 崩溃报告 | `无法验证` | 旧报告为高成本打包阶段内存失败；本轮按计划不重跑打包，不能推断当前仍存在。 |
| 旧开发总览“尚未实现代码” | `历史过时` | 与当前 `src/`、270 项测试和现有 GUI 明显不符，仅作历史规格。 |

## 4. 产品候选（不进入缺陷主待办）

### ISSUE-006：Library/Text 重名冲突策略

- 状态：`产品候选`
- 来源：旧 `bugissue.md`。
- 现状：Comic 有 `skip_incoming / keep_both / prefer_newer`；Library/Text 仍使用既有同名规则与冲突日志。
- 需要决策：三类资源是否必须同一策略、同名判定是否包含扩展名/路径、默认策略及迁移兼容。
- 进入开发前验收定义：分别给 Library/Text 建立同名同扩展、同名不同扩展、不同路径、mtime 新旧矩阵。

### PRODUCT-1：启动最小化

- 状态：`产品候选`
- 来源：`Simple-Book-library-Dev_Document/coding document/settings选项中的内容.md` 未勾选规格。
- 现状：当前 Settings 未提供该能力；它是新增功能，不是回归缺陷。
- 需要决策：仅最小化窗口还是最小化到托盘、首次启动行为、无托盘环境回退。

### PRODUCT-2：高 DPI 密度策略

- 状态：`产品候选`
- 来源：历史 GUI 日志。
- 现状：没有证明错误缩放，只观察到高 DPI 下信息密度可能偏高。
- 需要决策：目标缩放率与卡片最小物理尺寸；确认后再建 100%/125%/150%/200% GUI 矩阵。

### 历史规格“保持原路径 / 统一管理复制”

- 状态：`历史过时`
- 当前架构以登记源目录和原路径扫描为基础，并非待补的一枚设置开关；若要引入托管复制，应另立迁移型 PRD，不能按小优化实现。

## 5. 运维/发布事项（不进入代码待办）

### OPS-1：现有未提交改动的提交与 push

- 状态：`无法验证`
- 来源：2026-09-15 日志。
- 说明：核验开始时工作树已有用户改动，且本地 `main` 领先远端 4 个提交。本轮不提交、不 push，也不判断这些变更应如何分组。
- 处理条件：由用户确认提交边界、提交信息和是否推送。

### OPS-2：Nuitka 打包内存失败是否仍存在

- 状态：`无法验证`
- 来源：根目录旧 `nuitka-crash-report.xml`。
- 说明：当前源码测试与离屏 GUI 不能替代打包验收；只有下一次正式打包仍失败时才转为可执行 Issue。

## 6. 本轮验证基线

- 全量 Python：`270 passed, 43 subtests passed`。
- 定向 Python：`95 passed, 6 subtests passed`（CBZ、根删除、搜索、漫画预览、PDF/扫描进度、Bridge smoke）。
- Node 行为：Quick Add、随机推荐、快捷键、标签管理四组通过。
- GUI：Glass/Vaporwave；1440×860、749×860、600×749、390×844；临时 DB/缓存/资源夹具。
- 关键 GUI 证据：Text Rules `scrollTop` 保持；Vaporwave 600/390 内部滚动成立且 `scrollWidth == clientWidth`；字体检查失败。
- 最终门禁：见审计证据日志；所有命令均不使用真实书库路径和私人数据。

## 7. 建议实施顺序

1. BUG-9（路径修复小、可立即恢复设计字体）。
2. BUG-6、低-3（设置/任务接受状态的明确契约）。
3. BUG-8（先定缓存淘汰策略，再实现）。
4. OPT-1、OPT-2、OPT-3（统一定向失效和请求所有权）。
5. 低-5、低-1、低-4（性能与清理）。
6. BUG-7（先补真实负载基准，再决定 WAL）。
