-- ============================================================
-- M1：校验收费单元日通行能力表
-- ============================================================
-- 功能: 校验 dws_section_capacity_day 数据质量
-- 模块: M1

-- 校验1：无负通行能力值
SELECT
  'negative_capacity' AS check_name,
  COUNT(*) AS error_count
FROM dws_section_capacity_day
WHERE capacity_pcu < 0;

-- 校验2：主键唯一性
SELECT
  'duplicate_pk' AS check_name,
  COUNT(*) - COUNT(DISTINCT CONCAT(section_id, stat_date, vehicle_type)) AS error_count
FROM dws_section_capacity_day;

-- 校验3：可用车道数一致性
SELECT
  'lane_cnt_mismatch' AS check_name,
  COUNT(*) AS error_count
FROM dws_section_capacity_day c
JOIN dim_section_info s ON c.section_id = s.section_id
WHERE c.available_lane_cnt > s.lane_cnt;

-- 校验4：通行能力缩放校验
SELECT
  'capacity_zero_for_occupied' AS check_name,
  COUNT(*) AS error_count
FROM dws_section_capacity_day
WHERE available_lane_cnt = 0
  AND capacity_pcu > 0;

-- 汇总
DO $$
DECLARE
  v_total INTEGER;
BEGIN
  RAISE NOTICE 'M1 validation checks completed for dws_section_capacity_day';
END $$;
