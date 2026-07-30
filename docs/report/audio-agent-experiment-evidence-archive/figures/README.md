# Figures

- 这套 report family 默认追求图文并茂；架构、流程、协议、机制、实验等高密度内容应优先配图。
- 最终成稿优先使用 TikZ / PGFPlots，使图形保持矢量、可编辑、与正文字体一致。
- Mermaid 适合作为 brainstorming 或快速草图；若要进入最终 PDF，通常应转成 TikZ 定稿图。
- 一张图只回答一个核心问题；如果图已经承载多个主结论，应拆成总览图 + 细节图。
- 图前写用途，图后写结论；表格优先压缩定义、对比、证据与检查清单。
- 每次调整图表后，都应重新查看 `build/compile-review.md` 与 `build/self-check.md`。
