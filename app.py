#!/usr/bin/env python3
"""
个人所得税计算器 - Streamlit Web 界面
支持快速估算、详细计算、批量 JSON 上传、扣除项体检、个人养老金优惠、夫妻共同申报
"""

import sys
import os
import json
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.quick_calculator import quick_calculate, compare_bonus_methods, calculate_pension_tax_benefit
from scripts.tax_calculator import calculate_annual_settlement, generate_monthly_details
from scripts.deduction_checkup import DeductionCheckupCollector, DEDUCTION_POLICIES

# ── 页面配置 ──
st.set_page_config(
    page_title="个人所得税计算器",
    page_icon="🧮",
    layout="centered",
)

# ── 城市社保公积金比例参考（扩展版） ──
CITY_RATES = {
    # 一线城市
    "北京": 0.225,
    "上海": 0.175,
    "广州": 0.145,
    "深圳": 0.135,
    # 新一线城市
    "成都": 0.155,
    "杭州": 0.195,
    "重庆": 0.155,
    "武汉": 0.155,
    "西安": 0.155,
    "苏州": 0.185,
    "南京": 0.195,
    "天津": 0.185,
    "长沙": 0.155,
    "郑州": 0.155,
    "东莞": 0.135,
    "青岛": 0.185,
    "合肥": 0.155,
    "佛山": 0.135,
    # 二线城市
    "宁波": 0.185,
    "昆明": 0.155,
    "沈阳": 0.185,
    "大连": 0.185,
    "济南": 0.185,
    "厦门": 0.145,
    "福州": 0.155,
    "哈尔滨": 0.185,
    "温州": 0.185,
    "石家庄": 0.185,
    "太原": 0.155,
    "贵阳": 0.155,
    "南昌": 0.155,
    "南宁": 0.155,
    "海口": 0.155,
    "长春": 0.185,
    "兰州": 0.155,
    "乌鲁木齐": 0.155,
    # 其他
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


def get_tax_rate_for_income(taxable_income):
    """根据应纳税所得额估算适用税率"""
    brackets = [
        (36000, 0.03),
        (144000, 0.10),
        (300000, 0.20),
        (420000, 0.25),
        (660000, 0.30),
        (960000, 0.35),
        (float('inf'), 0.45),
    ]
    for threshold, rate in brackets:
        if taxable_income <= threshold:
            return rate
    return 0.45


# ── 初始化共享基础信息 ──
SHARED_DEFAULTS = {
    "monthly_income": 15000,
    "annual_bonus": 0,
    "city": "上海",
    "insurance_rate": 0.175,
    "bonus_method": "单独计税",
    "children_edu": 0,
    "infant_care": 0,
    "elderly_care": 0,
    "housing_loan": 0,
    "housing_rent": 0,
    "continuing_edu": 0,
    "serious_illness": 0,
    "personal_pension": 0,
    "health_insurance": 0,
    "other_income": 0,
    "unit_withheld": 0,
}

if "shared" not in st.session_state:
    st.session_state.shared = dict(SHARED_DEFAULTS)


def sync_to_shared(source):
    """将源 dict 中的值同步到共享基础信息"""
    for k in SHARED_DEFAULTS:
        if k in source:
            st.session_state.shared[k] = source[k]


def render_sidebar():
    """侧边栏基础信息配置"""
    with st.sidebar:
        st.markdown("### 📋 基础信息")
        st.caption("在此设置公共参数，所有板块自动读取")

        with st.expander("💰 收入信息", expanded=True):
            st.session_state.shared["monthly_income"] = st.number_input(
                "月税前收入（元）", min_value=0,
                value=st.session_state.shared["monthly_income"],
                step=1000, key="sb_income",
            )
            st.session_state.shared["annual_bonus"] = st.number_input(
                "年终奖（元）", min_value=0,
                value=st.session_state.shared["annual_bonus"],
                step=1000, key="sb_bonus",
            )

        with st.expander("🏙️ 城市与社保", expanded=True):
            city_idx = list(CITY_RATES.keys()).index(
                st.session_state.shared["city"]
            ) if st.session_state.shared["city"] in CITY_RATES else 0

            st.session_state.shared["city"] = st.selectbox(
                "所在城市", list(CITY_RATES.keys()),
                index=city_idx, key="sb_city",
            )
            default_rate = CITY_RATES.get(
                st.session_state.shared["city"], 0.175
            )
            st.session_state.shared["insurance_rate"] = st.slider(
                "社保公积金个人比例", 0.0, 0.50,
                value=default_rate, step=0.005,
                format="%.1f%%", key="sb_rate",
            )

        with st.expander("📝 专项附加扣除（月）", expanded=False):
            sc1, sc2 = st.columns(2)
            with sc1:
                st.session_state.shared["children_edu"] = st.number_input(
                    "子女教育", 0, 2000,
                    value=st.session_state.shared["children_edu"],
                    step=100, key="sb_ce",
                )
                st.session_state.shared["infant_care"] = st.number_input(
                    "婴幼儿照护", 0, 2000,
                    value=st.session_state.shared["infant_care"],
                    step=100, key="sb_ic",
                )
                st.session_state.shared["elderly_care"] = st.number_input(
                    "赡养老人", 0, 3000,
                    value=st.session_state.shared["elderly_care"],
                    step=100, key="sb_ec",
                )
            with sc2:
                st.session_state.shared["housing_loan"] = st.number_input(
                    "住房贷款利息", 0, 1000,
                    value=st.session_state.shared["housing_loan"],
                    step=100, key="sb_hl",
                )
                st.session_state.shared["housing_rent"] = st.number_input(
                    "住房租金", 0, 1500,
                    value=st.session_state.shared["housing_rent"],
                    step=100, key="sb_hr",
                )
                st.session_state.shared["continuing_edu"] = st.number_input(
                    "继续教育", 0, 400,
                    value=st.session_state.shared["continuing_edu"],
                    step=100, key="sb_cedu",
                )

        with st.expander("🏥 其他扣除（年）", expanded=False):
            st.session_state.shared["personal_pension"] = st.number_input(
                "个人养老金", 0, 12000,
                value=st.session_state.shared["personal_pension"],
                step=1000, key="sb_pp",
            )
            st.session_state.shared["health_insurance"] = st.number_input(
                "税优健康险", 0, 2400,
                value=st.session_state.shared["health_insurance"],
                step=200, key="sb_hi",
            )

        # 状态提示
        st.divider()
        income = st.session_state.shared["monthly_income"]
        city = st.session_state.shared["city"]
        st.caption(f"✅ 已配置：月薪 ¥{income:,} · {city}")
        st.caption("💡 切换板块后可直接[导入基础信息]")


# =============================================================
# Tab 1: 快速估算
# =============================================================

def render_quick_tab():
    st.subheader("快速估算年度个税")
    st.caption("适合简单场景，输入几项关键参数即可得到估算结果")

    s = st.session_state.shared

    # 显示从基础信息导入的值
    st.info(
        f"📥 已加载基础信息：月薪 **¥{s['monthly_income']:,}** · "
        f"年终奖 **¥{s['annual_bonus']:,}** · "
        f"城市 **{s['city']}** · "
        f"比例 **{s['insurance_rate']*100:.1f}%**",
        icon="💡",
    )

    with st.form("quick_form"):
        col1, col2 = st.columns(2)

        with col1:
            monthly_income = st.number_input(
                "月税前收入（元）", min_value=0,
                value=s["monthly_income"], step=1000,
            )
            bonus_amount = st.number_input(
                "年终奖（元）", min_value=0,
                value=s["annual_bonus"], step=1000,
            )

        with col2:
            city = st.selectbox("所在城市", list(CITY_RATES.keys()),
                                index=list(CITY_RATES.keys()).index(s["city"])
                                if s["city"] in CITY_RATES else 1)
            default_rate = CITY_RATES.get(city, 0.175)
            social_insurance_rate = st.slider(
                "社保公积金个人总比例",
                min_value=0.0, max_value=0.50,
                value=default_rate, step=0.005,
                format="%.1f%%",
            )
            bonus_method = st.radio("年终奖计税方式",
                                    ["单独计税", "并入综合所得"],
                                    index=0 if s["bonus_method"] == "单独计税" else 1)

        submitted = st.form_submit_button("开始估算", type="primary", use_container_width=True)

    # 同步成功提示（跨 rerun 保持）
    if st.session_state.get("sync_quick_ok"):
        st.success("✅ 已保存到侧边栏基础信息！")
        st.session_state.sync_quick_ok = False

    if submitted:
        annual_salary = monthly_income * 12
        total_insurance = annual_salary * social_insurance_rate
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

        # 同步到基础信息
        col_a, _ = st.columns([1, 2])
        with col_a:
            if st.button("💾 保存此数据到基础信息", key="sync_quick", use_container_width=True):
                sync_to_shared({
                    "monthly_income": monthly_income,
                    "annual_bonus": bonus_amount,
                    "city": city,
                    "insurance_rate": social_insurance_rate,
                    "bonus_method": bonus_method,
                })
                st.session_state.sync_quick_ok = True
                st.rerun()


# =============================================================
# Tab 2: 详细计算
# =============================================================

def render_detailed_tab():
    st.subheader("详细年度汇算清缴")
    st.caption("支持全部专项附加扣除项目，更精确地模拟汇算清缴")

    s = st.session_state.shared
    st.info(
        f"📥 已加载基础信息：月薪 **¥{s['monthly_income']:,}** · "
        f"年终奖 **¥{s['annual_bonus']:,}** · "
        f"比例 **{s['insurance_rate']*100:.1f}%**",
        icon="💡",
    )

    with st.form("detailed_form"):
        col1, col2 = st.columns(2)
        with col1:
            monthly_salary = st.number_input(
                "月薪（元）", min_value=0,
                value=s["monthly_income"], step=1000,
            )
            annual_bonus = st.number_input(
                "年终奖（元）", min_value=0,
                value=s["annual_bonus"], step=1000,
            )
        with col2:
            other_income = st.number_input(
                "其他年度收入（元）", min_value=0,
                value=s["other_income"], step=1000,
            )
            unit_withheld = st.number_input(
                "单位全年已代扣代缴（元）", min_value=0.0,
                value=float(s["unit_withheld"]), step=1000.0,
                format="%.2f",
            )

        bonus_method = st.radio("年终奖计税方式", ["单独计税", "并入综合所得"], horizontal=True,
                                index=0 if s["bonus_method"] == "单独计税" else 1)

        st.markdown("#### 社保公积金")
        col_rat, _ = st.columns([1, 1])
        with col_rat:
            social_insurance_rate = st.slider(
                "三险一金个人总比例",
                min_value=0.0, max_value=0.50,
                value=s["insurance_rate"], step=0.005,
                format="%.1f%%",
            )

        st.markdown("#### 专项附加扣除（月度金额）")
        sc1, sc2, sc3 = st.columns(3)
        ded_inputs = {}
        items_list = list(SPECIAL_DEDUCTION_ITEMS.items())
        for idx, (label, cfg) in enumerate(items_list):
            col = [sc1, sc2, sc3][idx % 3]
            with col:
                ded_val = s.get(cfg["key"], 0)
                ded_inputs[cfg["key"]] = st.number_input(
                    f"{label}（元）",
                    min_value=0, max_value=cfg["max"],
                    value=ded_val, step=cfg["step"],
                    help=cfg["help"],
                )

        st.markdown("#### 年度一次性扣除")
        ce1, ce2 = st.columns(2)
        with ce1:
            ded_inputs["serious_illness"] = st.number_input(
                "大病医疗（元/年）", min_value=0, max_value=80000,
                value=s["serious_illness"], step=1000,
                help="医保目录内自付超过 15000 元的部分，据实扣除，上限 80000 元",
            )
            ded_inputs["personal_pension"] = st.number_input(
                "个人养老金（元/年）", min_value=0, max_value=12000,
                value=s["personal_pension"], step=1000,
                help="个人向个人养老金账户缴存，上限 12000 元/年",
            )
        with ce2:
            ded_inputs["health_insurance"] = st.number_input(
                "税优健康险（元/年）", min_value=0, max_value=2400,
                value=s["health_insurance"], step=200,
                help="税前扣除，上限 2400 元/年",
            )

        submitted = st.form_submit_button("开始计算", type="primary", use_container_width=True)

    # 同步成功提示（跨 rerun 保持）
    if st.session_state.get("sync_detailed_ok"):
        st.success("✅ 已保存到侧边栏基础信息！")
        st.session_state.sync_detailed_ok = False

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

        r1, r2 = st.columns(2)
        with r1:
            st.metric("应纳税所得额", fmt(result["taxable_income"]))
            st.metric("年终奖税额", fmt(result["bonus_tax"]))
        with r2:
            st.metric("综合所得税额", fmt(result["income_tax"]))
            st.metric("合计应纳税额", fmt(result["total_tax"]))

        if unit_withheld > 0:
            result_icon = {"退税": "🎉", "补税": "⚠️", "无需调整": "✅"}
            st.info(
                f"{result_icon.get(result['result'], '')} **{result['result']}**：{result['message']}"
            )

        with st.expander("查看完整明细"):
            detail = {
                "年度总收入": fmt(result["annual_income"]),
                "扣除项目合计": fmt(result["total_deductions"]),
                "应纳税所得额": fmt(result["taxable_income"]),
                "综合所得税额": fmt(result["income_tax"]),
                "年终奖税额": fmt(result["bonus_tax"]),
                "合计应纳税额": fmt(result["total_tax"]),
                "单位已代扣": fmt(result["unit_withheld"]),
                "汇算结果": result["result"],
                "应退/补金额": fmt(result["amount"]),
            }
            st.json(detail)

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

        # 同步到基础信息
        col_a, _ = st.columns([1, 2])
        with col_a:
            if st.button("💾 保存此数据到基础信息", key="sync_detailed", use_container_width=True):
                sync_to_shared({
                    "monthly_income": monthly_salary,
                    "annual_bonus": annual_bonus,
                    "other_income": other_income,
                    "insurance_rate": social_insurance_rate,
                    "bonus_method": bonus_method,
                    **ded_inputs,
                })
                st.session_state.sync_detailed_ok = True
                st.rerun()


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

        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 下载结果 (CSV)",
            data=csv,
            file_name="tax_results.csv",
            mime="text/csv",
            type="primary",
        )

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
# Tab 4: 扣除项体检
# =============================================================

def render_checkup_tab():
    st.subheader("🔍 扣除项体检")
    st.caption("5 分钟快速诊断，检查您是否有遗漏的专项附加扣除项目")

    st.markdown("""
    > 通过回答几个简单问题，系统将自动检查 **9 项扣除政策** 的适用情况，
    > 生成个性化体检报告，帮您发现可能遗漏的扣除项，合法合理节税。
    """)

    with st.expander("📋 九项扣除政策一览", expanded=False):
        cols = st.columns(3)
        policies = [
            ("👶 子女教育", "每个子女 2000元/月", "3岁至博士研究生"),
            ("👶 婴幼儿照护", "每个婴幼儿 2000元/月", "0-3岁"),
            ("📚 继续教育", "400元/月 或 3600元/次", "学历教育/职业证书"),
            ("🏥 大病医疗", "自付超15000元部分，上限85000元/年", "医保目录内"),
            ("🏠 住房贷款利息", "1000元/月", "首套房贷款"),
            ("🏠 住房租金", "800-1500元/月", "工作城市无自有住房"),
            ("👴👵 赡养老人", "独生子女3000元/月", "父母满60岁"),
            ("💰 个人养老金", "限额12000元/年", "试点城市"),
            ("🏥 税优健康险", "限额2400元/年", "指定产品"),
        ]
        for i, (name, std, cond) in enumerate(policies):
            col = cols[i % 3]
            with col:
                st.markdown(f"**{name}**")
                st.markdown(f"*标准：{std}*")
                st.markdown(f"*条件：{cond}*")
                st.divider()

    # 使用 session_state 保存问卷进度
    if "checkup_step" not in st.session_state:
        st.session_state.checkup_step = 0
        st.session_state.checkup_data = {}
        st.session_state.checkup_report = None

    data = st.session_state.checkup_data
    step = st.session_state.checkup_step

    # 步骤进度
    total_steps = 5
    progress_text = ["基本信息", "家庭与住房", "教育与健康", "保障类支出", "工作与租金"]
    st.progress(step / total_steps, text=f"第 {min(step + 1, total_steps)} 步：{progress_text[min(step, total_steps - 1)]}" if step < total_steps else "完成")

    if step < total_steps:
        with st.container(border=True):
            if step == 0:
                st.markdown("#### 📋 第一步：基本信息")
                income_range = st.selectbox(
                    "您的年收入大概是多少？",
                    options=[
                        "6万元以下",
                        "6-12万元",
                        "12-20万元",
                        "20-36万元",
                        "36万元以上",
                    ],
                    index=1,
                    key="ck_income",
                )
                income_ranges = [
                    (0, 60000), (60000, 120000), (120000, 200000),
                    (200000, 360000), (360000, float('inf'))
                ]
                data['annual_income'] = income_ranges[["6万元以下", "6-12万元", "12-20万元", "20-36万元", "36万元以上"].index(income_range)]

            elif step == 1:
                st.markdown("#### 📋 第二步：家庭与住房")
                infant_count = st.number_input("您是否有3岁以下的子女？有几个？", min_value=0, max_value=9, value=0, step=1, key="ck_infant")
                data['infant_children'] = infant_count

                school_count = st.number_input("您是否有正接受学历教育的子女（3岁以上在校生）？有几个？", min_value=0, max_value=9, value=0, step=1, key="ck_school")
                data['school_children'] = school_count

                has_elderly = st.checkbox("您是否有60岁以上的父母需要赡养？", key="ck_elderly")
                data['elderly_parents'] = has_elderly
                if has_elderly:
                    is_only = st.checkbox("您是独生子女？", value=True, key="ck_only")
                    data['is_only_child'] = is_only
                    if not is_only:
                        sib_count = st.number_input("兄弟姐妹共有几人？（包括您）", min_value=2, max_value=10, value=2, step=1, key="ck_sib")
                        data['sibling_count'] = sib_count
                else:
                    data['is_only_child'] = False

                housing_type = st.selectbox(
                    "您目前的住房情况是？",
                    options=["自有住房（有房贷）", "自有住房（无房贷）", "租房", "其他"],
                    index=0,
                    key="ck_housing",
                )
                data['housing_type'] = {
                    "自有住房（有房贷）": "housing_loan",
                    "自有住房（无房贷）": "own_no_loan",
                    "租房": "rent",
                    "其他": "other",
                }[housing_type]

            elif step == 2:
                st.markdown("#### 📋 第三步：教育与健康")
                data['study_continuing'] = st.checkbox("您目前是否正在接受学历继续教育？（在职研究生等）", key="ck_study")
                data['has_cert'] = st.checkbox("您今年是否取得了职业资格证书？", key="ck_cert")
                if data['has_cert']:
                    data['cert_name'] = st.text_input("证书名称（可选）", value="", key="ck_cert_name", placeholder="如：法律职业资格")

                medical_options = [
                    "1.5万元以下",
                    "1.5-3万元",
                    "3-6万元",
                    "6万元以上",
                    "不清楚",
                ]
                medical_choice = st.radio(
                    "今年医保目录内自付金额大概多少？",
                    options=medical_options,
                    index=0,
                    horizontal=True,
                    key="ck_medical",
                )
                medical_ranges = {
                    "1.5万元以下": (0, 15000),
                    "1.5-3万元": (15000, 30000),
                    "3-6万元": (30000, 60000),
                    "6万元以上": (60000, float('inf')),
                    "不清楚": (0, 0),
                }
                data['medical_expense'] = medical_ranges[medical_choice]

            elif step == 3:
                st.markdown("#### 📋 第四步：保障类支出")
                has_pension = st.checkbox("您是否开通了个人养老金账户并缴存？", key="ck_pension")
                data['has_pension'] = has_pension
                if has_pension:
                    data['pension_amount'] = st.number_input("今年缴存金额是多少元？", min_value=0, max_value=12000, value=12000, step=1000, key="ck_pension_amt")
                else:
                    data['pension_amount'] = 0

                has_tax_health = st.checkbox("您是否购买了税优健康险？", key="ck_health")
                data['has_tax_health'] = has_tax_health
                if has_tax_health:
                    data['tax_health_amount'] = st.number_input("每年保费大概多少元？", min_value=0, max_value=2400, value=2400, step=200, key="ck_health_amt")
                else:
                    data['tax_health_amount'] = 0

            elif step == 4:
                st.markdown("#### 📋 第五步：工作与租金")
                if data.get('housing_type') == 'rent':
                    city_type = st.selectbox(
                        "您租房所在城市类型：",
                        options=["北京、上海、广州、深圳", "其他省会城市/直辖市", "其他城市"],
                        index=0,
                        key="ck_city_type",
                    )
                    data['city_type'] = {"北京、上海、广州、深圳": "tier1", "其他省会城市/直辖市": "provincial", "其他城市": "other"}[city_type]
                    data['same_city'] = st.checkbox("您的工作地与户籍所在地在同一城市？", value=True, key="ck_same_city")
                else:
                    data['city_type'] = "other"
                    data['same_city'] = True

    # 按钮区域
    col_prev, _, col_next = st.columns([1, 2, 1])
    with col_prev:
        if step > 0 and step < total_steps:
            if st.button("← 上一步", use_container_width=True):
                st.session_state.checkup_step = step - 1
                st.rerun()

    with col_next:
        if step < total_steps:
            if st.button("下一步 →" if step < total_steps - 1 else "生成体检报告", type="primary", use_container_width=True):
                if step < total_steps - 1:
                    st.session_state.checkup_step = step + 1
                    st.rerun()
                else:
                    collector = DeductionCheckupCollector()
                    collector.load_from_json(data)
                    st.session_state.checkup_report = collector
                    st.session_state.checkup_step = total_steps
                    st.rerun()

    # 显示报告
    if step >= total_steps and st.session_state.checkup_report:
        collector = st.session_state.checkup_report
        diagnosis = collector.diagnosis
        st.divider()
        st.success("🎉 体检完成！")

        # 健康总览
        st.markdown("#### 📊 健康总览")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("可能遗漏的扣除项", f"{len(diagnosis['possible_missed'])} 项")
        with c2:
            st.metric("可能遗漏金额", fmt(diagnosis['total_missed']))
        with c3:
            st.metric("预计可节省税款", fmt(diagnosis['potential_savings']),
                      delta=f"税率 {data.get('estimated_tax_rate', 0.20)*100:.0f}% 预估")

        # 可能遗漏项
        if diagnosis['possible_missed']:
            st.markdown("#### ⚠️ 可能有遗漏的扣除项")
            for item in diagnosis['possible_missed']:
                ptype = item['type']
                policy = DEDUCTION_POLICIES.get(ptype, {})
                name = policy.get('name_short', ptype)
                with st.container(border=True):
                    st.markdown(f"**{name}**")
                    st.markdown(f"- 扣除标准：{policy.get('standard', '')}")
                    st.markdown(f"- 您的条件：{item['reason']}")
                    st.markdown(f"- 预计扣除：**{fmt(item['amount'])}/年** → 节税 **{fmt(item['savings'])}/年**")
                    st.info(f"📝 {item['action']}")
                    if item.get('warning'):
                        st.warning(item['warning'])

        # 不符合条件项
        if diagnosis['not_applicable']:
            with st.expander("❓ 暂不符合条件，但未来可能适用"):
                for item in diagnosis['not_applicable']:
                    ptype = item['type']
                    policy = DEDUCTION_POLICIES.get(ptype, DEDUCTION_POLICIES.get(
                        'continuing_education' if 'continuing' in ptype else ptype, {}))
                    name = policy.get('name', ptype)
                    st.markdown(f"**{name}**：{item['reason']}")
                    st.caption(f"💡 {item['suggestion']}")
                    st.divider()

        # 行动清单
        if diagnosis['possible_missed']:
            st.markdown("#### 📋 补申报行动清单")
            for i, item in enumerate(diagnosis['possible_missed'], 1):
                ptype = item['type']
                policy = DEDUCTION_POLICIES.get(ptype, DEDUCTION_POLICIES.get(
                    'continuing_education' if 'continuing' in ptype else ptype, {}))
                name = policy.get('name', ptype)
                st.markdown(f"{i}. **{name}** — {item['action']}")

        st.info("💡 温馨提示：扣除项填报可通过 **个人所得税APP** 完成，每年12月可确认次年扣除信息。")
        st.caption("以上报告基于您提供的信息自动生成，仅供参考。实际扣除资格以税务机关核定为准。")

        # 同步体检年收入到基础信息
        income = data.get('annual_income', (0, 0))
        if isinstance(income, (list, tuple)) and len(income) >= 2:
            est_annual = income[0] if income[1] == float('inf') else (income[0] + income[1]) // 2
        else:
            est_annual = 0
        if est_annual > 0:
            sync_col, _ = st.columns([1, 2])
            with sync_col:
                if st.button("💾 保存年收入到基础信息", key="sync_checkup", use_container_width=True):
                    sync_to_shared({"monthly_income": est_annual // 12})
                    st.session_state.sync_checkup_ok = True
                    st.rerun()
        if st.session_state.get("sync_checkup_ok"):
            st.success("✅ 年收入已同步到侧边栏基础信息！")
            st.session_state.sync_checkup_ok = False

        if st.button("重新体检", type="primary"):
            for key in ["checkup_step", "checkup_data", "checkup_report"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


# =============================================================
# Tab 5: 个人养老金税收优惠
# =============================================================

def render_pension_tab():
    st.subheader("💰 个人养老金税收优惠计算")
    st.caption("测算个人养老金缴存的税收优惠效果，收入越高省税越多")

    s = st.session_state.shared
    monthly_total_ded = sum(s[k] for k in ["children_edu", "infant_care", "elderly_care",
                                            "housing_loan", "housing_rent", "continuing_edu"])
    st.info(
        f"📥 已加载基础信息：月薪 **¥{s['monthly_income']:,}** · "
        f"专项附加扣除 **¥{monthly_total_ded:,}/月** · "
        f"个人养老金 **¥{s['personal_pension']:,}/年**",
        icon="💡",
    )

    st.markdown("""
    > **个人养老金**：每年最高缴存 **12,000 元**，可在税前扣除。
    > 领取时按 3% 税率缴税。收入越高，边际税率越高，节税效果越显著。
    """)

    # 收益速查表
    st.markdown("#### 📊 不同收入档位收益速查")
    rate_data = [
        {"月收入": "3万", "年收入": "36万", "适用税率": "10%", "年省税": "¥1,200", "实际成本": "¥10,800", "等效收益率": "11%"},
        {"月收入": "5万", "年收入": "60万", "适用税率": "20%", "年省税": "¥2,400", "实际成本": "¥9,600", "等效收益率": "25%"},
        {"月收入": "8万", "年收入": "96万", "适用税率": "35%", "年省税": "¥4,200", "实际成本": "¥7,800", "等效收益率": "54%"},
        {"月收入": "10万+", "年收入": "120万+", "适用税率": "45%", "年省税": "¥5,400", "实际成本": "¥6,600", "等效收益率": "82%"},
    ]
    df_rate = pd.DataFrame(rate_data)
    st.dataframe(df_rate, hide_index=True, use_container_width=True)

    # 同步成功提示（跨 rerun 保持）
    if st.session_state.get("sync_pension_ok"):
        st.success("✅ 已同步到侧边栏基础信息！")
        st.session_state.sync_pension_ok = False

    st.divider()

    # 自定义计算
    st.markdown("#### 🧮 自定义计算")
    with st.form("pension_form"):
        c1, c2 = st.columns(2)
        with c1:
            annual_income = st.number_input("年工资薪金收入（元）", min_value=0,
                                            value=s["monthly_income"] * 12, step=10000, key="p_income")
            monthly_additions = st.number_input("月度专项附加扣除（元）", min_value=0,
                                                value=monthly_total_ded, step=500, key="p_additions",
                                                help="如子女教育、住房租金等月度专项附加扣除合计")
        with c2:
            monthly_insurance = st.number_input("月度社保公积金（元）", min_value=0,
                                                value=int(s["monthly_income"] * s["insurance_rate"]),
                                                step=500, key="p_ins",
                                                help="个人承担的社保和公积金月度合计")
            pension_amount = st.selectbox("个人养老金年缴存额（元）",
                                          options=[12000, 6000, 3000, 0],
                                          index=0 if s["personal_pension"] >= 12000
                                                  else (1 if s["personal_pension"] >= 6000
                                                        else (2 if s["personal_pension"] >= 3000 else 3)),
                                          key="p_pension")

        submitted = st.form_submit_button("计算税收优惠", type="primary", use_container_width=True)

    if submitted:
        result = calculate_pension_tax_benefit(
            annual_income=annual_income,
            other_deductions_monthly=monthly_additions,
            insurance_monthly=monthly_insurance,
        )

        st.divider()
        st.success("计算完成")

        # 缴存前 vs 缴存后对比
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("缴存前应纳税所得额", fmt(result['taxable_income_before']))
        with col_b:
            st.metric("缴存后应纳税所得额", fmt(result['taxable_income_after']),
                      delta=f"减少 {fmt(result['taxable_income_before'] - result['taxable_income_after'])}")
        with col_c:
            st.metric("节省税额", fmt(result['tax_saved']),
                      delta=f"等效收益率 {result['return_rate'] * 100:.0f}%")

        # 核心对比
        with st.container(border=True):
            sc1, sc2 = st.columns(2)
            before_df = pd.DataFrame({
                "项目": ["应纳税所得额", "应纳税额"],
                "缴存前": [fmt(result['taxable_income_before']), fmt(result['tax_before'])],
            })
            after_df = pd.DataFrame({
                "项目": ["应纳税所得额", "应纳税额"],
                "缴存后": [fmt(result['taxable_income_after']), fmt(result['tax_after'])],
            })
            with sc1:
                st.markdown("**缴存前**")
                st.dataframe(before_df, hide_index=True, use_container_width=True)
            with sc2:
                st.markdown("**缴存后**")
                st.dataframe(after_df, hide_index=True, use_container_width=True)

        st.info(f"""
        💡 **结论**：每年缴存 {fmt(pension_amount)} 个人养老金，
        可节省税款 **{fmt(result['tax_saved'])}**，
        实际成本仅 **{fmt(result['actual_cost'])}**，
        等效年化收益率 **{result['return_rate'] * 100:.1f}%**。
        """)

        # 同步到基础信息
        col_a, _ = st.columns([1, 2])
        with col_a:
            if st.button("💾 同步个人养老金到基础信息", key="sync_pension", use_container_width=True):
                sync_to_shared({
                    "personal_pension": pension_amount,
                    "monthly_income": annual_income // 12,
                })
                st.session_state.sync_pension_ok = True
                st.rerun()

    # 注意事项
    with st.expander("📖 个人养老金政策说明"):
        st.markdown("""
        **什么是个人养老金？**
        - 个人自愿参加、市场化运营的补充养老保险制度
        - 每年缴存上限 12,000 元
        - 缴存金额可在当年综合所得中税前扣除

        **税收优惠机制：**
        1. **缴存时**：在当年综合所得中扣除，免缴个人所得税
        2. **投资时**：投资收益暂不征收个人所得税
        3. **领取时**：仅按 3% 税率缴纳个人所得税

        **适合人群：**
        - 适用税率 10% 及以上的人群（年收入约 20 万+）收益最明显
        - 税率越高，节税效果越显著
        - 低税率人群（3%）建议综合考虑流动性需求
        """)


# =============================================================
# Tab 6: 夫妻共同申报
# =============================================================

def render_joint_tab():
    st.subheader("👫 夫妻共同申报测算")
    st.caption("夫妻双方分别计算个税，对比独立申报与优化分配扣除项的差异")

    s = st.session_state.shared
    st.info(
        f"📥 配偶 A 已加载基础信息：月薪 **¥{s['monthly_income']:,}** · "
        f"年终奖 **¥{s['annual_bonus']:,}** · "
        f"比例 **{s['insurance_rate']*100:.1f}%**",
        icon="💡",
    )

    st.markdown("""
    > **适用场景**：夫妻双方均可享受的扣除项（如子女教育、住房贷款利息、赡养老人等）
    > 可以在一方全额扣除，也可双方各分摊一半。合理分配可最大化税后收入。
    """)

    with st.form("joint_form"):
        st.markdown("#### 👤 配偶 A（本人）")
        c1, c2 = st.columns(2)
        with c1:
            a_income = st.number_input("月薪（元）", min_value=0,
                                       value=s["monthly_income"], step=1000, key="ja_income")
            a_bonus = st.number_input("年终奖（元）", min_value=0,
                                      value=s["annual_bonus"], step=1000, key="ja_bonus")
        with c2:
            a_rate = st.slider("社保公积金比例", 0.0, 0.50,
                               value=s["insurance_rate"], step=0.005, format="%.1f%%", key="ja_rate")
            a_bonus_method = st.radio("年终奖方式", ["单独计税", "并入综合所得"],
                                      horizontal=True, key="ja_bonus_m",
                                      index=0 if s["bonus_method"] == "单独计税" else 1)

        st.markdown("#### 👤 配偶 B")
        c3, c4 = st.columns(2)
        with c3:
            b_income = st.number_input("月薪（元）", min_value=0, value=10000, step=1000, key="jb_income")
            b_bonus = st.number_input("年终奖（元）", min_value=0, value=0, step=1000, key="jb_bonus")
        with c4:
            b_rate = st.slider("社保公积金比例", 0.0, 0.50, 0.175, 0.005, format="%.1f%%", key="jb_rate")
            b_bonus_method = st.radio("年终奖方式", ["单独计税", "并入综合所得"], horizontal=True, key="jb_bonus_m")

        st.markdown("#### 📋 共同扣除项分配")
        st.caption("以下扣除项夫妻双方均可享受，请选择分配方式")
        d1, d2 = st.columns(2)
        with d1:
            children_deduction = st.number_input("子女教育（元/月）", 0, 4000, 2000, step=500, key="j_child",
                                                 help="双方合计每个子女最多 2000 元/月")
            rent_deduction = st.number_input("住房租金（元/月）", 0, 3000, 0, step=500, key="j_rent",
                                             help="双方合计最多 1500 元/月")
        with d2:
            elderly_deduction = st.number_input("赡养老人（元/月）", 0, 6000, 0, step=500, key="j_elderly",
                                                help="双方合计最多 3000 元/月（独生子女）")
            loan_deduction = st.number_input("住房贷款利息（元/月）", 0, 2000, 0, step=500, key="j_loan",
                                             help="双方合计最多 1000 元/月")

        allocation_method = st.radio(
            "扣除额分配方式",
            ["统一归至高收入方（节税最大化）", "双方各 50% 分摊", "自定义分配比例"],
            index=0,
            horizontal=True,
            key="j_alloc",
        )

        if allocation_method == "自定义分配比例":
            a_pct = st.slider("配偶 A 承担比例", 0, 100, 50, 5, key="j_alloc_pct",
                              help="剩余部分由配偶 B 承担")
        else:
            a_pct = 100 if allocation_method == "统一归至高收入方" else 50

        submitted = st.form_submit_button("开始测算", type="primary", use_container_width=True)

    if submitted:
        # 计算各自独立申报
        a_annual = a_income * 12
        a_total_ins = a_annual * a_rate
        b_annual = b_income * 12
        b_total_ins = b_annual * b_rate

        def calc_individual(annual_salary, total_insurance, bonus, bonus_method):
            annual_social = total_insurance * 0.6
            annual_hf = total_insurance * 0.4
            bm = "separate" if bonus_method == "单独计税" else "combined"
            return quick_calculate(
                annual_salary=annual_salary,
                annual_social=annual_social,
                annual_housing_fund=annual_hf,
                annual_special_additions=0,
                annual_other_deductions=0,
                annual_bonus=bonus,
                bonus_method=bm,
            )

        a_base = calc_individual(a_annual, a_total_ins, a_bonus, a_bonus_method)
        b_base = calc_individual(b_annual, b_total_ins, b_bonus, b_bonus_method)
        base_total = a_base["total_tax"] + b_base["total_tax"]

        # 确定高收入方（优化分配目标方）
        if a_annual >= b_annual:
            higher = "A"
            higher_taxable = a_base["taxable_income"]
            higher_rate = get_tax_rate_for_income(higher_taxable)
            lower_rate = get_tax_rate_for_income(b_base["taxable_income"])
        else:
            higher = "B"
            higher_taxable = b_base["taxable_income"]
            higher_rate = get_tax_rate_for_income(higher_taxable)
            lower_rate = get_tax_rate_for_income(a_base["taxable_income"])

        # 计算可分配的月度扣除总额
        total_monthly_deduction = children_deduction + rent_deduction + elderly_deduction + loan_deduction
        annual_deduction_total = total_monthly_deduction * 12

        # 按分配比例计算
        if allocation_method == "统一归至高收入方":
            a_portion = annual_deduction_total if higher == "A" else 0
            b_portion = 0 if higher == "A" else annual_deduction_total
        elif allocation_method == "各 50% 分摊":
            a_portion = annual_deduction_total * 0.5
            b_portion = annual_deduction_total * 0.5
        else:
            a_portion = annual_deduction_total * a_pct / 100
            b_portion = annual_deduction_total * (100 - a_pct) / 100

        # 优化后重新计算
        a_opt_social = a_total_ins * 0.6
        a_opt_hf = a_total_ins * 0.4
        b_opt_social = b_total_ins * 0.6
        b_opt_hf = b_total_ins * 0.4

        a_opt = quick_calculate(
            annual_salary=a_annual,
            annual_social=a_opt_social,
            annual_housing_fund=a_opt_hf,
            annual_special_additions=a_portion,
            annual_other_deductions=0,
            annual_bonus=a_bonus,
            bonus_method="separate" if a_bonus_method == "单独计税" else "combined",
        )
        b_opt = quick_calculate(
            annual_salary=b_annual,
            annual_social=b_opt_social,
            annual_housing_fund=b_opt_hf,
            annual_special_additions=b_portion,
            annual_other_deductions=0,
            annual_bonus=b_bonus,
            bonus_method="separate" if b_bonus_method == "单独计税" else "combined",
        )
        opt_total = a_opt["total_tax"] + b_opt["total_tax"]
        savings = base_total - opt_total

        st.divider()
        st.success("测算完成")

        # 总体对比
        st.markdown("#### 📊 总体对比")
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            st.metric("独立申报总税额", fmt(base_total))
        with oc2:
            st.metric("优化分配总税额", fmt(opt_total),
                      delta=f"节省 {fmt(savings)}" if savings > 0 else "无变化")
        with oc3:
            st.metric("可分配扣除总额", fmt(annual_deduction_total))

        if savings > 0:
            st.success(f"🎉 通过优化分配共同扣除项，夫妻双方合计可节省税款 **{fmt(savings)}** ！")

        # 双方明细对比
        st.markdown("#### 👤 双方明细对比")
        detail_rows = []
        for label, p_base, p_opt in [("配偶 A", a_base, a_opt), ("配偶 B", b_base, b_opt)]:
            detail_rows.append({
                "成员": label,
                "独立申报税额": fmt(p_base["total_tax"]),
                "优化后税额": fmt(p_opt["total_tax"]),
                "变化": fmt(p_opt["total_tax"] - p_base["total_tax"]),
                "税前年收入": fmt(p_base["annual_salary"]),
                "应纳税所得额": fmt(p_opt["taxable_income"]),
            })

        # 配偶 A 的分配额
        detail_rows[0]["分配扣除额"] = fmt(a_portion)
        detail_rows[1]["分配扣除额"] = fmt(b_portion)

        df_detail = pd.DataFrame(detail_rows)
        st.dataframe(df_detail, hide_index=True, use_container_width=True)

        # 分配方式对比
        st.markdown("#### 📈 税率对比说明")
        st.info(f"""
        - 配偶 A 适用税率：**{get_tax_rate_for_income(a_base['taxable_income']) * 100:.0f}%**
        - 配偶 B 适用税率：**{get_tax_rate_for_income(b_base['taxable_income']) * 100:.0f}%**
        - {'将扣除额集中分配给高收入方（{higher}），可产生更显著的节税效果。'.format(higher=f"配偶 {higher}") if higher_rate > lower_rate else '双方税率相同，分配方式对税负无实质影响。'}
        """)

        if savings > 0:
            st.markdown("#### 💡 优化建议")
            st.markdown(f"""
            当前分配方案下：
            - 配偶 A 获得扣除额：**{fmt(a_portion)}/年**
            - 配偶 B 获得扣除额：**{fmt(b_portion)}/年**
            """)

        with st.expander("📖 政策说明"):
            st.markdown("""
            **可夫妻共同享受的扣除项目：**
            - **子女教育**：父母可选择一方100%扣除或双方各50%
            - **3岁以下婴幼儿照护**：同上
            - **住房贷款利息**：婚后可选择一方扣除或双方各50%
            - **赡养老人**：独生子女3000元/月，非独生子女分摊，建议由高收入方扣除
            - **大病医疗**：可由本人或配偶扣除

            **注意：**
            - 住房租金与住房贷款利息不可同时享受
            - 夫妻在同一城市工作的，住房租金只能一方扣除
            - 赡养老人各算各的，不能互相转移
            """)

        # 同步成功提示
        if st.session_state.get("sync_joint_ok"):
            st.success("✅ 配偶 A 已同步到侧边栏基础信息！")
            st.session_state.sync_joint_ok = False

        col_a, _ = st.columns([1, 2])
        with col_a:
            if st.button("💾 同步配偶 A 数据到基础信息", key="sync_joint", use_container_width=True):
                sync_to_shared({
                    "monthly_income": a_income,
                    "annual_bonus": a_bonus,
                    "insurance_rate": a_rate,
                    "bonus_method": a_bonus_method,
                })
                st.session_state.sync_joint_ok = True
                st.rerun()


# =============================================================
# 主页面
# =============================================================

st.title("🧮 个人所得税计算器")
st.markdown(
    "基于 **2025 年个人所得税法**，支持累计预扣预缴与年度汇算清缴。"
)

render_sidebar()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "快速估算", "详细计算", "批量 JSON 上传",
    "🔍 扣除项体检", "💰 养老金优惠", "👫 夫妻共同申报",
])

with tab1:
    render_quick_tab()

with tab2:
    render_detailed_tab()

with tab3:
    render_batch_tab()

with tab4:
    render_checkup_tab()

with tab5:
    render_pension_tab()

with tab6:
    render_joint_tab()

st.divider()
st.caption(
    "⚠️ 计算结果仅供参考，实际税额以税务机关核定为准。"
    "数据仅在浏览器本地计算，不会上传至任何服务器。"
)
