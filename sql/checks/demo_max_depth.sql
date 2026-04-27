-- ============================================================
-- 演示: max_depth 参数对性能的影响
-- ============================================================

-- 测试1: 查看两个节点之间的距离（需要几跳）
WITH RECURSIVE path_search AS (
    SELECT
        ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS node_path,
        exRoadNodeId AS last_node,
        1 AS depth
    FROM dwd_tom_noderelation
    WHERE enRoadNodeId = 'G0005610010060'  -- 陕西韦庄收费站
      AND version_yyyyMM = '202512'

    UNION ALL

    SELECT
        p.node_path || n.exRoadNodeId::VARCHAR,
        n.exRoadNodeId,
        p.depth + 1
    FROM path_search p
    JOIN dwd_tom_noderelation n
        ON p.last_node = n.enRoadNodeId
        AND n.version_yyyyMM = '202512'
    WHERE
        n.exRoadNodeId <> ALL(p.node_path)
        AND p.depth < 10  -- 先看10跳内
)
SELECT
    depth,
    array_length(node_path, 1) AS node_count,
    node_path
FROM path_search
WHERE last_node = 'G000561001001820'  -- 目标节点
ORDER BY depth
LIMIT 3;


-- 测试2: 统计不同深度能到达的节点数
WITH RECURSIVE node_reachable AS (
    SELECT
        exRoadNodeId AS node_id,
        1 AS depth
    FROM dwd_tom_noderelation
    WHERE enRoadNodeId = 'G0005610010060'
      AND version_yyyyMM = '202512'

    UNION ALL

    SELECT
        n.exRoadNodeId,
        nr.depth + 1
    FROM node_reachable nr
    JOIN dwd_tom_noderelation n
        ON nr.node_id = n.enRoadNodeId
        AND n.version_yyyyMM = '202512'
    WHERE
        n.exRoadNodeId NOT IN (SELECT node_id FROM node_reachable)
        AND nr.depth < 15
)
SELECT
    depth,
    COUNT(*) AS nodes_at_depth,
    SUM(COUNT(*)) OVER (ORDER BY depth) AS cumulative_nodes
FROM node_reachable
GROUP BY depth
ORDER BY depth;


-- 测试3: 不同max_depth的查询对比（手动执行查看性能）
-- 深度5:
-- SELECT * FROM find_all_paths('G0005610010060', 'G000561001001820', '202512', 5);

-- 深度10:
-- SELECT * FROM find_all_paths('G0005610010060', 'G000561001001820', '202512', 10);

-- 深度15:
-- SELECT * FROM find_all_paths('G0005610010060', 'G000561001001820', '202512', 15);
