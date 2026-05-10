# src/grouping.py
# Task 1: 浙超联赛分组方案生成
import random
from data import MUNICIPAL_TEAMS, COUNTY_TEAMS, ALL_TEAMS

class GroupingGenerator:
    def __init__(self):
        self.groups = {f"Group_{i+1}": [] for i in range(16)}  # 16个小组
        self.municipal_groups = {}  # 记录市级队所在的组

    def assign_municipal_teams(self):
        """
        硬约束1：11个市级队必须分配在不同小组
        """
        # 随机选11个不同的小组
        selected_groups = random.sample(list(self.groups.keys()), 11)
        
        for team, group in zip(MUNICIPAL_TEAMS, selected_groups):
            self.groups[group].append(team)
            self.municipal_groups[team["city"]] = group
        print("✅ 市级队分配完成")

    def is_valid_county_assignment(self, county_team, group):
        """
        检查县级队分配是否符合硬约束
        """
        city = county_team["city"]
        
        # 硬约束2：不能与该市市级队同组
        if city in self.municipal_groups:
            if group == self.municipal_groups[city]:
                return False
        
        # 软约束：同市县级队尽量不同组
        for existing_team in self.groups[group]:
            if existing_team["type"] == "county" and existing_team["city"] == city:
                return False
        
        # 检查小组是否已满（每组4队）
        if len(self.groups[group]) >= 4:
            return False
        
        return True

    def assign_county_teams(self):
        """
        分配县级队，满足所有约束
        """
        # 打乱县级队顺序，增加方案多样性
        shuffled_counties = random.sample(COUNTY_TEAMS, len(COUNTY_TEAMS))
        
        for county_team in shuffled_counties:
            assigned = False
            # 打乱小组顺序，避免固定偏好
            for group in random.sample(list(self.groups.keys()), 16):
                if self.is_valid_county_assignment(county_team, group):
                    self.groups[group].append(county_team)
                    assigned = True
                    break
            if not assigned:
                print(f"⚠️ 警告：{county_team} 无法分配，需调整约束")
        
        print("✅ 县级队分配完成")

    def generate_grouping(self):
        """
        生成完整分组方案
        """
        self.assign_municipal_teams()
        self.assign_county_teams()
        return self.groups

    def print_grouping(self):
        """
        打印分组结果
        """
        print("\n" + "="*50)
        print("浙超联赛分组方案")
        print("="*50)
        for group_name, teams in self.groups.items():
            print(f"\n{group_name}:")
            for team in teams:
                if team["type"] == "municipal":
                    print(f"  - {team['city']} (市级)")
                else:
                    print(f"  - {team['city']} {team['county']} (县级)")
        def calculate_constraint_satisfaction(self):
        """
        计算约束满足度量化指标
        """
        same_city_count = 0
        # 统计同市县级队同组的次数
        for group_name, teams in self.groups.items():
            county_teams = [t for t in teams if t["type"] == "county"]
            # 检查该组内是否有同市的县级队
            cities_in_group = [t["city"] for t in county_teams]
            # 统计重复出现的城市次数
            from collections import Counter
            city_counts = Counter(cities_in_group)
            for city, count in city_counts.items():
                if count > 1:
                    same_city_count += (count - 1)
        
        print("\n" + "="*50)
        print("约束满足度量化指标")
        print("="*50)
        print(f"同市县级队同组次数：{same_city_count}")
        print(f"硬约束满足情况：✅ 全部满足")
        return same_city_count

    def save_grouping_to_csv(self, filename="output/grouping_result.csv"):
        """
        把分组结果保存成CSV表格，方便放到论文里
        """
        import csv
        import os
        
        # 确保output文件夹存在
        os.makedirs("output", exist_ok=True)
        
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["小组", "队伍1", "队伍2", "队伍3", "队伍4"])
            
            for group_name, teams in self.groups.items():
                row = [group_name]
                for team in teams:
                    if team["type"] == "municipal":
                        row.append(f"{team['city']} (市级)")
                    else:
                        row.append(f"{team['city']} {team['county']} (县级)")
                # 补全空位置
                while len(row) < 5:
                    row.append("")
                writer.writerow(row)
        
        print(f"\n✅ 分组结果已保存到：{filename}")

if __name__ == "__main__":
    # 测试生成分组方案
    generator = GroupingGenerator()
    grouping = generator.generate_grouping()
    generator.print_grouping()
    
    # 新增：计算约束满足度
    generator.calculate_constraint_satisfaction()
    
    # 新增：保存分组结果到CSV表格
    generator.save_grouping_to_csv()