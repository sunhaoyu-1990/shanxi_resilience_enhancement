-- ============================================================
-- M1：构建收费单元日通行能力
-- ============================================================
-- 功能: 计算施工期间收费单元日通行能力
-- 模块: M1
-- 输入表: dim_section_info, dwd_scheme_section_map, dim_capacity_rule
-- 输出表: dws_section_capacity_day
-- 粒度: 收费单元 × 日期 × 车型
-- 关键字段: section_id, stat_date, vehicle_type

-- TODO: 确认 available_lane_cnt = lane_cnt - lane_occupied_cnt 逻辑
-- TODO: 如有需要添加更多车型

INSERT INTO dws_section_capacity_day (
  section_id,
  stat_date,
  vehicle_type,
  capacity_pcu,
  scheme_id,
  rule_id,
  total_lane_cnt,
  available_lane_cnt,
  created_at,
  updated_at
)
WITH construction_days AS (
  -- 将方案有效期展开为单日
  SELECT
    m.scheme_id,
    m.section_id,
    d.day_date AS stat_date,
    sec.lane_cnt AS total_lane_cnt,
    m.lane_occupied_cnt,
    sec.lane_cnt - m.lane_occupied_cnt AS available_lane_cnt
  FROM dwd_scheme_section_map m
  JOIN dim_section_info sec ON m.section_id = sec.section_id
  -- 展开日期范围（使用 generate_series 或递归 CTE）
  JOIN LATERAL (
    SELECT generate_series(
      m.valid_start_date,
      COALESCE(m.valid_end_date, CURRENT_DATE),
      '1 day'::INTERVAL
    )::DATE AS day_date
  ) d ON TRUE
  WHERE m.lane_occupied_cnt < sec.lane_cnt  -- 暂时排除完全封闭情况
),
capacity_rules AS (
  -- 获取通行能力规则
  SELECT
    lane_cnt,
    vehicle_type,
    rule_id,
    capacity_pcu
  FROM dim_capacity_rule
  WHERE valid_start_date <= CURRENT_DATE
    AND (valid_end_date IS NULL OR valid_end_date >= CURRENT_DATE)
)
SELECT
  cd.section_id,
  cd.stat_date,
  r.vehicle_type,
  -- 根据可用车道数等比缩放通行能力
  r.capacity_pcu * cd.available_lane_cnt / NULLIF(cd.total_lane_cnt, 0) AS capacity_pcu,
  cd.scheme_id,
  r.rule_id,
  cd.total_lane_cnt,
  cd.available_lane_cnt,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM construction_days cd
JOIN capacity_rules r ON r.lane_cnt = cd.available_lane_cnt
ON CONFLICT (section_id, stat_date, vehicle_type)
DO UPDATE SET
  capacity_pcu = EXCLUDED.capacity_pcu,
  scheme_id = EXCLUDED.scheme_id,
  updated_at = CURRENT_TIMESTAMP
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted/updated % rows into dws_section_capacity_day', v_count;
END $$;
