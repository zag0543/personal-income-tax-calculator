#!/usr/bin/env python3
"""
扣除项体检报告
交互式问卷收集用户信息，诊断九项扣除项使用情况，生成体检报告

v2.1.0 新增功能：
- 九项扣除诊断逻辑
- 交互式问卷流程
- 体检报告生成
- JSON非交互模式支持
"""

import json
import argparse
import sys
import os
from datetime import datetime

# ============================================================
# 九项扣除政策定义
# ============================================================

DEDUCTION_POLICIES = {
    'children_education': {
        'name': '子女教育',
        'name_short': '👶 子女教育',
        'standard': '每个子女 1,000元/月（12,000元/年）',
        'condition': '正接受学历教育（3岁至学历教育结束）',
        'detail': '学前教育至博士研究生，父母可选择一方100%或双方各50%扣除'
    },
    'infant_care': {
        'name': '3岁以下婴幼儿照护',
        'name_short': '👶 3岁以下婴幼儿照护',
        'standard': '每个婴幼儿 1,000元/月（12,000元/年）',
        'condition': '0-3岁婴幼儿的监护人',
        'detail': '与子女教育扣除类似，可单独享受或与子女教育叠加'
    },
    'continuing_education': {
        'name': '继续教育',
        'name_short': '📚 继续教育',
        'standard': '学历教育400元/月；职业资格证书3,600元/次',
        'condition': '正在接受学历教育或取证年度',
        'detail': '学历教育本人扣除；职业证书本人扣除，当年有效'
    },
    'medical_expense': {
        'name': '大病医疗',
        'name_short': '🏥 大病医疗',
        'standard': '医保内自付超过15,000元部分，限额85,000元/年',
        'condition': '医保定点医疗机构，医保目录内自付',
        'detail': '可本人或配偶扣除；未成年子女由父母扣除'
    },
    'housing_loan': {
        'name': '住房贷款利息',
        'name_short': '🏠 住房贷款利息',
        'standard': '1,000元/月（12,000元/年）',
        'condition': '首套商业住房或公积金贷款',
        'detail': '婚后可选择一方扣除或双方各50%'
    },
    'housing_rent': {
        'name': '住房租金',
        'name_short': '🏠 住房租金',
        'standard': '一线城市1,500元/月；其他城市800-1,100元/月',
        'condition': '在工作城市无自有住房租房',
        'detail': '与房贷利息不可同时享受；需租赁合同'
    },
    'elderly_support': {
        'name': '赡养老人',
        'name_short': '👴👵 赡养老人',
        'standard': '独生子女3,000元/月；非独生子女分摊≤1,500元/月',
        'condition': '年满60岁的父母（或祖父母、外祖父母）',
        'detail': '可指定分摊或兄弟姐妹约定'
    },
    'personal_pension': {
        'name': '个人养老金',
        'name_short': '💰 个人养老金',
        'standard': '实际缴存金额，限额12,000元/年',
        'condition': '试点城市开立账户并缴存',
        'detail': '汇算时自行填报；不同税率节税效果不同'
    },
    'tax_health': {
        'name': '税优健康险',
        'name_short': '🏥 税优健康险',
        'standard': '每年保费，限额2,400元/年（200元/月）',
        'condition': '购买符合规定的税优健康险产品',
        'detail': '由投保人扣除'
    }
}

# 城市租金标准
RENT_STANDARDS = {
    'tier1': {'name': '北京、上海、广州、深圳', 'monthly': 1500, 'annual': 18000},
    'provincial': {'name': '省会城市/直辖市', 'monthly': 1100, 'annual': 13200},
    'other': {'name': '其他城市', 'monthly': 800, 'annual': 9600}
}


class DeductionCheckupCollector:
    """扣除项体检信息采集器"""
    
    def __init__(self):
        self.data = {}
        self.diagnosis = {}
        
    def load_from_json(self, json_data):
        """从JSON加载数据"""
        self.data = json_data
        self.diagnosis = self._diagnose()
        
    def collect_interactive(self):
        """交互式采集信息"""
        print("\n" + "="*60)
        print("🔍 个税扣除项体检 - 信息采集")
        print("="*60)
        print("\n欢迎使用扣除项体检功能！")
        print("我将帮助您检查是否有遗漏的专项附加扣除。")
        print("请按步骤回答以下问题（输入数字选择，或直接填写）：\n")
        
        # 第一步：基本信息
        print("📋 第一步：基本信息")
        print("-" * 40)
        
        income_options = [
            "6万元以下",
            "6-12万元",
            "12-20万元",
            "20-36万元",
            "36万元以上"
        ]
        for i, opt in enumerate(income_options, 1):
            print(f"  {i}. {opt}")
        
        while True:
            try:
                choice = input("\n您的年收入大概是多少？[1-5]: ").strip()
                idx = int(choice) - 1
                if 0 <= idx < 5:
                    break
            except ValueError:
                pass
            print("请输入1-5之间的数字")
        
        income_ranges = [(0, 60000), (60000, 120000), (120000, 200000), 
                         (200000, 360000), (360000, float('inf'))]
        self.data['annual_income'] = income_ranges[idx]
        
        # 第二步：家庭与住房
        print("\n📋 第二步：家庭与住房")
        print("-" * 40)
        
        # 3岁以下子女
        while True:
            choice = input("您是否有3岁以下的子女？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                try:
                    count = int(input("有几个？(1-9): ").strip())
                    self.data['infant_children'] = max(1, min(9, count))
                except ValueError:
                    self.data['infant_children'] = 1
                break
            elif choice in ['n', 'no', '否', '']:
                self.data['infant_children'] = 0
                break
            print("请输入 y 或 n")
        
        # 学历教育子女
        while True:
            choice = input("\n您是否有正接受学历教育的子女（3岁以上在校生）？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                try:
                    count = int(input("有几个？(1-9): ").strip())
                    self.data['school_children'] = max(1, min(9, count))
                except ValueError:
                    self.data['school_children'] = 1
                break
            elif choice in ['n', 'no', '否', '']:
                self.data['school_children'] = 0
                break
            print("请输入 y 或 n")
        
        # 赡养老人
        while True:
            choice = input("\n您是否有60岁以上的父母需要赡养？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                self.data['elderly_parents'] = True
                while True:
                    solo = input("您是否为独生子女？(y/n): ").strip().lower()
                    if solo in ['y', 'yes', '是', '']:
                        self.data['is_only_child'] = True
                        break
                    elif solo in ['n', 'no', '否']:
                        self.data['is_only_child'] = False
                        try:
                            sibs = int(input("兄弟姐妹共有几人？(包括您): ").strip())
                            self.data['sibling_count'] = max(2, min(10, sibs))
                        except ValueError:
                            self.data['sibling_count'] = 2
                        break
                    print("请输入 y 或 n")
                break
            elif choice in ['n', 'no', '否', '']:
                self.data['elderly_parents'] = False
                self.data['is_only_child'] = False
                break
            print("请输入 y 或 n")
        
        # 住房情况
        print("\n🏠 住房情况")
        housing_options = ["自有住房（有房贷）", "自有住房（无房贷）", "租房", "其他"]
        for i, opt in enumerate(housing_options, 1):
            print(f"  {i}. {opt}")
        
        while True:
            try:
                choice = input("\n您目前的住房情况是？[1-4]: ").strip()
                idx = int(choice) - 1
                if 0 <= idx < 4:
                    break
            except ValueError:
                pass
            print("请输入1-4之间的数字")
        
        self.data['housing_type'] = ['housing_loan', 'own_no_loan', 'rent', 'other'][idx]
        
        # 第三步：教育与健康
        print("\n📋 第三步：教育与健康")
        print("-" * 40)
        
        # 学历继续教育
        while True:
            choice = input("您目前是否正在接受学历继续教育（在职研究生等）？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                self.data['study_continuing'] = True
                break
            elif choice in ['n', 'no', '否', '']:
                self.data['study_continuing'] = False
                break
            print("请输入 y 或 n")
        
        # 职业资格证书
        while True:
            choice = input("\n您今年是否取得了职业资格证书？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                self.data['has_cert'] = True
                cert = input("请输入证书名称（可选，直接回车跳过）: ").strip()
                self.data['cert_name'] = cert if cert else "职业资格证书"
                break
            elif choice in ['n', 'no', '否', '']:
                self.data['has_cert'] = False
                self.data['cert_name'] = ""
                break
            print("请输入 y 或 n")
        
        # 大病医疗
        print("\n🏥 大病医疗（医保目录内自付金额）")
        medical_options = ["1.5万元以下", "1.5-3万元", "3-6万元", "6万元以上", "不清楚"]
        for i, opt in enumerate(medical_options, 1):
            print(f"  {i}. {opt}")
        
        while True:
            try:
                choice = input("今年医保目录内自付金额大概多少？[1-5]: ").strip()
                idx = int(choice) - 1
                if 0 <= idx < 5:
                    break
            except ValueError:
                pass
            print("请输入1-5之间的数字")
        
        medical_ranges = [(0, 15000), (15000, 30000), (30000, 60000), 
                         (60000, float('inf')), (0, 0)]
        self.data['medical_expense'] = medical_ranges[idx]
        
        # 第四步：保障类支出
        print("\n📋 第四步：保障类支出")
        print("-" * 40)
        
        # 个人养老金
        while True:
            choice = input("您是否开通了个人养老金账户并缴存？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                self.data['has_pension'] = True
                try:
                    amount = input("今年缴存金额是多少元？(直接回车默认12000): ").strip()
                    self.data['pension_amount'] = int(amount) if amount else 12000
                except ValueError:
                    self.data['pension_amount'] = 12000
                break
            elif choice in ['n', 'no', '否', '']:
                self.data['has_pension'] = False
                self.data['pension_amount'] = 0
                break
            print("请输入 y 或 n")
        
        # 税优健康险
        while True:
            choice = input("\n您是否购买了税优健康险？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                self.data['has_tax_health'] = True
                try:
                    amount = input("每年保费大概多少元？(直接回车默认2400): ").strip()
                    self.data['tax_health_amount'] = int(amount) if amount else 2400
                except ValueError:
                    self.data['tax_health_amount'] = 2400
                break
            elif choice in ['n', 'no', '否', '']:
                self.data['has_tax_health'] = False
                self.data['tax_health_amount'] = 0
                break
            print("请输入 y 或 n")
        
        # 第五步：工作与租金
        print("\n📋 第五步：工作与租金")
        print("-" * 40)
        
        if self.data.get('housing_type') == 'rent':
            print("您租房所在城市类型：")
            city_options = [
                "北京、上海、广州、深圳",
                "其他省会城市/直辖市",
                "其他城市"
            ]
            for i, opt in enumerate(city_options, 1):
                print(f"  {i}. {opt}")
            
            while True:
                try:
                    choice = input("\n请选择：[1-3]: ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < 3:
                        break
                except ValueError:
                    pass
                print("请输入1-3之间的数字")
            
            self.data['city_type'] = ['tier1', 'provincial', 'other'][idx]
            
            while True:
                choice = input("您的工作地与户籍所在地是否在同一城市？(y/n): ").strip().lower()
                if choice in ['y', 'yes', '是', '']:
                    self.data['same_city'] = True
                    break
                elif choice in ['n', 'no', '否']:
                    self.data['same_city'] = False
                    break
                print("请输入 y 或 n")
        
        # 执行诊断
        self.diagnosis = self._diagnose()
    
    def _diagnose(self):
        """执行九项扣除诊断"""
        diagnosis = {
            'enjoyed': [],      # 已享受的
            'possible_missed': [],  # 可能遗漏的
            'not_applicable': [],   # 不适用
            'total_missed': 0,      # 可能遗漏总额
            'potential_savings': 0  # 潜在节税金额
        }
        
        income = self.data.get('annual_income', 0)
        # 支持整数或元组格式
        if isinstance(income, (int, float)):
            avg_income = income
        elif isinstance(income, (list, tuple)) and len(income) >= 2:
            avg_income = (income[0] + income[1]) / 2 if income[1] != float('inf') else income[0]
        else:
            avg_income = 0
        
        # 根据收入估算税率
        if avg_income <= 36000:
            tax_rate = 0.03
        elif avg_income <= 144000:
            tax_rate = 0.10
        elif avg_income <= 300000:
            tax_rate = 0.20
        elif avg_income <= 420000:
            tax_rate = 0.25
        elif avg_income <= 660000:
            tax_rate = 0.30
        else:
            tax_rate = 0.35
        
        self.data['estimated_tax_rate'] = tax_rate
        
        # 1. 子女教育
        school_children = self.data.get('school_children', 0)
        if school_children > 0:
            amount = school_children * 12000
            diagnosis['possible_missed'].append({
                'type': 'children_education',
                'amount': amount,
                'reason': f'您有{school_children}个正接受学历教育的子女',
                'action': '进入"子女教育" → 添加子女信息 → 选择扣除比例',
                'savings': amount * tax_rate
            })
            diagnosis['total_missed'] += amount
            diagnosis['potential_savings'] += amount * tax_rate
        
        # 2. 3岁以下婴幼儿照护
        infant_children = self.data.get('infant_children', 0)
        if infant_children > 0:
            amount = infant_children * 12000
            diagnosis['possible_missed'].append({
                'type': 'infant_care',
                'amount': amount,
                'reason': f'您有{infant_children}个3岁以下婴幼儿',
                'action': '进入"3岁以下婴幼儿照护" → 添加子女信息',
                'savings': amount * tax_rate
            })
            diagnosis['total_missed'] += amount
            diagnosis['potential_savings'] += amount * tax_rate
        
        # 3. 继续教育
        study_cont = self.data.get('study_continuing', False)
        has_cert = self.data.get('has_cert', False)
        
        if study_cont:
            amount = 4800  # 400*12
            diagnosis['possible_missed'].append({
                'type': 'continuing_education_study',
                'amount': amount,
                'reason': '您正在接受学历继续教育',
                'action': '进入"继续教育" → 选择学历教育',
                'savings': amount * tax_rate
            })
            diagnosis['total_missed'] += amount
            diagnosis['potential_savings'] += amount * tax_rate
        
        if has_cert:
            amount = 3600
            cert_name = self.data.get('cert_name', '职业资格证书')
            diagnosis['possible_missed'].append({
                'type': 'continuing_education_cert',
                'amount': amount,
                'reason': f'您今年取得了{cert_name}',
                'action': f'进入"继续教育" → 填写证书信息（证书名称：{cert_name}）',
                'savings': amount * tax_rate,
                'warning': '职业资格证书须在取证年度申报，过期不可补报！'
            })
            diagnosis['total_missed'] += amount
            diagnosis['potential_savings'] += amount * tax_rate
        
        # 4. 大病医疗
        medical = self.data.get('medical_expense', 0)
        # 支持整数或元组格式
        if isinstance(medical, (int, float)):
            medical_total = medical
        elif isinstance(medical, (list, tuple)) and len(medical) >= 2:
            medical_total = (medical[0] + medical[1]) / 2 if medical[1] != float('inf') else medical[0]
        else:
            medical_total = 0
        
        if medical_total > 15000:
            deductable = min(medical_total - 15000, 85000)
            diagnosis['possible_missed'].append({
                'type': 'medical_expense',
                'amount': deductable,
                'reason': f'医保目录内自付约{medical_total:.0f}元，超过起付线',
                'action': '汇算时进入"大病医疗"填报实际支出',
                'savings': deductable * tax_rate
            })
            diagnosis['total_missed'] += deductable
            diagnosis['potential_savings'] += deductable * tax_rate
        elif medical_total > 0:
            remaining = 15000 - medical_total
            diagnosis['not_applicable'].append({
                'type': 'medical_expense',
                'reason': f'自付约{medical_total:.0f}元，距起付线还差约{remaining:.0f}元',
                'suggestion': '如有大病支出，可在明年汇算时补充填报'
            })
        
        # 5. 住房贷款利息
        housing_type = self.data.get('housing_type', '')
        if housing_type == 'housing_loan':
            amount = 12000
            diagnosis['possible_missed'].append({
                'type': 'housing_loan',
                'amount': amount,
                'reason': '您有首套住房贷款',
                'action': '进入"住房贷款利息" → 填写贷款信息',
                'savings': amount * tax_rate
            })
            diagnosis['total_missed'] += amount
            diagnosis['potential_savings'] += amount * tax_rate
        elif housing_type == 'own_no_loan':
            diagnosis['not_applicable'].append({
                'type': 'housing_loan',
                'reason': '您有自有住房且无贷款',
                'suggestion': '住房贷款利息与租金不可同时享受'
            })
        
        # 6. 住房租金
        if housing_type == 'rent':
            city_type = self.data.get('city_type', 'other')
            same_city = self.data.get('same_city', True)
            
            if not same_city:
                amount = RENT_STANDARDS[city_type]['annual']
                city_name = RENT_STANDARDS[city_type]['name']
                diagnosis['possible_missed'].append({
                    'type': 'housing_rent',
                    'amount': amount,
                    'reason': f'您在{city_name}租房，工作地与户籍不同城市',
                    'action': '进入"住房租金" → 填写租赁信息',
                    'savings': amount * tax_rate,
                    'note': f'标准：{RENT_STANDARDS[city_type]["monthly"]}元/月'
                })
                diagnosis['total_missed'] += amount
                diagnosis['potential_savings'] += amount * tax_rate
            else:
                diagnosis['not_applicable'].append({
                    'type': 'housing_rent',
                    'reason': '工作地与户籍在同一城市',
                    'suggestion': '如在外租房且无自有住房，可考虑填报'
                })
        elif housing_type == 'other':
            diagnosis['not_applicable'].append({
                'type': 'housing_rent',
                'reason': '未选择租房',
                'suggestion': '租金扣除需在工作城市无自有住房'
            })
        
        # 7. 赡养老人
        if self.data.get('elderly_parents', False):
            if self.data.get('is_only_child', False):
                amount = 36000
                diagnosis['possible_missed'].append({
                    'type': 'elderly_support',
                    'amount': amount,
                    'reason': '您是独生子女，父母已满60岁',
                    'action': '进入"赡养老人" → 填写被赡养人信息 → 确认独生子女',
                    'savings': amount * tax_rate,
                    'materials': ['父母身份证号码', '独生子女证明']
                })
            else:
                sibs = self.data.get('sibling_count', 2)
                amount = min(36000 // sibs, 18000)
                diagnosis['possible_missed'].append({
                    'type': 'elderly_support',
                    'amount': amount,
                    'reason': f'您有{sibs}个兄弟姐妹，需分摊赡养扣除',
                    'action': '进入"赡养老人" → 填写被赡养人信息 → 与兄弟姐妹协商分摊',
                    'savings': amount * tax_rate,
                    'materials': ['父母身份证号码', '分摊协议（如非独生子女）']
                })
            diagnosis['total_missed'] += amount
            diagnosis['potential_savings'] += amount * tax_rate
        
        # 8. 个人养老金
        if self.data.get('has_pension', False):
            amount = min(self.data.get('pension_amount', 0), 12000)
            if amount > 0:
                diagnosis['possible_missed'].append({
                    'type': 'personal_pension',
                    'amount': amount,
                    'reason': '您已开通个人养老金账户并缴存',
                    'action': '汇算时进入"个人养老金" → 录入缴费凭证',
                    'savings': amount * tax_rate,
                    'tax_benefit': f'按{tax_rate*100:.0f}%税率，每年可节税{amount * tax_rate:.0f}元'
                })
                diagnosis['total_missed'] += amount
                diagnosis['potential_savings'] += amount * tax_rate
        else:
            diagnosis['not_applicable'].append({
                'type': 'personal_pension',
                'reason': '尚未开通个人养老金账户',
                'suggestion': '建议考虑开通，特别适合高税率人群'
            })
        
        # 9. 税优健康险
        if self.data.get('has_tax_health', False):
            amount = min(self.data.get('tax_health_amount', 0), 2400)
            if amount > 0:
                diagnosis['possible_missed'].append({
                    'type': 'tax_health',
                    'amount': amount,
                    'reason': '您已购买税优健康险',
                    'action': '进入"税优健康险" → 录入保单信息',
                    'savings': amount * tax_rate
                })
                diagnosis['total_missed'] += amount
                diagnosis['potential_savings'] += amount * tax_rate
        
        return diagnosis
    
    def generate_report(self) -> str:
        """生成体检报告"""
        today = datetime.now().strftime('%Y年%m月%d日')
        tax_rate = self.data.get('estimated_tax_rate', 0.20)
        
        # 获取收入范围描述
        income = self.data.get('annual_income', 0)
        if isinstance(income, (int, float)):
            income_desc = f"{income//10000}万元"
        elif isinstance(income, (list, tuple)) and len(income) >= 2:
            if income[1] == float('inf'):
                income_desc = f"{income[0]//10000}万元以上"
            else:
                income_desc = f"{income[0]//10000}-{income[1]//10000}万元"
        else:
            income_desc = "未填写"
        
        report = []
        report.append("=" * 66)
        report.append("║            🔍 您的个税扣除项体检报告                      ║")
        report.append("═" * 66)
        report.append(f"║                    体检日期：{today}                        ║")
        report.append("═" * 66 + "\n")
        
        # 健康总览
        report.append("┌" + "─" * 64 + "┐")
        report.append("│  📊 健康总览" + " " * 53 + "│")
        report.append("├" + "─" * 64 + "┤")
        report.append(f"│  您的年收入：{income_desc:<49}│")
        report.append(f"│  适用税率：{tax_rate*100:.0f}%（预估）{' ' * 47}│")
        report.append("│  ─" + "─" * 61 + "│")
        report.append(f"│  可能遗漏的扣除：{self.diagnosis['total_missed']:>10,.0f}元  ⚠️ 建议关注          │")
        report.append("│  ─" + "─" * 61 + "│")
        report.append(f"│  💡 如补齐遗漏项，预计可节省税款：{self.diagnosis['potential_savings']:>8,.0f}元    │")
        report.append("└" + "─" * 64 + "┘\n")
        
        # 可能遗漏的扣除项
        if self.diagnosis['possible_missed']:
            report.append("═" * 66)
            report.append("                    ⚠️  可能有遗漏的扣除项")
            report.append("═" * 66)
            
            for item in self.diagnosis['possible_missed']:
                ptype = item['type']
                policy = DEDUCTION_POLICIES.get(ptype, DEDUCTION_POLICIES.get(
                    'continuing_education' if 'continuing' in ptype else ptype, {}))
                
                name = policy.get('name_short', ptype)
                report.append(f"\n{name}")
                report.append("─" * 66)
                report.append(f"│  【扣除标准】{policy.get('standard', ''):<46}│")
                report.append("│  ─" + "─" * 61 + "│")
                report.append(f"│  【您的条件】{item['reason']:<48}│")
                report.append("│  ─" + "─" * 61 + "│")
                report.append(f"│  【预计扣除】{item['amount']:>10,.0f} 元/年{' ' * 32}│")
                report.append("│  【节税效果】按{:.0f}%税率计算 → 节省 {:,.0f}元/年".format(
                    tax_rate * 100, item['savings']) + " " * max(0, 36 - len(f"{item['savings']:.0f}")) + "│")
                report.append("│  【申报状态】⚠️  可能未申报" + " " * 45 + "│")
                report.append("│  ─" + "─" * 61 + "│")
                report.append(f"│  【操作指引】{item['action']:<47}│")
                
                if 'warning' in item:
                    report.append("│  ⚠️  " + item['warning'] + " " * max(0, 58 - len(item['warning'])) + "│")
                if 'note' in item:
                    report.append("│  📝  " + item['note'] + " " * max(0, 58 - len(item['note'])) + "│")
                if 'tax_benefit' in item:
                    report.append("│  📝  " + item['tax_benefit'] + " " * max(0, 58 - len(item['tax_benefit'])) + "│")
                if 'materials' in item:
                    mats = '、'.join(item['materials'])
                    report.append("│  【材料】" + mats + " " * max(0, 56 - len(mats)) + "│")
        
        # 暂不符合条件项
        if self.diagnosis['not_applicable']:
            report.append("\n" + "═" * 66)
            report.append("                   ❓ 暂不符合条件，但未来可能适用")
            report.append("═" * 66)
            
            for item in self.diagnosis['not_applicable']:
                ptype = item['type']
                policy = DEDUCTION_POLICIES.get(ptype, {})
                name = policy.get('name', ptype)
                report.append(f"\n│  {name}")
                report.append("│  ─" + "─" * 61)
                report.append(f"│  当前状态：{item['reason']:<48}")
                report.append(f"│  💡 建议：{item['suggestion']:<47}")
        
        # 行动清单
        if self.diagnosis['possible_missed']:
            report.append("\n" + "═" * 66)
            report.append("                         📋 补申报行动清单")
            report.append("═" * 66)
            
            for i, item in enumerate(self.diagnosis['possible_missed'], 1):
                ptype = item['type']
                policy = DEDUCTION_POLICIES.get(ptype, DEDUCTION_POLICIES.get(
                    'continuing_education' if 'continuing' in ptype else ptype, {}))
                name = policy.get('name', ptype)
                report.append(f"\n│  {i}️⃣  {name}")
                report.append("│     " + item['action'])
        
        # 温馨提示
        report.append("\n" + "─" * 66)
        report.append("│  💡 温馨提示：")
        report.append("│  • 扣除项填报可通过【个人所得税APP】完成")
        report.append("│  • 每年12月可确认次年扣除信息，单位将按此预扣")
        report.append("│  • 如有疑问，可咨询单位HR或拨打12366纳税服务热线")
        report.append("─" * 66)
        
        return "\n".join(report)
    
    def to_json(self) -> dict:
        """导出JSON格式结果"""
        return {
            'data': self.data,
            'diagnosis': self.diagnosis,
            'report_date': datetime.now().isoformat(),
            'summary': {
                'total_missed': self.diagnosis['total_missed'],
                'potential_savings': self.diagnosis['potential_savings'],
                'estimated_tax_rate': self.data.get('estimated_tax_rate', 0.20),
                'items_count': {
                    'possible_missed': len(self.diagnosis['possible_missed']),
                    'not_applicable': len(self.diagnosis['not_applicable'])
                }
            }
        }


def main():
    parser = argparse.ArgumentParser(description='个税扣除项体检报告')
    parser.add_argument('--json-input', type=str, help='JSON格式输入数据')
    parser.add_argument('--output-json', action='store_true', help='输出JSON格式')
    args = parser.parse_args()
    
    collector = DeductionCheckupCollector()
    
    if args.json_input:
        # JSON非交互模式
        try:
            json_data = json.loads(args.json_input)
            collector.load_from_json(json_data)
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            sys.exit(1)
    else:
        # 交互式问卷
        collector.collect_interactive()
    
    # 生成报告
    if args.output_json:
        result = collector.to_json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(collector.generate_report())


if __name__ == '__main__':
    main()
