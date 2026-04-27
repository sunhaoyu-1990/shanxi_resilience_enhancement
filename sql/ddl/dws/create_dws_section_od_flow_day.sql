-- ============================================================
-- 收费单元OD日流量表 DDL
-- ============================================================
-- 功能: 收费单元-OD粒度的日流量统计
-- 模块: M2
-- 输入表: dwd_single_trip_info, dwd_od_path_map
-- 输出表: dws_section_od_flow_day
-- 粒度: 收费单元 × OD × 日期 × 车型
-- 关键字段: section_id, od_id, stat_date, vehicle_type

CREATE TABLE IF NOT EXISTS dws_section_od_flow_day (
  -- 主键组成部分
  section_id VARCHAR(64) NOT NULL,
  od_id VARCHAR(128) NOT NULL,
  stat_date DATE NOT NULL,
  vehicle_type VARCHAR(32) NOT NULL,

  -- 流量统计
  flow_cnt INTEGER DEFAULT 0,  -- 自然车辆数
  flow_pcu DECIMAL(12, 2) DEFAULT 0,  -- PCU当量数

  -- 数据质量
  source_flag VARCHAR(32) DEFAULT 'actual',  -- 'actual' / 'filled' / 'rule'

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dws_section_od_flow_day PRIMARY KEY (
    section_id, od_id, stat_date, vehicle_type
  ),
  CONSTRAINT chk_flow_non_negative CHECK (flow_cnt >= 0 AND flow_pcu >= 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_sod_flow_section ON dws_section_od_flow_day(section_id);
CREATE INDEX IF NOT EXISTS idx_sod_flow_od ON dws_section_od_flow_day(od_id);
CREATE INDEX IF NOT EXISTS idx_sod_flow_date ON dws_section_od_flow_day(stat_date);
CREATE INDEX IF NOT EXISTS idx_sod_flow_source ON dws_section_od_flow_day(source_flag);

COMMENT ON TABLE dws_section_od_flow_day IS '收费单元-OD-日期-车型粒度流量统计表';
COMMENT ON COLUMN dws_section_od_flow_day.source_flag IS '数据来源标识：actual/filled/rule';
