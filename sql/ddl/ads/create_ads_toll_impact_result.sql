-- ============================================================
-- 通行费影响测算结果表 DDL
-- ============================================================
-- 功能: 通行费影响分析结果
-- 模块: M5
-- 输入表: dws_od_candidate_path, dws_impacted_od_flow_day, dim_toll_diversion_rule
-- 输出表: ads_toll_impact_result
-- 粒度: 方案 × 日期 × OD × 车型
-- 关键字段: scheme_id, stat_date, od_id, vehicle_type

CREATE TABLE IF NOT EXISTS ads_toll_impact_result (
  -- 主键组成部分
  scheme_id VARCHAR(64) NOT NULL,
  stat_date DATE NOT NULL,
  od_id VARCHAR(128) NOT NULL,
  vehicle_type VARCHAR(32) NOT NULL,

  -- 费用影响
  original_fee_amount DECIMAL(14, 2) DEFAULT 0,  -- 原始应收费用
  diverted_fee_amount DECIMAL(14, 2) DEFAULT 0,  -- 分流后费用
  fee_change_amount DECIMAL(14, 2) DEFAULT 0,  -- 费用变化量（正值为增加）

  -- 影响分类
  impact_type VARCHAR(32),  -- 'fee_increase' / 'fee_decrease' / 'no_impact'

  -- 推荐路径
  recommended_path_id VARCHAR(128),

  -- 规则匹配
  matched_rule_id VARCHAR(64),

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_ads_toll_impact_result PRIMARY KEY (
    scheme_id, stat_date, od_id, vehicle_type
  )
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_toll_scheme ON ads_toll_impact_result(scheme_id);
CREATE INDEX IF NOT EXISTS idx_toll_date ON ads_toll_impact_result(stat_date);
CREATE INDEX IF NOT EXISTS idx_toll_od ON ads_toll_impact_result(od_id);
CREATE INDEX IF NOT EXISTS idx_toll_impact_type ON ads_toll_impact_result(impact_type);

COMMENT ON TABLE ads_toll_impact_result IS '通行费影响测算结果表';
COMMENT ON COLUMN ads_toll_impact_result.fee_change_amount IS '金额变化量，正值表示增收，负值表示减收';
COMMENT ON COLUMN ads_toll_impact_result.impact_type IS '影响类型：fee_increase/fee_decrease/no_impact';
