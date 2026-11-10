# 主题索引

本 skill 目前只固化了一套主题：**摸鱼绿**。公众号版与 CSDN 版共用同一套配色和强调体系，保证两个平台读起来是同一篇文章。

| 主题 | 主色 | 适用场景 | 组件库文件 | 正文下划线 CSS |
|------|------|---------|-----------|---------------|
| 摸鱼绿 | `#059669` emerald | 教程、测评、清单、工具盘点、知识整理、方法论拆解（卡片丰富、信息密度高） | `references/theme-moyu-green.md` | `border-bottom:2px solid #A7F3D0;font-weight:600;` |

- **英文标识**：`moyu-green`，用于产物命名 `{原文件名}_排版_摸鱼绿(moyu-green).html`。
- **默认主题**：本 skill 只产出摸鱼绿，不需要选主题；用户明确要别的风格时，按 SKILL.md「扩展新主题」办理。
- **下划线权威来源**：正文关键词下划线一律用上表的值，组件库里的浅色变体只作可选样式。

## 扩展新主题

1. 参照 `theme-moyu-green.md` 的五段结构写 `references/theme-{英文标识}.md`：设计变量、组件 HTML、完整骨架、文章类型配方、Markdown 映射。
2. 在上表登记一行。
3. 跑 `python scripts/component_lint.py .`（该脚本在完整版 gzh-design 中提供，本仓库未内置）或用 `validate_gzh_html.py` 抽查组件，确认 0 ERROR。
4. CSDN 翻译器与主题无关，新主题可直接复用；只需确认配色不触发 CSDN 的「深底白字」红线（见 `references/csdn-compat.md`）。
