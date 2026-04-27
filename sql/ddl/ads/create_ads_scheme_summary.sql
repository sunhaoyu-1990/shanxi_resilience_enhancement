-- ============================================================
-- 施工方案汇总结果表 DDL
-- ============================================================
-- 功能: 每个施工方案的汇总统计
-- 模块: M5
-- 输入表: ads_toll_impact_result
-- 输出表: ads_scheme_summary
-- 粒度: 每个方案一行
-- 关键字段: scheme_id

CREATE TABLE IF NOT EXISTS ads_scheme_summary (
  -- 主键
  scheme_id VARCHAR(64) NOT NULL,

  -- 方案信息
  scheme_name VARCHAR(256),
  start_date DATE,
  end_date DATE,

  -- 影响统计
  impacted_section_cnt INTEGER DEFAULT 0,
  impacted_od_cnt INTEGER DEFAULT 0,

  -- 费用影响
  total_fee_increase DECIMAL(16, 2) DEFAULT 0,
  total_fee_decrease DECIMAL(16, 2) DEFAULT 0,
  net_fee_impact DECIMAL(16, 2) DEFAULT 0,

  -- 推荐方案统计
  recommended_plan_cnt INTEGER DEFAULT 0,

  -- 车型分类（未来扩展）
  fee_increase_by_passenger DECIMAL(16, 2),
  fee_increase_by_truck DECIMAL(16, 2),

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_ads_scheme_summary PRIMARY KEY (scheme_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_scheme_sum_dates ON ads_scheme_summary(start_date, end_date);

COMMENT ON TABLE ads_scheme_summary IS '施工方案汇总结果表';
COMMENT ON COLUMN ads_scheme_summary.net_fee_impact IS '净影响金额 = total_fee_increase - total_fee_decrease';
