"""
Task 2：分层抽签方案设计

流程：
1. 第一层：11个市级队随机抽签，分配到11个不同小组
2. 第二层：53个县级队分层抽签
   允许的组 = 所有组 - 该市市级队所在组 - 已被同市其他县级队占据的组
3. Monte Carlo 验证公平性
"""

import random
import numpy as np
from collections import defaultdict

from .data import (
    ALL_TEAMS, CITY_CODES, COUNTY_CODES, PARENT_MAP,
    CITY_CHILDREN, NUM_GROUPS, GROUP_SIZE, TEAM_BY_CODE,
)


def draw_municipal_order(seed: int = None) -> list[str]:
    """第一层：市级队随机抽签确定小组顺序。"""
    rng = random.Random(seed)
    order = CITY_CODES[:]
    rng.shuffle(order)
    return order


def draw_county_assignment_greedy(
    city_groups: dict[str, int],
    seed: int = None,
) -> dict[str, int]:
    """
    第二层（快速版）：县级队贪心随机分配。

    每市的县级队依次从"允许的且未满的组"中随机选取。
    允许的组 = 全部组 - 该市市级队所在组 - 已被同市其他县级队占据的组。
    """
    rng = random.Random(seed)
    county_assignment = {}

    # 容量追踪：每组已有队伍数
    group_count = defaultdict(int)
    for g in city_groups.values():
        group_count[g] += 1

    # 逐市处理（随机顺序增加多样性）
    city_order = CITY_CODES[:]
    rng.shuffle(city_order)

    for city_code in city_order:
        forbidden = {city_groups[city_code]}
        children = CITY_CHILDREN[city_code][:]
        rng.shuffle(children)

        for child_code in children:
            # 可选组：不在forbidden中且未满
            available = [g for g in range(NUM_GROUPS)
                         if g not in forbidden and group_count[g] < GROUP_SIZE]

            if available:
                chosen = rng.choice(available)
            else:
                # 所有允许组都满了，退而求其次用任意未满组
                fallback = [g for g in range(NUM_GROUPS) if group_count[g] < GROUP_SIZE]
                chosen = rng.choice(fallback) if fallback else rng.randint(0, NUM_GROUPS - 1)

            county_assignment[child_code] = chosen
            forbidden.add(chosen)
            group_count[chosen] += 1

    return county_assignment


def draw_county_assignment_csp(
    city_groups: dict[str, int],
    seed: int = None,
) -> dict[str, int]:
    """
    第二层（精确版）：用 CP-SAT 求解，保证每组恰好 4 队。
    仅用于单次演示，不适合 Monte Carlo。
    """
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    n = len(COUNTY_CODES)
    g = NUM_GROUPS

    x = {}
    for i in range(n):
        for j in range(g):
            x[i, j] = model.NewBoolVar(f"x_{i}_{j}")

    for i in range(n):
        model.Add(sum(x[i, j] for j in range(g)) == 1)

    group_base = defaultdict(int)
    for city_g in city_groups.values():
        group_base[city_g] += 1
    for j in range(g):
        model.Add(sum(x[i, j] for i in range(n)) == GROUP_SIZE - group_base[j])

    for i, county_code in enumerate(COUNTY_CODES):
        parent = PARENT_MAP[county_code]
        parent_group = city_groups[parent]
        model.Add(x[i, parent_group] == 0)

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    if seed is not None:
        solver.parameters.random_seed = seed
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("CP-SAT 无法找到可行解")

    county_assignment = {}
    for i, county_code in enumerate(COUNTY_CODES):
        for j in range(g):
            if solver.Value(x[i, j]) == 1:
                county_assignment[county_code] = j
                break

    return county_assignment


def run_lottery(seed: int = None, method: str = "greedy") -> tuple[dict, dict]:
    """
    执行一次完整抽签。
    method: "greedy"（快速）或 "csp"（精确）
    """
    city_order = draw_municipal_order(seed)
    city_groups = {}
    for i, city_code in enumerate(city_order):
        city_groups[city_code] = i % NUM_GROUPS

    if method == "csp":
        county_groups = draw_county_assignment_csp(city_groups, seed)
    else:
        county_groups = draw_county_assignment_greedy(city_groups, seed)

    return city_groups, county_groups


def lottery_to_groups(city_groups: dict, county_groups: dict) -> list[list[str]]:
    """将抽签结果转为分组列表。"""
    groups = [[] for _ in range(NUM_GROUPS)]
    for code, g in city_groups.items():
        groups[g].append(code)
    for code, g in county_groups.items():
        groups[g].append(code)
    return groups


def simulate_lottery_fairness(
    n_simulations: int = 10000,
    seed: int = 42,
) -> dict:
    """
    Monte Carlo 模拟大量抽签，统计：
    1. 各队落入各组的概率分布
    2. 软约束违反次数分布
    3. 可行解比例
    """
    from .grouping import check_hard_constraints, count_soft_violations

    rng = random.Random(seed)

    team_group_counts = defaultdict(lambda: np.zeros(NUM_GROUPS, dtype=int))
    violation_counts = []
    feasible_count = 0
    violation_dist = defaultdict(int)

    for sim in range(n_simulations):
        sim_seed = rng.randint(0, 2**31)
        city_groups, county_groups = run_lottery(seed=sim_seed, method="greedy")
        groups = lottery_to_groups(city_groups, county_groups)

        for g_idx, g in enumerate(groups):
            for code in g:
                team_group_counts[code][g_idx] += 1

        ok, _ = check_hard_constraints(groups)
        if ok:
            feasible_count += 1

        v = count_soft_violations(groups)
        violation_counts.append(v["total_violations"])
        violation_dist[v["total_violations"]] += 1

    n_actual = len(violation_counts)
    uniformity = {}
    for code in team_group_counts:
        counts = team_group_counts[code]
        total = counts.sum()
        if total == 0:
            continue
        expected = total / NUM_GROUPS
        chi_sq = float(np.sum((counts - expected) ** 2 / max(expected, 1)))
        uniformity[code] = {
            "chi_sq": chi_sq,
            "max_deviation": float(np.max(np.abs(counts - expected))),
            "probs": (counts / total).tolist(),
        }

    return {
        "n_simulations": n_actual,
        "feasible_rate": feasible_count / max(n_actual, 1),
        "violation_mean": float(np.mean(violation_counts)) if violation_counts else 0,
        "violation_std": float(np.std(violation_counts)) if violation_counts else 0,
        "violation_distribution": dict(violation_dist),
        "uniformity": uniformity,
        "team_group_counts": {k: v.tolist() for k, v in team_group_counts.items()},
    }


def format_lottery_result(city_groups: dict, county_groups: dict) -> str:
    """格式化抽签结果为文本。"""
    groups = [[] for _ in range(NUM_GROUPS)]
    for code, g in city_groups.items():
        groups[g].append(code)
    for code, g in county_groups.items():
        groups[g].append(code)

    lines = ["抽签结果：", "-" * 50]
    for i, g in enumerate(groups):
        names = [TEAM_BY_CODE[c]["name"] for c in g]
        lines.append(f"  组{i+1:2d}: {', '.join(names)}")
    return "\n".join(lines)
