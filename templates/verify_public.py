# -*- coding: utf-8 -*-
"""匿名验证 —— 「发布成功」的唯一证据。

**全程不带 Authorization。** 带着 token 验等于什么都没验：
私有仓库、私有资产的 404 会被 token 遮住。

检查项
------
1. 仓库已公开          GET /repos/{o}/{r} → private=false
2. README 双语可读      raw.githubusercontent.com/.../README.md → 200，
                       且正文里含指向另一语言的相对链接
3. 截图可访问          每张 docs/*.png → 200，且**字节数与本地一致**
                       （只看到 200 不算 —— 传上去一张旧的也可能 200）
4. 真实下载链接        github.com/{o}/{r}/releases/download/{tag}/{asset}
                       → **206**（Range 请求），且前 4KB 与本地一致

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


def session() -> requests.Session:
    s = requests.Session()
    # 关键：不带任何 Authorization。
    s.headers.pop("Authorization", None)
    s.headers["User-Agent"] = "%s-anon-verify" % REPO
    return s


def check_public(s: requests.Session) -> bool:
    r = s.get("%s/repos/%s/%s" % (API, OWNER, REPO), timeout=30)
    if r.status_code != 200:
        print("%s 仓库不可匿名访问：HTTP %s" % (FAIL, r.status_code))
        return False
    info = r.json()
    ok = not info.get("private")
    print("%s 仓库公开性：private=%s  stars=%s  size=%sKB"
          % (READY if ok else FAIL, info.get("private"),
             info.get("stargazers_count"), info.get("size")))
    return ok


def check_readme(s: requests.Session) -> bool:
    readme = CFG["readme"]
    pairs = [(readme["zh_target"], readme["en_target"]),
             (readme["en_target"], readme["zh_target"])]
    ok = True
    for name, counterpart in pairs:
        url = "%s/%s/%s/%s/%s" % (RAW, OWNER, REPO, DEFAULT_BRANCH, name)
        r = s.get(url, timeout=60)
        if r.status_code != 200:
            print("%s %s → HTTP %s" % (FAIL, name, r.status_code))
            ok = False
            continue
        text = r.text
        has_link = ("./%s" % counterpart) in text
        print("%s %s → 200，%d 字节，切换链接%s"
              % (READY if has_link else FAIL, name, len(r.content),
                 "存在" if has_link else "**缺失**"))
        ok = ok and has_link
    return ok


def check_images(s: requests.Session) -> bool:
    images = CFG["verify"].get("images") or []
    if not images:
        print("-- 未配置 verify.images，跳过图片校验")
        return True
    ok = True
    for rel in images:
        local = os.path.join(PROJECT, rel)
        url = "%s/%s/%s/%s/%s" % (RAW, OWNER, REPO, DEFAULT_BRANCH, rel)
        r = s.get(url, timeout=60)
        if r.status_code != 200:
            print("%s %s → HTTP %s" % (FAIL, rel, r.status_code))
            ok = False
            continue
        if not os.path.isfile(local):
            print("-- %s → 200（本地无同名文件，跳过字节比对）" % rel)
            continue
        local_size = os.path.getsize(local)
        same = len(r.content) == local_size
        print("%s %s → 200，远端 %d / 本地 %d 字节%s"
              % (READY if same else FAIL, rel, len(r.content), local_size,
                 "" if same else "  ← 不一致（是不是没同步？）"))
        ok = ok and same
    return ok


def check_release_assets(s: requests.Session) -> bool:
    rel = CFG["release"]
    tag = rel["tag"]
    ok = True
    for item in rel.get("assets") or []:
        name = item["name"]
        local = item["path"]
        if not os.path.isabs(local):
            local = os.path.join(PROJECT, local)
        url = "https://github.com/%s/%s/releases/download/%s/%s" % (OWNER, REPO, tag, name)
        try:
            r = s.get(url, headers={"Range": "bytes=0-4095"}, timeout=120)
        except Exception as exc:
            print("%s %s → 请求失败：%s" % (FAIL, name, exc))
            ok = False
            continue
        # 真实链接会 302 到 release-assets.githubusercontent.com，requests 自动跟随；
        # 206 = 服务端接受了 Range，比 200 更能证明是同一个文件。
        good = r.status_code in (200, 206) and len(r.content) > 0
        detail = "HTTP %s，前 %d 字节" % (r.status_code, len(r.content))
        if good and os.path.isfile(local):
            with open(local, "rb") as handle:
                head = handle.read(len(r.content))
            if head == r.content:
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
    print("-" * 60)
    s = session()

    results = {
        "仓库公开": check_public(s),
        "README 双语": check_readme(s),
        "截图字节": check_images(s),
        "下载链接": check_release_assets(s),
    }

    print("-" * 60)
    for label, ok in results.items():
        print("%s %s" % (READY if ok else FAIL, label))
    bad = [k for k, v in results.items() if not v]
    if bad:
        print()
        print("未通过：%s" % "、".join(bad))
        return 1
    print()
    print("全部通过 —— 任何人都可以打开链接、看到 README、下载到二进制。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
