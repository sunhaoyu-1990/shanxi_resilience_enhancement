-- ============================================================
-- DDL: dim_toll_road
-- ============================================================
-- 作用: 收费路段信息维表
-- 输入: 收费路段.xls
-- 输出: 无
-- 粒度: 收费路段编号
-- 关键字段: 收费路段编号, 路段性质
-- ============================================================
-- 数据说明:
--   - 共 110 条收费路段记录
--   - 还贷性: 84 条（交控集团）
--   - 经营性: 26 条
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_toll_road (
    序号 int NULL,
    收费路段编号 varchar(20) NOT NULL,
    收费路段名称 varchar(100) NULL,
    路段性质 varchar(10) NULL,
    路段类型 varchar(10) NULL,
    联网收费状态 varchar(10) NULL,
    路段里程 decimal(12,3) NULL,
    起始计费位置经度 decimal(12,8) NULL,
    起始计费位置纬度 decimal(12,8) NULL,
    起始计费位置桩号 varchar(20) NULL,
    终止计费位置桩号 varchar(20) NULL,
    终止计费位置经度 decimal(12,8) NULL,
    终止计费位置纬度 decimal(12,8) NULL,
    是否纳税 varchar(5) NULL,
    税率 decimal(6,3) NULL,
    所属业主编号 varchar(20) NULL,
    路段收费方式 varchar(10) NULL,
    重合收费公路编号 varchar(20) NULL,
    开工时间 date NULL,
    通车时间 date NULL,
    停止收费时间 date NULL,
    待用税率 decimal(6,3) NULL,
    待用税率生效时间 date NULL,
    source_flag varchar(16) DEFAULT 'actual',
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dim_toll_road PRIMARY KEY (收费路段编号)
);

COMMENT ON TABLE dim_toll_road IS '收费路段信息维表';
COMMENT ON COLUMN dim_toll_road.序号 IS '序号';
COMMENT ON COLUMN dim_toll_road.收费路段编号 IS '收费路段编号（主键）';
COMMENT ON COLUMN dim_toll_road.收费路段名称 IS '收费路段名称';
COMMENT ON COLUMN dim_toll_road.路段性质 IS '路段性质（还贷性/经营性）- 判断是否交控集团的关键字段';
COMMENT ON COLUMN dim_toll_road.路段类型 IS '路段类型（高速路段/普通路段）';
COMMENT ON COLUMN dim_toll_road.联网收费状态 IS '联网收费状态（联网收费/独立收费）';
COMMENT ON COLUMN dim_toll_road.路段里程 IS '路段里程（米）';
COMMENT ON COLUMN dim_toll_road.起始计费位置经度 IS '起始计费位置经度';
COMMENT ON COLUMN dim_toll_road.起始计费位置纬度 IS '起始计费位置纬度';
COMMENT ON COLUMN dim_toll_road.起始计费位置桩号 IS '起始计费位置桩号';
COMMENT ON COLUMN dim_toll_road.终止计费位置桩号 IS '终止计费位置桩号';
COMMENT ON COLUMN dim_toll_road.终止计费位置经度 IS '终止计费位置经度';
COMMENT ON COLUMN dim_toll_road.终止计费位置纬度 IS '终止计费位置纬度';
COMMENT ON COLUMN dim_toll_road.是否纳税 IS '是否纳税（是/否）';
COMMENT ON COLUMN dim_toll_road.税率 IS '税率';
COMMENT ON COLUMN dim_toll_road.所属业主编号 IS '所属业主编号';
COMMENT ON COLUMN dim_toll_road.路段收费方式 IS '路段收费方式（封闭式/开放式）';
COMMENT ON COLUMN dim_toll_road.重合收费公路编号 IS '重合收费公路编号';
COMMENT ON COLUMN dim_toll_road.开工时间 IS '开工时间';
COMMENT ON COLUMN dim_toll_road.通车时间 IS '通车时间';
COMMENT ON COLUMN dim_toll_road.停止收费时间 IS '停止收费时间';
COMMENT ON COLUMN dim_toll_road.待用税率 IS '待用税率';
COMMENT ON COLUMN dim_toll_road.待用税率生效时间 IS '待用税率生效时间';
COMMENT ON COLUMN dim_toll_road.source_flag IS '数据来源标识（actual/filled/rule/api/computed）';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_dim_toll_road_路段性质 ON dim_toll_road(路段性质);
CREATE INDEX IF NOT EXISTS idx_dim_toll_road_路段类型 ON dim_toll_road(路段类型);
CREATE INDEX IF NOT EXISTS idx_dim_toll_road_所属业主编号 ON dim_toll_road(所属业主编号);