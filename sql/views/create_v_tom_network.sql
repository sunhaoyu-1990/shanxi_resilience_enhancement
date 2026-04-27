-- ============================================================
-- View: v_tom_network
-- ============================================================
-- 作用: 高速路网拓扑简化视图
-- 输入表: dwd_tom_noderelation
-- 输出: 无
-- 粒度: 节点关系
-- 关键字段: enRoadNodeId, exRoadNodeId, miles, version_yyyyMM
-- ============================================================
-- 用途: 简化路径查询
-- ============================================================

CREATE OR REPLACE VIEW v_tom_network AS
SELECT
    id,
    version,
    version_yyyyMM,
    enRoadNodeId,
    enroadNodeType,
    enRoadNodeName,
    enStationID,
    enHEX,
    exRoadNodeId,
    exroadNodeType,
    exRoadNodeName,
    exStationID,
    exHEX,
    miles,
    source_flag,
    created_at,
    updated_at
FROM dwd_tom_noderelation;

COMMENT ON VIEW v_tom_network IS '高速路网拓扑简化视图';

-- ============================================================
-- 函数1: 获取收费单元的下一个节点
-- ============================================================

CREATE OR REPLACE FUNCTION get_next_nodes(
    p_section_id VARCHAR,
    p_version_yyyyMM VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    node_id VARCHAR,
    node_type INT,
    node_name VARCHAR,
    distance_miles INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.exRoadNodeId AS node_id,
        t.exroadNodeType AS node_type,
        t.exRoadNodeName AS node_name,
        t.miles AS distance_miles
    FROM dwd_tom_noderelation t
    WHERE t.enRoadNodeId = p_section_id
      AND (p_version_yyyyMM IS NULL OR t.version_yyyyMM = p_version_yyyyMM);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_next_nodes(VARCHAR, VARCHAR) IS '获取收费单元的下一个节点';

-- ============================================================
-- 函数2: 获取收费单元的上一个节点
-- ============================================================

CREATE OR REPLACE FUNCTION get_prev_nodes(
    p_section_id VARCHAR,
    p_version_yyyyMM VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    node_id VARCHAR,
    node_type INT,
    node_name VARCHAR,
    distance_miles INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.enRoadNodeId AS node_id,
        t.enroadNodeType AS node_type,
        t.enRoadNodeName AS node_name,
        t.miles AS distance_miles
    FROM dwd_tom_noderelation t
    WHERE t.exRoadNodeId = p_section_id
      AND (p_version_yyyyMM IS NULL OR t.version_yyyyMM = p_version_yyyyMM);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_prev_nodes(VARCHAR, VARCHAR) IS '获取收费单元的上一个节点';

-- ============================================================
-- 函数3: 查找两节点间的所有路径
-- ============================================================

CREATE OR REPLACE FUNCTION find_all_paths(
    p_start_node VARCHAR,
    p_end_node VARCHAR,
    p_version_yyyyMM VARCHAR,
    p_max_depth INT DEFAULT 20
)
RETURNS TABLE (
    node_path VARCHAR[],
    total_miles INT,
    node_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE path_search AS (
        -- 基础情况：从起点开始
        SELECT
            ARRAY[enRoadNodeId::VARCHAR, exRoadNodeId::VARCHAR] AS node_path,
            miles AS total_miles,
            1 AS node_count
        FROM dwd_tom_noderelation
        WHERE enRoadNodeId = p_start_node
          AND version_yyyyMM = p_version_yyyyMM

        UNION ALL

        -- 递归情况：继续扩展路径
        SELECT
            p.node_path || n.exRoadNodeId::VARCHAR,
            p.total_miles + n.miles,
            p.node_count + 1
        FROM path_search p
        JOIN dwd_tom_noderelation n
            ON p.node_path[array_upper(p.node_path, 1)] = n.enRoadNodeId
            AND n.version_yyyyMM = p_version_yyyyMM
        WHERE
            -- 避免循环
            n.exRoadNodeId <> ALL(p.node_path)
            -- 限制最大深度
            AND p.node_count < p_max_depth
    )
    SELECT
        path_search.node_path,
        path_search.total_miles,
        path_search.node_count
    FROM path_search
    WHERE path_search.node_path[array_upper(path_search.node_path, 1)] = p_end_node
    ORDER BY path_search.total_miles;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_all_paths(VARCHAR, VARCHAR, VARCHAR, INT) IS '查找两节点间的所有路径';