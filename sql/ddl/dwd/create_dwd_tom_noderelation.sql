-- ============================================================
-- DDL: dwd_tom_noderelation
-- ============================================================
-- 作用: 高速路网拓扑结构明细表
-- 输入: 各版本的 tom_noderelation CSV 文件
-- 输出: 无
-- 粒度: 自增 id
-- 关键字段: id, version_yyyyMM, enRoadNodeId, exRoadNodeId
-- ============================================================
-- 数据字典: research/data/基础数据/2024-2026年高速路网拓扑结构表/数据字典.xlsx
-- 各版本数据量:
--   - 202312: 待统计
--   - 202409: 待统计
--   - 202411: 待统计
--   - 202507: 待统计
--   - 202512: 待统计
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_tom_noderelation (
    id SERIAL,
    version VARCHAR(20) NULL,
    version_yyyyMM VARCHAR(6) NOT NULL,
    enRoadNodeId VARCHAR(32) NULL,
    enroadNodeType INT NULL,
    enRoadNodeName VARCHAR(100) NULL,
    enStationID VARCHAR(32) NULL,
    enHEX VARCHAR(16) NULL,
    exRoadNodeId VARCHAR(32) NULL,
    exroadNodeType INT NULL,
    exRoadNodeName VARCHAR(100) NULL,
    exStationID VARCHAR(32) NULL,
    exHEX VARCHAR(16) NULL,
    miles INT NULL,
    source_flag VARCHAR(16) DEFAULT 'actual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dwd_tom_noderelation PRIMARY KEY (id)
);

COMMENT ON TABLE dwd_tom_noderelation IS '高速路网拓扑结构明细表';
COMMENT ON COLUMN dwd_tom_noderelation.id IS '自增主键';
COMMENT ON COLUMN dwd_tom_noderelation.version IS '版本号（2位省域编码+YYYYMMDD+3位顺序码）';
COMMENT ON COLUMN dwd_tom_noderelation.version_yyyyMM IS '版本年月（YYYYMM）';
COMMENT ON COLUMN dwd_tom_noderelation.enRoadNodeId IS '入口节点编号';
COMMENT ON COLUMN dwd_tom_noderelation.enroadNodeType IS '入口节点类型:1-普通收费单元,2-省界收费单元,3-收费站';
COMMENT ON COLUMN dwd_tom_noderelation.enRoadNodeName IS '入口节点名称';
COMMENT ON COLUMN dwd_tom_noderelation.enStationID IS '入口站点原代码（收费站必填，收费单元16位编码）';
COMMENT ON COLUMN dwd_tom_noderelation.enHEX IS '入口节点HEX码（收费站8位，收费单元6位）';
COMMENT ON COLUMN dwd_tom_noderelation.exRoadNodeId IS '出口节点编号';
COMMENT ON COLUMN dwd_tom_noderelation.exroadNodeType IS '出口节点类型:1-普通收费单元,2-省界收费单元,3-收费站';
COMMENT ON COLUMN dwd_tom_noderelation.exRoadNodeName IS '出口节点名称';
COMMENT ON COLUMN dwd_tom_noderelation.exStationID IS '出口站点原代码（收费站必填，收费单元16位编码）';
COMMENT ON COLUMN dwd_tom_noderelation.exHEX IS '出口节点HEX码（收费站8位，收费单元6位）';
COMMENT ON COLUMN dwd_tom_noderelation.miles IS '里程(米)';
COMMENT ON COLUMN dwd_tom_noderelation.source_flag IS '数据来源标识（actual/filled/rule/api/computed）';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_dwd_tom_noderelation_version ON dwd_tom_noderelation(version_yyyyMM);
CREATE INDEX IF NOT EXISTS idx_dwd_tom_noderelation_en_node ON dwd_tom_noderelation(enRoadNodeId, enroadNodeType);
CREATE INDEX IF NOT EXISTS idx_dwd_tom_noderelation_ex_node ON dwd_tom_noderelation(exRoadNodeId, exroadNodeType);