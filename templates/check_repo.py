# -*- coding: utf-8 -*-
"""公开仓库的离线单测 —— 不需要网络、不需要 token。

放在**工程根**（与 `.tools/` 同级），命名如 `仓库单测.py`。

    python 仓库单测.py

覆盖七节：
  1. staging 文件闭包        —— 该有的都有、不该有的一律没有
  2. README 双语镜像         —— 章节顺序 / 图片引用（两种写法）/ 语言纯度
  3. 部署残留               —— obsolete 清单里的东西确实不在
  4. 凭据扫描               —— 通用模式 + 本机真实凭据反查
  5. 资产名双向一致          —— README 提到的文件名 ↔ 上传脚本里的资产名
  6. 同步脚本不碰 .git       —— **行为实测 + 反证**
  7. 幂等                   —— 不写 __pycache__

设计原则：**每条保护都要能反证**（把保护关掉 → 断言确实失败）。
只写「应该对」的断言，等于没测。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile

# 必须最先设置：单测 import 别的脚本会生成 __pycache__，
# 否则第 7 节会被自己的副产品弄脏。
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = HERE if os.path.isdir(os.path.join(HERE, ".tools")) else os.path.dirname(HERE)
TOOLS = os.path.join(PROJECT, ".tools")
sys.path.insert(0, TOOLS)

import _repo_config as RC          # noqa: E402
import sync_staging as S           # noqa: E402

CFG = RC.CFG
STAGING = RC.STAGING
FAILED = []
SKIPPED = []


# ---------------------------------------------------------------------------
def check(name: str, cond: bool, extra: str = "") -> None:
    mark = "  OK  " if cond else "  FAIL"
    print("%s %s%s" % (mark, name, ("  ← " + extra) if extra and not cond else ""))
    if not cond:
        FAILED.append(name)


def skip(label: str, why: str) -> None:
    """显式记录跳过项 —— 静默跳过看起来跟「通过」一模一样，是把关最坏的模式。"""
    SKIPPED.append("%s（%s）" % (label, why))
    print("  -- 跳过：%s（%s）" % (label, why))


def read(path: str) -> str:
    """读文本；**二进制文件不能把检查器弄崩**。

    早先只捕 OSError，扫到 .png 会抛 UnicodeDecodeError 整脚本挂掉 ——
    检查器本身崩溃比检查失败更糟（人会以为「没报错就是过了」）。
    """
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return ""


def walk_staging():
    """(相对文件集合, 相对目录集合)。跳过 ignored_top。"""
    files, dirs = set(), set()
    for current, subdirs, names in os.walk(STAGING):
        rel_dir = os.path.relpath(current, STAGING).replace("\\", "/")
        parts = [] if rel_dir == "." else rel_dir.split("/")
        if RC.IGNORED_TOP & set(parts):
            subdirs[:] = []
            continue
        for name in names:
            files.add(("/".join(parts + [name])))
        for name in subdirs:
            dirs.add("/".join(parts + [name]))
    return files, dirs


# ===========================================================================
# 1. staging 文件闭包
# ===========================================================================
print("\n[1] staging 文件闭包")

if not os.path.isdir(STAGING):
    check("staging 目录存在", False, "先跑 python .tools/sync_staging.py")
else:
    items, missing = S.resolve_include()
    expected = {dst.replace("\\", "/") for _src, dst in items}
    expected |= set(S.GENERATED_FILES.keys())
    actual, _dirs = walk_staging()

    extra = sorted(actual - expected)
    absent = sorted(expected - actual)
    check("不该有的文件：无（%d 个多余）" % len(extra), not extra, "; ".join(extra[:6]))
    check("该有的文件：齐（%d 个缺失）" % len(absent), not absent, "; ".join(absent[:6]))

    # 闭包里绝不能出现凭据与构建产物。
    # ⚠️ 早先这里用了一串「子串匹配」的硬编码黑名单（含 `_config.json`），
    # 结果把合法的 `templates/repo_config.json` 也判成残留 —— 假阳性。
    # 改为**配置驱动**：用 never_publish 里的条目精确匹配路径/文件名。
    ALWAYS_FORBIDDEN = ("__pycache__",)
    cfg_forbidden = [p for p in (CFG.get("never_publish") or []) if p]

    def _matches(rel: str, pattern: str) -> bool:
        p = pattern.replace("\\", "/").strip("/")
        if not p:
            return False
        if pattern.endswith("/") or "/" in p:       # 目录型：前缀匹配
            return rel == p or rel.startswith(p + "/") or ("/" + p + "/") in ("/" + rel)
        parts = rel.split("/")                       # 文件名型：只比文件名
        return p in parts

    hit = []
    for f in actual:
        if any(bad in f.split("/") for bad in ALWAYS_FORBIDDEN):
            hit.append(f)
            continue
        if any(_matches(f, p) for p in cfg_forbidden):
            hit.append(f)
    check("staging 无凭据 / 产物残留（按 never_publish 判定）", not hit,
          "; ".join(sorted(hit)[:6]))

    # 走 Git Data API 推送（本机 git 不可用）时可以关掉这一条。
    if CFG.get("ignore_staging_git"):
        skip("staging git 工作区检查", "配置 ignore_staging_git=true")
    else:
        check("staging 是 git 工作区（.git 存在）",
              os.path.isdir(os.path.join(STAGING, ".git")))


# ===========================================================================
# 2. README 双语镜像
# ===========================================================================
print("\n[2] README 双语镜像")

rd = CFG["readme"]
ZH = os.path.join(STAGING, rd["zh_target"])
EN = os.path.join(STAGING, rd["en_target"])
zh, en = read(ZH), read(EN)

check("两份 README 都存在", bool(zh) and bool(en))

# 2.1 顶部切换链接，双向可达
def head_has_link(text: str, target: str) -> bool:
    head = "\n".join(text.splitlines()[:6])
    return ("./%s" % target) in head


check("中文版顶部有指向英文版的链接", head_has_link(zh, rd["en_target"]))
check("英文版顶部有指向中文版的链接", head_has_link(en, rd["zh_target"]))

# 2.2 章节数量与顺序
def sections(text: str):
    return [line.strip() for line in text.splitlines() if line.startswith("## ")]


szh, sen = sections(zh), sections(en)
check("章节数量一致（中 %d / 英 %d）" % (len(szh), len(sen)),
      len(szh) == len(sen) and len(szh) > 5)

# 2.3 图片引用 —— ⚠️ 必须同时解析 HTML <img src> 与 Markdown ![]()
IMG_HTML = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
IMG_MD = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')


def images(text: str):
    return sorted(IMG_HTML.findall(text) + IMG_MD.findall(text))


def _is_local(ref: str) -> bool:
    """仓库内图片（相对路径）。外链徽章按语言不同是**合理**的
    —— 中文版写 `形态-智能体技能`、英文版写 `Form-Agent%20Skill` ——
    所以镜像检查只比对仓库内图片，外链只比对**数量**。"""
    return not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", ref) and not ref.startswith("//")


izh, ien = images(zh), images(en)
local_zh = [r for r in izh if _is_local(r)]
local_en = [r for r in ien if _is_local(r)]
ext_zh = [r for r in izh if not _is_local(r)]
ext_en = [r for r in ien if not _is_local(r)]

check("仓库内图片引用两版一致（中 %d / 英 %d）" % (len(local_zh), len(local_en)),
      local_zh == local_en and len(local_zh) > 0,
      "中 %s / 英 %s" % (local_zh, local_en))
# 兜底：正则一个都没匹配到时上面的断言会因为 len==0 失败 —— 但显式再断言一次
# 防止「两边都是空」造成的假阳性。
check("仓库内图片引用非空（防正则空转）", len(local_zh) > 0,
      "正则没匹配到任何仓库内图片引用")
check("外链图片数量两版一致（徽章不该少一个）", len(ext_zh) == len(ext_en),
      "中 %d / 英 %d" % (len(ext_zh), len(ext_en)))
check(".png 出现次数两版一致且非零",
      zh.count(".png") == en.count(".png") and zh.count(".png") > 0,
      "中 %d / 英 %d" % (zh.count(".png"), en.count(".png")))

# 2.4 图片文件真实存在
pdir = os.path.dirname(ZH)
missing_img = [p for p in local_zh if p.startswith("./") and not os.path.isfile(
    os.path.join(pdir, p[2:]))]
check("README 引用的图片都在仓库里", not missing_img, "; ".join(missing_img[:6]))

# 2.5 语言纯度
def cjk_ratio(text: str) -> float:
    body = re.sub(r"```.*?```", "", text, flags=re.S)
    body = re.sub(r"<[^>]+>", "", body)
    han = len(re.findall(r"[\u4e00-\u9fff]", body))
    total = len(re.findall(r"\S", body)) or 1
    return han / total


rz, re_ = cjk_ratio(zh), cjk_ratio(en)
check("中文版汉字占比 > 0.10（实测 %.3f）" % rz, rz > 0.10)
check("英文版汉字占比 < 中文版 1/3（实测 %.4f vs %.3f）" % (re_, rz),
      re_ < rz / 3.0)

# 2.6 不可删章节（能力边界 / 合规）
for label, text in (("中文", zh), ("英文", en)):
    for key in ("⚠️", "📄"):
        check("%s版含 %s 章节" % (label, key), key in text)


# ===========================================================================
# 3. 部署残留
# ===========================================================================
print("\n[3] 部署残留")

residue = []
for name in CFG.get("obsolete") or []:
    if os.path.exists(os.path.join(STAGING, name)):
        residue.append(name)
check("obsolete 清单里的文件不在仓库里（%d 个残留）" % len(residue),
      not residue, "; ".join(residue))

# 通用特征（清单可能漏项）
DEPLOY_MARKERS = ["dockerfile", "render.yaml", "procfile", ".dockerignore"]
found = []
files, _dirs = walk_staging()
for f in files:
    low = f.lower()
    if any(m in low for m in DEPLOY_MARKERS) or low.endswith(".dockerignore"):
        found.append(f)
check("无部署相关文件名（通用扫描）", not found, "; ".join(found))

joined = (zh + en).lower()
hits = [m for m in ("dockerfile", "render.yaml", "部署", "deploy to render")
        if m in joined]
check("README 未提及部署方案", not hits, "; ".join(hits))


# ===========================================================================
# 4. 凭据扫描
# ===========================================================================
print("\n[4] 凭据扫描")

SECRET_PATTERNS = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("GitHub PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}")),
    ("OpenAI key", re.compile(r"\bsk-[A-Za-z0-9]{24,}")),
    ("Google key", re.compile(r"\bAIza[0-9A-Za-z\-_]{30,}")),
    ("AWS key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("SESSDATA", re.compile(r"SESSDATA=[A-Za-z0-9%_\-.]{20,}")),
    ("Bearer", re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{30,}")),
    ("bili_jct", re.compile(r"bili_jct=[A-Za-z0-9]{20,}")),
]

TEXT_SUFFIX = (".py", ".js", ".html", ".md", ".txt", ".json", ".yml", ".yaml",
               ".toml", ".cfg", ".ini", ".bat", ".ps1", ".spec")

generic_hits = []
for rel in sorted(files):
    if not rel.endswith(TEXT_SUFFIX):
        continue
    text = read(os.path.join(STAGING, rel))
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            generic_hits.append("%s: %s（%s）" % (rel, label, match.group(0)[:12] + "…"))
check("通用凭据模式（命中 %d 条）" % len(generic_hits), not generic_hits,
      "; ".join(generic_hits[:5]))

# 4.2 本机真实凭据反查 —— 不认识的键一律当秘密（保守）
NOT_SECRET_KEYS = {"proxy"}   # 配置项，本就该出现在前端 placeholder 里
SECRET_LINE = re.compile(r'"?([A-Za-z_][A-Za-z0-9_]*)"?\s*[:=]\s*"?([^",\s}]{16,})"?')

#: 只扫「像配置文件」的文件 —— 别把 .png / .zip 拖进来（会解码失败，
#: 而且二进制里偶然的子串匹配毫无意义）。
CONFIG_SUFFIX = (".json", ".yml", ".yaml", ".ini", ".cfg", ".conf", ".env",
                 ".toml", ".txt", ".properties", ".xml")


def collect_secrets(node, out, key: str = "") -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            collect_secrets(v, out, k)
    elif isinstance(node, list):
        for v in node:
            collect_secrets(v, out, key)
    elif isinstance(node, str) and len(node) >= 16 and key not in NOT_SECRET_KEYS:
        out.append((key, node))


#: 配置里天然**就是公开**的键 —— 它们的值会正当地出现在 README 里。
#: 不排掉的话，`owner` / `repo` / 图片路径全会被判成「凭据泄漏」（假阳性淹没真问题）。
PUBLIC_KEYS = {"src", "dst", "path", "name", "body_file", "staging_dir",
               "default_branch", "default_language", "zh_source", "en_source",
               "zh_target", "en_target", "tag", "images"}
PUBLIC_TOP = {"owner", "repo"}


def _public_values() -> set:
    out = set()

    def walk(node, key=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif isinstance(node, str) and (key in PUBLIC_KEYS or key in PUBLIC_TOP):
            if len(node) >= 4:
                out.add(node)

    walk(CFG)
    return out


def _looks_like_secret(value: str) -> bool:
    """凭据的形状：够长、无空白、**不含路径分隔符**。

    路径与 URL 不是凭据 —— 这一步能消掉绝大部分假阳性。
    代价是「含 `/` 的真凭据」会漏掉，因此通用模式扫描是并行的一道，
    两层叠加；这里只负责「本机真实值的反查」。
    """
    if len(value) < 16:
        return False
    if any(ch in value for ch in " \t\r\n"):
        return False
    if "/" in value or "\\" in value or "://" in value:
        return False
    return True


def _in_staging(path: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), STAGING]) == STAGING
    except ValueError:
        return False


PUBLIC = _public_values()
local_secrets = set()
candidates = []
for rel in CFG.get("never_publish") or []:
    path = os.path.join(PROJECT, rel.rstrip("/"))
    if os.path.isfile(path):
        candidates.append(path)
    elif os.path.isdir(path):
        for cur, _d, names in os.walk(path):
            candidates += [os.path.join(cur, n) for n in names]
candidates = [p for p in candidates
              if p.lower().endswith(CONFIG_SUFFIX) and not _in_staging(p)]

for path in candidates:
    text = read(path)
    if not text:
        continue
    if path.endswith(".json"):
        try:
            buckets = []
            collect_secrets(json.loads(text), buckets)
            local_secrets |= {v for _k, v in buckets}
        except Exception:
            pass
    for match in SECRET_LINE.finditer(text):
        if match.group(1) not in NOT_SECRET_KEYS:
            local_secrets.add(match.group(2))

# 两层消噪：形状过滤（路径/URL 不是凭据）+ 公开值白名单（owner/repo/图片路径…）。
local_secrets = {v for v in local_secrets if _looks_like_secret(v)}
skipped_public = {v for v in local_secrets if v in PUBLIC}
local_secrets -= skipped_public
if skipped_public:
    print("  -- 已排除 %d 个「配置里本就公开」的值（owner / repo / 图片路径 等）"
          % len(skipped_public))

reverse_hits = []
for rel in sorted(files):
    if not rel.endswith(TEXT_SUFFIX):
        continue
    text = read(os.path.join(STAGING, rel))
    for value in local_secrets:
        token = value[:32]
        if token and token in text:
            reverse_hits.append("%s 里出现本机凭据前缀 %s…" % (rel, value[:8]))
check("本机真实凭据反查（命中 %d 条 / 扫描 %d 个本机值）"
      % (len(reverse_hits), len(local_secrets)), not reverse_hits,
      "; ".join(reverse_hits[:5]))


# ===========================================================================
# 5. 资产名双向一致
# ===========================================================================
print("\n[5] Release 资产名 双向一致")

# 从**配置**取资产名，而不是 import publish_release ——
# publish_release 依赖 requests，缺库时会静默跳过，而「静默跳过」看起来就是「通过」，
# 是把关最不该有的失败模式。
asset_names = [it["name"] for it in (CFG.get("release") or {}).get("assets") or []]
ASSET_RE = re.compile(r"`([A-Za-z0-9._\-]+\.(?:zip|apk|exe|7z|dmg|tar\.gz))`")
mentioned = set(ASSET_RE.findall(zh)) | set(ASSET_RE.findall(en))

check("README 提到的资产名都在配置里（提到 %d 个 / 配置 %d 个）"
      % (len(mentioned), len(asset_names)),
      mentioned <= set(asset_names), "缺：%s" % sorted(mentioned - set(asset_names)))
check("配置里的资产名都写进了 README（否则下载页对不上）",
      set(asset_names) <= mentioned,
      "缺：%s" % sorted(set(asset_names) - mentioned))

# 脚本可 import 时再核对一次（配置 -> 脚本 的传递是否正确）
try:
    import publish_release as _PR
    script_names = [name for _p, name in _PR.ASSETS]
    check("上传脚本读到的资产与配置一致", set(script_names) == set(asset_names),
          "脚本 %s / 配置 %s" % (sorted(script_names), sorted(asset_names)))
except Exception as exc:
    skip("上传脚本级资产核对", "未 import publish_release：%s" % type(exc).__name__)


# ===========================================================================
# 6. 同步脚本不碰 .git（行为实测 + 反证）
# ===========================================================================
print("\n[6] 同步脚本不碰 .git")

# 用字节码里真实引用的名字判断，而不是「源码切片找字符串」——
# docstring 一写长，常量就被挤出窗口，检查会自己先瞎掉。
check("_prune_empty_dirs 引用了 IGNORED_TOP",
      "IGNORED_TOP" in S._prune_empty_dirs.__code__.co_names,
      "字节码没引用该名字，保护可能被删掉了")


def _fake_worktree(prefix: str) -> str:
    """造一个「staging + 一个真 git 目录」的临时现场。"""
    root = tempfile.mkdtemp(prefix=prefix)
    for sub in ("objects/info", "objects/pack", "refs/tags"):
        os.makedirs(os.path.join(root, ".git", sub), exist_ok=True)
    with open(os.path.join(root, ".git", "HEAD"), "w", encoding="utf-8") as handle:
        handle.write("ref: refs/heads/main\n")
    # 非空目录：不该被清理
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "docs", "keep.txt"), "w", encoding="utf-8") as handle:
        handle.write("x\n")
    # 空目录：**应该**被清理（配对验证，证明清理本身还在工作）
    os.makedirs(os.path.join(root, "leftover"), exist_ok=True)
    return root


def _prune_on(root: str, ignore: set) -> None:
    old_staging, old_ignored = S.STAGING, S.IGNORED_TOP
    S.STAGING, S.IGNORED_TOP = root, ignore
    try:
        S._prune_empty_dirs()
    finally:
        S.STAGING, S.IGNORED_TOP = old_staging, old_ignored


worktree = _fake_worktree("_wt_guard_")
try:
    # 注意：这里用 `is None` 判断，不能写 `or [".git"]` ——
    # 空列表是 falsy，会把「显式关闭保护」误当成「未配置」。
    _ignored = CFG.get("ignored_top")
    _prune_on(worktree, set([".git"] if _ignored is None else _ignored))
    survived = [d for d in ("objects/info", "objects/pack", "refs/tags")
                if os.path.isdir(os.path.join(worktree, ".git", d))]
    check("排除生效：.git 内空目录未被删（存活 %d/3）" % len(survived),
          len(survived) == 3, "被删：%s" % survived)
    # 配对验证：证明清理本身仍在工作 —— 非空目录保留、空目录被删。
    check("非空目录保留（docs/ 内有文件）",
          os.path.isdir(os.path.join(worktree, "docs")))
    check("普通空目录仍被清理（leftover/ 已删）",
          not os.path.isdir(os.path.join(worktree, "leftover")))
finally:
    shutil.rmtree(worktree, ignore_errors=True)

# 反证：把排除名单清空 —— 必须确实被删，证明「是排除在起作用」
worktree = _fake_worktree("_wt_neg_")
try:
    _prune_on(worktree, set())
    gone = [d for d in ("objects/info", "objects/pack", "refs/tags")
            if not os.path.isdir(os.path.join(worktree, ".git", d))]
    check("反证：不排除时确实会被删（消失 %d/3）" % len(gone),
          len(gone) == 3, "仍存活：%s" % gone)
    check("反证：.git 本身非空故不被删（因为含 HEAD）",
          os.path.isfile(os.path.join(worktree, ".git", "HEAD")))
finally:
    shutil.rmtree(worktree, ignore_errors=True)

# 推送脚本的 SKIP_DIRS 必须含 .git
try:
    import push_cloud_via_api as PC  # noqa: F401
    skip = set(getattr(PC, "SKIP_DIRS", []) or [])
    check("推送脚本 SKIP_DIRS 含 .git", ".git" in skip, str(sorted(skip)))
except Exception:
    skip("推送脚本 SKIP_DIRS 检查", "本工程未使用 Git Data API 推送（改走 git push）")


# ===========================================================================
# 7. 幂等：不留 __pycache__
# ===========================================================================
print("\n[7] 幂等")

pycache = [os.path.join(cur, n)
           for cur, dirs, _f in os.walk(TOOLS)
           for n in dirs if n == "__pycache__"]
check("本次运行没在 .tools/ 造出 __pycache__（%d）" % len(pycache),
      not pycache, "; ".join(pycache))
check("sys.dont_write_bytecode 已开启", sys.dont_write_bytecode is True)


# ===========================================================================
print("\n" + "=" * 62)
if SKIPPED:
    print("跳过 %d 项（不算通过，需人工确认）：" % len(SKIPPED))
    for name in SKIPPED:
        print("   -", name)
if FAILED:
    print("失败 %d 项：" % len(FAILED))
    for name in FAILED:
        print("   -", name)
    sys.exit(1)
print("全部通过。")
sys.exit(0)
