#!/usr/bin/env python3
"""一条命令跑完公众号 + CSDN 的机械步骤。

前置：公众号母版 HTML 已由 Agent 按 references/theme-moyu-green.md 装配好。
本脚本不生成内容，只负责：校验 → 本地图内嵌 → 公众号预览 → CSDN 翻译 → 校验 → CSDN 预览。

用法:
    build_both.py <公众号母版.html> [--no-preview] [--host catbox|telegraph]

    --no-preview      只出正文文件，不生成两个预览页
    --host catbox     本地图走图床直链（默认 base64 内嵌；图床失败自动降级）

退出码:
    0 = 全部通过（允许 CSDN 侧仍有非阻塞 WARNING）
    1 = 公众号校验或 CSDN 校验出现 ERROR，已停止
    2 = 输入/环境异常
"""

import argparse
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_SRC = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1", re.I | re.S)


def run(script, args, label):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, script)] + args
    print(f"\n▶ {label}")
    print("  " + " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    out = (proc.stdout or "").rstrip()
    err = (proc.stderr or "").rstrip()
    if out:
        print(out)
    if err:
        print(err)
    return proc.returncode


def has_local_images(path):
    text = open(path, encoding="utf-8").read()
    for _, src in IMG_SRC.findall(text):
        s = src.strip()
        if s.lower().startswith(("http://", "https://", "data:", "//")):
            continue
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="公众号 + CSDN 双平台机械步骤一键跑")
    ap.add_argument("src", help="公众号母版 HTML（纯 <section> 正文片段）")
    ap.add_argument("--no-preview", action="store_true", help="不生成预览页")
    ap.add_argument("--host", choices=["catbox", "telegraph"],
                    help="本地图走图床直链；不填则 base64 内嵌")
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    if not os.path.isfile(src):
        print(f"✗ 找不到文件: {src}")
        return 2

    # 1) 公众号校验
    if run("validate_gzh_html.py", [src], "校验公众号 HTML") != 0:
        print("\n✗ 公众号校验有 ERROR，先按 SKILL.md 阶段 1 修组件，再重跑本脚本。")
        return 1

    # 2) 本地图内嵌
    paste = src
    if has_local_images(src):
        mode = ["--mode", "host", "--host", args.host] if args.host else ["--mode", "base64"]
        if run("upload_images.py", [src] + mode, "本地图片转可粘贴形态") != 0:
            print("\n✗ 图片处理失败，检查图片路径是否存在。")
            return 1
        paste = os.path.splitext(src)[0] + "_online" + os.path.splitext(src)[1]
        if not os.path.isfile(paste):
            print(f"✗ 预期产物不存在: {paste}")
            return 1
    else:
        print("\n· 未发现本地图片，直接用干净正文。")

    # 3) 公众号预览
    if not args.no_preview:
        if run("wrap_preview.py", [paste], "生成公众号预览页") != 0:
            return 1

    # 4) CSDN 翻译（含图必须用在线版）
    if run("translate_gzh_to_csdn.py", [paste], "翻译为 CSDN 兼容 HTML") != 0:
        return 1
    csdn = os.path.splitext(paste)[0] + "_CSDN.html"
    if not os.path.isfile(csdn):
        print(f"✗ 预期产物不存在: {csdn}")
        return 1

    # 5) CSDN 校验
    if run("validate_csdn_html.py", [csdn], "校验 CSDN HTML") != 0:
        print("\n✗ CSDN 校验有 ERROR：先修 translate_gzh_to_csdn.py 或母版，别手改产物绕过。")
        return 1

    # 6) CSDN 预览
    if not args.no_preview:
        if run("wrap_csdn_preview.py", [csdn], "生成 CSDN 预览页") != 0:
            return 1

    print("\n✓ 全流程通过，产物：")
    print(f"  公众号正文 : {paste}")
    if not args.no_preview:
        print(f"  公众号预览 : {os.path.splitext(paste)[0] + '_预览.html'}")
    print(f"  CSDN 正文  : {csdn}")
    if not args.no_preview:
        print(f"  CSDN 预览  : {os.path.splitext(csdn)[0] + '_预览.html'}")
    print("\n下一步：打开预览页点「复制」，分别粘到公众号 / CSDN 编辑器；")
    print("CSDN 版再按 references/csdn-manual-fixes.md 过一遍九项手改。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
