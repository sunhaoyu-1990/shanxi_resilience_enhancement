-- ============================================================
-- pgRouting: 带排除节点的最短路径查询
-- ============================================================
-- 作用: 查询不经过指定节点的最短路径
-- 输入表: dwd_tom_network_edges, dwd_tom_network_vertices
-- ============================================================

-- ============================================================
-- 函数1: find_shortest_path_excluding - 带排除节点的最短路径
-- ============================================================

DROP FUNCTION IF EXISTS find_shortest_path_excluding(VARCHAR, VARCHAR, VARCHAR, VARCHAR[]);

CREATE OR REPLACE FUNCTION find_shortest_path_excluding(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_exclude_nodes VARCHAR[] DEFAULT '{}'::VARCHAR[]
)
RETURNS TABLE (
    seq INT,
    node_path VARCHAR[],
    total_miles BIGINT,
    node_count BIGINT
) AS $$
DECLARE
    v_source BIGINT;
    v_target BIGINT;
    v_exclude_ids BIGINT[];
BEGIN
    -- 获取pgRouting节点ID
    v_source := get_pgr_node_id(p_start_node, p_version_yyyyMM);
    v_target := get_pgr_node_id(p_end_node, p_version_yyyyMM);

    -- 获取排除节点的pgRouting ID（如果有）
    IF array_length(p_exclude_nodes, 1) > 0 THEN
        SELECT array_agg(id) INTO v_exclude_ids
        FROM dwd_tom_network_vertices
        WHERE original_node_id = ANY(p_exclude_nodes)
          AND version_yyyyMM = p_version_yyyyMM;
    ELSE
        v_exclude_ids := '{}'::BIGINT[];
    END IF;

    RETURN QUERY
    WITH path_result AS (
        SELECT * FROM pgr_dijkstra(
            format('SELECT id, source, target, cost, reverse_cost
                    FROM dwd_tom_network_edges
                    WHERE version_yyyyMM = %L
                      AND source <> ALL(%L::BIGINT[])
                      AND target <> ALL(%L::BIGINT[])',
                   p_version_yyyyMM, v_exclude_ids, v_exclude_ids),
            v_source,
            v_target,
            directed := true
        )
    ),
    path_with_nodes AS (
        SELECT
            pr.seq,
            pr.node,
            pr.edge,
            pr.cost,
            pr.agg_cost,
            v.original_node_id,
            v.node_name
        FROM path_result pr
        LEFT JOIN dwd_tom_network_vertices v
            ON pr.node = v.id
            AND v.version_yyyyMM = p_version_yyyyMM
        ORDER BY pr.seq
    ),
    aggregated_path AS (
        SELECT
            1 AS seq,
            array_agg(original_node_id ORDER BY pwn.seq) AS node_path,
            ROUND(MAX(agg_cost))::BIGINT AS total_miles,
            (COUNT(*) - 1)::BIGINT AS node_count
        FROM path_with_nodes pwn
    )
    SELECT * FROM aggregated_path;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_shortest_path_excluding(VARCHAR, VARCHAR, VARCHAR, VARCHAR[])
IS '带排除节点的最短路径查询（Dijkstra算法）';


-- ============================================================
-- 使用示例
-- ============================================================

/*
-- 示例1: 基础最短路径（不排除任何节点）
SELECT * FROM find_shortest_path_excluding(
    '起点节点ID',
    '终点节点ID',
    '202512'
);

-- 示例2: 排除单个节点
SELECT * FROM find_shortest_path_excluding(
    '起点节点ID',
    '终点节点ID',
    '202512',
    ARRAY['要排除的节点ID']
);

-- 示例3: 排除多个节点
SELECT * FROM find_shortest_path_excluding(
    '起点节点ID',
    '终点节点ID',
    '202512',
    ARRAY['节点1', '节点2', '节点3']
);
*/

-- 验证函数创建
SELECT '带排除节点的最短路径查询函数创建完成！' AS message;


-- ============================================================
-- 函数2: find_k_shortest_paths_excluding - K条最短路径（排除节点）
-- ============================================================

DROP FUNCTION IF EXISTS find_k_shortest_paths_excluding(VARCHAR, VARCHAR, VARCHAR, VARCHAR[], INT);

CREATE OR REPLACE FUNCTION find_k_shortest_paths_excluding(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_exclude_nodes VARCHAR[] DEFAULT '{}'::VARCHAR[],
    p_k INT DEFAULT 5
)
RETURNS TABLE (
    path_id INT,
    node_path VARCHAR[],
    total_miles BIGINT,
    node_count BIGINT
) AS $$
DECLARE
    v_source BIGINT;
    v_target BIGINT;
    v_exclude_ids BIGINT[];
    v_sql TEXT;
BEGIN
    -- 获取pgRouting节点ID
    v_source := get_pgr_node_id(p_start_node, p_version_yyyyMM);
    v_target := get_pgr_node_id(p_end_node, p_version_yyyyMM);

    -- 获取排除节点的pgRouting ID（如果有）
    IF array_length(p_exclude_nodes, 1) > 0 THEN
        SELECT array_agg(id) INTO v_exclude_ids
        FROM dwd_tom_network_vertices
        WHERE original_node_id = ANY(p_exclude_nodes)
          AND version_yyyyMM = p_version_yyyyMM;
    ELSE
        v_exclude_ids := '{}'::BIGINT[];
    END IF;

    -- 构建 SQL：在边表中排除涉及 exclude_nodes 的边
    v_sql := format(
        'SELECT id, source, target, cost, reverse_cost
         FROM dwd_tom_network_edges
         WHERE version_yyyyMM = %L
           AND source <> ALL(%L::BIGINT[])
           AND target <> ALL(%L::BIGINT[])',
        p_version_yyyyMM, v_exclude_ids, v_exclude_ids
    );

    RETURN QUERY
    WITH
    -- 使用 CTE 来存储 pgr_ksp 的结果
    ksp_result AS (
        SELECT (x).seq AS ksp_seq,
               (x).path_id AS ksp_path_id,
               (x).path_seq AS ksp_path_seq,
               (x).node AS ksp_node,
               (x).edge AS ksp_edge,
               (x).cost AS ksp_cost,
               (x).agg_cost AS ksp_agg_cost
        FROM (
            SELECT pgr_ksp(
                v_sql,
                v_source,
                v_target,
                p_k,
                true,
                true
            ) AS x
        ) AS sub
    ),
    -- 转换为原始节点ID，并去重（同一 path_id 内可能返回重复节点）
    nodes_with_original AS (
        SELECT DISTINCT ON (ksp_path_id, ksp_node)
            ksp_path_id,
            ksp_seq,
            ksp_agg_cost,
            v.original_node_id
        FROM ksp_result k
        LEFT JOIN dwd_tom_network_vertices v
            ON k.ksp_node = v.id
            AND v.version_yyyyMM = p_version_yyyyMM
        ORDER BY ksp_path_id, ksp_node
    ),
    -- 按路径聚合节点
    aggregated_paths AS (
        SELECT
            ksp_path_id AS path_id,
            array_agg(original_node_id ORDER BY ksp_seq) AS node_path,
            ROUND(MAX(ksp_agg_cost))::BIGINT AS total_miles,
            COUNT(*) - 1 AS node_count
        FROM nodes_with_original
        GROUP BY ksp_path_id
        ORDER BY ksp_path_id
    )
    SELECT * FROM aggregated_paths;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_k_shortest_paths_excluding(VARCHAR, VARCHAR, VARCHAR, VARCHAR[], INT)
IS 'pgRouting K条最短路径查询（排除指定节点）';


-- ============================================================
-- 使用示例
-- ============================================================

/*
-- 示例1: 查询K条绕行路径（排除单个节点）
SELECT * FROM find_k_shortest_paths_excluding(
    '起点节点ID',
    '终点节点ID',
    '202512',
    ARRAY['要排除的节点ID'],
    5  -- 返回5条路径
);

-- 示例2: 查询K条绕行路径（排除多个节点）
SELECT * FROM find_k_shortest_paths_excluding(
    '起点节点ID',
    '终点节点ID',
    '202512',
    ARRAY['节点1', '节点2', '节点3'],
    5
);
*/