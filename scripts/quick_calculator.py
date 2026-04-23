#!/usr/bin/env python3
"""
个人所得税快速计算脚本
适用于简单场景的快速估算
v1.1.0 新增：年终奖临界点避税提示功能
"""

# ============================================================
# 年终奖临界点常量定义（v1.1.0 新增）
# 临界点说明：在这些金额附近，可能出现"多发1元，多交几千元税"的情况
# ============================================================
BONUS_CRITICAL_POINTS = [
    # (临界值, 当前税率, 跳档税率, 跳档说明)
    (36000, 0.03, 0.10, "税率从3%跳至10%"),
    (144000, 0.10, 0.20, "税率从10%跳至20%"),
    (300000, 0.20, 0.25, "税率从20%跳至25%"),
    (420000, 0.25, 0.30, "税率从25%跳至30%"),
    (660000, 0.30, 0.35, "税率从30%跳至35%"),
    (960000, 0.35, 0.45, "税率从35%跳至45%"),
]


def check_bonus_critical_point(bonus_amount):
    """
    检查年终奖是否处于临界点附近，并提供避税建议
    
    参数：
    - bonus_amount: 年终奖金额
    
    返回：
    - dict: 包含预警信息和避税建议
    """
    result = {
        'is_critical': False,
        'warnings': [],
        'suggestions': []
    }
    
    for point, current_rate, next_rate, description in BONUS_CRITICAL_POINTS:
        # 计算临界点上下的税负差异
        tax_at_point = calculate_bonus_tax_at_amount(point)
        tax_above_point = calculate_bonus_tax_at_amount(point + 1)
        
        # 计算多发1元后实际多交的税
        extra_income = 1
        extra_tax = tax_above_point - tax_at_point
        effective_tax_rate = extra_tax / extra_income if extra_income > 0 else 0
        
        # 检查奖金是否在临界点附近（±500元范围）
        threshold = 500
        if abs(bonus_amount - point) <= threshold:
            result['is_critical'] = True
            result['warnings'].append({
                'critical_point': point,
                'description': description,
                'effective_tax_rate': effective_tax_rate,
                'impact': f"多发1元多交税{extra_tax:.2f}元，实际税率{effective_tax_rate*100:.2f}%"
            })
            
            # 生成避税建议
            if bonus_amount < point:
                # 在临界点以下，建议少发一点
                optimal = point - 1
                optimal_tax = calculate_bonus_tax_at_amount(optimal)
                current_tax = calculate_bonus_tax_at_amount(bonus_amount)
                
                result['suggestions'].append({
                    'type': 'reduce',
                    'message': f"建议将奖金调整为{optimal}元，比{bonus_amount}元少发{point - bonus_amount}元，"
                               f"可节税{current_tax - optimal_tax:.2f}元"
                })
            else:
                # 在临界点以上，建议多发一点
                next_optimal = point
                current_tax = calculate_bonus_tax_at_amount(bonus_amount)
                next_tax = calculate_bonus_tax_at_amount(next_optimal)
                
                result['suggestions'].append({
                    'type': 'increase',
                    'message': f"当前{bonus_amount}元处于临界点边缘，建议："
                               f"① 保持现状注意税负；② 如能增加至{next_optimal + 10000}元以上可降低边际税负"
                })
    
    # 检查是否在两个临界点之间，且接近上限
    for i, (point, rate, _, _) in enumerate(BONUS_CRITICAL_POINTS):
        if i + 1 < len(BONUS_CRITICAL_POINTS):
            next_point, next_rate, _, _ = BONUS_CRITICAL_POINTS[i + 1]
            
            # 如果奖金接近下一个临界点的下限
            if point < bonus_amount < next_point:
                distance_to_next = next_point - bonus_amount
                if distance_to_next <= 10000:  # 距离下一个临界点不到1万
                    # 计算中间最优值（跳档临界点）
                    result['suggestions'].append({
                        'type': 'info',
                        'message': f"当前奖金{bonus_amount}元距临界点{next_point}元还有{distance_to_next:.0f}元，"
                                   f"注意控制奖金金额以避免进入更高税率档次"
                    })
    
    return result


def calculate_bonus_tax_at_amount(amount):
    """
    计算给定金额的年终奖税额（单独计税方式）
    """
    bonus_brackets = [
        (0, 3000, 0.03, 0),
        (3000, 12000, 0.10, 210),
        (12000, 25000, 0.20, 1410),
        (25000, 35000, 0.25, 2660),
        (35000, 55000, 0.30, 4410),
        (55000, 80000, 0.35, 7160),
        (80000, float('inf'), 0.45, 15160),
    ]
    
    for min_i, max_i, rate, quick in bonus_brackets:
        if amount <= max_i:
            return amount * rate - quick
    return 0


def quick_calculate(
    annual_salary,
    annual_social,
    annual_housing_fund,
    annual_annuity=0,
    annual_special_additions=0,
    annual_other_deductions=0,
    annual_bonus=0,
    bonus_method='separate'
):
    """
    快速计算年度应纳税额
    
    参数：
    - annual_salary: 年度税前工资
    - annual_social: 年度社保个人部分
    - annual_housing_fund: 年度公积金个人部分
    - annual_annuity: 年度职业年金个人部分
    - annual_special_additions: 年度专项附加扣除合计
    - annual_other_deductions: 年度其他扣除合计
    - annual_bonus: 年度奖金金额
    - bonus_method: 'separate' 单独计税 / 'combined' 并入综合所得
    
    返回：
    - dict: 包含计算结果和年终奖临界点预警（v1.1.0新增）
    """
    
    # 税率表
    brackets = [
        (0, 36000, 0.03, 0),
        (36000, 144000, 0.10, 2520),
        (144000, 300000, 0.20, 16920),
        (300000, 420000, 0.25, 31920),
        (420000, 660000, 0.30, 52920),
        (660000, 960000, 0.35, 85920),
        (960000, float('inf'), 0.45, 181920),
    ]
    
    def calc_tax(income):
        for min_i, max_i, rate, quick in brackets:
            if income <= max_i:
                return income * rate - quick
        return 0
    
    def calc_bonus_tax(bonus):
        bonus_brackets = [
            (0, 3000, 0.03, 0),
            (3000, 12000, 0.10, 210),
            (12000, 25000, 0.20, 1410),
            (25000, 35000, 0.25, 2660),
            (35000, 55000, 0.30, 4410),
            (55000, 80000, 0.35, 7160),
            (80000, float('inf'), 0.45, 15160),
        ]
        for min_i, max_i, rate, quick in bonus_brackets:
            if bonus <= max_i:
                return bonus * rate - quick
        return 0
    
    # 综合所得应纳税所得额
    taxable = (
        annual_salary
        - 60000
        - annual_social
        - annual_housing_fund
        - annual_annuity
        - annual_special_additions
        - annual_other_deductions
    )
    
    # 综合所得税额
    income_tax = calc_tax(taxable)
    
    # 奖金税额
    if bonus_method == 'separate':
        bonus_tax = calc_bonus_tax(annual_bonus)
    else:
        # 并入综合所得
        combined_taxable = taxable + annual_bonus
        bonus_tax = 0
        income_tax = calc_tax(combined_taxable)
    
    total_tax = income_tax + bonus_tax
    
    # v1.1.0 新增：年终奖临界点检测
    bonus_warning = None
    if annual_bonus > 0 and bonus_method == 'separate':
        bonus_warning = check_bonus_critical_point(annual_bonus)
    
    return {
        'annual_salary': annual_salary,
        'total_deductions': (
            60000 + annual_social + annual_housing_fund + annual_annuity
            + annual_special_additions + annual_other_deductions
        ),
        'taxable_income': taxable,
        'income_tax': income_tax,
        'bonus_tax': bonus_tax,
        'total_tax': total_tax,
        'effective_rate': total_tax / annual_salary if annual_salary > 0 else 0,
        'bonus_warning': bonus_warning  # v1.1.0 新增字段
    }


def compare_bonus_methods(annual_salary, annual_bonus, deductions):
    """
    对比年终奖两种计税方式，返回更优方案
    
    参数：
    - annual_salary: 年度税前工资
    - annual_bonus: 年度奖金金额
    - deductions: 其他扣除合计（不含奖金）
    
    返回：
    - dict: 对比结果
    """
    separate_result = quick_calculate(
        annual_salary, 
        0, 0, 0, 0, deductions, 
        annual_bonus, 
        'separate'
    )
    
    combined_result = quick_calculate(
        annual_salary, 
        0, 0, 0, 0, deductions, 
        annual_bonus, 
        'combined'
    )
    
    better = '单独计税' if separate_result['total_tax'] <= combined_result['total_tax'] else '并入综合所得'
    savings = abs(separate_result['total_tax'] - combined_result['total_tax'])
    
    return {
        'separate_tax': separate_result['total_tax'],
        'combined_tax': combined_result['total_tax'],
        'better_method': better,
        'tax_savings': savings
    }


def print_result(result):
    """打印计算结果"""
    print("\n" + "=" * 50)
    print("📊 个税计算结果")
    print("=" * 50)
    print(f"年度税前工资:     ¥{result['annual_salary']:>12,.2f}")
    print(f"扣除项目合计:     ¥{result['total_deductions']:>12,.2f}")
    print(f"应纳税所得额:     ¥{result['taxable_income']:>12,.2f}")
    print("-" * 50)
    print(f"工资薪金税额:     ¥{result['income_tax']:>12,.2f}")
    print(f"年终奖税额:       ¥{result['bonus_tax']:>12,.2f}")
    print(f"合计应纳税额:     ¥{result['total_tax']:>12,.2f}")
    print(f"实际税负率:       {result['effective_rate']*100:>11.2f}%")
    print("=" * 50)


def print_bonus_warning(bonus_warning):
    """
    打印年终奖临界点警告（v1.1.0 新增）
    
    参数：
    - bonus_warning: check_bonus_critical_point 返回的警告信息
    """
    if not bonus_warning or not bonus_warning.get('warnings'):
        return
    
    print("\n" + "=" * 50)
    print("⚠️  年终奖临界点预警")
    print("=" * 50)
    
    print("\n📌 您的年终奖处于以下临界点附近：")
    for warning in bonus_warning['warnings']:
        print(f"\n  🔸 {warning['critical_point']:,}元临界点")
        print(f"     {warning['description']}")
        print(f"     ⚠️ {warning['impact']}")
    
    if bonus_warning.get('suggestions'):
        print("\n💡 避税建议：")
        for i, suggestion in enumerate(bonus_warning['suggestions'], 1):
            print(f"\n  {i}. {suggestion['message']}")
    
    print("\n" + "-" * 50)
    print("💡 小贴士：年终奖在临界点附近时，")
    print("   '多发1元可能多交几千元税'的情况确实存在，")
    print("   合理规划奖金金额可以有效降低税负。")
    print("=" * 50)


# ============================================================
# 命令行使用示例
# ============================================================

if __name__ == '__main__':
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════╗
    ║       个人所得税快速计算器  v1.1.0               ║
    ║       新增：年终奖临界点避税提示               ║
    ╚══════════════════════════════════════════════════╝
    
    使用方法：
    python quick_calculator.py <年工资> [年奖金]
    
    示例：
    python quick_calculator.py 144000 20000
    """)
    
    if len(sys.argv) > 1:
        annual_salary = float(sys.argv[1])
        annual_bonus = float(sys.argv[2]) if len(sys.argv) > 2 else 0
        
        # 默认扣除估算（月薪的20%左右）
        default_deductions = annual_salary * 0.20
        
        result = quick_calculate(
            annual_salary=annual_salary,
            annual_social=default_deductions * 0.6,
            annual_housing_fund=default_deductions * 0.4,
            annual_special_additions=0,
            annual_other_deductions=0,
            annual_bonus=annual_bonus,
            bonus_method='separate'
        )
        
        print(f"\n📌 基于默认估算（实际以详细计算为准）")
        print_result(result)
        
        # v1.1.0 新增：打印年终奖临界点警告
        if result.get('bonus_warning'):
            print_bonus_warning(result['bonus_warning'])


def calculate_pension_tax_benefit(annual_income, other_deductions_monthly=0, insurance_monthly=0):
    """
    计算个人养老金税收优惠
    
    参数：
    - annual_income: 年度工资薪金收入
    - other_deductions_monthly: 月度专项附加扣除
    - insurance_monthly: 月度社保公积金（个人部分）
    
    返回：
    - dict: 包含税收优惠详情
    """
    
    # 基本减除费用
    basic_deduction = 60000
    
    # 专项扣除（社保公积金）
    special_deduction = insurance_monthly * 12
    
    # 专项附加扣除
    special_addition = other_deductions_monthly * 12
    
    # 缴存前应纳税所得额
    taxable_income_before = annual_income - basic_deduction - special_deduction - special_addition
    taxable_income_before = max(taxable_income_before, 0)
    
    # 缴存后应纳税所得额（扣除12000元个人养老金）
    pension_deduction = 12000
    taxable_income_after = taxable_income_before - pension_deduction
    taxable_income_after = max(taxable_income_after, 0)
    
    # 计算税额
    tax_before = calculate_tax_from_table(taxable_income_before)
    tax_after = calculate_tax_from_table(taxable_income_after)
    
    # 节省税额
    tax_saved = tax_before - tax_after
    
    # 实际成本 = 缴存金额 - 节省税额
    actual_cost = pension_deduction - tax_saved
    
    # 收益率 = 节省税额 / 实际成本
    if actual_cost > 0:
        return_rate = tax_saved / actual_cost
    else:
        return_rate = 0
    
    return {
        'taxable_income_before': taxable_income_before,
        'taxable_income_after': taxable_income_after,
        'tax_before': tax_before,
        'tax_after': tax_after,
        'tax_saved': tax_saved,
        'actual_cost': actual_cost,
        'return_rate': return_rate
    }


def calculate_tax_from_table(taxable_income):
    """根据综合所得税率表计算税额"""
    tax_brackets = [
        (0, 36000, 0.03, 0),
        (36000, 144000, 0.10, 2520),
        (144000, 300000, 0.20, 16920),
        (300000, 420000, 0.25, 31920),
        (420000, 660000, 0.30, 52920),
        (660000, 960000, 0.35, 85920),
        (960000, float('inf'), 0.45, 181920),
    ]
    
    for min_income, max_income, rate, quick_deduction in tax_brackets:
        if taxable_income <= max_income:
            return taxable_income * rate - quick_deduction
    
    return 0


def print_pension_benefit(result):
    """打印个人养老金税收优惠结果"""
    print("\n" + "=" * 50)
    print("🏦 个人养老金税收优惠")
    print("=" * 50)
    print(f"缴存前应纳税所得额: ¥{result['taxable_income_before']:>12,.2f}")
    print(f"缴存后应纳税所得额: ¥{result['taxable_income_after']:>12,.2f}")
    print("-" * 50)
    print(f"缴存前应纳税额:     ¥{result['tax_before']:>12,.2f}")
    print(f"缴存后应纳税额:     ¥{result['tax_after']:>12,.2f}")
    print(f"节省税额:           ¥{result['tax_saved']:>12,.2f}")
    print(f"实际成本:           ¥{result['actual_cost']:>12,.2f}")
    print(f"收益率:             {result['return_rate']*100:>11.2f}%")
    print("=" * 50)
