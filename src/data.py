# src/data.py
# 浙江省市县联赛参赛队伍数据

# 1. 市级队列表（11个设区市）
MUNICIPAL_TEAMS = [
    {"city": "杭州", "type": "municipal"},
    {"city": "宁波", "type": "municipal"},
    {"city": "温州", "type": "municipal"},
    {"city": "绍兴", "type": "municipal"},
    {"city": "湖州", "type": "municipal"},
    {"city": "嘉兴", "type": "municipal"},
    {"city": "金华", "type": "municipal"},
    {"city": "衢州", "type": "municipal"},
    {"city": "舟山", "type": "municipal"},
    {"city": "台州", "type": "municipal"},
    {"city": "丽水", "type": "municipal"},
]

# 2. 县级队列表（按实际53个县补充完整，这里先放示例）
COUNTY_TEAMS = [
    # 杭州代管县级队
    {"city": "杭州", "county": "桐庐", "type": "county"},
    {"city": "杭州", "county": "淳安", "type": "county"},
    {"city": "杭州", "county": "建德", "type": "county"},
    # 宁波代管县级队
    {"city": "宁波", "county": "余姚", "type": "county"},
    {"city": "宁波", "county": "慈溪", "type": "county"},
    {"city": "宁波", "county": "奉化", "type": "county"},
    {"city": "宁波", "county": "象山", "type": "county"},sss
    {"city": "宁波", "county": "宁海", "type": "county"},
    # 温州代管县级队
    {"city": "温州", "county": "瑞安", "type": "county"},
    {"city": "温州", "county": "乐清", "type": "county"},
    {"city": "温州", "county": "永嘉", "type": "county"},
    {"city": "温州", "county": "平阳", "type": "county"},
    {"city": "温州", "county": "苍南", "type": "county"},
    {"city": "温州", "county": "文成", "type": "county"},
    {"city": "温州", "county": "泰顺", "type": "county"},
    # 绍兴代管县级队
    {"city": "绍兴", "county": "诸暨", "type": "county"},
    {"city": "绍兴", "county": "上虞", "type": "county"},
    {"city": "绍兴", "county": "嵊州", "type": "county"},
    {"city": "绍兴", "county": "新昌", "type": "county"},
]

# 3. 合并所有队伍
ALL_TEAMS = MUNICIPAL_TEAMS + COUNTY_TEAMS

if __name__ == "__main__":
    print(f"市级队数量：{len(MUNICIPAL_TEAMS)}")
    print(f"县级队数量：{len(COUNTY_TEAMS)}")
    print(f"总队伍数量：{len(ALL_TEAMS)}")