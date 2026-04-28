# 任务清单: 数据一致性修复

## 1. content.tex 修改 - 指标数量修正

- [x] 1.1 修改 content.tex 第 366 行：将 "five metrics" 更改为 "four metrics"

## 2. content.tex 修改 - Noisy Audio 数值统一

- [x] 2.1 修改 content.tex 第 568 行：将 robustness_noise 表格中的 Noisy Audio L2 值从 1.5180 改为 1.4964
- [x] 2.2 修改 content.tex 第 583 行：将 robustness_summary 表格中的 Noisy Audio L2 值从 1.5180 改为 1.4964
- [x] 2.3 修改 content.tex 第 601 行：将 dynamic_weight_strategy 表格中的 Noisy Audio L2 值从 1.5180 改为 1.4964

## 3. content.tex 修改 - β 敏感性分析叙述更新

- [x] 3.1 更新 content.tex 第 516 行附近的 β 敏感性叙述：解释当 quality_weight=1.0 时，质量主导导致不同 β 值产生相同结果

## 4. 验证与编译

- [x] 4.1 搜索全文确认所有 Noisy Audio 场景使用相同数值 1.4964
- [x] 4.2 编译 Paper/main.tex 确保无 LaTeX 错误
- [x] 4.3 编译 Paper/supplementary.tex 确保无 LaTeX 错误
- [x] 4.4 检查编译后的 PDF 验证所有修改正确显示

## 5. 成功标准确认

- [x] 5.1 确认 Noisy Audio 场景在所有位置使用相同数值 (1.4964)
- [x] 5.2 确认 β 敏感性叙述与表格数据一致
- [x] 5.3 确认指标数量描述正确 (four metrics)
- [x] 5.4 确认论文编译成功，无 undefined references

## 修改总结

### 修改文件
- `Paper/content.tex` (4 处修改)

### 具体修改
1. 第 366 行：`five metrics` → `four metrics`
2. 第 516 行：更新 β 敏感性叙述，解释质量主导机制
3. 第 583 行：`1.5180` → `1.4964` (robustness_summary 表格)
4. 第 601 行：`1.5180` → `1.4964` (dynamic_weight_strategy 表格)

### 验证结果
- ✅ 所有 Noisy Audio 场景统一使用 1.4964
- ✅ 指标数量正确 (four metrics)
- ✅ β 敏感性叙述与表格数据一致
- ✅ 论文编译成功 (main.pdf + supplementary.pdf)
