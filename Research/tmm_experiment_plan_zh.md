# TMM 实验计划（算法主线）：TRR + Fusion + Constraint Repair（合成扩容版）

## 0. 元信息
- 目标期刊：IEEE Transactions on Multimedia (TMM)
- 论文定位：算法为主（表示学习/检索 + 融合 + 约束修复），系统作为应用场景
- 当前问题：现有结果多为 pilot 规模（例如 `retrieval_comparison_report.md:1` 的 N=5），证据强度不足以支撑 TMM 级别结论
- 数据扩容策略：合成扩容（从现有 preset 参数分布采样生成新 preset，并离线渲染生成目标音频）

## 1. AE 主要关切点 -> 研究需求与验收标准
- R1 规模（Scale）：主实验测试集 `>=200`，并用学习曲线证明结论不依赖小样本偶然性
- R2 听感链路（Perceptual Link）：证明“参数空间指标”与“音频质量/听感”之间的相关性与失效边界
- R3 强 baseline：与现代强音频表示（CLAP/PaSST/AST/HuBERT/Wav2Vec2 pooling 等）公平对比
- R4 效率/延迟：报告 p50/p95 延迟、吞吐、内存；给出性能-延迟 Pareto
- R5 融合可信度：做 per-query 分布、sanity checks、泄露排查，排除 bug/数据泄露/离群点驱动的“异常巨增益”
- R6 主观实验严谨：MUSHRA/ABX 分开；预注册分析计划；多重比较校正；效应量+置信区间
- R7 可复现闭环：固定 splits/seeds，统一产物目录与 manifest（sha256），Claim->Evidence 台账

## 2. 研究问题（RQs）与假设（Hs）
- RQ1：TRR 是否在 `>=200` 规模下，稳定优于强 embedding baseline，尤其在 texture-sensitive 场景？
- RQ2：不确定性感知融合是否带来一致、可解释的收益（不是少量样本/离群点）？
- RQ3：参数指标改善是否能带来音频空间指标（FAD 等）与主观评分的改善？何时不成立？
- RQ4：TRR/Fusion/Repair 的延迟开销是多少？是否满足 DAW 场景的可用性约束？

## 3. 我们已有的资产（现状与风险）
- 数据库：`music_info.db:1` 与 `audio_info.db:1` 各 50 条，可作为“参数分布先验”，但不足以做 TMM 主结论
- 合成音频目录：`Data/Audio_Synthetic:1` 约 50 条 wav（Tier S）
- MUSHRA：`Experiments/mushura/mushra.csv:1` 存在重复表头行，需要先清洗再做统计
- 现有实验脚本：`Experiments/TextureResonance/*`、`Experiments/Fusion/*`、`Experiments/AblationStudies/*`
- 离线渲染链路：插件可监听 `~/Documents/Supertonal/Audio-agent/` 的 `import_params.json` 与 `generated_input.wav`，输出 `final_output.wav`

## 4. 数据计划（合成扩容）

### 4.1 目标数据结构（每条样本）
- `SongName`：唯一 ID
- `Parameters`：嵌套 JSON（模块 On/Off + 各参数值）
- `AudioPath`：渲染得到的目标音频路径
- `Style`：标签（至少包含 synthetic 标记 + 模块组合标签）
- `Feature`：一句话描述（用于文本检索 baseline）
- `Meta`：父 preset、生成 seed、数据集版本等

### 4.2 Tier 规模（用于学习曲线）
- Tier S（现有）：N=50
- Tier M（TMM 最低）：N>=200（建议生成 220 以便去重/筛除后仍 >=200）
- Tier L（更强证据）：N>=500（视时间/算力/稳定性决定）

### 4.3 合成与渲染策略（E0 核心）
- 参数采样：从 50 条 base preset 统计参数范围与方差，对数值做高斯扰动并 clamp 到统计范围
- 模块开关：小概率翻转 On/Off，同时保证至少一个可听模块开启（EQ/Chorus/Flanger/Phaser/Reverb）
- 离线渲染：通过插件 Auto Import 机制渲染（写 `import_params.json`，触发 `generated_input.wav`，等待 `final_output.wav`）
- 当前 renderer 约束：插件 offline 渲染会跳过/规避部分模块（例如 Delay/Driver/Screamer 等），合成阶段默认将这些模块强制 Off，以保证“参数->音频”一致

### 4.4 切分与泄露控制（必须）
- 固定 splits：输出 `train/val/test` 列表文件，并用 2-3 个 seeds 重复
- 先去重再切分：做精确重复（sha256）+ 近重复（指纹/embedding），避免“训练-测试泄露”

## 5. 评测轨道（拆分证据来源，避免混杂）
- Track A（Retrieval-only）：只评估表示/检索/融合，不引入 LLM 与 repair 的影响
- Track B（End-to-end）：评估完整 pipeline，并控制变量做消融（no-LLM/no-repair 等）

## 6. Baseline 与公平协议（必须写进论文/补充材料）
- 强音频表示 baseline（至少 5 个）：CLAP、AST、PaSST、HuBERT pooling、Wav2Vec2 pooling
- 文本 baseline：BM25/关键词重叠（当前 RAGRetriever 的简化文本检索），可选句向量检索
- 融合 baseline：固定权重 0/0.5/1.0、随机权重、温度/β 扫描、简单 learned gating（只用 train split 训练）
- 公平协议：同一数据、同一预处理、同一 split、同一预算约束，所有配置与版本可追溯

## 7. 指标体系（参数空间为 proxy，必须补音频空间与主观）

### 7.1 参数空间指标（保留，但降格为代理指标）
- L2（归一化参数向量距离）
- Acc@0.1
- Recall（active-parameter recall）
- Cosine similarity
- Module consistency（Jaccard）
- Constraint violation rate（修复前/后）

### 7.2 音频空间客观指标（TMM 必做）
- FAD（锁定一个实现与配置；写清模型/采样率/窗口等）
- 多分辨率 STFT 距离（作为补充）
- 响度一致性（LUFS/true peak）作为公平性控制

### 7.3 参数指标 vs 听感链路（核心逻辑补洞）
- Spearman 相关 + 置信区间（按 excerpt 或 listener 分簇 bootstrap）
- 混合效应模型：`score ~ metric + (1|listener) + (1|excerpt)`
- 留一 excerpt 验证相关性是否泛化

### 7.4 Identifiability 压力测试（直接回应“参数不唯一”）
- 构造同一目标音频对应的多组参数候选（不同邻居/扰动/替代参数集）
- 渲染音频并测音频距离与主观混淆（必要时 ABX）
- 输出“参数差很大但声音很像”的失败案例族谱，明确参数指标的边界

## 8. 主观实验（MUSHRA/ABX 分离，预注册）
- S1（MUSHRA）：单一明确端点（例如“与参考音频相似度”或“整体音质”二选一），每页含 hidden reference + anchor
- S2（ABX，可选）：可辨别性（二选一），用于解释“参数不同但音频相似”的情形
- QC 门槛：hidden ref 中位数 >=90，anchor 中位数 <=30；失败者按预注册规则剔除
- 统计：LMM/GLMM，primary 家族用 Holm，exploratory 用 BH-FDR；报告效应量+95%CI

## 9. 实验清单（E0/E1 先落地）

### E0 数据生成 + manifest + splits + 泄露扫描（必须先做）
- 生成与渲染（Tier M 建议 220 条）：`Experiments/tmm/synth_dataset.py:1`
- 固定切分：`Experiments/tmm/make_splits.py:1`
- 泄露/近重复扫描：`Experiments/tmm/leakage_scan.py:1`
- 产物：
  - `Experiments/dataset_full_vectors.json`
  - `Data/TMM_Synth_v1/dataset_manifest.json`
  - `Experiments/tmm/splits/<name>/seed*/{train,val,test}.txt`
  - `Experiments/tmm/leakage_report.json`
- 验收：
  - 去重/筛除后 test 仍 `>=200`
  - train/test 精确重复为 0
  - 近重复对（高相似度）可解释并可选择剔除

### E1 学习曲线（Scale -> Performance）
- Tier S/M/(L) 上重复主评测，报告曲线与 CI
- 产物：`learning_curve.csv` + 学习曲线图
- 验收：趋势合理；若出现“小数据集胜过大数据集”，必须定位原因并在日志说明

### E2 强 baseline（Track A）
- 在固定 split 上比较强 embedding baseline vs TRR
- 产物：主表（mean±CI）+ per-query 分布图
- 验收：>=5 个强 baseline，且所有配置/版本/预处理可追溯

### E3 TRR 必要性消融
- TRR on/off、投影维度、层选择等系统扫描
- 产物：消融表 + 复杂度/延迟对比
- 验收：>=2 seeds 下可复现；报告 latency trade-off

### E4 Fusion 可信度（含 sanity checks）
- 固定权重/随机权重/β 扫描/learned gate；并做 pairing 打乱、静音/白噪等 sanity
- 产物：改进分布 CDF + sanity 表
- 验收：sanity 退化到 chance；收益不是单点离群驱动（报告 median/trimmed mean）

### E5 Repair 消融（约束违例率）
- none/soft/hard repair/post-hoc 对比
- 产物：违例率前后表 + repair 统计日志
- 验收：违例率 >=10x 降低，并达到预设阈值；性能代价量化

### E6 效率/延迟基准
- CPU/MPS 下测 p50/p95、吞吐、内存峰值
- 产物：Latency CDF + Pareto
- 验收：一条脚本可复现全部数字（设备/批大小/音频长度齐全记录）

### E7 参数指标 vs 听感链路
- 相关性/回归 + failure cases
- 产物：相关表 + scatter + 失败案例列表
- 验收：正反证据都报告，不做“等价”夸张结论

### E8 主观（MUSHRA）
- 产物：EMM+CI+效应量表 + QC 总结 +（可公开的）匿名评分
- 验收：分析计划冻结在前；多重比较校正后报告

### E9 Identifiability 压力测试
- 产物：参数距离 vs 音频距离 vs 主观混淆的对照表 + curated 音频集（补充材料）
- 验收：明确参数指标能支持什么，不能支持什么

## 10. 可复现与产物归档（最小闭环）
- 数据集：manifest（sha256）+ 版本号
- splits：固定 seeds，所有实验只读 splits
- 每次运行落盘：`runs/{exp_id}/{timestamp}/`（命令、配置、git_rev、pip freeze、硬件信息、表图音频、checksums）
- Claim->Evidence：持续更新 `Research/evidence_ledger.md:1`

## 11. 推荐时间表（按优先级）
- Week 1：E0 + E1（先把规模与泄露问题完全解决）
- Week 2：E2/E3/E4（强 baseline + TRR/fusion 消融 + sanity）
- Week 3：E5/E6/E7（repair、延迟、参数-听感链路）
- Week 4：E8/E9（主观与 identifiability），同时整理论文与补充材料

## 12. TMM 投稿 Go/No-Go 标准
- test `>=200` 且 >=2 seeds；主表报告 CI + 效应量
- >=5 强 baseline；不是“弱 baseline 证明强结论”
- 至少 1 个音频空间客观指标 + 1 个主观实验（预注册、校正统计）
- 有延迟 CDF 与 Pareto；有 sanity 与泄露扫描报告
- 可复现闭环完整（manifest/splits/runs/evidence ledger）

