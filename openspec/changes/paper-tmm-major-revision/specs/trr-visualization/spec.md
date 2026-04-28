## ADDED Requirements

### 需求:必须生成 TRR embedding 的 t-SNE/UMAP 可视化图

系统必须生成 TRR embedding 和 Wav2Vec2 mean-pooled embedding 的 t-SNE 或 UMAP 对比可视化图，按效果类型（style）着色。

#### 场景:t-SNE 对比图生成
- **当** 运行可视化脚本
- **那么** 脚本必须：(1) 从 Protocol-A 的 KB 数据提取 TRR embedding (4096-dim) 和 Wav2Vec2 mean-pooled (768-dim)；(2) 分别运行 t-SNE 降至 2D；(3) 按 Style 字段着色绘制散点图；(4) 生成并排对比图保存为 `Paper/figures/trr_vs_wav2vec_tsne.pdf`

### 需求:必须生成 Gram matrix 热力图示例

系统必须为至少两个代表性查询（一个 texture-dominant 如 tremolo，一个 transient-dominant 如 clean）生成 64×64 Gram matrix 热力图。

#### 场景:Gram 热力图生成
- **当** 运行 Gram 可视化脚本
- **那么** 脚本必须：(1) 选择两个代表性查询；(2) 计算各自的 averaged Gram matrix $\bar{G}$；(3) 绘制 64×64 热力图（使用 diverging colormap）；(4) 保存为 `Paper/figures/gram_matrix_examples.pdf`

### 需求:论文必须包含嵌入可视化图

论文 Sec 4 或 Sec 5 必须引用 t-SNE 对比图和 Gram 热力图。

#### 场景:可视化图引用
- **当** 读者阅读 TRR 结果或讨论
- **那么** 必须看到 Figure 引用指向 t-SNE 对比图和 Gram 热力图，附带简要解读
