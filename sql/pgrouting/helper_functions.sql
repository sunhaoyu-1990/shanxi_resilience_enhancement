-- ============================================================
-- pgRouting: 辅助查询函数
-- ============================================================
-- 作用: 相邻节点查询等辅助功能
-- 输入表: dwd_tom_noderelation
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
        d.exRoadNodeId AS section_id,
        d.exRoadNodeName AS section_name,
        d.exroadNodeType AS section_type,
        d.miles
    FROM dwd_tom_noderelation d
    WHERE d.enRoadNodeId = p_section_id
      AND d.version_yyyyMM = p_version_yyyyMM;
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
        d.enRoadNodeId AS section_id,
        d.enRoadNodeName AS section_name,
        d.enroadNodeType AS section_type,
        d.miles
    FROM dwd_tom_noderelation d
    WHERE d.exRoadNodeId = p_section_id
      AND d.version_yyyyMM = p_version_yyyyMM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_prev_sections(VARCHAR, VARCHAR)
IS '获取指定收费单元的上一个单元';


-- 验证函数创建
SELECT '辅助查询函数创建完成！' AS message;