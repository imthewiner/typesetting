---
name: typesetting
description: 摸鱼绿双平台排版引擎：把一篇文章（Markdown / Word / PDF / 纯文本）排成微信公众号版，再翻成 CSDN 版，两版共用同一套 emerald 绿色杂志风。公众号侧产出可直接粘贴的 `<section>` 正文 + 一键复制预览页；CSDN 侧把公众号 HTML 降级翻译成富文本兼容 HTML（语义标签 + HTML4 属性），并做校验与预览。触发场景：(1) 用户要"公众号排版 / 公众号文章 / 微信排版 / 摸鱼绿排版 / 自动排版"，(2) 用户要把文章排成公众号后同步发 CSDN、掘金、博客园，(3) 用户说"公众号 + CSDN 双版 / 一稿两发 / CSDN 兼容排版"，(4) 用户已有公众号 HTML 要转 CSDN 富文本。不用于普通网页、落地页、PPT。
---

# 摸鱼绿双平台排版 Skill

**一份稿子，两版产物**：公众号版保留摸鱼绿的卡片、渐变、横滑目录；CSDN 版把同一套视觉降级成 CSDN 富文本能存住的语义标签。两个平台读起来是同一篇文章，但各自都合规。

核心原则：**公众号 HTML 是母版，CSDN 版由母版翻译而来**。不要为 CSDN 从零手写第二套，否则两版气质会漂移，且以后改稿要改两遍。

## 资产地图

| 路径 | 作用 |
|------|------|
| `references/theme-moyu-green.md` | 摸鱼绿组件库：设计变量 + 全部组件 HTML + 文章骨架 + 类型配方 + Markdown 映射 |
| `references/common-components.md` | 通用增量库：代码块、图片/GIF、小标签标题（全主题共用） |
| `references/theme-index.md` | 主题索引（当前只有摸鱼绿） |
| `references/format-normalize.md` | docx / PDF / 纯文本 → Markdown 的归一化规则 |
| `references/csdn-compat.md` | CSDN 富文本白名单与降级规则（CSDN 侧单一权威） |
| `references/translate-rules.md` | gzh HTML → CSDN HTML 的逐标签翻译表 |
| `references/csdn-manual-fixes.md` | 翻译后固定手改清单（目录/封面/三连/表格等 9 项） |
| `scripts/validate_gzh_html.py` | 公众号 HTML 合规校验（ERROR 必须清零） |
| `scripts/upload_images.py` | 本地图片 → base64 内嵌 / 图床直链，产出 `_online.html` |
| `scripts/wrap_preview.py` | 公众号预览页（右上角「复制到公众号」按钮） |
| `scripts/translate_gzh_to_csdn.py` | 公众号 HTML → CSDN 兼容 HTML |
| `scripts/validate_csdn_html.py` | CSDN HTML 合规校验（ERROR 必须清零） |
| `scripts/wrap_csdn_preview.py` | CSDN 预览页（「复制到 CSDN」按钮） |
| `scripts/extract_images.py` | base64 图片抽成独立文件（CSDN 转存失败时兜底） |
| `scripts/build_both.py` | 一键跑完「校验 → 内嵌图 → 双预览 → 翻译 → 再校验」 |
| `assets/preview-template*.html` | 两个预览外壳模板，勿改文件名 |

所有脚本仅依赖 Python 3 标准库，无需 pip 安装。命令统一写成 `python <SKILL_ROOT>/scripts/xxx.py`，`<SKILL_ROOT>` 是本 skill 目录的绝对路径。

---

## 工作流总览

```
输入（md/docx/pdf/纯文本/已有公众号 HTML）
   │
   ├─ 阶段 1  公众号版：解析结构 → 取摸鱼绿组件 → 装配 → 校验 → 内嵌图 → 预览
   │            产物：xxx_排版_摸鱼绿(moyu-green).html （+ _online.html / _预览.html）
   │
   └─ 阶段 2  CSDN 版：拿阶段 1 的 HTML 翻译 → 校验 → 手改 → 预览
                产物：xxx_排版_摸鱼绿(moyu-green)_CSDN.html（+ _CSDN_预览.html）
```

用户只说要公众号 → 做完阶段 1 即交付；只说 CSDN → 仍先做阶段 1 母版再翻译（直接对未来样式排 CSDN 会又丑又难维护）；说双版 → 两阶段都做完。

---

## 阶段 0 输入与归一化

- `.md` 或 Markdown 文本 → 直接进阶段 1。
- `.docx` → `python <SKILL_ROOT>/scripts/extract_docx.py <文件>`；`.pdf` → 用 Read 分页读取并清噪；`.txt`/无标记纯文本 → 按标题启发式推断结构。三者都要先按 `references/format-normalize.md` 转成 Markdown 草稿，结构不确定时先和用户确认章节划分。
- 已有公众号 HTML（文件名含 `_排版_`）→ 跳过阶段 1 的装配，直接校验后进阶段 2。
- 什么都没给 → 向用户索要，不要凭空造稿。

**全自动模式**：用户说「直接排 / 一键 / 不用问」时，不问结构、不问主题，直接按题材装配并在交付时说明章节划分与标题拟定理由。

---

## 阶段 1 公众号版

### 1.1 解析结构并判定文章类型

| Markdown 元素 | 识别规则 |
|------|---------|
| 文章标题 | `# 标题` 或 frontmatter `title`（公众号标题在平台设置，正文不用它） |
| 开头引言 | 文章最开头的 `> 引用` |
| 章节 | `## 标题`；子章节 `### 标题` |
| 强调 | `**加粗**`、`==高亮==`、`<u>下划线</u>` 或 `++文字++`、`~~删除线~~` |
| 引用段 | 非开头的 `> 文字` |
| 图片 / GIF | `![说明](URL)`、`![](xxx.gif)`（GIF 当图片处理） |
| 代码 | ` ``` 围栏 ``` `、行内 `` `code` `` |
| 列表 / 表格 / 分割线 | `- 项`、`1. 项`、`\|` 表格、`---` |

判类型（取主导类型，可复合）：教程/操作指南、盘点/工具清单、观点/深度分析、访谈/人物特稿、数据复盘/报告、生活/情感随笔、案例实战。步骤命令多→教程；并列条目多→盘点；引语叙事多→访谈；数字对比多→数据；论证推演多→观点。

### 1.2 取组件（两份都要读）

1. `references/theme-moyu-green.md` —— 摸鱼绿专属组件（封面、目录、章节标题、行内样式、标签、引用、提示、布局、媒体、结尾）。
2. `references/common-components.md` —— 代码块、图片、小标签等通用增量组件，颜色套摸鱼绿主色。

**HTML 一律从组件库取，不凭记忆手写**；编号以语义为准，不同库编号不统一。

### 1.3 按配方装配

先查 theme 文件的「文章类型 → 组件组合配方」表，确定本篇核心组件组合（教程用 step-label + 代码块；盘点用 tool-label + tool-card + pill-list；观点用 paragraph + quote-box + oneliner-card……），点缀组件全文 ≤3 种。

骨架顺序以 theme 文件的「完整文章模板骨架」为准，固定顺序是：

```
封面 cover-breaking → 目录 toc-scroll → 开头引言 oneliner-card
→ 前言正文 → 第 1 章 chapter-title（margin-top:16px）→ 第 2…N 章（margin-top:48px）
→ 结语章（编号 ///、PART 改 LAST、章名「写在最后」）
→ 作者签名段 → 互动三连 footer-cta → 品牌尾图（有素材才加）
```

目录必须紧跟封面之下、在引言和正文之前。

### 1.4 生成时必须做的智能处理

1. **章节自动编号**：按 `##` 顺序 `01/02/03…`，末章若为总结/结语用 `///`。
2. **英文标签**：据中文章节名生成（实测→TEST、教程→TUTORIAL、总结→SUMMARY、思考→THOUGHTS…）。
3. **正文关键词下划线（核心特色）**：每个正文段落主动找 1–3 个最重要短语，用 `border-bottom:2px solid #A7F3D0;font-weight:600` 标记；短语 4–15 字；整段无要点可跳过，但不要整篇漏标。
4. **引言关键词高亮**：开头金句里的核心词用黄色渐变高亮。
5. **目录取精选 3 个看点**，不是全章节列表。
6. **作者署名（固定，末尾唯一一处）**：默认 `我是 百年江湖 随意沉浮，怕什么真理无穷，进一步有进一步的欢喜`；第二句 `如果你觉得今天这篇有收获，欢迎点赞、在看、转发三连，我们下篇见`。用户给了别的署名才替换；原文自带签名段则沿用原文并合并成这一处。
7. **工具清单说明段（工具盘点/合集/教程类自动加）**：出现 ≥3 个工具名时，在签名段后、三连前插入 9a `quote-box` 灰底虚线框，固定话术：
   `📒 附：文中涉及的每一款工具，我都按章节整理在了这份合集里，感兴趣的话翻一翻就好，没有所谓的「全套打包」，按需取用即可。`
   纯观点/方法论/随笔不加，避免软广嫌疑。
8. **中文全角标点**：正文标点一律全角（，。！？：；""''（）——…），生成时直接写弯引号；代码块、行内代码、URL、英文标识符内部保持原样。
9. **图片自适应**：`<img>` 统一 `max-width:100%;height:auto;display:block;margin:0 auto`，不用 `width:100%`。

### 1.5 校验（强制）

```powershell
python <SKILL_ROOT>\scripts\validate_gzh_html.py <生成的.html>
```

- ERROR 必须为 0：`<div>`、`class/id`、`<style>/<script>`、`position:fixed/absolute`、`float`、`display:grid`、CSS 变量、外部字体、文字未包 `<span leaf="">`。
- **半角标点 WARNING 也要修到 0**，这是最高频返工点。
- 报错就回 1.3 改组件，不要手改校验器。

### 1.6 图片转可粘贴形态（有本地图必做）

```powershell
python <SKILL_ROOT>\scripts\upload_images.py <干净正文.html>
```

默认 `--mode base64`：本地图转 data URI 内嵌，产出 `_online.html`，公众号粘贴时自动转存微信 CDN。网络可用且想要直链时加 `--mode host --host catbox`，单图失败自动降级 base64。不改原文件。

### 1.7 预览与产物命名

```powershell
python <SKILL_ROOT>\scripts\wrap_preview.py <要粘贴的那份.html>
```

- 有图 → 传 `_online.html`，产出 `..._online_预览.html`；无图 → 传干净正文，产出 `..._预览.html`。
- **含图却拿干净正文打预览 = 图片相对路径丢失，属于返工事故，禁止。**
- 产物格式：纯 `<section>…</section>` 正文片段，不带 `<!DOCTYPE>/<html>/<head>/<body>`。

命名规范：

| 产物 | 文件名 |
|------|--------|
| 公众号干净正文 | `{原文件名}_排版_摸鱼绿(moyu-green).html` |
| 公众号内嵌图版 | `{原文件名}_排版_摸鱼绿(moyu-green)_online.html` |
| 公众号预览页 | 上者 + `_预览.html` |
| CSDN 正文 | 母版名 + `_CSDN.html`（如 `..._online_CSDN.html`） |
| CSDN 预览页 | CSDN 正文 + `_预览.html`（如 `..._CSDN_预览.html`） |

---

## 阶段 2 CSDN 版

### 2.1 选对母版

- **含图文章必须拿 `_online.html`（base64 版）翻译**：粘贴时 CSDN 会把 data URI 转存为站内图（已实测）。从干净正文翻译会得到 `images/xxx.png` 相对路径，CSDN 报「非正常图片地址，图片转存失败」。
- 无图文章用干净正文即可，产物更小。
- 只有 Markdown、没有公众号母版 → 先回阶段 1。

### 2.2 翻译

```powershell
python <SKILL_ROOT>\scripts\translate_gzh_to_csdn.py <母版.html>
```

翻译器做的事：`<section>` 降级为语义块；章节标题按结构槽位重提为 `<h2>/<h3>`；按白名单保留样式，丢弃 flex/grid/gap/position/box-shadow/横向滚动；`rgba()` 与「深底白字」统一反转为浅底深字；装饰性空 span、SVG 移除；关键表现提升为 `<font color/size>`、`<strong>`、`<del>`、`bgcolor` 等 HTML4 语义。

### 2.3 校验

```powershell
python <SKILL_ROOT>\scripts\validate_csdn_html.py <..._CSDN.html>
```

ERROR 必须为 0：残留 `<section>`、flex/grid、`rgba()`/`rgb()`、`color:#fff`、`#111827` 黑底、`<svg>`、`class/id`、外部字体。若出现颜色类 ERROR，说明翻译脚本的 `_fix_color_safety` 有漏项——**修脚本后重跑，不要手改产物绕过**。

### 2.4 固定手改（按 `references/csdn-manual-fixes.md` 逐项过）

翻译器打平 flex 后会留下几处粘连：目录 `PART 01标题副标题` 连写、封面日期贴左、残留「👉 滑动」、三连竖排三行、末章 `/// · 写在最后`、代码块浅灰字发飘、表格缩宽 / 窄表头竖排、编号列表圆点变横条。九项修法见清单，通常 5 分钟。

### 2.5 预览

```powershell
python <SKILL_ROOT>\scripts\wrap_csdn_preview.py <..._CSDN.html>
```

预览页点「复制到 CSDN」→ 粘贴进 CSDN 富文本编辑器。base64 图正常转存；个别图转存失败时才跑：

```powershell
python <SKILL_ROOT>\scripts\extract_images.py <..._CSDN.html>
```

抽出 `images/<基名>/img-01.png…`，由用户手动上传 CSDN 后替换为 `img-blog.csdnimg.cn` 直链。

---

## 一键脚本

母版 HTML 已经就绪时，一条命令跑完剩余全部机械步骤：

```powershell
python <SKILL_ROOT>\scripts\build_both.py <母版.html>
```

它会依次：校验公众号 → 有本地图则内嵌并生成 `_online.html` → 公众号预览 → 翻译 CSDN → 校验 CSDN → CSDN 预览，最后打印全部产物路径。任一步 ERROR 立即停下并指明回哪一步修。可选参数：`--no-preview` 不出预览页，`--host catbox` 改用图床直链。

---

## 平台规则对照

| 项目 | 公众号版 | CSDN 版 |
|------|---------|---------|
| 块容器 | `<section>` | `<div>`（≤2 层）/ 语义标签 |
| 文字包裹 | 必须 `<span leaf="">` | 去掉 `leaf`，保留 `<span>` |
| 布局 | 可用有限 flex、渐变、阴影、圆角 | 全部打平，靠块级堆叠 + 边框 |
| 颜色 | 可用 `rgba()`、深底白字 | 禁止 `rgba()`、禁止深底白字 |
| 标题 | 组件化 PART 编号 | 真 `<h2>/<h3>` + 英文小标 `<p>` |
| 目录 | 横向滚动卡片 | `<ul><li>` 或单行文本 |
| 图标 | 内联 SVG 可用 | 换 unicode 或删 |
| 图片 | 相对路径 → base64 内嵌 | base64 可转存；失败则抽文件手传 |

**两版不可互换**：CSDN 版贴回公众号会丢高级样式；公众号版直接贴 CSDN 会掉色掉布局。

---

## Gotchas（真实踩过的坑）

- **漏 `<span leaf>`** 是公众号最致命错，粘贴后样式整片消失；靠 1.5 校验兜底。
- **含图却用干净正文做预览/翻译**：图全丢。认准 `_online.html`。
- **章节编号跳号 / 结语编号用在中间章**：严格按 `##` 顺序。
- **签名区出现两次**：原文自带签名要并入唯一签名区，不要保留原段又加一段。
- **下划线整段划 or 整篇漏**：逐段 1–3 个短语，列表项里的关键描述也要标。
- **锚点层滥用**：最强强调（绿色加粗/黄底下划线/亮点卡）全文 ≤5 处。
- **代码块用 `white-space:pre`**：会把源码缩进渲染成大左缩进 + 空行；用「每行一个 `<p style="margin:0">`」，缩进只用全角空格 `　`。
- **不用四周虚线框包标题**：突出小标题用左竖条/药丸标签；例外是摸鱼绿自带的 quote-box、oneliner-card（这是主题特征）。
- **占位图/【插入…】残留**：没有真实素材就整块删掉；待补素材用通用库 2c 居中占位板块。
- **CSDN 表格宽度**：翻译器会剥 `width:100%` 和 `border-collapse`，必须补 HTML 属性。
- **CSDN 里加 `nowrap`**：校验器判 ERROR，用 `th width` 解决竖排。

---

## 维护

- **改视觉**：只改 `references/theme-moyu-green.md`，公众号版立即生效；CSDN 版由翻译器自动跟随，涉及新组件时同步补 `translate-rules.md` 的映射行。
- **改 CSDN 降级规则**：以 `references/csdn-compat.md` 为准，同步改 `translate_gzh_to_csdn.py` 与 `validate_csdn_html.py`，再跑一遍实测样例。
- **回归样例**：`assets/sample-article.md` 可排一版公众号 → 翻 CSDN，作为改动后的最小回归。

## 出处与许可

- 公众号排版体系（组件库、校验器、预览器、格式归一化）来自 [gzh-design-skill](https://github.com/isjiamu/gzh-design-skill)（作者：甲木 × 摸鱼小李），AGPL-3.0；本仓库保留原许可，见 `LICENSE` 与 `NOTICE.md`。
- CSDN 翻译体系（翻译器、CSDN 校验器、CSDN 预览器）来自本机 `csdn-design`，与本 skill 合并维护。
- 本 skill 把两者收敛为「摸鱼绿一稿两发」单入口，并补了 `build_both.py` 与手改清单；上游更新时可对照差异选择性吸收。
