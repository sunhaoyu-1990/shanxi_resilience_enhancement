-- ============================================================
-- M0：校验收费单元维表
-- ============================================================
-- 功能: 校验 dim_section_info 数据质量
-- 模块: M0
-- 输入表: dim_section_info
-- 输出: 校验报告

-- 校验1：必填字段非空
SELECT
  'section_id_null' AS check_name,
  COUNT(*) AS error_count
FROM dim_section_info
WHERE section_id IS NULL
UNION ALL
SELECT
  'section_number_null' AS check_name,
  COUNT(*) AS error_count
FROM dim_section_info
WHERE section_number IS NULL;

-- 校验2：有效期内的 section_id 无重复
SELECT
  'duplicate_section_id' AS check_name,
  COUNT(*) AS error_count
FROM (
  SELECT
    section_id,
    valid_start_date,
    COUNT(*) AS cnt
  FROM dim_section_info
  GROUP BY section_id, valid_start_date
  HAVING COUNT(*) > 1
) duplicates;

-- 校验3：有效期范围合法
SELECT
  'invalid_date_range' AS check_name,
  COUNT(*) AS error_count
FROM dim_section_info
WHERE valid_end_date IS NOT NULL
  AND valid_end_date < valid_start_date;

-- 校验4：车道数有效性
SELECT
  'invalid_lane_cnt' AS check_name,
  COUNT(*) AS error_count
FROM dim_section_info
WHERE lane_cnt < 0;

-- 校验5：收费单元编号一致性
SELECT
  'inconsistent_section_number' AS check_name,
  COUNT(DISTINCT section_id) AS error_count
FROM dim_section_info
WHERE section_id IN (
  SELECT section_id
  FROM dim_section_info
  GROUP BY section_id
  HAVING COUNT(DISTINCT section_number) > 1
);

-- 汇总
DO $$
DECLARE
  v_total INTEGER;
BEGIN
  SELECT COALESCE(SUM(error_count), 0)
  INTO v_total
  FROM (
    -- 此处添加各项校验子查询
    SELECT COUNT(*) AS error_count FROM dim_section_info WHERE section_id IS NULL
    UNION ALL
    SELECT COUNT(*) FROM dim_section_info WHERE section_number IS NULL
    UNION ALL
    SELECT COUNT(*) FROM dim_section_info WHERE lane_cnt < 0
  ) checks;

  RAISE NOTICE 'Total validation errors in dim_section_info: %', v_total;
END $$;
