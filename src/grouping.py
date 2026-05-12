"""
Task 1：生成符合约束的分组方案
 
方法：
- 约束规划（CP-SAT）求解可行分组
- 模拟退火优化软约束（T0=100, alpha=0.995, Tf=1）
- 多方案生成 + 多目标评价
 
修复说明：
1. 模拟退火参数改为与论文一致：T_start=100, alpha=0.995, T_end=1，
   冷却方式改为几何冷却 T *= alpha。
2. generate_solutions 对所有方案（包括 CP-SAT 方案）均施加 SA 优化，
   与论文"所有方案均经模拟退火优化"一致。
3. generate_csp_solution 中删除冗余的 CITY_CODES.index(city_code) 调用，
   直接用枚举索引 ci。
"""
 
import math
import random
import numpy as np
from collections import defaultdict
 
from .data import (
    ALL_TEAMS, CITY_CODES, COUNTY_CODES, PARENT_MAP,
    CITY_CHILDREN, NUM_GROUPS, GROUP_SIZE, NUM_TEAMS,
    TEAM_BY_CODE, haversine_km,
)
 
 
# -- 约束检查 -------------------------------------------------------------------
 
def check_hard_constraints(groups: list[list[str]]) -> tuple[bool, str]:
    """
    检查硬约束：
    1. 每组恰好 GROUP_SIZE 队
    2. 每组最多 1 个市级队
    3. 市级队不能与该市代管的县级队同组
    """
    for i, g in enumerate(groups):
        if len(g) != GROUP_SIZE:
            return False, f"组{i+1}只有{len(g)}队"
        city_count = sum(1 for c in g if TEAM_BY_CODE[c]["is_city"])
        if city_count > 1:
            return False, f"组{i+1}有{city_count}个市级队"
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
    - 同市县级队被分到同组的对数
    """
    violations = 0
    detail = defaultdict(int)
    for g in groups:
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
    """评估组间均衡性（基于 GDP）。"""
    gdp_sums = []
    for g in groups:
        s = sum(TEAM_BY_CODE[c]["gdp"] for c in g)
        gdp_sums.append(s)
    gdp_sums = np.array(gdp_sums, dtype=float)
    return {
        "mean": float(np.mean(gdp_sums)),
        "std":  float(np.std(gdp_sums)),
        "cv":   float(np.std(gdp_sums) / np.mean(gdp_sums)),
        "min":  float(np.min(gdp_sums)),
        "max":  float(np.max(gdp_sums)),
    }
 
 
def evaluate_groups(groups: list[list[str]]) -> dict:
    """综合评价一个分组方案。"""
    ok, msg = check_hard_constraints(groups)
    soft = count_soft_violations(groups)
    balance = evaluate_balance(groups)
    return {
        "feasible":       ok,
        "feasible_msg":   msg,
        "soft_violations": soft["total_violations"],
        "soft_detail":    soft["detail"],
        "balance":        balance,
    }
 
 
# -- 方案生成：约束规划（CP-SAT） -----------------------------------------------
 
def generate_csp_solution(seed: int = None) -> list[list[str]] | None:
    """用 OR-Tools CP-SAT 求解一个可行分组。"""
    try:
        from ortools.sat.python import cp_model
    except ModuleNotFoundError:
        return None
 
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
 
    # 每队恰好分到 1 组
    for i in range(n):
        model.Add(sum(x[i, j] for j in range(g)) == 1)
 
    # 每组恰好 GROUP_SIZE 队
    for j in range(g):
        model.Add(sum(x[i, j] for i in range(n)) == GROUP_SIZE)
 
    # 硬约束：每组最多 1 个市级队
    city_indices = [i for i in range(n) if ALL_TEAMS[i]["is_city"]]
    for j in range(g):
        model.Add(sum(x[i, j] for i in city_indices) <= 1)
 
    # 硬约束：市级队不与该市代管县级队同组
    # 修复：直接用 enumerate 的 ci，去掉冗余的 CITY_CODES.index(city_code)
    for ci, city_code in enumerate(CITY_CODES):
        city_team_idx = next(
            i for i in range(n) if ALL_TEAMS[i]["code"] == city_code
        )
        children_codes = CITY_CHILDREN[city_code]
        child_team_indices = [
            i for i in range(n) if ALL_TEAMS[i]["code"] in children_codes
        ]
        for j in range(g):
            for ct in child_team_indices:
                model.Add(x[city_team_idx, j] + x[ct, j] <= 1)
 
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
 
 
# -- 方案生成：贪心 + 随机化 -----------------------------------------------------
 
def generate_greedy_random(seed: int = None) -> list[list[str]]:
    """
    贪心 + 随机化：
    1. 先把 11 个市级队随机分配到 11 个不同组
    2. 剩余 5 个空组 + 53 个县级队，用带约束的随机填充
    """
    if seed is not None:
        random.seed(seed)
 
    groups = [[] for _ in range(NUM_GROUPS)]
    city_order = CITY_CODES[:]
    random.shuffle(city_order)
 
    group_indices = list(range(NUM_GROUPS))
    random.shuffle(group_indices)
    city_to_group = {}
    for i, city_code in enumerate(city_order):
        g_idx = group_indices[i]
        groups[g_idx].append(city_code)
        city_to_group[city_code] = g_idx
 
    county_shuffled = COUNTY_CODES[:]
    random.shuffle(county_shuffled)
 
    parent_counties = defaultdict(list)
    for c in county_shuffled:
        parent_counties[PARENT_MAP[c]].append(c)
 
    for parent_city, children in parent_counties.items():
        forbidden_group = city_to_group.get(parent_city)
        available = [i for i in range(NUM_GROUPS) if i != forbidden_group]
 
        for child_code in children:
            random.shuffle(available)
            placed = False
            for g_idx in available:
                if len(groups[g_idx]) < GROUP_SIZE:
                    groups[g_idx].append(child_code)
                    placed = True
                    break
            if not placed:
                for g_idx in range(NUM_GROUPS):
                    if len(groups[g_idx]) < GROUP_SIZE:
                        groups[g_idx].append(child_code)
                        break
 
    return groups
 
 
# -- 模拟退火优化 ----------------------------------------------------------------
 
def _swap_counties_between_groups(groups, rng):
    """随机交换两个组中的县级队，保持硬约束。"""
    new_groups = [g[:] for g in groups]
 
    attempts = 0
    while attempts < 100:
        g1, g2 = rng.sample(range(NUM_GROUPS), 2)
        county_in_g1 = [c for c in new_groups[g1] if not TEAM_BY_CODE[c]["is_city"]]
        county_in_g2 = [c for c in new_groups[g2] if not TEAM_BY_CODE[c]["is_city"]]
        if county_in_g1 and county_in_g2:
            c1 = rng.choice(county_in_g1)
            c2 = rng.choice(county_in_g2)
            t1, t2 = TEAM_BY_CODE[c1], TEAM_BY_CODE[c2]
            g2_cities = [
                TEAM_BY_CODE[c]["code"]
                for c in new_groups[g2] if TEAM_BY_CODE[c]["is_city"]
            ]
            if t1["parent"] in g2_cities:
                attempts += 1
                continue
            g1_cities = [
                TEAM_BY_CODE[c]["code"]
                for c in new_groups[g1] if TEAM_BY_CODE[c]["is_city"]
            ]
            if t2["parent"] in g1_cities:
                attempts += 1
                continue
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
    T_start: float = 100.0,   # 修复：与论文一致
    T_end: float = 1.0,       # 修复：与论文一致
    alpha: float = 0.995,     # 修复：新增冷却系数参数，与论文一致
    seed: int = None,
) -> tuple[list[list[str]], dict]:
    """
    模拟退火优化软约束。
    冷却方式：几何冷却 T = T * alpha，当 T < T_end 时停止。
    参数与论文对齐：T_start=100, alpha=0.995, T_end=1。
    """
    rng = random.Random(seed)
 
    def cost(groups):
        return count_soft_violations(groups)["total_violations"]
 
    current = initial
    current_cost = cost(current)
    best = current
    best_cost = current_cost
 
    T = T_start
    history = []
 
    for it in range(max_iter):
        if T < T_end:
            break
 
        neighbor = _swap_counties_between_groups(current, rng)
        neighbor_cost = cost(neighbor)
 
        delta = neighbor_cost - current_cost
        if delta <= 0 or rng.random() < math.exp(-delta / max(T, 1e-10)):
            current = neighbor
            current_cost = neighbor_cost
 
        if current_cost < best_cost:
            best = current
            best_cost = current_cost
            history.append({"iter": it, "cost": best_cost})
 
        T *= alpha  # 修复：几何冷却，与论文 alpha=0.995 一致
 
        if best_cost == 0:
            break
 
    return best, {"history": history, "final_cost": best_cost}
 
 
# -- 多方案生成与评价 ------------------------------------------------------------
 
def generate_solutions(n: int = 6, method: str = "mixed", seed: int = 42) -> list[dict]:
    """
    生成 n 个分组方案并评价。
    method: "csp", "greedy", "mixed"
 
    修复：所有方案均施加模拟退火优化，与论文描述一致。
    """
    solutions = []
 
    for i in range(n):
        # 生成初始可行解
        if method == "csp" or (method == "mixed" and i < 2):
            sol = generate_csp_solution(seed=seed + i)
            if sol is None:
                sol = generate_greedy_random(seed=seed + i)
                base_method = "greedy-fallback"
            else:
                base_method = "csp"
        else:
            sol = generate_greedy_random(seed=seed + i)
            base_method = "greedy"
 
        # 修复：对所有方案统一施加 SA 优化
        sol, sa_info = simulated_annealing(
            sol, max_iter=50000, T_start=100.0, T_end=1.0, alpha=0.995,
            seed=seed + i
        )
        method_used = f"{base_method}+SA"
 
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
    lines = [
        f"方案 {sol['id']} ({sol['method']})  "
        f"可行={sol['eval']['feasible']}  "
        f"软约束违反={sol['eval']['soft_violations']}"
    ]
    lines.append(
        f"  GDP均衡: 均值={sol['eval']['balance']['mean']:.0f}亿  "
        f"CV={sol['eval']['balance']['cv']:.4f}"
    )
    lines.append("-" * 60)
    for i, g in enumerate(sol["groups"]):
        names = [TEAM_BY_CODE[c]["name"] for c in g]
        gdp = sum(TEAM_BY_CODE[c]["gdp"] for c in g)
        lines.append(f"  组{i+1:2d}: {', '.join(names):30s}  GDP={gdp:5d}亿")
    return "\n".join(lines)
 
