# 个人所得税智能计算助手

## 技能简介

个人所得税智能计算助手是一款基于中国税务局官方政策设计的专业税务计算工具，帮助用户准确计算年度综合所得应纳税额，自动识别可享受的专项附加扣除项目，并与单位代扣代缴金额进行对比分析，最终给出退税/补税建议。

### 核心功能亮点

| 功能 | 说明 |
|------|------|
| 🔢 **九项扣除全覆盖** | 涵盖7项专项附加扣除 + 个人养老金 + 税优健康险 |
| 📊 **累计预扣预缴法** | 完全按照税务局月度累计计算规则，与单位发薪逻辑一致 |
| ⚖️ **精准对比分析** | 自动对比年度应纳税额与单位代扣代缴，判断退税/补税 |
| 📝 **逐月精细计算** | 支持12个月逐月输入，确保计算精准无误 |
| 💼 **职业年金支持** | 明确包含职业年金个人缴纳部分扣除 |
| 🏦 **个人养老金优惠计算** | 一键演示缴存1.2万能省多少钱，适合服务高收入客户 |
| ⚠️ **年终奖临界点预警** | v1.1.0新增：智能识别年终奖临界点，提供避税建议 |
| 🔄 **非交互式计算** | v1.1.1修复：JSON输入模式现已执行实际税额计算 |

### 适用场景

- **年终汇算清缴**：每年3-6月个税汇算期，自主核算应退/应补税额
- **年度收入规划**：年初预估全年收入，合理安排专项附加扣除申报
- **跳槽/离职计算**：计算多单位收入合并计税
- **个税自查**：核对单位代扣代缴是否准确
- **专项附加扣除规划**：了解可享受的扣除政策，优化税务筹划
- **个人养老金推广服务**：演示缴存1.2万/年的税收优惠

### 触发词设置

```
触发词（任选其一）：
个税计算、个税计算器、个人所得税计算、计算个税、工资扣税、
退税计算、补税计算、年终奖计税、个税汇算、专项附加扣除、
个人养老金优惠、个人养老金计算、养老金省税
```

---

## 🏦 独立功能：个人养老金税收优惠计算

此功能专门用于向高收入客户演示个人养老金税收优惠，帮助客户理解缴存1.2万/年的实际收益。

### 功能入口

```
用户输入：个人养老金优惠 / 养老金省税 / 缴存1.2万能省多少钱
```

### 计算逻辑

```python
def calculate_pension_tax_benefit(annual_income, other_deductions_monthly, insurance_monthly):
    """
    计算个人养老金税收优惠
    """
    basic_deduction = 60000
    special_deduction = insurance_monthly * 12
    special_addition = other_deductions_monthly * 12
    
    taxable_income_before = annual_income - basic_deduction - special_deduction - special_addition
    taxable_income_after = taxable_income_before - 12000  # 个人养老金扣除
    
    tax_before = calculate_tax_from_table(taxable_income_before)
    tax_after = calculate_tax_from_table(taxable_income_after)
    
    return {
        'tax_saved': tax_before - tax_after,
        'actual_cost': 12000 - (tax_before - tax_after),
        'return_rate': (tax_before - tax_after) / (12000 - (tax_before - tax_after))
    }
```

### 不同收入档位收益速查

| 月收入 | 年收入 | 适用税率 | 缴存1.2万能省税 | 实际成本 | 收益率 |
|--------|--------|----------|-----------------|----------|--------|
| 3万    | 36万   | 10%      | ¥1,200          | ¥10,800  | 11%    |
| 5万    | 60万   | 20%      | ¥2,400          | ¥9,600   | 25%    |
| 8万    | 96万   | 35%      | ¥4,200          | ¥7,800   | 54%    |
| 10万+  | 120万+ | 45%      | ¥5,400          | ¥6,600   | 82%    |

> 💡 提示：收入越高，税收优惠越明显！

---

## 使用流程

### 方式一：交互式问卷（默认）

**启动后按步骤输入：**

```
🏠 欢迎使用【个人所得税智能计算助手】

📅 第一步：选择年度（默认2024）
👤 第二步：纳税人身份（居民/非居民）
💰 第三步：收入信息（逐月或月均）
📋 第四步：专项扣除（社保公积金）
📝 第五步：专项附加扣除（7项）
💼 第六步：其他扣除（个人养老金等）
📋 第七步：单位代扣代缴信息
```

### 方式二：JSON非交互式（v1.1.0 新增）

适合程序调用和批量计算场景：

```bash
python questionnaire.py --json-input '{
    "monthly_salary": 30000,
    "bonus": 36000,
    "bonus_method": "separate",
    "monthly_social": 3000,
    "monthly_housing_fund": 2500,
    "special_additions": {
        "children_education": 24000,
        "elderly_support": 36000
    },
    "personal_pension": 12000
}'
```

**支持的JSON字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| year | string | 年度（默认2024） |
| monthly_salary | number | 月均税前工资 |
| monthly_incomes | array | 逐月工资列表（12项） |
| bonus | number | 年终奖金额 |
| bonus_method | string | separate/combined |
| monthly_social | number | 月社保个人部分 |
| monthly_housing_fund | number | 月公积金个人部分 |
| monthly_annuity | number | 月职业年金个人部分 |
| special_additions | object | 专项附加扣除对象 |
| personal_pension | number | 个人养老金年缴存额 |
| unit_withheld | number | 单位年代扣代缴税额 |

### 方式三：快速计算器

适用于简单场景的快速估算：

```bash
python quick_calculator.py <年工资> [年奖金]
```

**示例：**
```bash
python quick_calculator.py 144000 20000
```

> v1.1.0 会在年终奖计算结果中自动显示临界点预警！

---

## 计算逻辑

### 核心计算公式

```
应纳税所得额 = 综合所得收入额 - 60000 - 专项扣除 - 专项附加扣除 - 其他扣除
应纳税额 = 应纳税所得额 × 适用税率 - 速算扣除数
```

### 累计预扣预缴法

```python
def calculate_monthly_tax(month, monthly_income_list, monthly_deductions):
    cumulative_income = sum(monthly_income_list[:month])
    cumulative_deduction_fee = 5000 * month
    cumulative_taxable = cumulative_income - cumulative_deduction_fee - sum(monthly_deductions[:month])
    return cumulative_taxable
```

### 全年一次性奖金计税

```python
def calculate_bonus_tax(bonus, method='separate'):
    if method == 'separate':
        # 单独计税：奖金÷12找税率
        monthly_bonus = bonus / 12
        # 月度税率表（3%-45%）
        ...
    else:
        # 并入综合所得
        ...
```

### ⚠️ 年终奖临界点预警（v1.1.0 新增）

年终奖在以下临界点附近时，可能出现"多发1元，多交几千元税"：

| 临界值 | 税率变化 | 边际税负率 |
|:------:|:--------:|:----------:|
| 36,000元 | 3%→10% | 最高230% |
| 144,000元 | 10%→20% | 最高1150% |
| 300,000元 | 20%→25% | 最高2100% |
| 420,000元 | 25%→30% | 最高2400% |
| 660,000元 | 30%→35% | 最高2700% |
| 960,000元 | 35%→45% | 最高4950% |

---

## 输出模板

### 完整计算结果报告

```markdown
# 📊 个人所得税年度汇算清缴报告

## 一、收入汇总
| 收入类型 | 金额 |
|----------|------|
| 工资薪金（12个月） | ¥_____ |
| 全年一次性奖金 | ¥_____ |
| 综合所得收入总额 | ¥_____ |

## 二、扣除项目
| 类别 | 年度金额 |
|------|----------|
| 基本减除费用 | ¥60,000 |
| 专项扣除 | ¥_____ |
| 专项附加扣除 | ¥_____ |
| 其他扣除 | ¥_____ |
| 扣除总计 | ¥_____ |

## 三、应纳税额
| 项目 | 金额 |
|------|------|
| 应纳税所得额 | ¥_____ |
| 适用税率 | ___% |
| 年度应纳税额 | ¥_____ |
| 全年一次性奖金税额 | ¥_____ |
| **合计应纳税额** | **¥_____** |

## 四、退税/补税结果
| 项目 | 金额 |
|------|------|
| 单位已扣税额 | ¥_____ |
| 应纳税额 | ¥_____ |
| **应退税/补税** | **¥_____** |
```

---

## 📚 参考文档

详细税率表、专项附加扣除政策、FAQ等内容请参阅：

- `references/tax_reference.md` - 完整税率表、FAQ、政策依据
- `references/deduction-policy.md` - 专项附加扣除详细政策
- `references/calculation-examples.md` - 计算示例

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2026-04-22 | 初始版本，九项扣除覆盖 |
| v1.0.1 | 2026-04-22 | 修复代码与文档不一致问题 |
| v1.1.0 | 2026-04-22 | 新增年终奖临界点预警、非交互式计算模式 |
| v1.1.1 | 2026-04-24 | **重要修复**：JSON模式现执行实际税额计算 |

### v1.1.1 重要修复 (2026-04-24)

**修复严重缺陷**：`--json-input` 模式之前只展示采集信息，不执行税额计算
- 新增 `perform_tax_calculation()` 函数
- JSON模式现输出完整汇算清缴结果（应纳税额、退税/补税）

### v1.1.0 新增功能

1. **年终奖临界点避税提示**：自动检测年终奖是否处于临界点附近，提供避税建议
2. **非交互式计算模式**：支持 `--json-input` 参数，适合程序调用和批量计算
3. **文档拆分优化**：税率表和FAQ独立为参考文档，便于维护
