-- ============================================================
-- 受影响OD流量表 DDL
-- ============================================================
-- 功能: 施工影响分析后的受影响OD流量
-- 模块: M3
-- 输入表: dws_section_capacity_day, dws_section_od_flow_day
-- 输出表: dws_impacted_od_flow_day
-- 粒度: 方案 × 日期 × OD × 车型
-- 关键字段: scheme_id, stat_date, od_id, vehicle_type

CREATE TABLE IF NOT EXISTS dws_impacted_od_flow_day (
  -- 主键组成部分
  scheme_id VARCHAR(64) NOT NULL,
  stat_date DATE NOT NULL,
  od_id VARCHAR(128) NOT NULL,
  vehicle_type VARCHAR(32) NOT NULL,

  -- 影响分析结果
  impacted_flow_cnt INTEGER DEFAULT 0,  -- 受影响自然车辆数
  impacted_flow_pcu DECIMAL(12, 2) DEFAULT 0,  -- 受影响PCU数
  impact_ratio DECIMAL(5, 4) DEFAULT 0,  -- 影响比例 0-1
  adjusted_flow_cnt INTEGER DEFAULT 0,  -- 需要重新分配的流量

  -- 参考数据
  original_flow_cnt INTEGER,
  original_flow_pcu DECIMAL(12, 2),
  capacity_pcu DECIMAL(12, 2),

  -- 数据质量
  source_flag VARCHAR(32) DEFAULT 'rule',  -- 'actual' / 'filled' / 'rule'

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dws_impacted_od_flow_day PRIMARY KEY (
    scheme_id, stat_date, od_id, vehicle_type
  ),
  CONSTRAINT chk_impact_ratio CHECK (impact_ratio >= 0 AND impact_ratio <= 1),
  CONSTRAINT chk_impacted_flow CHECK (impacted_flow_cnt >= 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_imp_od_scheme ON dws_impacted_od_flow_day(scheme_id);
CREATE INDEX IF NOT EXISTS idx_imp_od_date ON dws_impacted_od_flow_day(stat_date);
CREATE INDEX IF NOT EXISTS idx_imp_od_od ON dws_impacted_od_flow_day(od_id);
CREATE INDEX IF NOT EXISTS idx_imp_od_vehicle ON dws_impacted_od_flow_day(vehicle_type);

COMMENT ON TABLE dws_impacted_od_flow_day IS '施工影响下受影响OD及迁移流量结果表';
COMMENT ON COLUMN dws_impacted_od_flow_day.impact_ratio IS '影响比例，0表示无影响，1表示完全受影响';
COMMENT ON COLUMN dws_impacted_od_flow_day.adjusted_flow_cnt IS '需要进入后续路径分配的流量';
