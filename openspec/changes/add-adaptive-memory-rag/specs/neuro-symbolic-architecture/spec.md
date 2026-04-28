## 修改需求

### 需求:系统架构设计
**修改说明**：显式增加记忆反馈回路。

系统的逻辑架构图（Figure 1）必须包含从“Parameter Selection”到“Retrieval Module”的反馈路径，标记为 "Feedback / Memory Storage"。

#### 场景:可视化闭环
- **当** 更新 `Paper/content.tex` 中的 TikZ 绘图代码时
- **那么** 系统必须通过虚线或箭头展示参数如何被回存到记忆缓冲区中
