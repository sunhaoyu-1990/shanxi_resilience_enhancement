-- ============================================================
-- M4：构建OD候选替代路径
-- ============================================================
-- 功能: 为受影响OD生成候选替代路径
-- 模块: M4
-- 输入表: dws_impacted_od_flow_day, dwd_od_path_map
-- 输出表: dws_od_candidate_path
-- 粒度: 方案 × OD × 路径
-- 关键字段: scheme_id, od_id, path_id

-- TODO: 实现外部路径API调用
-- TODO: 实现路径-收费单元匹配
-- TODO: 实现分流管控点识别

INSERT INTO dws_od_candidate_path (
  scheme_id,
  od_id,
  path_id,
  original_path_id,
  control_section_id,
  original_mileage,
  candidate_mileage,
  mileage_diff,
  original_fee,
  candidate_fee,
  fee_diff,
  original_jk_fee,
  candidate_jk_fee,
  jk_fee_diff,
  candidate_rank,
  is_affected,
  source_flag,
  created_at,
  updated_at
)
WITH impacted_ods AS (
  -- 获取受影响OD列表
  SELECT DISTINCT
    scheme_id,
    od_id,
    stat_date
  FROM dws_impacted_od_flow_day
  WHERE adjusted_flow_cnt > 0
),
original_paths AS (
  -- 获取每个OD的原路径
  SELECT
    od_id,
    path_id,
    mileage AS original_mileage,
    fee AS original_fee,
    jk_fee AS original_jk_fee,
    path_sections
  FROM dwd_od_path_map
  WHERE source_flag = 'actual'
    OR source_flag = 'rule'
)
SELECT
  io.scheme_id,
  io.od_id,
  -- TODO: 从外部路径API获取或生成替代路径
  op.path_id AS path_id,
  op.path_id AS original_path_id,
  NULL::VARCHAR AS control_section_id,  -- TODO: 计算分叉点
  COALESCE(op.original_mileage, 0) AS original_mileage,
  COALESCE(op.original_mileage, 0) AS candidate_mileage,  -- TODO: 计算替代路径里程
  0 AS mileage_diff,  -- TODO: 计算里程差
  COALESCE(op.original_fee, 0) AS original_fee,
  COALESCE(op.original_fee, 0) AS candidate_fee,  -- TODO: 计算替代路径费用
  0 AS fee_diff,  -- TODO: 计算费用差
  COALESCE(op.original_jk_fee, 0) AS original_jk_fee,
  COALESCE(op.original_jk_fee, 0) AS candidate_jk_fee,  -- TODO: 计算替代路径费用
  0 AS jk_fee_diff,
  1 AS candidate_rank,
  FALSE AS is_affected,  -- TODO: 检查路径是否经过施工区域
  'api' AS source_flag,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM impacted_ods io
JOIN original_paths op ON io.od_id = op.od_id
ON CONFLICT (scheme_id, od_id, path_id)
DO UPDATE SET
  mileage_diff = EXCLUDED.mileage_diff,
  fee_diff = EXCLUDED.fee_diff,
  updated_at = CURRENT_TIMESTAMP
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted/updated % rows into dws_od_candidate_path', v_count;
END $$;
