-- ============================================================
-- M5：构建通行费影响测算结果
-- ============================================================
-- 功能: 基于分流规则计算通行费影响
-- 模块: M5
-- 输入表: dws_od_candidate_path, dws_impacted_od_flow_day, dim_toll_diversion_rule
-- 输出表: ads_toll_impact_result
-- 粒度: 方案 × 日期 × OD × 车型
-- 关键字段: scheme_id, stat_date, od_id, vehicle_type

-- TODO: 确认 diversion_ratio 匹配逻辑
-- TODO: 添加最优路径选择逻辑

INSERT INTO ads_toll_impact_result (
  scheme_id,
  stat_date,
  od_id,
  vehicle_type,
  original_fee_amount,
  diverted_fee_amount,
  fee_change_amount,
  impact_type,
  recommended_path_id,
  matched_rule_id,
  created_at,
  updated_at
)
WITH candidate_flows AS (
  -- 关联候选路径与受影响流量
  SELECT
    cp.scheme_id,
    iof.stat_date,
    cp.od_id,
    iof.vehicle_type,
    cp.path_id,
    cp.original_mileage,
    cp.candidate_mileage,
    cp.mileage_diff,
    cp.original_fee,
    cp.candidate_fee,
    cp.fee_diff,
    cp.candidate_rank,
    iof.adjusted_flow_cnt,
    iof.impacted_flow_cnt,
    iof.impacted_flow_pcu
  FROM dws_od_candidate_path cp
  JOIN dws_impacted_od_flow_day iof
    ON cp.scheme_id = iof.scheme_id
    AND cp.od_id = iof.od_id
  WHERE cp.candidate_rank = 1  -- 最优候选路径
),
matched_rules AS (
  -- 匹配分流规则
  SELECT
    cf.scheme_id,
    cf.stat_date,
    cf.od_id,
    cf.vehicle_type,
    cf.path_id,
    cf.mileage_diff,
    cf.fee_diff,
    cf.adjusted_flow_cnt,
    r.rule_id,
    r.diversion_ratio,
    -- 计算分流流量
    cf.adjusted_flow_cnt * r.diversion_ratio AS diverted_flow_cnt,
    -- 计算费用影响
    cf.adjusted_flow_cnt * r.diversion_ratio * cf.fee_diff AS fee_impact
  FROM candidate_flows cf
  LEFT JOIN dim_toll_diversion_rule r
    ON (r.vehicle_type = cf.vehicle_type OR r.vehicle_type IS NULL)
    AND r.mileage_increase_min <= cf.mileage_diff
    AND r.mileage_increase_max > cf.mileage_diff
    AND r.fee_increase_min <= cf.fee_diff
    AND r.fee_increase_max > cf.fee_diff
    AND (r.valid_start_date IS NULL OR r.valid_start_date <= cf.stat_date)
    AND (r.valid_end_date IS NULL OR r.valid_end_date >= cf.stat_date)
  WHERE cf.fee_diff != 0  -- 仅处理有费用变化的路径
)
SELECT
  mr.scheme_id,
  mr.stat_date,
  mr.od_id,
  mr.vehicle_type,
  -- 原始费用
  mr.adjusted_flow_cnt * mr.fee_diff + mr.adjusted_flow_cnt * COALESCE(mr.original_fee, 0)
    AS original_fee_amount,  -- TODO: 正确计算
  -- 分流后费用（按规则匹配的分流比例）
  mr.adjusted_flow_cnt * COALESCE(mr.candidate_fee, 0) AS diverted_fee_amount,
  -- 费用变化
  mr.fee_impact AS fee_change_amount,
  -- 影响类型
  CASE
    WHEN mr.fee_diff > 0 THEN 'fee_increase'
    WHEN mr.fee_diff < 0 THEN 'fee_decrease'
    ELSE 'no_impact'
  END AS impact_type,
  mr.path_id AS recommended_path_id,
  mr.rule_id,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM matched_rules mr
ON CONFLICT (scheme_id, stat_date, od_id, vehicle_type)
DO UPDATE SET
  fee_change_amount = EXCLUDED.fee_change_amount,
  impact_type = EXCLUDED.impact_type,
  recommended_path_id = EXCLUDED.recommended_path_id,
  updated_at = CURRENT_TIMESTAMP
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted/updated % rows into ads_toll_impact_result', v_count;
END $$;
