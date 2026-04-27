-- ============================================================
-- M5：构建施工方案汇总
-- ============================================================
-- 功能: 汇总各施工方案级别统计指标
-- 模块: M5
-- 输入表: ads_toll_impact_result, dwd_scheme_section_map
-- 输出表: ads_scheme_summary
-- 粒度: 每个方案一行
-- 关键字段: scheme_id

INSERT INTO ads_scheme_summary (
  scheme_id,
  scheme_name,
  start_date,
  end_date,
  impacted_section_cnt,
  impacted_od_cnt,
  total_fee_increase,
  total_fee_decrease,
  net_fee_impact,
  recommended_plan_cnt,
  created_at,
  updated_at
)
WITH impact_summary AS (
  SELECT
    scheme_id,
    SUM(CASE WHEN impact_type = 'fee_increase' THEN fee_change_amount ELSE 0 END) AS total_increase,
    SUM(CASE WHEN impact_type = 'fee_decrease' THEN ABS(fee_change_amount) ELSE 0 END) AS total_decrease,
    COUNT(DISTINCT od_id) AS od_cnt
  FROM ads_toll_impact_result
  GROUP BY scheme_id
),
section_count AS (
  SELECT
    scheme_id,
    COUNT(DISTINCT section_id) AS section_cnt
  FROM dwd_scheme_section_map
  GROUP BY scheme_id
)
SELECT
  s.scheme_id,
  s.scheme_name,
  s.start_date,
  s.end_date,
  COALESCE(sc.section_cnt, 0) AS impacted_section_cnt,
  COALESCE(ix.od_cnt, 0) AS impacted_od_cnt,
  COALESCE(ix.total_increase, 0) AS total_fee_increase,
  COALESCE(ix.total_decrease, 0) AS total_fee_decrease,
  COALESCE(ix.total_increase, 0) - COALESCE(ix.total_decrease, 0) AS net_fee_impact,
  (SELECT COUNT(*) FROM dws_od_candidate_path WHERE scheme_id = s.scheme_id AND candidate_rank = 1) AS recommended_plan_cnt,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM dim_scheme_info s
LEFT JOIN section_count sc ON s.scheme_id = sc.scheme_id
LEFT JOIN impact_summary ix ON s.scheme_id = ix.scheme_id
WHERE s.scheme_status IN ('approved', 'in_progress')
ON CONFLICT (scheme_id)
DO UPDATE SET
  impacted_section_cnt = EXCLUDED.impacted_section_cnt,
  impacted_od_cnt = EXCLUDED.impacted_od_cnt,
  total_fee_increase = EXCLUDED.total_fee_increase,
  total_fee_decrease = EXCLUDED.total_fee_decrease,
  net_fee_impact = EXCLUDED.net_fee_impact,
  recommended_plan_cnt = EXCLUDED.recommended_plan_cnt,
  updated_at = CURRENT_TIMESTAMP
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted/updated % rows into ads_scheme_summary', v_count;
END $$;
