#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_images.py — 从 CSDN HTML 中抽出 base64 内嵌图片为独立文件。

CSDN 富文本粘贴针对 data: URI 会提示「非正常图片地址，图片转存失败」，
因此交付时必须：
  1) 把 base64 图片解码为独立 png（放 <输出目录>/images/）供用户在
     CSDN 编辑器手动「插入图片 / 拖拽上传」；
  2) HTML 里仍保留 base64（本地预览页可正常显示）。

用法:
  python extract_images.py <input.html> [--out-dir <目录>]
说明:
  - 默认输出目录 = 输入文件同目录下的 `images/<输入基名>/`
  - 在 HTML 中把 <img src="data:..."> 的 src 加后缀注释属性不改变文件本身，
    保持 HTML 原样（提示由 wrap 预览页与交付说明负责）。
"""
import argparse
import base64
import os
import re
import sys

IMGRE = re.compile(r'<img\b[^>]*?src="data:image/(?P<fmt>[^;]+);base64,(?P<data>[^"]+)"', re.I)


def extract(html_path, out_dir=None):
    if not os.path.isfile(html_path):
        print(f"❌ 未找到输入文件: {html_path}")
        return 1

    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    dirn, base = os.path.split(html_path)
    stem = os.path.splitext(base)[0]
    if out_dir is None:
        out_dir = os.path.join(dirn, "images", stem)
    os.makedirs(out_dir, exist_ok=True)

    matches = list(IMGRE.finditer(html))
    if not matches:
        print(f"ℹ️  未在 {base} 中发现 base64 内联图片。")
        return 0

    saved = []
    for idx, m in enumerate(matches, 1):
        fmt = m.group("fmt").lower()
        if fmt not in ("png", "jpeg", "jpg", "gif", "webp"):
            fmt = "png"  # 兜底
        elif fmt == "jpeg":
            fmt = "jpg"
        data_b64 = m.group("data")
        try:
            raw = base64.b64decode(data_b64)
        except Exception as e:
            print(f"⚠️  第 {idx} 张图片 base64 解码失败: {e}")
            continue
        fname = f"img-{idx:02d}.{fmt}"
        dst = os.path.join(out_dir, fname)
        with open(dst, "wb") as f:
            f.write(raw)
        saved.append((fname, len(raw)))
        print(f"  [OK] {fname}  ({len(raw)} bytes)")

    print(f"\n[OK] 共抽出 {len(saved)} 张图片 -> {out_dir}")
    print("CSDN 侧：请在公众号编辑器里用「插入图片/拖拽」上传以上文件，")
    print("        再把文章内的图片替换为 img-blog.csdnimg.cn 链接后再发布。")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="抽取 base64 内联图为独立文件")
    ap.add_argument("html_path", help="包含 base64 图片的 HTML 文件")
    ap.add_argument("-o", "--out-dir", default=None, help="图片输出目录（默认 同级/images/<基名>）")
    args = ap.parse_args()
    raise SystemExit(extract(args.html_path, args.out_dir))