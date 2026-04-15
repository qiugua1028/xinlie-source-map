"""
寻源地图 v4 — 品牌+福利双核心 · 可编辑版
- 移除：薪资Benchmark独立页（数据保留在数据库，公司卡片内仍可查看）
- 新增：福利查询可编辑（data_editor inline编辑）
- 新增：品牌库可编辑（inline编辑）
Run: python3 -m streamlit run ~/xinlie-source-map/app.py --server.port 8502
"""

import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime
import re

st.set_page_config(page_title="寻源地图", page_icon="🗺️", layout="wide")

DB_PATH = os.path.join(os.path.dirname(__file__), "db/source_map.db")

# ─── 数据库辅助 ───────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH)

def qdf(sql, params=()):
    conn = get_conn()
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df

# ─── 公司+品牌整合查询 ───────────────────────────────────────────────────
def get_companies_with_brands():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT 
            c.id, c.company_name, c.short_name,
            c.industry_tag, c.reg_address, c.business,
            c.tags, c.updated_at,
            c.annual_revenue, c.revenue_year,
            c.working_hours, c.benefits, c.notes as co_notes,
            c.search_keywords as co_search_kw,
            (SELECT GROUP_CONCAT(b.brand_name || COALESCE(', ' || b.search_keywords, ''), ', ')
             FROM brands b WHERE b.company_id = c.id) as brand_keywords,
            (SELECT COUNT(*) FROM brands WHERE company_id = c.id) as brand_count,
            (SELECT COUNT(*) FROM benefits_structured 
             WHERE company_name LIKE c.company_name||'%') as benefit_count
        FROM companies c
        WHERE c.to_delete = 0
        ORDER BY brand_count DESC, c.company_name
    """, conn)
    conn.close()
    return df

def get_brands_for_company(company_id):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT id, brand_name, industry, category, position, tags, notes
        FROM brands WHERE company_id = ?
    """, conn, params=(company_id,))
    conn.close()
    return df

def get_benefits_for_company(company_name):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT id, dept, job_title, level,
               work_schedule, insurance, meal, transport,
               housing, holiday, other, raw_benefits
        FROM benefits_structured
        WHERE company_name LIKE ? || '%'
        ORDER BY level
    """, conn, params=(company_name,))
    conn.close()
    return df

def get_salary_for_company(company_name):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT dept, job_title, level,
               monthly_min, monthly_max, yearly_min, yearly_max,
               salary_structure, candidate_name
        FROM salary_benchmarks
        WHERE company_name LIKE ? || '%'
    """, conn, params=(company_name,))
    conn.close()
    return df

# ─── 侧边栏 ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🗺️ 寻源地图")
    st.caption("快消电商情报库")

    conn = get_conn()
    b_count = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    c_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    benefits = conn.execute("SELECT COUNT(*) FROM benefits_structured").fetchone()[0]
    conn.close()

    st.metric("品牌", b_count)
    st.metric("公司", c_count)
    st.metric("福利记录", benefits)
    st.divider()

    page = st.radio("功能", [
        "🏢 公司品牌库",
        "📋 福利查询",
        "📦 品牌库",
        "🔧 公司管理",
        "📰 公司动态",
        "➕ 手动录入",
    ], label_visibility="collapsed")

# ─── 主内容 ──────────────────────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════════════
# 页面1：公司品牌库
# ════════════════════════════════════════════════════════════════════════
if page == "🏢 公司品牌库":
    st.title("🏢 公司品牌库")
    st.caption("公司 · 品牌 · 福利 — 三维信息一屏掌握")

    df = get_companies_with_brands()

    col0, col1, col2 = st.columns([3, 2, 1])
    with col0:
        keyword = st.text_input("🔍 搜索公司/品牌", placeholder="输入关键词，如：安踏、珀莱雅...")
    with col1:
        industry = st.selectbox("行业", ["全部", "服饰", "美妆", "电商", "其他", "食品"])
    with col2:
        sort_by = st.selectbox("排序", ["品牌最多", "公司名称"])

    if industry != "全部":
        df = df[df['industry_tag'] == industry]
    if keyword:
        kw_lower = keyword.lower()
        mask = df['company_name'].str.contains(keyword, na=False, regex=False) | \
               df['business'].str.contains(keyword, na=False, regex=False) | \
               df['tags'].str.contains(keyword, na=False, regex=False) | \
               (df.get('co_search_kw', '').fillna('').str.lower().str.contains(kw_lower, na=False, regex=False)) | \
               (df.get('brand_keywords', '').fillna('').str.lower().str.contains(kw_lower, na=False, regex=False))
        df = df[mask]
    if sort_by == "品牌最多":
        df = df.sort_values('brand_count', ascending=False)

    st.info(f"共 {len(df)} 家公司")

    if df.empty:
        st.info("没有符合条件的公司，试试调整筛选条件 🔍")
    else:
        for _, row in df.iterrows():
            co_id = row['id']
            co_name = row['company_name']
            industry_tag = row['industry_tag'] or '其他'
            brand_n = row['brand_count']
            benefit_n = row['benefit_count']
            address = row['reg_address'] or ''
            business = row['business'] or ''
            annual_rev = row['annual_revenue']
            rev_year = row['revenue_year']
            working_hours = row.get('working_hours') or ''
            benefits = row.get('benefits') or ''

            # 标签：行业+品牌数+福利+销售规模
            rev_tag = f"💰{annual_rev}" if annual_rev else ""
            hours_tag = "⏰作息" if working_hours and working_hours not in ['', '待查', None] else ""
            benefits_tag = "🎁福利" if benefits and benefits not in ['', '待查', None] else ""
            tags = [t for t in [industry_tag, f"📦{brand_n}品牌", f"🏠{benefit_n}福利", hours_tag, benefits_tag, rev_tag] if t]
            tag_str = " · ".join(tags)

            with st.expander(f"**{co_name}**  {tag_str}"):
                col_l, col_r = st.columns([1, 1])

                with col_l:
                    st.markdown("**基本信息**")
                    st.text(f"行业：{industry_tag}")
                    if annual_rev:
                        year_str = f"({rev_year}年)" if rev_year else ""
                        st.markdown(f"💰 **年销售规模**：{annual_rev} {year_str}")
                    if working_hours and working_hours not in ['', '待查', None]:
                        st.markdown(f"⏰ **作息**：{working_hours}")
                    if benefits and benefits not in ['', '待查', None]:
                        short_benefits = benefits[:60] + ('...' if len(benefits) > 60 else '')
                        st.markdown(f"🎁 **福利**：{short_benefits}")
                    st.text(f"注册地：{address}" if address else "注册地：未知")
                    st.text(f"业务：{business[:60]}" if business else "业务：未知")
                    if row['tags']:
                        st.text(f"标签：{row['tags'][:80]}")

                    # 关联品牌
                    brands_df = get_brands_for_company(co_id)
                    if not brands_df.empty:
                        st.markdown(f"\n**📦 关联品牌（{len(brands_df)}个）**")
                        st.dataframe(brands_df.rename(columns={
                            'brand_name': '品牌', 'industry': '行业', 'category': '品类',
                            'position': '定位', 'tags': '标签'
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.text("暂无关联品牌")

                with col_r:
                    # 薪资记录（公司卡片内保留查看）
                    salary_df = get_salary_for_company(co_name)
                    if not salary_df.empty:
                        st.markdown(f"**💰 薪资Benchmark（{len(salary_df)}条）**")
                        def fmt_salary(r):
                            if pd.notna(r['monthly_min']):
                                # 数据库存的是元，转换为K显示
                                min_k = r['monthly_min'] / 1000
                                mx = f"{r['monthly_max']/1000:.0f}" if pd.notna(r['monthly_max']) and r['monthly_max'] != r['monthly_min'] else ''
                                return f"{min_k:.0f}{mx and '-'+mx}K/月  ·  {r['dept'] or ''}/{r['job_title']}  ·  {r['level'] or ''}"
                            elif pd.notna(r['yearly_min']):
                                # 年薪转换为W显示
                                min_w = r['yearly_min'] / 10000
                                my = f"{r['yearly_max']/10000:.0f}" if pd.notna(r['yearly_max']) and r['yearly_max'] != r['yearly_min'] else ''
                                return f"{min_w:.0f}{my and '-'+my}W/年  ·  {r['dept'] or ''}/{r['job_title']}  ·  {r['level'] or ''}"
                            return f"{r['dept'] or ''}/{r['job_title']}  ·  {r['level'] or ''}"
                        for _, s in salary_df.iterrows():
                            st.text(f"  • {fmt_salary(s)}")
                    else:
                        st.markdown("**💰 薪资Benchmark**")
                        st.text("暂无薪资数据")

                    # 福利记录
                    benefits_df = get_benefits_for_company(co_name)
                    if not benefits_df.empty:
                        st.markdown(f"**🏠 福利待遇（{len(benefits_df)}条）**")
                        ws_vals = benefits_df['work_schedule'].dropna().unique()
                        ins_vals = benefits_df['insurance'].dropna().unique()
                        meal_vals = benefits_df['meal'].dropna().unique()
                        tr_vals  = benefits_df['transport'].dropna().unique()
                        ho_vals  = benefits_df['housing'].dropna().unique()
                        hol_vals = benefits_df['holiday'].dropna().unique()
                        other_vals = benefits_df['other'].dropna().unique()
                        items = []
                        if len(ws_vals):  items.append(f"**作息**：{' / '.join(ws_vals)}")
                        if len(ins_vals): items.append(f"**社保**：{' / '.join(ins_vals)}")
                        if len(meal_vals): items.append(f"**餐补**：{' / '.join(meal_vals)}")
                        if len(tr_vals):   items.append(f"**交通**：{' / '.join(tr_vals)}")
                        if len(ho_vals):   items.append(f"**住宿**：{' / '.join(ho_vals)}")
                        if len(hol_vals):  items.append(f"**假期**：{' / '.join(hol_vals)}")
                        if len(other_vals): items.append(f"**其他**：{' / '.join(other_vals)}")
                        for item in items:
                            st.text(item)
                        # 直接显示完整福利明细（不嵌套expander）
                        st.dataframe(benefits_df.rename(columns={
                            'dept': '部门', 'job_title': '职位', 'level': '职级',
                            'work_schedule': '作息', 'insurance': '社保',
                            'meal': '餐补', 'transport': '交通', 'housing': '住宿',
                            'holiday': '假期', 'other': '其他福利'
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.markdown("**🏠 福利待遇**")
                        st.text("暂无福利数据")

# ════════════════════════════════════════════════════════════════════════
# 页面2：福利查询（可编辑）
# ════════════════════════════════════════════════════════════════════════
elif page == "📋 福利查询":
    st.title("📋 福利待遇查询")
    st.caption("按公司聚合 · 快速编辑明细 · 作息 · 五险一金 · 餐补 · 交通 · 住宿")

    # ── 上部：聚合总览表 ───────────────────
    def fmt_cell(v):
        if not v: return "—"
        parts = list(dict.fromkeys(v.split(',')))
        return " / ".join(p.strip() for p in parts if p.strip())

    conn = get_conn()
    df = pd.read_sql("""
        SELECT company_name, industry_tag,
               work_schedules, insurances, meals, transports,
               housings, holidays, others, sample_count
        FROM v_company_benefits
        ORDER BY sample_count DESC, company_name
    """, conn)
    conn.close()

    c1, c2 = st.columns([3, 1])
    with c2:
        ind = st.selectbox("行业", ["全部", "服饰", "美妆", "电商", "其他", "食品"], key="b_ind")
    with c1:
        kw = st.text_input("🔍 搜索公司", placeholder="输入公司名...", key="b_kw")

    d = df.copy()
    if ind != "全部": d = d[d['industry_tag'] == ind]
    if kw: d = d[d['company_name'].str.contains(kw, na=False)]

    st.info(f"共 {len(d)} 家公司有福利数据")

    disp = d.copy()
    disp['作息']     = disp['work_schedules'].apply(fmt_cell)
    disp['五险一金'] = disp['insurances'].apply(fmt_cell)
    disp['餐补']     = disp['meals'].apply(fmt_cell)
    disp['交通']     = disp['transports'].apply(fmt_cell)
    disp['住宿']     = disp['housings'].apply(fmt_cell)
    disp['假期']     = disp['holidays'].apply(fmt_cell)
    disp['其他']     = disp['others'].apply(fmt_cell)

    st.dataframe(
        disp[['company_name','industry_tag','作息','五险一金','餐补','交通','住宿','假期','其他','sample_count']]
             .rename(columns={'company_name':'公司','industry_tag':'行业','sample_count':'样本数'}),
        use_container_width=True, hide_index=True, height=350
    )

    st.divider()

    # ── 下部：✏️ 快速编辑（表单模式） ─────────
    st.subheader("✏️ 快速编辑")

    conn = get_conn()
    detail_df = pd.read_sql("""
        SELECT id, company_name, dept, job_title, level,
               work_schedule, insurance, meal, transport,
               housing, holiday, other
        FROM benefits_structured
        ORDER BY company_name, id
    """, conn)
    conn.close()

    # 选择要编辑的记录
    opts = ["（新建记录）"] + [
        f"{r['company_name']} | {r['dept'] or ''} | {r['job_title'] or ''} | {r['id']}"
        for _, r in detail_df.iterrows()
    ]

    sel_opt = st.selectbox("选择要编辑的记录", opts, key="b_sel_opt")

    if sel_opt == "（新建记录）":
        # ── 新建表单 ────────────────────────
        with st.form("new_benefit", clear_on_submit=False):
            nc1, nc2 = st.columns(2)
            with nc1:
                n_co   = st.text_input("🏢 公司名 *", placeholder="如：安踏集团")
                n_dept = st.text_input("🏬 部门", placeholder="如：商品部")
                n_job  = st.text_input("💼 职位", placeholder="如：采购经理")
            with nc2:
                n_lvl  = st.selectbox("📊 职级", ["","P1","P2","P3","P4","P5","P6","P7","M1","M2","M3","M4","M5"])
                n_ws   = st.selectbox("⏰ 作息", ["","双休","大小周","单休","做五休二","其他"])
                n_ins  = st.text_input("🏥 社保", placeholder="如：五险一金")
            nc3, nc4 = st.columns(2)
            with nc3:
                n_meal = st.text_input("🍱 餐补", placeholder="如：餐补30元/天")
                n_tr   = st.text_input("🚌 交通", placeholder="如：交通补贴500/月")
            with nc4:
                n_hous = st.text_input("🏠 住宿", placeholder="如：人才公寓免租2年")
                n_hol  = st.text_input("🏖️ 假期", placeholder="如：年假10天起")
            n_oth = st.text_input("🎁 其他福利", placeholder="如：年度体检、父母津贴")
            submitted = st.form_submit_button("💾 新增记录", type="primary", use_container_width=True)
            if submitted:
                if not n_co.strip():
                    st.error("公司名必填")
                else:
                    conn2 = get_conn()
                    conn2.execute("""
                        INSERT INTO benefits_structured
                            (company_name, dept, job_title, level,
                             work_schedule, insurance, meal, transport,
                             housing, holiday, other)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """, (n_co.strip(), n_dept.strip() or None, n_job.strip() or None, n_lvl or None,
                          n_ws or None, n_ins.strip() or None, n_meal.strip() or None,
                          n_tr.strip() or None, n_hous.strip() or None,
                          n_hol.strip() or None, n_oth.strip() or None))
                    conn2.commit(); conn2.close()
                    st.success(f"✅ 已新增：「{n_co}」")
                    st.cache_data.clear()
                    st.rerun()

    else:
        # ── 加载选中记录并展示编辑表单 ──────
        sel_id = int(sel_opt.split("|")[-1].strip())
        row = detail_df[detail_df['id'] == sel_id].iloc[0]

        def sv(v):  # safe string
            return "" if (pd.isna(v) or v is None) else str(v)

        with st.form(f"edit_benefit_{sel_id}", clear_on_submit=False):
            ec1, ec2 = st.columns(2)
            with ec1:
                e_co   = st.text_input("🏢 公司名", value=sv(row['company_name']))
                e_dept = st.text_input("🏬 部门",   value=sv(row['dept']))
                e_job  = st.text_input("💼 职位",   value=sv(row['job_title']))
            with ec2:
                lvl_opts = ["","P1","P2","P3","P4","P5","P6","P7","M1","M2","M3","M4","M5"]
                e_lvl    = st.selectbox("📊 职级", lvl_opts,
                               index=lvl_opts.index(row['level']) if sv(row['level']) in lvl_opts else 0)
                ws_opts  = ["","双休","大小周","单休","做五休二","其他"]
                e_ws     = st.selectbox("⏰ 作息", ws_opts,
                               index=ws_opts.index(row['work_schedule']) if sv(row['work_schedule']) in ws_opts else 0)
                e_ins    = st.text_input("🏥 社保",  value=sv(row['insurance']))
            ec3, ec4 = st.columns(2)
            with ec3:
                e_meal  = st.text_input("🍱 餐补",  value=sv(row['meal']))
                e_tr    = st.text_input("🚌 交通",  value=sv(row['transport']))
            with ec4:
                e_hous  = st.text_input("🏠 住宿",  value=sv(row['housing']))
                e_hol   = st.text_input("🏖️ 假期",  value=sv(row['holiday']))
            e_oth = st.text_input("🎁 其他福利", value=sv(row['other']))

            # 删除确认
            e_del = st.checkbox("🚫 标记删除此记录")

            cdel1, cdel2 = st.columns(2)
            with cdel1:
                submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
            with cdel2:
                if st.form_submit_button("🗑️ 删除此记录", use_container_width=True):
                    conn3 = get_conn()
                    conn3.execute("DELETE FROM benefits_structured WHERE id = ?", (sel_id,))
                    conn3.commit(); conn3.close()
                    st.success("✅ 已删除")
                    st.cache_data.clear()
                    st.rerun()

            if submitted:
                conn4 = get_conn()
                conn4.execute("""
                    UPDATE benefits_structured SET
                        company_name=?, dept=?, job_title=?, level=?,
                        work_schedule=?, insurance=?, meal=?,
                        transport=?, housing=?, holiday=?, other=?
                    WHERE id=?
                """, (
                    e_co.strip(), e_dept.strip() or None, e_job.strip() or None, e_lvl or None,
                    e_ws or None, e_ins.strip() or None, e_meal.strip() or None,
                    e_tr.strip() or None, e_hous.strip() or None,
                    e_hol.strip() or None, e_oth.strip() or None,
                    sel_id
                ))
                conn4.commit(); conn4.close()
                st.success(f"✅ 已保存：「{e_co}」")
                st.cache_data.clear()
                st.rerun()

    st.divider()
    # ── 行业作息对比图 ────────────────────
    st.subheader("📊 行业作息对比")
    conn = get_conn()
    sched = pd.read_sql("""
        SELECT industry_tag, work_schedules, COUNT(*) as cnt
        FROM v_company_benefits
        WHERE industry_tag IS NOT NULL AND work_schedules IS NOT NULL
        GROUP BY industry_tag, work_schedules
    """, conn)
    conn.close()
    if not sched.empty:
        piv = sched.pivot_table(index='work_schedules', columns='industry_tag', values='cnt', fill_value=0)
        st.bar_chart(piv)

# ════════════════════════════════════════════════════════════════════════
# 页面3：品牌库（可编辑）
# ════════════════════════════════════════════════════════════════════════
elif page == "📦 品牌库":
    st.title("📦 品牌库")
    st.caption("筛选浏览 · 快速编辑单个品牌")

    # ── 上部：筛选 + 只读列表 ────────────────
    conn = get_conn()
    df = pd.read_sql("""
        SELECT b.id, b.brand_name, c.company_name, c.industry_tag,
               b.industry, b.category, b.position, b.tags, b.notes,
               b.search_keywords,
               (SELECT COUNT(*) FROM salary_benchmarks WHERE company_name LIKE c.company_name||'%') as bench_count,
               (SELECT COUNT(*) FROM benefits_structured WHERE company_name LIKE c.company_name||'%') as benefit_count
        FROM brands b
        LEFT JOIN companies c ON b.company_id = c.id
        ORDER BY b.brand_name
    """, conn)
    conn.close()

    col1, col2 = st.columns([4, 1])
    with col2:
        industry = st.selectbox("行业", ["全部", "服饰", "美妆", "电商", "食品", "其他"], key="brand_ind")
    with col1:
        kw = st.text_input("🔍 搜索品牌/公司", placeholder="筛选品牌...", key="brand_kw")

    df_filtered = df.copy()
    if industry != "全部":
        df_filtered = df_filtered[df_filtered['industry_tag'] == industry]
    if kw:
        kw_lower = kw.lower()
        df_filtered = df_filtered[
            df_filtered['brand_name'].str.contains(kw, na=False, regex=False) |
            df_filtered['company_name'].str.contains(kw, na=False, regex=False) |
            (df_filtered.get('search_keywords', '').fillna('').str.lower().str.contains(kw_lower, na=False, regex=False))
        ]

    st.info(f"共 {len(df_filtered)} 个品牌")
    st.dataframe(
        df_filtered.rename(columns={
            'id': 'id', 'brand_name': '品牌名', 'company_name': '所属公司',
            'industry_tag': '行业', 'industry': '品类行业', 'category': '品类',
            'position': '定位', 'tags': '标签', 'notes': '备注',
            'bench_count': '薪资记录', 'benefit_count': '福利记录'
        }),
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "品牌名": st.column_config.TextColumn("品牌名"),
            "所属公司": st.column_config.TextColumn("所属公司"),
            "行业": st.column_config.TextColumn("行业"),
            "品类行业": st.column_config.TextColumn("品类行业"),
            "品类": st.column_config.TextColumn("品类"),
            "定位": st.column_config.TextColumn("定位"),
            "标签": st.column_config.TextColumn("标签"),
            "备注": st.column_config.TextColumn("备注"),
            "薪资记录": st.column_config.NumberColumn("薪资记录", disabled=True),
            "福利记录": st.column_config.NumberColumn("福利记录", disabled=True),
        },
        hide_index=True,
        use_container_width=True
    )

    # ── 导出品牌库 ──
    col_exp1, col_exp2 = st.columns([1, 4])
    with col_exp1:
        brand_export = st.button("📥 导出品牌库", use_container_width=True)
    if brand_export:
        brand_csv = brand_display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="⬇ 点击下载",
            data=brand_csv,
            file_name=f"寻源地图_品牌库_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # ── 下部：快速编辑表单 ─────────────────
    st.divider()
    st.subheader("✏️ 快速编辑")

    conn = get_conn()
    all_brands = pd.read_sql("""
        SELECT b.id, b.brand_name, b.company_id, b.industry, b.category,
               b.position, b.tags, b.notes, c.company_name
        FROM brands b
        LEFT JOIN companies c ON b.company_id = c.id
        ORDER BY b.brand_name
    """, conn)
    conn.close()

    if len(all_brands) == 0:
        st.info("暂无品牌数据")
    else:
        # 默认选中
        if "edit_brand_id" not in st.session_state:
            st.session_state["edit_brand_id"] = int(all_brands.iloc[0]["id"])

        sel = st.selectbox(
            "选择要编辑的品牌",
            options=all_brands["id"].tolist(),
            format_func=lambda x: all_brands.loc[all_brands["id"] == x, "brand_name"].values[0],
            index=list(all_brands["id"]).index(st.session_state["edit_brand_id"]),
            key="sel_brand"
        )
        st.session_state["edit_brand_id"] = sel
        row = all_brands[all_brands["id"] == sel].iloc[0]

        # 加载公司下拉选项
        conn = get_conn()
        cos = conn.execute("SELECT id, company_name FROM companies ORDER BY company_name").fetchall()
        conn.close()
        co_opts = {c[1]: c[0] for c in cos}
        co_opts_list = list(co_opts.keys())
        current_co = row["company_name"] or ""
        try:
            co_default_idx = co_opts_list.index(current_co)
        except ValueError:
            co_default_idx = 0

        with st.form(f"edit_brand_{sel}", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("品牌名 *", value=str(row["brand_name"] or ""))
                edit_co = st.selectbox("所属公司", co_opts_list, index=co_default_idx)
            with col2:
                edit_industry = st.selectbox(
                    "行业", ["服饰", "美妆", "电商", "食品", "其他"],
                    index=["服饰","美妆","电商","食品","其他"].index(row["industry"])
                    if row["industry"] in ["服饰","美妆","电商","食品","其他"] else 4
                )
                edit_category = st.text_input("品类", value=str(row["category"] or ""),
                                              placeholder="如：防晒衣、内衣...")
            col3, col4 = st.columns(2)
            with col3:
                edit_position = st.selectbox("价格定位",
                    ["未知","高端","中高端","中端","平价"],
                    index=["未知","高端","中高端","中端","平价"].index(row["position"])
                    if row["position"] in ["未知","高端","中高端","中端","平价"] else 0
                )
            with col4:
                edit_tags = st.text_input("标签（逗号分隔）", value=str(row["tags"] or ""))
            edit_notes = st.text_area("备注", value=str(row["notes"] or ""))

            submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)

            if submitted:
                import math
                def safe_str(v):
                    if v is None: return None
                    if isinstance(v, float) and math.isnan(v): return None
                    return v.strip() if isinstance(v, str) else str(v)
                new_co_id = co_opts.get(edit_co)
                try:
                    conn2 = get_conn()
                    conn2.execute("""
                        UPDATE brands SET
                            brand_name = ?,
                            company_id = ?,
                            industry = ?,
                            category = ?,
                            position = ?,
                            tags = ?,
                            notes = ?,
                            updated_at = datetime('now')
                        WHERE id = ?
                    """, (
                        safe_str(edit_name),
                        new_co_id,
                        edit_industry,
                        safe_str(edit_category),
                        edit_position,
                        safe_str(edit_tags),
                        safe_str(edit_notes),
                        sel
                    ))
                    conn2.commit()
                    conn2.close()
                    st.success(f"✅ 已保存：「{edit_name}」")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 保存失败: {e}")

    # ── 统计 ──────────────────────────────────
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("品牌行业分布")
        if not df_filtered.empty:
            ind_chart = df_filtered['industry'].value_counts()
            st.bar_chart(ind_chart)
    with col2:
        st.subheader("定位分布")
        if not df_filtered.empty:
            pos_chart = df_filtered['position'].value_counts()
            st.bar_chart(pos_chart)

# ════════════════════════════════════════════════════════════════════════
# 页面4：公司管理（标记删除/合并同类项）
# ════════════════════════════════════════════════════════════════════════
elif page == "🔧 公司管理":
    st.title("🔧 公司管理")
    st.caption("标记删除公司 · 合并同类项 · 集团归类")

    conn = get_conn()
    df = pd.read_sql("""
        SELECT 
            c.id, c.company_name, c.industry_tag, c.parent_company,
            c.annual_revenue, c.revenue_year,
            c.competitors, c.boss_job_count, c.boss_job_check_date, c.data_quality,
            c.founded_year, c.reg_address, c.business,
            (SELECT COUNT(*) FROM brands WHERE company_id = c.id) as brand_count,
            (SELECT GROUP_CONCAT(brand_name, ', ') FROM brands WHERE company_id = c.id) as brand_names,
            (SELECT COUNT(*) FROM salary_benchmarks WHERE company_name LIKE c.company_name||'%') as bench_count,
            (SELECT COUNT(*) FROM benefits_structured WHERE company_name LIKE c.company_name||'%') as benefit_count,
            COALESCE(c.to_delete, 0) as to_delete
        FROM companies c
        ORDER BY c.industry_tag, brand_count DESC, c.company_name
    """, conn)
    conn.close()

    # 筛选 - 加 MCN机构 选项
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        kw = st.text_input("🔍 搜索", placeholder="公司名...")
    with col2:
        ind_filter = st.selectbox("行业", ["全部", "服饰", "美妆", "电商", "MCN机构", "其他", "食品"])
    with col3:
        show_deleted = st.selectbox("显示", ["全部", "仅保留", "仅标记删除"])

    df_filtered = df.copy()
    if kw:
        df_filtered = df_filtered[df_filtered['company_name'].str.contains(kw, na=False)]
    if ind_filter != "全部":
        df_filtered = df_filtered[df_filtered['industry_tag'] == ind_filter]
    if show_deleted == "仅保留":
        df_filtered = df_filtered[df_filtered['to_delete'] == 0]
    elif show_deleted == "仅标记删除":
        df_filtered = df_filtered[df_filtered['to_delete'] == 1]

    st.info(f"共 {len(df_filtered)} 家公司")

    # ── 展示表格：非编辑，只读 ──
    display_df = df_filtered.rename(columns={
        'id': 'ID',
        'company_name': '公司名',
        'industry_tag': '行业',
        'parent_company': '所属集团',
        'annual_revenue': '年销售规模',
        'revenue_year': '年份',
        'brand_count': '品牌',
        'brand_names': '关联品牌',
        'bench_count': '薪资',
        'benefit_count': '福利',
        'to_delete': '删?',
        'competitors': '竞品',
        'boss_job_count': 'BOSS在招',
        'boss_job_check_date': '核查日期',
        'data_quality': '质量',
        'founded_year': '成立',
        'reg_address': '注册地',
    }).copy()

    st.dataframe(
        display_df[['公司名','行业','年销售规模','年份','品牌','成立','注册地','竞品','BOSS在招','核查日期','质量','删?']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "公司名": st.column_config.TextColumn("公司名"),
            "行业": st.column_config.TextColumn("行业", width="small"),
            "年销售规模": st.column_config.TextColumn("年销售规模", width="medium"),
            "年份": st.column_config.NumberColumn("年份", width="tiny"),
            "品牌": st.column_config.NumberColumn("品牌", width="tiny"),
            "成立": st.column_config.NumberColumn("成立", width="tiny"),
            "注册地": st.column_config.TextColumn("注册地", width="medium"),
            "竞品": st.column_config.TextColumn("竞品"),
            "BOSS在招": st.column_config.NumberColumn("BOSS在招", width="tiny"),
            "核查日期": st.column_config.TextColumn("核查日期", width="small"),
            "质量": st.column_config.TextColumn("质量", width="tiny"),
            "删?": st.column_config.CheckboxColumn("删?", width="tiny"),
        }
    )

    # ── 导出功能 ──
    col_export1, col_export2 = st.columns([1, 4])
    with col_export1:
        export_btn = st.button("📥 导出Excel", use_container_width=True)
    if export_btn:
        csv = display_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="⬇ 点击下载",
            data=csv,
            file_name=f"寻源地图_公司管理_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.divider()
    st.subheader("✏️ 快速编辑")

    # ── 编辑表单（每次只编辑一条）─────────────
    conn = get_conn()
    all_companies = pd.read_sql("""
        SELECT id, company_name, industry_tag, parent_company, annual_revenue, revenue_year,
               to_delete, competitors, boss_job_count, boss_job_check_date, data_quality,
               founded_year, reg_address, business
        FROM companies ORDER BY company_name""", conn)
    conn.close()

    # 默认选第一条
    if "edit_company_id" not in st.session_state:
        st.session_state["edit_company_id"] = all_companies.iloc[0]["id"] if len(all_companies) > 0 else None

    sel = st.selectbox(
        "选择要编辑的公司",
        options=all_companies["id"].tolist(),
        format_func=lambda x: all_companies.loc[all_companies["id"] == x, "company_name"].values[0],
        index=list(all_companies["id"]).index(st.session_state["edit_company_id"]) if st.session_state["edit_company_id"] in all_companies["id"].values else 0,
        key="sel_company"
    )
    st.session_state["edit_company_id"] = sel

    row = all_companies[all_companies["id"] == sel].iloc[0]

    # ── 加载关联品牌 ───────────────────────
    conn = get_conn()
    current_brands = conn.execute(
        "SELECT id, brand_name FROM brands WHERE company_id = ? ORDER BY brand_name",
        (sel,)
    ).fetchall()
    all_brands_opts = conn.execute(
        "SELECT id, brand_name FROM brands ORDER BY brand_name"
    ).fetchall()
    conn.close()

    brand_names_map = {b[0]: b[1] for b in all_brands_opts}
    current_brand_ids = [b[0] for b in current_brands]
    current_brand_names = [b[1] for b in current_brands]

    with st.form(f"edit_company_{sel}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            edit_name = st.text_input("🏢 公司名", value=str(row["company_name"] or ""))
            edit_industry = st.selectbox("🏷️ 行业", ["服饰", "美妆", "电商", "MCN机构", "其他", "食品"],
                                        index=["服饰","美妆","电商","MCN机构","其他","食品"].index(row["industry_tag"]) if row["industry_tag"] in ["服饰","美妆","电商","MCN机构","其他","食品"] else 5)
        with c2:
            edit_parent = st.text_input("🏛️ 所属集团", value=str(row["parent_company"] or ""))
            edit_revenue = st.text_input("💰 年销售规模", value=str(row["annual_revenue"] or ""))
        c3, c4, c5 = st.columns(3)
        with c3:
            edit_year = st.number_input("📅 数据年份", min_value=2000, max_value=2030,
                                        value=int(row["revenue_year"]) if pd.notna(row["revenue_year"]) else 2024, step=1)
        with c4:
            edit_boss = st.number_input("📋 BOSS在招岗位", min_value=0, max_value=999,
                                        value=int(row["boss_job_count"]) if pd.notna(row["boss_job_count"]) else 0, step=1)
        with c5:
            edit_quality = st.selectbox("🏆 数据质量",
                                        ["pending_review", "verified", "needs_update", "low_confidence"],
                                        index=["pending_review", "verified", "needs_update", "low_confidence"].index(row["data_quality"]) if row["data_quality"] in ["pending_review", "verified", "needs_update", "low_confidence"] else 0)
        
        c6, c7 = st.columns(2)
        with c6:
            edit_competitors = st.text_input("🎯 关键竞品", value=str(row["competitors"] or ""))
        with c7:
            edit_check_date = st.text_input("📆 核查日期(YYYY-MM-DD)", value=str(row["boss_job_check_date"] or ""))
        edit_delete = st.checkbox("🚫 标记删除", value=bool(row["to_delete"]))

        # ── 关联品牌 ───────────────────────
        st.markdown("**🏷️ 关联品牌**")
        if current_brand_names:
            st.info("当前关联：" + "、".join(current_brand_names))
        else:
            st.info("暂无关联品牌")

        # 可选品牌列表（排除已关联的）
        avail_brands = [(bid, bname) for bid, bname in all_brands_opts if bid not in current_brand_ids]
        avail_names = [bname for bid, bname in avail_brands]
        avail_ids = [bid for bid, bname in avail_brands]

        if avail_names:
            to_add = st.multiselect(
                "➕ 添加关联品牌（选一个或多个后保存）",
                options=avail_names,
                format_func=lambda x: x,
                key=f"add_brands_{sel}"
            )
        else:
            st.success("✅ 所有品牌已关联完，无需添加新品牌")
            to_add = []

        submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)

        if submitted:
            import math
            try:
                def safe_str(val):
                    return val.strip() if isinstance(val, str) else val

                conn2 = get_conn()

                # 保存公司基础信息（含新字段）
                conn2.execute("""
                    UPDATE companies SET
                        company_name = ?,
                        industry_tag = ?,
                        parent_company = ?,
                        annual_revenue = ?,
                        revenue_year = ?,
                        competitors = ?,
                        boss_job_count = ?,
                        boss_job_check_date = ?,
                        data_quality = ?,
                        to_delete = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (
                    safe_str(edit_name),
                    edit_industry,
                    safe_str(edit_parent) or None,
                    safe_str(edit_revenue) or None,
                    int(edit_year) if edit_year else None,
                    safe_str(edit_competitors) or None,
                    int(edit_boss) if edit_boss else 0,
                    safe_str(edit_check_date) or None,
                    edit_quality,
                    1 if edit_delete else 0,
                    sel
                ))

                # 保存品牌关联
                if to_add:
                    brand_ids_to_add = [bid for bid, bname in avail_brands if bname in to_add]
                    for bid in brand_ids_to_add:
                        conn2.execute(
                            "UPDATE brands SET company_id = ? WHERE id = ?",
                            (sel, bid)
                        )

                conn2.commit()
                conn2.close()
                st.success(f"✅ 已保存：「{edit_name}」" +
                          (f" + 关联 {len(to_add)} 个品牌" if to_add else ""))
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 保存失败: {e}")

    # ── 批量删除 ─────────────────────────────
    st.divider()
    col_del, col_stats = st.columns([1, 3])
    with col_del:
        if st.button("🗑️ 彻底删除已标记公司", type="secondary", use_container_width=True):
            conn3 = get_conn()
            to_del = conn3.execute("SELECT company_name FROM companies WHERE to_delete = 1").fetchall()
            to_del_names = [t[0] for t in to_del]
            if to_del_names:
                for name in to_del_names:
                    conn3.execute("DELETE FROM benefits_structured WHERE company_name LIKE ?", (name+'%',))
                conn3.execute("DELETE FROM companies WHERE to_delete = 1")
                conn3.commit()
                st.success(f"✅ 已删除 {len(to_del_names)} 家公司")
                st.cache_data.clear()
                st.rerun()
            else:
                st.info("没有标记要删除的公司")
            conn3.close()

    with col_stats:
        stat_conn = get_conn()
        deleted_count = stat_conn.execute("SELECT COUNT(*) FROM companies WHERE to_delete = 1").fetchone()[0]
        stat_conn.close()
        col_s1, col_s2 = st.columns(2)
        col_s1.metric("已标记删除", deleted_count)
        col_s2.metric("总计公司数", len(df_filtered))

# ════════════════════════════════════════════════════════════════════════
# 页面：📰 公司动态
# ════════════════════════════════════════════════════════════════════════
elif page == "📰 公司动态":
    st.title("📰 公司动态")
    st.caption("人事变动 · 融资裁员 · 扩张收缩 · 均可录入 · 可搜索可编辑")

    conn = get_conn()
    # 修复 SQLite 不支持 NULLS LAST 的问题
    df = pd.read_sql("""
        SELECT e.id, e.company_name, e.event_type, e.event_date,
               e.details, e.source, e.notes, e.created_at,
               e.source_account, e.article_url, e.article_content, e.ai_summary,
               CASE WHEN e.event_date IS NULL THEN 1 ELSE 0 END AS null_date
        FROM company_events e
        ORDER BY null_date ASC, e.event_date DESC, e.created_at DESC
    """, conn)

    co_opts = [r[0] for r in conn.execute(
        "SELECT DISTINCT company_name FROM companies WHERE to_delete=0 ORDER BY company_name"
    ).fetchall()]
    conn.close()

    def sv(v):
        if v is None or (isinstance(v, float) and pd.isna(v)): return ""
        return str(v)

    # ── 筛选栏 ─────────────────────────────
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        kw = st.text_input("🔍 搜索公司/关键词", placeholder="输入公司名或事件关键词...", key="ev_kw")
    with c2:
        type_f = st.selectbox("事件类型", ["全部", "行业资讯", "新品", "行业趋势", "营销玩法", "创始人/高管", "渠道零售", "营收数据", "融资上市", "人事变动", "社会责任", "其他"], key="ev_type_f")
    with c3:
        co_f = st.selectbox("公司", ["全部"] + co_opts[:50], key="ev_co_f")

    d = df.copy()
    if kw:
        d = d[d['company_name'].str.contains(kw, na=False) |
               d['details'].fillna('').str.contains(kw, na=False) |
               d['notes'].fillna('').str.contains(kw, na=False) |
               d['article_content'].fillna('').str.contains(kw, na=False)]
    if type_f != "全部": d = d[d['event_type'] == type_f]
    if co_f != "全部":  d = d[d['company_name'] == co_f]

    st.info(f"共 {len(d)} 条动态记录（点击下方卡片展开查看完整内容）")

    # ── 📋 卡片列表（可展开查看全文）────────
    if not d.empty:
        # 每3个一组展示
        chunk_size = 3
        chunks = [d.iloc[i:i+chunk_size] for i in range(0, len(d), chunk_size)]

        for chunk in chunks:
            cols = st.columns(chunk_size)
            for col_idx, (_, row) in enumerate(chunk.iterrows()):
                with cols[col_idx]:
                    with st.container():
                        # 头部信息
                        ev_type = sv(row['event_type'])
                        ev_date = sv(row['event_date']) or sv(row['created_at'])[:10]
                        ev_co   = sv(row['company_name'])
                        ev_det  = sv(row['details'])
                        ev_note = sv(row['notes'])
                        ev_src  = sv(row['source'])
                        ev_acc  = sv(row['source_account'])
                        ev_url  = sv(row['article_url'])
                        ev_art  = sv(row['article_content'])
                        ev_ai   = sv(row['ai_summary'])

                        # 类型标签颜色
                        type_colors = {
                            "融资上市": "🟢", "行业趋势": "🔵", "营销玩法": "🟣",
                            "创始人/高管": "🟠", "渠道零售": "🔶", "营收数据": "💰",
                            "人事变动": "🔴", "新品": "🆕", "社会责任": "💚", "行业资讯": "📋"
                        }
                        type_icon = type_colors.get(ev_type, "📌")

                        # 卡片标题
                        card_title = f"{type_icon} {ev_co}"
                        subtitle = f"{ev_type} · {ev_date}"
                        if ev_acc:
                            subtitle += f" · {ev_acc}"

                        st.markdown(f"**{card_title}**")
                        st.caption(subtitle)

                        # 事件描述（展开前可见）
                        if ev_det:
                            st.text(ev_det[:100] + ("..." if len(ev_det) > 100 else ""))

                        # 关键数据（如果有）
                        if ev_note:
                            st.caption(f"📊 {ev_note[:60]}")

                        # 展开全文
                        with st.expander("🔎 展开查看完整内容"):
                            if ev_art:
                                st.markdown("**📄 文章摘要：**")
                                st.text(ev_art[:800] + ("..." if len(ev_art) > 800 else ""))
                                st.divider()
                            if ev_det:
                                st.markdown("**📝 事件描述：**")
                                st.text(ev_det)
                                st.divider()
                            if ev_note:
                                st.markdown(f"**💬 备注：**")
                                st.text(ev_note)
                            if ev_url and ev_url != ev_src:
                                st.divider()
                                st.markdown(f"**🔗 来源：** [{ev_url[:60]}]({ev_url})" if ev_url.startswith("http") else f"🔗 来源：{ev_url}")

                        st.markdown("---")

                        # 编辑/删除按钮
                        ev_opts_single = ["（不操作）"] + [f"{ev_co} | {ev_type} | {row['id']}"]
                        sel_single = st.selectbox("操作", ev_opts_single, key=f"ev_act_{row['id']}")
                        if sel_single != "（不操作）":
                            st.warning(f"⚠️ 确认要编辑/删除这条记录？ID={row['id']}")
                            if st.button("✅ 确认编辑", key=f"edit_{row['id']}"):
                                st.session_state['ev_edit_id'] = row['id']
                                st.rerun()
                            if st.button("🗑️ 确认删除", key=f"del_{row['id']}"):
                                conn_del = get_conn()
                                conn_del.execute("DELETE FROM company_events WHERE id=?", (row['id'],))
                                conn_del.commit(); conn_del.close()
                                st.success("✅ 已删除")
                                st.cache_data.clear()
                                st.rerun()
    else:
        st.info("暂无动态记录，请通过下方表单新增")

    st.divider()

    # ── ✏️ 新增 / 编辑表单 ───────────────────
    st.subheader("✏️ 新增 / 编辑动态")

    ev_opts = ["（新建记录）"] + [
        f"{r['company_name']} | {r['event_type']} | {r['id']}"
        for _, r in d.iterrows()
    ]
    if len(ev_opts) == 1:
        ev_opts = ["（新建记录）"] + [
            f"{r['company_name']} | {r['event_type']} | {r['id']}"
            for _, r in df.iterrows()
        ]

    sel_ev = st.selectbox("选择要编辑的记录", ev_opts, key="ev_sel")

    if sel_ev == "（新建记录）":
        with st.form("new_event", clear_on_submit=False):
            nc1, nc2 = st.columns([3, 1])
            with nc1:
                n_co = st.text_input("🏢 公司名 *", placeholder="如：安踏集团")
            with nc2:
                n_type = st.selectbox("📌 事件类型 *", ev_types_all)
            n_date  = st.text_input("📅 事件时间", placeholder="如：2025-03 或 2025年Q1")
            n_det   = st.text_area("📝 事件详情 *", placeholder="描述事件内容...", height=80)
            n_src   = st.text_input("🔗 信息来源", placeholder="如：36氪/脉脉/官网公告")
            n_note  = st.text_input("💬 备注/解读", placeholder="如：对招聘的影响？猎头机会？")
            submitted = st.form_submit_button("💾 新增记录", type="primary", use_container_width=True)
            if submitted:
                if not n_co.strip():
                    st.error("公司名必填")
                elif not n_det.strip():
                    st.error("事件详情必填")
                else:
                    conn2 = get_conn()
                    conn2.execute("""
                        INSERT INTO company_events
                            (company_name, event_type, event_date, details, source, notes)
                        VALUES (?,?,?,?,?,?)
                    """, (n_co.strip(), n_type, n_date.strip() or None,
                          n_det.strip(), n_src.strip() or None, n_note.strip() or None))
                    conn2.commit(); conn2.close()
                    st.success(f"✅ 已新增：「{n_co}」{n_type}")
                    st.cache_data.clear()
                    st.rerun()
    else:
        sel_id = int(sel_ev.split("|")[-1].strip())
        row = df[df['id'] == sel_id].iloc[0]
        def sv(v): return "" if (pd.isna(v) or v is None) else str(v)

        with st.form(f"edit_event_{sel_id}", clear_on_submit=False):
            ec1, ec2 = st.columns([3, 1])
            with ec1:
                e_co   = st.text_input("🏢 公司名",  value=sv(row['company_name']))
            with ec2:
                e_type = st.selectbox("📌 事件类型", ev_types_all,
                             index=ev_types_all.index(row['event_type']) if sv(row['event_type']) in ev_types_all else 0)
            e_date = st.text_input("📅 事件时间",  value=sv(row['event_date']))
            e_det  = st.text_area("📝 事件详情",   value=sv(row['details']), height=80)
            e_src  = st.text_input("🔗 信息来源",  value=sv(row['source']))
            e_note = st.text_input("💬 备注/解读", value=sv(row['notes']))
            submitted = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
            if submitted:
                conn3 = get_conn()
                conn3.execute("""
                    UPDATE company_events SET
                        company_name=?, event_type=?, event_date=?,
                        details=?, source=?, notes=?
                    WHERE id=?
                """, (e_co.strip(), e_type, e_date.strip() or None,
                      e_det.strip(), e_src.strip() or None, e_note.strip() or None,
                      sel_id))
                conn3.commit(); conn3.close()
                st.success(f"✅ 已保存：「{e_co}」")
                st.cache_data.clear()
                st.rerun()
            # 删除
            if st.form_submit_button("🗑️ 删除此记录", use_container_width=True):
                conn4 = get_conn()
                conn4.execute("DELETE FROM company_events WHERE id=?", (sel_id,))
                conn4.commit(); conn4.close()
                st.success("✅ 已删除")
                st.cache_data.clear()
                st.rerun()

# ════════════════════════════════════════════════════════════════════════
# 页面5：手动录入（精简版，去掉薪资录入tab）
# ════════════════════════════════════════════════════════════════════════
elif page == "➕ 手动录入":
    st.title("➕ 手动录入")
    tab1, tab2, tab3 = st.tabs(["📦 录入品牌", "🏢 录入公司", "🏠 录入福利"])

    with tab1:
        with st.form("add_brand", clear_on_submit=True):
            brand_name = st.text_input("品牌名 *")
            conn = get_conn()
            cos = conn.execute("SELECT id, company_name FROM companies ORDER BY company_name").fetchall()
            conn.close()
            co_opts = {c[1]: c[0] for c in cos}
            co_opts["（无/未知）"] = None
            co_sel = st.selectbox("所属公司", list(co_opts.keys()))
            col1, col2 = st.columns(2)
            industry = col1.selectbox("行业 *", ["服饰", "美妆", "电商", "食品", "其他"])
            category = col2.text_input("品类", placeholder="如：防晒衣、内衣...")
            position = st.selectbox("价格定位", ["未知", "高端", "中高端", "中端", "平价"])
            tags = st.text_input("标签（逗号分隔）")
            notes = st.text_area("备注")
            sub = st.form_submit_button("💾 保存")
            if sub and brand_name:
                conn = get_conn()
                conn.execute("""
                    INSERT OR REPLACE INTO brands (brand_name, company_id, industry, category, position, tags, notes, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (brand_name, co_opts[co_sel], industry, category, position, tags, notes))
                conn.commit(); conn.close()
                st.success(f"✅ 品牌「{brand_name}」已保存")

    with tab2:
        with st.form("add_company", clear_on_submit=True):
            co_name = st.text_input("公司全称 *")
            col1, col2 = st.columns(2)
            short = col1.text_input("简称")
            ind_tag = col2.selectbox("行业标签", ["服饰", "美妆", "电商", "食品", "其他"])
            legal = st.text_input("法定代表人")
            reg_cap = st.text_input("注册资本")
            reg_addr = st.text_input("注册地")
            col1, col2 = st.columns(2)
            year = col1.number_input("成立年份", 1990, 2026, 2020)
            business = col2.text_input("主营业务")
            website = st.text_input("官网")
            tags = st.text_input("标签")
            sub = st.form_submit_button("💾 保存")
            if sub and co_name:
                conn = get_conn()
                conn.execute("""
                    INSERT OR REPLACE INTO companies (company_name, short_name, legal_person, reg_capital,
                        reg_address, founded_year, business, website, tags, industry_tag, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (co_name, short, legal, reg_cap, reg_addr, year, business, website, tags, ind_tag))
                conn.commit(); conn.close()
                st.success(f"✅ 公司「{co_name}」已保存")

    with tab3:
        with st.form("add_benefit", clear_on_submit=True):
            co = st.text_input("公司名 *")
            col1, col2 = st.columns(2)
            dept = col1.text_input("部门")
            job = col2.text_input("职位")
            level = col2.selectbox("职级", ["","P1","P2","P3","P4","P5","P6","P7","M1","M2","M3","M4","M5"])
            col1, col2, col3 = st.columns(3)
            schedule = col1.selectbox("作息", ["","双休","大小周","单休","做五休二"])
            insurance = col2.selectbox("五险一金", ["","五险一金","六险一金","五险一金（最低基数）","五险一金（实缴）","五险","买社保（无公积金）","无社保"])
            meal = col3.text_input("餐补", placeholder="如：35元/天")
            col1, col2 = st.columns(2)
            transport = col1.text_input("交通补贴", placeholder="如：班车、打车报销")
            housing = col2.text_input("住宿/公积金", placeholder="如：包住、公积金12%")
            holiday = st.text_input("假期福利", placeholder="如：5天年假、旅游假")
            other = st.text_area("其他福利", placeholder="团建、节假日礼包、全勤奖...")
            sub = st.form_submit_button("💾 保存")
            if sub and co:
                conn = get_conn()
                conn.execute("""
                    INSERT INTO benefits_structured (company_name, dept, job_title, level,
                        work_schedule, insurance, meal, transport, housing, holiday, other)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (co, dept, job, level, schedule, insurance, meal, transport, housing, holiday, other))
                conn.commit(); conn.close()
                st.success(f"✅ 福利记录已保存")

# ════════════════════════════════════════════════════════════════════════
# 页面5：统计总览
# ════════════════════════════════════════════════════════════════════════
elif page == "📊 统计总览":
    st.title("📊 统计总览")

    conn = get_conn()
    b_count  = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    c_count  = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    benefits = conn.execute("SELECT COUNT(*) FROM benefits_structured").fetchone()[0]
    ind_dist = conn.execute("""
        SELECT industry_tag, COUNT(*) FROM companies
        WHERE industry_tag IS NOT NULL
        GROUP BY industry_tag ORDER BY COUNT(*) DESC
    """).fetchall()
    conn.close()

    c1, c2, c3 = st.columns(3)
    c1.metric("品牌", b_count)
    c2.metric("公司", c_count)
    c3.metric("福利记录", benefits)

    chart1, chart2 = st.columns(2)
    with chart1:
        st.subheader("公司行业分布")
        if ind_dist:
            st.bar_chart({r[0] or '其他': r[1] for r in ind_dist})
    with chart2:
        st.subheader("品牌行业分布")
        conn = get_conn()
        brand_ind = conn.execute("""
            SELECT industry, COUNT(*) FROM brands WHERE industry IS NOT NULL
            GROUP BY industry ORDER BY COUNT(*) DESC
        """).fetchall()
        conn.close()
        if brand_ind:
            st.bar_chart({r[0]: r[1] for r in brand_ind})

    # 品牌定位分布
    st.subheader("品牌定位分布")
    conn = get_conn()
    positions = conn.execute("""
        SELECT position, COUNT(*) FROM brands
        WHERE position IS NOT NULL AND position != ''
        GROUP BY position ORDER BY COUNT(*) DESC
    """).fetchall()
    conn.close()
    if positions:
        st.bar_chart({r[0]: r[1] for r in positions})

    # 有福利数据的公司
    st.subheader("有福利数据的公司（Top30）")
    conn = get_conn()
    benefit_companies = conn.execute("""
        SELECT b.company_name, b.industry_tag, b.sample_count
        FROM v_company_benefits b
        ORDER BY b.sample_count DESC LIMIT 30
    """).fetchall()
    conn.close()
    st.dataframe(
        pd.DataFrame(benefit_companies, columns=["公司", "行业", "福利样本数"]),
        use_container_width=True, hide_index=True
    )
