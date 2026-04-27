-- ============================================================
-- 收费单元日通行能力表 DDL
-- ============================================================
-- 功能: 施工期间收费单元日通行能力
-- 模块: M1
-- 输入表: dim_section_info, dwd_scheme_section_map, dim_capacity_rule
-- 输出表: dws_section_capacity_day
-- 粒度: 收费单元 × 日期 × 车型
-- 关键字段: section_id, stat_date, vehicle_type

CREATE TABLE IF NOT EXISTS dws_section_capacity_day (
  -- 主键组成部分
  section_id VARCHAR(64) NOT NULL,
  stat_date DATE NOT NULL,
  vehicle_type VARCHAR(32) NOT NULL,

  -- 通行能力信息
  capacity_pcu DECIMAL(12, 2) NOT NULL,

  -- 上下文
  scheme_id VARCHAR(64),
  rule_id VARCHAR(64),

  -- 可用车道数
  total_lane_cnt INTEGER,
  available_lane_cnt INTEGER,

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dws_section_capacity_day PRIMARY KEY (
    section_id, stat_date, vehicle_type
  ),
  CONSTRAINT chk_capacity_non_negative CHECK (capacity_pcu >= 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_cap_day_scheme ON dws_section_capacity_day(scheme_id);
CREATE INDEX IF NOT EXISTS idx_cap_day_date ON dws_section_capacity_day(stat_date);
CREATE INDEX IF NOT EXISTS idx_cap_day_vehicle ON dws_section_capacity_day(vehicle_type);

COMMENT ON TABLE dws_section_capacity_day IS '施工期间收费单元日可通行当量结果表';
COMMENT ON COLUMN dws_section_capacity_day.capacity_pcu IS '日可通行当量（PCU）';
