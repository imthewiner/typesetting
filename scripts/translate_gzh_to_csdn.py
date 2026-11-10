#!/usr/bin/env python3
"""把 gzh-design 生成的公众号正文 HTML（纯 <section> 片段）翻译成 CSDN 富文本兼容 HTML。

设计依据：references/translate-rules.md 与 references/csdn-compat.md。
不做 <head>/<body> 外壳，保持正文片段，供 csdn-design 预览页嵌入。

用法:
    translate_gzh_to_csdn.py <gzh_body.html> [output.html]
    默认输出 <输入去扩展名>_CSDN.html

退出码: 0 = 成功；2 = 解析/处理异常
"""

import os
import re
import sys
from html.parser import HTMLParser

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

VOID_TAGS = {"br", "img", "hr", "meta", "link", "source", "input"}
SVG_TAGS = {"svg", "path", "circle", "rect", "polyline", "polygon", "line", "g",
            "text", "tspan", "defs", "use", "linearGradient", "radialGradient",
            "stop", "pattern", "mask"}

# 保留的常规 CSS 属性
KEEP_PROPS = {
    "color", "font-size", "font-weight", "font-style", "font-family",
    "text-align", "text-decoration", "line-height", "letter-spacing",
    "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
    "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
    "border", "border-bottom", "border-left", "border-top", "border-right",
    "border-radius", "vertical-align", "word-break", "text-justify",
    "max-width", "list-style", "list-style-type",
}

# 在 style 中一律剔除的属性（CSDN 不支持/不确定）
DROP_PROPS = {
    "display", "gap", "align-items", "align-self", "justify-content",
    "flex", "flex-grow", "flex-shrink", "flex-basis", "order",
    "position", "top", "bottom", "left", "right", "float",
    "z-index", "cursor", "pointer-events", "user-select",
    "opacity", "transform", "transition", "animation",
    "overflow", "overflow-x", "overflow-y", "text-overflow",
    "white-space", "-webkit-overflow-scrolling", "-webkit-tap-highlight-color",
    "box-shadow", "filter", "backdrop-filter",
}


# CSDN 富文本真实保留的是 HTML4 语义（<font>/<del>/<strong>/bgcolor 属性），
# 而不是 inline CSS。这里把关键表现提升为"语义双轨"：主通道是 HTML4 标签/属性，
# 残留的内联 CSS 仅作兜底（部分编辑器可能仍保留）。
FONT_SIZE_TO_HTML = [(32, 6), (22, 6), (19, 5), (16, 4), (14, 4), (12, 3),
                     (11, 2), (10, 2), (8, 1)]


def _css_color_v(style: str) -> str:
    """从 color: 提取文字颜色（不抓 background，那是块级背景）。"""
    m = re.search(r"(?:^|;)\s*color\s*:\s*"
                  r"(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|[a-zA-Z]+)", style)
    if m:
        v = m.group(1).strip()
        if v and v.lower() != "transparent":
            return v
    return ""


def _css_font_size(style: str) -> int:
    m = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", style)
    return int(float(m.group(1))) if m else 0


def _css_has(style: str, prop_substr: str) -> bool:
    return re.search(prop_substr, style, re.I) is not None


def _semanticize(inner: str, css: str) -> str:
    """把内联 CSS 的关键表现形式提升为 CSDN 保留的 HTML4 语义。

    - text-decoration:line-through → <del>
    - font-weight:700+ → <strong>
    - color → <font color>
    - font-size → <font size="1..7">
    返回包装后的 inner（若无可提取则原样返回）。
    """
    if not css or not inner:
        return inner
    # font/del/strong 是行内语义，包裹块级子元素（div/table/ul/h…）非法，
    # 若内部已有块级结构则只保留原样（内联 CSS 兜底即可）
    if re.search(r"<(div|table|tr|td|th|ul|ol|li|h[1-6]|p|section|blockquote|pre)\b",
                 inner, re.I):
        return inner
    out = inner
    if _css_has(css, r"text-decoration\s*:\s*[^;]*line-through"):
        out = f"<del>{out}</del>"
    if _css_has(css, r"font-weight\s*:\s*(700|800|900)|font-weight\s*:\s*bold"):
        out = f"<strong>{out}</strong>"
    color = _css_color_v(css)
    size = _css_font_size(css)
    font_parts = []
    if color and color.lower() != "transparent":
        font_parts.append(f'color="{color}"')
    if size:
        for threshold, html_size in FONT_SIZE_TO_HTML:
            if size >= threshold:
                font_parts.append(f'size="{html_size}"')
                break
        else:
            font_parts.append('size="1"')
    if font_parts:
        out = f"<font {' '.join(font_parts)}>{out}</font>"
    return out


def _css_bgcolor(style: str) -> str:
    """提取 background 纯色（用于 <td bgcolor> 等属性）。"""
    for m in re.finditer(r"background(?:\s*\:\s*)(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))",
                         style):
        v = m.group(1)
        if v.lower() == "transparent":
            continue
        return v
    return ""


def _pick_color(style_value: str) -> str:
    """从一个 background(-image) 值里取第一个颜色 token。支持 rgba()/括号内逗号。"""
    v = style_value.strip()
    tokens = re.findall(
        r"(rgba?\([^)]*\)|hsla?\([^)]*\)|#[0-9a-fA-F]{3,8}|[a-zA-Z][a-zA-Z0-9-]*)",
        v)
    for tok in tokens:
        if tok.startswith(("rgba", "rgb", "hsl", "#")) or tok.lower() in (
                "transparent", "white", "black", "red", "green", "blue",
                "yellow", "gray", "grey", "currentcolor"):
            return tok
    return ""


# ---------- 颜色安全降级（跨平台不兼容色系处理） ----------
# 实测教训：CSDN/博客园/掘金等平台粘贴时——
#   · rgba(255,255,255,0.9) 这类半透明白文字，背景被剥离后 = 白底白字，不可见
#   · background:rgba(255,255,255,0.2) + color:#fff 的小标签，两种平台都变白 = 不可见
#   · background:#111827 + color:#fff 的 STEP 胶囊，黑底只盖住半个字高 = 半个字可见
#   · 公众号浅灰字（#D1D5DB / #9CA3AF 等）压在彩色卡片底时尚可，翻译后卡片变浅底，
#     浅灰字落在近似白底上 → 对比度过低（≈1.5:1），几乎看不见
# 因此翻译器统一：① 把「深底白字」反转为「浅底深字」；② 任何 rgba() 转纯色 hex；
# ③ 浅底上的浅色字自动加深到 WCAG 对比度 ≥3.0，确保白底清晰可读。

def _hex_to_rgb(h: str):
    """#rgb / #rrggbb → (r,g,b)；非法返回 None。"""
    h = (h or "").strip().lstrip("#")
    if len(h) == 3:
        return tuple(int(c * 2, 16) for c in h)
    if len(h) == 6:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return None


def _rgb_to_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        *(max(0, min(255, round(c))) for c in rgb))


def _luminance(rgb) -> float:
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _rel_lum(rgb):
    """WCAG 相对亮度（用于真实对比度计算）。"""
    def _f(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * _f(r) + 0.7152 * _f(g) + 0.0722 * _f(b)


def _contrast_ratio(c1, c2) -> float:
    """WCAG 对比度（输入 rgb 元组）。"""
    l1, l2 = _rel_lum(c1), _rel_lum(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _darken_to_contrast(color: str, bg: str, target: float = 3.0) -> str:
    """把文字色逐步加深，直到与背景对比度达到 target（浅底上的浅灰字保底）。

    迭代乘以 0.82，直到对比度达标或逼近黑色；保证 CSDN 白底上文字清晰可读。
    """
    text_rgb = _hex_to_rgb(color)
    bg_rgb = _hex_to_rgb(bg)
    if not text_rgb or not bg_rgb:
        return color
    cur = list(text_rgb)
    for _ in range(48):
        if _contrast_ratio(cur, bg_rgb) >= target:
            break
        cur = [c * 0.82 for c in cur]
    return _rgb_to_hex(tuple(int(max(0, min(255, c))) for c in cur))


def _parse_rgba(v: str):
    """解析 rgb()/rgba() → (r,g,b,a)；非法返回 None。"""
    m = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)"
                 r"(?:\s*,\s*([\d.]+))?\s*\)", v.strip(), re.I)
    if not m:
        return None
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)),
            float(m.group(4)) if m.group(4) else 1.0)


def _solidify_color(value: str, base: str = "#ffffff") -> str:
    """把 rgba()/rgb()/hex 合成到 base 背景上得到纯色 hex；无法识别原样返回。"""
    v = value.strip()
    m = _parse_rgba(v)
    if m:
        r, g, b, a = m
        br, bg, bb = _hex_to_rgb(base) or (255, 255, 255)
        return _rgb_to_hex((r * a + br * (1 - a),
                            g * a + bg * (1 - a),
                            b * a + bb * (1 - a)))
    if v.lower() in ("transparent", "none"):
        return base
    return v


def _solidify_bg(bg_raw: str, parent_bg=None):
    """把 background 值解析成纯色 hex（渐变取首色、rgba 合成到父背景）。
    透明/无法识别返回 None（表示无背景）。"""
    v = (bg_raw or "").strip()
    if not v or v.lower() in ("transparent", "none"):
        return None
    if "gradient" in v.lower():
        c = _pick_color(v)
        if not c or c.lower() in ("transparent", "none"):
            return None
        v = c
    if _parse_rgba(v):
        return _solidify_color(v, parent_bg or "#ffffff")
    if v.lower().startswith("#"):
        return v
    return None


def _is_whiteish(value: str) -> bool:
    """判断是否为白/近白文字色（rgba 白或 #fff/#ffffff）。"""
    v = (value or "").strip().lower()
    if v in ("#fff", "#ffffff", "white"):
        return True
    m = _parse_rgba(value)
    if m:
        r, g, b, a = m
        return r >= 248 and g >= 248 and b >= 248 and a >= 0.5
    rgb = _hex_to_rgb(value)
    return bool(rgb) and all(c >= 248 for c in rgb)


def _is_colorful(color) -> bool:
    """背景是否属于「需要反转」的深色/彩色（亮度 < 190）。"""
    rgb = _hex_to_rgb(color) if color and color.startswith("#") else None
    return bool(rgb) and _luminance(rgb) < 190


def _lighten(color: str, t: float = 0.88) -> str:
    rgb = _hex_to_rgb(color)
    if not rgb:
        return color
    return _rgb_to_hex(tuple(c + (255 - c) * t for c in rgb))


def _darken(color: str, t: float = 0.75) -> str:
    rgb = _hex_to_rgb(color)
    if not rgb:
        return color
    return _rgb_to_hex(tuple(c * t for c in rgb))


def _parse_style(style: str) -> dict:
    d = {}
    for decl in (style or "").split(";"):
        if ":" in decl:
            p, _, v = decl.partition(":")
            d[p.strip().lower()] = v.strip()
    return d


def _build_style(d: dict) -> str:
    return ";".join(f"{k}:{v}" for k, v in d.items())


def _fix_color_safety(node, parent_bg=None, prefer_dark=None):
    """把「深底白字」反转为「浅底深字」，并把 rgba() 全部转纯色。

    - 自身 background 为深色/彩色 → 底色变浅（lighten），子树白字继承深色文字色
    - 白/近白文字（含 rgba 白）→ 换成深色文字（优先用祖先的深底色）
    - 所有 color/background 的 rgba() 合成到有效背景上变成 hex
    递归自上而下，把浅底与深文字色沿子树传递。
    """
    if node.tag == "#text":
        return
    style = _parse_style(node.attrs.get("style", ""))
    bg_raw = (style.get("background") or style.get("background-color") or "").strip()
    own_bg = _solidify_bg(bg_raw, parent_bg) if bg_raw else None
    eff_bg = own_bg or parent_bg
    color = (style.get("color") or "").strip()

    # rgba() 文字色 → 合成到有效背景成纯色
    if color and _parse_rgba(color):
        color = _solidify_color(color, eff_bg or "#ffffff")
        style["color"] = color

    child_bg = eff_bg
    dark = prefer_dark
    if own_bg:
        if _is_colorful(own_bg):
            light = _lighten(own_bg)
            style["background"] = light
            dark = _darken(own_bg)
            child_bg = light
        else:
            # 非彩色底（含半透明白 pill 等）→ 把 rgba 合成成纯色，文字已转深色
            style["background"] = own_bg
            child_bg = own_bg

    if color:
        if _is_whiteish(color):
            if dark:
                style["color"] = dark
            elif eff_bg and _is_colorful(eff_bg):
                style["color"] = _darken(eff_bg)
            else:
                # 白字但无深底可依托 → 兜底转深灰，保证可读
                style["color"] = "#111827"

    # 低对比度文字保底：浅底（白/浅色）上的浅灰/浅色字，在 CSDN 白底上会看不见。
    # 公众号设计里这些浅灰字常压在彩色卡片底上（尚可），但翻译后卡片变浅底，
    # 浅灰字直接落在白底附近 → 对比度过低。这里统一加深到可读对比度（≥3.0）。
    # 注意：祖先链无任何背景时 eff_bg 为 None，但 CSDN 默认白底，按白底处理。
    color_now = (style.get("color") or "").strip()
    if color_now:
        bg_for_check = eff_bg or "#ffffff"
        bg_rgb = _hex_to_rgb(bg_for_check)
        if bg_rgb and _luminance(bg_rgb) > 180:  # 浅底
            text_rgb = _hex_to_rgb(color_now)
            if text_rgb and _contrast_ratio(text_rgb, bg_rgb) < 3.0:
                style["color"] = _darken_to_contrast(color_now, bg_for_check, 3.0)

    node.attrs["style"] = _build_style(style)
    for c in node.children:
        if c.tag != "#text":
            _fix_color_safety(c, child_bg, dark)


def sanitize_style(style: str, is_code: bool = False, keep_layout: bool = False) -> str:
    """按 CSDN 白名单过滤 style，返回保留的属性串。

    keep_layout=True 时保留 width/height（用于图片）；代码块则剥离 background。
    """
    if not style:
        return ""
    kept = []
    seen = set()
    for decl in style.split(";"):
        decl = decl.strip()
        if not decl or ":" not in decl:
            continue
        prop, _, value = decl.partition(":")
        prop = prop.strip().lower()
        value = value.strip()
        if not prop or not value or prop in seen:
            continue
        seen.add(prop)

        if prop in DROP_PROPS:
            continue
        if prop in ("width", "height"):
            if keep_layout and re.fullmatch(r"\d+(\.\d+)?(px|%)?", value):
                kept.append(f"{prop}:{value}")
            continue
        if prop in ("background", "background-color", "background-image"):
            if is_code:
                continue
            if prop == "background-image":
                val = _pick_color(value)
                if val:
                    kept.append(f"background:{val}")
            elif prop == "background":
                val = _pick_color(value) if "gradient" in value else value
                if val:
                    kept.append(f"background:{val}")
            else:
                if value:
                    kept.append(f"background:{value}")
            continue
        if prop in KEEP_PROPS:
            # 双保险：任何 rgba() 一律合成到白色上转纯色（CSDN 等平台对 rgba 不稳）
            if "rgba(" in value or "rgb(" in value:
                if prop == "color":
                    value = _solidify_color(value, "#ffffff")
                elif prop.startswith("border") and "rgba(" in value:
                    # border: 1px solid rgba(...) → 换纯色（只换颜色 token，保留宽度/样式）
                    def _rep(m):
                        return _solidify_color(m.group(0), "#ffffff")
                    value = re.sub(r"rgba?\([^)]*\)", _rep, value)
            kept.append(f"{prop}:{value}")
    return ";".join(kept)


# ---------------- 简单 DOM 树 ----------------
class Node:
    """极简 DOM。tag='#text' 时 text 存文本；否则 children 存子节点。"""

    def __init__(self, tag="root", attrs=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.text = ""
        self.children = []
        self.parent = None

    def append(self, child):
        child.parent = self
        self.children.append(child)


def html_to_dom(html: str) -> Node:
    root = Node("root")
    stack = [root]
    buf = []

    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)

        def _flush(self):
            if buf:
                txt = "".join(buf)
                del buf[:]
                if txt.strip():
                    n = Node("#text")
                    n.text = txt
                    stack[-1].append(n)

        def handle_starttag(self, tag, attrs):
            self._flush()
            ad = {}
            for k, v in attrs:
                if v is not None:
                    ad[k.lower()] = v
            node = Node(tag.lower(), ad)
            stack[-1].append(node)
            if tag.lower() not in VOID_TAGS:
                stack.append(node)

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            if tag.lower() not in VOID_TAGS:
                self.handle_endtag(tag)

        def handle_endtag(self, tag):
            self._flush()
            tag = tag.lower()
            for i in range(len(stack) - 1, 0, -1):
                if stack[i].tag == tag:
                    del stack[i:]
                    break

        def handle_data(self, data):
            buf.append(data)

    P().feed(html)
    return root


# ---------------- 翻译与渲染 ----------------
def _has_flex(node: Node) -> bool:
    return "display" in node.attrs and "flex" in node.attrs.get("display", "")


def _has_scroll(node: Node) -> bool:
    style = node.attrs.get("style", "")
    return "scroll" in style or "nowrap" in style


def _text_content(node: Node) -> str:
    if node.tag == "#text":
        return node.text
    return "".join(_text_content(c) for c in node.children)


def _plain_text(node: Node) -> str:
    """去掉 SVG/装饰后的人类可读文本。"""
    if node.tag == "#text":
        return node.text
    if node.tag in SVG_TAGS:
        return ""
    return "".join(_plain_text(c) for c in node.children)


def _is_only_br(node: Node) -> bool:
    """节点内部仅剩装饰占位（空 span+br / br / 空白文本）。"""
    content = _plain_text(node).strip()
    if content:
        return False
    for c in node.children:
        if c.tag == "#text" and c.text.strip():
            return False
        if c.tag not in ("span", "br", "div", "section", "svg", "path", "i", "em"):
            return False
        if not _is_only_br(c):
            return False
    return True


def _find_child_by_text(node: Node, keyword: str) -> Node | None:
    """在直接子节点里找包含关键字的第一个。"""
    for c in node.children:
        if c.tag == "#text":
            continue
        if keyword in _plain_text(c):
            return c
        # 递归一层
        for cc in c.children:
            if cc.tag != "#text" and keyword in _plain_text(cc):
                return cc
    return None


def _is_chapter_header(node: Node) -> bool:
    """识别 gzh 章节标题块：外层 section 内含 'PART' + 大号数字 + 中文标题。"""
    if node.tag not in ("section", "div", "span"):
        return False
    style = node.attrs.get("style", "")
    if "flex" not in style:
        return False
    txt = _plain_text(node)
    has_label = "PART" in txt or "LAST" in txt
    has_number = bool(re.search(r"\d{2}", txt)) or "///" in txt
    return has_label and has_number


def _find_style_text(node: Node, *kw: str) -> str:
    """在节点子树里找 style 含任意关键字的直接文本。"""
    if node.tag == "#text":
        return ""
    style = node.attrs.get("style", "")
    if any(k in style for k in kw):
        t = _plain_text(node).strip()
        if t:
            return t
    for c in node.children:
        t = _find_style_text(c, *kw)
        if t:
            return t
    return ""


def _extract_chapter_header(node: Node):
    """从章节标题块提取 (编号, 中文标题, 英文标签)。

    基于结构槽位：英文标签在 font-size:11px（或 5-12px 小字）段落里，
    中文标题在 17px 段落里，编号在 28px/8px 里；比拼接文本更稳。
    防御：当 zh 为空（误判的孤立小容器如 flex-shrink:0 仅含 "01PART"）时，
    返回空三元组而非 None，让上层走常规渲染分支。
    """
    # 英文标签
    en = _find_style_text(node, "font-size:11px", "font-size:10px")
    if en and en.upper() != en:
        en = ""
    # 中文标题：17px（章节主标题字号）或最长的中文 p
    zh = _find_style_text(node, "font-size:17px")
    if not zh:
        zh = _find_style_text(node, "font-size:16px")
    # 编号
    number = ""
    m = re.search(r"(\d{2}|///)", _plain_text(node))
    if m:
        number = m.group(1)
    # 健壮：zh 空一律返回空三元组，调用方走 if zh: 分支判断
    if not zh:
        return "", "", ""
    return number, zh, en


def render(node: Node, is_code: bool = False, keep_layout: bool = False) -> str:
    if node.tag == "#text":
        return node.text

    tag = node.tag
    if tag in ("script", "style", "link", "meta"):
        return ""
    if tag in SVG_TAGS:
        return ""

    attrs = dict(node.attrs)
    style = attrs.get("style", "")
    attrs.pop("style", None)  # 稍后按白名单重放
    attrs.pop("leaf", None)   # gzh 的样式包裹标记，CSDN 无意义

    # ------- 目录横向滚动 -------
    if _has_scroll(node) and tag in ("section", "div", "ul"):
        # 横向滚动容器：转为 <ul> 列表
        lis = []
        for c in node.children:
            if c.tag in ("section", "div", "li"):
                text = _plain_text(c).strip()
                if not text:
                    continue
                lis.append(f"<li style=\"margin:0 0 6px;padding:4px 0;\">{text}</li>")
        if lis:
            return "<ul style=\"margin:0 0 20px;padding:0 18px;\">\n" + "\n".join(lis) + "\n</ul>"
        # 没有段落就继续常规

    # ------- section → 语义/div -------
    if tag == "section":
        # 章节标题块 → <h3>
        if _is_chapter_header(node):
            number, zh, en = _extract_chapter_header(node)
            if zh:
                h3_css = "color:#059669;font-size:22px;font-weight:800;margin:36px 0 12px;letter-spacing:0.5px;"
                # CSDN 真正保留 <h3> 语义与 <font color>，内联颜色仅兜底
                head = (f"<h3 style=\"{h3_css}\">"
                        f"<font color=\"#059669\"><strong>{number} · {zh}</strong></font></h3>")
                if en:
                    # 注意：英文小标签原为浅灰 #9CA3AF，在 CSDN 白底上对比度仅≈2.6:1，
                    # 几乎看不清；统一改为可读的中灰 #6B7280（对比度≈4.8:1，达 AA）。
                    en_css = "color:#6B7280;font-size:11px;font-weight:600;margin:0 0 16px;letter-spacing:1.5px;"
                    head += (f"<p style=\"{en_css}\"><font color=\"#6B7280\" size=\"2\">"
                             f"{en}</font></p>")
                    return head
        # 引用卡（虚线框 + 居中）→ blockquote
        if "dashed" in style:
            inner = "".join(render(c, is_code) for c in node.children)
            if inner.strip():
                css = sanitize_style(style, is_code, keep_layout)
                bq_css = css if css else ""
                if bq_css:
                    return f'<blockquote style="{bq_css}">{inner}</blockquote>'
                return f"<blockquote>{inner}</blockquote>"
            return ""
        # oneliner-card（居中 golden sentence）→ blockquote
        if "text-align:center" in style and "border:" in style:
            inner = "".join(render(c, is_code) for c in node.children)
            css = sanitize_style(style, is_code, keep_layout)
            return f'<blockquote style="{css}">{inner}</blockquote>'

        # 其余 section → div，去掉 flex 布局相关样式（sanitize 会丢弃）
        tag = "div"

    code_mode = is_code or tag in ("pre", "code")

    if tag == "br":
        return "<br>"

    # 代码块：保留 <pre><code>
    if tag == "pre":
        inner = "".join(render(c, True) for c in node.children)
        css = sanitize_style(style, True)
        pre_css = css or "background:#0B1220;color:#E5E7EB;border-radius:8px;padding:14px;font-family:Menlo,Consolas,monospace;font-size:13px;line-height:1.6;overflow-x:auto;"
        return f'<pre style="{pre_css}">{inner}</pre>'
    if tag == "code":
        inner = "".join(render(c, True) for c in node.children)
        css = sanitize_style(style, True)
        code_css = css or "background:#F3F4F6;color:#374151;padding:2px 3px;border-radius:4px;font-family:Menlo,Consolas,monospace;"
        return f'<code style="{code_css}">{inner}</code>'

    inner = "".join(render(c, code_mode) for c in node.children)
    stripped = inner.strip()

    # 空装饰移除：内容仅剩 <br>/空白/空占位 的容器与文字节点
    br_only_content = re.sub(r"<br\s*/?>", "", inner).strip()
    if (not stripped or not br_only_content) and tag in (
            "span", "div", "strong", "em", "b", "i", "section", "p", "li",
            "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"):
        # 装饰性占位（只有 br）→ 丢弃；确保有真实文本的不误删
        if _is_only_br(node) or (not br_only_content and inner and not _plain_text(node)):
            return ""
        if not stripped:
            return ""

    # 图片
    if tag == "img":
        src = attrs.get("src", "")
        if not src:
            return ""
        img_css = sanitize_style(style, False, keep_layout=True) or \
            "max-width:100%;height:auto;display:block;margin:0 auto;"
        alt = attrs.get("alt", "")
        sa = f' src="{src}"'
        if alt:
            sa += f' alt="{alt}"'
        return f'<img{sa} style="{img_css}">'

    # flex 内容盒（横向流程卡/三列对比等）→ 堆叠（子卡 transformed separately）
    if "flex" in style:
        # flex 容器：内部卡片变 div 堆叠；箭头→换行文本
        css = sanitize_style(style, is_code, keep_layout)
        if css:
            # 容器级 margin/background 保留
            return f'<div style="{css}">{inner}</div>'
        return f"<div>{inner}</div>"

    css = sanitize_style(style, is_code, keep_layout)
    if css:
        attrs["style"] = css
    else:
        attrs.pop("style", None)

    # 语义双轨提升：把关键 CSS 表现提升为 CSDN 保留的 HTML4 语义，
    # 内联 CSS 保留作兜底（适合部分环境仍识别 style 的场景）
    semantic_inline = tag in ("span", "p", "strong", "em", "b", "i",
                              "li", "td", "th", "div", "blockquote")
    if semantic_inline and inner and css and not code_mode:
        sem = _semanticize(inner, css)
        if sem != inner:
            inner = sem
            stripped = inner.strip()
            if not stripped:
                return ""

    # 表格单元格背景：转为 bgcolor 属性（CSDN 保留属性）
    if tag in ("td", "th", "tr"):
        bg = _css_bgcolor(style)
        if bg:
            attrs["bgcolor"] = bg

    # 去除 href="#" 连接
    if tag == "a":
        href = attrs.get("href", "")
        if href == "#" or not href:
            return inner

    # 如果子节点全非文本（纯嵌套容器），尝试收窄:如果是细分内联样式头部之类的无意义壳，丢弃
    if css:
        at = "".join(f' {k}="{v}"' for k, v in attrs.items())
        return f"<{tag}{at}>{inner}</{tag}>"

    if not css and not inner:
        return ""
    if not css:
        return f"<{tag}>{inner}</{tag}>"
    return f"<{tag}{''.join(f' {k}=\"{v}\"' for k, v in attrs.items())}>{inner}</{tag}>"


def sanitize_css(style: str, **kw) -> str:
    return sanitize_style(style, **kw)


def main():
    if len(sys.argv) < 2:
        print("用法: translate_gzh_to_csdn.py <gzh_body.html> [output.html]")
        sys.exit(2)
    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"✗ 找不到文件: {src}")
        sys.exit(2)

    html = open(src, encoding="utf-8").read().strip()
    try:
        dom = html_to_dom(html)
    except Exception as e:
        print(f"✗ HTML 解析失败: {e}")
        sys.exit(2)

    # 颜色安全降级：深底白字 → 浅底深字；rgba() → 纯色（跨平台必做，见文件头注释）
    for child in dom.children:
        _fix_color_safety(child)

    out_parts = []
    for child in dom.children:
        rendered = render(child)
        if rendered:
            out_parts.append(rendered)
    out_html = "".join(out_parts).strip()

    out = sys.argv[2] if len(sys.argv) > 2 else (
        os.path.splitext(src)[0] + "_CSDN.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(out_html)
    print(f"✓ 已生成 CSDN 兼容 HTML: {out}")
    print(f"  输出长度: {len(out_html)} 字符")
    return 0


if __name__ == "__main__":
    sys.exit(main())