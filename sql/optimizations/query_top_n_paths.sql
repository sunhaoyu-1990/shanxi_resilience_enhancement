-- ============================================================
-- 简化: Top N 路径查询（修复版v3）
-- ============================================================
-- 作用: 简化版的K最短路径查询（递归CTE）
-- 输入表: dwd_tom_noderelation
-- ============================================================

-- ============================================================
-- 函数1: find_top_n_paths - Top N路径查询
-- ============================================================

DROP FUNCTION IF EXISTS find_top_n_paths(VARCHAR, VARCHAR, VARCHAR, INT, INT);

CREATE OR REPLACE FUNCTION find_top_n_paths(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_n INT DEFAULT 5,
    p_max_depth INT DEFAULT 30
)
RETURNS TABLE (
    path_id INT,
    node_path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_finder AS (
        -- 基础情况：从起点开始
        SELECT
            t.enRoadNodeId AS start_node,
            t.exRoadNodeId AS end_node,
            ARRAY[t.enRoadNodeId, t.exRoadNodeId]::VARCHAR[] AS route,
            t.miles::INT AS cost,
            1::INT AS hops
        FROM dwd_tom_noderelation t
        WHERE t.enRoadNodeId = p_start_node
          AND t.version_yyyyMM = p_version_yyyyMM

        UNION ALL

        -- 递归情况：继续扩展路径
        SELECT
            f.end_node,
            n.exRoadNodeId,
            f.route || n.exRoadNodeId,
            (f.cost + n.miles::INT)::INT,
            (f.hops + 1)::INT
        FROM path_finder f
        JOIN dwd_tom_noderelation n
            ON f.end_node = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            n.exRoadNodeId <> ALL(f.route)
            AND f.hops < p_max_depth
    ),
    all_routes AS (
        SELECT
            route,
            cost,
            hops,
            ROW_NUMBER() OVER (ORDER BY cost ASC, hops ASC) AS rank_id
        FROM path_finder
        WHERE end_node = p_end_node
    )
    SELECT
        ar.rank_id::INT AS path_id,
        ar.route AS node_path,
        ar.cost AS total_miles,
        ar.hops AS node_count
    FROM all_routes ar
    WHERE ar.rank_id <= p_n
    ORDER BY ar.rank_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_top_n_paths(VARCHAR, VARCHAR, VARCHAR, INT, INT)
IS 'Top N路径查询（简化递归CTE）';


-- ============================================================
-- 使用示例
-- ============================================================

/*
-- 示例: 查询Top 5路径
SELECT * FROM find_top_n_paths(
    '起点节点ID',
    '终点节点ID',
    '202512',
    5,   -- 返回5条路径
    30   -- 最大深度30
);
*/

-- 验证函数创建
SELECT 'Top N路径查询函数创建完成！' AS message;