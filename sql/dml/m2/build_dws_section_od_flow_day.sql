-- ============================================================
-- M2：构建收费单元OD日流量表
-- ============================================================
-- 功能: 按收费单元-OD粒度汇总历史流量
-- 模块: M2
-- 输入表: dwd_single_trip_info, dwd_od_path_map
-- 输出表: dws_section_od_flow_day
-- 粒度: 收费单元 × OD × 日期 × 车型
-- 关键字段: section_id, od_id, stat_date, vehicle_type

-- TODO: 确认 PCU 换算系数
-- TODO: 添加从 path_sections 展开收费单元的逻辑

INSERT INTO dws_section_od_flow_day (
  section_id,
  od_id,
  stat_date,
  vehicle_type,
  flow_cnt,
  flow_pcu,
  source_flag,
  created_at,
  updated_at
)
WITH daily_trips AS (
  SELECT
    t.entry_time::DATE AS stat_date,
    t.vehicle_type,
    t.entry_station_id,
    t.exit_station_id,
    CONCAT(t.entry_station_id, '_', t.exit_station_id) AS od_id,
    COUNT(*) AS trip_cnt,
    -- PCU换算（TODO: 确认换算系数）
    COUNT(*) * CASE
      WHEN t.vehicle_type IN ('passenger_small', 'passenger_medium') THEN 1.0
      WHEN t.vehicle_type = 'passenger_large' THEN 1.5
      WHEN t.vehicle_type IN ('truck_small', 'truck_medium') THEN 2.0
      WHEN t.vehicle_type IN ('truck_large', 'truck_oversize') THEN 3.0
      WHEN t.vehicle_type = 'bus' THEN 2.5
      ELSE 1.0
    END AS flow_pcu
  FROM dwd_single_trip_info t
  WHERE t.data_status = 'valid'
    AND t.entry_time >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY
    t.entry_time::DATE,
    t.vehicle_type,
    t.entry_station_id,
    t.exit_station_id
)
SELECT
  -- TODO: 根据 od_path_map.path_sections 展开到收费单元级别
  -- 目前使用入口站作为代理
  st.entry_station_id AS section_id,  -- TODO: 映射到实际收费单元
  dt.od_id,
  dt.stat_date,
  dt.vehicle_type,
  dt.trip_cnt AS flow_cnt,
  dt.flow_pcu,
  'actual' AS source_flag,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM daily_trips dt
-- TODO: 与 dwd_od_path_map 关联获取收费单元映射
-- JOIN dwd_od_path_map op ON dt.od_id = op.od_id
ON CONFLICT (section_id, od_id, stat_date, vehicle_type)
DO UPDATE SET
  flow_cnt = EXCLUDED.flow_cnt,
  flow_pcu = EXCLUDED.flow_pcu,
  updated_at = CURRENT_TIMESTAMP
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted/updated % rows into dws_section_od_flow_day', v_count;
END $$;
