-- ============================================================
-- M0：构建施工方案收费单元映射表
-- ============================================================
-- 功能: 建立施工方案与受影响收费单元的映射关系
-- 模块: M0
-- 输入表: dim_scheme_info, dim_section_info, 原始方案数据
-- 输出表: dwd_scheme_section_map
-- 粒度: 方案 × 收费单元 × 有效期
-- 关键字段: scheme_id, section_id, valid_start_date

-- TODO: 确认 construction_mode 枚举值
-- TODO: 确认 impact_level 计算方式

INSERT INTO dwd_scheme_section_map (
  scheme_id,
  section_id,
  lane_occupied_cnt,
  construction_mode,
  speed_limit,
  distance_limit,
  valid_start_date,
  valid_end_date,
  impact_level,
  created_at,
  updated_at
)
SELECT
  s.scheme_id,
  m.section_id,
  COALESCE(m.lane_occupied_cnt, 1) AS lane_occupied_cnt,
  COALESCE(m.construction_mode, 'single_lane') AS construction_mode,
  m.speed_limit,
  m.distance_limit,
  s.start_date AS valid_start_date,
  s.end_date AS valid_end_date,
  CASE
    WHEN COALESCE(m.lane_occupied_cnt, 0) >= 2 THEN 'high'
    WHEN COALESCE(m.lane_occupied_cnt, 0) = 1 THEN 'medium'
    ELSE 'low'
  END AS impact_level,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM dim_scheme_info s
-- TODO: 与原始方案-收费单元映射数据关联
-- JOIN ods_scheme_section_mapping m ON s.scheme_id = m.scheme_id
LEFT JOIN dim_section_info sec ON sec.section_id = m.section_id
WHERE 1=1
  AND s.scheme_status IN ('approved', 'in_progress')
  -- TODO: 如有需要添加方案过滤条件
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted % rows into dwd_scheme_section_map', v_count;
END $$;
