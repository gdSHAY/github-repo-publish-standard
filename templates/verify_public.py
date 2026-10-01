# -*- coding: utf-8 -*-
"""匿名验证 —— 「发布成功」的唯一证据。

**全程不带 Authorization。** 带着 token 验等于什么都没验：
私有仓库、私有资产的 404 会被 token 遮住。

检查项
------
1. 仓库已公开          GET /repos/{o}/{r} → private=false
2. README 双语可读     两份 README 都取得到，且正文里含指向另一语言的相对链接
3. 截图可访问          每张 docs/*.png 取得到，且**字节数与本地一致**
                       （只看到 200 不算 —— 传上去一张旧的也可能 200）
4. 真实下载链接        releases/download/{tag}/{asset} 取得到，且前 4KB 与本地一致

双通道
------
`raw.githubusercontent.com` 与 `github.com` 的可达性跟 `api.github.com` **常常不一致**
（本机实测过：api 通、raw 超时）。所以每个资源都准备两条路：

    raw 通道      raw.githubusercontent.com/...            （首选，最接近真实读者体验）
    API 兜底      GET /repos/{o}/{r}/contents/<path>
                  Accept: application/vnd.github.raw+json （仍然是匿名请求）

最终报告会写明每一项实际走的是哪条通道 —— 「验证通过」必须能说清是怎么通过的。

用法
----
    python .tools/verify_public.py
"""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True  # 别在 .tools/ 留 __pycache__

import requests  # noqa: E402

from _repo_config import CFG, DEFAULT_BRANCH, OWNER, PROJECT, REPO  # noqa: E402

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

READY = "OK  "
FAIL = "FAIL"
SKIPPED = []


def session() -> requests.Session:
    s = requests.Session()
    # 关键：不带任何 Authorization。
    s.headers.pop("Authorization", None)
    s.headers["User-Agent"] = "%s-anon-verify" % REPO
    return s


def fetch_any(s: requests.Session, candidates: list) -> tuple:
    """依次尝试 [(url, headers), ...]，返回 (status, content, url, errors)。

    只有 5xx 与网络异常才继续往下试；4xx 是**明确的答案**（比如 404），直接返回。

    ⚠️ 超时必须**短**（连接 10s / 读 30s）。本机实测 raw 通道会整段假死，
    给 90s 会让「验证」变成一次几分钟的挂起 —— 而挂起比失败更难判断。
    """
    errors = []
    for url, headers in candidates:
        try:
            r = s.get(url, headers=headers or None, timeout=(10, 30))
            if r.status_code < 500:
                return r.status_code, r.content, url, None
            errors.append("%s -> HTTP %s" % (url, r.status_code))
        except requests.RequestException as exc:
            errors.append("%s -> %s" % (url, type(exc).__name__))
    return None, b"", "", "；".join(errors)


def _channel(url: str) -> str:
    return "api" if "api.github.com" in (url or "") else "raw"


# ---------------------------------------------------------------------------
def check_public(s: requests.Session) -> bool:
    r = s.get("%s/repos/%s/%s" % (API, OWNER, REPO), timeout=(8, 20))
    if r.status_code != 200:
        print("%s 仓库不可匿名访问：HTTP %s" % (FAIL, r.status_code))
        return False
    info = r.json()
    ok = not info.get("private")
    print("%s 仓库公开性：private=%s  stars=%s  size=%sKB"
          % (READY if ok else FAIL, info.get("private"),
             info.get("stargazers_count"), info.get("size")))
    return ok


def _file_candidates(rel_path: str, accept: str) -> list:
    return [
        ("%s/%s/%s/%s/%s" % (RAW, OWNER, REPO, DEFAULT_BRANCH, rel_path), None),
        ("%s/repos/%s/%s/contents/%s" % (API, OWNER, REPO, rel_path), {"Accept": accept}),
    ]


def check_readme(s: requests.Session) -> bool:
    readme = CFG["readme"]
    pairs = [(readme["zh_target"], readme["en_target"]),
             (readme["en_target"], readme["zh_target"])]
    ok = True
    for name, counterpart in pairs:
        status, content, url, err = fetch_any(
            s, _file_candidates(name, "application/vnd.github.raw+json"))
        if status != 200:
            print("%s %s → 取不到（%s）" % (FAIL, name, err or "HTTP %s" % status))
            ok = False
            continue
        text = content.decode("utf-8", errors="replace")
        has_link = ("./%s" % counterpart) in text
        print("%s %s → 200，%d 字节，切换链接%s（通道 %s）"
              % (READY if has_link else FAIL, name, len(content),
                 "存在" if has_link else "**缺失**", _channel(url)))
        ok = ok and has_link
    return ok


def check_images(s: requests.Session) -> bool:
    images = CFG["verify"].get("images") or []
    if not images:
        SKIPPED.append("截图校验（verify.images 未配置）")
        print("-- 跳过：截图校验（verify.images 未配置）")
        return True
    ok = True
    for rel in images:
        local = os.path.join(PROJECT, rel)
        status, content, url, err = fetch_any(
            s, _file_candidates(rel, "application/vnd.github.raw+json"))
        if status != 200:
            print("%s %s → 取不到（%s）" % (FAIL, rel, err or "HTTP %s" % status))
            ok = False
            continue
        if not os.path.isfile(local):
            print("-- %s → 200（本地无同名文件，跳过字节比对）" % rel)
            continue
        local_size = os.path.getsize(local)
        same = len(content) == local_size
        print("%s %s → 200，远端 %d / 本地 %d 字节%s（通道 %s）"
              % (READY if same else FAIL, rel, len(content), local_size,
                 "" if same else "  ← 不一致（是不是没同步？）", _channel(url)))
        ok = ok and same
    return ok


def check_release_assets(s: requests.Session) -> bool:
    rel = CFG.get("release") or {}
    assets = rel.get("assets") or []
    if not assets:
        SKIPPED.append("下载链接校验（release.assets 为空）")
        print("-- 跳过：下载链接校验（配置里没有 Release 资产）")
        return True

    tag = rel["tag"]
    # 先拿一次资产清单，供 API 兜底用（匿名请求，公开仓库可读）
    by_name = {}
    try:
        r = s.get("%s/repos/%s/%s/releases/tags/%s" % (API, OWNER, REPO, tag),
                  timeout=(8, 20))
        if r.status_code == 200:
            for item in r.json().get("assets") or []:
                by_name[item["name"]] = item["id"]
    except requests.RequestException:
        pass

    ok = True
    for item in assets:
        name = item["name"]
        local = item["path"]
        if not os.path.isabs(local):
            local = os.path.join(PROJECT, local)

        cands = [("https://github.com/%s/%s/releases/download/%s/%s" % (OWNER, REPO, tag, name),
                  {"Range": "bytes=0-4095"})]
        if name in by_name:
            cands.append(("%s/repos/%s/%s/releases/assets/%s"
                          % (API, OWNER, REPO, by_name[name]),
                          {"Accept": "application/octet-stream",
                           "Range": "bytes=0-4095"}))

        status, content, url, err = fetch_any(s, cands)
        if status is None:
            print("%s %s → 两条通道都不通（%s）" % (FAIL, name, err))
            ok = False
            continue
        # 206 = 服务端接受了 Range，比 200 更能证明是同一个文件
        good = status in (200, 206) and len(content) > 0
        detail = "HTTP %s，前 %d 字节（通道 %s）" % (status, len(content), _channel(url))
        if good and os.path.isfile(local):
            with open(local, "rb") as handle:
                head = handle.read(len(content))
            if head == content:
                detail += "，与本地一致"
            else:
                detail += "，**与本地不一致**"
                good = False
        elif good:
            detail += "（本地无同名文件，跳过比对）"
        print("%s %s → %s" % (READY if good else FAIL, name, detail))
        ok = ok and good
    return ok


def main() -> int:
    print("匿名验证 %s/%s（不带 Authorization）" % (OWNER, REPO))
    print("-" * 66)
    s = session()

    results = {
        "仓库公开": check_public(s),
        "README 双语": check_readme(s),
        "截图字节": check_images(s),
        "下载链接": check_release_assets(s),
    }

    print("-" * 66)
    for label, ok in results.items():
        print("%s %s" % (READY if ok else FAIL, label))
    if SKIPPED:
        print()
        print("跳过 %d 项（不算通过）：" % len(SKIPPED))
        for name in SKIPPED:
            print("   -", name)
    bad = [k for k, v in results.items() if not v]
    if bad:
        print()
        print("未通过：%s" % "、".join(bad))
        return 1
    print()
    print("全部通过 —— 任何人都可以打开链接、看到 README、拿到文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
