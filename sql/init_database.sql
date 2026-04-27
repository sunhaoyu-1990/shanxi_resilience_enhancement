-- ============================================================
-- 数据库初始化脚本
-- 陕交控多路段改扩建韧性提升项目（一期）
-- ============================================================
-- 作用: 初始化数据库 schema 和基础表
-- 执行顺序: 1. 创建 schema 2. 创建 Dim 层表 3. 创建 DWD 层表 4. 插入版本配置数据
-- ============================================================

\echo '========================================'
\echo '开始初始化数据库...'
\echo '========================================'

-- ------------------------------------------------------------
-- Step 1: 创建 Schema（如果不存在）
-- ------------------------------------------------------------
\echo '[1/5] 创建 Schema...'
CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public, public;

\echo 'Schema 初始化完成'

-- ------------------------------------------------------------
-- Step 2: 创建 Dim 层表
-- ------------------------------------------------------------
\echo '[2/5] 创建 Dim 层表...'

-- 收费单元路径版本配置表
\ir dim/create_dim_section_path_version.sql

-- 其他 Dim 层表（按需要启用）
-- \ir dim/create_dim_section_info.sql
-- \ir dim/create_dim_station_info.sql
-- \ir dim/create_dim_road_topology.sql
-- \ir dim/create_dim_scheme_info.sql
-- \ir dim/create_dim_capacity_rule.sql
-- \ir dim/create_dim_toll_diversion_rule.sql

\echo 'Dim 层表创建完成'

-- ------------------------------------------------------------
-- Step 3: 创建 DWD 层表
-- ------------------------------------------------------------
\echo '[3/5] 创建 DWD 层表...'

-- 收费单元唯一路径明细表
\ir dwd/create_dwd_section_path.sql

-- 其他 DWD 层表（按需要启用）
-- \ir dwd/create_dwd_single_trip_info.sql
-- \ir dwd/create_dwd_scheme_section_map.sql
-- \ir dwd/create_dwd_od_path_map.sql

\echo 'DWD 层表创建完成'

-- ------------------------------------------------------------
-- Step 4: 创建 DWS 层表（可选）
-- ------------------------------------------------------------
\echo '[4/5] 创建 DWS 层表（跳过，按需执行）...'
-- \ir dws/create_dws_section_capacity_day.sql
-- \ir dws/create_dws_section_flow_day.sql
-- \ir dws/create_dws_section_od_flow_day.sql
-- \ir dws/create_dws_impacted_od_flow_day.sql
-- \ir dws/create_dws_od_candidate_path.sql

-- ------------------------------------------------------------
-- Step 5: 创建 ADS 层表（可选）
-- ------------------------------------------------------------
\echo '[5/5] 创建 ADS 层表（跳过，按需执行）...'
-- \ir ads/create_ads_od_diversion_plan.sql
-- \ir ads/create_ads_toll_impact_result.sql
-- \ir ads/create_ads_scheme_summary.sql

-- ------------------------------------------------------------
-- 插入版本配置数据
-- ------------------------------------------------------------
\echo '插入版本配置数据...'

INSERT INTO dim_section_path_version
    (version_yyyyMM, effect_date, file_path, description)
VALUES
    ('202401', '2024-01-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202401单元唯一路径.xlsx', '2024年1月起生效'),
    ('202409', '2024-09-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202409单元唯一路径.xlsx', '2024年9月起生效'),
    ('202412', '2024-12-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202412单元唯一路径.xlsx', '2024年12月起生效'),
    ('202507', '2025-07-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202507单元唯一路径.xlsx', '2025年7月起生效'),
    ('202512', '2025-12-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202512单元唯一路径.xlsx', '2025年12月起生效'),
    ('202603', '2026-03-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202603单元唯一路径.xlsx', '2026年3月起生效')
ON CONFLICT (version_yyyyMM) DO NOTHING;

\echo '版本配置数据插入完成'

-- ------------------------------------------------------------
-- 验证
-- ------------------------------------------------------------
\echo '========================================'
\echo '数据库初始化完成！'
\echo '========================================'

-- 显示已创建的表
\echo '已创建的表：'
\dt public.

-- 显示版本配置
\echo '版本配置：'
SELECT * FROM dim_section_path_version ORDER BY version_yyyyMM;
