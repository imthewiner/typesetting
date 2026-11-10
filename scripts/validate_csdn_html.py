#!/usr/bin/env python3
"""CSDN 富文本 HTML 合规校验器。

检查翻译产物是否符合 CSDN 富文本粘贴的清洗容忍度：
  - 禁止 <style>/<script>/<link>/<section>/class/id / display:flex|grid / gap /
    position absol-fixed / float / @media / @keyframes / @import / var(--x)
    / 外部字体 / <svg>（SVG 在 CSDN 不可靠）
  - 建议：只保留语义标签 <p>/<h1-h6>/<strong>/<span>/<ul>/<ol>/<li>/
    <blockquote>/<pre>/<code>/<table>/<img>/<hr>/<a>；样式全部内联
  - 校验半角标点（中文后接半角逗号/分号/叹号/问号）

用法:
    validate_csdn_html.py <file.html>
    validate_csdn_html.py --stdin < file.html

退出码: 1 = 有 ERROR；0 = 通过
"""

import argparse
import re
import sys
from html.parser import HTMLParser

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

FORBIDDEN = [
    (re.compile(r"<style[\s>]", re.I), "ERROR", "<style> 会被 CSDN 过滤，样式必须内联"),
    (re.compile(r"<script[\s>]", re.I), "ERROR", "<script> 会被过滤"),
    (re.compile(r"<link[\s>]", re.I), "ERROR", "外部 <link>（CSS/字体）会被过滤"),
    (re.compile(r"<section[\s>]", re.I), "ERROR", "<section> 在 CSDN 不可靠，会折叠，应使用语义标签"),
    (re.compile(r"\sclass\s*=", re.I), "ERROR", "class 属性会被剥离"),
    (re.compile(r"\sid\s*=", re.I), "ERROR", "id 属性会被剥离"),
    (re.compile(r"display\s*:\s*(flex|grid|inline-flex)", re.I), "ERROR",
     "display:flex/grid 不被 CSDN 支持，会打平"),
    (re.compile(r"(?:^|;)\s*gap:", re.I), "ERROR", "gap 不被支持，应改 margin"),
    (re.compile(r"(?:^|;)\s*justify-content:", re.I), "ERROR",
     "justify-content 不被支持"),
    (re.compile(r"(?:^|;)\s*align-(items|self|content):", re.I), "ERROR",
     "flex 对齐属性不被支持"),
    (re.compile(r"\sfloat\s*:", re.I), "ERROR", "float 不被支持"),
    (re.compile(r"position\s*:\s*(absolute|fixed|sticky)", re.I), "ERROR",
     "position:absolute/fixed/sticky 不被支持"),
    (re.compile(r"@media", re.I), "WARNING", "@media 媒体查询不被支持"),
    (re.compile(r"@keyframes", re.I), "ERROR", "@keyframes 动画不被支持"),
    (re.compile(r"@import", re.I), "ERROR", "@import 不被支持"),
    (re.compile(r"var\s*\(\s*--", re.I), "ERROR", "CSS 变量 var(--x) 不被支持"),
    (re.compile(r"<svg[\s>]", re.I), "ERROR", "SVG 在 CSDN 富文本不可靠，应替换为文本/emoji"),
    (re.compile(r"url\s*\(\s*['\"]?https?://[^)]*\.(woff2?|ttf|otf|eot)", re.I),
     "ERROR", "外部字体不被支持"),
    (re.compile(r"position\s*:\s*fixed", re.I), "ERROR", "fixed 定位不被支持"),
    # 颜色安全：rgba()/rgb() 与白字配彩底在跨平台粘贴时不兼容（背景剥离后白字白底不可见）
    (re.compile(r"rgba?\(", re.I), "ERROR",
     "rgba()/rgb() 颜色值跨平台不稳定，必须转纯色 hex（translate 已自动处理，若出现说明源 gzh 有遗漏）"),
    (re.compile(r"color\s*:\s*(#fff|#ffffff|white)\b", re.I), "ERROR",
     "白色文字在背景被剥离的平台上不可见，必须反转为深色文字（translate 已自动反色）"),
    (re.compile(r"<font[^>]*\bcolor\s*=\s*[\"']?(#fff|#ffffff|white)\b", re.I), "ERROR",
     "白色 <font color> 在背景被剥离的平台上不可见，必须反转为深色文字"),
    (re.compile(r"background\s*:\s*#0{2,6}\b|background\s*:\s*black\b", re.I), "ERROR",
     "纯黑背景+浅字在部分平台只盖住半个字高，必须改为浅底深字"),
]

CJK = re.compile(r"[一-鿿㐀-䶿]")
HALF_PUNCT = re.compile(r"[一-鿿㐀-䶿][,?;!]")
ASCII_QUOTE = re.compile(r"[\"']")
CODE_STYLE = re.compile(r"monospace|white-space\s*:\s*pre|courier|consolas|sf mono", re.I)


def _csdn_hex_to_rgb(h: str):
    """#rgb / #rrggbb → (r,g,b)；非法返回 None。"""
    h = (h or "").strip().lstrip("#")
    if len(h) == 3:
        return tuple(int(c * 2, 16) for c in h)
    if len(h) == 6:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return None


def _csdn_lum(rgb) -> float:
    """简单灰度亮度，用于判断文字是否过浅（白底上 luminance>=200 近似不可见）。"""
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def validate(html: str, name: str = "<input>"):
    errors, warnings = [], []

    for rx, level, msg in FORBIDDEN:
        n = len(rx.findall(html))
        if n:
            target = errors if level == "ERROR" else warnings
            target.append(f"{msg}（命中 {n} 处）")

    # 低对比度文字回归检查：CSDN 富文本默认白底，文字灰度 luminance>=200 时
    # 与白底对比度极低（≈1.5:1），肉眼几乎不可见。translate 已自动加深此类文字，
    # 若仍命中说明脚本有遗漏，必须修复。仅检查 color: / <font color> 文字色，不检查背景。
    light_text = set()
    for m in re.finditer(
            r"(?:color\s*:\s*#([0-9a-fA-F]{3,8})|"
            r"<font[^>]*\bcolor\s*=\s*[\"']?#([0-9a-fA-F]{3,8}))", html):
        hexv = m.group(1) or m.group(2)
        rgb = _csdn_hex_to_rgb(hexv)
        if rgb and _csdn_lum(rgb) >= 200:
            light_text.add("#" + hexv.lower())
    if light_text:
        errors.append(
            "检测到浅色文字（白底上对比度过低、近乎不可见，luminance>=200）: "
            + ", ".join(sorted(light_text))
            + "（translate 应已自动加深，若仍出现说明有遗漏，请修复 translate 脚本）")

    # 半角标点
    cjk = bool(CJK.search(html))
    if cjk:
        sample = []
        for m in HALF_PUNCT.finditer(html):
            snippet = html[max(0, m.start() - 10):m.end() + 5]
            sample.append(snippet.replace("\n", " "))
            if len(sample) >= 5:
                break
        if sample:
            warnings.append(
                f"{len(list(HALF_PUNCT.finditer(html)))} 处正文疑似半角标点，应改全角"
                f"（例: {'；'.join(sample)}）")

    # 标签白名单检查（div 在 CSDN 富文本中可接受，仅提示）
    parser = TagCounter()
    parser.feed(html)
    ok_tags = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "b",
               "em", "i", "span", "ul", "ol", "li", "blockquote", "pre",
               "code", "table", "thead", "tbody", "tr", "td", "th",
               "img", "hr", "a", "br", "div",
               "font", "del", "s", "ins", "u", "sup", "sub", "center"}
    unknown = sorted(t for t in parser.tag_counts if t not in ok_tags and t != "#text")
    if unknown:
        errors.append("出现了 CSDN 不推荐的标签: " + ", ".join(unknown))
    divs = parser.tag_counts.get("div", 0)
    if divs:
        warnings.append(f"包含 {divs} 个 <div> 标签"
                        f"（CSDN 可接受，但建议以 <p> 承载文本）")

    # HTML4 语义属性白名单（font color/size, bgcolor, align 等 CSDN 保留）
    attr_parser = AttrChecker()
    attr_parser.feed(html)
    if attr_parser.bad_attrs:
        errors.append("存在 CSDN 不保留的属性: "
                      + ", ".join(sorted(set(attr_parser.bad_attrs)))[:200])

    return errors, warnings


class TagCounter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tag_counts = {}

    def handle_starttag(self, tag, attrs):
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1


ALLOWED_ATTRS = {"style", "href", "src", "alt", "title", "target",
                 "colspan", "rowspan", "width", "height", "align", "valign",
                 "bgcolor", "color", "size", "face", "cellpadding",
                 "cellspacing", "border", "start", "type", "name"}


class AttrChecker(HTMLParser):
    """收集出现的不在白名单里的属性名。class/id 由 FORBIDDEN 另行拦截。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bad_attrs = []

    def handle_starttag(self, tag, attrs):
        for k, _ in attrs:
            if k.lower() not in ALLOWED_ATTRS and k.lower() not in ("class", "id"):
                self.bad_attrs.append(k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="HTML 文件路径")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读取")
    args = ap.parse_args()

    if args.stdin or not args.file:
        html = sys.stdin.read()
        name = "<stdin>"
    else:
        with open(args.file, encoding="utf-8", errors="replace") as f:
            html = f.read()
        name = args.file

    errors, warnings = validate(html, name)
    print(f"📋 CSDN 富文本 HTML 合规校验: {name}")
    if errors:
        print(f"\n❌ ERROR ×{len(errors)}（必须修复）:")
        for e in errors:
            print(f"   • {e}")
    if warnings:
        print(f"\n⚠️  WARNING ×{len(warnings)}（建议处理）:")
        for w in warnings:
            print(f"   • {w}")
    if not errors and not warnings:
        print("\n✅ 完全合规，可直接粘贴到 CSDN 富文本编辑器")
    elif not errors:
        print("\n✅ 无致命问题，可粘贴（warning 请人工确认）")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()