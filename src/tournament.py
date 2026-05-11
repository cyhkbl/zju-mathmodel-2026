"""
Task 4：赛制建议与分析

方法：
- 基于 GDP 构建 Bradley-Terry 实力模型
- 蒙特卡洛模拟三种赛制：当前赛制、简化瑞士轮制、近似双败淘汰制
- 用 Gini 系数衡量夺冠概率分布离散程度
"""

import random
import numpy as np
from collections import defaultdict

from data import ALL_TEAMS, TEAM_BY_CODE


# =========================
# 实力模型
# =========================

def build_strength_model(gdp_weight=0.7,
                         random_weight=0.3,
                         seed=42) -> dict[str, float]:
    """
    基于 GDP 构建队伍实力分数。
    对数归一化 + 随机噪声，映射到 [0.3, 1.0]。
    """
    rng = np.random.RandomState(seed)

    gdps = np.array([t["gdp"] for t in ALL_TEAMS], dtype=float)

    log_gdp = np.log1p(gdps)

    norm_gdp = (
        (log_gdp - log_gdp.min())
        / (log_gdp.max() - log_gdp.min())
    )

    noise = rng.uniform(0, 1, len(ALL_TEAMS))

    raw = gdp_weight * norm_gdp + random_weight * noise

    strength = (
        0.3
        + 0.7 * (raw - raw.min())
        / (raw.max() - raw.min())
    )

    return {
        ALL_TEAMS[i]["code"]: float(strength[i])
        for i in range(len(ALL_TEAMS))
    }


def match_prob(s_a: float, s_b: float) -> float:
    """Bradley-Terry：A 胜 B 的概率。"""
    return s_a / (s_a + s_b)


def simulate_match(a: str,
                   b: str,
                   strength: dict,
                   rng: random.Random) -> tuple[str, str]:
    """
    模拟一场比赛。

    返回：
        (胜者代号, 败者代号)
    """
    if rng.random() < match_prob(strength[a], strength[b]):
        return a, b
    return b, a


# =========================
# 赛制 1：当前赛制
# 16组单循环 + 32强淘汰赛
# =========================

def simulate_group_stage(group_codes: list[str],
                         strength: dict,
                         rng: random.Random):
    """
    单循环小组赛。

    返回：
        ranking : 排名列表
        points  : 积分字典
    """
    points = {c: 0 for c in group_codes}

    for i in range(len(group_codes)):
        for j in range(i + 1, len(group_codes)):
            a, b = group_codes[i], group_codes[j]

            winner, loser = simulate_match(
                a, b, strength, rng
            )

            points[winner] += 3

    ranking = sorted(
        group_codes,
        key=lambda c: (points[c], strength[c]),
        reverse=True
    )

    return ranking, points


def simulate_knockout(teams: list[str],
                      strength: dict,
                      rng: random.Random) -> str:
    """
    单败淘汰赛。

    返回：
        champion : 冠军代号
    """
    current = list(teams)

    while len(current) > 1:

        next_round = []

        rng.shuffle(current)

        for i in range(0, len(current), 2):

            if i + 1 < len(current):

                a, b = current[i], current[i + 1]

                winner, loser = simulate_match(
                    a, b, strength, rng
                )

                next_round.append(winner)

            else:
                # 奇数队轮空
                next_round.append(current[i])

        current = next_round

    return current[0]


def simulate_current_format(groups: list[list[str]],
                            strength: dict,
                            rng: random.Random):
    """
    当前赛制：
    16组单循环 + 32强淘汰赛

    返回：
        champion
        all_points
        qualifiers
    """
    qualifiers = []

    all_points = {}

    for g in groups:

        ranking, points = simulate_group_stage(
            g, strength, rng
        )

        qualifiers.extend(ranking[:2])

        all_points.update(points)

    rng.shuffle(qualifiers)

    champion = simulate_knockout(
        qualifiers,
        strength,
        rng
    )

    return champion, all_points, qualifiers


# =========================
# 赛制 2：简化瑞士轮制
# =========================

def simulate_swiss_system(all_codes: list[str],
                          strength: dict,
                          n_rounds: int = 6,
                          rng: random.Random = None):
    """
    简化瑞士轮近似模型：

    - 按当前积分排序后相邻配对
    - 不考虑重复对阵规避等标准瑞士轮细节
    - 6轮后取前32进入淘汰赛
    """
    if rng is None:
        rng = random.Random()

    points = {c: 0.0 for c in all_codes}

    for _ in range(n_rounds):

        sorted_teams = sorted(
            all_codes,
            key=lambda c: (points[c], strength[c]),
            reverse=True
        )

        for i in range(0, len(sorted_teams) - 1, 2):

            a = sorted_teams[i]
            b = sorted_teams[i + 1]

            winner, loser = simulate_match(
                a, b, strength, rng
            )

            points[winner] += 1.0

    ranking = sorted(
        all_codes,
        key=lambda c: (points[c], strength[c]),
        reverse=True
    )

    top32 = ranking[:32]

    champion = simulate_knockout(
        top32,
        strength,
        rng
    )

    return champion, points, top32


# =========================
# 赛制 3：近似双败淘汰制
# =========================

def simulate_double_elimination(all_codes: list[str],
                                strength: dict,
                                rng: random.Random) -> str:
    """
    近似双败淘汰机制：

    说明：
    - 先进行 3 轮积分预选
    - 取前 32 名进入淘汰阶段
    - 输一场进入败者组
    - 输两场后淘汰
    - 并非严格标准双败赛程
    """

    # ---------------------
    # 预选：3轮积分赛
    # ---------------------

    points = {c: 0.0 for c in all_codes}

    for _ in range(3):

        sorted_teams = sorted(
            all_codes,
            key=lambda c: (points[c], strength[c]),
            reverse=True
        )

        for i in range(0, len(sorted_teams) - 1, 2):

            a = sorted_teams[i]
            b = sorted_teams[i + 1]

            winner, loser = simulate_match(
                a, b, strength, rng
            )

            points[winner] += 1.0

    ranking = sorted(
        all_codes,
        key=lambda c: (points[c], strength[c]),
        reverse=True
    )

    top32 = ranking[:32]

    # ---------------------
    # 双败阶段
    # ---------------------

    winners = list(top32)

    losers = []

    rng.shuffle(winners)

    while True:

        # -----------------
        # 胜者组
        # -----------------

        next_winners = []

        for i in range(0, len(winners), 2):

            if i + 1 < len(winners):

                a = winners[i]
                b = winners[i + 1]

                win, lose = simulate_match(
                    a, b, strength, rng
                )

                next_winners.append(win)

                losers.append(lose)

            else:
                next_winners.append(winners[i])

        winners = next_winners

        # -----------------
        # 败者组
        # -----------------

        next_losers = []

        for i in range(0, len(losers), 2):

            if i + 1 < len(losers):

                a = losers[i]
                b = losers[i + 1]

                win, lose = simulate_match(
                    a, b, strength, rng
                )

                next_losers.append(win)

            else:
                next_losers.append(losers[i])

        losers = next_losers

        # -----------------
        # 决赛
        # -----------------

        if len(winners) == 1 and len(losers) <= 1:

            if len(losers) == 1:

                a = winners[0]
                b = losers[0]

                winner, loser = simulate_match(
                    a, b, strength, rng
                )

                return winner

            return winners[0]


# =========================
# 蒙特卡洛模拟
# =========================

def monte_carlo_comparison(groups: list[list[str]],
                           n_simulations: int = 5000,
                           seed: int = 42):
    """
    对比三种赛制下各队夺冠概率。

    返回：
        probs
        ginis
        strength
    """

    rng = random.Random(seed)

    strength = build_strength_model(seed=seed)

    all_codes = [t["code"] for t in ALL_TEAMS]

    results = {
        "current": defaultdict(int),
        "swiss": defaultdict(int),
        "double_elim": defaultdict(int),
    }

    for _ in range(n_simulations):

        # 当前赛制
        sim_rng = random.Random(
            rng.randint(0, 2**31 - 1)
        )

        champ, _, _ = simulate_current_format(
            groups,
            strength,
            sim_rng
        )

        results["current"][champ] += 1

        # 瑞士轮
        sim_rng2 = random.Random(
            rng.randint(0, 2**31 - 1)
        )

        champ, _, _ = simulate_swiss_system(
            all_codes,
            strength,
            6,
            sim_rng2
        )

        results["swiss"][champ] += 1

        # 双败
        sim_rng3 = random.Random(
            rng.randint(0, 2**31 - 1)
        )

        champ = simulate_double_elimination(
            all_codes,
            strength,
            sim_rng3
        )

        results["double_elim"][champ] += 1

    probs = {
        fmt: {
            code: cnt / n_simulations
            for code, cnt in counts.items()
        }
        for fmt, counts in results.items()
    }

    ginis = {}

    for fmt in ["current", "swiss", "double_elim"]:

        vals = np.array([
            probs[fmt].get(t["code"], 0)
            for t in ALL_TEAMS
        ])

        ginis[fmt] = _gini(vals)

    return probs, ginis, strength


# =========================
# Gini 系数
# =========================

def _gini(x: np.ndarray) -> float:
    """
    计算 Gini 系数。

    Gini 越低，
    说明夺冠概率分布越均衡。
    """
    x = np.sort(x)

    n = len(x)

    if n == 0 or np.sum(x) == 0:
        return 0.0

    g = (
        2 * np.sum(np.arange(1, n + 1) * x)
        - (n + 1) * np.sum(x)
    ) / (n * np.sum(x))

    return float(max(g, 0.0))


# =========================
# 格式化输出
# =========================

def format_tournament_comparison(probs: dict,
                                 strength: dict) -> str:
    """
    格式化赛制对比结果。
    """

    lines = [
        "赛制对比分析",
        "=" * 70
    ]

    top_teams = sorted(
        ALL_TEAMS,
        key=lambda t: strength.get(t["code"], 0),
        reverse=True
    )[:15]

    header = (
        f"{'队伍':>8s}  "
        f"{'实力':>6s}  "
        f"{'当前赛制':>10s}  "
        f"{'瑞士轮':>10s}  "
        f"{'近似双败':>10s}"
    )

    lines.append(header)

    lines.append("-" * 70)

    for t in top_teams:

        code = t["code"]

        name = t["name"]

        s = strength.get(code, 0)

        p1 = probs["current"].get(code, 0)

        p2 = probs["swiss"].get(code, 0)

        p3 = probs["double_elim"].get(code, 0)

        lines.append(
            f"{name:>8s}  "
            f"{s:.4f}    "
            f"{p1:10.4f}    "
            f"{p2:10.4f}    "
            f"{p3:10.4f}"
        )

    lines.append("\n")

    for fmt, label in [
        ("current", "当前赛制"),
        ("swiss", "瑞士轮"),
        ("double_elim", "近似双败"),
    ]:

        vals = np.array([
            probs[fmt].get(t["code"], 0)
            for t in ALL_TEAMS
        ])

        gini = _gini(vals)

        lines.append(
            f"{label} Gini 系数: {gini:.4f}"
        )

    return "\n".join(lines)