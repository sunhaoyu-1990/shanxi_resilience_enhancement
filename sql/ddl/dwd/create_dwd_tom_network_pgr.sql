-- ============================================================
-- DDL: pgRouting 拓扑表
-- ============================================================
-- 作用: 为pgRouting创建路网拓扑结构表
-- 输入表: dwd_tom_noderelation
-- 输出表: dwd_tom_network_edges, dwd_tom_network_vertices
-- 粒度: 边（edge）
-- 关键字段: id, source, target, cost, version_yyyyMM
-- ============================================================

-- ============================================================
-- 1. 创建节点映射表（原始节点ID → pgRouting BIGINT）
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_tom_network_vertices (
    id BIGSERIAL,
    original_node_id VARCHAR(32) NOT NULL,
    version_yyyyMM VARCHAR(6) NOT NULL,
    node_type INT NULL,
    node_name VARCHAR(100) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dwd_tom_network_vertices PRIMARY KEY (id),
    CONSTRAINT uq_dwd_tom_network_vertices UNIQUE (original_node_id, version_yyyyMM)
);

COMMENT ON TABLE dwd_tom_network_vertices IS 'pgRouting路网节点映射表';
COMMENT ON COLUMN dwd_tom_network_vertices.id IS 'pgRouting节点ID';
COMMENT ON COLUMN dwd_tom_network_vertices.original_node_id IS '原始节点ID（enRoadNodeId/exRoadNodeId）';
COMMENT ON COLUMN dwd_tom_network_vertices.version_yyyyMM IS '版本年月';


-- ============================================================
-- 2. 创建边表（pgRouting格式）
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_tom_network_edges (
    id BIGSERIAL,
    source BIGINT NOT NULL,
    target BIGINT NOT NULL,
    cost FLOAT NOT NULL,
    reverse_cost FLOAT NOT NULL,
    version_yyyyMM VARCHAR(6) NOT NULL,
    original_enRoadNodeId VARCHAR(32) NULL,
    original_exRoadNodeId VARCHAR(32) NULL,
    enroadNodeType INT NULL,
    exroadNodeType INT NULL,
    enRoadNodeName VARCHAR(100) NULL,
    exRoadNodeName VARCHAR(100) NULL,
    miles INT NULL,
    source_flag VARCHAR(16) DEFAULT 'computed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dwd_tom_network_edges PRIMARY KEY (id),
    CONSTRAINT fk_dwd_tom_network_edges_source FOREIGN KEY (source)
        REFERENCES dwd_tom_network_vertices(id),
    CONSTRAINT fk_dwd_tom_network_edges_target FOREIGN KEY (target)
        REFERENCES dwd_tom_network_vertices(id)
);

COMMENT ON TABLE dwd_tom_network_edges IS 'pgRouting路网边表';
COMMENT ON COLUMN dwd_tom_network_edges.id IS 'pgRouting边ID';
COMMENT ON COLUMN dwd_tom_network_edges.source IS '起点节点ID（pgRouting内部）';
COMMENT ON COLUMN dwd_tom_network_edges.target IS '终点节点ID（pgRouting内部）';
COMMENT ON COLUMN dwd_tom_network_edges.cost IS '正向代价（里程）';
COMMENT ON COLUMN dwd_tom_network_edges.reverse_cost IS '反向代价（单向路网设为1e9）';


-- ============================================================
-- 3. 创建索引
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_dwd_tom_network_edges_version
ON dwd_tom_network_edges(version_yyyyMM);

CREATE INDEX IF NOT EXISTS idx_dwd_tom_network_edges_source
ON dwd_tom_network_edges(source);

CREATE INDEX IF NOT EXISTS idx_dwd_tom_network_edges_target
ON dwd_tom_network_edges(target);

CREATE INDEX IF NOT EXISTS idx_dwd_tom_network_vertices_version
ON dwd_tom_network_vertices(version_yyyyMM);

CREATE INDEX IF NOT EXISTS idx_dwd_tom_network_vertices_original
ON dwd_tom_network_vertices(original_node_id);
