#!/usr/bin/env python3
"""
个人所得税信息采集问卷
用于交互式收集用户税务信息

v1.1.1 新增功能：
- --json-input 参数支持非交互式计算模式
- JSON模式现在会执行实际税额计算（修复之前的严重缺陷）
"""

import json
import argparse
import sys
import os

# 添加脚本目录到路径，以便导入tax_calculator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from tax_calculator import calculate_annual_settlement, calculate_annual_bonus_tax, TAX_BRACKETS_ANNUAL
    TAX_CALCULATOR_AVAILABLE = True
except ImportError:
    TAX_CALCULATOR_AVAILABLE = False


class TaxInfoCollector:
    """税务信息采集器"""
    
    def __init__(self):
        self.data = {}
        self.step = 0
    
    def load_from_json(self, json_data):
        """
        从JSON数据加载信息（v1.1.1 新增）
        
        参数：
        - json_data: dict，包含用户税务信息的JSON对象
        
        支持的字段：
        - year: 年度（默认2024）
        - identity: 纳税人身份（居民个人/非居民个人）
        - monthly_salary: 月均税前工资
        - monthly_incomes: 逐月工资列表（12个月）
        - bonus: 年终奖金额
        - bonus_method: 奖金计税方式（separate/combined）
        - monthly_social: 月社保个人部分
        - monthly_housing_fund: 月公积金个人部分
        - monthly_annuity: 月职业年金个人部分
        - special_additions: 专项附加扣除对象
        - personal_pension: 个人养老金年缴存额
        - tax_health: 税优健康险年缴存额
        - enterprise_annuity: 企业年金年缴存额
        - commercial_health: 商业健康险年缴存额
        - unit_withheld: 单位全年代扣代缴税额
        """
        self.data = {}
        
        # 基础信息
        self.data['year'] = json_data.get('year', '2024')
        self.data['identity'] = json_data.get('identity', '居民个人')
        
        # 收入信息
        if 'monthly_incomes' in json_data:
            self.data['monthly_incomes'] = json_data['monthly_incomes']
            self.data['annual_income'] = sum(json_data['monthly_incomes'])
        elif 'monthly_salary' in json_data:
            self.data['monthly_avg'] = json_data['monthly_salary']
            self.data['annual_income'] = json_data['monthly_salary'] * 12
        else:
            self.data['annual_income'] = 0
        
        # 年终奖
        self.data['bonus'] = json_data.get('bonus', 0)
        self.data['bonus_method'] = json_data.get('bonus_method', 'separate')
        
        # 专项扣除
        self.data['monthly_social'] = json_data.get('monthly_social', 0)
        self.data['monthly_housing_fund'] = json_data.get('monthly_housing_fund', 0)
        self.data['monthly_annuity'] = json_data.get('monthly_annuity', 0)
        
        self.data['annual_social'] = self.data['monthly_social'] * 12
        self.data['annual_housing_fund'] = self.data['monthly_housing_fund'] * 12
        self.data['annual_annuity'] = self.data['monthly_annuity'] * 12
        
        # 专项附加扣除
        special_additions_input = json_data.get('special_additions', {})
        self.data['special_additions'] = {
            'children_education': special_additions_input.get('children_education', 0),
            'continuing_education': special_additions_input.get('continuing_education', 0),
            'medical_expense': special_additions_input.get('medical_expense', 0),
            'housing_loan': special_additions_input.get('housing_loan', 0),
            'housing_rent': special_additions_input.get('housing_rent', 0),
            'elderly_support': special_additions_input.get('elderly_support', 0),
            'infant_care': special_additions_input.get('infant_care', 0)
        }
        self.data['annual_special_additions'] = sum(self.data['special_additions'].values())
        
        # 其他扣除
        self.data['personal_pension'] = min(json_data.get('personal_pension', 0), 12000)
        self.data['tax_health'] = min(json_data.get('tax_health', 0), 2400)
        self.data['enterprise_annuity'] = json_data.get('enterprise_annuity', 0)
        self.data['commercial_health'] = json_data.get('commercial_health', 0)
        
        self.data['annual_other_deductions'] = (
            self.data['personal_pension'] +
            self.data['tax_health'] +
            self.data['enterprise_annuity'] +
            self.data['commercial_health']
        )
        
        # 单位代扣
        self.data['unit_withheld'] = json_data.get('unit_withheld', 0)
        
        return self.data
    
    def collect_basic_info(self):
        """采集基础信息"""
        print("\n" + "=" * 50)
        print("📋 第一步：基础信息")
        print("=" * 50)
        
        # 年度选择
        year = input("请输入要计算的年度（默认2024）：").strip() or "2024"
        self.data['year'] = year
        
        # 纳税人身份
        print("\n请选择纳税人身份：")
        print("1. 居民个人")
        print("2. 非居民个人")
        identity = input("请输入选项（1或2）：").strip()
        self.data['identity'] = "居民个人" if identity == "1" else "非居民个人"
        
        return self.data
    
    def collect_income(self):
        """采集收入信息"""
        print("\n" + "=" * 50)
        print("💰 第二步：收入信息")
        print("=" * 50)
        
        print("\n请选择收入录入方式：")
        print("1. 逐月输入（更精准）")
        print("2. 快速输入（月均+奖金）")
        method = input("请选择（1或2）：").strip()
        
        if method == "1":
            monthly_incomes = []
            for month in range(1, 13):
                income = float(input(f"  {month}月工资（税前）：").strip() or "0")
                monthly_incomes.append(income)
            self.data['monthly_incomes'] = monthly_incomes
            self.data['annual_income'] = sum(monthly_incomes)
        else:
            monthly_avg = float(input("  月均税前工资：").strip() or "0")
            self.data['monthly_avg'] = monthly_avg
            self.data['annual_income'] = monthly_avg * 12
        
        # 年终奖
        has_bonus = input("\n是否有年终奖/全年一次性奖金？（y/n）：").strip().lower()
        if has_bonus == 'y':
            bonus = float(input("  年终奖金额：").strip() or "0")
            self.data['bonus'] = bonus
            
            print("\n奖金计税方式：")
            print("1. 单独计税（推荐，月度税额较低时）")
            print("2. 并入综合所得")
            method = input("请选择（1或2）：").strip()
            self.data['bonus_method'] = "separate" if method == "1" else "combined"
        else:
            self.data['bonus'] = 0
            self.data['bonus_method'] = None
        
        return self.data
    
    def collect_special_deductions(self):
        """采集专项扣除信息"""
        print("\n" + "=" * 50)
        print("📋 第三步：专项扣除")
        print("=" * 50)
        print("\n专项扣除包括：养老、医疗、失业保险、公积金、职业年金")
        
        print("\n请选择输入方式：")
        print("1. 逐月输入各项金额")
        print("2. 按基数和比例计算")
        method = input("请选择（1或2）：").strip()
        
        if method == "1":
            monthly_pension = float(input("  月养老保险个人部分：").strip() or "0")
            monthly_medical = float(input("  月医疗保险个人部分：").strip() or "0")
            monthly_unemployment = float(input("  月失业保险个人部分：").strip() or "0")
            monthly_housing = float(input("  月住房公积金个人部分：").strip() or "0")
            monthly_annuity = float(input("  月职业年金个人部分：").strip() or "0")
            
            self.data['monthly_social'] = monthly_pension + monthly_medical + monthly_unemployment
            self.data['monthly_housing_fund'] = monthly_housing
            self.data['monthly_annuity'] = monthly_annuity
        else:
            base = float(input("  社保缴纳基数：").strip() or "0")
            
            pension_rate = float(input("  养老保险比例%（默认8）：").strip() or "8") / 100
            medical_rate = float(input("  医疗保险比例%（默认2）：").strip() or "2") / 100
            unemployment_rate = float(input("  失业保险比例%（默认0.5）：").strip() or "0.5") / 100
            housing_rate = float(input("  公积金比例%（默认12）：").strip() or "12") / 100
            annuity_rate = float(input("  职业年金比例%（默认4）：").strip() or "4") / 100
            
            self.data['monthly_social'] = base * (pension_rate + medical_rate + unemployment_rate)
            self.data['monthly_housing_fund'] = base * housing_rate
            self.data['monthly_annuity'] = base * annuity_rate
        
        self.data['annual_social'] = self.data['monthly_social'] * 12
        self.data['annual_housing_fund'] = self.data['monthly_housing_fund'] * 12
        self.data['annual_annuity'] = self.data['monthly_annuity'] * 12
        
        return self.data
    
    def collect_special_additions(self):
        """采集专项附加扣除信息"""
        print("\n" + "=" * 50)
        print("📝 第四步：专项附加扣除")
        print("=" * 50)
        
        self.data['special_additions'] = {
            'children_education': 0,
            'continuing_education': 0,
            'medical_expense': 0,
            'housing_loan': 0,
            'housing_rent': 0,
            'elderly_support': 0,
            'infant_care': 0
        }
        
        # 子女教育
        print("\n1️⃣ 子女教育")
        has_children = input("  是否有接受学历教育的子女？（y/n）：").strip().lower()
        if has_children == 'y':
            num_children = int(input("  子女数量：").strip() or "0")
            self.data['special_additions']['children_education'] = num_children * 2000 * 12
            print(f"  年度扣除：{num_children} × 2000 × 12 = ¥{self.data['special_additions']['children_education']:,.0f}")
        
        # 继续教育
        print("\n2️⃣ 继续教育")
        has_edu = input("  是否有学历教育或职业资格证书？（y/n）：").strip().lower()
        if has_edu == 'y':
            edu_type = input("  类型：1-学历教育 2-职业资格：").strip()
            if edu_type == "1":
                self.data['special_additions']['continuing_education'] = 400 * 12
                print(f"  年度扣除：400 × 12 = ¥{self.data['special_additions']['continuing_education']:,.0f}")
            else:
                self.data['special_additions']['continuing_education'] = 3600
                print(f"  年度扣除：¥3,600")
        
        # 大病医疗
        print("\n3️⃣ 大病医疗")
        has_medical = input("  是否有大病医疗支出？（y/n）：").strip().lower()
        if has_medical == 'y':
            expense = float(input("  医保报销后自付金额：").strip() or "0")
            if expense > 15000:
                deductible = (expense - 15000) * 0.6
                deductible = min(deductible, 80000)
                self.data['special_additions']['medical_expense'] = deductible
                print(f"  可扣除金额：(¥{expense:,.0f} - 15000) × 60% = ¥{deductible:,.0f}")
        
        # 住房
        print("\n4️⃣ 住房")
        print("  1-住房贷款利息（首套房）")
        print("  2-住房租金")
        print("  3-无住房相关扣除")
        housing_choice = input("  请选择：").strip()
        if housing_choice == "1":
            self.data['special_additions']['housing_loan'] = 1000 * 12
            print(f"  年度扣除：1000 × 12 = ¥12,000")
        elif housing_choice == "2":
            print("  城市级别：1-一线城市 2-省会/计划单列市 3-其他城市")
            city_level = input("  请选择：").strip()
            rent_map = {"1": 1500, "2": 1100, "3": 800}
            rent = rent_map.get(city_level, 800)
            self.data['special_additions']['housing_rent'] = rent * 12
            print(f"  年度扣除：{rent} × 12 = ¥{rent * 12:,.0f}")
        
        # 赡养老人
        print("\n5️⃣ 赡养老人")
        is_only_child = input("  是否为独生子女？（y/n）：").strip().lower()
        if is_only_child == 'y':
            self.data['special_additions']['elderly_support'] = 3000 * 12
            print(f"  年度扣除：3000 × 12 = ¥36,000")
        else:
            num_siblings = int(input("  兄弟姐妹数量（不含自己）：").strip() or "1")
            share = min(3000 / (num_siblings + 1), 1500)
            self.data['special_additions']['elderly_support'] = share * 12
            print(f"  年度扣除：{share:.0f} × 12 = ¥{share * 12:,.0f}")
        
        # 婴幼儿照护
        print("\n6️⃣ 3岁以下婴幼儿照护")
        has_infant = input("  是否有3岁以下子女？（y/n）：").strip().lower()
        if has_infant == 'y':
            num_infants = int(input("  婴幼儿数量：").strip() or "0")
            self.data['special_additions']['infant_care'] = num_infants * 2000 * 12
            print(f"  年度扣除：{num_infants} × 2000 × 12 = ¥{self.data['special_additions']['infant_care']:,.0f}")
        
        # 合计
        total = sum(self.data['special_additions'].values())
        self.data['annual_special_additions'] = total
        print(f"\n📊 专项附加扣除合计：¥{total:,.0f}/年")
        
        return self.data
    
    def collect_other_deductions(self):
        """采集其他扣除信息"""
        print("\n" + "=" * 50)
        print("💼 第五步：其他扣除")
        print("=" * 50)
        
        print("\n请输入年度缴纳金额（无则输入0）：")
        
        personal_pension = float(input("  个人养老金（上限¥12,000）：").strip() or "0")
        tax_health = float(input("  税优健康险（上限¥2,400）：").strip() or "0")
        enterprise_annuity = float(input("  企业年金：").strip() or "0")
        commercial_health = float(input("  商业健康保险：").strip() or "0")
        
        self.data['personal_pension'] = min(personal_pension, 12000)
        self.data['tax_health'] = min(tax_health, 2400)
        self.data['enterprise_annuity'] = enterprise_annuity
        self.data['commercial_health'] = commercial_health
        
        self.data['annual_other_deductions'] = (
            self.data['personal_pension'] +
            self.data['tax_health'] +
            self.data['enterprise_annuity'] +
            self.data['commercial_health']
        )
        
        print(f"\n📊 其他扣除合计：¥{self.data['annual_other_deductions']:,.2f}")
        
        return self.data
    
    def collect_unit_withheld(self):
        """采集单位代扣信息"""
        print("\n" + "=" * 50)
        print("📋 第六步：单位代扣代缴")
        print("=" * 50)
        
        print("\n如知道单位全年代扣代缴金额，请输入（否则可跳过）：")
        withheld = input("  单位全年代扣代缴税额：").strip()
        
        if withheld:
            self.data['unit_withheld'] = float(withheld)
        else:
            self.data['unit_withheld'] = 0
        
        return self.data
    
    def collect_all(self):
        """采集全部信息"""
        self.collect_basic_info()
        self.collect_income()
        self.collect_special_deductions()
        self.collect_special_additions()
        self.collect_other_deductions()
        self.collect_unit_withheld()
        
        print("\n" + "=" * 50)
        print("✅ 信息采集完成！")
        print("=" * 50)
        
        return self.data


def perform_tax_calculation(data):
    """
    执行实际税额计算（v1.1.1 修复核心功能）
    
    返回：
    - dict: 包含完整计算结果的字典
    """
    if not TAX_CALCULATOR_AVAILABLE:
        return {
            'error': 'tax_calculator模块未找到，无法执行计算',
            'collected_data': data
        }
    
    try:
        # 调用税额计算函数
        result = calculate_annual_settlement(
            annual_income=data.get('annual_income', 0),
            annual_social=data.get('annual_social', 0),
            annual_housing_fund=data.get('annual_housing_fund', 0),
            annual_annuity=data.get('annual_annuity', 0),
            annual_special_additions=data.get('annual_special_additions', 0),
            annual_other_deductions=data.get('annual_other_deductions', 0),
            annual_bonus=data.get('bonus', 0),
            bonus_method=data.get('bonus_method', 'separate'),
            unit_withheld=data.get('unit_withheld', 0)
        )
        
        return result
    except Exception as e:
        return {
            'error': f'计算过程出错: {str(e)}',
            'collected_data': data
        }


def print_summary(data):
    """打印信息汇总"""
    print("\n" + "=" * 50)
    print("📊 采集信息汇总")
    print("=" * 50)
    
    print(f"\n【基础信息】")
    print(f"  年度：{data.get('year', 'N/A')}")
    print(f"  纳税人身份：{data.get('identity', 'N/A')}")
    
    print(f"\n【收入信息】")
    print(f"  年度工资薪金：¥{data.get('annual_income', 0):,.2f}")
    if data.get('bonus', 0) > 0:
        print(f"  年度奖金：¥{data.get('bonus'):,.2f}（{data.get('bonus_method', 'separate')}）")
    
    print(f"\n【专项扣除】")
    print(f"  社保（年）：¥{data.get('annual_social', 0):,.2f}")
    print(f"  公积金（年）：¥{data.get('annual_housing_fund', 0):,.2f}")
    print(f"  职业年金（年）：¥{data.get('annual_annuity', 0):,.2f}")
    
    print(f"\n【专项附加扣除】")
    additions = data.get('special_additions', {})
    for key, value in additions.items():
        if value > 0:
            name_map = {
                'children_education': '子女教育',
                'continuing_education': '继续教育',
                'medical_expense': '大病医疗',
                'housing_loan': '住房贷款',
                'housing_rent': '住房租金',
                'elderly_support': '赡养老人',
                'infant_care': '婴幼儿照护'
            }
            print(f"  {name_map.get(key, key)}：¥{value:,.2f}")
    print(f"  合计：¥{data.get('annual_special_additions', 0):,.2f}")
    
    print(f"\n【其他扣除】")
    print(f"  个人养老金：¥{data.get('personal_pension', 0):,.2f}")
    print(f"  税优健康险：¥{data.get('tax_health', 0):,.2f}")
    print(f"  企业年金：¥{data.get('enterprise_annuity', 0):,.2f}")
    print(f"  商业健康险：¥{data.get('commercial_health', 0):,.2f}")
    print(f"  合计：¥{data.get('annual_other_deductions', 0):,.2f}")
    
    if data.get('unit_withheld', 0) > 0:
        print(f"\n【单位代扣】")
        print(f"  单位代扣代缴：¥{data.get('unit_withheld'):,.2f}")


def print_calculation_result(calc_result):
    """打印税额计算结果（v1.1.1 新增）"""
    print("\n" + "=" * 50)
    print("💰 税额计算结果")
    print("=" * 50)
    
    if 'error' in calc_result:
        print(f"\n❌ {calc_result['error']}")
        return
    
    print(f"\n【应纳税所得额】")
    print(f"  年度收入：¥{calc_result.get('annual_income', 0):,.2f}")
    print(f"  基本减除费用：¥60,000")
    print(f"  专项扣除合计：¥{calc_result.get('annual_income', 0) - calc_result.get('taxable_income', 0) - 60000:,.2f}")
    print(f"  应纳税所得额：¥{calc_result.get('taxable_income', 0):,.2f}")
    
    print(f"\n【税额计算】")
    print(f"  综合所得税额：¥{calc_result.get('income_tax', 0):,.2f}")
    if calc_result.get('bonus_tax') is not None:
        print(f"  年终奖税额：¥{calc_result.get('bonus_tax'):,.2f}")
    print(f"  应纳税额合计：¥{calc_result.get('total_tax', 0):,.2f}")
    
    if calc_result.get('unit_withheld', 0) > 0:
        print(f"\n【汇算清缴结果】")
        print(f"  单位代扣代缴：¥{calc_result.get('unit_withheld'):,.2f}")
        print(f"  应纳税额：¥{calc_result.get('total_tax'):,.2f}")
        
        result = calc_result.get('result', '无需调整')
        amount = calc_result.get('amount', 0)
        message = calc_result.get('message', '')
        
        if result == '退税':
            print(f"\n  🎉 {message}")
        elif result == '补税':
            print(f"\n  ⚠️ {message}")
        else:
            print(f"\n  ✅ {message}")


def print_json_result(data, calc_result=None):
    """以JSON格式输出结果（v1.1.1 修复版）"""
    result = {
        'year': data.get('year', '2024'),
        'identity': data.get('identity', '居民个人'),
        'collected_info': {
            'annual_income': data.get('annual_income', 0),
            'bonus': data.get('bonus', 0),
            'bonus_method': data.get('bonus_method'),
            'annual_social': data.get('annual_social', 0),
            'annual_housing_fund': data.get('annual_housing_fund', 0),
            'annual_annuity': data.get('annual_annuity', 0),
            'special_additions': data.get('special_additions', {}),
            'annual_special_additions': data.get('annual_special_additions', 0),
            'personal_pension': data.get('personal_pension', 0),
            'tax_health': data.get('tax_health', 0),
            'enterprise_annuity': data.get('enterprise_annuity', 0),
            'commercial_health': data.get('commercial_health', 0),
            'annual_other_deductions': data.get('annual_other_deductions', 0),
            'unit_withheld': data.get('unit_withheld', 0)
        }
    }
    
    # 添加计算结果（v1.1.1 修复核心功能）
    if calc_result:
        result['calculation_result'] = calc_result
    
    print("\n" + "=" * 50)
    print("📋 JSON格式完整结果")
    print("=" * 50)
    print(json.dumps(result, ensure_ascii=False, indent=2))


# 主程序
if __name__ == '__main__':
    # v1.1.1 新增：命令行参数解析
    parser = argparse.ArgumentParser(
        description='个人所得税信息采集问卷 v1.1.1（修复JSON模式计算问题）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 交互式模式（默认）
  python questionnaire.py
  
  # 非交互式JSON输入模式（v1.1.1 现在会执行实际税额计算）
  python questionnaire.py --json-input '{"monthly_salary": 30000, "bonus": 50000}'
  
  # 完整的JSON输入示例
  python questionnaire.py --json-input '{
    "monthly_salary": 30000,
    "bonus": 36000,
    "bonus_method": "separate",
    "monthly_social": 3000,
    "monthly_housing_fund": 2500,
    "monthly_annuity": 500,
    "special_additions": {
      "children_education": 24000,
      "elderly_support": 36000
    },
    "personal_pension": 12000,
    "unit_withheld": 45000
  }'
        """
    )
    
    parser.add_argument(
        '--json-input', '-j',
        type=str,
        help='以JSON格式传入用户税务信息，执行实际税额计算'
    )
    
    parser.add_argument(
        '--output-json', '-o',
        action='store_true',
        help='以JSON格式输出结果（仅在--json-input模式下有效）'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='%(prog)s v1.1.1 (修复JSON模式计算问题)'
    )
    
    args = parser.parse_args()
    
    collector = TaxInfoCollector()
    
    if args.json_input:
        # v1.1.1 修复：非交互式JSON输入模式，执行实际税额计算
        try:
            json_data = json.loads(args.json_input)
            print("\n" + "=" * 50)
            print("📥 收到JSON数据，正在处理并计算...")
            print("=" * 50)
            
            # 1. 加载数据
            data = collector.load_from_json(json_data)
            print_summary(data)
            
            # 2. 执行实际税额计算（v1.1.1 修复的核心功能）
            print("\n" + "=" * 50)
            print("🔢 正在计算应纳税额...")
            print("=" * 50)
            calc_result = perform_tax_calculation(data)
            
            # 3. 输出计算结果
            print_calculation_result(calc_result)
            
            # 4. 根据参数决定输出格式
            if args.output_json:
                print_json_result(data, calc_result)
                
        except json.JSONDecodeError as e:
            print("\n❌ JSON格式错误：" + str(e))
            print("请检查JSON格式是否正确，例如：")
            print("  python questionnaire.py --json-input '{\"monthly_salary\": 30000}'")
            sys.exit(1)
    else:
        # 传统交互式模式
        print("""
╔══════════════════════════════════════════════════╗
║       个人所得税信息采集问卷  v1.1.1              ║
║       新增：--json-input 非交互式计算模式        ║
║       修复：JSON模式现在执行实际税额计算         ║
╚══════════════════════════════════════════════════╝
        """)
        
        data = collector.collect_all()
        print_summary(data)
