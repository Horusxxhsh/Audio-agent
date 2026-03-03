# Proposal: Fix Data Consistency Issues

## Why

TMM Major Review 指出了多个数据一致性和可审计性问题，这些问题的存在不一定是由于方法本身的问题，而是由于：
1. 多个数据源（JSON、CSV、手工表格）之间存在数值不一致
2. 同一实验场景在不同位置报告不同的数值
3. 实验参数（如 quality_weight）导致预期行为与实际结果不符

修复这些问题对于建立论文的可信度至关重要，因为审稿人需要确认：
- 报告的结果可以被复现
- 不同位置的数值保持一致
- 实验方法描述与实际实现相符

## 变更内容

### 主要修复

1. **Noisy Audio 场景数值统一** (Critical #2)
   - 修复 `1.4964` vs `1.5180` 的数值不一致
   - 确保 content.tex 和 supplementary.tex 中同一场景使用相同数值
   - 统一使用 `1.4964`（与 supplementary Table S9 一致）

2. **β 敏感性分析更新** (Critical #3)
   - 当前表格显示所有 β 值产生相同结果（0.3056）
   - 更新正文叙述以反映实际情况：当 `quality_weight=1.0` 时，质量得分占主导，β 对熵的影响被掩盖
   - 或者：降低 `quality_weight` 展示真实的 β 敏感性

3. **动态权重表验证** (High #4)
   - 验证 conflict 场景的权重计算
   - 确保 `w_text` 值与实际计算结果一致

4. **指标数量修正** (Low #11)
   - 正文写 "five metrics" 但实际定义 4 个
   - 更正为 "four metrics"

### 次要修复

5. **Layer Sweep 数据泄漏说明** (Critical #1)
   - 添加说明：layer sweep 在 Protocol-A 上进行
   - 如果 ℓ=10 用于主结果，需确认不存在数据泄漏

6. **协议命名统一** (Medium #8)
   - 统一使用 Protocol-A/Protocol-C
   - 移除 A′ 等不一致命名

## 功能 (Capabilities)

### 新增功能
无新增功能 - 这是现有论文的修复工作

### 修改功能
- **paper-ieee-template**: 更新主论文数据一致性
- **trr-analysis-section**: 更新 TRR 实验结果描述
- **fusion-analysis-section**: 更新 Fusion 实验结果和 β 敏感性分析
- **mushra-subsection**: 更新听测方法描述一致性

## 影响

- **Paper/main.tex**: 修复数据不一致问题
- **Paper/supplementary.tex**: 修复数据不一致问题
- **Experiments/AblationStudies/**: 可能需要重新生成实验报告
- **Experiments/AblationStudies/protocolC_objective_stats.json**: 可能需要更新 stress scenarios 数据

## 成功标准

1. [ ] Noisy Audio 场景在论文中所有位置使用相同数值 (1.4964)
2. [ ] β 敏感性叙述与表格数据一致
3. [ ] 动态权重表与复算值一致
4. [ ] 指标数量描述正确 (four metrics)
5. [ ] 协议命名统一 (Protocol-A/Protocol-C)
6. [ ] 论文编译成功，无 undefined references
