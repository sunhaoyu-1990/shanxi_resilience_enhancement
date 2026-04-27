-- ============================================================
-- 通行能力规则维表 DDL
-- ============================================================
-- 功能: 车道数与通行能力映射规则
-- 模块: M1
-- 输入表: 手动配置规则
-- 输出表: dim_capacity_rule
-- 粒度: 每条规则一行
-- 关键字段: rule_id

-- TODO: 确认 capacity_pcu 计算公式
-- TODO: 确认 vehicle_type 枚举值
-- TODO: 添加更复杂的规则（坡度、桥梁、隧道等）

CREATE TABLE IF NOT EXISTS dim_capacity_rule (
  -- 主键
  rule_id VARCHAR(64) NOT NULL,

  -- 规则属性
  lane_cnt INTEGER NOT NULL,  -- 可用车道数
  vehicle_type VARCHAR(32) NOT NULL,  -- 'passenger_small' / 'passenger_medium' / 'truck_small' / 'truck_medium' / 'truck_large'

  -- PCU（当量小客车）日通行能力
  capacity_pcu DECIMAL(12, 2) NOT NULL,

  -- 调整系数（未来使用）
  speed_limit INTEGER,  -- km/h
  slope_factor DECIMAL(5, 4),  -- 坡度系数
  bridge_factor DECIMAL(5, 4),  -- 桥隧系数

  -- 有效期
  valid_start_date DATE,
  valid_end_date DATE,

  -- 元数据
  remark TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_capacity_rule PRIMARY KEY (rule_id),
  CONSTRAINT chk_capacity_positive CHECK (capacity_pcu > 0),
  CONSTRAINT chk_lane_cnt_positive CHECK (lane_cnt > 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_rule_lane_cnt ON dim_capacity_rule(lane_cnt);
CREATE INDEX IF NOT EXISTS idx_rule_vehicle_type ON dim_capacity_rule(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_rule_validity ON dim_capacity_rule(valid_start_date, valid_end_date);

COMMENT ON TABLE dim_capacity_rule IS '车道数-通行当量规则表';
COMMENT ON COLUMN dim_capacity_rule.capacity_pcu IS '日通行当量（PCU），按车道数和车型计算';
COMMENT ON COLUMN dim_capacity_rule.vehicle_type IS '车型分类：passenger_small/medium/large, truck_small/medium/large/oversize, bus, other';
