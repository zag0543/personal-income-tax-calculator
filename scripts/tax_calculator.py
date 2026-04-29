#!/usr/bin/env python3
"""
个人所得税智能计算器
支持累计预扣预缴法、年度汇算清缴、专项附加扣除等全部功能
"""

# ============================================================
# 税率表定义
# ============================================================

# 综合所得税率表（年度）
TAX_BRACKETS_ANNUAL = [
    (0, 36000, 0.03, 0),
    (36000, 144000, 0.10, 2520),
    (144000, 300000, 0.20, 16920),
    (300000, 420000, 0.25, 31920),
    (420000, 660000, 0.30, 52920),
    (660000, 960000, 0.35, 85920),
    (960000, float('inf'), 0.45, 181920),
]

# 全年一次性奖金税率表（月度换算）
BONUS_TAX_BRACKETS = [
    (0, 3000, 0.03, 0),
    (3000, 12000, 0.10, 210),
    (12000, 25000, 0.20, 1410),
    (25000, 35000, 0.25, 2660),
    (35000, 55000, 0.30, 4410),
    (55000, 80000, 0.35, 7160),
    (80000, float('inf'), 0.45, 15160),
]

# 月度累计预扣预缴税率表
MONTHLY_TAX_BRACKETS = TAX_BRACKETS_ANNUAL


# ============================================================
# 计算函数
# ============================================================

def calculate_tax(taxable_income, brackets):
    """
    根据税率表计算税额
    
    参数：
    - taxable_income: 应纳税所得额
    - brackets: 税率表
    
    返回：
    - 应纳税额
    """
    for min_income, max_income, rate, quick_deduction in brackets:
        if taxable_income <= max_income:
            tax = taxable_income * rate - quick_deduction
            return max(tax, 0)
    return 0


def calculate_annual_bonus_tax(bonus_amount, method='separate'):
    """
    计算全年一次性奖金税额
    
    参数：
    - bonus_amount: 奖金金额
    - method: 'separate' 单独计税 / 'combined' 并入综合所得
    
    返回：
    - 税额（单独计税时）；None（并入综合所得时，需合并计算）
    """
    if method == 'separate':
        monthly_bonus = bonus_amount / 12
        # 用月平均查税率，然后用年终奖总额计算税额
        for min_income, max_income, rate, quick_deduction in BONUS_TAX_BRACKETS:
            if monthly_bonus <= max_income:
                tax = bonus_amount * rate - quick_deduction
                return max(tax, 0)
        return 0
    else:
        return None


def calculate_monthly_pre_tax(
    month,
    monthly_income,
    monthly_social,
    monthly_housing_fund,
    monthly_annuity=0,
    monthly_special_additions=0,
    monthly_other_deductions=0
):
    """
    计算月度累计预扣预缴税额
    
    参数：
    - month: 月份 (1-12)
    - monthly_income: 月税前工资
    - monthly_social: 月社保个人部分（养老+医疗+失业）
    - monthly_housing_fund: 月公积金个人部分
    - monthly_annuity: 月职业年金个人部分
    - monthly_special_additions: 月专项附加扣除合计
    - monthly_other_deductions: 月其他扣除合计
    
    返回：
    - (本月应扣税额, 累计应扣税额)
    """
    # 累计收入
    cumulative_income = monthly_income * month
    
    # 累计减除费用
    cumulative_deduction_fee = 5000 * month
    
    # 累计专项扣除
    cumulative_special_deduction = (monthly_social + monthly_housing_fund + monthly_annuity) * month
    
    # 累计专项附加扣除
    cumulative_special_addition = monthly_special_additions * month
    
    # 累计其他扣除
    cumulative_other_deduction = monthly_other_deductions * month
    
    # 累计应纳税所得额
    cumulative_taxable_income = (
        cumulative_income
        - cumulative_deduction_fee
        - cumulative_special_deduction
        - cumulative_special_addition
        - cumulative_other_deduction
    )
    
    # 累计应纳税额
    cumulative_tax = calculate_tax(cumulative_taxable_income, MONTHLY_TAX_BRACKETS)
    
    # 上月累计税额（简化处理，这里用公式反推）
    if month == 1:
        monthly_tax = cumulative_tax
    else:
        prev_cumulative_income = monthly_income * (month - 1)
        prev_deduction = 5000 * (month - 1)
        prev_special = (monthly_social + monthly_housing_fund + monthly_annuity) * (month - 1)
        prev_additions = monthly_special_additions * (month - 1)
        prev_other = monthly_other_deductions * (month - 1)
        prev_taxable = (
            prev_cumulative_income - prev_deduction - prev_special 
            - prev_additions - prev_other
        )
        prev_tax = calculate_tax(prev_taxable, MONTHLY_TAX_BRACKETS)
        monthly_tax = cumulative_tax - prev_tax
    
    return monthly_tax, cumulative_tax


def calculate_annual_settlement(
    annual_income,
    annual_social,
    annual_housing_fund,
    annual_annuity=0,
    annual_special_additions=0,
    annual_other_deductions=0,
    annual_bonus=0,
    bonus_method='separate',
    unit_withheld=0
):
    """
    计算年度汇算清缴
    
    参数：
    - annual_income: 年度工资薪金收入
    - annual_social: 年度社保个人部分
    - annual_housing_fund: 年度公积金个人部分
    - annual_annuity: 年度职业年金个人部分
    - annual_special_additions: 年度专项附加扣除合计
    - annual_other_deductions: 年度其他扣除合计
    - annual_bonus: 年度奖金金额
    - bonus_method: 'separate' 单独计税 / 'combined' 并入综合所得
    - unit_withheld: 单位全年代扣代缴
    
    返回：
    - dict: 包含计算结果的字典
    """
    # 计算应纳税所得额
    taxable_income = (
        annual_income
        - 60000  # 基本减除费用
        - annual_social
        - annual_housing_fund
        - annual_annuity
        - annual_special_additions
        - annual_other_deductions
    )
    
    # 综合所得应纳税额
    income_tax = calculate_tax(taxable_income, TAX_BRACKETS_ANNUAL)
    
    # 奖金税额
    bonus_tax = calculate_annual_bonus_tax(annual_bonus, bonus_method)
    
    # 总税额
    if bonus_tax is not None:
        total_tax = income_tax + bonus_tax
    else:
        # 并入综合所得，重新计算
        combined_income = annual_income + annual_bonus
        combined_taxable = (
            combined_income
            - 60000
            - annual_social
            - annual_housing_fund
            - annual_annuity
            - annual_special_additions
            - annual_other_deductions
        )
        total_tax = calculate_tax(combined_taxable, TAX_BRACKETS_ANNUAL)
    
    # 对比结果
    difference = unit_withheld - total_tax
    
    # 判断结果
    if difference > 0:
        result = '退税'
        amount = difference
        message = f'您多缴了{difference:.2f}元，可以申请退税'
    elif difference < 0:
        result = '补税'
        amount = abs(difference)
        message = f'您需要补缴{abs(difference):.2f}元'
    else:
        result = '无需调整'
        amount = 0
        message = '您的税款已结清，无需办理汇算'
    
    return {
        'annual_income': annual_income,
        'total_deductions': (
            60000 + annual_social + annual_housing_fund + annual_annuity
            + annual_special_additions + annual_other_deductions
        ),
        'taxable_income': taxable_income,
        'income_tax': income_tax,
        'bonus_tax': bonus_tax if bonus_tax else 0,
        'total_tax': total_tax,
        'unit_withheld': unit_withheld,
        'difference': difference,
        'result': result,
        'amount': amount,
        'message': message
    }


def generate_monthly_details(
    monthly_income,
    monthly_social,
    monthly_housing_fund,
    monthly_annuity=0,
    monthly_special_additions=0,
    monthly_other_deductions=0
):
    """
    生成12个月的预扣预缴明细
    
    返回：
    - list: 每月明细列表
    """
    details = []
    cumulative_income = 0
    cumulative_deduction = 0
    cumulative_tax = 0
    
    for month in range(1, 13):
        monthly_tax, cumulative_tax = calculate_monthly_pre_tax(
            month,
            monthly_income,
            monthly_social,
            monthly_housing_fund,
            monthly_annuity,
            monthly_special_additions,
            monthly_other_deductions
        )
        
        cumulative_income += monthly_income
        monthly_deduction = 5000 + monthly_social + monthly_housing_fund + monthly_annuity + monthly_special_additions + monthly_other_deductions
        cumulative_deduction += monthly_deduction
        
        cumulative_taxable = cumulative_income - cumulative_deduction
        
        details.append({
            'month': month,
            'monthly_income': monthly_income,
            'cumulative_income': cumulative_income,
            'cumulative_deduction': cumulative_deduction,
            'cumulative_taxable': cumulative_taxable,
            'cumulative_tax': cumulative_tax,
            'monthly_tax': monthly_tax
        })
    
    return details


# ============================================================
# 主程序入口
# ============================================================

if __name__ == '__main__':
    # 示例：月薪1.2万，社保1800/月，公积金800/月，无职业年金
    # 专项附加扣除3500/月，无其他扣除，年终奖2万单独计税
    # 单位代扣6000
    
    monthly_income = 12000
    monthly_social = 800 + 200 + 100  # 养老+医疗+失业
    monthly_housing_fund = 800
    monthly_annuity = 0
    monthly_special_additions = 2000 + 1500  # 子女教育+住房租金
    monthly_other_deductions = 0
    annual_bonus = 20000
    bonus_method = 'separate'
    unit_withheld = 6000
    
    # 计算
    result = calculate_annual_settlement(
        annual_income=monthly_income * 12,
        annual_social=monthly_social * 12,
        annual_housing_fund=monthly_housing_fund * 12,
        annual_annuity=monthly_annuity * 12,
        annual_special_additions=monthly_special_additions * 12,
        annual_other_deductions=monthly_other_deductions,
        annual_bonus=annual_bonus,
        bonus_method=bonus_method,
        unit_withheld=unit_withheld
    )
    
    print("=" * 50)
    print("个人所得税计算结果")
    print("=" * 50)
    print(f"年度工资收入: ¥{result['annual_income']:,.2f}")
    print(f"扣除总计: ¥{result['total_deductions']:,.2f}")
    print(f"应纳税所得额: ¥{result['taxable_income']:,.2f}")
    print(f"工资薪金税额: ¥{result['income_tax']:,.2f}")
    print(f"年终奖税额: ¥{result['bonus_tax']:,.2f}")
    print(f"合计应纳税额: ¥{result['total_tax']:,.2f}")
    print(f"单位代扣代缴: ¥{result['unit_withheld']:,.2f}")
    print("-" * 50)
    print(f"结果: {result['result']} ¥{result['amount']:,.2f}")
    print(f"提示: {result['message']}")
    print("=" * 50)
