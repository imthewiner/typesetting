#!/usr/bin/env python3
"""把公众号文章（HTML / Markdown）里的本地图片一键转成「可粘贴」形式：

方案 A（默认, 零配置必成功）— base64 内嵌
    将本地图片转成 data:image;base64,... 直接内嵌到 HTML/Markdown 里。
    预览页点「复制到公众号」→ 微信编辑器粘贴时会把图片自动转存到微信 CDN
    （mmbiz.qpic.cn），无需任何图床账号、任何网络假设。

方案 B（需网络可达的匿名图床）— 直链上传
    catbox.moe / Telegra.ph，脚本逐个上传本地图并把 src 换成在线直链 URL。
    单图上传失败会自动降级为 base64 内嵌（不中断、不丢图）。

设计要点:
- 只处理本地相对/绝对路径；http(s):、data:、// 开头的在线地址一律跳过(幂等)。
- 相对路径以 目标文件所在目录 为基准解析。
- 不覆盖原文件，默认输出为 `<原文件名>_线上.<ext>`。
- Windows 控制台强制 UTF-8；图片扩展名自动映射 MIME 类型。

用法:
    upload_images.py <article.html|article.md> [--mode base64|host --host catbox|telegraph]
                         [--out out.html] [--sleep 0.5]

依赖: 仅标准库（base64/base64、os、re、sys、urllib），无需 pip 安装。
"""

import argparse
import base64
import mimetypes
import os
import re
import sys
import time
import urllib.request
import urllib.parse

# Windows 控制台默认 GBK，强制 UTF-8 输出避免 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

MIME_EXT = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".bmp": "image/bmp", ".ico": "image/x-icon", ".avif": "image/avif",
}


def to_base64(path: str) -> str:
    """读入图片并返回 data: URI。"""
    ext = os.path.splitext(path)[1].lower()
    mime = MIME_EXT.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _post_multipart(url: str, fields: dict, timeout: int = 60) -> str:
    """极简 multipart/form-data 上传，仅标准库。fields: {name: ('filename', bytes)}."""
    boundary = "----gzhupload" + hex(id(url))[2:]
    body = bytearray()
    for name, (filename, data_bytes) in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: application/octet-stream\r\n\r\n"
        body += data_bytes
        body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace").strip()


def _catbox(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    resp = _post_multipart("https://catbox.moe/user/api.php", {
        "reqtype": (None, "fileupload"),
        "fileToUpload": (os.path.basename(path), raw),
    })
    if not resp.startswith("http"):
        raise RuntimeError(f"catbox 返回异常: {resp[:120]!r}")
    return resp


def _telegraph(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    resp = _post_multipart("https://telegra.ph/upload", {
        "file": (os.path.basename(path), raw),
    })
    # Telegra.ph 返回 JSON: [{"src": "/file/xxx.jpg", ...}]
    import json
    data = json.loads(resp) if resp.startswith("[") else resp
    if isinstance(data, list) and data and "src" in data[0]:
        return "https://telegra.ph" + data[0]["src"]
    raise RuntimeError(f"telegra.ph 返回异常: {resp[:120]!r}")


HOSTS = {"catbox": _catbox, "telegraph": _telegraph}


def is_online(src: str) -> bool:
    s = src.strip().lower()
    return s.startswith(("http://", "https://", "data:", "//"))


def resolve_abs(src: str, base_dir: str) -> str:
    if not src:
        return None
    cand = src.split("?", 1)[0].split("#", 1)[0]
    p = cand if os.path.isabs(cand) else os.path.join(base_dir, cand)
    return p if os.path.isfile(p) else None


def convert_path(abs_path: str, mode: str, host: str) -> str:
    """把本地图片转成 data URI（base64 模式）或图床直链（直传模式）。
    直传失败时自动降级 base64，保证不丢图。"""
    if mode == "base64" or mode == "inline":
        return to_base64(abs_path)
    try:
        url = HOSTS[host](abs_path)
        print(f"    ↑ {os.path.basename(abs_path)}  →  {url}")
        return url
    except Exception as e:
        print(f"    ⚠ {os.path.basename(abs_path)} 图床失败({e})，降级 base64")
        return to_base64(abs_path)


def handle_html(text: str, base_dir: str, mode: str, host: str, sleep: float) -> str:
    html_img = re.compile(r"<img[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1", re.I | re.S)

    def _r(m):
        src = m.group(2).strip()
        if is_online(src):
            return m.group(0)
        abs_p = resolve_abs(src, base_dir)
        if not abs_p:
            print(f"  ⚠ 未找到本地文件，跳过: {src}")
            return m.group(0)
        new_src = convert_path(abs_p, mode, host)
        time.sleep(sleep)
        # m.start/end(2) 是全文绝对位置，须转成 group(0) 内的相对偏移
        s0 = m.start(0)
        i = m.start(2) - s0
        j = m.end(2) - s0
        return m.group(0)[:i] + new_src + m.group(0)[j:]

    return html_img.sub(_r, text)


def handle_markdown(text: str, base_dir: str, mode: str, host: str, sleep: float) -> str:
    md_img = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")

    def repl(m):
        alt, src = m.group(1), m.group(2).strip()
        if is_online(src):
            return m.group(0)
        abs_p = resolve_abs(src, base_dir)
        if not abs_p:
            print(f"  ⚠ 未找到本地文件，跳过: {src}")
            return m.group(0)
        new_src = convert_path(abs_p, mode, host)
        time.sleep(sleep)
        return f"![{alt}]({new_src})"

    return md_img.sub(repl, text)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="HTML 或 Markdown 文件")
    ap.add_argument("--mode", default="base64", choices=["base64", "inline", "host"],
                    help="base64(默认,内嵌)/inline(同 base64)/host(直传图床)")
    ap.add_argument("--host", default="catbox", choices=HOSTS.keys(),
                    help="直传模式用哪个图床（默认 catbox）")
    ap.add_argument("--out", help="输出文件（默认 <原文件名>_online.<ext>）")
    ap.add_argument("--sleep", type=float, default=0.3,
                    help="每张间隔秒数防限流（默认 0.3）")
    args = ap.parse_args()

    src_path = args.file
    if not os.path.isfile(src_path):
        sys.exit(f"找不到文件: {src_path}")

    base_dir = os.path.dirname(os.path.abspath(src_path))
    ext = os.path.splitext(src_path)[1].lower()
    out = args.out or os.path.splitext(src_path)[0] + "_online" + ext

    with open(src_path, encoding="utf-8") as f:
        text = f.read()

    mode = "base64" if args.mode == "inline" else args.mode
    desc = "base64 内嵌" if mode == "base64" else f"图床直传({args.host})"
    print(f"📤 图片处理: {os.path.basename(src_path)}  方式={desc}")

    if ext in (".html", ".htm"):
        text = handle_html(text, base_dir, mode, args.host, args.sleep)
        # HTML 里可能混 markdown 语法，兜底再跑一遍（幂等）
        text = handle_markdown(text, base_dir, mode, args.host, args.sleep)
    else:
        text = handle_markdown(text, base_dir, mode, args.host, args.sleep)

    with open(out, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n✅ 已生成: {out}")
    if mode == "base64":
        print("   图片已 base64 内嵌。写公众号时把此文件复制粘贴即可，微信会自动转存图片。")
    else:
        print("   图片已转为图床直链。若还有残留本地图，说明对应图床不可达（已自动降级 base64）。")


if __name__ == "__main__":
    main()