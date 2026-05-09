"""
浙超分组方案 — 主程序

运行全部四个任务，输出结果到 output/ 目录。
"""

import os
import sys
import json
import time

# 确保可以 import 本项目
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data import ALL_TEAMS, TEAM_BY_CODE, CITY_CODES, NUM_GROUPS
from src.grouping import (
    generate_solutions, format_solution_table, evaluate_groups,
    simulated_annealing, generate_greedy_random,
)
from src.lottery import (
    run_lottery, lottery_to_groups, simulate_lottery_fairness,
    format_lottery_result,
)
from src.venue import (
    generate_venue_plan, format_venue_plan, optimize_venue_assignment,
    evaluate_venue_plan,
)
from src.tournament import (
    monte_carlo_comparison, analyze_competitiveness,
    build_strength_model, format_tournament_comparison,
)
from src.visualize import (
    plot_group_heatmap, plot_gdp_balance, plot_soft_violations,
    plot_venue_map, plot_lottery_fairness, plot_tournament_probs,
    plot_distance_distribution, plot_radar_comparison,
)


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_task1():
    """Task 1: 生成分组方案"""
    print("=" * 60)
    print("Task 1: 生成分组方案")
    print("=" * 60)

    solutions = generate_solutions(n=6, method="mixed", seed=42)

    # 对每个方案做SA优化
    for sol in solutions:
        if sol["eval"]["soft_violations"] > 0:
            print(f"  方案{sol['id']} 软约束违反={sol['eval']['soft_violations']}，尝试SA优化...")
            optimized, sa_info = simulated_annealing(
                sol["groups"], max_iter=30000, seed=42 + sol["id"]
            )
            opt_eval = evaluate_groups(optimized)
            if opt_eval["soft_violations"] < sol["eval"]["soft_violations"]:
                sol["groups"] = optimized
                sol["eval"] = opt_eval
                sol["method"] += "+SA"
                print(f"    → 优化后违反={opt_eval['soft_violations']}")

    # 输出
    report_lines = ["Task 1: 分组方案", "=" * 60, ""]
    for sol in solutions:
        report_lines.append(format_solution_table(sol))
        report_lines.append("")

    report_path = os.path.join(OUTPUT_DIR, "task1_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"  报告已保存: {report_path}")

    # 可视化
    plot_gdp_balance(solutions, save_path=os.path.join(OUTPUT_DIR, "task1_gdp_balance.png"))
    plot_soft_violations(solutions, save_path=os.path.join(OUTPUT_DIR, "task1_soft_violations.png"))
    plot_radar_comparison(solutions, save_path=os.path.join(OUTPUT_DIR, "task1_radar.png"))

    # 选最优方案做热力图
    best = min(solutions, key=lambda s: s["eval"]["soft_violations"])
    plot_group_heatmap(
        best["groups"],
        save_path=os.path.join(OUTPUT_DIR, "task1_best_heatmap.png"),
        title=f"最优方案{best['id']}分组热力图",
    )

    print(f"  最优方案: 方案{best['id']}  软约束违反={best['eval']['soft_violations']}")
    return solutions


def run_task2(groups):
    """Task 2: 抽签方案"""
    print("\n" + "=" * 60)
    print("Task 2: 抽签方案设计")
    print("=" * 60)

    # 单次抽签演示
    city_groups, county_groups = run_lottery(seed=123)
    print(format_lottery_result(city_groups, county_groups))

    # Monte Carlo 验证
    print("\n  运行500次Monte Carlo模拟...")
    fairness = simulate_lottery_fairness(n_simulations=500, seed=42)

    report_lines = [
        "Task 2: 抽签方案分析",
        "=" * 60,
        "",
        "1. 抽签流程设计",
        "-" * 40,
        "第一层：11个市级队随机抽签，分配到11个不同小组。",
        "第二层：每市县级队依次抽签，从允许的组中随机选取。",
        "允许的组 = 全部组 - 该市市级队所在组 - 已被同市其他县级队占据的组",
        "",
        "2. 公平性验证 (Monte Carlo, N=10000)",
        "-" * 40,
        f"  可行解比例: {fairness['feasible_rate']:.4f}",
        f"  平均软约束违反: {fairness['violation_mean']:.2f} ± {fairness['violation_std']:.2f}",
        "",
        "3. 违反次数分布:",
    ]
    for k in sorted(fairness["violation_distribution"].keys()):
        cnt = fairness["violation_distribution"][k]
        report_lines.append(f"  {k}次违反: {cnt}次 ({cnt/10000*100:.1f}%)")

    report_path = os.path.join(OUTPUT_DIR, "task2_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))

    plot_lottery_fairness(fairness, save_path=os.path.join(OUTPUT_DIR, "task2_fairness.png"))
    print(f"  报告已保存: {report_path}")
    return fairness


def run_task3(groups):
    """Task 3: 比赛地点选择"""
    print("\n" + "=" * 60)
    print("Task 3: 比赛地点选择")
    print("=" * 60)

    venue_plan = generate_venue_plan(groups, method="greedy", seed=42)
    print(format_venue_plan(groups, venue_plan))

    report_lines = [
        "Task 3: 比赛地点选择",
        "=" * 60,
        "",
        format_venue_plan(groups, venue_plan),
    ]

    report_path = os.path.join(OUTPUT_DIR, "task3_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))

    plot_venue_map(
        groups, venue_plan["venue_map"],
        save_path=os.path.join(OUTPUT_DIR, "task3_venue_map.html"),
    )
    plot_distance_distribution(
        venue_plan["eval"],
        save_path=os.path.join(OUTPUT_DIR, "task3_distance.png"),
    )
    print(f"  报告已保存: {report_path}")
    return venue_plan


def run_task4(groups):
    """Task 4: 赛制分析"""
    print("\n" + "=" * 60)
    print("Task 4: 赛制建议与分析")
    print("=" * 60)

    print("  运行500次Monte Carlo模拟...")
    probs, strength = monte_carlo_comparison(groups, n_simulations=500, seed=42)

    print("  分析竞技水平展示度...")
    competitiveness = analyze_competitiveness(groups, strength, n_simulations=200, seed=42)

    comparison_text = format_tournament_comparison(probs, strength)
    print(comparison_text)

    report_lines = [
        "Task 4: 赛制建议与分析",
        "=" * 60,
        "",
        comparison_text,
        "",
        "竞技水平展示度分析",
        "-" * 40,
        f"  弱队平均出线率: {competitiveness['avg_qualify_rate']:.4f}",
    ]

    report_path = os.path.join(OUTPUT_DIR, "task4_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))

    plot_tournament_probs(probs, strength, save_path=os.path.join(OUTPUT_DIR, "task4_probs.png"))
    print(f"  报告已保存: {report_path}")


def main():
    ensure_output_dir()
    t0 = time.time()

    # Task 1
    solutions = run_task1()
    best = min(solutions, key=lambda s: s["eval"]["soft_violations"])
    best_groups = best["groups"]

    # Task 2
    run_task2(best_groups)

    # Task 3
    run_task3(best_groups)

    # Task 4
    run_task4(best_groups)

    # 保存最优方案为JSON
    best_json = {
        "id": best["id"],
        "method": best["method"],
        "eval": best["eval"],
        "groups": [
            [{"code": c, "name": TEAM_BY_CODE[c]["name"], "gdp": TEAM_BY_CODE[c]["gdp"]}
             for c in g]
            for g in best["groups"]
        ],
    }
    json_path = os.path.join(OUTPUT_DIR, "best_solution.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(best_json, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print(f"\n全部完成! 用时: {elapsed:.1f}s")
    print(f"输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
