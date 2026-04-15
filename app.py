"""
寻源地图 · 只读版（部署至 Streamlit Cloud）
"""
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="寻源地图", page_icon="🗺️", layout="wide")

DB_PATH = os.path.join(os.path.dirname(__file__), "db/source_map.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def qdf(sql, params=()):
    conn = get_conn()
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df

def sv(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v)

conn = get_conn()
c_count   = conn.execute("SELECT COUNT(*) FROM companies WHERE COALESCE(to_delete,0)=0").fetchone()[0]
b_count   = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
ben_count = conn.execute("SELECT COUNT(*) FROM salary_benchmarks").fetchone()[0]
benf_cnt  = conn.execute("SELECT COUNT(*) FROM benefits_structured").fetchone()[0]
ev_count  = conn.execute("SELECT COUNT(*) FROM company_events").fetchone()[0]
conn.close()

st.markdown(f"""<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;padding:10px 16px;margin-bottom:16px">
<b>🗺️ 寻源地图 · 只读版</b> &nbsp; <span style="color:#888">数据截至 2026-04-15 · 共 {c_count} 家公司 / {b_count} 个品牌</span>
</div>""", unsafe_allow_html=True)

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("公司", c_count)
c2.metric("品牌", b_count)
c3.metric("薪资记录", ben_count)
c4.metric("福利记录", benf_cnt)
c5.metric("公司动态", ev_count)

st.divider()
page = st.radio("选择页面",
    ["🔍 公司搜索","🏷️ 品牌库","🏢 公司管理","📰 公司动态","🍎 福利查询","📊 统计总览"],
    horizontal=True)

# ── 页面1：公司搜索 ──────────────────────
if page == "🔍 公司搜索":
    st.title("🔍 公司搜索")
    col_kw,col_ind = st.columns([3,1])
    kw  = col_kw.text_input("关键词搜索", placeholder="公司名 / 品牌名 / 行业...", key="kw")
    ind = col_ind.selectbox("行业",["全部","服饰","美妆","电商","MCN机构","其他","食品"], key="ind")
    df = qdf("""SELECT c.id, c.company_name, c.industry_tag, c.business,
        c.annual_revenue, c.revenue_year, c.data_quality,
        c.founded_year, c.reg_address,
        (SELECT GROUP_CONCAT(brand_name,'、') FROM brands WHERE company_id=c.id) as brands,
        (SELECT COUNT(*) FROM salary_benchmarks WHERE company_name LIKE c.company_name||'%') as bench_cnt,
        (SELECT COUNT(*) FROM benefits_structured WHERE company_name LIKE c.company_name||'%') as benf_cnt
        FROM companies c WHERE COALESCE(c.to_delete,0)=0 ORDER BY c.industry_tag,c.company_name""")
    d = df.copy()
    if kw: d=d[d.company_name.str.contains(kw,na=False)|d.business.fillna('').str.contains(kw,na=False)|d.brands.fillna('').str.contains(kw,na=False)]
    if ind!="全部": d=d[d.industry_tag==ind]
    st.info(f"匹配 {len(d)} 家公司")
    st.dataframe(d.rename(columns={'company_name':'公司名','industry_tag':'行业','business':'主营业务',
        'annual_revenue':'年销售规模','revenue_year':'年份','data_quality':'数据质量',
        'founded_year':'成立','reg_address':'注册地','brands':'关联品牌',
        'bench_cnt':'薪资','benf_cnt':'福利'}),
        column_config={"公司名":st.column_config.TextColumn("公司名",width="medium"),
            "行业":st.column_config.TextColumn("行业",width="small"),
            "年销售规模":st.column_config.TextColumn("年销售规模",width="medium"),
            "年份":st.column_config.NumberColumn("年份",width="tiny"),
            "成立":st.column_config.NumberColumn("成立",width="tiny"),
            "注册地":st.column_config.TextColumn("注册地",width="medium"),
            "数据质量":st.column_config.TextColumn("质量",width="small"),
            "薪资":st.column_config.NumberColumn("薪资",width="tiny"),
            "福利":st.column_config.NumberColumn("福利",width="tiny")},
        hide_index=True,use_container_width=True)
    if st.button("📥 导出搜索结果",use_container_width=True):
        csv=d.to_csv(index=False,encoding='utf-8-sig')
        st.download_button("⬇ 下载 CSV",data=csv,
            file_name=f"寻源地图_公司搜索_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",use_container_width=True)

# ── 页面2：品牌库 ──────────────────────
elif page == "🏷️ 品牌库":
    st.title("🏷️ 品牌库")
    col_kw,col_ind=st.columns([3,1])
    kw=col_kw.text_input("搜索品牌/公司",placeholder="输入品牌名或公司名...",key="brand_kw")
    ind=col_ind.selectbox("行业",["全部","服饰","美妆","电商","食品","其他"],key="brand_ind")
    df=qdf("""SELECT b.id, b.brand_name, c.company_name, c.industry_tag,
        b.industry, b.category, b.position, b.tags,
        (SELECT COUNT(*) FROM salary_benchmarks WHERE company_name LIKE c.company_name||'%') as bench_cnt,
        (SELECT COUNT(*) FROM benefits_structured WHERE company_name LIKE c.company_name||'%') as benf_cnt
        FROM brands b LEFT JOIN companies c ON b.company_id=c.id ORDER BY b.brand_name""")
    d=df.copy()
    if kw: d=d[d.brand_name.str.contains(kw,na=False)|d.company_name.fillna('').str.contains(kw,na=False)]
    if ind!="全部": d=d[d.industry_tag==ind]
    st.info(f"共 {len(d)} 个品牌")
    st.dataframe(d.rename(columns={'brand_name':'品牌名','company_name':'所属公司','industry_tag':'行业',
        'industry':'品类','category':'品类细分','position':'定位','tags':'标签',
        'bench_cnt':'薪资','benf_cnt':'福利'}),
        column_config={"品牌名":st.column_config.TextColumn("品牌名"),
            "所属公司":st.column_config.TextColumn("所属公司"),
            "行业":st.column_config.TextColumn("行业",width="small"),
            "定位":st.column_config.TextColumn("定位",width="small"),
            "薪资":st.column_config.NumberColumn("薪资",width="tiny"),
            "福利":st.column_config.NumberColumn("福利",width="tiny")},
        hide_index=True,use_container_width=True)
    if st.button("📥 导出品牌库",use_container_width=True):
        csv=d.to_csv(index=False,encoding='utf-8-sig')
        st.download_button("⬇ 下载 CSV",data=csv,
            file_name=f"寻源地图_品牌库_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",use_container_width=True)

# ── 页面3：公司管理 ──────────────────────
elif page == "🏢 公司管理":
    st.title("🏢 公司管理")
    col_kw,col_ind=st.columns([3,1])
    kw=col_kw.text_input("搜索公司",placeholder="公司名...",key="co_kw")
    ind=col_ind.selectbox("行业",["全部","服饰","美妆","电商","MCN机构","其他","食品"],key="co_ind")
    df=qdf("""SELECT c.id, c.company_name, c.industry_tag, c.parent_company,
        c.annual_revenue, c.revenue_year, c.data_quality,
        c.founded_year, c.reg_address, c.business,
        (SELECT GROUP_CONCAT(brand_name,'、') FROM brands WHERE company_id=c.id) as brands,
        (SELECT COUNT(*) FROM salary_benchmarks WHERE company_name LIKE c.company_name||'%') as bench_cnt,
        (SELECT COUNT(*) FROM benefits_structured WHERE company_name LIKE c.company_name||'%') as benf_cnt
        FROM companies c WHERE COALESCE(c.to_delete,0)=0 ORDER BY c.industry_tag,c.company_name""")
    d=df.copy()
    if kw: d=d[d.company_name.str.contains(kw,na=False)]
    if ind!="全部": d=d[d.industry_tag==ind]
    st.info(f"共 {len(d)} 家公司")
    st.dataframe(d.rename(columns={'company_name':'公司名','industry_tag':'行业','parent_company':'所属集团',
        'annual_revenue':'年销售规模','revenue_year':'年份','data_quality':'质量',
        'founded_year':'成立','reg_address':'注册地','business':'主营业务','brands':'关联品牌',
        'bench_cnt':'薪资','benf_cnt':'福利'}),
        column_config={"公司名":st.column_config.TextColumn("公司名"),
            "行业":st.column_config.TextColumn("行业",width="small"),
            "年销售规模":st.column_config.TextColumn("年销售规模",width="medium"),
            "年份":st.column_config.NumberColumn("年份",width="tiny"),
            "成立":st.column_config.NumberColumn("成立",width="tiny"),
            "质量":st.column_config.TextColumn("质量",width="small"),
            "薪资":st.column_config.NumberColumn("薪资",width="tiny"),
            "福利":st.column_config.NumberColumn("福利",width="tiny")},
        hide_index=True,use_container_width=True)
    if st.button("📥 导出公司管理",use_container_width=True):
        csv=d.to_csv(index=False,encoding='utf-8-sig')
        st.download_button("⬇ 下载 CSV",data=csv,
            file_name=f"寻源地图_公司管理_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",use_container_width=True)

# ── 页面4：公司动态 ──────────────────────
elif page == "📰 公司动态":
    st.title("📰 公司动态")
    col_kw,col_type=st.columns([3,1])
    kw=col_kw.text_input("搜索关键词",placeholder="公司名或事件关键词...",key="ev_kw")
    t=col_type.selectbox("类型",["全部","行业资讯","新品","行业趋势","营销玩法",
        "创始人/高管","渠道零售","营收数据","融资上市","人事变动","社会责任","其他"],key="ev_t")
    df=qdf("""SELECT e.id, e.company_name, e.event_type, e.event_date,
        e.details, e.source, e.notes, e.created_at
        FROM company_events e ORDER BY e.created_at DESC""")
    d=df.copy()
    if kw: d=d[d.company_name.str.contains(kw,na=False)|d.details.fillna('').str.contains(kw,na=False)|d.notes.fillna('').str.contains(kw,na=False)]
    if t!="全部": d=d[d.event_type==t]
    st.info(f"共 {len(d)} 条动态")
    type_colors={"融资上市":"🟢","行业趋势":"🔵","营销玩法":"🟣","创始人/高管":"🟠",
        "渠道零售":"🔶","营收数据":"💰","人事变动":"🔴","新品":"🆕","行业资讯":"📋"}
    for i in range(0,len(d),3):
        cols=st.columns(3)
        for j,(_,row) in enumerate(d.iloc[i:i+3].iterrows()):
            with cols[j]:
                ev_type=sv(row['event_type'])
                ev_date=sv(row['event_date']) or str(row['created_at'])[:10]
                icon=type_colors.get(ev_type,"📌")
                st.markdown(f"**{icon} {sv(row['company_name'])}**")
                st.caption(f"{ev_type} · {ev_date}")
                det=sv(row['details'])
                if det: st.text(det[:100]+("..." if len(det)>100 else ""))
                with st.expander("查看详情"):
                    st.text(det)
                    if row['notes']: st.caption(f"💬 {sv(row['notes'])}")
                    if row['source']: st.caption(f"🔗 来源: {sv(row['source'])}")
                st.markdown("---")
    if st.button("📥 导出公司动态",use_container_width=True):
        csv=d.to_csv(index=False,encoding='utf-8-sig')
        st.download_button("⬇ 下载 CSV",data=csv,
            file_name=f"寻源地图_公司动态_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",use_container_width=True)

# ── 页面5：福利查询 ──────────────────────
elif page == "🍎 福利查询":
    st.title("🍎 福利查询")
    col_kw,col_ind,col_sched=st.columns([3,1,1])
    kw=col_kw.text_input("搜索公司",placeholder="公司名...",key="ben_kw")
    ind=col_ind.selectbox("行业",["全部","服饰","美妆","电商","MCN机构","其他"],key="ben_ind")
    sched=col_sched.selectbox("作息",["全部","双休","大小周","单休"],key="ben_sched")
    df=qdf("""SELECT b.id, b.company_name, c.industry_tag,
        b.dept, b.job_title, b.level,
        b.work_schedule, b.insurance, b.housing_fund_rate,
        b.meal, b.transport, b.housing, b.holiday, b.other
        FROM benefits_structured b
        LEFT JOIN companies c ON b.company_name LIKE c.company_name||'%'
        ORDER BY b.company_name, b.created_at DESC""")
    d=df.copy()
    if kw: d=d[d.company_name.str.contains(kw,na=False)]
    if ind!="全部": d=d[d.industry_tag==ind]
    if sched!="全部": d=d[d.work_schedule==sched]
    st.info(f"共 {len(d)} 条福利记录")
    st.dataframe(d.rename(columns={'company_name':'公司','industry_tag':'行业',
        'dept':'部门','job_title':'职位','level':'职级',
        'work_schedule':'作息','insurance':'五险一金','housing_fund_rate':'公积金比例',
        'meal':'餐补','transport':'交通','housing':'住宿','holiday':'假期','other':'其他'}),
        column_config={"公司":st.column_config.TextColumn("公司",width="medium"),
            "行业":st.column_config.TextColumn("行业",width="small"),
            "作息":st.column_config.TextColumn("作息",width="small"),
            "五险一金":st.column_config.TextColumn("五险一金",width="medium"),
            "公积金比例":st.column_config.TextColumn("公积金",width="small")},
        hide_index=True,use_container_width=True)
    if st.button("📥 导出福利数据",use_container_width=True):
        csv=d.to_csv(index=False,encoding='utf-8-sig')
        st.download_button("⬇ 下载 CSV",data=csv,
            file_name=f"寻源地图_福利查询_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",use_container_width=True)

# ── 页面6：统计总览 ──────────────────────
elif page == "📊 统计总览":
    st.title("📊 统计总览")
    c1,c2,c3=st.columns(3)
    c1.metric("公司",c_count)
    c2.metric("品牌",b_count)
    c3.metric("福利记录",benf_cnt)
    chart_ind,chart_pos=st.columns(2)
    with chart_ind:
        st.subheader("公司行业分布")
        conn=get_conn()
        ind_dist=conn.execute("""SELECT industry_tag,COUNT(*) as cnt FROM companies
            WHERE industry_tag IS NOT NULL AND COALESCE(to_delete,0)=0
            GROUP BY industry_tag ORDER BY cnt DESC""").fetchall()
        conn.close()
        if ind_dist: st.bar_chart({r[0]:r[1] for r in ind_dist})
    with chart_pos:
        st.subheader("品牌定位分布")
        conn=get_conn()
        pos_dist=conn.execute("""SELECT position,COUNT(*) as cnt FROM brands
            WHERE position IS NOT NULL AND position!='' GROUP BY position ORDER BY cnt DESC""").fetchall()
        conn.close()
        if pos_dist: st.bar_chart({r[0]:r[1] for r in pos_dist})
    st.subheader("有福利数据的公司（Top20）")
    conn=get_conn()
    top=conn.execute("""SELECT b.company_name,c.industry_tag,COUNT(*) as cnt
        FROM benefits_structured b
        LEFT JOIN companies c ON b.company_name LIKE c.company_name||'%'
        GROUP BY b.company_name ORDER BY cnt DESC LIMIT 20""").fetchall()
    conn.close()
    st.dataframe(pd.DataFrame(top,columns=["公司","行业","福利样本"]),
        use_container_width=True,hide_index=True)
