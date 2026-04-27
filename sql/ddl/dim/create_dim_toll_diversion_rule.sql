-- ============================================================
-- 通行费分流规则维表 DDL
-- ============================================================
-- 功能: 基于里程/费用增幅的分流比例规则
-- 模块: M5
-- 输入表: 手动配置规则
-- 输出表: dim_toll_diversion_rule
-- 粒度: 每条规则一行
-- 关键字段: rule_id

-- TODO: 确认 diversion_ratio 计算方法
-- TODO: 确认 project_scope 处理方式
-- TODO: 添加更多规则维度

CREATE TABLE IF NOT EXISTS dim_toll_diversion_rule (
  -- 主键
  rule_id VARCHAR(64) NOT NULL,

  -- 规则匹配条件
  vehicle_type VARCHAR(32),  -- NULL 表示所有车型

  -- 里程增加范围（km）
  mileage_increase_min DECIMAL(10, 2) DEFAULT 0,
  mileage_increase_max DECIMAL(10, 2) DEFAULT 99999,

  -- 费用增加范围（元）
  fee_increase_min DECIMAL(10, 2) DEFAULT 0,
  fee_increase_max DECIMAL(10, 2) DEFAULT 99999,

  -- 分流比例（0-1）
  diversion_ratio DECIMAL(5, 4) NOT NULL,

  -- 范围
  project_scope VARCHAR(64),  -- 'all' 或特定项目编号

  -- 有效期
  valid_start_date DATE,
  valid_end_date DATE,

  -- 元数据
  remark TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_toll_diversion_rule PRIMARY KEY (rule_id),
  CONSTRAINT chk_diversion_ratio CHECK (diversion_ratio >= 0 AND diversion_ratio <= 1),
  CONSTRAINT chk_mileage_range CHECK (mileage_increase_max >= mileage_increase_min),
  CONSTRAINT chk_fee_range CHECK (fee_increase_max >= fee_increase_min)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_diversion_vehicle ON dim_toll_diversion_rule(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_diversion_mileage ON dim_toll_diversion_rule(mileage_increase_min, mileage_increase_max);
CREATE INDEX IF NOT EXISTS idx_diversion_fee ON dim_toll_diversion_rule(fee_increase_min, fee_increase_max);
CREATE INDEX IF NOT EXISTS idx_diversion_validity ON dim_toll_diversion_rule(valid_start_date, valid_end_date);

COMMENT ON TABLE dim_toll_diversion_rule IS '通行里程/金额增幅与绕行比例规则表';
COMMENT ON COLUMN dim_toll_diversion_rule.diversion_ratio IS '绕行比例，0表示不绕行，1表示全部绕行';
