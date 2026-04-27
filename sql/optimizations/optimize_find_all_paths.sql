-- ============================================================
-- 优化: find_all_paths 性能优化版
-- ============================================================
-- 作用: 优化路径查询性能
-- 输入表: dwd_tom_noderelation
-- 输出: 无
-- 关键字段: version_yyyyMM, enRoadNodeId, exRoadNodeId
-- ============================================================

-- ============================================================
-- 函数1: find_path_simple - 简化版（最快，只返回最短路径）
-- ============================================================

DROP FUNCTION IF EXISTS find_path_simple(VARCHAR, VARCHAR, VARCHAR);

CREATE OR REPLACE FUNCTION find_path_simple(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR
)
RETURNS TABLE (
    node_path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_search AS (
        SELECT
            ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS node_path,
            miles AS total_miles,
            1 AS node_count,
            exRoadNodeId AS last_node
        FROM dwd_tom_noderelation
        WHERE enRoadNodeId = p_start_node
          AND version_yyyyMM = p_version_yyyyMM

        UNION ALL

        SELECT
            p.node_path || n.exRoadNodeId::VARCHAR,
            p.total_miles + n.miles,
            p.node_count + 1,
            n.exRoadNodeId
        FROM path_search p
        JOIN dwd_tom_noderelation n
            ON p.last_node = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            n.exRoadNodeId <> ALL(p.node_path)
            AND p.node_count < 15
    )
    SELECT
        path_search.node_path,
        path_search.total_miles,
        path_search.node_count
    FROM path_search
    WHERE path_search.last_node = p_end_node
    ORDER BY path_search.total_miles
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_path_simple(VARCHAR, VARCHAR, VARCHAR)
IS '简化版路径查询（最快，只返回最短路径）';


-- ============================================================
-- 函数2: find_shortest_path - 最短路径优先（带限制）
-- ============================================================

DROP FUNCTION IF EXISTS find_shortest_path(VARCHAR, VARCHAR, VARCHAR, INT, INT);

CREATE OR REPLACE FUNCTION find_shortest_path(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_max_depth INT DEFAULT 20,
    p_max_paths INT DEFAULT 5
)
RETURNS TABLE (
    node_path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_search AS (
        SELECT
            ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS node_path,
            miles AS total_miles,
            1 AS node_count,
            exRoadNodeId AS last_node
        FROM dwd_tom_noderelation
        WHERE enRoadNodeId = p_start_node
          AND version_yyyyMM = p_version_yyyyMM

        UNION ALL

        SELECT
            p.node_path || n.exRoadNodeId::VARCHAR,
            p.total_miles + n.miles,
            p.node_count + 1,
            n.exRoadNodeId
        FROM path_search p
        JOIN dwd_tom_noderelation n
            ON p.last_node = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            n.exRoadNodeId <> ALL(p.node_path)
            AND p.node_count < p_max_depth
    )
    SELECT
        path_search.node_path,
        path_search.total_miles,
        path_search.node_count
    FROM path_search
    WHERE path_search.last_node = p_end_node
    ORDER BY path_search.total_miles
    LIMIT p_max_paths;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_shortest_path(VARCHAR, VARCHAR, VARCHAR, INT, INT)
IS '查找最短路径（限制返回数量，带剪枝优化）';


-- 验证函数创建
SELECT '路径查询优化函数创建完成！' AS message;
