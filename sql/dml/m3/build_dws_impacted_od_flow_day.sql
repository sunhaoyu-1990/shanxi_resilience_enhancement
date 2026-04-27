-- ============================================================
-- M3：构建受影响OD流量表
-- ============================================================
-- 功能: 通过供需对比计算受影响流量
-- 模块: M3
-- 输入表: dws_section_capacity_day, dws_section_od_flow_day
-- 输出表: dws_impacted_od_flow_day
-- 粒度: 方案 × 日期 × OD × 车型
-- 关键字段: scheme_id, stat_date, od_id, vehicle_type

-- TODO: 确认 impact_ratio 计算公式
-- TODO: 添加收费单元级别分配逻辑

INSERT INTO dws_impacted_od_flow_day (
  scheme_id,
  stat_date,
  od_id,
  vehicle_type,
  impacted_flow_cnt,
  impacted_flow_pcu,
  impact_ratio,
  adjusted_flow_cnt,
  original_flow_cnt,
  original_flow_pcu,
  capacity_pcu,
  source_flag,
  created_at,
  updated_at
)
WITH supply_demand AS (
  -- 关联通行能力与流量数据
  SELECT
    c.scheme_id,
    c.stat_date,
    f.section_id,
    f.od_id,
    f.vehicle_type,
    COALESCE(f.flow_cnt, 0) AS original_flow_cnt,
    COALESCE(f.flow_pcu, 0) AS original_flow_pcu,
    COALESCE(c.capacity_pcu, 0) AS capacity_pcu
  FROM dws_section_capacity_day c
  -- TODO: 按收费单元关联以提高精度
  LEFT JOIN dws_section_od_flow_day f
    ON c.stat_date = f.stat_date
    AND c.vehicle_type = f.vehicle_type
  WHERE c.scheme_id IS NOT NULL
)
, impact_calc AS (
  -- 计算影响比例
  SELECT
    scheme_id,
    stat_date,
    od_id,
    vehicle_type,
    original_flow_cnt,
    original_flow_pcu,
    capacity_pcu,
    -- 如果通行能力 >= 需求量，则无影响
    -- 如果通行能力 < 需求量，则计算影响比例
    CASE
      WHEN capacity_pcu >= original_flow_pcu THEN 0
      ELSE LEAST(1.0, (original_flow_pcu - capacity_pcu) / original_flow_pcu)
    END AS impact_ratio
  FROM supply_demand
)
SELECT
  ic.scheme_id,
  ic.stat_date,
  ic.od_id,
  ic.vehicle_type,
  -- 受影响流量 = 原始流量 × 影响比例
  (ic.original_flow_cnt * ic.impact_ratio)::INTEGER AS impacted_flow_cnt,
  ic.original_flow_pcu * ic.impact_ratio AS impacted_flow_pcu,
  ic.impact_ratio,
  -- 调整流量 = 受影响流量（用于分配到替代路径）
  (ic.original_flow_cnt * ic.impact_ratio)::INTEGER AS adjusted_flow_cnt,
  ic.original_flow_cnt AS original_flow_cnt,
  ic.original_flow_pcu AS original_flow_pcu,
  ic.capacity_pcu,
  'rule' AS source_flag,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM impact_calc ic
WHERE ic.impact_ratio > 0  -- 仅保留受影响记录
ON CONFLICT (scheme_id, stat_date, od_id, vehicle_type)
DO UPDATE SET
  impacted_flow_cnt = EXCLUDED.impacted_flow_cnt,
  impacted_flow_pcu = EXCLUDED.impacted_flow_pcu,
  impact_ratio = EXCLUDED.impact_ratio,
  adjusted_flow_cnt = EXCLUDED.adjusted_flow_cnt,
  updated_at = CURRENT_TIMESTAMP
;

DO $$
DECLARE
  v_count INTEGER;
BEGIN
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RAISE NOTICE 'Inserted/updated % rows into dws_impacted_od_flow_day', v_count;
END $$;
