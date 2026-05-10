"""
浙江省64支参赛队伍数据（11市 + 53县/市）

数据来源：浙江省行政区划（2025年），国家统计局2024年GDP数据
坐标系：WGS84 (经度, 纬度)

问题原文（附录）：
杭州市，代管建德市、桐庐县、淳安县
宁波市，代管余姚市、慈溪市、象山县、宁海县
温州市，代管瑞安市、乐清市、龙港市、永嘉县、平阳县、苍南县、文成县、泰顺县
嘉兴市，代管海宁市、平湖市、桐乡市、嘉善县、海盐县
湖州市，代管德清县、长兴县、安吉县
绍兴市，代管诸暨市、嵊州市、新昌县
金华市，代管兰溪市、义乌市、东阳市、永康市、武义县、浦江县、磐安县
衢州市，代管江山市、常山县、开化县、龙游县
舟山市，代管岱山县、嵊泗县
台州市，代管温岭市、临海市、玉环市、三门县、天台县、仙居县
丽水市，代管龙泉市、青田县、缙云县、遂昌县、松阳县、云和县、庆元县、景宁畲族自治县
"""

# -- 市级队 ----------------------------------------------------------
# (city_code, name, lng, lat, gdp_yi_元, is_city)
MUNICIPAL = [
    ("hangzhou",   "杭州",  120.15, 30.28, 21980, True),
    ("ningbo",     "宁波",  121.55, 29.87, 16954, True),
    ("wenzhou",    "温州",  120.65, 28.00,  8730, True),
    ("jiaxing",    "嘉兴",  120.75, 30.77,  7062, True),
    ("huzhou",     "湖州",  120.08, 30.89,  4015, True),
    ("shaoxing",   "绍兴",  120.58, 30.00,  7620, True),
    ("jinhua",     "金华",  119.65, 29.08,  6012, True),
    ("quzhou",     "衢州",  118.87, 28.93,  2125, True),
    ("zhoushan",   "舟山",  122.10, 30.00,  2053, True),
    ("taizhou",    "台州",  121.42, 28.65,  6587, True),
    ("lishui",     "丽水",  119.91, 28.45,  1962, True),
]

# -- 县/市级队（按所属市分组）-----------------------------------------
# (code, name, lng, lat, gdp_yi_元, parent_city)
# 数据按题目附录行政区划逐一对应
COUNTY = [
    # 杭州市代管 (3)
    ("jiande",     "建德",  119.28, 29.47,  430, "hangzhou"),
    ("tonglu",     "桐庐",  119.67, 29.80,  460, "hangzhou"),
    ("chunan",     "淳安",  119.05, 29.61,  280, "hangzhou"),

    # 宁波市代管 (4)
    ("yuyao",      "余姚",  121.15, 30.03, 1580, "ningbo"),
    ("cixi",       "慈溪",  121.23, 30.17, 2520, "ningbo"),
    ("xiangshan",  "象山",  121.87, 29.48,  720, "ningbo"),
    ("ninghai",    "宁海",  121.43, 29.29,  880, "ningbo"),

    # 温州市代管 (8)
    ("ruian",      "瑞安",  120.63, 27.78, 1230, "wenzhou"),
    ("leqing",     "乐清",  120.98, 28.12, 1500, "wenzhou"),
    ("longgang",   "龙港",  120.55, 27.58,  420, "wenzhou"),
    ("yongjia",    "永嘉",  120.69, 28.15,  560, "wenzhou"),
    ("pingyang",   "平阳",  120.57, 27.67,  640, "wenzhou"),
    ("cangnan",    "苍南",  120.43, 27.52,  520, "wenzhou"),
    ("wencheng",   "文成",  120.09, 27.79,  160, "wenzhou"),
    ("taishun",    "泰顺",  119.72, 27.56,  150, "wenzhou"),

    # 嘉兴市代管 (5)
    ("haining",    "海宁",  120.69, 30.53, 1200, "jiaxing"),
    ("pinghu",     "平湖",  121.01, 30.70,  850, "jiaxing"),
    ("tongxiang",  "桐乡",  120.56, 30.63, 1050, "jiaxing"),
    ("jiashan",    "嘉善",  120.92, 30.84,  830, "jiaxing"),
    ("haiyan",     "海盐",  120.94, 30.53,  620, "jiaxing"),

    # 湖州市代管 (3)
    ("deqing",     "德清",  119.97, 30.54,  650, "huzhou"),
    ("changxing",  "长兴",  119.91, 31.02,  820, "huzhou"),
    ("anji",       "安吉",  119.68, 30.63,  580, "huzhou"),

    # 绍兴市代管 (3)
    ("zhuji",      "诸暨",  120.23, 29.71, 1500, "shaoxing"),
    ("shengzhou",  "嵊州",  120.82, 29.59,  720, "shaoxing"),
    ("xinchang",   "新昌",  120.90, 29.50,  500, "shaoxing"),

    # 金华市代管 (7)
    ("lanxi",      "兰溪",  119.48, 29.21,  430, "jinhua"),
    ("yiwu",       "义乌",  120.07, 29.31, 2050, "jinhua"),
    ("dongyang",   "东阳",  120.23, 29.28,  780, "jinhua"),
    ("yongkang",   "永康",  120.02, 28.92,  720, "jinhua"),
    ("wuyi",       "武义",  119.81, 28.89,  340, "jinhua"),
    ("pujiang",    "浦江",  119.89, 29.45,  310, "jinhua"),
    ("panan",      "磐安",  120.45, 29.06,  160, "jinhua"),

    # 衢州市代管 (4)
    ("jiangshan",  "江山",  118.62, 28.74,  360, "quzhou"),
    ("changshan",  "常山",  118.51, 28.90,  210, "quzhou"),
    ("kaihua",     "开化",  118.41, 29.14,  180, "quzhou"),
    ("longyou",    "龙游",  119.17, 29.03,  280, "quzhou"),

    # 舟山市代管 (2)
    ("daishan",    "岱山",  122.20, 30.24,  300, "zhoushan"),
    ("shengsi",    "嵊泗",  122.45, 30.73,  110, "zhoushan"),

    # 台州市代管 (6)
    ("wenling",    "温岭",  121.37, 28.37, 1280, "taizhou"),
    ("linhai",     "临海",  121.12, 28.85,  870, "taizhou"),
    ("yuhuan",     "玉环",  121.23, 28.13,  760, "taizhou"),
    ("sanmen",     "三门",  121.39, 29.10,  330, "taizhou"),
    ("tiantai",    "天台",  121.00, 29.14,  350, "taizhou"),
    ("xianju",     "仙居",  120.73, 28.85,  320, "taizhou"),

    # 丽水市代管 (8)
    ("longquan",   "龙泉",  119.14, 28.07,  230, "lishui"),
    ("qingtian",   "青田",  120.29, 28.14,  310, "lishui"),
    ("jinyun",     "缙云",  120.07, 28.66,  310, "lishui"),
    ("suichang",   "遂昌",  119.27, 28.59,  170, "lishui"),
    ("songyang",   "松阳",  119.48, 28.45,  190, "lishui"),
    ("yunhe",      "云和",  119.57, 28.12,  110, "lishui"),
    ("qingyuan",   "庆元",  119.06, 27.61,  130, "lishui"),
    ("jingning",   "景宁",  119.63, 27.98,  110, "lishui"),
]

# -- 合并为统一列表 --------------------------------------------------
ALL_TEAMS = []
for code, name, lng, lat, gdp, is_city in MUNICIPAL:
    ALL_TEAMS.append({
        "code": code,
        "name": name,
        "lng": lng,
        "lat": lat,
        "gdp": gdp,
        "is_city": True,
        "parent": None,
    })

for code, name, lng, lat, gdp, parent in COUNTY:
    ALL_TEAMS.append({
        "code": code,
        "name": name,
        "lng": lng,
        "lat": lat,
        "gdp": gdp,
        "is_city": False,
        "parent": parent,
    })

# -- 快速索引 ------------------------------------------------------
TEAM_BY_CODE = {t["code"]: t for t in ALL_TEAMS}
CITY_CODES = [c[0] for c in MUNICIPAL]
COUNTY_CODES = [c[0] for c in COUNTY]
PARENT_MAP = {c[0]: c[5] for c in COUNTY}  # county_code → city_code

# 城市 → 代管县列表
CITY_CHILDREN = {}
for t in ALL_TEAMS:
    if t["is_city"]:
        CITY_CHILDREN[t["code"]] = []
for code, name, lng, lat, gdp, parent in COUNTY:
    CITY_CHILDREN[parent].append(code)

NUM_GROUPS = 16
GROUP_SIZE = 4
NUM_TEAMS = 64
NUM_CITIES = 11
NUM_COUNTIES = 53


def get_coords_matrix():
    """返回 64×2 坐标矩阵 (lng, lat)，按 ALL_TEAMS 顺序。"""
    import numpy as np
    return np.array([[t["lng"], t["lat"]] for t in ALL_TEAMS])


def get_city_coords():
    """返回 11×2 市级队坐标矩阵。"""
    import numpy as np
    return np.array([[t["lng"], t["lat"]] for t in ALL_TEAMS if t["is_city"]])


def haversine_km(lng1, lat1, lng2, lat2):
    """Haversine公式计算两点间球面距离(km)。"""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))
