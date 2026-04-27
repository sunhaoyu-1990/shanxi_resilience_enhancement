-- ============================================================
-- OD分流方案表 DDL
-- ============================================================
-- 功能: 受影响OD的分流推荐方案
-- 模块: M4
-- 输入表: dws_od_candidate_path
-- 输出表: ads_od_diversion_plan
-- 粒度: 方案 × OD × 推荐路径
-- 关键字段: scheme_id, od_id, path_id

CREATE TABLE IF NOT EXISTS ads_od_diversion_plan (
  -- 主键组成部分
  scheme_id VARCHAR(64) NOT NULL,
  od_id VARCHAR(128) NOT NULL,
  path_id VARCHAR(128) NOT NULL,

  -- 分流详情
  control_section_id VARCHAR(64),
  diversion_reason VARCHAR(256),
  recommendation_level VARCHAR(32),  -- 'recommended' / 'alternative' / 'fallback'

  -- 路径对比
  mileage_diff DECIMAL(10, 2),
  fee_diff DECIMAL(10, 2),
  jk_fee_diff DECIMAL(10, 2),

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_ads_od_diversion_plan PRIMARY KEY (
    scheme_id, od_id, path_id
  )
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_div_plan_scheme ON ads_od_diversion_plan(scheme_id);
CREATE INDEX IF NOT EXISTS idx_div_plan_od ON ads_od_diversion_plan(od_id);
CREATE INDEX IF NOT EXISTS idx_div_plan_level ON ads_od_diversion_plan(recommendation_level);

COMMENT ON TABLE ads_od_diversion_plan IS 'OD分流方案结果表';
COMMENT ON COLUMN ads_od_diversion_plan.recommendation_level IS '推荐等级：recommended(推荐)/alternative(备选)/fallback(兜底)';
