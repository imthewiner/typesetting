# CSDN 富文本兼容清单与降级规则

本文是本 skill 的**单一权威来源**：CSDN 文章编辑器对粘贴内容的支持边界，以及从公众号 HTML 降级翻译时必须遵守的规则。任何与本表冲突的做法场景丢弃，以本表为准。

> **2026-10 实测更新（覆盖旧结论）**：从公众号 `_online.html`（base64 内嵌版）翻译出的 `_online_CSDN.html`，整段富文本粘贴进 CSDN 编辑器时，`data:image/...` 图片**可以正常转存**并显示。因此**含图文章默认走 base64 母版翻译**，`extract_images.py` 只在个别图片转存失败时兜底，不再是必做步骤。旧版「CSDN 必拒 data URI」的结论仅适用于「粘贴纯 `<img src=data:...>` 片段且编辑器未拿到完整富文本上下文」的场景。

## 0. 为什么需要这份清单

CSDN 的富文本编辑器（所见即所得，contenteditable）粘贴剪贴板里的富文本 HTML 时，会做一次**清洗（sanitize/filter）**：只保留它认识的标准语义标签与部分安全 CSS，其余折叠或丢弃。公众号编辑器则几乎原样保留我们写的内联样式。

所以同一套 gzh 排版 HTML：
- 粘贴到**公众号**：样式全保留（section/flex/gradient/shadow 都在）
- 粘贴到 **CSDN**：只保留 CSDN 白名单里的部分 → 需要先翻译成 CSDN 兼容形态

本 skill 的翻译器（`scripts/translate_gzh_to_csdn.py`）即按本表把 gzh HTML 一版性降级为 CSDN 兼容 HTML。

## 1. CSDN 富文本标签支持（实测推导）

| 标签 | 支持度 | 说明 |
|------|--------|------|
| `<p>` | ✅ 建议 | 段落容器，可带基础样式 |
| `<h1>`~`<h6>` | ✅ 建议 | 标题，保留 block 效果 |
| `<strong>` / `<b>` | ✅ | 加粗 |
| `<em>` / `<i>` | ✅ | 斜体 |
| `<span>` | ✅ | 行内容器，样式可保留部分 |
| `<ul>` / `<ol>` / `<li>` | ✅ | 列表 |
| `<blockquote>` | ✅ | 引用块 |
| `<pre>` / `<code>` | ✅ | 代码块（CSDN 代码区独立处理） |
| `<table>` / `<tr>` / `<td>` / `<th>` | ✅ | 表格；`bgcolor` / `align` / `width` 属性保留（内联 `background:` 不稳，表头底靠 `bgcolor` 或纯色内联）。`width:100%` 与 `border-collapse` 样式会被剥，需补 HTML 属性 |
| `<img>` | ✅ | http(s) 直链稳定；`data:` base64 在整段富文本粘贴时可转存（见文首实测更新），个别失败再用 `extract_images.py` 抽文件手传 |
| `<a>` | ✅ | 链接 |
| `<hr>` | ✅ | 分割线 |
| `<div>` | ⚠️ 可用 | 块级容器，但**类/ID 会被剥离**，尽量少用；嵌套层级建议 ≤2 |
| `<section>` | ❌ **不可靠** | 会被折叠/改写，降级翻译为 `<div>` 或语义块 |
| `<style>` | ❌ | 全局样式标签会被过滤 |
| `<script>` | ❌ | 无意义，全过滤 |
| SVG (inline) | ⚠️ 部分情况支持，不建议依赖 | CSDN web 端富文本对 SVG 支持不稳定；公众号版的三连图标等 SVG 在 CSDN 降级为文字 |
| `class` / `id` 属性 | ❌ | 一律剥离，靠内联样式 |

## 2. 样式保真策略（HTML4 语义 > 内联 CSS）

**核心结论（本轮全网查证）**：CSDN 富文本/Markdown 编辑器粘贴时对 HTML 做「语义标签 + HTML4 属性」清洗——`<del>/<strong>/<font color size>/<h1-h6>/<table bgcolor>` 这类 HTML4 语义**稳定保留**；而内联 `style="color:/background:/font-size:/border:"` 在**富文本编辑器里多数被剥**（表现为"标题变大但颜色没了、删除线没了、边框没了"）。

因此翻译策略必须**双轨**：关键效果优先提升为 HTML4 语义标签/属性，内联 CSS 只在 HTML4 无对应时兜底、且**不依赖它生效**。

### 2a. 颜色/字号/加粗/删除线 → HTML4 语义（优先使用）

| 想要的效果 | 优先写法（HTML4 语义） | 兜底内联（不保证） |
|-----------|------------------------|--------------------|
| 文字颜色 | `<font color="#059669">…</font>` | `style="color:#059669"` |
| 字号 | `<font size="1..7">`（1=最小） | `style="font-size:18px"`（不一定保留） |
| 加粗 | `<strong>…</strong>` / `<b>` | `style="font-weight:700"`（不一定保留） |
| 删除线 | `<del>…</del>`（或 `<s>`） | `style="text-decoration:line-through"`（经常被剥） |
| 斜体 | `<em>` | `style="font-style:italic"` |
| 表格背景 | `<td bgcolor="#F0FDF4">` / `<tr bgcolor>…` | `style="background:#…"`（不稳定） |

字号映射（px → size，经验值）：`12px≈1，14px≈2，16px≈3，18px≈4，22px≈5，26px≈6，32px+≈7`。

### 2b. 内联 CSS 属性处理

以下属性 CSDN 清洗器**多数保留**，可作兜底（但不要作为唯一手段）：

```
text-align
line-height
padding / margin（数值）
max-width / width / height（数字）
border（simple / solid；dashed 支持弱）
border-radius（部分）
font-family
```

**颜色安全红线（跨平台实测教训，翻译器已自动执行）**：

| 场景 | 风险 | 处理（翻译器自动做） |
|------|------|------|
| `color:rgba(255,255,255,0.9)` 这类半透明白文字 | 部分平台背景被剥离 → 白底白字不可见 | **反色**：底色变浅、文字变深（如 `#e1f2ed` 底 + `#04704f` 字） |
| `background:rgba(255,255,255,0.2)` + `color:#fff` 小标签 | 部分平台 rgba 背景与白字都变白 → 不可见 | **合成纯色**：rgba 合成到父背景成 hex，文字转深色 |
| `background:#111827` + `color:#fff` 的 STEP 胶囊 | 黑底只盖住半个字高，剥离后白字白底 → 半个字可见 | **反色**：浅灰底 `#e2e3e5` + 深字 `#0d121d` |
| 任何 `rgba()`/`rgb()` 颜色（含 border） | 平台支持不稳 | **一律转纯色 hex**（合成到白色/父背景上） |
| `<font color="#fff">` 白字 | 背景剥离后不可见 | 反转为深色 `<font color="#04704f">` 等 |

> 结论：**跨平台正文里不要出现「深底白字」与 `rgba()`**。深色文字 + 浅色底永远安全。

**清洗器大概率丢弃或不支持**（不要依赖）：

| 属性 | 风险 | 处理 |
|------|------|------|
| `display:flex` | ❌ 不支持，会被打平 | 移除该块或转成块级堆叠 |
| `display:inline-block` 布局 | ⚠️ 部分保留 | 尽量不用做横向布局 |
| `gap` | ❌ | 移除，改用 margin |
| `align-items` / `justify-content` | ❌ | 移除 |
| `box-shadow` | ⚠️ 有时保留、有时丢 | 不依赖，用边框替代观感 |
| `position:absolute/fixed/sticky` | ❌ 不支持 | 移除，造成布局靠流式 |
| `float` | ❌ | 移除 |
| `flex-*`（flex/1、flex-shrink…） | ❌ | 移除 |
| `overflow-x: scroll` | ⚠️ 分类差 | 移除横向滚动 |
| `background:linear/radial-gradient` | ⚠️ 不稳 | 富文本首选 `bgcolor`/纯色，白底文章不依赖渐变 |
| `color` 内联 | ⚠️ 富文本不稳 | **改用 `<font color>`** |
| `font-size` 内联 | ⚠️ 富文本不稳 | **改用 `<font size>`** |
| `border` 卡片观感 | ⚠️ | 三连/步骤卡外观 CSDN 难复刻，接受简化（色块或加粗字） |
| `letter-spacing` | ⚠️ | 不依赖 |
| `cursor`/`opacity`/`text-overflow`/`-webkit-*` | ⚠️/❌ | 移除 |

## 3. 降级映射规则（gzh 组件 → CSDN 语义块）

| gzh 组件/模式 | CSDN 翻译目标 |
|---------------|---------------|
| 多层 `<section>` 嵌套 | 折叠为层数 = 1-2 的 `<div>`（或语义标签），去除 flex |
| `display:flex` 横向封面/目录 | 逐行 div 堆叠（封面：章节块依次上下堆；目录：改为 `<p>PART 01 ...` 一行概述） |
| 横向滚动目录 toc-scroll | 纯文本目录段落：`01 为什么慢 ｜ 02 三步法 ｜ 03 套用全场景`，或用 `<ul><li>` 列表 |
| 章节标题数字 + PART | `<h3>` 内联样式，格式 `01 · 中文标题`，英文标签移入括号或去掉 |
| 5+ 级 emphasis（黄/绿高亮、下划线） | `<strong>` / `<span style="border-bottom...">` + 内联色，去掉多层嵌套 |
| 引用块 quote-box / oneliner-card | `<blockquote>` + 左 border 样式 |
| 代码块 `<pre class="hljs">` | 保留 `<pre><code>`（CSDN 代码区）；去掉 `.hljs` class 与 `leaf` 包裹减少干扰 |
| 表格 | `<table>` 原样内联样式，缩小表头样式简化 |
| 作者签名 / 互动三连 | `<p>` 赏析签一段 + 简化 `<p>` 文字 |
| SVG 图标 | 移除或换 unicode（👍/🔗/💬） |
| `<span leaf="">` | 移除 `leaf` 属性；但**文字继续用 `<span>` 包**以保住内联样式（CSDN 保留 span 内 style） |
| 装饰性空 `<span><br></span>` | 移除 |

## 4. 平台的硬性红线（validate_csdn_html.py 会查）

- ❌ `<section>`、`<div>` 可留可、少用）；`class=`、`id=` 一律禁止
- ❌ `<style>`/`<script>`/`<link>` 禁止
- ❌ `display:flex|grid`、`gap`、`position:absolute/fixed`、`float`、`@media`/`@keyframes`/`@import`、`var(--x)`
- ❌ `rgba()`/`rgb()` 颜色（含 border）、`color:#fff`/`#ffffff`/`white`、`<font color="#fff">`、`background:black/#000`
- ❌ 外部字体
- ✅ 允许：`<p>/<h1-h6>/<strong>/<span>/<ul>/<ol>/<li>/<blockquote>/<pre>/<code>/<table>/<img>/<hr>/<a>/<font>/<del>/<s>/<ins>/<u>/<sup>/<sub>/<center>`，样式全部内联 + HTML4 属性（`color`/`size`/`bgcolor`/`align`/`width`/`height`/`colspan`/`rowspan`）
- ✅ `<img>`：http(s) 直链稳定；整段富文本粘贴时 base64 data URI 可转存（见文首实测更新）。转存异常时再用 `extract_images.py` 抽成独立文件，用户上传 CSDN 后替换 src。

## 3. 校验结果判定

在校验器输出里：

- **ERROR** = CSDN 清洗器会丢弃/ 必然失效（标签/属性/样式），**必须修复到 0**。
- **WARNING** = CSDN 兼容性弱但通常能用（如 `letter-spacing`），修复到 0 更稳妥，至少人工确认。
- 无 ERROR 无 WARNING → 「兼容 CSDN 富文本粘贴」。

## 4. 使用边界

本 skill 只处理**公众号内容 → CSDN 富文本**的翻译。直接把翻译产物再贴回公众号会导致公众号高级样式丢失——发布渠道决定用哪一版，两个产品不能互相替换。