#!/usr/bin/env python3
"""
个人所得税计算器 - Streamlit Web 界面
支持快速估算、详细计算、批量 JSON 上传
"""

import sys
import os
import json
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.quick_calculator import quick_calculate, compare_bonus_methods
from scripts.tax_calculator import calculate_annual_settlement, generate_monthly_details

# ── 页面配置 ──
st.set_page_config(
    page_title="个人所得税计算器",
    page_icon="🧮",
    layout="centered",
)

# ── 城市社保公积金比例参考 ──
CITY_RATES = {
    "北京": 0.225,
    "上海": 0.175,
    "广州": 0.145,
    "深圳": 0.135,
    "杭州": 0.195,
    "成都": 0.155,
    "武汉": 0.155,
    "南京": 0.195,
    "重庆": 0.155,
    "苏州": 0.185,
    "其他": 0.175,
}

# ── 专项附加扣除配置说明 ──
SPECIAL_DEDUCTION_ITEMS = {
    "子女教育": {"key": "children_edu", "max": 2000, "step": 100, "help": "每个子女每月 2000 元"},
    "3岁以下婴幼儿照护": {"key": "infant_care", "max": 2000, "step": 100, "help": "每个婴幼儿每月 2000 元"},
    "赡养老人": {"key": "elderly_care", "max": 3000, "step": 100, "help": "每月 3000 元"},
    "住房贷款利息": {"key": "housing_loan", "max": 1000, "step": 100, "help": "首套住房，每月 1000 元"},
    "住房租金": {"key": "housing_rent", "max": 1500, "step": 100, "help": "根据城市 800-1500 元/月"},
    "继续教育": {"key": "continuing_edu", "max": 400, "step": 100, "help": "每月 400 元"},
}


# =============================================================
# 辅助函数
# =============================================================

def fmt(val):
    """格式化金额为中文货币字符串"""
    return f"¥{val:,.2f}"


def display_result_summary(result):
    """展示快速估算的结果摘要"""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("应纳税所得额", fmt(result["taxable_income"]))
    with c2:
        st.metric("年应纳税额", fmt(result["total_tax"]))
    with c3:
        net = result["annual_salary"] - result["total_tax"]
        st.metric("税后到手收入", fmt(net))

    with st.expander("查看详细明细"):
        detail = {
            "年度税前工资": result["annual_salary"],
            "扣除项目合计": result["total_deductions"],
            "应纳税所得额": result["taxable_income"],
            "工资薪金税额": result["income_tax"],
            "年终奖税额": result["bonus_tax"],
            "合计应纳税额": result["total_tax"],
            "实际税负率": f"{result['effective_rate'] * 100:.2f}%",
        }
        st.json(detail)


def display_bonus_warning(warning):
    """展示年终奖临界点预警"""
    if not warning or not warning.get("warnings"):
        return
    st.warning("⚠️ 年终奖临界点预警", icon="⚠️")
    for w in warning["warnings"]:
        st.write(f"- **{w['critical_point']:,}元** 临界点：{w['impact']}")
    if warning.get("suggestions"):
        for s in warning["suggestions"]:
            st.info(s["message"])


def build_special_additions(inputs):
    """将专项附加扣除输入项汇总为年度金额"""
    monthly = 0
    for item in SPECIAL_DEDUCTION_ITEMS.values():
        monthly += inputs.get(item["key"], 0)
    annual_special = monthly * 12
    annual_special += inputs.get("serious_illness", 0)  # 大病医疗为年度金额
    return annual_special


def build_other_deductions(inputs):
    """构建其他扣除（个人养老金 + 税优健康险）"""
    d = 0
    d += inputs.get("personal_pension", 0)  # 个人养老金，年度
    d += inputs.get("health_insurance", 0)  # 税优健康险，年度
    return d


# =============================================================
# Tab 1: 快速估算
# =============================================================

def render_quick_tab():
    st.subheader("快速估算年度个税")
    st.caption("适合简单场景，输入几项关键参数即可得到估算结果")

    with st.form("quick_form"):
        col1, col2 = st.columns(2)

        with col1:
            monthly_income = st.number_input(
                "月税前收入（元）", min_value=0, value=15000, step=1000
            )
            bonus_amount = st.number_input(
                "年终奖（元）", min_value=0, value=0, step=1000
            )

        with col2:
            city = st.selectbox("所在城市", list(CITY_RATES.keys()), index=1)
            default_rate = CITY_RATES.get(city, 0.175)
            social_insurance_rate = st.slider(
                "社保公积金个人总比例",
                min_value=0.0, max_value=0.50,
                value=default_rate, step=0.005,
                format="%.1f%%",
            )
            bonus_method = st.radio("年终奖计税方式", ["单独计税", "并入综合所得"])

        submitted = st.form_submit_button("开始估算", type="primary", use_container_width=True)

    if submitted:
        annual_salary = monthly_income * 12
        total_insurance = annual_salary * social_insurance_rate
        # 按 quick_calculator 默认逻辑拆分：社保 ~60%，公积金 ~40%
        annual_social = total_insurance * 0.6
        annual_housing_fund = total_insurance * 0.4
        bonus_method_val = "separate" if bonus_method == "单独计税" else "combined"

        result = quick_calculate(
            annual_salary=annual_salary,
            annual_social=annual_social,
            annual_housing_fund=annual_housing_fund,
            annual_special_additions=0,
            annual_other_deductions=0,
            annual_bonus=bonus_amount,
            bonus_method=bonus_method_val,
        )

        st.divider()
        st.success("估算完成")
        display_result_summary(result)

        if result.get("bonus_warning"):
            display_bonus_warning(result["bonus_warning"])

        # 年终奖计税方式对比
        if bonus_amount > 0:
            st.divider()
            st.subheader("年终奖计税方式对比")
            deductions = result["total_deductions"] - 60000
            comparison = compare_bonus_methods(annual_salary, bonus_amount, deductions)
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.metric("单独计税", fmt(comparison["separate_tax"]))
            with mc2:
                st.metric("并入综合所得", fmt(comparison["combined_tax"]))
            with mc3:
                st.metric(
                    "推荐方案",
                    comparison["better_method"],
                    delta=f"可节省 {fmt(comparison['tax_savings'])}",
                )


# =============================================================
# Tab 2: 详细计算
# =============================================================

def render_detailed_tab():
    st.subheader("详细年度汇算清缴")
    st.caption("支持全部专项附加扣除项目，更精确地模拟汇算清缴")

    with st.form("detailed_form"):
        col1, col2 = st.columns(2)
        with col1:
            monthly_salary = st.number_input(
                "月薪（元）", min_value=0, value=15000, step=1000
            )
            annual_bonus = st.number_input(
                "年终奖（元）", min_value=0, value=0, step=1000
            )
        with col2:
            other_income = st.number_input(
                "其他年度收入（元）", min_value=0, value=0, step=1000
            )
            unit_withheld = st.number_input(
                "单位全年已代扣代缴（元）", min_value=0.0, value=0.0, step=1000.0,
                format="%.2f",
            )

        bonus_method = st.radio("年终奖计税方式", ["单独计税", "并入综合所得"], horizontal=True)

        st.markdown("#### 社保公积金")
        col_rat, _ = st.columns([1, 1])
        with col_rat:
            social_insurance_rate = st.slider(
                "三险一金个人总比例",
                min_value=0.0, max_value=0.50,
                value=0.175, step=0.005,
                format="%.1f%%",
            )

        st.markdown("#### 专项附加扣除（月度金额）")
        sc1, sc2, sc3 = st.columns(3)
        ded_inputs = {}
        items_list = list(SPECIAL_DEDUCTION_ITEMS.items())
        for idx, (label, cfg) in enumerate(items_list):
            col = [sc1, sc2, sc3][idx % 3]
            with col:
                ded_inputs[cfg["key"]] = st.number_input(
                    f"{label}（元）",
                    min_value=0, max_value=cfg["max"],
                    value=0, step=cfg["step"],
                    help=cfg["help"],
                )

        st.markdown("#### 年度一次性扣除")
        ce1, ce2 = st.columns(2)
        with ce1:
            ded_inputs["serious_illness"] = st.number_input(
                "大病医疗（元/年）", min_value=0, max_value=80000,
                value=0, step=1000,
                help="医保目录内自付超过 15000 元的部分，据实扣除，上限 80000 元",
            )
            ded_inputs["personal_pension"] = st.number_input(
                "个人养老金（元/年）", min_value=0, max_value=12000,
                value=0, step=1000,
                help="个人向个人养老金账户缴存，上限 12000 元/年",
            )
        with ce2:
            ded_inputs["health_insurance"] = st.number_input(
                "税优健康险（元/年）", min_value=0, max_value=2400,
                value=0, step=200,
                help="税前扣除，上限 2400 元/年",
            )

        submitted = st.form_submit_button("开始计算", type="primary", use_container_width=True)

    if submitted:
        annual_income = monthly_salary * 12 + other_income
        total_insurance = monthly_salary * 12 * social_insurance_rate
        annual_social = total_insurance * 0.6
        annual_housing_fund = total_insurance * 0.4
        annual_special = build_special_additions(ded_inputs)
        annual_other = build_other_deductions(ded_inputs)
        bonus_method_val = "separate" if bonus_method == "单独计税" else "combined"

        result = calculate_annual_settlement(
            annual_income=annual_income,
            annual_social=annual_social,
            annual_housing_fund=annual_housing_fund,
            annual_special_additions=annual_special,
            annual_other_deductions=annual_other,
            annual_bonus=annual_bonus,
            bonus_method=bonus_method_val,
            unit_withheld=unit_withheld,
        )

        st.divider()
        st.success("计算完成")

        # 核心指标
        cols = st.columns(4)
        with cols[0]:
            st.metric("应纳税所得额", fmt(result["taxable_income"]))
        with cols[1]:
            st.metric("综合所得税额", fmt(result["income_tax"]))
        with cols[2]:
            st.metric("年终奖税额", fmt(result["bonus_tax"]))
        with cols[3]:
            st.metric("合计应纳税额", fmt(result["total_tax"]))

        # 汇算清缴结果
        if unit_withheld > 0:
            result_icon = {"退税": "🎉", "补税": "⚠️", "无需调整": "✅"}
            st.info(
                f"{result_icon.get(result['result'], '')} **{result['result']}**：{result['message']}"
            )

        with st.expander("查看完整明细"):
            detail = {
                "年度总收入": result["annual_income"],
                "扣除项目合计": result["total_deductions"],
                "应纳税所得额": result["taxable_income"],
                "综合所得税额": result["income_tax"],
                "年终奖税额": result["bonus_tax"],
                "合计应纳税额": result["total_tax"],
                "单位已代扣": result["unit_withheld"],
                "汇算结果": result["result"],
                "应退/补金额": result["amount"],
            }
            st.json(detail)

        # 月度预扣明细
        with st.expander("查看月度预扣预缴明细"):
            months = generate_monthly_details(
                monthly_income=monthly_salary,
                monthly_social=(annual_social / 12),
                monthly_housing_fund=(annual_housing_fund / 12),
                monthly_special_additions=(annual_special / 12),
                monthly_other_deductions=(annual_other / 12),
            )
            df = pd.DataFrame(months)
            df.columns = [
                "月份", "本月收入", "累计收入", "累计扣除",
                "累计应纳税所得额", "累计应纳税额", "本月预扣",
            ]
            df["本月收入"] = df["本月收入"].apply(fmt)
            df["累计收入"] = df["累计收入"].apply(fmt)
            df["累计扣除"] = df["累计扣除"].apply(fmt)
            df["累计应纳税所得额"] = df["累计应纳税所得额"].apply(fmt)
            df["累计应纳税额"] = df["累计应纳税额"].apply(fmt)
            df["本月预扣"] = df["本月预扣"].apply(fmt)
            st.dataframe(df, hide_index=True, use_container_width=True)


# =============================================================
# Tab 3: 批量 JSON 上传
# =============================================================

def render_batch_tab():
    st.subheader("批量 JSON 计算")
    st.caption("上传 JSON 文件，批量计算个人所得税")

    with st.expander("📄 JSON 格式说明", expanded=False):
        st.code(json.dumps([
            {
                "monthly_salary": 15000,
                "annual_bonus": 20000,
                "other_income": 0,
                "social_insurance_rate": 0.175,
                "bonus_method": "单独计税",
                "children_edu": 1000,
                "infant_care": 0,
                "elderly_care": 500,
                "housing_loan": 0,
                "housing_rent": 1500,
                "continuing_edu": 0,
                "serious_illness": 0,
                "personal_pension": 0,
                "health_insurance": 0,
                "unit_withheld": 0,
            }
        ], ensure_ascii=False, indent=2), language="json")

    uploaded = st.file_uploader(
        "选择 JSON 文件", type=["json"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        try:
            raw = uploaded.read().decode("utf-8")
            records = json.loads(raw)
            if isinstance(records, dict):
                records = [records]
        except Exception as e:
            st.error(f"JSON 解析失败：{e}")
            return

        if not records:
            st.warning("文件中没有数据")
            return

        st.info(f"共读取 {len(records)} 条记录")

        results = []
        progress = st.progress(0, text="计算中…")

        for i, rec in enumerate(records):
            try:
                monthly_salary = float(rec.get("monthly_salary", 0))
                annual_bonus = float(rec.get("annual_bonus", 0))
                other_income = float(rec.get("other_income", 0))
                rate = float(rec.get("social_insurance_rate", 0.175))
                bonus_method_raw = rec.get("bonus_method", "单独计税")
                bonus_method_val = "separate" if bonus_method_raw == "单独计税" else "combined"
                unit_withheld = float(rec.get("unit_withheld", 0))

                annual_income = monthly_salary * 12 + other_income
                total_insurance = monthly_salary * 12 * rate
                annual_social = total_insurance * 0.6
                annual_housing_fund = total_insurance * 0.4

                ded = {}
                for item in SPECIAL_DEDUCTION_ITEMS.values():
                    ded[item["key"]] = float(rec.get(item["key"], 0))
                ded["serious_illness"] = float(rec.get("serious_illness", 0))
                ded["personal_pension"] = float(rec.get("personal_pension", 0))
                ded["health_insurance"] = float(rec.get("health_insurance", 0))

                annual_special = build_special_additions(ded)
                annual_other = build_other_deductions(ded)

                result = calculate_annual_settlement(
                    annual_income=annual_income,
                    annual_social=annual_social,
                    annual_housing_fund=annual_housing_fund,
                    annual_special_additions=annual_special,
                    annual_other_deductions=annual_other,
                    annual_bonus=annual_bonus,
                    bonus_method=bonus_method_val,
                    unit_withheld=unit_withheld,
                )

                row = {
                    "序号": i + 1,
                    "月薪": monthly_salary,
                    "年终奖": annual_bonus,
                    "其他收入": other_income,
                    "应纳税所得额": result["taxable_income"],
                    "综合所得税额": result["income_tax"],
                    "年终奖税额": result["bonus_tax"],
                    "合计应纳税额": result["total_tax"],
                    "单位已代扣": result["unit_withheld"],
                    "汇算结果": result["result"],
                    "应退/补金额": result["amount"],
                }
                results.append(row)
            except Exception as e:
                results.append({
                    "序号": i + 1,
                    "月薪": rec.get("monthly_salary", "?"),
                    "错误": str(e),
                })

            progress.progress((i + 1) / len(records),
                              text=f"计算中… ({i + 1}/{len(records)})")

        progress.empty()

        df = pd.DataFrame(results)
        ok = df[~df["错误"].notna()] if "错误" in df.columns else df

        st.success(f"成功计算 {len(ok)} 条")
        st.dataframe(df, hide_index=True, use_container_width=True)

        # 下载 CSV
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 下载结果 (CSV)",
            data=csv,
            file_name="tax_results.csv",
            mime="text/csv",
            type="primary",
        )

        # 下载 JSON
        json_str = json.dumps(
            results, ensure_ascii=False, indent=2, default=str
        )
        st.download_button(
            label="📥 下载结果 (JSON)",
            data=json_str,
            file_name="tax_results.json",
            mime="application/json",
        )


# =============================================================
# 主页面
# =============================================================

st.title("🧮 个人所得税计算器")
st.markdown(
    "基于 **2025 年个人所得税法**，支持累计预扣预缴与年度汇算清缴。"
)

tab1, tab2, tab3 = st.tabs(["快速估算", "详细计算", "批量 JSON 上传"])

with tab1:
    render_quick_tab()

with tab2:
    render_detailed_tab()

with tab3:
    render_batch_tab()

st.divider()
st.caption(
    "⚠️ 计算结果仅供参考，实际税额以税务机关核定为准。"
    "数据仅在浏览器本地计算，不会上传至任何服务器。"
)
