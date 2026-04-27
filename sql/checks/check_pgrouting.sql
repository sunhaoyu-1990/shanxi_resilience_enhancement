-- ============================================================
-- 检查: pgRouting 安装状态
-- ============================================================

-- 检查已安装的扩展
SELECT extname, extversion
FROM pg_extension
WHERE extname LIKE '%postgis%' OR extname LIKE '%pgr%';

-- 检查版本
SELECT version();
SELECT PostGIS_Version();
