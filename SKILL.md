---
name: github-repo-release-showcase
description: 【用户固定规范】把本地项目做成公开可分享的 GitHub 仓库时的**标准格式**：双语 README 门面（中英一键切换、中文默认）、自动生成的真实界面截图、APK/EXE 走 Releases 分发、公开前凭据扫描、发布后匿名可下载验证。触发场景：用户上传/提供任何本地项目并提到「上传 GitHub / 开源 / 公开 / 发布 / 分享 / 做个仓库 / 加 README / 放进 releases」，或说「按 XX 项目的格式改我的项目」「中英双语可切换」「把 apk 和 exe 放进 releases 里可供下载」。**只要用户要交付一个 GitHub 仓库，就按本技能的格式产出，不要每次自创结构。**
agent_created: true
version: 2.1.0
---

# GitHub 仓库「标准格式」规范

> **这是用户的长期固定规范。** 以后凡是把本地项目做成/改造 GitHub 仓库，
> 一律按本文件 §2 的目录布局与 README 骨架产出，不要每次另起炉灶。
> 模板文件在 `templates/`，落地实例在 `reference.md`。

**参考格式基准**：`Evil0ctal/Douyin_TikTok_Download_API`
（双语切换行 → 居中大标题 → 徽章组 → 大截图 → 能力表 → 平台前提 → API 表 → FAQ → 合规 → Star history）。

**核心原则**：README 是写给**陌生人**看的 —— 他要在 30 秒内知道
「这是什么 / 长什么样 / 怎么下载 / 有什么坑 / 能拿到什么程度」。达不到就当没写。

---

## 1. 开工四问（不要自己猜）

这四条会改变整条流水线，必须先用 `AskUserQuestion` 问清：

| 问题 | 为什么必须先问 |
| --- | --- |
| **双语是哪一层？** README / 应用界面 UI / 都要 | README 双语 = 两个文件 + 一行切换链接，几分钟；UI 双语要抽全部文案 + 加语言状态，工作量差一个数量级 |
| **仓库可见性？** 公开 / 私有 | ⚠️ **私有仓库的 Release 资产别人下不了**（必须登录且被授权，分享出去是 404）。只要目标是「供下载」，就必须公开 —— 要**提前说清源码也会公开** |
| **默认语言？** `README.md` 用中文还是英文 | GitHub 首页只渲染 `README.md`。中文用户为主 → `README.md` 中文、`README.en.md` 英文 |
| **Release 放什么？** 复用现有产物 / 重新构建 | 复用最快（几分钟）；重建更干净但可能很慢（安卓要下 SDK/NDK） |

顺带摸清：本地产物在哪（`dist/`、`安卓APK/`）、有没有现成截图、
原来的 README 是不是「开发笔记合集」（那种**不能**当门面，见 §3.3）。

---

## 2. 标准目录布局（规范）

公开仓库的**根目录只放这些**。其余一律不进仓库：

```
<repo-root>/
├── README.md              ← 门面（默认语言）。来自本机 项目主页.md
├── README.en.md           ← 另一语言。来自本机 项目主页.en.md
├── .gitignore             ← 同步脚本**生成**（不是复用工程根那份）
├── docs/                  ← README 引用的全部图片
│   ├── screenshot-home-zh.png
│   ├── screenshot-result-zh.png
│   └── watermark-compare.png
├── <源码>                 ← 服务代码 / 前端 / requirements.txt
├── static/                ← 前端（若前后端分离）
└── 使用说明.txt            ← 随压缩包分发的快速上手（可选）
```

**不进程仓库的东西**（本机保留、显式排除）：

| 类别 | 例子 | 去向 |
| --- | --- | --- |
| 构建产物 | `dist/`、`build/`、`安卓APK/` | **Releases** |
| 凭据/运行期数据 | `*_config.json`、`data/`、`.env` | 永不发布 |
| 工具与日志 | `.tools/`、`*.log`、job 下载物 | 永不发布 |
| 中间素材 | `水印对比验证/`（原始大图） | 只发布合成后的对比图 |
| 部署残留 | `Dockerfile`、`render.yaml`、`.github/workflows/` | 若产品定位是「本地运行」，一律移除并用 `OBSOLETE_FILES` 从已发仓库里删掉 |

**本机工程 / 仓库 双层结构**（关键设计）：
本机工程根保留开发文档与构建产物，`.tools/sync_cloud.py` 把它们**同步**到
`发布仓库/`；`发布仓库/` 才是 git 工作区。

- 好处：本机那份 100 KB 的开发 README 原封不动；仓库里只有干净门面。
- 维护命令只有一条：`cd 发布仓库 && git add -A && git commit -m "..." && git push`。

**staging 放在哪里**：默认放在工程根下（`发布仓库/`）。但**不要把它嵌在会被自动扫描的
目录里** —— 如果工程本身就是一份「技能 / 插件 / 会被发现的项目」，staging 里那份完整的
`SKILL.md`（或 `plugin.json`、`package.json`）副本会被扫描器当成第二个同名对象。
这时把 staging 放到工程之外：`repo_config.json` 的 `staging_dir` **支持绝对路径**
（`os.path.join` 遇到绝对路径会原样使用）。

> 本轮实测踩到：最初把 `发布仓库/` 放在技能目录内，里面有一份完整的 SKILL.md。
> 技能按「一级目录 + SKILL.md」枚举，嵌套副本不会被枚举到，所以当时没有症状 ——
> 但这是**靠约定而不是靠结构**保证的，一旦扫描逻辑变化就是难排查的歧义。
> 已把工作区移到工程外的 `~/.workbuddy/skill-repos/<repo>/`。

> 若改用「一个仓库直接放工程根」的形态，则 README 门面仍须遵守本文其余条款，
> 只是没有了同步层 —— 但 §6 的 `.git` 相关坑依然适用。

---

## 3. 双语 README 门面

### 3.1 骨架（照抄，替换尖括号内容）

完整可复制版本见 `templates/README.zh.template.md` / `README.en.template.md`。

```markdown
<div align="center">
<h1><项目名></h1>
<b><平台/品类关键词，用 · 分隔></b><br>
<一句话价值主张>

**简体中文** | [English](./README.en.md)

<徽章组：Release / Downloads / Stars / Forks / Issues>
<br>
<徽章组：平台 / 语言 / 许可证>

</div>

---
<一段 3~5 行的定位说明：做什么、跑在哪、数据去向>

> ⚠️ <最要命的前提条件，直链到下文锚点>

## 🎬 它长什么样        ← 真实截图 + <sub> 图注
## 📥 下载安装          ← 表格：文件名 / 大小 / 依赖 + 分平台步骤
## ✨ <能力矩阵表>       ← 平台 × 能力的 ✅ 表
## ⚙️ 三步开始用
## ⚠️ <各平台前提条件>    ← 最建立信任的一节
## 🧱 技术栈
## 🗂 项目结构
## 🔌 REST API           ← 有 HTTP 接口就必须写
## ❓ 常见问题           ← 用 <details> 折叠
## 📄 合规与免责
## 📮 联系
## ⭐ Star 历史
## 📄 许可
<div align="center"><sub>双语切换说明</sub></div>
```

### 3.2 门面五条硬性条款

1. **切换行在顶部第 5 行以内** —— 且**两份都要有**指向对方的相对链接
   （`./README.en.md` / `./README.md`）。放在最底部也算不合格。
2. **徽章只用静态可达的**。`img.shields.io/badge/...` 安全；
   Actions 徽章只在公开仓库可用，仓库还没公开时会 404。徽章不要超过 10 个。
3. **截图必须是真实界面**，且图注（`<sub>`）说明「这张图在演示什么」。
   不要用占位图、不要用设计稿。
4. **必须有「能力边界 / 前提条件」一节**，明确写出**做不到什么**
   （分辨率上限、需要登录态、某些平台不支持）。这比吹功能更能建立信任，
   也挡掉一半 issue。写入单测（关键词断言）防止后续被改文档时删掉。
5. **合规与免责必须写**：著作权归属、仅个人学习、24 小时内删除、风险自担。

### 3.3 别把开发 README 当门面

本地那份 README 往往有几十上百 KB 的开发笔记（决策记录、调试过程）。
**单独维护两个门面文件**（`项目主页.md` / `项目主页.en.md`），
让同步脚本映射成仓库的 `README.md` / `README.en.md`；开发文档原封不动。

### 3.4 两版必须互为镜像 —— 用单测守，别靠人眼

改中文忘了改英文，是这类仓库最常见的腐烂方式。写进单测
（`templates/check_repo.py` 已内置）：

- 章节（`##` 级标题）**数量与顺序**对应；
- 图片引用**两版一致** —— ⚠️ 要同时解析 `<img src="...">` 和 `![](...)` 两种写法，
  只解析 Markdown 语法会在 HTML 写法下**全程空转还报 OK**（最危险的假阴性）；
- 下载文件名一致；
- **语言纯度**：中文版汉字占比 > 0.10，英文版汉字占比 < 中文版的三分之一
  （抓「复制过来忘了翻译」，实测有效）。

---

## 4. 门面素材自动生成（截图一定会过期）

界面改一次截图就废。所以**做成一条命令**，而不是手工截一次。
模板：`templates/make_readme_assets.py`。

### 4.1 真实界面截图（Playwright）

1. 先起本地服务，**轮询探活成功**再开浏览器（不要 `sleep` 拍脑袋）；
2. `page.fill("#输入框真实id")` —— 别猜选择器，先去前端源码 `grep 'id="'`；
3. 点解析后**等结果区出现**（`wait_for_selector`），再 `sleep` 几秒让图片/视频帧加载完；
4. **视口高度按元素实测高度定**：`page.evaluate(... getBoundingClientRect().height)`，
   否则底部被裁或大片留白；
5. 用独立端口（如 8790）拉服务，**不碰用户正在跑的服务**；
6. 走本机地址时**绕开环境代理**：`urllib.request.build_opener(ProxyHandler({}))`。

### 4.2 水印 / 前后对比图：用像素找差异，别用肉眼估

1. 先把可疑区域放大存成探针图，**看一眼**确定目标在哪；
2. 再用**亮像素计数**机械化定位包围盒（同一个框：一张有亮像素、另一张为 0）；
3. **同一个坐标框同时框住两张图** —— 框里左边有角标、右边没有，才叫对比；
4. 标注的平台名要对（拿小红书素材却写「抖音」会被一眼看穿）。

### 4.3 固化成脚本

放 `.tools/make_readme_assets.py`，支持 `--with-shots` 开关。
**不要留临时脚本**（`_shot.py`、`_probe.py`），用完即删。

---

## 5. Releases 分发（二进制不进 git 对象库）

APK 25 MB + Windows 包 74 MB，且每次发版都换 —— 走 Releases，不走 git。
模板：`templates/publish_release.py`。

- **建 release / 传资产都走 API**：
  - 建：`POST https://api.github.com/repos/{o}/{r}/releases`
  - 传：`POST https://uploads.github.com/repos/{o}/{r}/releases/{id}/assets?name=...`
    （`Content-Type: application/octet-stream`，`timeout=(30, 1800)`，流式发送不读进内存）
- **资产名必须与 README 里写的完全一致** —— 写进单测（双向断言：
  README 里提到的文件名，上传脚本里必须有；反之亦然）。
- **幂等**：release 已存在 → 复用不新建；同名资产字节数相同 → 跳过；
  不同 → 先删旧的再传（防中断留下的半截文件）。
- **发布说明正文也是脚本的一部分**（`BODY` 常量），否则改本地没用；
  脚本要支持「仅更新 body」重跑。
- **默认 dry-run，`--push` 才执行**。
- **上传后必须验字节**：`Range: bytes=0-4095` 取头部、再取尾部
  （zip 的中央目录在末尾），与本地逐字节比对。**只看 HTTP 200 不够** —— 半截上传也可能 200。
- 发布说明里附本地算的 **SHA256** + 核验命令。

---

## 6. 安全闸 + 同步/推送（最容易被忽略的两块）

### 6.1 公开前的凭据扫描

模板：`templates/check_repo.py` 的 secrets 节。

```python
# 递归收集所有"看起来像秘密"的值：不认识的键一律当秘密（保守）
NOT_SECRET_KEYS = {"proxy"}   # 配置项，本就该出现在前端 placeholder 里
```

- 通用模式：`gh[pousr]_...`、`github_pat_...`、`sk-...`、`AIza...`、`AKIA...`、
  `-----BEGIN ... PRIVATE KEY-----`、`SESSDATA=<长值>`、`Bearer <长值>`。
- **同时**做「本机真实凭据反查」：从本地配置文件里取出 ≥16 字符的值
  （排除 `NOT_SECRET_KEYS`），在待发布内容里做全文/前缀搜索。
- ⚠️ **会误报**：`http://127.0.0.1:7890` 这种代理地址**不是**凭据，
  它出现在前端 placeholder 里是正确的 —— 别一刀切报警而淹没真问题。
- 同步脚本应在 staging 目录**生成**一份 `.gitignore`（排 `data/`、凭据文件、
  `__pycache__`），**不要**复用工程根那份（职责不同：一个管本机开发、一个管公开仓库）。

### 6.2 staging 目录兼作 git 工作区 —— 两个脚本都有 `.git` 的坑

| 脚本 | 不处理的后果 |
| --- | --- |
| **同步脚本的空目录清理** | 自底向上删空目录会删掉 `.git/objects/info`、`.git/objects/pack`、`.git/refs/tags`。**实测**：删后 `git status/log/fsck/rev-parse` 全正常，git 能容忍 —— **不是致命 bug，但工具不该动元数据**，而且不排除时会把 `.git/objects`、`.git/refs` 一并带走 |
| **推送脚本的文件清单** | 清单来自 `os.walk`。`SKIP_DIRS` 里若没有 `.git`，会把整个对象库当「待上传文件」，几百个 blob 全建一遍推上去，仓库变成奇怪的镜像 |

做法：
- 同步脚本加 `IGNORED_TOP = {".git"}`，清理时
  `if IGNORED_TOP & set(rel.split("/")): continue`；
- 推送脚本的 `SKIP_DIRS` 必须含 `.git`；
- **单测要行为实测 + 反证**：造一个含 `.git/objects/info` 的临时目录跑清理，
  验证未被删；再把排除名单清空，验证确实会被删（**反证「排除是它生效的原因」**）。

### 6.3 两条推送路径互相复核（最省力）

- `git push` 之后 → 跑 API 脚本 dry-run，应输出「未变 N」；
- API 脚本推完 → `cd 发布仓库 && git fetch && git status` 应为空；
- 另用 `git ls-remote` 看 HEAD 是否等于本地 commit。

---

## 7. 匿名验证 —— 发布成功的唯一证据

用**故意不带 `Authorization`** 的会话逐项验（模板：`templates/verify_public.py`）：

| 验证项 | 判据 |
| --- | --- |
| 仓库已公开 | `GET /repos/{o}/{r}` → `private=false` |
| README 双语可读 | `raw.githubusercontent.com/{o}/{r}/main/README.md` → 200，且含 `./README.en.md` |
| 截图可访问 | 三张图 200，且**字节数与本地一致**（不是只看 200） |
| **真实下载链接** | `https://github.com/{o}/{r}/releases/download/{tag}/{asset}` → **206**，前 4KB 与本地一致 |

- 第 4 项最终会 302 到 `release-assets.githubusercontent.com`，正常。
- 顺带配齐门面：`description`、`topics`、`has_wiki=false`、`has_projects=false`。
  ⚠️ topics **不能**通过 `PATCH /repos` 设置，要用
  `PUT /repos/{o}/{r}/topics`（`{"names": [...]}`）。

---

## 8. 已知坑（都实测过）

1. **GitHub 不支持中文仓库名** —— `抖音无水印下载` 会被规范化成 `-`，真名成 `owner/-`。
   用 `PATCH /repos/{o}/{r}` 改成 ASCII 名（改名 ≫ 删库重建）。**要主动告知用户这个平台限制**，别静默跳过。
2. **空仓库取 ref / 建 blob 回 `409` 而不是 `404`**（`"Git Repository is empty."`）。
   先用 Contents API 写一个 seed 文件（如 `.gitignore`）把 git 对象库「点亮」。
3. **CRLF 假象（Windows 上必踩）**：`git clone` 下来比对时全显示「内容不同」，
   且远端都比本地**大**若干字节 —— 其实是 `core.autocrlf` 把 LF 转成了 CRLF。
   **比对必须用 `git -c core.autocrlf=false -c core.eol=lf clone`**。
   判断技巧：差值 ≈ 该文件行数 → 基本可确定是 CRLF。
4. **私有仓库的 Release 资产对外 404** —— 详见 §1。
5. **`github.com` / `raw.githubusercontent.com` / `api.github.com` 可达性可能各不相同**。
   别用「首页 200」推断「能 push」；`git ls-remote` 成功才是判据。
6. **单测 import 别的脚本会写 `__pycache__`** —— 单测顶部加
   `sys.dont_write_bytecode = True`，否则「没有多余文件」那条会被自己的副产品弄脏。
7. **静态检查别用「源码切片里找字符串」** —— `src.split("def f")[1][:800]` 里找常量：
   docstring 一写长，常量就被挤出窗口，**检查自己先瞎了**。
   改用 `func.__code__.co_names`（字节码里真实引用的名字），长度与注释无关。
8. **「接口可达」的判据不是 200** —— `4xx` 也是可达（TCP+TLS 通了、应用层真的响应了）。
   出口被挡的表现是**超时**或 5xx。探测时要把「不可达」与「参数被拒」分开报。
9. **写「会发生什么」之前先实测** —— 本轮曾断言「清理会一路删到 `.git` 本身」，
   实测推翻（`.git` 里有 `HEAD`/`config`，永远非空）。结论要按实测修正，别夸大危害。
10. **`X.get(k) or DEFAULT` 会把「显式配置成空」误判成「未配置」** ——
   空列表/空字典是 falsy。本轮 `IGNORED_TOP = set(cfg.get("ignored_top") or [".git"])`
    导致 `ignored_top: []` **关不掉保护**（想验证「保护确实生效」时会得到假结论）。
    要区分缺省与显式空：`v = cfg.get(k); default if v is None else v`。
    **凡是默认值为非空容器、而空容器又是合法输入的地方，都要用 `is None` 判断。**
11. **「静默跳过」比「失败」更危险** —— 依赖缺失（如 `requests` 没装）导致整节
   检查被 `except` 吞掉时，输出看起来和「通过」一模一样。
    两条对策：① 能从**配置**读的就别 import 脚本（本轮资产名核对从
    `import publish_release` 改成读 `repo_config.json`，去掉了硬依赖）；
    ② 真跳过的项要进 `SKIPPED` 清单并在结尾**显式列出**，不计入通过。
12. **模板本身要有回归测试** —— `tests/verify_templates.py` 会用真项目现场跑一遍
    同步 → `git init` → 单测，再做 **5 组反证**（删图片引用 / 注入假 token /
    资产名写错 / 配置关闭保护 / 把本机凭据值抄进仓库）。改任何模板后必须重跑；
    本轮它抓出了上面第 10、11 条，外加三处只在真实项目上才暴露的假阳性与崩溃。
13. **检查器的「子串黑名单」必然误伤** —— 早先用 `_config.json` 这种子串去拦凭据文件，
    把合法的 `templates/repo_config.json` 也判成残留。改用**配置驱动**：
    拿 `never_publish` 的条目去比对路径分段（目录型前缀匹配、文件型只比文件名）。
    同理，检查器读文件必须同时捕 `OSError` 与 `UnicodeDecodeError`，
    否则扫到 `.png` 会**整脚本崩掉** —— 崩溃比失败更糟，人会以为「没报错就是过了」。
14. **「假阳性」与「假阴性」都要治，但方向相反** —— 反向凭据扫描一开始会把
    `owner` / `repo` / 图片路径全判成泄漏（假阳性），噪声一多真问题就被淹掉；
    而图片正则空转（假阴性）会让检查「通过」。两个都要专门处理：
    前者用「形状过滤（含 `/` 的不是凭据）+ 公开值白名单」，后者用「非空兜底断言」。
15. **一条断言要同时是「正例」和「反例」** —— 只验证「通过」，不验证「该失败时会失败」，
    等于没测。所有关键保护都必须配一个**反证**：把保护关掉，断言确实失败。

---

## 9. 交付前核对单

见 `CHECKLIST.md`（可直接当交付清单打勾）。摘要：

- [ ] `README.md` / `README.en.md` 都在，切换链接**双向可达且在顶部**
- [ ] 所有图片引用都能在仓库里找到（单测守，含 HTML `<img>` 写法）
- [ ] Release 资产名与 README 里写的一致（双向断言）
- [ ] 凭据扫描 0 命中（通用模式 + 真实凭据反查）
- [ ] 仓库已公开；`description` / `topics` 已设
- [ ] 匿名验证：README 200、截图字节数一致、**真实下载链接 206 + 前 4KB 一致**
- [ ] 单测全过且**幂等**（连跑两遍不新增文件）
- [ ] 临时脚本 / `__pycache__` / 备份目录已清理

---

## 10. 模板索引

| 文件 | 用途 |
| --- | --- |
| `templates/README.zh.template.md` | 中文门面骨架（占位符待填） |
| `templates/README.en.template.md` | 英文门面骨架（与中文逐节对应） |
| `templates/repo_config.json` | **一份配置驱动全部脚本**：仓库名、语言、同步清单、资产清单 |
| `templates/sync_staging.py` | 工程根 → `发布仓库/`（含 `.git` 排除、生成的 `.gitignore`、淘汰文件清理） |
| `templates/make_readme_assets.py` | Playwright 截图 + PIL 对比图，一键重生成 `docs/` |
| `templates/publish_release.py` | 幂等上传资产到 Releases（默认 dry-run）+ 发布说明同步 |
| `templates/verify_public.py` | 匿名验证（公开性 / README / 图片字节 / 下载链接 206） |
| `templates/check_repo.py` | 单测：镜像 / 图片 / 资产名 / 部署残留 / 凭据 / `.git` 行为实测 |
| `tests/verify_templates.py` | **模板自身的回归测试**（真跑一遍 + 5 组反证），改模板后必跑 |
| `CHECKLIST.md` | 交付核对单 |
| `reference.md` | 落地实例：`gdSHAY/douyin-wm-downloader` 的完整参数与踩坑记录 |

**使用姿势**：把 `templates/repo_config.json` 拷到目标工程 `.tools/repo_config.json`
改参数，再拷需要的脚本到 `.tools/`，改脚本顶部的 `import repo_config` 路径即可。
`--check` / dry-run 是默认行为，任何写操作都要显式开关。

**改过模板后**：`python tests/verify_templates.py` 必须 29/29 全绿（需要装了
`requests` 的解释器）。它证明的是「模板本身可用」，与具体项目无关。
