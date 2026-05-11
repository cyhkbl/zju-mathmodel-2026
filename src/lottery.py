"""
Task 2：抽签方案设计

方法：
- 分层随机抽签：第一层市级队，第二层县级队
- 县级队抽签时优先满足软约束（同市尽量不同组），
  当所有满足软约束的组均不可用时允许违反软约束。

修复说明：
1. 修正原论文公式"允许的组"把软约束变成硬约束的问题。
   县级队抽签时：
   - 优先从"不含同市其他县级队"的未满组中随机选；
   - 若没有此类组，则从所有符合硬约束的未满组中随机选。
   这样软约束是"尽量满足"而非"强制满足"。
"""

import random
import numpy as np
from collections import defaultdict

from .data import (
    ALL_TEAMS, CITY_CODES, COUNTY_CODES, PARENT_MAP,
    CITY_CHILDREN, NUM_GROUPS, GROUP_SIZE, TEAM_BY_CODE,
)


# -- 第一层：市级队抽签 ---------------------------------------------------------

def draw_municipal_order(seed: int = None) -> list[str]:
    """市级队随机排序，返回随机顺序的市级队列表。"""
    rng = random.Random(seed)
    order = CITY_CODES[:]
    rng.shuffle(order)
    return order


# -- 第二层：县级队抽签（优先软约束版）------------------------------------------

def draw_county_assignment_greedy(
    city_groups: dict[str, int],
    seed: int = None,
) -> dict[str, int]:
    """
    第二层（优先软约束版）：县级队贪心随机分配。

    对于每个市级队代管的县：
    - 优先选择满足以下所有条件的组：
      1. 未满（< GROUP_SIZE）
      2. 不含该市市级队（硬约束）
      3. 不含同市其他已分配的县级队（软约束优先）
    - 若没有同时满足以上条件的组，则放宽条件3，
      从仅满足条件1和2的组中随机选择（允许软约束违反）。
    """
    rng = random.Random(seed)

    county_assignment = {}
    group_count = defaultdict(int)

    # 初始化：市级队已占位
    for city_code, g_idx in city_groups.items():
        group_count[g_idx] += 1

    # 逐市分配县级队（随机顺序增加多样性）
    city_order = CITY_CODES[:]
    rng.shuffle(city_order)

    for city_code in city_order:
        city_group = city_groups[city_code]       # 该市市级队所在组（硬禁止）
        children = CITY_CHILDREN[city_code][:]
        rng.shuffle(children)

        # 记录同市已分配的县级队所在的组（用于软约束优先）
        used_by_same_city = set()

        for child_code in children:
            # ---- 第一优先级：满足硬约束 + 软约束----
            ideal_groups = []
            for g_idx in range(NUM_GROUPS):
                if (
                    g_idx != city_group                   # 硬约束：不与本市市级队同组
                    and group_count[g_idx] < GROUP_SIZE    # 未满
                    and g_idx not in used_by_same_city     # 软约束优先：不与同市其他县同组
                ):
                    ideal_groups.append(g_idx)

            if ideal_groups:
                chosen = rng.choice(ideal_groups)
            else:
                # ---- 第二优先级：放松软约束，仅满足硬约束 ----
                fallback_groups = []
                for g_idx in range(NUM_GROUPS):
                    if (
                        g_idx != city_group
                        and group_count[g_idx] < GROUP_SIZE
                    ):
                        fallback_groups.append(g_idx)

                if fallback_groups:
                    chosen = rng.choice(fallback_groups)
                else:
                    # 理论上不应发生（16组×4容量=64队，完全够放）
                    chosen = rng.randint(0, NUM_GROUPS - 1)

            county_assignment[child_code] = chosen
            group_count[chosen] += 1
            used_by_same_city.add(chosen)  # 记录该组已被本市级队的一个县占用

    return county_assignment


# -- 第二层备用：CP-SAT 精确版 --------------------------------------------------

def draw_county_assignment_csp(
    city_groups: dict[str, int],
    seed: int = None,
) -> dict[str, int]:
    """
    第二层（精确版）：用 CP-SAT 求解，确保每组恰好 4 队。
    仅用于单次精确抽签展示，不适合蒙特卡洛大规模模拟。
    """
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    n = len(COUNTY_CODES)
    g = NUM_GROUPS

    x = {}
    for i in range(n):
        for j in range(g):
            x[i, j] = model.NewBoolVar(f"x_{i}_{j}")

    # 每县恰好一队
    for i in range(n):
        model.Add(sum(x[i, j] for j in range(g)) == 1)

    # 每组最终恰好 4 队（减去已放入的市级队）
    group_base = defaultdict(int)
    for city_g in city_groups.values():
        group_base[city_g] += 1
    for j in range(g):
        model.Add(sum(x[i, j] for i in range(n)) == GROUP_SIZE - group_base[j])

    # 硬约束：市级队与该市县级队不同组
    for i, county_code in enumerate(COUNTY_CODES):
        parent = PARENT_MAP[county_code]
        parent_group = city_groups[parent]
        model.Add(x[i, parent_group] == 0)

    # 软约束：同市县级队尽量不同组（不强制）
    # 注：CP-SAT 版本不主动优化软约束，仅保证硬约束。

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


# -- 完整抽签流程 ---------------------------------------------------------------

def run_lottery(seed: int = None, method: str = "greedy") -> tuple[dict, dict]:
    """
    执行一次完整抽签。

    返回：
        city_groups: 市级队 -> 所在组编号
        county_groups: 县级队 -> 所在组编号
    """
    # 第一层：市级队抽签
    city_order = draw_municipal_order(seed)
    city_groups = {}
    for i, city_code in enumerate(city_order):
        city_groups[city_code] = i % NUM_GROUPS

    # 第二层：县级队抽签
    if method == "csp":
        county_groups = draw_county_assignment_csp(city_groups, seed)
    else:
        county_groups = draw_county_assignment_greedy(city_groups, seed)

    return city_groups, county_groups


def lottery_to_groups(
    city_groups: dict[str, int],
    county_groups: dict[str, int],
) -> list[list[str]]:
    """将抽签结果转化为分组列表格式。"""
    groups = [[] for _ in range(NUM_GROUPS)]
    for code, g_idx in city_groups.items():
        groups[g_idx].append(code)
    for code, g_idx in county_groups.items():
        groups[g_idx].append(code)
    return groups


# -- 蒙特卡洛公平性验证 ---------------------------------------------------------

def simulate_lottery_fairness(
    n_simulations: int = 10000,
    seed: int = 42,
) -> dict:
    """
    蒙特卡洛模拟大量抽签，统计：

    1. hard_feasible_rate: 硬约束全部满足的比例
    2. violation_mean / violation_std: 软约束违反次数的均值与标准差
    3. violation_distribution: 软约束违反次数的分布
    4. uniformity: 各队落入各组的概率均匀性
    """
    from .grouping import check_hard_constraints, count_soft_violations

    rng = random.Random(seed)

    team_group_counts = defaultdict(lambda: np.zeros(NUM_GROUPS, dtype=int))
    violation_counts = []
    feasible_count = 0
    violation_dist = defaultdict(int)

    for sim in range(n_simulations):
        sim_seed = rng.randint(0, 2**31 - 1)
        city_groups, county_groups = run_lottery(seed=sim_seed, method="greedy")
        groups = lottery_to_groups(city_groups, county_groups)

        # 统计各队在各个组出现的次数
        for g_idx, g in enumerate(groups):
            for code in g:
                team_group_counts[code][g_idx] += 1

        # 硬约束检查
        ok, _ = check_hard_constraints(groups)
        if ok:
            feasible_count += 1

        # 软约束统计
        v = count_soft_violations(groups)
        violation_counts.append(v["total_violations"])
        violation_dist[v["total_violations"]] += 1

    n_actual = len(violation_counts)

    # 均匀性检验：各队在各组的分布是否均匀
    uniformity = {}
    for code in team_group_counts:
        counts = team_group_counts[code]
        total = counts.sum()
        if total == 0:
            continue
        expected = total / NUM_GROUPS
        chi_sq = float(np.sum((counts - expected) ** 2 / max(expected, 1e-6)))
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


# -- 格式化输出 -----------------------------------------------------------------

def format_lottery_result(city_groups: dict, county_groups: dict) -> str:
    """格式化一次抽签结果为可读文本。"""
    groups = [[] for _ in range(NUM_GROUPS)]
    for code, g in city_groups.items():
        groups[g].append(code)
    for code, g in county_groups.items():
        groups[g].append(code)

    lines = ["抽签结果:", "-" * 50]
    for i, g in enumerate(groups):
        names = [TEAM_BY_CODE[c]["name"] for c in g]
        lines.append(f"  组{i+1:2d}: {', '.join(names)}")
    return "\n".join(lines)