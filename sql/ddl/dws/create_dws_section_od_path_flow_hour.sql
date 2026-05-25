-- ============================================================
-- M2: 收费单元-OD(path)小时流量统计表 DDL
-- ============================================================
-- 作用: 按收费单元×OD-path映射×小时×车型粒度统计通行流量
-- 输入表: CSV:gstx_exit_with_min_fee, dwd_od_section_path_map
-- 输出表: {{table_name}}
-- 粒度: section_id × od_section_path_id × stat_hour × vehicle_type
-- 关键字段: section_id, od_section_path_id, stat_hour, vehicle_type, flow_cnt
-- 主键: id (自增) / 业务唯一键: (section_id, od_section_path_id, stat_hour, vehicle_type)
-- ============================================================
-- 查询模式:
--   Q1: 查询收费单元影响的所有OD(path)
--       WHERE section_id = <sid>
--       → idx_sopfh_section_odpath (section_id, od_section_path_id, vehicle_type)
--
--   Q2: 查询OD(path)的多日/月/小时流量
--       WHERE od_section_path_id = <oid> AND stat_hour BETWEEN <t1> AND <t2>
--       → idx_sopfh_odpath_hour (od_section_path_id, stat_hour, vehicle_type)
--
--   Q3: 查询收费单元的多日/月/小时流量
--       WHERE section_id = <sid> AND stat_hour BETWEEN <t1> AND <t2>
--       → idx_sopfh_section_hour (section_id, stat_hour, vehicle_type)
-- ============================================================

CREATE TABLE IF NOT EXISTS {{table_name}} (
    id                BIGSERIAL PRIMARY KEY,
    section_id        VARCHAR(64)  NOT NULL,
    od_section_path_id BIGINT      NOT NULL,
    stat_hour         TIMESTAMP    NOT NULL,
    vehicle_type      VARCHAR(32)  NOT NULL DEFAULT '0',
    flow_cnt          INTEGER      DEFAULT 0,
    source_flag       VARCHAR(32)  DEFAULT 'computed',
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_{{table_name}}
        UNIQUE (section_id, od_section_path_id, stat_hour, vehicle_type),
    CONSTRAINT chk_flow_non_negative CHECK (flow_cnt >= 0)
);

-- ============================================================================
-- 索引 — 按三大查询模式设计复合索引
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_sopfh_section_odpath
    ON {{table_name}}(section_id, od_section_path_id, vehicle_type);

CREATE INDEX IF NOT EXISTS idx_sopfh_odpath_hour
    ON {{table_name}}(od_section_path_id, stat_hour, vehicle_type);

CREATE INDEX IF NOT EXISTS idx_sopfh_section_hour
    ON {{table_name}}(section_id, stat_hour, vehicle_type);

-- ============================================================================
-- 注释
-- ============================================================================
COMMENT ON TABLE {{table_name}} IS
    '收费单元-OD(path)小时车型流量统计表 — 按收费单元经过时间统计的小时级流量(含车型维度)';
COMMENT ON COLUMN {{table_name}}.section_id IS
    '收费单元ID，来自修复后intervalgroup';
COMMENT ON COLUMN {{table_name}}.od_section_path_id IS
    'OD-Section-Path映射表ID，外键关联 dwd_od_section_path_map.id';
COMMENT ON COLUMN {{table_name}}.stat_hour IS
    '统计小时(带日期)，如 2026-03-01 12:00:00 代表12:00~13:00的流量，取自修复后intervaltimegroup中该收费单元对应时间截断到小时';
COMMENT ON COLUMN {{table_name}}.vehicle_type IS
    '车型编码，取自new_vehicletype，为空时为"0"';
COMMENT ON COLUMN {{table_name}}.flow_cnt IS
    '通行流量（自然车辆数），同一记录内相同(section_id,hour)只计1次';
