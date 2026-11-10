#!/usr/bin/env python3
"""把已校验的 CSDN 正文片段（纯 <div> 内容）包成带「复制」按钮的浏览器预览页。

用户打开预览页 → 点右上角「复制到 CSDN」→ 复制的是一段 HTML（等价手动
Ctrl+A/Ctrl+C 的富文本，样式全保留）→ 到 CSDN 富文本编辑器 Ctrl+V 粘贴即可。

按钮和 JS 只存在于预览外壳里，**不在被复制的内容内**，所以粘进 CSDN 的
仍是干净合规的正文，不含 <script>/<button>。校验请对原始 HTML 文件跑
validate_csdn_html.py（本预览页含 script/style，不参与校验）。

用法:
    wrap_csdn_preview.py <csdn.html> [output.html]
    默认输出 <csdn去扩展名>_预览.html
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    if len(sys.argv) < 2:
        print("用法: wrap_csdn_preview.py <csdn.html> [output.html]")
        sys.exit(1)
    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"✗ 找不到文件: {src}")
        sys.exit(1)

    content = open(src, encoding="utf-8").read().strip()
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "assets", "preview-template-csdn.html")
    tpl = open(tpl_path, encoding="utf-8").read()

    title = os.path.splitext(os.path.basename(src))[0]
    out_html = (tpl.replace("{{TITLE}}", title)
                   .replace("<!--CSDN_CONTENT-->", content))

    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + "_预览.html"
    open(out, "w", encoding="utf-8").write(out_html)
    print(f"✓ 已生成带「复制」按钮的 CSDN 预览页: {out}")
    print("  用浏览器打开它，点右上角「复制到 CSDN」，再去 CSDN 富文本编辑器 Ctrl/⌘+V 粘贴。")


if __name__ == "__main__":
    main()