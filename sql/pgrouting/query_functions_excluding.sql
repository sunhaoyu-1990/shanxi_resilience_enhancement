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