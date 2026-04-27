-- ============================================================
-- 修复: find_all_paths 函数数组类型问题
-- ============================================================

-- 删除旧函数
DROP FUNCTION IF EXISTS find_all_paths(VARCHAR, VARCHAR, VARCHAR, INT);

-- 重新创建函数（添加显式类型转换）
CREATE OR REPLACE FUNCTION find_all_paths(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_max_depth INT DEFAULT 20
)
RETURNS TABLE (
    path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_search AS (
        -- 基础情况：从起点开始
        SELECT
            ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS path,
            miles AS total_miles,
            1 AS node_count
        FROM dwd_tom_noderelation
        WHERE enRoadNodeId = p_start_node
          AND version_yyyyMM = p_version_yyyyMM

        UNION ALL

        -- 递归情况：继续扩展路径
        SELECT
            p.path || n.exRoadNodeId::VARCHAR,
            p.total_miles + n.miles,
            p.node_count + 1
        FROM path_search p
        JOIN dwd_tom_noderelation n
            ON p.path[array_upper(p.path, 1)] = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            -- 避免循环
            n.exRoadNodeId <> ALL(p.path)
            -- 限制最大深度
            AND p.node_count < p_max_depth
    )
    SELECT
        path,
        total_miles,
        node_count
    FROM path_search
    WHERE path[array_upper(path, 1)] = p_end_node
    ORDER BY total_miles;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_all_paths(VARCHAR, VARCHAR, VARCHAR, INT) IS '查找两节点间的所有路径';

-- 验证函数已创建
SELECT '函数 find_all_paths 修复完成！' AS message;