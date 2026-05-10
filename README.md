# 浙超联赛分组方案 — 数学建模

浙江大学第24届数学建模竞赛 B题

## 项目结构

```
├── SPEC.md                # 问题规格与方法论
├── 2026problem.pdf        # 竞赛题目
├── requirements.txt       # Python 依赖
├── src/
│   ├── data.py            # 浙江省64支队伍数据（11市+53县，含GDP/坐标）
│   ├── grouping.py        # Task 1: 分组算法（CP-SAT + 模拟退火）
│   ├── lottery.py         # Task 2: 分层抽签方案 + Monte Carlo验证
│   ├── venue.py           # Task 3: 比赛地点选择（K-means + 贪心优化）
│   ├── tournament.py      # Task 4: 赛制分析（Bradley-Terry + 蒙特卡洛）
│   ├── visualize.py       # 可视化工具
│   └── main.py            # 主程序：一键运行全部4个Task
├── output/                # 生成的输出（报告、图表、JSON）
└── paper/
    ├── main.tex           # LaTeX论文源文件
    └── main.pdf           # 编译后的PDF论文
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行全部任务
python -m src.main

# 输出到 output/ 目录
```

## 四个子任务

### Task 1: 分组方案生成
- 约束规划（CP-SAT）生成可行解
- 模拟退火优化软约束
- 输出6个全部可行的分组方案（软约束违反=0）

### Task 2: 抽签方案设计
- 分层随机抽签流程
- 蒙特卡洛模拟（10000次）验证公平性
- 卡方均匀性检验

### Task 3: 比赛地点选择
- K-means++聚类（K=8）
- 贪心优化最小化旅行距离
- 平均距离134.8km

### Task 4: 赛制建议
- Bradley-Terry实力模型
- 三种赛制对比：当前赛制、瑞士轮、双败淘汰
- 蒙特卡洛模拟夺冠概率

## 技术栈

- Python 3.14
- Google OR-Tools（约束规划求解）
- NumPy, Pandas, Matplotlib, Seaborn
- scikit-learn（聚类）
- Folium（地图可视化）
- LaTeX + ctex（论文排版）

## AI工具使用说明

本项目使用以下AI工具辅助完成：
- **Hermes Agent / Claude Code**：代码编写、算法实现、调试
- **LLM辅助**：论文写作、方案对比分析

所有AI交互记录按竞赛要求存档。
