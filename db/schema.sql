-- 寻源地图 数据库结构

CREATE TABLE IF NOT EXISTS brands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name  TEXT NOT NULL UNIQUE,         -- 品牌名
    company_id  INTEGER,                       -- 所属公司ID
    industry    TEXT NOT NULL,                 -- 行业赛道：服饰/美妆/电商/食品...
    category    TEXT,                          -- 主品类：防晒衣/鲨鱼裤/内衣/...
    position    TEXT,                         -- 价格定位：高/中/低/高端
    tags        TEXT,                          -- 标签，逗号分隔
    notes       TEXT,                          -- 备注：融资/代言人/特色...
    source_url  TEXT,                          -- 数据来源
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS companies (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,        -- 公司全称
    short_name   TEXT,                        -- 简称
    legal_person TEXT,                        -- 法定代表人
    reg_capital  TEXT,                        -- 注册资本
    reg_address  TEXT,                        -- 注册地
    founded_year INTEGER,                     -- 成立年份
    website      TEXT,
    business     TEXT,                        -- 主营业务
    parent_id    INTEGER,                     -- 母公司ID（大型集团）
    tags         TEXT,
    notes        TEXT,
    source_url   TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS industries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    industry_name TEXT NOT NULL UNIQUE,       -- 赛道名
    description  TEXT,                        -- 赛道描述
    talent_demand TEXT,                        -- 人才需求特点
    key_companies TEXT,                        -- 核心玩家（逗号分隔品牌名）
    tags         TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS source_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_type     TEXT NOT NULL,               -- 记录类型：brand/company/industry/article
    ref_id       INTEGER,                     -- 关联ID
    title        TEXT NOT NULL,               -- 标题
    content      TEXT,                        -- 内容摘要
    source_url   TEXT,                        -- 原文链接
    source_name  TEXT,                        -- 来源：天猫榜单/亿邦动力/...
    uploaded_by  TEXT DEFAULT '洛托姆',
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_brands_industry  ON brands(industry);
CREATE INDEX idx_brands_company   ON brands(company_id);
CREATE INDEX idx_companies_parent ON companies(parent_id);
