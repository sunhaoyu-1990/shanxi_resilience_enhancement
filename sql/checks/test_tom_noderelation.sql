-- ============================================================
-- 高速路网拓扑结构表 - 测试SQL
-- ============================================================
-- 作用: 测试路网拓扑查询功能
-- ============================================================

-- ============================================================
-- 测试1: 查看各版本数据量
-- ============================================================

SELECT
    version_yyyyMM,
    COUNT(*) AS cnt
FROM dwd_tom_noderelation
GROUP BY version_yyyyMM
ORDER BY version_yyyyMM;

-- ============================================================
-- 测试2: 查看节点类型分布
-- ============================================================

SELECT
    '入口' AS node_type,
    enroadNodeType AS type,
    CASE enroadNodeType
        WHEN 1 THEN '普通收费单元'
        WHEN 2 THEN '省界收费单元'
        WHEN 3 THEN '收费站'
        ELSE '未知'
    END AS type_desc,
    COUNT(*) AS cnt
FROM dwd_tom_noderelation
GROUP BY enroadNodeType
UNION ALL
SELECT
    '出口' AS node_type,
    exroadNodeType AS type,
    CASE exroadNodeType
        WHEN 1 THEN '普通收费单元'
        WHEN 2 THEN '省界收费单元'
        WHEN 3 THEN '收费站'
        ELSE '未知'
    END AS type_desc,
    COUNT(*) AS cnt
FROM dwd_tom_noderelation
GROUP BY exroadNodeType
ORDER BY node_type, type;

-- ============================================================
-- 测试3: 查看样本数据（前20条）
-- ============================================================

SELECT *
FROM dwd_tom_noderelation
WHERE version_yyyyMM = '202512'
LIMIT 20;

-- ============================================================
-- 测试4: 获取某节点的下一个节点
-- ============================================================
-- 使用示例: 替换 'G000561001001820' 为实际节点ID

SELECT *
FROM get_next_nodes('G000561001001820', '202512');

-- 或者直接查询
SELECT
    exRoadNodeId AS node_id,
    exroadNodeType AS node_type,
    exRoadNodeName AS node_name,
    miles
FROM dwd_tom_noderelation
WHERE enRoadNodeId = 'G000561001001820'
  AND version_yyyyMM = '202512';

-- ============================================================
-- 测试5: 获取某节点的上一个节点
-- ============================================================
-- 使用示例: 替换 'G000561001001820' 为实际节点ID

SELECT *
FROM get_prev_nodes('G000561001001820', '202512');

-- 或者直接查询
SELECT
    enRoadNodeId AS node_id,
    enroadNodeType AS node_type,
    enRoadNodeName AS node_name,
    miles
FROM dwd_tom_noderelation
WHERE exRoadNodeId = 'G000561001001820'
  AND version_yyyyMM = '202512';

-- ============================================================
-- 测试6: 查找从某收费站到某收费单元的路径
-- ============================================================
-- 使用示例: 替换起点和终点为实际节点ID

SELECT *
FROM find_all_paths(
    'G0005610010060',      -- 起点: 陕西韦庄收费站
    'G000561001001820',  -- 终点
    '202512',              -- 版本
    20                     -- 最大深度
);

-- ============================================================
-- 测试7: 查看某收费站的相邻节点
-- ============================================================
-- 使用示例: 替换 'G0005610010060' 为实际收费站ID

-- 从收费站出发的节点
SELECT
    '从收费站出发' AS direction,
    exRoadNodeId,
    exroadNodeType,
    exRoadNodeName,
    miles
FROM dwd_tom_noderelation
WHERE enRoadNodeId = 'G0005610010060'
  AND version_yyyyMM = '202512'

UNION ALL

-- 到达收费站的节点
SELECT
    '到达收费站' AS direction,
    enRoadNodeId,
    enroadNodeType,
    enRoadNodeName,
    miles
FROM dwd_tom_noderelation
WHERE exRoadNodeId = 'G0005610010060'
  AND version_yyyyMM = '202512';

-- ============================================================
-- 测试8: 统计各版本的平均里程
-- ============================================================

SELECT
    version_yyyyMM,
    COUNT(*) AS total_relations,
    AVG(miles) AS avg_miles,
    MIN(miles) AS min_miles,
    MAX(miles) AS max_miles
FROM dwd_tom_noderelation
WHERE miles > 0
GROUP BY version_yyyyMM
ORDER BY version_yyyyMM;

-- ============================================================
-- 测试9: 查找里程最长的10条关系
-- ============================================================

SELECT
    version_yyyyMM,
    enRoadNodeId,
    enRoadNodeName,
    exRoadNodeId,
    exRoadNodeName,
    miles
FROM dwd_tom_noderelation
WHERE miles > 0
ORDER BY miles DESC
LIMIT 10;

-- ============================================================
-- 测试10: 查找某节点的所有相邻节点（双向）
-- ============================================================
-- 使用示例: 替换 'G000561001001820' 为实际节点ID

WITH next_nodes AS (
    SELECT
        'next' AS direction,
        exRoadNodeId AS node_id,
        exroadNodeType AS node_type,
        exRoadNodeName AS node_name,
        miles
    FROM dwd_tom_noderelation
    WHERE enRoadNodeId = 'G000561001001820'
      AND version_yyyyMM = '202512'
),
prev_nodes AS (
    SELECT
        'prev' AS direction,
        enRoadNodeId AS node_id,
        enroadNodeType AS node_type,
        enRoadNodeName AS node_name,
        miles
    FROM dwd_tom_noderelation
    WHERE exRoadNodeId = 'G000561001001820'
      AND version_yyyyMM = '202512'
)
SELECT * FROM next_nodes
UNION ALL
SELECT * FROM prev_nodes
ORDER BY direction, miles;