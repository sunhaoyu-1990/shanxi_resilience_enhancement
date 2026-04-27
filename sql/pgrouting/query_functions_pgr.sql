-- ============================================================
-- pgRouting: 查询函数
-- ============================================================
-- 作用: 封装pgRouting路径查询函数
-- 输入表: dwd_tom_network_edges, dwd_tom_network_vertices
-- 输出: 路径结果
-- ============================================================

-- ============================================================
-- 辅助函数: 原始节点ID → pgRouting节点ID
-- ============================================================

CREATE OR REPLACE FUNCTION get_pgr_node_id(
    p_original_node_id VARCHAR,
    p_version_yyyyMM VARCHAR
)
RETURNS BIGINT AS $$
DECLARE
    v_pgr_node_id BIGINT;
BEGIN
    SELECT id INTO v_pgr_node_id
    FROM dwd_tom_network_vertices
    WHERE original_node_id = p_original_node_id
      AND version_yyyyMM = p_version_yyyyMM;

    IF v_pgr_node_id IS NULL THEN
        RAISE EXCEPTION 'Node not found: % (version: %)', p_original_node_id, p_version_yyyyMM;
    END IF;

    RETURN v_pgr_node_id;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 辅助函数: pgRouting节点ID → 原始节点信息
-- ============================================================

CREATE OR REPLACE FUNCTION get_original_node_info(
    p_pgr_node_id BIGINT,
    p_version_yyyyMM VARCHAR
)
RETURNS TABLE (
    original_node_id VARCHAR,
    node_type INT,
    node_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.original_node_id,
        v.node_type,
        v.node_name
    FROM dwd_tom_network_vertices v
    WHERE v.id = p_pgr_node_id
      AND v.version_yyyyMM = p_version_yyyyMM;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 函数1: find_shortest_path_pgr - 最短路径（Dijkstra）
-- ============================================================

DROP FUNCTION IF EXISTS find_shortest_path_pgr(VARCHAR, VARCHAR, VARCHAR);

CREATE OR REPLACE FUNCTION find_shortest_path_pgr(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR
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
BEGIN
    -- 获取pgRouting节点ID
    v_source := get_pgr_node_id(p_start_node, p_version_yyyyMM);
    v_target := get_pgr_node_id(p_end_node, p_version_yyyyMM);

    RETURN QUERY
    WITH path_result AS (
        SELECT * FROM pgr_dijkstra(
            format('SELECT id, source, target, cost, reverse_cost
                    FROM dwd_tom_network_edges
                    WHERE version_yyyyMM = %L', p_version_yyyyMM),
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

COMMENT ON FUNCTION find_shortest_path_pgr(VARCHAR, VARCHAR, VARCHAR)
IS 'pgRouting最短路径查询（Dijkstra算法）';


-- ============================================================
-- 函数2: find_k_shortest_paths_pgr - K最短路径（KSP）
-- ============================================================

DROP FUNCTION IF EXISTS find_k_shortest_paths_pgr(VARCHAR, VARCHAR, VARCHAR, INT);

CREATE OR REPLACE FUNCTION find_k_shortest_paths_pgr(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
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
BEGIN
    -- 获取pgRouting节点ID
    v_source := get_pgr_node_id(p_start_node, p_version_yyyyMM);
    v_target := get_pgr_node_id(p_end_node, p_version_yyyyMM);

    RETURN QUERY
    WITH path_result AS (
        SELECT * FROM pgr_ksp(
            format('SELECT id, source, target, cost, reverse_cost
                    FROM dwd_tom_network_edges
                    WHERE version_yyyyMM = %L', p_version_yyyyMM),
            v_source,
            v_target,
            K := p_k,
            directed := true,
            heap_paths := true
        )
    ),
    path_with_info AS (
        SELECT
            pr.path_id,
            pr.seq,
            pr.node,
            pr.edge,
            pr.cost,
            pr.agg_cost,
            v.original_node_id
        FROM path_result pr
        LEFT JOIN dwd_tom_network_vertices v
            ON pr.node = v.id
            AND v.version_yyyyMM = p_version_yyyyMM
        ORDER BY pr.path_id, pr.seq
    ),
    aggregated_paths AS (
        SELECT
            path_id,
            array_agg(original_node_id ORDER BY seq) AS node_path,
            ROUND(MAX(agg_cost))::BIGINT AS total_miles,
            (COUNT(*) - 1)::BIGINT AS node_count
        FROM path_with_info
        GROUP BY path_id
        ORDER BY path_id
    )
    SELECT * FROM aggregated_paths;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_k_shortest_paths_pgr(VARCHAR, VARCHAR, VARCHAR, INT)
IS 'pgRouting K最短路径查询（K-Shortest Path）';


-- ============================================================
-- 使用示例
-- ============================================================

/*
-- 示例1: 查询最短路径
SELECT * FROM find_shortest_path_pgr(
    'G0005610010060',      -- 起点
    'G000561001001820',  -- 终点
    '202512'               -- 版本
);

-- 示例2: 查询Top-5最短路径
SELECT * FROM find_k_shortest_paths_pgr(
    'G0005610010060',
    'G000561001001820',
    '202512',
    5  -- 返回5条路径
);
*/

-- 验证函数创建
SELECT 'pgRouting查询函数创建完成！' AS message;
