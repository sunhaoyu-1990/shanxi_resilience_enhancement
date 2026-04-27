-- ============================================================
-- M0：构建OD路径映射表
-- ============================================================
-- 功能: 建立OD与路径的映射关系
-- 模块: M0
-- 输入表: dwd_single_trip_info, 现有OD路径映射
-- 输出表: dwd_od_path_map
-- 粒度: OD × 路径
-- 关键字段: od_id, path_id

-- TODO: 确认 path_sections 格式（JSON数组）
-- TODO: 确认路径识别逻辑

INSERT INTO dwd_od_path_map (
  od_id,
  path_id,
  entry_station_id,
  exit_station_id,
  path_sections,
  section_count,
  mileage,
  fee,
  jk_fee,
  source_flag,
  confidence,
  valid_start_date,
  valid_end_date,
  created_at,
  updated_at
)
WITH od_paths AS (
  -- 从通行数据中识别OD路径组合
  SELECT
    entry_station_id,
    exit_station_id,
    path_id,
    -- 生成 od_id（入口站和出口站的组合）
    CONCAT(entry_station_id, '_', exit_station_id) AS od_id,
    COUNT(*) AS trip_count,
    SUM(mileage) AS total_mileage,
    AVG(fee_amount) AS avg_fee,
    MIN(entry_time) AS first_trip,
    MAX(entry_time) AS last_trip
  FROM dwd_single_trip_info
  WHERE path_id IS NOT NULL
    AND entry_station_id IS NOT NULL
    AND exit_station_id IS NOT NULL
  GROUP BY
    entry_station_id,
    exit_station_id,
    path_id
)
SELECT
  CONCAT(od.entry_station_id, '_', od.exit_station_id) AS od_id,
  od.path_id,
  od.entry_station_id,
  od.exit_station_id,
  -- TODO: 将 path_id 展开为收费单元序列
  NULL::TEXT AS path_sections,  -- TODO: 填充收费单元序列
  0 AS section_count,  -- TODO: 统计收费单元数量
  od.total_mileage AS mileage,
  od.avg_fee AS fee,
  0 AS jk_fee,  -- TODO: 计算监控费
  'actual' AS source_flag,
  1.0 AS confidence,
  od.first_trip::DATE AS valid_start_date,
  od.last_trip::DATE AS valid_end_date,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM od_paths od
WHERE od.trip_count >= 10  -- 仅保留样本量充足的路径
ON CONFLICT (od_id, path_id)
DO UPDATE SET
  mileage = EXCLUDED.mileage,
  fee = EXCLUDED.fee,
  updated_at = CURRENT_TIMESTAMP
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted/updated % rows into dwd_od_path_map', v_count;
END $$;
