-- ============================================================
-- M2：构建收费单元日流量表（汇总）
-- ============================================================
-- 功能: 汇总收费单元级别日流量
-- 模块: M2
-- 输入表: dws_section_od_flow_day
-- 输出表: dws_section_flow_day
-- 粒度: 收费单元 × 日期 × 车型
-- 关键字段: section_id, stat_date, vehicle_type

INSERT INTO dws_section_flow_day (
  section_id,
  stat_date,
  vehicle_type,
  flow_cnt,
  flow_pcu,
  created_at,
  updated_at
)
SELECT
  section_id,
  stat_date,
  vehicle_type,
  SUM(flow_cnt) AS flow_cnt,
  SUM(flow_pcu) AS flow_pcu,
  CURRENT_TIMESTAMP AS created_at,
  CURRENT_TIMESTAMP AS updated_at
FROM dws_section_od_flow_day
GROUP BY
  section_id,
  stat_date,
  vehicle_type
ON CONFLICT (section_id, stat_date, vehicle_type)
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
  RAISE NOTICE 'Inserted/updated % rows into dws_section_flow_day', v_count;
END $$;
