import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# 1) 读取数据
DF_PATH = "mushra.csv"
CONFIG_PATH = "default.yaml"
REPORT_PATH = "results_report.md"

df = pd.read_csv(DF_PATH)

# 2) 清洗（保留 reference / anchor）
df["rating_score"] = pd.to_numeric(df["rating_score"], errors="coerce")
# 移除可能混入的表头行（例如 email 列出现字符串 "email"）
df = df[df["email"].astype(str).str.lower() != "email"]

# 3) 定义三组实验
groups = {
    "Trial 1": ["trial1"],
    "Trial 2-5": ["trial2", "trial3", "trial4", "trial5"],
    "Trial 6-10": ["trial6", "trial7", "trial8", "trial9", "trial10"],
}

# 4) 从 default.yaml 提取实验介绍（优先英文，去掉括号内中文）
def _extract_content(text: str, trial_id: str) -> str:
    lines = text.splitlines()
    in_trial = False
    for line in lines:
        s = line.strip()
        if s.startswith("id:") and s.endswith(trial_id):
            in_trial = True
            continue
        if in_trial and s.startswith("content:"):
            content = s[len("content:"):].strip()
            # 只保留括号前的英文说明
            if "(" in content:
                content = content.split("(", 1)[0].strip()
            return content
        # 离开当前 trial 块
        if in_trial and s.startswith("- type:"):
            in_trial = False
    return ""

def _summarize_desc(desc: str) -> str:
    d = (desc or "").lower()
    if "style description" in d:
        return "评估处理后音频与给定风格描述的匹配度，关注风格准确性与音频完整性（无明显伪影）。"
    if "training" in d and "basic audio quality" in d:
        return "界面训练与主观评分示例，评估各条件的基础音频质量（BAQ）。"
    if "reference audio clip" in d or "similarity to reference" in d:
        return "根据参考音频评估生成音频在风格、音色与音乐内容上的相似度。"
    return desc.strip()

try:
    with open(CONFIG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        config_text = f.read()
except FileNotFoundError:
    config_text = ""

trial_descriptions = {
    "Trial 1": "任务概述：在本次测试中，您需要评价经由 AI 效果器处理后的音频，在多大程度上准确还原了给定的“风格描述词”（例如：“温暖复古”、“激进金属”或“明亮现代”）。评价准则：请针对每个测试条件，根据以下两个维度对音色匹配度进行评分：1.风格准确性： 处理后的音色是否真实、贴切地体现了描述词的特征？2.音频完整性： 在音色改变的同时，输出音频是否包含不必要的数字伪影（如：异常杂音、不自然的断音或失真）？评分说明：请通过滑块进行评分。高分代表 AI 成功捕捉并呈现了该风格的精髓；低分则代表音色不匹配或处理质量较差。",
    "Trial 2-5": "对比一些热门吉他solo，评判参考音频与各测试项之间检测到的所有差异。",
    "Trial 6-10": "在本次测试中，您将听到一段参考音频（Reference）及其对应的文字描述。随后，您将听到由不同 AI 模型生成的测试样本。您的任务是评价这些生成样本在风格、音色及音乐内容上与参考音频的相似程度。评价准则：请根据“与参考音的相似度”调节滑块：高分 (80-100): 生成的音频在风格和质量上与参考音几乎一致。中分 (40-70): 捕捉到了大致的氛围，但在音色或音乐表现力上有明显差异。低分 (0-30): 无法匹配参考音，或者包含严重的杂音/失真。",
}

# 5) 生成报告
lines = []
lines.append("# MUSHRA 实验结果总结")
lines.append("")
lines.append("本报告将 Trial 分为三组分别统计：")
lines.append("- Trial 1")
lines.append("- Trial 2-5")
lines.append("- Trial 6-10")
lines.append("")

for group_name, trial_list in groups.items():
    df_g = df[df["trial_id"].isin(trial_list)].copy()

    # 基本统计
    n_rows = len(df_g)
    n_participants = df_g["email"].nunique()
    n_systems = df_g["rating_stimulus"].nunique()
    n_trials = df_g["trial_id"].nunique()
    score_desc = df_g["rating_score"].describe()

    # 被试-系统-试次 -> 均值，再到系统级分布
    df_sub = (
        df_g.groupby(["email", "rating_stimulus", "trial_id"], as_index=False)["rating_score"]
        .mean()
    )
    df_sys = (
        df_sub.groupby(["email", "rating_stimulus"], as_index=False)["rating_score"]
        .mean()
    )

    # 系统级箱线图
    order = (
        df_sys.groupby("rating_stimulus")["rating_score"]
        .median()
        .sort_values(ascending=False)
        .index
    )

    plot_path = f"system_boxplot_{group_name.replace(' ', '_').replace('-', '_')}.png"

    plt.figure(figsize=(10, 5))
    sns.boxplot(data=df_sys, x="rating_stimulus", y="rating_score", order=order)
    sns.stripplot(
        data=df_sys,
        x="rating_stimulus",
        y="rating_score",
        order=order,
        color="black",
        size=3,
        alpha=0.4,
    )
    plt.xticks(rotation=30, ha="right")
    plt.title(f"System-Level MUSHRA Boxplot ({group_name})")
    plt.tight_layout()
    plt.ylim(df_sys["rating_score"].min(), df_sys["rating_score"].max())
    plt.savefig(plot_path, dpi=200)
    plt.close()

    # 系统级统计
    system_stats = (
        df_sys.groupby("rating_stimulus")["rating_score"]
        .agg(["count", "mean", "median", "std"])
        .sort_values("median", ascending=False)
    )

    # 写入报告
    lines.append(f"## {group_name}")
    lines.append("")
    desc = trial_descriptions.get(group_name, "").strip()
    if desc:
        lines.append("### 实验介绍")
        lines.append(desc)
        lines.append("")

    lines.append("### 实验数据概况")
    lines.append(f"- 样本行数: {n_rows}")
    lines.append(f"- 被试人数: {n_participants}")
    lines.append(f"- 系统数量: {n_systems}")
    lines.append(f"- 试次数量: {n_trials}")
    lines.append("")

    lines.append("### 评分总体统计")
    lines.append(f"- 均值: {score_desc['mean']:.2f}")
    lines.append(f"- 中位数: {score_desc['50%']:.2f}")
    lines.append(f"- 标准差: {score_desc['std']:.2f}")
    lines.append(f"- 最小值: {score_desc['min']:.2f}")
    lines.append(f"- 最大值: {score_desc['max']:.2f}")
    lines.append("")

    lines.append("### 系统级箱线图")
    lines.append(f"![]({plot_path})")
    lines.append("")

    lines.append("### 系统级统计（基于被试内均值）")
    lines.append("")
    lines.append(system_stats.to_string())
    lines.append("")

with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
    f.write("\n".join(lines))

print(f"Report written to {REPORT_PATH}")
