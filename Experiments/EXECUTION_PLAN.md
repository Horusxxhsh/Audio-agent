# TMM Revision 实验执行计划 (1周紧急版)

> 配置确认: AAAAC (API预算OK / 全基线 / RTX 3090 / MUSHRA数据 / 1周紧急)
> API: DeepSeek (成本降低80%)

---

## 📅 详细时间表

### Day 1 (周一) - 环境配置
```bash
# 上午 (你执行)
pip install transformers torch torchaudio soundfile pydub scipy pandas numpy matplotlib seaborn
brew install ffmpeg  # macOS

# 验证DeepSeek API
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY"

# 验证GPU
nvidia-smi

# 下午 (我提供支持)
# 解决任何安装问题
```

### Day 2 (周二) - E2启动
```bash
# 早上 (你运行 - GPU专用给E2)
cd Experiments/E2_SOTABaselines
python run_comparison.py

# 预计运行时间: 8-12小时
# 预计算所有基线的embedding
```

### Day 3 (周三) - E1 + E2并行
```bash
# 上午 (你运行E1 - CPU)
cd Experiments/E1_AEM
python memory_learning_curve.py

# 下午 (E2应该完成)
# 检查E2结果
```

### Day 4 (周四) - 【关键决策点】
```bash
# 上午: E2结果分析
# 检查TRR vs CLAP性能

# 决策:
# IF TRR >= CLAP-10%: 继续原claim
# IF TRR < CLAP-20%: 调整claim为"轻量级专用方法"
```

### Day 5 (周五) - E3 + E5
```bash
# 上午 (GPU给E3)
cd Experiments/E3_ProtocolC
python protocol_c_experiment.py

# 下午 (E5 - CPU)
cd Experiments/E5_Ablations
python ablation_study.py
```

### Day 6 (周六) - E4 + 整合
```bash
# E4 (需要MUSHRA数据)
cd Experiments/E4_MetricCorrelation
python correlation_analysis.py \
  --mushra-data path/to/mushra.csv \
  --metrics-data path/to/metrics.csv
```

### Day 7 (周日) - 论文修订
```bash
# 整合所有结果
# 更新Response Letter
# 生成图表
```

---

## 📊 实验完成清单

| 实验 | 代码状态 | 执行时间 | 优先级 |
|------|----------|----------|--------|
| **E1** AEM学习曲线 | ✅ 完成 | 4小时 | P0 |
| **E2** SOTA基线对比 | ✅ 完成 | 12小时 | P0 (关键!) |
| **E3** 真实噪声 | ✅ 完成 | 8小时 | P0 |
| **E4** 指标相关性 | ✅ 完成 | 1小时 | P1 (简化版) |
| **E5** 消融实验 | ✅ 完成 | 2小时 | P1 (简化版) |
| **E6** 延迟分析 | ✅ 完成 | 1小时 | P2 (已跳过) |

---

## 🔥 关键风险与应对

### Risk 1: E2结果不如CLAP (概率: 30%)
**影响**: 可能需要重写Response Letter
**应对**: Day 4立即启动Plan B，调整claim

### Risk 2: CLAP安装失败 (概率: 20%)
**影响**: E2无法完成
**应对**: 使用OpenL3或AST作为替代

### Risk 3: GPU OOM (概率: 15%)
**影响**: 需要重新跑
**应对**: 减小batch_size到4或2

### Risk 4: DeepSeek API限流 (概率: 10%)
**影响**: 实验变慢
**应对**: 添加time.sleep(0.5)节流

---

## 💰 DeepSeek API成本估算

| 实验 | 调用次数 | OpenAI成本 | DeepSeek成本 |
|------|----------|------------|--------------|
| E1 | ~2500 | $20-30 | $3-5 |
| E5 | ~500 | $5-8 | $0.8-1.2 |
| **总计** | ~3000 | **$25-38** | **$4-6** |

**节省: ~$20**

---

## 📁 代码文件清单

```
Experiments/
├── README.md                          # 使用指南
├── EXECUTION_PLAN.md                  # 本文件
├── E1_AEM/
│   └── memory_learning_curve.py       # ✅ AEM学习曲线
├── E2_SOTABaselines/
│   ├── clap_encoder.py                # ✅ CLAP编码器
│   ├── passt_encoder.py               # ✅ PaSST编码器
│   ├── panns_encoder.py               # ✅ PANNs编码器
│   └── run_comparison.py              # ✅ 主对比脚本
├── E3_ProtocolC/
│   └── audio_degrader.py              # ✅ 音频退化
├── E4_MetricCorrelation/
│   └── correlation_analysis.py        # ✅ 相关性分析(简化)
├── E5_Ablations/
│   └── ablation_study.py              # ✅ 消融实验(简化)
└── E6_Latency/
    └── latency_profiler.py            # ✅ 延迟分析
```

---

## 🚀 立即开始

### Step 1: 环境检查
```bash
# 验证所有依赖
python -c "import torch; print(torch.cuda.is_available())"
python -c "import transformers; print(transformers.__version__)"
```

### Step 2: 运行E6 (最快验证)
```bash
cd Experiments/E6_Latency
python latency_profiler.py
# 应该5分钟内完成
```

### Step 3: 运行E1 (API测试)
```bash
cd Experiments/E1_AEM
export OPENAI_API_KEY="your-deepseek-key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
python memory_learning_curve.py
# 测试DeepSeek API是否正常工作
```

### Step 4: 启动E2 (GPU长时间运行)
```bash
cd Experiments/E2_SOTABaselines
python run_comparison.py
# 让它过夜运行
```

---

## 📞 支持

如果遇到问题:
1. 检查Experiments/README.md
2. 查看各目录中的代码注释
3. 联系我获取实时支持

---

**祝实验顺利！🎯**
