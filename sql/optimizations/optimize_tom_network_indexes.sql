-- ============================================================
-- 优化: 高速路网拓扑查询索引优化
-- ============================================================
-- 作用: 为路径查询添加高效复合索引
-- 输入表: dwd_tom_noderelation
-- 输出: 无
-- 关键字段: version_yyyyMM, enRoadNodeId, exRoadNodeId
-- ============================================================

-- 1. 删除旧的低效索引
DROP INDEX IF EXISTS idx_dwd_tom_noderelation_en_node;
DROP INDEX IF EXISTS idx_dwd_tom_noderelation_ex_node;

-- 2. 创建高效复合索引（包含版本和里程信息）
-- 用于前向搜索: version + 入口节点
CREATE INDEX IF NOT EXISTS idx_dwd_tom_noderelation_forward
ON dwd_tom_noderelation(version_yyyyMM, enRoadNodeId)
INCLUDE (exRoadNodeId, miles, exRoadNodeName, exroadNodeType);

-- 用于反向搜索: version + 出口节点
CREATE INDEX IF NOT EXISTS idx_dwd_tom_noderelation_backward
ON dwd_tom_noderelation(version_yyyyMM, exRoadNodeId)
INCLUDE (enRoadNodeId, miles, enRoadNodeName, enroadNodeType);

-- 3. 创建节点统计信息（用于查询优化器）
ANALYZE dwd_tom_noderelation;

-- 验证索引
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'dwd_tom_noderelation'
ORDER BY indexname;
