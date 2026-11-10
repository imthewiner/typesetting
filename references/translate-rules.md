# gzh HTML → CSDN HTML 翻译规则

本文件给翻译器（`scripts/translate_gzh_to_csdn.py`）与模型都提供统一的翻译决策。翻译输入是公众号侧产出的**干净正文 HTML**（`{原文件}_排版_{主题}({id}).html`，纯 `<section>` 片段；含图时用 base64 的 `_online.html`），输出是 CSDN 富文本兼容 HTML。

**总原则**：保留"主题气质"（配色、字号层级、关键强调、章节编号、落款），丢弃"高级布局"（flex、卡片、横向滚动、阴影、渐变渐变），转成 CSDN 白名单里的语义标签 + HTML4 属性（`<font color size>/<del>/<strong>/<td bgcolor>`），内联 CSS 仅兜底且不依赖。

> **双轨规则（最重要）**：CSDN 富文本粘贴更认得 HTML4 语义标签/属性，不认得多数内联 `style=`。
> - `text-decoration:line-through` → `<del>…</del>`
> - `font-weight:700/800/900` → `<strong>…</strong>`
> - 内联 `color:#…` → `<font color="#…">…</font>`
> - 内联 `font-size:..px` → `<font size="1..7">…</font>`（12px→1, 14px→2, 16px→3, 18px→4, 22px→5, 26px→6, 32px+→7）
> - 内联 `background:`（表格） → `bgcolor` 属性

## 0. 输入约定

- 输入：gzh 干净正文文件（已过 validate_gzh_html.py，无 class/id/style/script/div）
- 输出：CSDN 兼容 HTML（纯 body 片段，无外框，供预览页嵌入）
- 若输入含 `<img src="本地路径">`：先 `upload_images.py` 转 base64 内嵌再翻译；含图文章**必须**用 `_online.html` 作输入，整段富文本粘贴 CSDN 时 base64 可正常转存（2026-10 实测）。个别图片转存失败时才用 `extract_images.py` 抽成独立文件、手传后替换 src。

## 1. 标签翻译表（自上而下遍历 DOM）

gzh 结构以 `<section>` 多层嵌套 + `<p>/<span>/<strong>/<img>` 为主。翻译规则按"父 section 的功能"和"内部结构"判定：

| gzh 元素/结构 | CSDN 目标 | 说明 |
|---------------|-----------|------|
| 最外层 `<section style="max-width:677px...">` 全局容器 | 忽略外层壳，直接保留内层 | 不需 max-width 容器（CSDN 全文固定宽度），但若想统一底色可包一个 `<div style="max-width:677px;margin:0 auto;background:#fff;...">` |
| 外层 section 且含 `display:flex` | 移除 flex，内部块按文档流堆叠 | section 本身转 `<div>` 或删除壳 |
| `display:flex;align-items:center;...` 组成双列（封面标题+图） | 转 `<div>`（避免并排，直接堆叠）；有图片时 `<img>` 保留居中 | 封面区块整体转为"标题式块" |
| 横向目录 `overflow-x:scroll;white-space:nowrap` | 转为 `<ul><li>` 列表，每章一行 `PART 01 ｜ 标题` | 不可滚动，保证全部可见 |
| 章节标题 `PART 01 + 中文标题 + EN sub` | `<h3 style="...">01 · 中文标题</h3>`，EN 小标转为 `<p style="...">EN SUBTITLE</p>` | 保留主题主色字号层次 |
| 章节内正文 `<p style="font-size:14px;line-height:1.9;...">` | `<p>` 原样，样式降级保留（见样式降级表） | 保持 `text-align:justify;color:#374151;` 等 |
| 正文行内强调 `<span style="border-bottom:2px solid #A7F3D0;...">` | 保留 `border-bottom` + 加粗，改放 `<span>` 上；如需更稳健可转 `<strong>` | underline 关键词语义等价 |
| 行内 `<strong style="color:#059669;">` | 原样保留 | |
| quote-box / oneliner-card（虚线边框卡片） | `<blockquote style="border-left:3px solid #059669;background:#F0FDF4;padding:...">…</p></blockquote>` | 引用语义 |
| `background:#F0FDF4/... 提示卡`（非 quote） | `<div style="background:...;border:1px solid ...;border-radius:...;padding:...">…</div>` | 盒子降级为简单 div，边界以内联 |
| 代码块 `<pre class="hljs">…</pre>` | `<pre style="background:#0B1220;color:#E5E7EB;..."><code>…</code></pre>` | 保留深/浅底色，去掉 hljs class 与 leaf |
| `<table>` | 保留 `<table style="width:100%;border-collapse:collapse;...">` + thead/tbody；表头/隔行底色用 **`<th bgcolor="#059669">` / `<td bgcolor="#F0FDF4">`**（内联 `background:` 在 CSDN 富文本不稳定） | 表头保留主色底白字 |
| 三连图标 `<section style="display:flex"><svg>...` | 转纯文字：`👍 点赞 👍 在看 🔗 转发` | SVG/icon 在 CSDN 不可靠 |
| 签名段 / CTA 卡 | `<p>` 文本 + `<div style="text-align:center;padding:...">` 简化 | CTA 卡片不追求视觉，保留文案 |

## 2. CSS 样式降级表

对每个节点的事件 `style=""` 做**属性级过滤**：

| 原属性 | 动作 |
|--------|------|
| `display` | `flex`/`grid`/`inline-flex` → 删除；`inline-block` 保留布尔（不依赖布局） |
| `gap` | 删除 |
| `align-items` / `justify-content` | 删除 |
| `flex*`（flex、flex-shrink、flex-grow） | 删除 |
| `position: absolute/fixed/sticky` | 删除（若该元素因此不可见，由模型按语义决定去留） |
| `float` | 删除 |
| `box-shadow` | 删除（少量可保留但默认删，边框替代） |
| `letter-spacing` | 保留 |
| `overflow` 滚动类 | `scroll`/`auto` 横向 → 删除（无滚动） |
| `width`/`height` | 数字+px 保留；`flex:1` 类删除 |
| `background` 若为 `linear-gradient` | 保留（CSDN 部分支持）若渐变依赖 flex 布局场景成熟，留纯色兜底：`background:#059669` |
| `background` 若为 `radial-gradient` | 转纯色（取该渐变内层色） |
| `border`（含 dashed/solid） | 保留，`dashed` 部分 CSDN 保留度低 → 可转 `solid`+浅色 |
| `border-radius` | 保留（部分支持） |
| `text-transform` | 保留 |
| `cursor` | 删除 |
| `-webkit-*` | 删除 |
| `white-space:nowrap` | 删除 |

### 2a. 颜色安全降级（跨平台不兼容色系，**翻译器自动做，人工不要绕回**）

跨平台（CSDN/博客园/掘金等）粘贴时，**「深底白字」与 `rgba()` 颜色必踩坑**，翻译器
（`_fix_color_safety`）统一降级，产出物里**不允许再出现**以下形态：

| 源 gzh 形态（例子） | CSDN 目标（安全形态） |
|------|------|
| `color:rgba(255,255,255,0.9)` 半透明白字（如 AIBook 底部条） | 底反浅 `#e1f2ed` + 字反深 `#04704f` |
| `background:rgba(255,255,255,0.2)` + `color:#fff` 标签（如 `避坑指南`/`第1章`） | 底合成纯色 `#e7f5f1` + 字反深 `#04704f` |
| `background:#111827` + `color:#fff` 的 STEP 胶囊 | 底反浅 `#e2e3e5` + 字反深 `#0d121d` |
| 任何 `rgba()`/`rgb()`（含 border 内颜色） | 一律转纯色 hex（合成到父背景/白色上） |
| `<font color="#fff">` 白字 | 反转为深色 `<font color="#...">` |

原则：**深色文字 + 浅色底**在任何平台都安全；白字 + 深底依赖背景被保留，不可依赖。

## 3. 文本与 span leaf

- `<span leaf="">` 目标：`leaf` 属性去掉。**文字仍需 `<span style="...">` 或 `<strong>` 包裹**，保证 CSDN 粘贴后样式留在行内元素上。
- 装饰性 `<span leaf=""><br></span>`（圆点/分割线占位）→ **删除**。
- 文字内容保持不变；由 gzh 侧已处理全角标点。

## 4. 骨架输出（CSDN 兼容版）

```
<div style="max-width:677px;margin:0 auto;padding:16px 8px;color:#374151;font-size:14px;line-height:1.8;">
  [封面]（转成标题式块，可留品牌行）
  [目录]（ul 列表）
  [开头引言]（blockquote）
  正文...
  章节→ <h3> 标题 + <p> EN 标
  ...
  [签名] <p>
  [三连] 文字版
</div>
```

无 `<!DOCTYPE>/<html>/<head>/<body>`。样式全内联。

## 5. 校验产物

翻译产出的 HTML 跑 `validate_csdn_html.py` 到 0 ERROR（0 WARNING 最佳）。ERROR 条目回译解决；若该 ERROR 属于"主题天然表现"，按本规则降级为允许形式重写。