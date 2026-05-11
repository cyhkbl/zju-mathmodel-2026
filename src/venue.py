"""
Task 3：比赛地点选择

方法：
1. 默认从候选城市中筛选8个比赛地点
2. 结合分组结果，优化分配使总旅行距离最小
3. 保证每个地点承办2个小组
4. folium 地图可视化（缺少 folium 时降级为简易 HTML）
"""

import numpy as np
from collections import defaultdict
from itertools import combinations

from .data import (
    ALL_TEAMS, CITY_CODES, NUM_GROUPS, TEAM_BY_CODE,
    get_coords_matrix, haversine_km, MUNICIPAL,
)


def kmeans_partition(teams=None, k=8, max_iter=100, seed=42):
    """K-means 聚类，将64队分为k个赛区。"""
    if teams is None:
        teams = ALL_TEAMS
    coords = np.array([[t["lng"], t["lat"]] for t in teams])

    rng = np.random.RandomState(seed)
    # K-means++ 初始化
    centers = [coords[rng.randint(len(coords))]]
    for _ in range(k - 1):
        dists = np.array([min(np.sum((c - np.array(centers))**2, axis=1)) for c in coords])
        probs = dists / dists.sum()
        idx = rng.choice(len(coords), p=probs)
        centers.append(coords[idx])
    centers = np.array(centers)

    labels = np.zeros(len(coords), dtype=int)
    for _ in range(max_iter):
        # 分配
        for i, c in enumerate(coords):
            dists = np.sum((centers - c) ** 2, axis=1)
            labels[i] = np.argmin(dists)
        # 更新中心
        new_centers = np.array([coords[labels == j].mean(axis=0) if np.sum(labels == j) > 0 else centers[j] for j in range(k)])
        if np.allclose(centers, new_centers, atol=1e-6):
            break
        centers = new_centers

    return labels, centers


def compute_travel_distances(groups, venue_assignments):
    """
    计算每个队到比赛地的距离。
    groups: 16个小组
    venue_assignments: {group_idx: venue_code} 或 {group_idx: (lng, lat)}
    返回每个队的距离列表。
    """
    distances = {}
    for g_idx, g in enumerate(groups):
        venue = venue_assignments[g_idx]
        if isinstance(venue, str):
            v = TEAM_BY_CODE[venue]
            v_lng, v_lat = v["lng"], v["lat"]
        else:
            v_lng, v_lat = venue
        for code in g:
            t = TEAM_BY_CODE[code]
            d = haversine_km(t["lng"], t["lat"], v_lng, v_lat)
            distances[code] = d
    return distances


def optimize_venue_assignment(groups, candidate_cities=None, seed=42):
    """
    优化比赛地点分配。

    候选城市：11个市级队所在城市。
    每个地点承办2个小组。
    目标：最小化总旅行距离 + 最大化公平性（距离标准差最小）。
    """
    if candidate_cities is None:
        candidate_cities = [t["code"] for t in ALL_TEAMS if t["is_city"]]

    # 计算所有队伍到所有候选城市的距离矩阵
    city_coords = {}
    for cc in candidate_cities:
        t = TEAM_BY_CODE[cc]
        city_coords[cc] = (t["lng"], t["lat"])

    # 对每个组，计算到每个候选城市的"组内平均距离"
    group_city_dist = {}
    for g_idx, g in enumerate(groups):
        for cc in candidate_cities:
            cx, cy = city_coords[cc]
            total = sum(
                haversine_km(TEAM_BY_CODE[c]["lng"], TEAM_BY_CODE[c]["lat"], cx, cy)
                for c in g
            )
            group_city_dist[(g_idx, cc)] = total / len(g)

    def greedy_assign(venues):
        """在给定场馆集合下，每轮选一个最小距离的(组, 地点)对。"""
        city_group_count = defaultdict(int)
        venue_map = {}
        remaining_groups = set(range(NUM_GROUPS))

        while remaining_groups:
            best_pair = None
            best_dist = float("inf")

            for g_idx in remaining_groups:
                for cc in venues:
                    if city_group_count[cc] >= 2:
                        continue
                    d = group_city_dist[(g_idx, cc)]
                    if d < best_dist:
                        best_dist = d
                        best_pair = (g_idx, cc)

            if best_pair is None:
                break

            g_idx, cc = best_pair
            venue_map[g_idx] = cc
            city_group_count[cc] += 1
            remaining_groups.remove(g_idx)

        score = sum(group_city_dist[(g_idx, cc)] for g_idx, cc in venue_map.items())
        return venue_map, score

    # 若候选地点多于8个，先枚举选出8个，使后续16组恰好每地2组。
    if len(candidate_cities) > 8:
        best_subset = None
        best_score = float("inf")
        for subset in combinations(candidate_cities, 8):
            subset_map, subset_score = greedy_assign(subset)
            if len(subset_map) == NUM_GROUPS and subset_score < best_score:
                best_subset = subset
                best_score = subset_score
        if best_subset is not None:
            candidate_cities = list(best_subset)

    # 贪心：每轮选一个 (group, city) 对使得总距离增量最小
    venue_map, _ = greedy_assign(candidate_cities)

    return venue_map


def evaluate_venue_plan(groups, venue_map):
    """评估比赛地点方案。"""
    distances = compute_travel_distances(groups, venue_map)
    dists = list(distances.values())
    dists_arr = np.array(dists)

    return {
        "mean_distance": float(np.mean(dists_arr)),
        "std_distance": float(np.std(dists_arr)),
        "max_distance": float(np.max(dists_arr)),
        "min_distance": float(np.min(dists_arr)),
        "cv": float(np.std(dists_arr) / np.mean(dists_arr)),
        "median_distance": float(np.median(dists_arr)),
        "team_distances": distances,
    }


def generate_venue_plan(groups, method="greedy", seed=42):
    """生成比赛地点方案。"""
    if method == "greedy":
        venue_map = optimize_venue_assignment(groups, seed=seed)
    elif method == "kmeans":
        # 用聚类结果指导
        labels, centers = kmeans_partition(k=8, seed=seed)
        venue_map = _assign_groups_to_kmeans_venue(groups, labels, centers)
    else:
        venue_map = optimize_venue_assignment(groups, seed=seed)

    eval_result = evaluate_venue_plan(groups, venue_map)
    return {
        "venue_map": venue_map,
        "eval": eval_result,
        "method": method,
    }


def _assign_groups_to_kmeans_venue(groups, labels, centers):
    """用聚类中心匹配最近的城市作为比赛地。"""
    city_codes = [t["code"] for t in ALL_TEAMS if t["is_city"]]
    city_coords = np.array([[TEAM_BY_CODE[c]["lng"], TEAM_BY_CODE[c]["lat"]] for c in city_codes])

    venue_map = {}
    city_group_count = defaultdict(int)
    assigned = set()

    # 对每个组，计算其中心，找最近的候选城市
    group_centers = []
    for g in groups:
        cx = np.mean([TEAM_BY_CODE[c]["lng"] for c in g])
        cy = np.mean([TEAM_BY_CODE[c]["lat"] for c in g])
        group_centers.append((cx, cy))

    # 按距离排序分配
    pairs = []
    for g_idx, (gcx, gcy) in enumerate(group_centers):
        for ci, cc in enumerate(city_codes):
            d = haversine_km(gcx, gcy, city_coords[ci][0], city_coords[ci][1])
            pairs.append((d, g_idx, cc))

    pairs.sort()
    for d, g_idx, cc in pairs:
        if g_idx in assigned:
            continue
        if city_group_count[cc] >= 2:
            continue
        venue_map[g_idx] = cc
        city_group_count[cc] += 1
        assigned.add(g_idx)

    return venue_map


def format_venue_plan(groups, venue_plan: dict) -> str:
    """格式化比赛地点方案。"""
    venue_map = venue_plan["venue_map"]
    eval_r = venue_plan["eval"]

    lines = [f"比赛地点方案 ({venue_plan['method']})"]
    lines.append(f"  平均距离: {eval_r['mean_distance']:.1f} km")
    lines.append(f"  距离标准差: {eval_r['std_distance']:.1f} km")
    lines.append(f"  变异系数: {eval_r['cv']:.4f}")
    lines.append("-" * 60)

    # 按比赛地分组
    venue_groups = defaultdict(list)
    for g_idx, cc in venue_map.items():
        venue_groups[cc].append(g_idx)

    for cc, g_idxs in sorted(venue_groups.items()):
        v = TEAM_BY_CODE[cc]
        lines.append(f"\n  比赛地: {v['name']} ({v['lng']:.2f}, {v['lat']:.2f})")
        for g_idx in g_idxs:
            g = groups[g_idx]
            names = [TEAM_BY_CODE[c]["name"] for c in g]
            avg_dist = np.mean([
                haversine_km(TEAM_BY_CODE[c]["lng"], TEAM_BY_CODE[c]["lat"], v["lng"], v["lat"])
                for c in g
            ])
            lines.append(f"    组{g_idx+1:2d} (平均{avg_dist:.0f}km): {', '.join(names)}")

    return "\n".join(lines)
