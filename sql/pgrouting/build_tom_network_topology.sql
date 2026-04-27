-- ============================================================
-- pgRouting: 构建路网拓扑
-- ============================================================
-- 作用: 将dwd_tom_noderelation转换为pgRouting格式
-- 输入表: dwd_tom_noderelation
-- 输出表: dwd_tom_network_vertices, dwd_tom_network_edges
-- ============================================================

-- ============================================================
-- Step 1: 清空旧数据（按版本）
-- ============================================================

CREATE OR REPLACE FUNCTION clear_tom_network_topology(p_version_yyyyMM VARCHAR)
RETURNS VOID AS $$
BEGIN
    DELETE FROM dwd_tom_network_edges
    WHERE version_yyyyMM = p_version_yyyyMM;

    DELETE FROM dwd_tom_network_vertices
    WHERE version_yyyyMM = p_version_yyyyMM;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- Step 2: 构建节点映射
-- ============================================================

CREATE OR REPLACE FUNCTION build_tom_network_vertices(p_version_yyyyMM VARCHAR)
RETURNS INT AS $$
DECLARE
    v_node_count INT;
BEGIN
    -- 插入所有入口节点
    INSERT INTO dwd_tom_network_vertices (
        original_node_id,
        version_yyyyMM,
        node_type,
        node_name
    )
    SELECT DISTINCT
        enRoadNodeId AS original_node_id,
        version_yyyyMM,
        enroadNodeType AS node_type,
        enRoadNodeName AS node_name
    FROM dwd_tom_noderelation
    WHERE version_yyyyMM = p_version_yyyyMM
      AND enRoadNodeId IS NOT NULL
    ON CONFLICT (original_node_id, version_yyyyMM) DO NOTHING;

    -- 插入所有出口节点
    INSERT INTO dwd_tom_network_vertices (
        original_node_id,
        version_yyyyMM,
        node_type,
        node_name
    )
    SELECT DISTINCT
        exRoadNodeId AS original_node_id,
        version_yyyyMM,
        exroadNodeType AS node_type,
        exRoadNodeName AS node_name
    FROM dwd_tom_noderelation
    WHERE version_yyyyMM = p_version_yyyyMM
      AND exRoadNodeId IS NOT NULL
    ON CONFLICT (original_node_id, version_yyyyMM) DO NOTHING;

    SELECT COUNT(*) INTO v_node_count
    FROM dwd_tom_network_vertices
    WHERE version_yyyyMM = p_version_yyyyMM;

    RETURN v_node_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- Step 3: 构建边表
-- ============================================================

CREATE OR REPLACE FUNCTION build_tom_network_edges(p_version_yyyyMM VARCHAR)
RETURNS INT AS $$
DECLARE
    v_edge_count INT;
BEGIN
    INSERT INTO dwd_tom_network_edges (
        source,
        target,
        cost,
        reverse_cost,
        version_yyyyMM,
        original_enRoadNodeId,
        original_exRoadNodeId,
        enroadNodeType,
        exroadNodeType,
        enRoadNodeName,
        exRoadNodeName,
        miles
    )
    SELECT
        v_src.id AS source,
        v_tgt.id AS target,
        COALESCE(NULLIF(t.miles, 0), 1) AS cost,  -- 避免0代价
        1e9 AS reverse_cost,  -- 单向路网，反向代价设为极大值
        t.version_yyyyMM,
        t.enRoadNodeId AS original_enRoadNodeId,
        t.exRoadNodeId AS original_exRoadNodeId,
        t.enroadNodeType,
        t.exroadNodeType,
        t.enRoadNodeName,
        t.exRoadNodeName,
        t.miles
    FROM dwd_tom_noderelation t
    JOIN dwd_tom_network_vertices v_src
        ON t.enRoadNodeId = v_src.original_node_id
        AND t.version_yyyyMM = v_src.version_yyyyMM
    JOIN dwd_tom_network_vertices v_tgt
        ON t.exRoadNodeId = v_tgt.original_node_id
        AND t.version_yyyyMM = v_tgt.version_yyyyMM
    WHERE t.version_yyyyMM = p_version_yyyyMM;

    SELECT COUNT(*) INTO v_edge_count
    FROM dwd_tom_network_edges
    WHERE version_yyyyMM = p_version_yyyyMM;

    RETURN v_edge_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- Step 4: 完整构建（一个版本）
-- ============================================================

CREATE OR REPLACE FUNCTION build_tom_network_topology(p_version_yyyyMM VARCHAR)
RETURNS TABLE (
    version_yyyyMM VARCHAR,
    node_count INT,
    edge_count INT
) AS $$
DECLARE
    v_node_count INT;
    v_edge_count INT;
BEGIN
    RAISE NOTICE 'Building topology for version %...', p_version_yyyyMM;

    -- 清空旧数据
    PERFORM clear_tom_network_topology(p_version_yyyyMM);

    -- 构建节点
    v_node_count := build_tom_network_vertices(p_version_yyyyMM);
    RAISE NOTICE '  Nodes created: %', v_node_count;

    -- 构建边
    v_edge_count := build_tom_network_edges(p_version_yyyyMM);
    RAISE NOTICE '  Edges created: %', v_edge_count;

    RETURN QUERY
    SELECT p_version_yyyyMM, v_node_count, v_edge_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- Step 5: 构建所有版本
-- ============================================================

CREATE OR REPLACE FUNCTION build_all_tom_network_topologies()
RETURNS TABLE (
    version_yyyyMM VARCHAR,
    node_count INT,
    edge_count INT
) AS $$
DECLARE
    v_version RECORD;
BEGIN
    FOR v_version IN
        SELECT DISTINCT d.version_yyyyMM
        FROM dwd_tom_noderelation d
        ORDER BY d.version_yyyyMM
    LOOP
        RETURN QUERY
        SELECT * FROM build_tom_network_topology(v_version.version_yyyyMM);
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- 验证函数创建
SELECT 'pgRouting拓扑构建函数创建完成！' AS message;
