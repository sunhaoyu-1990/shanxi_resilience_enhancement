-- ============================================================
-- M0：构建收费单元维表
-- ============================================================
-- 功能: 构建标准化的收费单元维表
-- 模块: M0
-- 输入表: 原始收费单元数据（ods_section_info）
-- 输出表: dim_section_info
-- 粒度: 收费单元 × 有效期
-- 关键字段: section_id, section_number

-- TODO: 替换为实际的 ODS 表名和字段映射
-- TODO: 确认 section_number 分配逻辑

INSERT INTO dim_section_info (
  section_id,
  section_name,
  road_id,
  road_name,
  direction,
  start_station_id,
  end_station_id,
  lane_cnt,
  section_number,
  valid_start_date,
  valid_end_date,
  created_at,
  updated_at
)
SELECT
  section_id,
  section_name,
  road_id,
  road_name,
  direction,
  start_station_id,
  end_station_id,
  lane_cnt,
  -- TODO: 根据路径分组逻辑分配 section_number
  COALESCE(section_number, section_id) AS section_number,
  valid_start_date,
  valid_end_date,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM ods_section_info
WHERE 1=1
  -- TODO: 添加数据质量过滤条件
;

-- 日志汇总
DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted % rows into dim_section_info', v_count;
END $$;
