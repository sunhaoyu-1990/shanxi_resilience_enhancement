-- ============================================================
-- M5: Create Dimension Table - Detour Ratio Rule
-- ============================================================
-- 作用: 存储绕行通行费增幅区间与绕行比例的对应规则
-- 输入表: 手动配置规则
-- 输出表: dim_detour_ratio_rule
-- 粒度: 每条规则一行（按通行费增幅区间划分）
-- 关键字段: id, detour_toll_increase_min, detour_toll_increase_max, detour_ratio
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_detour_ratio_rule (
  -- 主键
  id                       VARCHAR(20)  NOT NULL,

  -- 绕行通行费增幅区间（左闭右开）
  detour_toll_increase_min FLOAT8       NOT NULL,
  detour_toll_increase_max FLOAT8       NOT NULL,

  -- 绕行比例
  detour_ratio             FLOAT8       NOT NULL,

  -- 元数据
  remark      TEXT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_detour_ratio_rule PRIMARY KEY (id),
  CONSTRAINT chk_detour_increase_range CHECK (detour_toll_increase_min < detour_toll_increase_max),
  CONSTRAINT chk_detour_increase_min   CHECK (detour_toll_increase_min >= 0),
  CONSTRAINT chk_detour_ratio_range    CHECK (detour_ratio >= 0 AND detour_ratio <= 1)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_detour_ratio_min ON dim_detour_ratio_rule(detour_toll_increase_min);
CREATE INDEX IF NOT EXISTS idx_detour_ratio_max ON dim_detour_ratio_rule(detour_toll_increase_max);

-- 表与字段注释
COMMENT ON TABLE dim_detour_ratio_rule IS '绕行通行费增幅区间与绕行比例对应规则表';
COMMENT ON COLUMN dim_detour_ratio_rule.id                       IS '规则 ID';
COMMENT ON COLUMN dim_detour_ratio_rule.detour_toll_increase_min IS '绕行通行费增幅下限（含），取值 [0, 1]';
COMMENT ON COLUMN dim_detour_ratio_rule.detour_toll_increase_max IS '绕行通行费增幅上限（不含），取值 (0, 1]';
COMMENT ON COLUMN dim_detour_ratio_rule.detour_ratio             IS '对应绕行比例，取值 [0, 1]';
