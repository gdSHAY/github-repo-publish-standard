# 落地实例：`gdSHAY/douyin-wm-downloader`

> 这是本规范的**第一个完整落地案例**（2026-09/10）。
> 参数直接抄，坑别再踩第二遍。

## 一、成品参数

| 项 | 值 |
| --- | --- |
| 仓库 | `gdSHAY/douyin-wm-downloader`（公开） |
| 本地工程 | `<本地工作目录>/抖音无水印下载站/` |
| staging | `发布仓库/`（同时是 git 工作区） |
| 默认语言 | 简体中文 → `README.md` 中文、`README.en.md` 英文 |
| 门面源文件 | `项目主页.md`（15.6 KB）/ `项目主页.en.md`（16.0 KB） |
| 开发文档 | `README.md`（本机，102 KB，**不发布**） |
| Release | `v1.0.7` —— APK 24.9 MB（arm64-v8a debug）+ Windows zip ≈ 74 MB |
| 素材 | `docs/screenshot-home-zh.png`、`docs/screenshot-result-zh.png`、`docs/watermark-compare.png` |
| 维护命令 | `cd 发布仓库 && git add -A && git commit -m "..." && git push` |

发布仓库最终 19 个文件：10 个 `.py` + `static/index.html` + `requirements.txt` +
`使用说明.txt` + `README.md` + `README.en.md` + `.gitignore` + 3 张 `docs/*.png`。

## 二、目录分层（本机 vs 仓库）

```
抖音无水印下载站/                     ← 本机工程（200 MB+）
├── README.md                         ← 开发文档 102 KB，不发布
├── 项目主页.md / 项目主页.en.md         ← 门面源文件，同步时重命名为 README*
├── server.py / *_parser.py / …        ← 源码
├── static/index.html                  ← 前端（单文件，无构建）
├── docs/*.png                         ← 素材（由 make_readme_assets.py 生成）
├── dist/ build/ 安卓APK/               ← 构建产物，走 Releases
├── bili_config.json tiktok_config.json data/  ← 凭据，永不发布
├── 水印对比验证/                        ← 原始大图，只发布合成后的对比图
├── 已停用/                             ← 归档的部署件（Dockerfile / render.yaml 等）
├── .tools/                            ← 脚本（sync_staging / publish_release / …）
└── 发布仓库/                           ← staging + git 工作区 ──────┐
                                                                  │ git push
                                        github.com/gdSHAY/douyin-wm-downloader
```

`.tools/` 里实际存在的脚本：

| 脚本 | 职责 |
| --- | --- |
| `sync_cloud.py` | 本机 → `发布仓库/`（对应模板 `sync_staging.py`） |
| `make_readme_assets.py` | Playwright 截图 + PIL 对比图 |
| `push_release_via_api.py` | 上传 Release 资产（对应模板 `publish_release.py`） |
| `push_cloud_via_api.py` | 走 Git Data API 推代码（github.com 不可达时的兜底） |
| `gh_run_monitor.py` | 看 Actions 跑得怎么样（带 `--repo`） |

## 三、这次踩到的坑（按代价排序）

### 1. 单测图片正则全程空转，还报 OK（最危险）

README 用的是 HTML `<img src="./docs/x.png">`，而单测只写了 Markdown 的
`![](...)` 正则 —— **一个引用都没匹配到，检查「通过」了**。
这是最危险的失败模式：假阴性比报错更可怕。

修复：同时解析两种写法，并加 `.png` 出现次数兜底断言（两边都得 > 0 且相等）。

### 2. 「清理会一路删到 `.git` 本身」—— 实测推翻

我原本断言 `_prune_empty_dirs()` 会删掉整个 `.git`。**实测不成立**：
`.git` 里有 `HEAD`/`config`，永远非空。真正会被删的是
`.git/objects/info`、`.git/objects/pack`、`.git/refs/tags` 这几个**内部**空目录，
而且删掉后 `git status / log / fsck / rev-parse` 全部正常 —— **不致命**。

结论按实测修正，没有夸大危害。

### 3. 静态检查用「源码切片」会自己先瞎

单测原本用 `源码.split("def _prune_empty_dirs")[1][:800]` 找 `IGNORED_TOP`。
docstring 一写长，常量就被挤出 800 字符窗口 → 断言莫名失败。
改用 `sync_mod._prune_empty_dirs.__code__.co_names`，长度与注释完全解耦。

### 4. CRLF 假象（Windows 必踩）

`git clone` 后比对，16 个文件全报「内容不同」，且远端都**更大**若干字节。
实际是 `core.autocrlf` 把 LF 转成了 CRLF。

判据：差值 ≈ 该文件行数。复核命令：

```bash
git -c core.autocrlf=false -c core.eol=lf clone <url> _verify
```

重 clone 后 18/19 相同，唯一真差异是重拍过的那张截图。

### 5. 单测 import 别的脚本会写 `__pycache__`

新加了 `importlib` 让单测在 `.tools/` 生成 `__pycache__`，
把「没有多余文件」那条自己弄脏了。修复：顶部 `sys.dont_write_bytecode = True`。

### 6. GitHub 不支持中文仓库名

`抖音无水印下载` 被规范化成 `-`，真名成了 `owner/-`。
用 `PATCH /repos/{o}/{r}` 改成 ASCII 名。**要主动告诉用户这个平台限制**。

### 7. 空仓库取 ref 回 409 而不是 404

`"Git Repository is empty."` —— 先用 Contents API 写一个 seed 文件
（如 `.gitignore`）把 git 对象库点亮，再走正常流程。

### 8. `or DEFAULT` 把「显式配置成空」吃掉了（模板回归测试抓出来的）

把脚本抽成模板、加回归测试后发现的：`IGNORED_TOP = set(cfg.get("ignored_top") or [".git"])`
—— 空列表是 falsy，于是 `ignored_top: []` **关不掉保护**。
危险之处在于：你想用「关掉保护看看会不会删」来**验证保护真的生效**，
却得到了「没删 → 保护生效」的**假结论**。

修复：`v = cfg.get(k); default if v is None else v`。
凡默认值是非空容器、而空容器又是合法输入的地方，都要这样写。

### 9. 静默跳过伪装成「通过」

`check_repo.py` 的资产名核对原本是 `import publish_release` 后取 `ASSETS`。
环境里没装 `requests` 时整节被 `except` 吞掉，**输出看起来完全正常**。

修复两条：① 资产名改从 `repo_config.json` 直接读，去掉硬依赖；
② 真跳过的项进 `SKIPPED` 清单，结尾显式列出，不计入通过。

## 三补：模板回归测试

`tests/verify_templates.py` 会临时造一个真项目，跑完整链路
（同步 → `git init` → 反跑一次同步 → 单测 → 复跑单测），再做 5 组反证：

| 反证 | 期望 |
| --- | --- |
| 英文版删掉图片引用 | 单测失败，且失败原因指向图片镜像 |
| 向 staging 注入 `ghp_xxx` 假 token | 单测失败，命中通用凭据模式 |
| README 写不存在的资产名 | 单测失败 |
| 新工程配 `ignored_top: []` | `.git` 内部空目录确实被删（证明配置真的驱动了行为） |
| 把本机配置里的真实值抄进 staging | 单测失败，命中**反向扫描**（通用模式抓不到这种「自定义字段名 + 真值」） |

当前结果：**29/29 通过**。改任何模板后必跑。

## 四、这次做的三件「非功能但很值」的事

1. **水印对比图带可复核依据** —— 在 README 里用 `<details>` 给出
   「亮像素计数 1241 vs 0」和扫描区域坐标，让「无水印」这个卖点变成可验证的事实，
   而不是宣传词。
2. **「能力边界」写成了主力章节** —— 抖音档位为什么只有一档、B站 未登录上限 480P、
   小红书必须带 `xsec_token`、TikTok 大陆必须挂代理 —— 每条都带实测记录。
   这一节挡掉了一半的潜在 issue。
3. **两条推送路径互证** —— `git push` 之后跑 API 脚本 dry-run 显示「未变 19」，
   等于让两套独立实现互相校验，比任何单一自检都可靠。

## 五、第二个实例：本技能自己（`gdSHAY/github-repo-publish-standard`）

规范发布自己时，又踩到三处**只在真实项目上才暴露**的问题 —— 记下来，这类问题单看模板看不出来：

| 问题 | 表象 | 根因 | 修法 |
| --- | --- | --- | --- |
| 子串黑名单误伤 | `templates/repo_config.json` 被判成「凭据残留」 | 黑名单里有 `_config.json` 这个**子串** | 改成配置驱动：拿 `never_publish` 的条目比对路径分段 |
| 检查器崩溃 | 扫到 `docs/*.png` 抛 `UnicodeDecodeError`，整脚本挂掉 | `read()` 只捕了 `OSError` | 同时捕 `UnicodeDecodeError`；崩掉的检查器会被误读成「没报错 = 通过」 |
| 反向扫描假阳性 | `owner` / `repo` / 图片路径全被当成「凭据泄漏」 | 保守策略「≥16 字符的未知键一律当秘密」把配置里的公开值也吞了 | 形状过滤（含 `/`、`\`、`://` 的不是凭据）+ 公开值白名单（`owner`/`repo`/路径类键） |

另外两处是**结构**问题：

- **镜像检查不该比对全部图片** —— 徽章按语言不同是合理的（中文版写
  `形态-智能体技能`、英文版写 `Form-Agent%20Skill`），URL 必然不同。
  改为：仓库内图片必须**逐字一致**，外链只比对**数量**。
- **staging 不能嵌在会被扫描的目录里** —— `发布仓库/` 里有一份完整的 SKILL.md。
  技能按「一级目录 + SKILL.md」枚举，嵌套副本不会被枚举，所以当场没有症状；
  但这是靠约定而非结构保证的。已把工作区移到技能树之外
  （`~/.workbuddy/skill-repos/<repo>/`，配置里用绝对路径）。

`repo_config.json` 的 `staging_dir` 因此改为**显式支持绝对路径** —— 不再依赖
`os.path.join` 遇到绝对路径原样返回这个副作用。

## 六、复用清单

拷到新项目时按顺序做：

1. 复制 `templates/repo_config.json` → 新工程 `.tools/repo_config.json`，改 owner/repo/include/release。
2. 复制 `_repo_config.py`、`sync_staging.py`、`publish_release.py`、`verify_public.py`、`check_repo.py` 到 `.tools/`。
3. 复制 `README.zh.template.md` / `README.en.template.md` → 工程根的 `项目主页.md` / `项目主页.en.md`，填内容。
4. 复制 `make_readme_assets.py` → `.tools/`，改顶部 `SEL_*` / `SAMPLE_INPUT` / 端口。
5. `python .tools/sync_staging.py` → `cd 发布仓库 && git init && git remote add origin ... && git push`。
6. `python .tools/publish_release.py --push`（**没有二进制产物就跳过** —— 纯文本仓库不需要 Release）。
7. `python .tools/verify_public.py` —— 全绿才算发完。
8. 跑 `python 仓库单测.py`，然后用 `CHECKLIST.md` 逐条打勾。

> `github.com` / `raw.githubusercontent.com` 不可达时：`verify_public.py` 会自动退到
> `api.github.com` 的 contents 接口（仍然匿名，报告里会写明走的哪条通道）；
> 推送则改用 Git Data API —— 见技能 `github-api-fallback`。
