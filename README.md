<div align="center">
<h1>GitHub 仓库标准化上传 Skill</h1>
<b>把本地项目做成「别人打开链接就能看懂、能下载、能用」的公开仓库</b><br>
双语门面 · 白名单同步 · 二进制走 Releases · 公开前扫描 · 发布后匿名验证

**简体中文** | [English](./README.en.md)

<a href="../../stargazers"><img src="https://img.shields.io/github/stars/gdSHAY/github-repo-publish-standard?style=flat-square&label=Stars&color=06d6a0" alt="Stars"></a>
<a href="../../forks"><img src="https://img.shields.io/github/forks/gdSHAY/github-repo-publish-standard?style=flat-square&label=Forks&color=4cc9f0" alt="Forks"></a>
<a href="../../issues"><img src="https://img.shields.io/github/issues/gdSHAY/github-repo-publish-standard?style=flat-square&label=Issues" alt="Issues"></a>

<br>

<img src="https://img.shields.io/badge/形态-智能体技能-6f42c1?style=flat-square" alt="Skill">
<img src="https://img.shields.io/badge/运行环境-WorkBuddy-2b7fff?style=flat-square" alt="Runtime">
<img src="https://img.shields.io/badge/许可证-MIT-3da639?style=flat-square" alt="License">

</div>

---

一套**写给智能体看的格式规范 + 可直接复制的工具**。它解决的问题很具体：本地项目明明跑通了，传到 GitHub 之后别人还是看不懂、下不动、不敢用。

它把「上传」这件事拆成一条固定流水线 —— 白名单同步（凭据与构建产物永远进不去）、双语 README 门面、真实截图、二进制走 Releases、公开前扫凭据、发布后匿名验证。

> ⚠️ **三条前提，先看清楚：**
> **① 双语指的是项目页文档**（`README.md` / `README.en.md`），不是改你的应用界面；
> **② 仓库一旦设为公开，源码也是公开的** —— 凭据扫描是最后一道闸，不是保险，别拿它兜底；
> **③ 私有仓库的 Releases 资产别人下不了**，想让人下载就必须公开。

## 🎬 它长什么样

它不是界面型工具，产出的是**目录结构**与**一份能通过自检的仓库**：

<div align="center">
<img src="./docs/flow-zh.png" width="880" alt="两层目录结构与四道关卡">
<br>
<sub>左边是双层结构：工程根只放源码与开发文档，仓库由一个白名单同步生成；右边是发布前后必须过的四道关卡</sub>
</div>

<br>

规范本身也要经得起检验。配图下面是**真实跑一遍** `tests/verify_templates.py` 的输出留影 —— 不是设计稿，是把实际运行结果渲染成终端样式：

<div align="center">
<img src="./docs/verify-run-zh.png" width="820" alt="模板回归测试的真实输出">
<br>
<sub>27 项断言 + 4 组反证全部通过。反证的意义是：把保护关掉，测试确实会失败，才证明保护真的在起作用</sub>
</div>

## 📥 获取

没有发行版（纯文本技能，没有二进制产物），克隆即用：

```bash
git clone https://github.com/gdSHAY/github-repo-publish-standard.git
```

把它放进你的智能体技能目录即可被加载；只想要模板的话，`templates/` 单独拷走也能用。

## ✨ 它解决什么

| 常见问题 | 本规范的做法 | 对应产物 |
| --- | --- | --- |
| README 是开发笔记合集，外人看不懂 | 门面与开发文档**分开维护**，仓库里只放干净门面 | `项目主页.md` → `README.md` |
| 改中文忘了改英文 | 两版**互为镜像**由单测强制：章节顺序、图片引用、语言纯度 | `templates/check_repo.py` |
| 截图早就过期了 | 素材**一条命令重生成**，不是手工截一次 | `templates/make_readme_assets.py` |
| 安装包塞进 git，仓库越滚越大 | 二进制走 Releases，**不进 git 对象库** | `templates/publish_release.py` |
| 凭据跟着代码一起公开了 | 白名单同步 + **通用模式与真实凭据双路扫描** | `templates/sync_staging.py` |
| 传上去了，但别人真能下吗 | **匿名（不带 token）** 逐项验证到字节 | `templates/verify_public.py` |
| 每次的仓库结构都不一样 | 一份 `repo_config.json` **驱动全部脚本** | `templates/repo_config.json` |

## ⚙️ 三步开始用

**第一步**：把配置拷到目标工程的 `.tools/`，改四个字段（`owner` / `repo` / `staging_dir` / `include`）。

**第二步**：把需要的脚本从 `templates/` 拷到 `.tools/`：

```bash
mkdir -p .tools
cp templates/_repo_config.py templates/sync_staging.py templates/check_repo.py .tools/
cp templates/repo_config.json .tools/
```

**第三步**：同步 → 推送 → 验证。

```bash
python .tools/sync_staging.py            # 工程根 -> 发布仓库/（含 --check 只比对）
cd 发布仓库 && git add -A && git commit -m "init" && git push
cd .. && python .tools/verify_public.py  # 匿名验证，全绿才算发完
```

`--check`、dry-run 都是**默认行为**，任何写操作都要显式开关（`--push`）。

> **⚠️ 一个平台事实**：GitHub **不支持中文仓库名**。取 `抖音无水印下载` 这类名字会被规范化成 `-`，真名变成 `owner/-`。仓库名用 ASCII，中文名放进仓库描述与 README 大标题。

## ⚠️ 前提条件与能力边界

写清楚**做不到什么**，比列一堆特性更有用。

### 双语做到哪一层

只做**文档层**双语（README 两份文件 + 一行切换链接，几分钟）。**不做应用界面双语** —— 那要抽全部界面文案并引入语言状态，工作量差一个数量级。选型前先想清楚要哪一种。

### 二进制怎么分发

`dist/`、`build/`、APK 目录一律**不进仓库**。Releases 会话内**上传后验字节**（取头部与尾部与本地逐字节比对）—— 只看 HTTP 200 不够，半截上传也可能返回 200。

### 私有仓库的资产下不了

⚠️ 私有仓库的 Releases 资产**必须登录且被授权**才能访问，分享出去的链接对别人是 404。只要目标包含「供下载」，仓库就必须公开。

### 凭据扫描会有误报

`127.0.0.1:7890` 这类本机代理地址**不是凭据**，它出现在前端输入框的占位符里是正确的。脚本把它们放进白名单，避免误报淹没真问题。但**反向扫描**（拿本机配置里的真实值去待发布内容里搜）才是关键的一道。

### 关于「实测」而非「应该」

规范里的每条坑都标了是**实测**还是推断。举例：早先断言「清理空目录会一路删到 `.git` 本身」，实测推翻 —— `.git` 里有 `HEAD`/`config`，永远非空；真正会被删的是它**内部**的几个空目录，而且删掉后 git 全部操作正常，**不致命**。结论按实测修正，没有夸大危害。

### 环境依赖

需要 `git`；发布 Releases 与匿名验证需要 `requests`。若 `github.com` 在你这台机器不可直连，但 `api.github.com` 通，可改走 Git Data API 路径（`templates/` 之外另见同类实践）。

## 🧱 技术栈

| | |
| --- | --- |
| 形态 | 智能体技能（Markdown 规范 + Python 工具） |
| 语言 | Python 3.10+（仅标准库 + `requests`） |
| 素材 | Playwright（界面截图）、Pillow（对比图合成） |
| 校验 | 纯离线单测，不需要网络与 token |
| 依赖策略 | 单文件脚本，无构建步骤，拷走即用 |

## 🗂 项目结构

```
SKILL.md                    规范正文：标准目录布局、README 骨架、12 条已知坑
CHECKLIST.md                交付核对单（A~I 九组），逐条要证据
reference.md                落地实例与 9 条踩坑记录
LICENSE                     MIT
templates/
  repo_config.json          一份配置驱动全部脚本
  _repo_config.py           配置加载（含「空列表 vs 未配置」的正确判断）
  sync_staging.py           工程根 -> 发布仓库/（白名单同步、.git 保护）
  make_readme_assets.py     Playwright 截图 + Pillow 对比图
  publish_release.py        幂等上传 Releases（默认 dry-run）
  verify_public.py          匿名验证：公开性 / README / 图片字节 / 下载 206
  check_repo.py             仓库自检：双语镜像、图片、资产名、凭据、淘汰文件
  README.zh.template.md     中文门面骨架
  README.en.template.md     英文门面骨架
tests/
  verify_templates.py       模板自身回归测试（真跑一遍 + 4 组反证）
docs/                       README 配图
```

## ❓ 常见问题

<details>
<summary><b>这套东西必须配合智能体用吗？</b></summary>

不必。`templates/` 里都是普通 Python 脚本，改改 `repo_config.json` 在命令行直接跑就行。`SKILL.md` 是给智能体读的规范说明，人当然也能读。
</details>

<details>
<summary><b>为什么要把「能力边界」单独写一节？</b></summary>

因为读者最想知道的是**做不到什么**。写明分辨率上限、需要登录态、某些来源不支持，比列一堆特性更能建立信任，也挡掉一半的重复提问。这节会被单测守住，防止后续改文档时被顺手删掉。
</details>

<details>
<summary><b>改了模板，怎么确认没改坏？</b></summary>

```bash
python tests/verify_templates.py
```

它会临时造一个真项目，跑完整链路（同步 → `git init` → 二次同步 → 自检 → 复跑自检），再做 4 组反证：删掉英文版图片引用、注入假 token、写错资产名、把保护配置关掉 —— 每一组都**必须让自检失败**。当前 27/27 通过。
</details>

<details>
<summary><b>为什么单测里要写「反证」？</b></summary>

只写「应该通过」的断言，等于没测。本规范开发过程中真踩过两次：一次是图片引用的正则**一个都没匹配到**，检查全程空转还报通过；一次是 `ignored_top: []` 因为空列表是假值而**关不掉保护**，导致「验证保护生效」得到假结论。反证就是为了堵住这类假阴性。
</details>

<details>
<summary><b>可以拿来发别人的项目吗？</b></summary>

可以，但只发**你有权发布的内容**。规范本身不判断版权归属，把别人的代码打包成自己的仓库是使用者自己的责任。
</details>

## 📄 合规与免责

- 本仓库内容按 **MIT 许可证**发布，可自由使用、修改与再分发。
- 规范中的**示例仓库名、账号名仅作说明**，不代表任何背书关系。
- 工具会执行**文件删除**（同步时的淘汰文件清理）与**网络写入**（创建 Releases、推送提交）。请先在非关键仓库上试跑 `--check` / dry-run，确认行为符合预期再执行写操作。
- 凭据扫描是**尽力而为的最后一道闸**，不构成任何安全保证。发布前请自行确认仓库内容不含敏感信息。
- 使用本规范产生的任何后果由使用者自行承担。

## 📮 联系

| | |
| --- | --- |
| 问题反馈 | [Issues](../../issues) |
| 仓库 | <https://github.com/gdSHAY/github-repo-publish-standard> |

## ⭐ Star 历史

<a href="https://star-history.com/#gdSHAY/github-repo-publish-standard&Timeline">
  <img src="https://api.star-history.com/svg?repos=gdSHAY/github-repo-publish-standard&type=Timeline" alt="Star History" width="620">
</a>

## 📄 许可

本项目采用 **MIT 许可证**，详见 [LICENSE](./LICENSE)。可自由用于个人或商业项目，保留版权声明即可。

<div align="center">
<sub>本 README 采用「<a href="./README.en.md">简体中文</a> / English」双语，可用顶部链接切换。</sub>
</div>
