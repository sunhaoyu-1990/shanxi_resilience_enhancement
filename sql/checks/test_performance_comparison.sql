-- ============================================================
-- 测试: 性能对比测试SQL（多跳路径）
-- ============================================================

-- 测试1: 查找测试数据中的远节点对
WITH node_stats AS (
    SELECT
        enRoadNodeId AS node_id,
        COUNT(*) AS out_degree
    FROM dwd_tom_noderelation
    WHERE version_yyyyMM = '202512'
    GROUP BY enRoadNodeId
),
ranked_nodes AS (
    SELECT
        node_id,
        out_degree,
        ROW_NUMBER() OVER (ORDER BY out_degree DESC) AS rn
    FROM node_stats
)
SELECT * FROM ranked_nodes WHERE rn <= 5;

-- 测试2: 测试 find_path_simple
-- EXPLAIN ANALYZE
SELECT * FROM find_path_simple(
    'G0005610010060',      -- 陕西韦庄收费站
    'G000561001001820',  -- 某收费单元
    '202512'
);

-- 测试3: 测试 find_shortest_path
-- EXPLAIN ANALYZE
SELECT * FROM find_shortest_path(
    'G0005610010060',
    'G000561001001820',
    '202512',
    15,  -- 最大深度
    5     -- 返回5条
);

-- 测试4: 原版对比（限制深度）
-- EXPLAIN ANALYZE
SELECT * FROM find_all_paths(
    'G0005610010060',
    'G000561001001820',
    '202512',
    15
);
