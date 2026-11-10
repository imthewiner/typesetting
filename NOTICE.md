# NOTICE

本仓库为衍生作品，合并自两套本机 skill：

1. **gzh-design / gzh-design-skill** — 微信公众号排版引擎
   - 上游：https://github.com/isjiamu/gzh-design-skill
   - 作者：甲木（Jiamu）× 摸鱼小李（Moyu Xiaoli）
   - 许可：GNU Affero General Public License v3.0（见 `LICENSE`，原样保留）
   - 本仓库沿用其：`theme-moyu-green.md`、`common-components.md`、`format-normalize.md`、`theme-index.md`（收敛为单主题）、`validate_gzh_html.py`、`upload_images.py`、`wrap_preview.py`、`extract_docx.py`、`assets/preview-template.html`、`assets/sample-article.md`，以及 SKILL.md 中的公众号排版流程。

2. **csdn-design** — 公众号 HTML → CSDN 富文本翻译
   - 作者：本机自有 skill（无独立上游仓库）
   - 本仓库沿用其：`translate_gzh_to_csdn.py`、`validate_csdn_html.py`、`wrap_csdn_preview.py`、`extract_images.py`、`csdn-compat.md`、`translate-rules.md`、`assets/preview-template-csdn.html`。

## 本仓库做了什么改动

- 把两套 skill 合并成单一入口 `typesetting`：公众号版为母版，CSDN 版由母版翻译，不再要求用户装两个 skill。
- 主题收敛为「摸鱼绿」一套，删去其余内置主题与自定义主题生成器，降低维护面。
- 新增 `scripts/build_both.py`：校验 → 内嵌图 → 双预览 → 翻译 → 再校验，一条命令跑完机械步骤。
- 新增 `references/csdn-manual-fixes.md`：把翻译后反复出现的 9 处手改固化下来。
- 统一作者署名为「百年江湖 随意沉浮」，并保留工具清单说明段的固定话术。
- 修正上游文档里「CSDN 拒收 base64」的旧结论：实测从 `_online.html`（base64 内嵌版）翻译后粘贴 CSDN 可正常转存，`extract_images.py` 降级为兜底方案。

## 许可

依据 AGPL-3.0，本仓库以相同许可发布，完整许可文本见 `LICENSE`。分发或修改时请保留本 NOTICE 与原作者署名。
