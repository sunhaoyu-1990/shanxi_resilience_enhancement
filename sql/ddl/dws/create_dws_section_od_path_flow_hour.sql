-- ============================================================
-- M2: 收费单元-OD(path)小时流量统计表 DDL
-- ============================================================
-- 作用: 按收费单元×OD-path映射×小时粒度统计通行流量
-- 输入表: CSV:gstx_exit_with_min_fee, dwd_od_section_path_map
-- 输出表: dws_section_od_path_flow_hour
-- 粒度: section_id × od_section_path_id × stat_hour
-- 关键字段: section_id, od_section_path_id, stat_hour, flow_cnt
-- 主键: id (自增) / 业务唯一键: (section_id, od_section_path_id, stat_hour)
-- ============================================================
-- 查询模式:
--   Q1: 查询收费单元影响的所有OD(path)
--       WHERE section_id = :sid
--       → idx_sopfh_section_odpath (section_id, od_section_path_id)
--
--   Q2: 查询OD(path)的多日/月/小时流量
--       WHERE od_section_path_id = :oid AND stat_hour BETWEEN :t1 AND :t2
--       → idx_sopfh_odpath_hour (od_section_path_id, stat_hour)
--
--   Q3: 查询收费单元的多日/月/小时流量
--       WHERE section_id = :sid AND stat_hour BETWEEN :t1 AND :t2
--       → idx_sopfh_section_hour (section_id, stat_hour)
-- ============================================================

CREATE TABLE IF NOT EXISTS dws_section_od_path_flow_hour (
    id                BIGSERIAL PRIMARY KEY,
    section_id        VARCHAR(64)  NOT NULL,
    od_section_path_id BIGINT      NOT NULL,
    stat_hour         TIMESTAMP    NOT NULL,
    flow_cnt          INTEGER      DEFAULT 0,
    source_flag       VARCHAR(32)  DEFAULT 'computed',
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dws_section_od_path_flow_hour
        UNIQUE (section_id, od_section_path_id, stat_hour),
    CONSTRAINT chk_flow_non_negative CHECK (flow_cnt >= 0)
);

-- ============================================================================
-- 索引 — 按三大查询模式设计复合索引
-- ============================================================================

-- Q1: 查询收费单元影响的所有OD(path)
--     WHERE section_id = :sid
--     复合索引可覆盖查找，避免回表取 od_section_path_id
CREATE INDEX IF NOT EXISTS idx_sopfh_section_odpath
    ON dws_section_od_path_flow_hour(section_id, od_section_path_id);

-- Q2: 查询OD(path)的多日/月/小时流量
--     WHERE od_section_path_id = :oid AND stat_hour BETWEEN :t1 AND :t2
--     复合索引前缀匹配od_section_path_id，范围扫描stat_hour
CREATE INDEX IF NOT EXISTS idx_sopfh_odpath_hour
    ON dws_section_od_path_flow_hour(od_section_path_id, stat_hour);

-- Q3: 查询收费单元的多日/月/小时流量
--     WHERE section_id = :sid AND stat_hour BETWEEN :t1 AND :t2
--     复合索引前缀匹配section_id，范围扫描stat_hour
CREATE INDEX IF NOT EXISTS idx_sopfh_section_hour
    ON dws_section_od_path_flow_hour(section_id, stat_hour);

-- 注释
COMMENT ON TABLE dws_section_od_path_flow_hour IS
    '收费单元-OD(path)小时流量统计表 — 按收费单元经过时间统计的小时级流量';
COMMENT ON COLUMN dws_section_od_path_flow_hour.section_id IS
    '收费单元ID，来自修复后intervalgroup';
COMMENT ON COLUMN dws_section_od_path_flow_hour.od_section_path_id IS
    'OD-Section-Path映射表ID，外键关联 dwd_od_section_path_map.id';
COMMENT ON COLUMN dws_section_od_path_flow_hour.stat_hour IS
    '统计小时(带日期)，如 2026-03-01 12:00:00 代表12:00~13:00的流量，取自修复后intervaltimegroup中该收费单元对应时间截断到小时';
COMMENT ON COLUMN dws_section_od_path_flow_hour.flow_cnt IS
    '通行流量（自然车辆数），同一记录内相同(section_id,hour)只计1次';
