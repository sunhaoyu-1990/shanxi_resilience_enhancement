-- ============================================================
-- 优化: 高效路径查询函数（不依赖pgRouting）
-- ============================================================
-- 作用: 使用优化的递归CTE实现路径查询
-- 输入表: dwd_tom_noderelation
-- 输出: 路径结果
-- ============================================================

-- ============================================================
-- 函数1: get_next_sections - 获取下一个收费单元
-- ============================================================

CREATE OR REPLACE FUNCTION get_next_sections(
    p_section_id VARCHAR,
    p_version_yyyyMM VARCHAR
)
RETURNS TABLE (
    section_id VARCHAR,
    section_name VARCHAR,
    section_type INT,
    miles INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        exRoadNodeId AS section_id,
        exRoadNodeName AS section_name,
        exroadNodeType AS section_type,
        miles
    FROM dwd_tom_noderelation
    WHERE enRoadNodeId = p_section_id
      AND version_yyyyMM = p_version_yyyyMM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_next_sections(VARCHAR, VARCHAR)
IS '获取指定收费单元的下一个单元';


-- ============================================================
-- 函数2: get_prev_sections - 获取上一个收费单元
-- ============================================================

CREATE OR REPLACE FUNCTION get_prev_sections(
    p_section_id VARCHAR,
    p_version_yyyyMM VARCHAR
)
RETURNS TABLE (
    section_id VARCHAR,
    section_name VARCHAR,
    section_type INT,
    miles INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        enRoadNodeId AS section_id,
        enRoadNodeName AS section_name,
        enroadNodeType AS section_type,
        miles
    FROM dwd_tom_noderelation
    WHERE exRoadNodeId = p_section_id
      AND version_yyyyMM = p_version_yyyyMM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_prev_sections(VARCHAR, VARCHAR)
IS '获取指定收费单元的上一个单元';


-- ============================================================
-- 函数3: find_shortest_path_optimized - 最短路径（优化递归CTE）
-- ============================================================

DROP FUNCTION IF EXISTS find_shortest_path_optimized(VARCHAR, VARCHAR, VARCHAR, INT);

CREATE OR REPLACE FUNCTION find_shortest_path_optimized(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_max_depth INT DEFAULT 50
)
RETURNS TABLE (
    seq INT,
    node_path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_search AS (
        -- 基础情况：从起点开始
        SELECT
            enRoadNodeId,
            exRoadNodeId,
            ARRAY[enRoadNodeId, exRoadNodeId] AS path,
            miles AS total_miles,
            1 AS node_count,
            miles AS priority  -- 使用里程作为优先级（Dijkstra-like）
        FROM dwd_tom_noderelation
        WHERE enRoadNodeId = p_start_node
          AND version_yyyyMM = p_version_yyyyMM

        UNION ALL

        -- 递归情况：继续扩展路径
        SELECT
            p.enRoadNodeId,
            n.exRoadNodeId,
            p.path || n.exRoadNodeId,
            p.total_miles + n.miles,
            p.node_count + 1,
            p.total_miles + n.miles AS priority
        FROM path_search p
        JOIN dwd_tom_noderelation n
            ON p.exRoadNodeId = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            -- 避免循环
            n.exRoadNodeId <> ALL(p.path)
            -- 限制最大深度
            AND p.node_count < p_max_depth
            -- 提前终止：如果找到终点，不再扩展太长的路径
            AND NOT EXISTS (
                SELECT 1 FROM path_search
                WHERE exRoadNodeId = p_end_node
                  AND total_miles <= p.total_miles + n.miles
            )
    ),
    ranked_paths AS (
        SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY total_miles, node_count) AS rn
        FROM path_search
        WHERE exRoadNodeId = p_end_node
    )
    SELECT
        1 AS seq,
        path AS node_path,
        total_miles,
        node_count
    FROM ranked_paths
    WHERE rn = 1
    ORDER BY total_miles;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_shortest_path_optimized(VARCHAR, VARCHAR, VARCHAR, INT)
IS '优化的最短路径查询（使用递归CTE + 剪枝）';


-- ============================================================
-- 函数4: find_k_shortest_paths_optimized - K最短路径（优化版）
-- ============================================================

DROP FUNCTION IF EXISTS find_k_shortest_paths_optimized(VARCHAR, VARCHAR, VARCHAR, INT, INT);

CREATE OR REPLACE FUNCTION find_k_shortest_paths_optimized(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_k INT DEFAULT 5,
    p_max_depth INT DEFAULT 50
)
RETURNS TABLE (
    path_id INT,
    node_path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_search AS (
        -- 基础情况：从起点开始
        SELECT
            enRoadNodeId,
            exRoadNodeId,
            ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS path,
            miles AS total_miles,
            1 AS node_count
        FROM dwd_tom_noderelation
        WHERE enRoadNodeId = p_start_node
          AND version_yyyyMM = p_version_yyyyMM

        UNION ALL

        -- 递归情况：继续扩展路径
        SELECT
            p.enRoadNodeId,
            n.exRoadNodeId,
            p.path || n.exRoadNodeId,
            p.total_miles + n.miles,
            p.node_count + 1
        FROM path_search p
        JOIN dwd_tom_noderelation n
            ON p.exRoadNodeId = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            -- 避免循环
            n.exRoadNodeId <> ALL(p.path)
            -- 限制最大深度
            AND p.node_count < p_max_depth
    ),
    valid_paths AS (
        SELECT
            path,
            total_miles,
            node_count,
            ROW_NUMBER() OVER (ORDER BY total_miles, node_count) AS path_id
        FROM path_search
        WHERE exRoadNodeId = p_end_node
    )
    SELECT
        path_id,
        path AS node_path,
        total_miles,
        node_count
    FROM valid_paths
    WHERE path_id <= p_k
    ORDER BY path_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_k_shortest_paths_optimized(VARCHAR, VARCHAR, VARCHAR, INT, INT)
IS '优化的K最短路径查询（递归CTE）';


-- ============================================================
-- 函数5: find_all_paths_bounded - 边界全路径搜索
-- ============================================================
-- 适用于30+节点的长路径，但有边界约束

DROP FUNCTION IF EXISTS find_all_paths_bounded(VARCHAR, VARCHAR, VARCHAR, INT, INT);

CREATE OR REPLACE FUNCTION find_all_paths_bounded(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_max_depth INT DEFAULT 30,
    p_max_paths INT DEFAULT 100
)
RETURNS TABLE (
    path_id INT,
    node_path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
DECLARE
    v_shortest_miles INT;
BEGIN
    -- 先找最短路径的里程
    SELECT fso.total_miles INTO v_shortest_miles
    FROM find_shortest_path_optimized(
        p_start_node,
        p_end_node,
        p_version_yyyyMM,
        p_max_depth
    ) fso;

    IF v_shortest_miles IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH RECURSIVE path_search AS (
        -- 基础情况：从起点开始
        SELECT
            enRoadNodeId,
            exRoadNodeId,
            ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS path,
            miles AS total_miles,
            1 AS node_count
        FROM dwd_tom_noderelation
        WHERE enRoadNodeId = p_start_node
          AND version_yyyyMM = p_version_yyyyMM

        UNION ALL

        -- 递归情况：继续扩展路径
        SELECT
            p.enRoadNodeId,
            n.exRoadNodeId,
            p.path || n.exRoadNodeId,
            p.total_miles + n.miles,
            p.node_count + 1
        FROM path_search p
        JOIN dwd_tom_noderelation n
            ON p.exRoadNodeId = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            -- 避免循环
            n.exRoadNodeId <> ALL(p.path)
            -- 限制最大深度
            AND p.node_count < p_max_depth
            -- 里程剪枝：不超过最短路径的2倍
            AND p.total_miles + n.miles <= v_shortest_miles * 2
    ),
    valid_paths AS (
        SELECT
            path,
            total_miles,
            node_count,
            ROW_NUMBER() OVER (ORDER BY total_miles, node_count) AS path_id
        FROM path_search
        WHERE exRoadNodeId = p_end_node
    )
    SELECT
        path_id,
        path AS node_path,
        total_miles,
        node_count
    FROM valid_paths
    WHERE path_id <= p_max_paths
    ORDER BY path_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_all_paths_bounded(VARCHAR, VARCHAR, VARCHAR, INT, INT)
IS '边界全路径搜索（带里程和路径数限制）';


-- ============================================================
-- 使用示例
-- ============================================================

/*
-- 示例1: 获取相邻节点
SELECT * FROM get_next_sections('G0005610010060', '202512');
SELECT * FROM get_prev_sections('G0005610010060', '202512');

-- 示例2: 查询最短路径
SELECT * FROM find_shortest_path_optimized(
    'G0005610010060',      -- 起点
    'G000561001001820',  -- 终点
    '202512',              -- 版本
    50                      -- 最大深度
);

-- 示例3: 查询Top-5最短路径
SELECT * FROM find_k_shortest_paths_optimized(
    'G0005610010060',
    'G000561001001820',
    '202512',
    5,  -- 返回5条路径
    50  -- 最大深度
);

-- 示例4: 边界全路径搜索（适用于长路径）
SELECT * FROM find_all_paths_bounded(
    'G0005610010060',
    'G000561001001820',
    '202512',
    30,  -- 最大深度
    100  -- 最大路径数
);
*/

-- 验证函数创建
SELECT '优化路径查询函数创建完成！' AS message;