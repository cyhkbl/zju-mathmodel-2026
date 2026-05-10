"""
Task 4：赛制建议与分析

分析内容：
1. 当前赛制（16组×4队 → 32强淘汰赛）公平性分析
2. 备选赛制：瑞士轮制、双败淘汰制
3. 蒙特卡洛模拟各队夺冠概率分布
4. 竞技水平展示度分析
"""

import random
import numpy as np
from collections import defaultdict

from .data import ALL_TEAMS, NUM_GROUPS, GROUP_SIZE, TEAM_BY_CODE


# -- 实力模型 -----------------------------------------------------

def build_strength_model(gdp_weight=0.7, random_weight=0.3, seed=42):
    """
    基于GDP构建队伍实力分数。
    归一化到 [0.3, 1.0]。
    """
    rng = np.random.RandomState(seed)
    gdps = np.array([t["gdp"] for t in ALL_TEAMS], dtype=float)
    log_gdp = np.log1p(gdps)
    norm_gdp = (log_gdp - log_gdp.min()) / (log_gdp.max() - log_gdp.min())
    noise = rng.uniform(0, 1, len(ALL_TEAMS))
    raw = gdp_weight * norm_gdp + random_weight * noise
    strength = 0.3 + 0.7 * (raw - raw.min()) / (raw.max() - raw.min())
    return {ALL_TEAMS[i]["code"]: float(strength[i]) for i in range(len(ALL_TEAMS))}


def match_prob(s_a, s_b):
    """Bradley-Terry模型：A赢B的概率。"""
    return s_a / (s_a + s_b)


def simulate_match(s_a, s_b, rng):
    """模拟一场比赛，返回 (winner, loser)。"""
    if rng.random() < match_prob(s_a, s_b):
        return "A", "B"
    return "B", "A"


# -- 赛制1：当前赛制（小组循环 + 淘汰赛）----------------------------

def simulate_group_stage(group_codes, strength, rng):
    """模拟单循环小组赛，返回组内排名。"""
    n = len(group_codes)
    points = {c: 0 for c in group_codes}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = group_codes[i], group_codes[j]
            result = simulate_match(strength[a], strength[b], rng)
            if result[0] == "A":
                points[a] += 3
            else:
                points[b] += 3
    ranking = sorted(group_codes, key=lambda c: points[c], reverse=True)
    return ranking, points


def simulate_knockout(teams, strength, rng):
    """模拟单败淘汰赛，返回冠军。"""
    current = list(teams)
    while len(current) > 1:
        next_round = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                a, b = current[i], current[i + 1]
                result = simulate_match(strength[a], strength[b], rng)
                winner = a if result[0] == "A" else b
                next_round.append(winner)
            else:
                next_round.append(current[i])
        current = next_round
    return current[0]


def simulate_current_format(groups, strength, rng):
    """模拟当前赛制：16组单循环 + 32强淘汰赛。"""
    qualifiers = []
    all_points = {}
    for g in groups:
        ranking, points = simulate_group_stage(g, strength, rng)
        qualifiers.extend(ranking[:2])
        all_points.update(points)
    rng.shuffle(qualifiers)
    champion = simulate_knockout(qualifiers, strength, rng)
    return champion, all_points, qualifiers


# -- 赛制2：瑞士轮制 ----------------------------------------------

def simulate_swiss_system(all_codes, strength, n_rounds=6, rng=None):
    """瑞士轮制：O(n log n) 配对。"""
    if rng is None:
        rng = random.Random()

    points = {c: 0.0 for c in all_codes}

    for r in range(n_rounds):
        # 按积分排序后顺序配对相邻队（O(n log n)）
        sorted_teams = sorted(all_codes, key=lambda c: points[c], reverse=True)
        for i in range(0, len(sorted_teams) - 1, 2):
            a, b = sorted_teams[i], sorted_teams[i + 1]
            result = simulate_match(strength[a], strength[b], rng)
            if result[0] == "A":
                points[a] += 1.0
            else:
                points[b] += 1.0

    ranking = sorted(all_codes, key=lambda c: points[c], reverse=True)
    top32 = ranking[:32]
    champion = simulate_knockout(top32, strength, rng)
    return champion, points, top32


# -- 赛制3：双败淘汰制 --------------------------------------------

def simulate_double_elimination(all_codes, strength, rng):
    """
    双败淘汰制：输两场才出局。
    先做3轮瑞士轮预选取前32名，再双败淘汰。
    """
    # 预选：3轮瑞士轮
    points = {c: 0.0 for c in all_codes}
    for r in range(3):
        sorted_teams = sorted(all_codes, key=lambda c: points[c], reverse=True)
        for i in range(0, len(sorted_teams) - 1, 2):
            a, b = sorted_teams[i], sorted_teams[i + 1]
            result = simulate_match(strength[a], strength[b], rng)
            if result[0] == "A":
                points[a] += 1.0
            else:
                points[b] += 1.0

    ranking = sorted(all_codes, key=lambda c: points[c], reverse=True)
    top32 = ranking[:32]

    # 双败淘汰：简洁实现
    wins_needed = {c: 2 for c in top32}  # 需赢2场才安全
    losses = {c: 0 for c in top32}
    alive = set(top32)

    rng.shuffle(top32)
    current = list(top32)

    while len(current) > 1:
        next_round = []
        for i in range(0, len(current) - 1, 2):
            a, b = current[i], current[i + 1]
            result = simulate_match(strength[a], strength[b], rng)
            winner = a if result[0] == "A" else b
            loser = b if result[0] == "A" else a
            losses[loser] += 1
            if losses[loser] < 2:
                next_round.append(loser)
            next_round.append(winner)
        if len(current) % 2 == 1:
            next_round.append(current[-1])
        current = next_round

        # 淘汰累积过多败场的队
        current = [c for c in current if losses[c] < 2]

    champion = current[0] if current else top32[0]
    return champion


# -- 蒙特卡洛综合模拟 --------------------------------------------

def monte_carlo_comparison(groups, n_simulations=5000, seed=42):
    """对比三种赛制下各队夺冠概率。"""
    rng = random.Random(seed)
    strength = build_strength_model(seed=seed)
    all_codes = [t["code"] for t in ALL_TEAMS]

    results = {
        "current": defaultdict(int),
        "swiss": defaultdict(int),
        "double_elim": defaultdict(int),
    }

    for sim in range(n_simulations):
        sim_rng = random.Random(rng.randint(0, 2**31))
        champ, _, _ = simulate_current_format(groups, strength, sim_rng)
        results["current"][champ] += 1

        sim_rng2 = random.Random(rng.randint(0, 2**31))
        champ2, _, _ = simulate_swiss_system(all_codes, strength, rng=sim_rng2)
        results["swiss"][champ2] += 1

        sim_rng3 = random.Random(rng.randint(0, 2**31))
        champ3 = simulate_double_elimination(all_codes, strength, sim_rng3)
        results["double_elim"][champ3] += 1

    probs = {}
    for fmt in results:
        probs[fmt] = {c: cnt / n_simulations for c, cnt in results[fmt].items()}

    return probs, strength


def analyze_competitiveness(groups, strength, n_simulations=2000, seed=42):
    """分析竞技水平展示度：弱队平均比赛场数和出线率。"""
    rng = random.Random(seed)

    sorted_teams = sorted(ALL_TEAMS, key=lambda t: strength[t["code"]])
    weak_codes = set(t["code"] for t in sorted_teams[:13])

    weak_qualify = defaultdict(int)

    for sim in range(n_simulations):
        sim_rng = random.Random(rng.randint(0, 2**31))
        for g in groups:
            ranking, _ = simulate_group_stage(g, strength, sim_rng)
            for code in g:
                if code in weak_codes and code in ranking[:2]:
                    weak_qualify[code] += 1

    qualify_rate = {c: weak_qualify[c] / n_simulations for c in weak_codes}

    return {
        "weak_teams": list(weak_codes),
        "avg_matches": {c: 3.0 for c in weak_codes},  # 小组赛固定3场
        "qualify_rate": qualify_rate,
        "avg_qualify_rate": np.mean(list(qualify_rate.values())),
    }


def format_tournament_comparison(probs, strength) -> str:
    """格式化赛制对比结果。"""
    lines = ["赛制对比分析", "=" * 60]

    top_teams = sorted(ALL_TEAMS, key=lambda t: strength[t["code"]], reverse=True)[:15]

    header = f"{'队伍':>8s}  {'实力':>6s}  {'当前赛制':>8s}  {'瑞士轮':>8s}  {'双败淘汰':>8s}"
    lines.append(header)
    lines.append("-" * 60)

    for t in top_teams:
        code = t["code"]
        name = t["name"]
        s = strength[code]
        p1 = probs["current"].get(code, 0)
        p2 = probs["swiss"].get(code, 0)
        p3 = probs["double_elim"].get(code, 0)
        lines.append(f"{name:>8s}  {s:.4f}  {p1:8.4f}  {p2:8.4f}  {p3:8.4f}")

    for fmt in ["current", "swiss", "double_elim"]:
        p = [probs[fmt].get(c, 0) for c in [t["code"] for t in ALL_TEAMS]]
        gini = _gini(np.array(p))
        lines.append(f"\n{fmt} 赛制 Gini系数: {gini:.4f}")

    return "\n".join(lines)


def _gini(x):
    """计算Gini系数。"""
    x = np.sort(x)
    n = len(x)
    if n == 0 or np.sum(x) == 0:
        return 0
    return (2 * np.sum((np.arange(1, n + 1) * x)) - (n + 1) * np.sum(x)) / (n * np.sum(x))
