# -*- coding: utf-8 -*-
"""把发行版（安装包 / 压缩包 / APK）上传到 GitHub Releases。

为什么单独一个脚本
------------------
推**代码**走 git（或 Git Data API），但二进制不适合塞进 git 对象库 ——
动辄几十 MB，而且每次发版都会换。Releases 才是放二进制的正路。

为什么要走 API 而不是网页
------------------------
① 可脚本化、可幂等、可复核；② 本机 `github.com` 不可达时
`api.github.com` / `uploads.github.com` 往往仍然通。

幂等
----
重复跑不会炸：
  · 同名 tag 的 Release 已存在 → 复用，不新建；
  · 同名资产已存在且**字节数一致** → 跳过；
  · 字节数不同 → 先删旧的再传（防止上次中断留下半截文件。
    ⚠️ 只看 HTTP 200 不够 —— 半截上传也可能返回 200）。

安全性
------
**默认 dry-run**，加 `--push` 才真的写。只可能删「同名的资产」，不会删 Release。

用法
----
    python .tools/publish_release.py            # 只看会做什么
    python .tools/publish_release.py --push     # 真上传
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

sys.dont_write_bytecode = True  # 别在 .tools/ 留 __pycache__

import requests  # noqa: E402

from _repo_config import (  # noqa: E402, F401
    CFG, DEFAULT_BRANCH, HERE, OWNER, PROJECT, REPO, token,
)

API = "https://api.github.com"
UPLOAD_API = "https://uploads.github.com"

REL = CFG["release"]
TAG = REL["tag"]
RELEASE_NAME = REL.get("name") or TAG

#: (本地绝对路径, Release 上的资产名)
#: ⚠️ 资产名必须与 README 里写的**逐字一致** —— check_repo.py 会双向核对。
ASSETS = []
for _item in REL.get("assets") or []:
    path = _item["path"]
    if not os.path.isabs(path):
        path = os.path.join(PROJECT, path)
    ASSETS.append((path, _item["name"]))


def release_body() -> str:
    """发布说明正文：优先读 body_file（改本地即生效），否则用内联默认值。"""
    body_file = REL.get("body_file")
    if body_file:
        path = body_file if os.path.isabs(body_file) else os.path.join(PROJECT, body_file)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        print("[提示] body_file 不存在（%s），退回内联正文。" % body_file)
    return REL.get("body") or ""


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Api:
    def __init__(self, tok: str) -> None:
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": "Bearer %s" % tok,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "%s-release-push" % REPO,
        })
        # 用环境/注册表的系统代理（沙箱里它才通 api.github.com）。
        # 若你的环境必须直连，改成 False。
        self.s.trust_env = True

    def get(self, path: str, ok404: bool = False):
        r = self.s.get(API + path, timeout=60)
        if r.status_code == 404 and ok404:
            return None
        if r.status_code >= 300:
            raise RuntimeError("GET %s -> %s %s" % (path, r.status_code, r.text[:300]))
        return r.json()

    def post(self, path: str, payload: dict):
        r = self.s.post(API + path, json=payload, timeout=120)
        if r.status_code >= 300:
            raise RuntimeError("POST %s -> %s %s" % (path, r.status_code, r.text[:300]))
        return r.json()

    def patch(self, path: str, payload: dict):
        r = self.s.patch(API + path, json=payload, timeout=60)
        if r.status_code >= 300:
            raise RuntimeError("PATCH %s -> %s %s" % (path, r.status_code, r.text[:300]))
        return r.json()

    def delete(self, path: str) -> int:
        return self.s.delete(API + path, timeout=60).status_code


def find_release(api: Api, tag: str):
    """按 tag 找 Release。用 `/releases/tags/{tag}` 比翻列表稳（避免分页）。"""
    return api.get("/repos/%s/%s/releases/tags/%s" % (OWNER, REPO, tag), ok404=True)


def asset_state(release: dict) -> dict:
    """{资产名: (id, 字节数)}"""
    return {it["name"]: (it["id"], it["size"]) for it in (release.get("assets") or [])}


def upload(api: Api, release_id: int, local_path: str, name: str) -> dict:
    """流式上传单个资产（几十 MB 不要整个读进内存再拼 base64）。"""
    size = os.path.getsize(local_path)
    url = "%s/repos/%s/%s/releases/%s/assets" % (UPLOAD_API, OWNER, REPO, release_id)
    with open(local_path, "rb") as handle:
        r = api.s.post(
            url,
            params={"name": name},
            data=handle,
            headers={"Content-Type": "application/octet-stream",
                     "Content-Length": str(size)},
            timeout=(30, 1800),  # 大文件经代理，读超时给足
        )
    if r.status_code >= 300:
        raise RuntimeError("上传 %s -> %s %s" % (name, r.status_code, r.text[:300]))
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser(description="上传发行版到 GitHub Releases")
    ap.add_argument("--push", action="store_true", help="真的创建 Release 并上传")
    ap.add_argument("--repo", default="", help="覆盖 owner/repo（默认读配置）")
    args = ap.parse_args()

    body = release_body()

    plan = []
    for path, name in ASSETS:
        if not os.path.isfile(path):
            print("[失败] 找不到本地文件：%s" % path)
            return 2
        plan.append((path, name, os.path.getsize(path)))

    print("仓库：%s/%s     tag：%s" % (OWNER, REPO, TAG))
    print("待上传 %d 个资产：" % len(plan))
    for path, name, size in plan:
        print("  %-42s %8.1f MB  sha256=%s…"
              % (name, size / 1024 / 1024, sha256(path)[:16]))

    api = Api(token())
    release = find_release(api, TAG)

    if release is None:
        print()
        print("Release %s 不存在，将新建。" % TAG)
        todo, body_stale = plan, False
    else:
        state = asset_state(release)
        print()
        print("Release %s 已存在（id=%s，%d 个资产）。" % (TAG, release["id"], len(state)))
        todo = []
        for path, name, size in plan:
            old = state.get(name)
            if old is None:
                print("  + %s 需要上传" % name)
                todo.append((path, name, size))
            elif old[1] == size:
                print("  = %s 已存在且字节数一致，跳过" % name)
            else:
                print("  M %s 字节数不同（远端 %d / 本地 %d），将替换" % (name, old[1], size))
                todo.append((path, name, size))
        body_stale = (release.get("body") or "").strip() != body.strip()
        if body_stale:
            print("  M 发布说明与本地不一致，将更新")

    if not args.push:
        print()
        print("[dry-run] 加 --push 才真的执行。")
        return 0

    if release is None:
        release = api.post("/repos/%s/%s/releases" % (OWNER, REPO), {
            "tag_name": TAG,
            "name": RELEASE_NAME,
            "body": body,
            "draft": bool(REL.get("draft")),
            "prerelease": bool(REL.get("prerelease")),
            "target_commitish": DEFAULT_BRANCH,
        })
        print()
        print("已创建 Release：%s" % release["html_url"])
    elif body_stale:
        release = api.patch("/repos/%s/%s/releases/%s" % (OWNER, REPO, release["id"]),
                            {"body": body})
        print("已更新发布说明。")

    state = asset_state(release)
    for _path, name, size in todo:
        old = state.get(name)
        if old is not None and old[1] != size:
            code = api.delete("/repos/%s/%s/releases/assets/%s" % (OWNER, REPO, old[0]))
            print("  已删除旧资产 %s（HTTP %s）" % (name, code))

    for path, name, size in todo:
        print("  上传 %s（%.1f MB）…" % (name, size / 1024 / 1024))
        info = upload(api, release["id"], path, name)
        print("    → %s  %d 字节" % (info["name"], info["size"]))

    final = api.get("/repos/%s/%s/releases/tags/%s" % (OWNER, REPO, TAG))
    print()
    print("完成。Release 页：%s" % final["html_url"])
    for item in final["assets"]:
        print("  %-42s %8.1f MB" % (item["name"], item["size"] / 1024 / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
