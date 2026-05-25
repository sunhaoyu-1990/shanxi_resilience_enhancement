-- ============================================================
-- M8: 路径修正结果表
-- ============================================================
-- 作用: 存储路径修正后的结果，包括修正路径、质量指标、折返指标等
-- 输入表: 无（由 M8 模块直接写入）
-- 输出表: dws_path_repair_result
-- 粒度: record_id（每条通行记录一条结果）
-- 主键: record_id
-- 关键字段: record_id, corrected_path, repair_status, backtrack_index, repair_confidence
-- ============================================================

CREATE TABLE IF NOT EXISTS dws_path_repair_result (
    record_id VARCHAR(128) PRIMARY KEY,
    enid VARCHAR(64) NOT NULL,
    exid VARCHAR(64) NOT NULL,

    raw_path TEXT NOT NULL,
    corrected_path TEXT NOT NULL,

    raw_node_count INT DEFAULT 0,
    corrected_node_count INT DEFAULT 0,
    inserted_node_count INT DEFAULT 0,
    dropped_node_count INT DEFAULT 0,

    raw_match_ratio DOUBLE PRECISION DEFAULT 1.0,
    detour_ratio DOUBLE PRECISION DEFAULT 1.0,

    reverse_edge_count INT DEFAULT 0,
    backward_progress_count INT DEFAULT 0,
    backward_progress_distance DOUBLE PRECISION DEFAULT 0.0,
    u_turn_count INT DEFAULT 0,
    repeated_node_count INT DEFAULT 0,
    backtrack_index DOUBLE PRECISION DEFAULT 0.0,

    repair_confidence DOUBLE PRECISION DEFAULT 100.0,
    repair_status VARCHAR(32) DEFAULT 'HIGH_CONFIDENCE',

    repair_detail JSONB,
    corrected_geo_points JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_dws_pr_status ON dws_path_repair_result (repair_status);
CREATE INDEX IF NOT EXISTS idx_dws_pr_confidence ON dws_path_repair_result (repair_confidence);
CREATE INDEX IF NOT EXISTS idx_dws_pr_backtrack ON dws_path_repair_result (backtrack_index);
CREATE INDEX IF NOT EXISTS idx_dws_pr_enid ON dws_path_repair_result (enid);
CREATE INDEX IF NOT EXISTS idx_dws_pr_exid ON dws_path_repair_result (exid);

COMMENT ON TABLE dws_path_repair_result IS 'M8 路径修正结果表';
COMMENT ON COLUMN dws_path_repair_result.record_id IS '通行记录唯一标识';
COMMENT ON COLUMN dws_path_repair_result.enid IS '入口节点ID';
COMMENT ON COLUMN dws_path_repair_result.exid IS '出口节点ID';
COMMENT ON COLUMN dws_path_repair_result.raw_path IS '原始路径（|分隔）';
COMMENT ON COLUMN dws_path_repair_result.corrected_path IS '修正后路径（|分隔）';
COMMENT ON COLUMN dws_path_repair_result.raw_match_ratio IS '原始节点匹配率';
COMMENT ON COLUMN dws_path_repair_result.detour_ratio IS '绕行比 = 修正路径长度 / 起终点最短路长度';
COMMENT ON COLUMN dws_path_repair_result.backtrack_index IS '综合折返指数 0-100';
COMMENT ON COLUMN dws_path_repair_result.repair_confidence IS '修正置信度 0-100';
COMMENT ON COLUMN dws_path_repair_result.repair_status IS '修正状态: HIGH/MEDIUM/LOW/NEED_REVIEW/FAILED';
COMMENT ON COLUMN dws_path_repair_result.repair_detail IS '修正详情 JSONB';
COMMENT ON COLUMN dws_path_repair_result.corrected_geo_points IS '修正后经纬度序列 JSONB';
