# typesetting · 摸鱼绿双平台排版

把一个 skill 用在两个平台：**微信公众号 + CSDN**，共用同一套「摸鱼绿」emerald 绿色杂志风。

- **公众号版**：卡片、渐变、横向滚动目录全套保留，产出可直接粘贴进公众号编辑器的 `<section>` 正文 + 一键复制预览页。
- **CSDN 版**：把公众号母版降级翻译成 CSDN 富文本能存住的语义 HTML（`<h3>`、`<font color/size>`、`<del>`、`bgcolor`），配色自动避开「深底白字 / rgba」两个跨平台雷区。

一稿两发，不用维护两套模板。

## 安装

把整个目录放进你的 skill 根目录即可，目录名建议保持 `typesetting`：

```powershell
# 示例：opencode / Claude 类工具
Copy-Item -Recurse . "$env:USERPROFILE\.config\opencode\skills\typesetting"
```

豆包办公用户放进 `.skills` 根目录：

```powershell
Copy-Item -Recurse . "C:\Users\<你>\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.skills\typesetting"
```

无需安装依赖，脚本只用 Python 3 标准库。

## 用法

对 Agent 说：

> 帮我把这篇排成公众号，再出一版 CSDN 的。

或者直接把 Markdown / docx / PDF 丢进来。完整流程见 `SKILL.md`，最短路径：

```powershell
# 1) 公众号版（由 Agent 按组件库装配）
# 2) 校验
python scripts/validate_gzh_html.py article_排版_摸鱼绿(moyu-green).html
# 3) 有本地图 → 内嵌
python scripts/upload_images.py article_排版_摸鱼绿(moyu-green).html
# 4) 公众号预览（右上角「复制到公众号」）
python scripts/wrap_preview.py article_排版_摸鱼绿(moyu-green)_online.html
# 5) CSDN 翻译 + 校验 + 预览
python scripts/translate_gzh_to_csdn.py article_排版_摸鱼绿(moyu-green)_online.html
python scripts/validate_csdn_html.py article_排版_摸鱼绿(moyu-green)_online_CSDN.html
python scripts/wrap_csdn_preview.py article_排版_摸鱼绿(moyu-green)_online_CSDN.html
```

母版已就绪时，第 2–5 步可合并成一条：

```powershell
python scripts/build_both.py article_排版_摸鱼绿(moyu-green).html
```

## 目录

```
SKILL.md                      主流程（Agent 读这个）
references/
  theme-moyu-green.md         摸鱼绿组件库（视觉唯一来源）
  common-components.md        通用增量组件（代码块/图片/标签）
  theme-index.md              主题索引
  format-normalize.md         docx/PDF/纯文本 → Markdown
  csdn-compat.md              CSDN 富文本兼容白名单
  translate-rules.md          gzh → CSDN 逐标签翻译表
  csdn-manual-fixes.md        翻译后 9 项固定手改
scripts/
  validate_gzh_html.py        公众号合规校验
  upload_images.py            本地图 → base64/图床
  wrap_preview.py             公众号预览页
  translate_gzh_to_csdn.py    公众号 HTML → CSDN HTML
  validate_csdn_html.py       CSDN 合规校验
  wrap_csdn_preview.py        CSDN 预览页
  extract_images.py           base64 抽图（兜底）
  extract_docx.py             docx 取文
  build_both.py               一键跑完机械步骤
assets/
  preview-template.html       公众号预览外壳
  preview-template-csdn.html  CSDN 预览外壳
  sample-article.md           回归样例
```

## 产物命名

| 产物 | 文件名 |
|------|--------|
| 公众号正文 | `{原名}_排版_摸鱼绿(moyu-green).html` |
| 公众号内嵌图版 | `{原名}_排版_摸鱼绿(moyu-green)_online.html` |
| 公众号预览 | `..._online_预览.html` / `..._预览.html` |
| CSDN 正文 | `..._CSDN.html`（含图时为 `..._online_CSDN.html`） |
| CSDN 预览 | `..._CSDN_预览.html` |

## 许可与致谢

公众号排版体系源自 [gzh-design-skill](https://github.com/isjiamu/gzh-design-skill)（甲木 × 摸鱼小李），AGPL-3.0。本仓库是衍生作品，同样以 AGPL-3.0 发布，保留原 `LICENSE`；改动说明见 `NOTICE.md`。
