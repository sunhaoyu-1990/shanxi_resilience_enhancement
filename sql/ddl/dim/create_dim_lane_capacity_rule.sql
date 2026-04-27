-- ============================================================
-- M1: Create Dimension Table - Lane Traffic Capacity Rule
-- ============================================================
-- 作用: 存储各设计时速下单车道高速通行能力对应规则
-- 输入表: 手动配置规则
-- 输出表: dim_lane_capacity_rule
-- 粒度: 每条规则一行（按设计时速划分）
-- 关键字段: id, design_speed_kmh, single_lane_traffic_capacity
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_lane_capacity_rule (
  -- 主键
  id                           VARCHAR(20)  NOT NULL,

  -- 设计时速与通行能力
  design_speed_kmh             FLOAT8       NOT NULL,
  single_lane_traffic_capacity FLOAT8       NOT NULL,

  -- 元数据
  remark     TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_lane_capacity_rule PRIMARY KEY (id),
  CONSTRAINT uq_dim_lane_capacity_rule_speed UNIQUE (design_speed_kmh),
  CONSTRAINT chk_design_speed_positive   CHECK (design_speed_kmh > 0),
  CONSTRAINT chk_lane_capacity_positive  CHECK (single_lane_traffic_capacity > 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_lane_cap_speed ON dim_lane_capacity_rule(design_speed_kmh);

-- 表与字段注释
COMMENT ON TABLE dim_lane_capacity_rule IS '各设计时速下单车道高速通行能力规则表';
COMMENT ON COLUMN dim_lane_capacity_rule.id                           IS '规则 ID';
COMMENT ON COLUMN dim_lane_capacity_rule.design_speed_kmh             IS '设计时速，单位 km/h';
COMMENT ON COLUMN dim_lane_capacity_rule.single_lane_traffic_capacity IS '单车道通行能力，单位 pcu/h';
