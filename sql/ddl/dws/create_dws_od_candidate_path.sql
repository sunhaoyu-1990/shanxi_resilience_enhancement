-- ============================================================
-- OD候选替代路径表 DDL
-- ============================================================
-- 功能: 受影响OD的候选替代路径
-- 模块: M4
-- 输入表: dws_impacted_od_flow_day, dwd_od_path_map
-- 输出表: dws_od_candidate_path
-- 粒度: 方案 × OD × 路径
-- 关键字段: scheme_id, od_id, path_id

-- TODO: 确认 mileage_diff/fee_diff 计算方式

CREATE TABLE IF NOT EXISTS dws_od_candidate_path (
  -- 主键组成部分
  scheme_id VARCHAR(64) NOT NULL,
  od_id VARCHAR(128) NOT NULL,
  path_id VARCHAR(128) NOT NULL,

  -- 原路径参考
  original_path_id VARCHAR(128),

  -- 分流管控点
  control_section_id VARCHAR(64),  -- 第一个分叉点

  -- 里程对比
  original_mileage DECIMAL(10, 2),
  candidate_mileage DECIMAL(10, 2),
  mileage_diff DECIMAL(10, 2),

  -- 费用对比
  original_fee DECIMAL(10, 2),
  candidate_fee DECIMAL(10, 2),
  fee_diff DECIMAL(10, 2),

  -- 监控费对比
  original_jk_fee DECIMAL(10, 2),
  candidate_jk_fee DECIMAL(10, 2),
  jk_fee_diff DECIMAL(10, 2),

  -- 路径排序
  candidate_rank INTEGER,

  -- 影响评估
  is_affected BOOLEAN DEFAULT FALSE,  -- 该路径是否经过施工区域

  -- 数据质量
  source_flag VARCHAR(32) DEFAULT 'api',  -- 'actual' / 'filled' / 'rule' / 'api'

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dws_od_candidate_path PRIMARY KEY (
    scheme_id, od_id, path_id
  )
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_cand_scheme ON dws_od_candidate_path(scheme_id);
CREATE INDEX IF NOT EXISTS idx_cand_od ON dws_od_candidate_path(od_id);
CREATE INDEX IF NOT EXISTS idx_cand_rank ON dws_od_candidate_path(candidate_rank);
CREATE INDEX IF NOT EXISTS idx_cand_affected ON dws_od_candidate_path(is_affected);

COMMENT ON TABLE dws_od_candidate_path IS 'OD候选替代路径表';
COMMENT ON COLUMN dws_od_candidate_path.control_section_id IS '分流管控点，原路径与替代路径的第一个分叉点';
