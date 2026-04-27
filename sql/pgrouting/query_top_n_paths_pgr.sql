-- ============================================================
-- pgRouting: Top N 路径查询（贪婪算法v6 - 修复排除逻辑）
-- ============================================================
-- 作用: 使用贪婪算法基于pgRouting找Top N最短路径
-- 原理: 每次找最短路径，然后禁用该路径上的所有中间节点（任意一端禁用），重复N次
-- 输入表: dwd_tom_network_edges, dwd_tom_network_vertices
-- ============================================================

DROP FUNCTION IF EXISTS find_top_n_paths_pgr(VARCHAR, VARCHAR, VARCHAR, INT);

CREATE OR REPLACE FUNCTION find_top_n_paths_pgr(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_n INT DEFAULT 5
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
    v_exclude_nodes BIGINT[] := ARRAY[]::BIGINT[];
    v_sql TEXT;
    v_i INT;
    v_path_count INT := 0;
    v_path_nodes BIGINT[];
    v_path_nodes_original VARCHAR[];
BEGIN
    -- 获取pgRouting节点ID
    v_source := get_pgr_node_id(p_start_node, p_version_yyyyMM);
    v_target := get_pgr_node_id(p_end_node, p_version_yyyyMM);

    -- 循环找N条不同的路径
    WHILE v_path_count < p_n LOOP
        -- 构建排除节点的SQL条件
        IF array_length(v_exclude_nodes, 1) > 0 THEN
            v_sql := format(
                'SELECT id, source, target, cost, reverse_cost FROM dwd_tom_network_edges WHERE version_yyyyMM = %L AND NOT (source = ANY(%L) OR target = ANY(%L))',
                p_version_yyyyMM, v_exclude_nodes, v_exclude_nodes
            );
        ELSE
            v_sql := format(
                'SELECT id, source, target, cost, reverse_cost FROM dwd_tom_network_edges WHERE version_yyyyMM = %L',
                p_version_yyyyMM
            );
        END IF;

        -- 获取路径节点
        SELECT array_agg(node ORDER BY seq), array_agg(original_node_id ORDER BY seq)
        INTO v_path_nodes, v_path_nodes_original
        FROM (
            SELECT pr.seq, pr.node, v.original_node_id
            FROM pgr_dijkstra(v_sql, v_source, v_target, directed := true) pr
            LEFT JOIN dwd_tom_network_vertices v
                ON pr.node = v.id
                AND v.version_yyyyMM = p_version_yyyyMM
            WHERE pr.node > 0
        ) t;

        -- 如果没有找到路径，退出循环
        IF v_path_nodes IS NULL OR array_length(v_path_nodes, 1) IS NULL THEN
            EXIT;
        END IF;

        -- 检查路径是否有效（至少要有起点和终点）
        IF array_length(v_path_nodes, 1) >= 2 THEN
            v_path_count := v_path_count + 1;

            -- 返回路径详情
            RETURN QUERY
            WITH path_info AS (
                SELECT pr.seq, pr.agg_cost, v.original_node_id
                FROM pgr_dijkstra(v_sql, v_source, v_target, directed := true) pr
                LEFT JOIN dwd_tom_network_vertices v
                    ON pr.node = v.id
                    AND v.version_yyyyMM = p_version_yyyyMM
                WHERE pr.node > 0
                ORDER BY pr.seq
            )
            SELECT
                (v_path_count)::INT AS path_id,
                array_agg(original_node_id ORDER BY pi.seq)::VARCHAR[] AS node_path,
                ROUND(MAX(pi.agg_cost))::BIGINT AS total_miles,
                (COUNT(*) - 1)::BIGINT AS node_count
            FROM path_info pi;

            -- 将当前路径上的所有节点加入排除列表（除了起点和终点）
            -- 这样下一次会寻找替代路径
            FOR i IN 2..array_length(v_path_nodes, 1) - 1 LOOP
                v_exclude_nodes := v_exclude_nodes || v_path_nodes[i];
            END LOOP;

            -- 去重
            SELECT array_agg(DISTINCT x ORDER BY x) INTO v_exclude_nodes
            FROM unnest(v_exclude_nodes) AS t(x);
        ELSE
            EXIT;
        END IF;

    END LOOP;

    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_top_n_paths_pgr(VARCHAR, VARCHAR, VARCHAR, INT)
IS 'Top N路径查询（pgRouting贪婪算法，禁用所有分叉点）';


-- ============================================================
-- 使用示例
-- ============================================================

/*
-- 示例: Top 5路径（贪婪算法）
SELECT * FROM find_top_n_paths_pgr(
    '起点节点ID',
    '终点节点ID',
    '202512',
    5
);
*/

-- 验证函数创建
SELECT 'Top N路径查询函数（pgRouting贪婪算法v6）创建完成！' AS message;