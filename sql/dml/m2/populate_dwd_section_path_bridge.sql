-- ============================================================
-- M2: 填充收费单元-OD路径桥接表
-- ============================================================
-- 作用: 从 dwd_od_section_path_map 的 fixed_intervalpath 展开填充桥接表
-- 输入表: dwd_od_section_path_map
-- 输出表: dwd_section_path_bridge
-- 粒度: section_id × od_section_path_id × version_yyyyMM
-- 关键字段: section_id, od_section_path_id, version_yyyyMM
-- ============================================================

INSERT INTO dwd_section_path_bridge (section_id, od_section_path_id, version_yyyyMM)
SELECT
    sec AS section_id,
    m.id AS od_section_path_id,
    m.version_yyyyMM
FROM dwd_od_section_path_map m
CROSS JOIN LATERAL unnest(string_to_array(m.fixed_intervalpath, '|')) AS sec
WHERE m.fixed_intervalpath IS NOT NULL
  AND m.fixed_intervalpath != ''
ON CONFLICT (section_id, od_section_path_id, version_yyyyMM)
DO NOTHING;
