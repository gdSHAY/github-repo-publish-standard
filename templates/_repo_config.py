# -*- coding: utf-8 -*-
"""读取 .tools/repo_config.json —— 所有模板脚本共用这一份配置。

放到目标工程的 `.tools/` 下，与 `repo_config.json` 同级。
脚本顶部这样引入：

    from _repo_config import PROJECT, HERE, CFG
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
CONFIG_PATH = os.path.join(HERE, "repo_config.json")


def _strip_comments(node):
    """去掉以 `_` 开头的说明键，避免误用。"""
    if isinstance(node, dict):
        return {k: _strip_comments(v) for k, v in node.items() if not k.startswith("_")}
    if isinstance(node, list):
        return [_strip_comments(v) for v in node]
    return node


def load(path: str = "") -> dict:
    path = path or CONFIG_PATH
    if not os.path.isfile(path):
        raise SystemExit("[失败] 找不到配置：%s\n"
                         "请把 templates/repo_config.json 拷到 .tools/ 并改好参数。" % path)
    with open(path, encoding="utf-8") as handle:
        return _strip_comments(json.load(handle))


CFG = load()

OWNER = CFG["owner"]
REPO = CFG["repo"]
DEFAULT_BRANCH = CFG.get("default_branch", "main")
STAGING = os.path.join(PROJECT, CFG["staging_dir"])

# ⚠️ 不能写成 `CFG.get("ignored_top") or [".git"]` ——
# 空列表是 falsy，会把「显式配置成空」误判成「未配置」，导致保护关不掉。
# 必须区分 None（缺省）与 []（显式关闭）。
_ignored = CFG.get("ignored_top")
IGNORED_TOP = set([".git"] if _ignored is None else _ignored)


def token() -> str:
    """取 GitHub token：优先 .tools/gh_token.txt，其次 `gh auth token`。"""
    import subprocess

    tok_path = os.path.join(HERE, "gh_token.txt")
    if os.path.isfile(tok_path):
        with open(tok_path, encoding="utf-8") as handle:
            value = handle.read().strip()
        if value:
            return value
    gh = os.path.join(HERE, "bin", "gh.exe")
    cmd = [gh, "auth", "token"] if os.path.isfile(gh) else ["gh", "auth", "token"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("[失败] 拿不到 token：%s" % (out.stderr or out.stdout)[:300])
    return out.stdout.strip()
