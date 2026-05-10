"""
Task 1：生成符合约束的分组方案

方法：
- 约束规划（CP-SAT）求解可行分组
- 模拟退火优化软约束
- 多方案生成 + 多目标评价
"""

import random
import itertools
import numpy as np
from collections import defaultdict

from .data import (
    ALL_TEAMS, CITY_CODES, COUNTY_CODES, PARENT_MAP,
    CITY_CHILDREN, NUM_GROUPS, GROUP_SIZE, NUM_TEAMS,
    TEAM_BY_CODE, haversine_km,
)


# ── 约束检查 ─────────────────────────────────────────────────────

def check_hard_constraints(groups: list[list[str]]) -> tuple[bool, str]:
    """
    检查硬约束：
    1. 每组恰好4队
    2. 每组最多1个市级队
    3. 市级队不能与该市代管的县级队同组
    """
    for i, g in enumerate(groups):
        if len(g) != GROUP_SIZE:
            return False, f"组{i+1}只有{len(g)}队"
        city_count = sum(1 for c in g if TEAM_BY_CODE[c]["is_city"])
        if city_count > 1:
            return False, f"组{i+1}有{city_count}个市级队"
        # 市-县冲突
        for c in g:
            t = TEAM_BY_CODE[c]
            if t["is_city"]:
                for cc in g:
                    tt = TEAM_BY_CODE[cc]
                    if not tt["is_city"] and tt["parent"] == c:
                        return False, f"组{i+1}: {t['name']}与{tt['name']}同城"
    return True, "OK"


def count_soft_violations(groups: list[list[str]]) -> dict:
    """
    统计软约束违反次数：
    - 同市县级队被分到同组的次数
    """
    violations = 0
    detail = defaultdict(int)
    for g in groups:
        # 按 parent 分组统计县级队
        parent_count = defaultdict(int)
        for c in g:
            t = TEAM_BY_CODE[c]
            if not t["is_city"]:
                parent_count[t["parent"]] += 1
        for parent, cnt in parent_count.items():
            if cnt > 1:
                pairs = cnt * (cnt - 1) // 2
                violations += pairs
                detail[parent] += pairs
    return {"total_violations": violations, "detail": dict(detail)}


def evaluate_balance(groups: list[list[str]]) -> dict:
    """
    评估组间均衡性（基于GDP）。
    """
    gdp_sums = []
    for g in groups:
        s = sum(TEAM_BY_CODE[c]["gdp"] for c in g)
        gdp_sums.append(s)
    gdp_sums = np.array(gdp_sums, dtype=float)
    return {
        "mean": float(np.mean(gdp_sums)),
        "std": float(np.std(gdp_sums)),
        "cv": float(np.std(gdp_sums) / np.mean(gdp_sums)),
        "min": float(np.min(gdp_sums)),
        "max": float(np.max(gdp_sums)),
    }


def evaluate_groups(groups: list[list[str]]) -> dict:
    """综合评价一个分组方案。"""
    ok, msg = check_hard_constraints(groups)
    soft = count_soft_violations(groups)
    balance = evaluate_balance(groups)
    return {
        "feasible": ok,
        "feasible_msg": msg,
        "soft_violations": soft["total_violations"],
        "soft_detail": soft["detail"],
        "balance": balance,
    }


# ── 方案生成：约束规划（CP-SAT）─────────────────────────────────────

def generate_csp_solution(seed: int = None) -> list[list[str]] | None:
    """用 OR-Tools CP-SAT 求解一个可行分组。"""
    from ortools.sat.python import cp_model

    if seed is not None:
        random.seed(seed)

    model = cp_model.CpModel()
    n = NUM_TEAMS
    g = NUM_GROUPS

    # x[i][j] = 1 表示队 i 分到组 j
    x = {}
    for i in range(n):
        for j in range(g):
            x[i, j] = model.NewBoolVar(f"x_{i}_{j}")

    # 每队恰好分到1组
    for i in range(n):
        model.Add(sum(x[i, j] for j in range(g)) == 1)

    # 每组恰好4队
    for j in range(g):
        model.Add(sum(x[i, j] for i in range(n)) == GROUP_SIZE)

    # 硬约束：每组最多1个市级队
    city_indices = [i for i in range(n) if ALL_TEAMS[i]["is_city"]]
    for j in range(g):
        model.Add(sum(x[i, j] for i in city_indices) <= 1)

    # 硬约束：市级队不与该市代管县级队同组
    for ci, city_code in enumerate(CITY_CODES):
        city_idx = CITY_CODES.index(city_code)
        children_codes = CITY_CHILDREN[city_code]
        child_indices = [COUNTY_CODES.index(c) for c in children_codes]
        # 修正索引：city_idx 对应 ALL_TEAMS 中的位置
        city_team_idx = [i for i in range(n) if ALL_TEAMS[i]["code"] == city_code][0]
        child_team_indices = [i for i in range(n) if ALL_TEAMS[i]["code"] in children_codes]
        for j in range(g):
            for ct in child_team_indices:
                model.Add(x[city_team_idx, j] + x[ct, j] <= 1)

    # 求解
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    if seed is not None:
        solver.parameters.random_seed = seed
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        groups = [[] for _ in range(g)]
        for i in range(n):
            for j in range(g):
                if solver.Value(x[i, j]) == 1:
                    groups[j].append(ALL_TEAMS[i]["code"])
        return groups
    return None


# ── 方案生成：贪心 + 随机化 ──────────────────────────────────────

def generate_greedy_random(seed: int = None) -> list[list[str]]:
    """
    贪心 + 随机化：
    1. 先把11个市级队随机分配到11个不同组
    2. 剩余5个空组 + 53个县级队，用带约束的随机填充
    """
    if seed is not None:
        random.seed(seed)

    groups = [[] for _ in range(NUM_GROUPS)]
    city_order = CITY_CODES[:]
    random.shuffle(city_order)

    # 市级队分配到不同组
    group_indices = list(range(NUM_GROUPS))
    random.shuffle(group_indices)
    city_to_group = {}
    for i, city_code in enumerate(city_order):
        g_idx = group_indices[i]
        groups[g_idx].append(city_code)
        city_to_group[city_code] = g_idx

    # 按 parent 分组县级队，逐市处理
    county_shuffled = COUNTY_CODES[:]
    random.shuffle(county_shuffled)

    # 按 parent 分组
    parent_counties = defaultdict(list)
    for c in county_shuffled:
        parent_counties[PARENT_MAP[c]].append(c)

    for parent_city, children in parent_counties.items():
        forbidden_group = city_to_group.get(parent_city)
        # 可选组（不含该市市级队所在组）
        available = [i for i in range(NUM_GROUPS) if i != forbidden_group]

        for child_code in children:
            # 在可用组中选一个未满的组
            random.shuffle(available)
            placed = False
            for g_idx in available:
                if len(groups[g_idx]) < GROUP_SIZE:
                    groups[g_idx].append(child_code)
                    placed = True
                    break
            if not placed:
                # 退而求其次：任意未满组
                for g_idx in range(NUM_GROUPS):
                    if len(groups[g_idx]) < GROUP_SIZE:
                        groups[g_idx].append(child_code)
                        break

    return groups


# ── 模拟退火优化 ─────────────────────────────────────────────────

def _swap_counties_between_groups(groups, rng):
    """随机交换两个组中的县级队，保持硬约束。"""
    new_groups = [g[:] for g in groups]

    # 找两个不同的组，各有县级队
    attempts = 0
    while attempts < 100:
        g1, g2 = rng.sample(range(NUM_GROUPS), 2)
        county_in_g1 = [c for c in new_groups[g1] if not TEAM_BY_CODE[c]["is_city"]]
        county_in_g2 = [c for c in new_groups[g2] if not TEAM_BY_CODE[c]["is_city"]]
        if county_in_g1 and county_in_g2:
            c1 = rng.choice(county_in_g1)
            c2 = rng.choice(county_in_g2)
            # 检查交换后是否违反硬约束
            t1, t2 = TEAM_BY_CODE[c1], TEAM_BY_CODE[c2]
            # 检查 c1 到 g2：不能与 g2 中市级队同城
            g2_cities = [TEAM_BY_CODE[c]["code"] for c in new_groups[g2] if TEAM_BY_CODE[c]["is_city"]]
            if t1["parent"] in g2_cities:
                attempts += 1
                continue
            g1_cities = [TEAM_BY_CODE[c]["code"] for c in new_groups[g1] if TEAM_BY_CODE[c]["is_city"]]
            if t2["parent"] in g1_cities:
                attempts += 1
                continue
            # 交换
            new_groups[g1].remove(c1)
            new_groups[g2].remove(c2)
            new_groups[g1].append(c2)
            new_groups[g2].append(c1)
            return new_groups
        attempts += 1
    return new_groups


def simulated_annealing(
    initial: list[list[str]],
    max_iter: int = 50000,
    T_start: float = 10.0,
    T_end: float = 0.01,
    seed: int = None,
) -> tuple[list[list[str]], dict]:
    """模拟退火优化软约束。"""
    rng = random.Random(seed)

    def cost(groups):
        soft = count_soft_violations(groups)
        return soft["total_violations"]

    current = initial
    current_cost = cost(current)
    best = current
    best_cost = current_cost

    history = []

    for it in range(max_iter):
        T = T_start * (T_end / T_start) ** (it / max_iter)
        neighbor = _swap_counties_between_groups(current, rng)
        neighbor_cost = cost(neighbor)

        delta = neighbor_cost - current_cost
        if delta <= 0 or rng.random() < np.exp(-delta / max(T, 1e-10)):
            current = neighbor
            current_cost = neighbor_cost

        if current_cost < best_cost:
            best = current
            best_cost = current_cost
            history.append({"iter": it, "cost": best_cost})

        if best_cost == 0:
            break

    return best, {"history": history, "final_cost": best_cost}


# ── 多方案生成与评价 ─────────────────────────────────────────────

def generate_solutions(n: int = 5, method: str = "mixed", seed: int = 42) -> list[dict]:
    """
    生成 n 个分组方案并评价。
    method: "csp", "greedy", "mixed"
    """
    solutions = []
    rng = random.Random(seed)

    for i in range(n):
        if method == "csp" or (method == "mixed" and i < 2):
            sol = generate_csp_solution(seed=seed + i)
            if sol is None:
                sol = generate_greedy_random(seed=seed + i)
            method_used = "csp"
        elif method == "greedy" or (method == "mixed" and i < 4):
            sol = generate_greedy_random(seed=seed + i)
            method_used = "greedy"
        else:
            # greedy + SA
            sol = generate_greedy_random(seed=seed + i)
            sol, sa_info = simulated_annealing(sol, max_iter=20000, seed=seed + i)
            method_used = f"greedy+SA"

        eval_result = evaluate_groups(sol)
        solutions.append({
            "id": i + 1,
            "method": method_used,
            "groups": sol,
            "eval": eval_result,
        })

    return solutions


def format_solution_table(sol: dict) -> str:
    """格式化一个方案为文本表格。"""
    lines = [f"方案 {sol['id']} ({sol['method']})  可行={sol['eval']['feasible']}  软约束违反={sol['eval']['soft_violations']}"]
    lines.append(f"  GDP均衡: 均值={sol['eval']['balance']['mean']:.0f}亿  CV={sol['eval']['balance']['cv']:.4f}")
    lines.append("-" * 60)
    for i, g in enumerate(sol["groups"]):
        names = [TEAM_BY_CODE[c]["name"] for c in g]
        gdp = sum(TEAM_BY_CODE[c]["gdp"] for c in g)
        lines.append(f"  组{i+1:2d}: {', '.join(names):30s}  GDP={gdp:5d}亿")
    return "\n".join(lines)
