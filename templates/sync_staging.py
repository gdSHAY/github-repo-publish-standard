# -*- coding: utf-8 -*-
"""把「要发布到 GitHub 的内容」同步到 staging 目录（默认 `发布仓库/`）。

staging 目录**就是可以 git push 的仓库根**。

    工程根（200 MB+，含构建产物与凭据）
        │  sync_staging.py —— 只挑该发布的
        ▼
    发布仓库/（干净，git 工作区）
        │  git add -A && git commit && git push
        ▼
    github.com/<owner>/<repo>

由 `.tools/repo_config.json` 驱动，清单不在脚本里写死。

为什么需要这一层
----------------
工程根里绝大多数东西**不该进仓库**：构建产物（发行版走 Releases）、
凭据（含登录态）、运行期数据、工具脚本。而且本地 README 往往是几十上百 KB 的
开发笔记合集，不适合当仓库门面 —— 门面单独维护，同步时重命名过去。

用法
----
    python .tools/sync_staging.py            # 同步（覆盖、清理淘汰文件）
    python .tools/sync_staging.py --check    # 只比对，不写入（退出码 1 = 有差异）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import shutil
import sys

# 必须在 import 本地模块**之前**：否则本脚本一跑就会在 .tools/ 生成 __pycache__，
# 把自己「不留多余文件」的幂等检查弄脏。
sys.dont_write_bytecode = True

from _repo_config import CFG, IGNORED_TOP, PROJECT, STAGING  # noqa: E402

# staging 目录专属、源工程没有对应文件的生成内容。
# 不要复用工程根的 .gitignore —— 两者职责不同：一个管「本机开发别提交脏东西」，
# 一个管「公开仓库别带上凭据」。
GENERATED_FILES = dict(CFG.get("generate") or {})
OBSOLETE_FILES = list(CFG.get("obsolete") or [])


def md5(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.md5(handle.read()).hexdigest()


def _has_glob(rel: str) -> bool:
    return any(ch in rel for ch in "*?[")


def resolve_include() -> tuple:
    """[(源绝对路径, 目标相对路径), ...], 缺失列表

    条目形态：
        "server.py"                        -> 同名拷到根
        {"src": "...", "dst": "README.md"} -> 重命名
        "docs/*.png"                       -> 通配，保持相对路径
    """
    items, missing = [], []
    for entry in CFG.get("include") or []:
        if isinstance(entry, str):
            src_rel, dst_rel = entry, entry
        else:
            src_rel, dst_rel = entry["src"], entry.get("dst") or entry["src"]

        if _has_glob(src_rel):
            # ⚠️ glob 也会匹配到**目录**（如 templates/* 里的子目录），
            # 不过滤的话 shutil.copy2 会在拷贝环节炸掉。
            matches = [m for m in sorted(glob.glob(os.path.join(PROJECT, src_rel)))
                       if os.path.isfile(m)]
            if not matches:
                missing.append(src_rel)
            for match in matches:
                name = os.path.basename(match)
                dst_dir = os.path.dirname(dst_rel)
                items.append((match, os.path.join(dst_dir, name) if dst_dir else name))
        else:
            path = os.path.join(PROJECT, src_rel)
            if os.path.isfile(path):
                items.append((path, dst_rel))
            else:
                missing.append(src_rel)

    # 门面文件：本机 项目主页.md -> 仓库 README.md
    readme = CFG["readme"]
    for src_key, dst_key in (("zh_source", "zh_target"), ("en_source", "en_target")):
        src_rel, dst_rel = readme[src_key], readme[dst_key]
        if not src_rel or not dst_rel:
            continue
        path = os.path.join(PROJECT, src_rel)
        if os.path.isfile(path):
            items.append((path, dst_rel))
        else:
            missing.append(src_rel)

    # 去重（后者胜），保持稳定顺序
    seen, out = {}, []
    for src, dst in items:
        if dst in seen:
            out[seen[dst]] = (src, dst)
        else:
            seen[dst] = len(out)
            out.append((src, dst))
    return out, missing


def _generated_diff() -> list:
    diff = []
    for name, content in GENERATED_FILES.items():
        path = os.path.join(STAGING, name)
        if not os.path.isfile(path):
            diff.append("缺失  %s（生成文件）" % name)
        else:
            with open(path, encoding="utf-8") as handle:
                if handle.read() != content:
                    diff.append("不一致 %s（生成文件）" % name)
    for name in OBSOLETE_FILES:
        if os.path.exists(os.path.join(STAGING, name)):
            diff.append("多余  %s（已淘汰，应删除）" % name)
    return diff


def _prune_empty_dirs() -> list:
    """删掉淘汰文件后留下的空目录。

    ★ 必须跳过 `.git/`。staging 同时是 git 工作区，`git init` 之后就有
    `objects/info`、`objects/pack`、`refs/tags` 这几个**空目录**；不排除的话
    每次同步都会静默删掉它们，并连带把 `.git/objects`、`.git/refs` 也带走。

    实测（2026-09-30）：删掉后 `git status / log / fsck / rev-parse` 全部正常，
    git 能容忍 —— **不是致命 bug**。但仍然要排除，因为：
      1. 本函数职责是清理「内容同步」留下的空目录，版本控制元数据不归它管；
      2. git 对这类缺失没有承诺，worktree / submodule 形态下可能承载语义；
      3. 排除成本 ≈ 0。
    """
    removed = []
    for current, _dirs, _files in os.walk(STAGING, topdown=False):
        if current == STAGING:
            continue
        rel = os.path.relpath(current, STAGING).replace("\\", "/")
        if IGNORED_TOP & set(rel.split("/")):
            continue
        try:
            if not os.listdir(current):
                os.rmdir(current)
                removed.append(rel + "/")
        except OSError:
            pass
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="同步发布内容到 %s/" % CFG["staging_dir"])
    parser.add_argument("--check", action="store_true", help="只比对差异，不写文件")
    args = parser.parse_args()

    # 配置在进程启动时读一次（`_repo_config` 的模块级加载）。
    # 改 repo_config.json 后重跑即可生效 —— 不再提供 --config：
    # 那个开关只会重新 load 一个被丢弃的返回值，属于「说了但没做」的接口。

    items, missing = resolve_include()
    if missing:
        print("[失败] 以下源文件不存在（检查 repo_config.json 的 include / readme）：")
        for name in missing:
            print("   ", name)
        return 2

    if args.check:
        diff = []
        for src, rel in items:
            dst = os.path.join(STAGING, rel)
            if not os.path.isfile(dst):
                diff.append("缺失  %s" % rel)
            elif md5(src) != md5(dst):
                diff.append("不一致 %s" % rel)
        diff += _generated_diff()
        if diff:
            print("目标目录与源存在 %d 处差异：" % len(diff))
            for line in diff:
                print("   ", line)
            return 1
        print("一致：%d 个同步文件 + %d 个生成文件，全部与源相同。"
              % (len(items), len(GENERATED_FILES)))
        return 0

    os.makedirs(STAGING, exist_ok=True)
    copied = []
    for src, rel in items:
        dst = os.path.join(STAGING, rel)
        os.makedirs(os.path.dirname(dst) or STAGING, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append((rel, os.path.getsize(src)))

    for name, content in GENERATED_FILES.items():
        path = os.path.join(STAGING, name)
        os.makedirs(os.path.dirname(path) or STAGING, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        copied.append((name + "（生成）", len(content.encode("utf-8"))))

    removed = []
    for name in OBSOLETE_FILES:
        path = os.path.join(STAGING, name)
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed.append(name)

    pruned = _prune_empty_dirs()

    for rel, size in copied:
        print("  写入 %-34s %8d 字节" % (rel, size))
    if removed:
        print()
        print("已删除 %d 个淘汰文件：" % len(removed))
        for name in removed:
            print("   ", name)
    if pruned:
        print("已清理空目录：%s" % ", ".join(pruned))

    print()
    print("已同步 %d 个文件到 %s" % (len(copied), STAGING))
    print("总体积：%.1f KB" % (sum(size for _r, size in copied) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
