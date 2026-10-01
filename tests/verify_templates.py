# -*- coding: utf-8 -*-
"""验证台：用 templates/ 里的模板真实跑一遍「同步 -> git init -> 单测」，
并做反向验证（故意破坏，确认单测会失败）。

改过任何模板后必须重跑这个 —— 它测的是**模板本身**能不能用。

跑法（需要 requests 的解释器）：
    python tests/verify_templates.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TPL = os.path.join(SKILL, "templates")
PY = sys.executable

GIT = shutil.which("git") or r"C:\g\Git\cmd\git.exe"
if not os.path.isfile(GIT) and not shutil.which("git"):
    raise SystemExit("[失败] 找不到 git：%s" % GIT)

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
    "0000000c4944415408d763f8cfc000000301010018dd8db00000000049454e44ae426082"
)

ZH = """<div align="center">

<h1>测试工具</h1>

**简体中文** | [English](./README.en.md)

</div>

---

这是一个用于离线校验的测试项目，用来演示双语门面与发布流程是否完整可用。

## 🎬 它长什么样

<img src="./docs/home.png" width="880" alt="界面">

## 📥 下载安装

| 文件 | 说明 |
| --- | --- |
| `app-1.0.0.zip` | Windows 包 |

## ⚙️ 三步开始用

先下载，再解压，最后双击运行即可，全过程不需要联网。

## ⚠️ 能力边界

只支持在本机运行，不提供任何云端服务，也不支持多用户同时使用。

## 🧱 技术栈

纯 Python，没有构建步骤，也不需要额外的运行时环境。

## ❓ 常见问题

如果窗口一闪而过，通常是缺少配套文件夹，请整体解压后再运行。

## 📄 合规与免责

仅供个人学习与技术交流使用，请勿用于商业用途，风险由使用者自行承担。

## 📄 许可

未附带开源许可证，保留所有权利。
"""

EN = """<div align="center">

<h1>Test Tool</h1>

[简体中文](./README.md) | **English**

</div>

---

A tiny project used to validate the bilingual README convention offline.

## 🎬 What it looks like

<img src="./docs/home.png" width="880" alt="UI">

## 📥 Download

| File | Note |
| --- | --- |
| `app-1.0.0.zip` | Windows package |

## ⚙️ Three steps to start

Download, unzip, then double-click to run. No network required at all.

## ⚠️ Limits

Local use only. No cloud service, and no multi-user support whatsoever.

## 🧱 Tech stack

Plain Python with no build step and no extra runtime needed.

## ❓ FAQ

If the window flashes and closes, you probably extracted only the exe.

## 📄 Legal and disclaimer

For personal study and technical exchange only. You bear the risk.

## 📄 License

Not licensed. All rights reserved.
"""

CONFIG = {
    "owner": "example",
    "repo": "verify-rig",
    "default_branch": "main",
    "default_language": "zh",
    "staging_dir": "发布仓库",
    "readme": {"zh_source": "项目主页.md", "en_source": "项目主页.en.md",
               "zh_target": "README.md", "en_target": "README.en.md"},
    "include": ["server.py", {"src": "docs/*.png", "dst": "docs/*.png"}],
    "never_publish": ["secret_config.json", "data/"],
    "obsolete": ["Dockerfile"],
    "ignored_top": [".git"],
    "generate": {".gitignore": "data/\n*_config.json\n__pycache__/\n"},
    "release": {"tag": "v1.0.0", "name": "v1.0.0", "body_file": ".tools/body.md",
                "assets": [{"path": "dist/app-1.0.0.zip", "name": "app-1.0.0.zip"}]},
    "verify": {"images": ["docs/home.png"],
               "required_sections_zh": ["## ⚠️"], "required_sections_en": ["## ⚠️"]},
}

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print("  %s %s%s" % ("PASS" if ok else "FAIL", name,
                         ("  ← " + detail) if detail and not ok else ""))


def build(root, cfg=None):
    os.makedirs(os.path.join(root, ".tools"), exist_ok=True)
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    os.makedirs(os.path.join(root, "dist"), exist_ok=True)

    for name in ("_repo_config.py", "sync_staging.py", "publish_release.py",
                 "verify_public.py", "make_readme_assets.py"):
        shutil.copy2(os.path.join(TPL, name), os.path.join(root, ".tools", name))
    shutil.copy2(os.path.join(TPL, "check_repo.py"), os.path.join(root, "仓库单测.py"))

    with open(os.path.join(root, ".tools", "repo_config.json"), "w",
              encoding="utf-8") as h:
        json.dump(cfg or CONFIG, h, ensure_ascii=False, indent=2)

    with open(os.path.join(root, "项目主页.md"), "w", encoding="utf-8") as h:
        h.write(ZH)
    with open(os.path.join(root, "项目主页.en.md"), "w", encoding="utf-8") as h:
        h.write(EN)
    with open(os.path.join(root, "server.py"), "w", encoding="utf-8") as h:
        h.write("# -*- coding: utf-8 -*-\nprint('hello')\n")
    with open(os.path.join(root, "secret_config.json"), "w", encoding="utf-8") as h:
        json.dump({"sessdata": "A" * 40}, h)
    with open(os.path.join(root, "docs", "home.png"), "wb") as h:
        h.write(PNG)
    with open(os.path.join(root, "Dockerfile"), "w", encoding="utf-8") as h:
        h.write("FROM python:3.12\n")
    with open(os.path.join(root, "dist", "app-1.0.0.zip"), "wb") as h:
        h.write(b"PK\x03\x04" + b"x" * 2048)


def run(args, cwd):
    return subprocess.run([PY] + args, cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def run_raw(args, cwd):
    """不预置解释器 —— 给 git 这类可执行文件用。"""
    return subprocess.run(args, cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def main() -> int:
    root = tempfile.mkdtemp(prefix="_skillrig_")
    print("验证台：%s\n" % root)
    try:
        build(root)

        # --- 1. 同步 ---
        print("[1] sync_staging.py")
        r = run([os.path.join(".tools", "sync_staging.py")], root)
        record("同步脚本退出码 0", r.returncode == 0, (r.stdout + r.stderr)[-400:])

        staging = os.path.join(root, "发布仓库")
        record("staging 已生成", os.path.isdir(staging))
        record("README.md 已由 项目主页.md 生成",
               os.path.isfile(os.path.join(staging, "README.md")))
        record("README.en.md 已生成",
               os.path.isfile(os.path.join(staging, "README.en.md")))
        record(".gitignore 已生成（非复用工程根）",
               os.path.isfile(os.path.join(staging, ".gitignore")))
        record("docs/home.png 已同步",
               os.path.isfile(os.path.join(staging, "docs", "home.png")))
        record("凭据文件未同步",
               not os.path.exists(os.path.join(staging, "secret_config.json")))
        record("构建产物未同步（dist/ 不在）",
               not os.path.exists(os.path.join(staging, "dist")))
        record("Dockerfile 未进 staging",
               not os.path.exists(os.path.join(staging, "Dockerfile")))

        # --- 2. --check 幂等 ---
        print("\n[2] sync_staging.py --check（应报一致）")
        r = run([os.path.join(".tools", "sync_staging.py"), "--check"], root)
        record("--check 退出码 0", r.returncode == 0, (r.stdout + r.stderr)[-400:])
        record("--check 输出「一致」", "一致" in r.stdout, r.stdout[-200:])

        # --- 3. git 工作区 ---
        print("\n[3] git init + 造 .git 内部空目录")
        for cmd in ([GIT, "init", "-q"], [GIT, "config", "user.email", "t@example.com"],
                    [GIT, "config", "user.name", "t"]):
            run_raw(cmd, staging)
        # 新版 git 惰性创建，objects/info 等可能不存在 —— 手工补齐，
        # 因为老版本 git（以及本项目的实测环境）确实有这几个空目录。
        git_empties = ["objects/info", "objects/pack", "refs/tags"]
        for d in git_empties:
            os.makedirs(os.path.join(staging, ".git", d), exist_ok=True)
        existing = [d for d in git_empties
                    if os.path.isdir(os.path.join(staging, ".git", d))]
        record(".git 存在", os.path.isdir(os.path.join(staging, ".git")))
        record("内部空目录就位（%d 个）" % len(existing), len(existing) == 3)

        # 再同步一次，验证 .git 内部空目录没被清理掉
        r = run([os.path.join(".tools", "sync_staging.py")], root)
        survived = [d for d in git_empties
                    if os.path.isdir(os.path.join(staging, ".git", d))]
        record("二次同步后 .git 内部空目录存活（%d/%d）"
               % (len(survived), len(existing)), len(survived) == len(existing),
               "被删：%s" % sorted(set(existing) - set(survived)))
        record("二次同步后 HEAD 仍在",
               os.path.isfile(os.path.join(staging, ".git", "HEAD")))

        # --- 4. 单测：应全过 ---
        print("\n[4] 仓库单测.py（期望退出码 0）")
        r = run(["仓库单测.py"], root)
        record("单测退出码 0", r.returncode == 0, (r.stdout + r.stderr)[-1200:])
        record("单测输出「全部通过」", "全部通过" in r.stdout, r.stdout[-300:])
        record("无 FAIL 行", "FAIL" not in r.stdout, r.stdout[-400:])

        # --- 5. 幂等：再跑一次单测，不应出 __pycache__ ---
        print("\n[5] 幂等复跑")
        r = run(["仓库单测.py"], root)
        record("复跑仍退出码 0", r.returncode == 0)
        pycache = [os.path.join(c, d) for c, ds, _f in os.walk(os.path.join(root, ".tools"))
                   for d in ds if d == "__pycache__"]
        record("复跑后 .tools/ 无 __pycache__（%d）" % len(pycache), not pycache,
               "; ".join(pycache))

        # --- 6. 反证：破坏英文版图片引用 -> 单测必须失败 ---
        print("\n[6] 反证 A：英文版删掉图片引用，单测应失败")
        en_path = os.path.join(staging, "README.en.md")
        with open(en_path, encoding="utf-8") as h:
            text = h.read()
        with open(en_path, "w", encoding="utf-8") as h:
            h.write(text.replace('<img src="./docs/home.png" width="880" alt="UI">', ""))
        r = run(["仓库单测.py"], root)
        record("单测确实失败（退出码非 0）", r.returncode != 0, r.stdout[-300:])
        record("失败原因指向图片镜像",
               "图片引用两版一致" in r.stdout or "图片" in r.stdout, r.stdout[-500:])

        # --- 7. 反证：注入凭据 -> 单测必须失败 ---
        print("\n[7] 反证 B：向 staging 注入假 token，单测应失败")
        run([os.path.join(".tools", "sync_staging.py")], root)  # 先复原
        leak = os.path.join(staging, "leak.py")
        with open(leak, "w", encoding="utf-8") as h:
            h.write('TOKEN = "ghp_%s"\n' % ("A" * 36))
        r = run(["仓库单测.py"], root)
        record("单测确实失败", r.returncode != 0)
        record("命中通用凭据模式", "GitHub token" in r.stdout, r.stdout[-500:])
        os.remove(leak)

        # --- 8. 反证 C：配置是否真的驱动行为 ---
        print("\n[8] 反证 C：新工程配 ignored_top=[]，同步应删掉 .git 内部空目录")
        root2 = tempfile.mkdtemp(prefix="_skillrig2_")
        try:
            cfg2 = dict(CONFIG)
            cfg2["ignored_top"] = []
            build(root2, cfg2)
            st2 = os.path.join(root2, "发布仓库")
            run([os.path.join(".tools", "sync_staging.py")], root2)
            run_raw([GIT, "init", "-q"], st2)
            for d in git_empties:
                os.makedirs(os.path.join(st2, ".git", d), exist_ok=True)
            before2 = [d for d in git_empties
                       if os.path.isdir(os.path.join(st2, ".git", d))]
            run([os.path.join(".tools", "sync_staging.py")], root2)
            after2 = [d for d in git_empties
                      if os.path.isdir(os.path.join(st2, ".git", d))]
            record("配置 ignored_top=[] 时确实被删（%d -> %d）"
                   % (len(before2), len(after2)),
                   len(before2) == 3 and len(after2) == 0,
                   "证明 repo_config 的 ignored_top 真的驱动了清理逻辑")
        finally:
            shutil.rmtree(root2, ignore_errors=True)

        # --- 9. 反证：README 里写错资产名 -> 单测必须失败 ---
        print("\n[9] 反证 D：README 写不存在的资产名，单测应失败")
        with open(os.path.join(root, "项目主页.md"), "w", encoding="utf-8") as h:
            h.write(ZH.replace("`app-1.0.0.zip`", "`app-9.9.9.zip`"))
        run([os.path.join(".tools", "sync_staging.py")], root)
        r = run(["仓库单测.py"], root)
        record("单测确实失败", r.returncode != 0)
        skip = "跳过" in r.stdout and "publish_release" in r.stdout
        record("检查了资产名一致性" + ("（但 import 失败被跳过）" if skip else ""),
               ("资产名" in r.stdout) or skip, r.stdout[-500:])

        # --- 10. 反证 E：把本机凭据值抄进仓库 -> 反向扫描必须命中 ---
        # 通用模式扫描抓不到这种「自定义字段名 + 真实值」，只有反查能抓。
        print("\n[10] 反证 E：把本机配置里的真实值写进 staging，单测应失败")
        with open(os.path.join(root, "项目主页.md"), "w", encoding="utf-8") as h:
            h.write(ZH)  # 先把上一节改坏的资产名复原
        run([os.path.join(".tools", "sync_staging.py")], root)
        leak_file = os.path.join(staging, "notes.txt")
        with open(leak_file, "w", encoding="utf-8") as h:
            h.write("backup token = %s\n" % ("A" * 40))  # 与 secret_config.json 同值
        r = run(["仓库单测.py"], root)
        record("单测确实失败", r.returncode != 0)
        # ⚠️ 别去匹配「0 命中」这种字样：那是检查项的固定名称，
        # 无论成败都会出现，写成条件会恒假（这个坑本轮真踩了）。
        # 判据要用**失败标记本身**。
        record("命中「本机真实凭据反查」",
               "FAIL 本机真实凭据反查" in r.stdout, r.stdout[-600:])
        os.remove(leak_file)

    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\n" + "=" * 62)
    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print("共 %d 项，失败 %d 项" % (len(RESULTS), len(failed)))
    for n, d in failed:
        print("   FAIL %s  %s" % (n, d[:200]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
