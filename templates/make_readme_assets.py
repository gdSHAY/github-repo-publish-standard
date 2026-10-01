# -*- coding: utf-8 -*-
"""重生成 README 用的图片素材（`docs/` 下那几张）。

界面一改，README 里的截图就过期了。把整条链路固化成一条命令，
不要每次再去写临时脚本（`_shot.py`、`_probe.py` 这种用完即弃的东西最容易留垃圾）。

    python .tools/make_readme_assets.py                 # 只用已有素材合成对比图
    python .tools/make_readme_assets.py --with-shots    # 连截图一起重拍（会临时起本机服务）

前提
----
· playwright 的 chromium 已下载（`playwright install chromium`）
· 合成中文标签需要中文字体（Windows 用 msyh.ttc / msyhbd.ttc）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request

sys.dont_write_bytecode = True  # 别在 .tools/ 留 __pycache__

from _repo_config import PROJECT  # noqa: E402

# ---------------------------------------------------------------------------
# 按项目改这一段
# ---------------------------------------------------------------------------

DOCS = os.path.join(PROJECT, "docs")

#: 截图用的独立端口 —— **不要**用你正在跑的服务那个端口
SHOT_PORT = 8790
SERVER_CMD = [sys.executable, "server.py", "--no-browser"]
HEALTH_PATH = "/"

#: 页面元素 id（先去前端源码 grep 'id="' 确认真实 id，别猜）
SEL_INPUT = "#input"
SEL_BUTTON = "#btnParse"
SEL_RESULT = "#result"
SEL_RESULT_READY = "#result .btn-dl"

#: 截图要用的真实输入 —— 换一条时要确认能解析成功，否则那一步会跳过
SAMPLE_INPUT = "https://example.com/item/xxxx"

#: 视口。初始页按元素实测高度定，这里给上下限避免极端值
VIEW_WIDTH = 1400
HOME_MIN_H, HOME_MAX_H = 420, 1400
RESULT_MIN_H, RESULT_MAX_H = 600, 3000

#: 前后对比图（两张素材通常同尺寸）
CMP_SCALE = 0.72
CMP_MARK = (452, 902, 533, 950)      # 差异区域包围盒（+ 余量）
CMP_SOURCE = ("素材/原图_带水印.png", "素材/原图_无水印.png")
CMP_OUT = "watermark-compare.png"
CMP_TITLE = "同一件作品 · 平台播放流 vs 原图直链"
CMP_LEFT = ("平台播放流 · 右下角带平台水印", "× 带水印")
CMP_RIGHT = ("原图直链 · 同一位置干净无水印", "√ 无水印")

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


# ---------------------------------------------------------------------------
def shoot() -> None:
    """拉起本机服务，拍界面截图。拍完关掉，不碰你正在跑的服务。"""
    from playwright.sync_api import sync_playwright

    env = dict(os.environ)
    env["PORT"] = str(SHOT_PORT)
    env["PYTHONUNBUFFERED"] = "1"
    log_path = os.path.join(PROJECT, "_readme_shot_server.log")
    log = open(log_path, "wb")
    proc = subprocess.Popen(SERVER_CMD, cwd=PROJECT, env=env,
                            stdout=log, stderr=subprocess.STDOUT)
    base = "http://127.0.0.1:%d" % SHOT_PORT
    # 本机地址必须绕开环境代理，否则请求会被丢给代理而超时
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    try:
        for i in range(60):
            time.sleep(1)
            try:
                with opener.open(base + HEALTH_PATH, timeout=3) as resp:
                    if resp.status == 200:
                        print("  服务就绪（第 %ds）" % (i + 1))
                        break
            except Exception:
                pass
        else:
            raise SystemExit("[失败] 服务没起来，看 %s" % log_path)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": VIEW_WIDTH, "height": HOME_MIN_H},
                                    device_scale_factor=2)
            page.goto(base + HEALTH_PATH, wait_until="networkidle", timeout=60000)
            time.sleep(1.2)

            # 1) 初始界面：按实测元素高度定视口，避免底部被裁 / 大片留白
            try:
                height = page.evaluate(
                    "() => Math.max(document.body.scrollHeight,"
                    " document.documentElement.scrollHeight)")
                height = min(max(int(height), HOME_MIN_H), HOME_MAX_H)
                page.set_viewport_size({"width": VIEW_WIDTH, "height": height})
                time.sleep(0.4)
            except Exception:
                pass
            out = os.path.join(DOCS, "screenshot-home-zh.png")
            page.screenshot(path=out)
            print("  已存 %s（%d 字节）" % (os.path.basename(out), os.path.getsize(out)))

            # 2) 结果页：真发一次请求 —— 截图里得有真东西，不能用假数据糊
            try:
                page.set_viewport_size({"width": VIEW_WIDTH, "height": 1000})
                page.fill(SEL_INPUT, SAMPLE_INPUT)
                page.click(SEL_BUTTON)
                page.wait_for_selector(SEL_RESULT_READY, timeout=120000)
                time.sleep(3.0)  # 等图片 / 视频帧渲染完
                box = page.evaluate(
                    "() => { const a = document.querySelector('%s');"
                    " if (!a) return null; const r = a.getBoundingClientRect();"
                    " return {top: r.top + window.scrollY, h: r.height}; }" % SEL_RESULT)
                height = RESULT_MIN_H
                if box:
                    height = min(max(int(box["top"] + box["h"]) + 40, RESULT_MIN_H),
                                 RESULT_MAX_H)
                page.set_viewport_size({"width": VIEW_WIDTH, "height": height})
                time.sleep(0.6)
                out = os.path.join(DOCS, "screenshot-result-zh.png")
                page.screenshot(path=out)
                print("  已存 %s（%d 字节，视口高 %d）"
                      % (os.path.basename(out), os.path.getsize(out), height))
            except Exception as exc:
                print("  [跳过] 结果图没截到：%s: %s"
                      % (type(exc).__name__, str(exc)[:140]))

            browser.close()
    finally:
        proc.kill()
        log.close()


# ---------------------------------------------------------------------------
def make_compare() -> None:
    """合成「带水印 / 无水印」或任意「改前 / 改后」对比图。

    要点：**同一个坐标框同时框住两张图** —— 左边框里有目标、右边没有，才叫对比。
    框的位置先用「亮像素计数」机械化定位，别用肉眼估。
    """
    from PIL import Image, ImageDraw, ImageFont

    for cand in (FONT, FONT_BOLD):
        if not os.path.isfile(cand):
            raise SystemExit("[失败] 缺中文字体：%s" % cand)

    left = Image.open(os.path.join(PROJECT, CMP_SOURCE[0])).convert("RGB")
    right = Image.open(os.path.join(PROJECT, CMP_SOURCE[1])).convert("RGB")
    w, h = int(left.width * CMP_SCALE), int(left.height * CMP_SCALE)
    left = left.resize((w, h), Image.LANCZOS)
    right = right.resize((w, h), Image.LANCZOS)

    pad, gap, title_h, cap_h, border = 26, 22, 48, 42, 3
    cw = pad * 2 + w * 2 + gap
    ch = pad + title_h + 14 + h + cap_h + pad
    canvas = Image.new("RGB", (cw, ch), (246, 247, 249))
    draw = ImageDraw.Draw(canvas)

    f_title = ImageFont.truetype(FONT_BOLD, 30)
    f_cap = ImageFont.truetype(FONT, 22)
    f_tag = ImageFont.truetype(FONT_BOLD, 20)

    draw.text(((cw - draw.textlength(CMP_TITLE, font=f_title)) / 2, pad),
              CMP_TITLE, font=f_title, fill=(28, 30, 34))

    top = pad + title_h + 14
    bad, good = (208, 66, 66), (28, 132, 71)
    panels = ((left, CMP_LEFT, bad), (right, CMP_RIGHT, good))
    for idx, (img, (caption, tag), color) in enumerate(panels):
        x = pad + idx * (w + gap)
        draw.rectangle([x - border, top - border,
                        x + w + border - 1, top + h + border - 1], fill=color)
        canvas.paste(img, (x, top))
        draw.rectangle([x + CMP_MARK[0] * CMP_SCALE, top + CMP_MARK[1] * CMP_SCALE,
                        x + CMP_MARK[2] * CMP_SCALE, top + CMP_MARK[3] * CMP_SCALE],
                       outline=(255, 214, 0), width=3)
        bbox = draw.textbbox((0, 0), tag, font=f_tag)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rectangle([x + 12, top + 12, x + 12 + bw + 24, top + 12 + bh + 24], fill=color)
        draw.text((x + 24 - bbox[0], top + 24 - bbox[1]), tag,
                  font=f_tag, fill=(255, 255, 255))
        tw = draw.textlength(caption, font=f_cap)
        draw.text((x + (w - tw) / 2, top + h + 10), caption, font=f_cap, fill=color)

    out = os.path.join(DOCS, CMP_OUT)
    canvas.save(out, optimize=True)
    print("  已存 %s（%dx%d，%d 字节）"
          % (os.path.basename(out), cw, ch, os.path.getsize(out)))


def main() -> int:
    ap = argparse.ArgumentParser(description="重生成 README 图片素材")
    ap.add_argument("--with-shots", action="store_true",
                    help="连界面截图一起重拍（会临时拉起本机服务）")
    args = ap.parse_args()

    os.makedirs(DOCS, exist_ok=True)

    if args.with_shots:
        print("--- 界面截图 ---")
        shoot()
    else:
        print("--- 跳过界面截图（要重拍请加 --with-shots）---")

    if os.path.isfile(os.path.join(PROJECT, CMP_SOURCE[0])):
        print("--- 对比图 ---")
        make_compare()
    else:
        print("--- 跳过对比图（素材不存在：%s）---" % CMP_SOURCE[0])

    print()
    print("完成。记得重跑：")
    print("  python .tools/sync_staging.py     # 把 docs/ 同步进 staging")
    print("  python 仓库单测.py                 # 校验 README 引用的图都在")
    return 0


if __name__ == "__main__":
    sys.exit(main())
