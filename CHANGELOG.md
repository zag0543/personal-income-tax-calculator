# 个人所得税智能计算助手 - 改进清单

## v1.1.1 重要修复（2026-04-24）

### 🐛 严重缺陷修复
- **修复JSON模式不执行计算的问题**：`questionnaire.py --json-input` 之前只展示采集信息，不执行税额计算
- 新增 `perform_tax_calculation()` 函数调用 `tax_calculator.py`
- JSON模式现在输出完整的汇算清缴结果（应纳税额、退税/补税）
- 文档描述与代码行为现已一致

**测试验证**：
```bash
python questionnaire.py --json-input '{"monthly_salary": 30000, "bonus": 36000, ...}'
# 输出：应纳税额¥21,870，退税¥23,130 ✅
```

---

## v1.0.0 当前版本（2026-04-22）

### ✅ 已发布功能
- 九项扣除全覆盖（7项专项附加扣除 + 个人养老金 + 税优健康险）
- 累计预扣预缴计算
- 个人养老金税收优惠计算模块
- 年金险收益对比演示
- 退税/补税一键对比
- 年终奖双轨计税（单独计税/并入综合所得）

### 📊 用户反馈统计（截至 2026-04-22 11:20）
- 下载量：21
- 评测数：18
- 平均评分：4.4/5.0
- 5星评测：8条
- 4星评测：10条

---

## v1.0.1 修复更新（2026-04-22）

### 🔧 Bug修复
- ✅ 修复 `quick_calculator.py` 缺少 `calculate_pension_tax_benefit` 函数的问题
- ✅ 新增 `print_pension_benefit()` 打印函数
- ✅ 文档与代码现已一致

---

## v1.1.0 功能增强（2026-04-22）

### 🆕 新增功能

#### 1. 年终奖临界点避税提示 ⭐
**来源**：WPS 灵犀、鸿渐
**功能说明**：
- 在年终奖计算结果中增加临界点预警
- 自动检测以下临界点：36,000 / 144,000 / 300,000 / 420,000 / 660,000 / 960,000 元
- 提供避税建议和最优调整方案
- 打印清晰的警告和建议信息

**实现位置**：
- `scripts/quick_calculator.py` 新增 `BONUS_CRITICAL_POINTS` 常量
- 新增 `check_bonus_critical_point()` 函数
- 新增 `print_bonus_warning()` 函数
- `quick_calculate()` 返回结果增加 `bonus_warning` 字段

**示例输出**：
```
⚠️  年终奖临界点预警
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 您的年终奖处于以下临界点附近：

  🔸 36,000元临界点
     税率从3%跳至10%
     ⚠️ 多发1元多交税230.00元，实际税率23000.00%

💡 避税建议：

  1. 建议将奖金调整为35,999元，比36,000元少发1元，
     可节税230.00元
```

#### 2. 非交互式计算模式 ⭐
**来源**：批量计算需求
**功能说明**：
- `questionnaire.py` 新增 `--json-input` 参数
- 支持通过命令行直接传入JSON数据进行计算
- 无需交互，适合程序调用和批量处理
- 新增 `--output-json` 参数，输出JSON格式结果

**使用方法**：
```bash
# 交互式模式（保持原有功能）
python questionnaire.py

# 非交互式JSON输入
python questionnaire.py --json-input '{"monthly_salary": 30000, "bonus": 50000}'

# 输出JSON格式结果
python questionnaire.py --json-input '{"monthly_salary": 30000}' --output-json
```

**支持的JSON字段**：
```json
{
    "year": "2024",
    "identity": "居民个人",
    "monthly_salary": 30000,
    "monthly_incomes": [30000, 30000, ...],
    "bonus": 50000,
    "bonus_method": "separate",
    "monthly_social": 3000,
    "monthly_housing_fund": 2500,
    "monthly_annuity": 500,
    "special_additions": {
        "children_education": 24000,
        "elderly_support": 36000
    },
    "personal_pension": 12000,
    "tax_health": 2400,
    "enterprise_annuity": 0,
    "commercial_health": 0,
    "unit_withheld": 50000
}
```

#### 3. 文档拆分优化
**来源**：SKILL.md 文档过长（1169行）
**功能说明**：
- SKILL.md 主文档精简至约 230 行
- 将税率表、FAQ、政策依据移至 `references/tax_reference.md`
- 新增完整的年终奖临界点说明
- 新增详细FAQ和问题解答

**文档结构**：
```
tax-calculator/
├── SKILL.md                    # 主文档（精简版）
└── references/
    ├── tax_reference.md         # 新增：税率表、FAQ、政策依据
    ├── deduction-policy.md      # 专项附加扣除详细政策
    └── calculation-examples.md  # 计算示例
```

---

### 🔧 代码优化

#### quick_calculator.py
| 项目 | 说明 |
|------|------|
| 新增常量 | `BONUS_CRITICAL_POINTS` 临界点定义 |
| 新增函数 | `check_bonus_critical_point()` 临界点检测 |
| 新增函数 | `print_bonus_warning()` 打印警告信息 |
| 修改函数 | `quick_calculate()` 增加 `bonus_warning` 返回值 |
| 代码注释 | 增加 v1.1.0 版本标识 |

#### questionnaire.py
| 项目 | 说明 |
|------|------|
| 新增导入 | `json`, `argparse` 模块 |
| 新增类方法 | `load_from_json()` JSON数据加载 |
| 新增函数 | `print_json_result()` JSON格式输出 |
| 新增参数 | `--json-input`, `--output-json`, `--version` |
| 代码注释 | 增加 v1.1.0 版本标识 |

---

### 📋 测试建议

1. **年终奖临界点测试**：
   - 测试边界值：35,999 / 36,000 / 36,001
   - 测试其他临界点：143,999 / 144,000 等
   - 验证警告信息是否正确显示

2. **JSON输入测试**：
   - 测试完整JSON数据
   - 测试部分字段缺失情况
   - 测试JSON格式错误处理

3. **回归测试**：
   - 确保原有交互模式不受影响
   - 确保快速计算器功能正常

---

### 📈 预期改进效果

基于用户评测反馈，v1.1.0 预计可提升：
- 用户评分：4.4 → 4.6（+0.2）
- 核心问题解决：年终奖临界点提醒（高优先级）
- 使用便利性：非交互式模式支持批量计算

---

## 未来版本计划（v1.2.0+）

### 🔴 高优先级
- 多单位收入合并计算（跳槽场景）
- PDF/报告导出功能

### 🟡 中优先级
- 历史记录保存功能
- 地区差异自动识别
- 年度趋势分析功能

### 🟢 低优先级
- UI交互优化
- 中低收入群体分析
- 批量计算功能（企业HR场景）
- 大病医疗医保API对接

---

*最后更新：2026-04-22*
