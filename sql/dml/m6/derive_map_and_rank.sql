-- ============================================================
-- M6: 从 freq 表派生 map 表，并计算 rank
-- ============================================================
-- 作用:
--   1. 更新 freq 表的 ig_rank（从 ig_count 降序）
--   2. 从 freq 表派生 map 表（best_fixed_ig = ig_count 最大的）
-- 输入: dwd_od_section_path_numpath_freq
-- 输出: dwd_od_section_path_map（覆盖）, ig_rank（更新）
-- 口径: ig_rank 在同 (enid, exid, numpath, version_yyyyMM, topo_version) 下按 ig_count 降序
-- ============================================================

-- Step 1: 计算 ig_rank
UPDATE dwd_od_section_path_numpath_freq AS t
SET    ig_rank     = ranked.r_rank,
       updated_at  = CURRENT_TIMESTAMP
FROM   (
    SELECT id,
           RANK() OVER (
               PARTITION BY enid, exid, numpath, version_yyyyMM, topo_version
               ORDER BY ig_count DESC
           ) AS r_rank
    FROM dwd_od_section_path_numpath_freq
) AS ranked
WHERE  t.id = ranked.id
  AND  t.ig_rank IS DISTINCT FROM ranked.r_rank;

-- Step 2: 从 freq 表派生 map 表
-- 先计算每个 (enid, exid, numpath, version, topo) 的 total_trip_cnt
WITH total_cnt AS (
    SELECT
        enid, exid, numpath, version_yyyyMM, topo_version,
        SUM(ig_count) AS total_trip_cnt
    FROM dwd_od_section_path_numpath_freq
    GROUP BY enid, exid, numpath, version_yyyyMM, topo_version
),
-- 取 ig_count 最大的 fixed_intervalgroup（rank=1）
best_ig AS (
    SELECT
        f.enid, f.exid, f.numpath,
        f.version_yyyyMM, f.topo_version,
        f.fixed_intervalgroup,
        f.ig_count,
        t.total_trip_cnt
    FROM dwd_od_section_path_numpath_freq f
    JOIN total_cnt t USING (enid, exid, numpath, version_yyyyMM, topo_version)
    WHERE f.ig_rank = 1
)
INSERT INTO dwd_od_section_path_map (
    enid, exid, numpath, version_yyyyMM,
    fixed_intervalpath, intervalpath_cnt,
    total_trip_cnt, path_freq_ratio,
    topo_version, source_flag
)
SELECT
    enid, exid, numpath, version_yyyyMM,
    fixed_intervalgroup,
    ig_count,
    total_trip_cnt,
    ROUND(ig_count::NUMERIC / NULLIF(total_trip_cnt, 0), 4),
    topo_version,
    'hive_computed'
FROM best_ig
ON CONFLICT (enid, exid, numpath, version_yyyyMM)
DO UPDATE SET
    fixed_intervalpath = EXCLUDED.fixed_intervalpath,
    intervalpath_cnt   = EXCLUDED.intervalpath_cnt,
    total_trip_cnt    = EXCLUDED.total_trip_cnt,
    path_freq_ratio    = EXCLUDED.path_freq_ratio,
    topo_version       = EXCLUDED.topo_version,
    updated_at         = CURRENT_TIMESTAMP;
