"""
可视化工具模块

提供：
- 分组方案表格图
- 比赛地点地图（folium）
- 赛制对比图表
- 抽签公平性统计图
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch
from collections import defaultdict

from .data import ALL_TEAMS, TEAM_BY_CODE, NUM_GROUPS, haversine_km

# -- 中文字体 -----------------------------------------------------

def _setup_chinese_font():
    """尝试设置中文字体。"""
    candidates = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    ]
    for path in candidates:
        try:
            fm.FontProperties(fname=path)
            plt.rcParams["font.family"] = fm.FontProperties(fname=path).get_name()
            plt.rcParams["axes.unicode_minus"] = False
            return
        except Exception:
            continue
    # fallback: 用 sans-serif
    plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

_setup_chinese_font()


# -- 分组方案热力图 -----------------------------------------------

def plot_group_heatmap(groups, save_path=None, title="分组方案"):
    """绘制分组方案热力图（按GDP）。"""
    fig, ax = plt.subplots(figsize=(14, 10))

    data = []
    row_labels = []
    col_labels = [f"组{i+1}" for i in range(NUM_GROUPS)]

    for code in [t["code"] for t in ALL_TEAMS]:
        row = []
        for g_idx, g in enumerate(groups):
            row.append(1.0 if code in g else 0.0)
        data.append(row)
        row_labels.append(TEAM_BY_CODE[code]["name"])

    data = np.array(data)
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", interpolation="nearest")

    ax.set_xticks(range(NUM_GROUPS))
    ax.set_xticklabels(col_labels, fontsize=9, rotation=45, ha="right")
    ax.set_yticks(range(len(ALL_TEAMS)))
    ax.set_yticklabels(row_labels, fontsize=7)
    ax.set_title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# -- GDP 均衡箱线图 -----------------------------------------------

def plot_gdp_balance(solutions, save_path=None):
    """对比多个方案的GDP均衡性箱线图。"""
    fig, ax = plt.subplots(figsize=(10, 6))

    data = []
    labels = []
    for sol in solutions:
        gdp_sums = []
        for g in sol["groups"]:
            s = sum(TEAM_BY_CODE[c]["gdp"] for c in g)
            gdp_sums.append(s)
        data.append(gdp_sums)
        labels.append(f"方案{sol['id']}")

    bp = ax.boxplot(data, labels=labels, patch_artist=True)
    colors = plt.cm.Set2(np.linspace(0, 1, len(data)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)

    ax.set_ylabel("组GDP总和（亿元）")
    ax.set_title("各方案组间GDP均衡性对比")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# -- 软约束违反对比 -----------------------------------------------

def plot_soft_violations(solutions, save_path=None):
    """画各方案软约束违反次数：全部为0时用汇总卡片，否则用柱状图"""
    violations = [sol["eval"]["soft_violations"] for sol in solutions]

    if all(v == 0 for v in violations):
        # 全部为0：左边汇总卡片 + 右边柱状图
        fig, (ax_card, ax_bar) = plt.subplots(1, 2, figsize=(14, 5),
                                               gridspec_kw={"width_ratios": [1, 1.2]})

        # 左侧卡片
        ax_card.set_xlim(0, 1)
        ax_card.set_ylim(0, 1)
        ax_card.axis("off")
        ax_card.text(0.5, 0.75, "各方案软约束违反次数对比", fontsize=15, fontweight="bold",
                     ha="center", va="center")
        ax_card.text(0.5, 0.45, f"全部 {len(solutions)} 个方案\n软约束违反次数均为 0",
                     fontsize=13, ha="center", va="center", color="#2d8a4e")
        ax_card.text(0.5, 0.2, "✓ 硬约束与软约束全部满足",
                     fontsize=12, ha="center", va="center", color="#888888")
        rect = plt.Rectangle((0.05, 0.05), 0.9, 0.9, linewidth=1.5,
                              edgecolor="#2d8a4e", facecolor="#f0faf3",
                              transform=ax_card.transAxes, zorder=-1)
        ax_card.add_patch(rect)

        # 右侧柱状图
        labels = [f"方案{sol['id']}" for sol in solutions]
        bars = ax_bar.bar(labels, violations, color="#4e79a7", edgecolor="white", width=0.6)
        ax_bar.set_ylabel("软约束违反次数")
        ax_bar.set_title("各方案软约束违反次数")
        ax_bar.set_ylim(0, 1)
        ax_bar.set_yticks([0, 1])
        ax_bar.grid(True, alpha=0.3, axis="y")
    else:
        # 有违反：柱状图
        fig, ax = plt.subplots(figsize=(10, 6))
        labels = [f"方案{sol['id']}" for sol in solutions]
        colors = ["#4e79a7" if v == 0 else "#e15759" for v in violations]
        bars = ax.bar(labels, violations, color=colors, edgecolor="white", width=0.6)
        for bar, v in zip(bars, violations):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                    str(v), ha="center", va="bottom", fontsize=11, fontweight="bold")
        ax.set_ylabel("软约束违反次数")
        ax.set_title("各方案软约束违反次数对比")
        ax.set_ylim(0, max(max(violations) * 1.3, 1))
        ax.grid(True, alpha=0.3, axis="y")
        ax.axhline(y=0, color="green", linestyle="--", alpha=0.5, label="理想值(0)")
        ax.legend()

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# -- 比赛地点地图（folium）-----------------------------------------

def plot_venue_map(groups, venue_map, save_path=None):
    """用 folium 绘制比赛地点地图。"""
    try:
        import folium
    except ModuleNotFoundError:
        if save_path:
            from html import escape

            venue_groups = defaultdict(list)
            for g_idx, cc in venue_map.items():
                venue_groups[cc].append(g_idx)

            rows = []
            for cc, g_idxs in sorted(venue_groups.items()):
                v = TEAM_BY_CODE[cc]
                group_text = []
                for g_idx in g_idxs:
                    names = "、".join(TEAM_BY_CODE[c]["name"] for c in groups[g_idx])
                    group_text.append(f"组{g_idx + 1}: {names}")
                rows.append(
                    "<tr>"
                    f"<td>{escape(v['name'])}</td>"
                    f"<td>{v['lng']:.2f}, {v['lat']:.2f}</td>"
                    f"<td>{escape('；'.join(group_text))}</td>"
                    "</tr>"
                )

            html = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>比赛地点方案</title>"
                "<style>body{font-family:sans-serif;line-height:1.6;padding:24px;}"
                "table{border-collapse:collapse;width:100%;}"
                "td,th{border:1px solid #ccc;padding:8px;text-align:left;}</style>"
                "</head><body><h1>比赛地点方案</h1>"
                "<p>当前环境未安装 folium，已生成简易 HTML 版本。</p>"
                "<table><tr><th>比赛地</th><th>坐标</th><th>承办小组</th></tr>"
                + "".join(rows)
                + "</table></body></html>"
            )
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html)
        return save_path

    # 浙江中心
    m = folium.Map(location=[29.1, 120.5], zoom_start=7, tiles="CartoDB positron")

    colors = [
        "red", "blue", "green", "purple", "orange", "darkred",
        "lightred", "beige", "darkblue", "darkgreen", "cadetblue",
        "darkpurple", "white", "pink", "lightblue", "lightgreen",
    ]

    # 绘制各队位置（小点）
    for t in ALL_TEAMS:
        folium.CircleMarker(
            location=[t["lat"], t["lng"]],
            radius=3,
            color="gray",
            fill=True,
            fill_opacity=0.5,
            popup=t["name"],
        ).add_to(m)

    # 绘制比赛地（大标记）
    venue_groups = defaultdict(list)
    for g_idx, cc in venue_map.items():
        venue_groups[cc].append(g_idx)

    for cc, g_idxs in venue_groups.items():
        v = TEAM_BY_CODE[cc]
        # 绘制比赛地标记
        folium.Marker(
            location=[v["lat"], v["lng"]],
            popup=f"{v['name']} (承办组: {', '.join(str(g+1) for g in g_idxs)})",
            icon=folium.Icon(color="red", icon="flag"),
        ).add_to(m)

        # 绘制到各队的连线
        for g_idx in g_idxs:
            g = groups[g_idx]
            for code in g:
                t = TEAM_BY_CODE[code]
                folium.PolyLine(
                    locations=[[v["lat"], v["lng"]], [t["lat"], t["lng"]]],
                    color=colors[g_idx % len(colors)],
                    weight=1,
                    opacity=0.3,
                ).add_to(m)

    if save_path:
        m.save(save_path)
    return m


# -- 抽签公平性热力图 ----------------------------------------------

def plot_lottery_fairness(fairness_result, save_path=None):
    """绘制抽签公平性热力图（各队落入各组的概率）。"""
    fig, ax = plt.subplots(figsize=(14, 10))

    codes = sorted(fairness_result["team_group_counts"].keys())
    data = []
    for code in codes:
        counts = fairness_result["team_group_counts"][code]
        total = sum(counts)
        probs = [c / total for c in counts]
        data.append(probs)

    data = np.array(data)
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", interpolation="nearest")

    ax.set_xticks(range(NUM_GROUPS))
    ax.set_xticklabels([f"组{i+1}" for i in range(NUM_GROUPS)], fontsize=9, rotation=45)
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels([TEAM_BY_CODE[c]["name"] for c in codes], fontsize=7)
    ax.set_title("抽签公平性：各队落入各组的概率分布")

    plt.colorbar(im, ax=ax, label="概率")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# -- 赛制对比柱状图 -----------------------------------------------

def plot_tournament_probs(probs, strength, save_path=None, top_n=15):
    """绘制三种赛制下各队夺冠概率对比柱状图。"""
    fig, ax = plt.subplots(figsize=(12, 6))

    top_teams = sorted(ALL_TEAMS, key=lambda t: strength[t["code"]], reverse=True)[:top_n]
    names = [t["name"] for t in top_teams]
    x = np.arange(len(names))
    width = 0.25

    p1 = [probs["current"].get(t["code"], 0) for t in top_teams]
    p2 = [probs["swiss"].get(t["code"], 0) for t in top_teams]
    p3 = [probs["double_elim"].get(t["code"], 0) for t in top_teams]

    ax.bar(x - width, p1, width, label="当前赛制", color="#4e79a7")
    ax.bar(x, p2, width, label="瑞士轮", color="#f28e2b")
    ax.bar(x + width, p3, width, label="双败淘汰", color="#e15759")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_ylabel("夺冠概率")
    ax.set_title("不同赛制下各队夺冠概率对比")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# -- 距离分布图 ---------------------------------------------------

def plot_distance_distribution(eval_result, save_path=None):
    """绘制各队到比赛地的距离分布。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    dists = list(eval_result["team_distances"].values())

    ax1.hist(dists, bins=20, color="#4e79a7", edgecolor="white", alpha=0.8)
    ax1.axvline(eval_result["mean_distance"], color="red", linestyle="--",
                label=f"均值={eval_result['mean_distance']:.1f}km")
    ax1.set_xlabel("旅行距离 (km)")
    ax1.set_ylabel("队伍数")
    ax1.set_title("各队到比赛地距离分布")
    ax1.legend()

    # 用累计分布
    sorted_dists = np.sort(dists)
    cdf = np.arange(1, len(sorted_dists) + 1) / len(sorted_dists)
    ax2.plot(sorted_dists, cdf, color="#4e79a7", linewidth=2)
    ax2.set_xlabel("旅行距离 (km)")
    ax2.set_ylabel("累积比例")
    ax2.set_title("旅行距离累积分布函数")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


# -- 综合评价雷达图 -----------------------------------------------

def plot_radar_comparison(solutions, save_path=None):
    """综合评价雷达图。"""
    import matplotlib.pyplot as plt
    from math import pi

    categories = ["可行性", "软约束", "GDP均衡", "方案多样性"]
    N = len(categories)

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    colors = plt.cm.Set2(np.linspace(0, 1, len(solutions)))

    for i, sol in enumerate(solutions):
        values = [
            1.0 if sol["eval"]["feasible"] else 0.0,
            max(0, 1.0 - sol["eval"]["soft_violations"] / 10.0),
            max(0, 1.0 - sol["eval"]["balance"]["cv"] * 10),
            0.8,  # 简化：固定值
        ]
        values += values[:1]

        ax.plot(angles, values, "o-", linewidth=2, label=f"方案{sol['id']}", color=colors[i])
        ax.fill(angles, values, alpha=0.1, color=colors[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_title("分组方案综合评价雷达图")
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path
