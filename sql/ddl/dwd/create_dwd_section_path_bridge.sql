-- ============================================================
-- M2: 收费单元-OD路径桥接表 DDL
-- ============================================================
-- 作用: section_id → od_section_path_id 桥接表，加速受影响OD-Path查询
-- 输入表: dwd_od_section_path_map
-- 输出表: dwd_section_path_bridge
-- 粒度: section_id × od_section_path_id × version_yyyyMM
-- 关键字段: section_id, od_section_path_id, version_yyyyMM
-- 主键: id (自增) / 业务唯一键: (section_id, od_section_path_id, version_yyyyMM)
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_section_path_bridge (
    id                BIGSERIAL PRIMARY KEY,
    section_id        VARCHAR(64)  NOT NULL,
    od_section_path_id BIGINT      NOT NULL,
    version_yyyyMM    VARCHAR(6)   NOT NULL,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_section_path_bridge
        UNIQUE (section_id, od_section_path_id, version_yyyyMM)
);

-- 核心查询索引：给定 section_id 列表，快速找到所有 od_section_path_id
CREATE INDEX IF NOT EXISTS idx_spb_section_version
    ON dwd_section_path_bridge(section_id, version_yyyyMM);

-- 反向查询索引：给定 od_section_path_id，找所有 section_id
CREATE INDEX IF NOT EXISTS idx_spb_odpath_version
    ON dwd_section_path_bridge(od_section_path_id, version_yyyyMM);

COMMENT ON TABLE dwd_section_path_bridge IS
    '收费单元-OD路径桥接表 — 从 fixed_intervalpath 展开的 section_id × od_section_path_id 映射，加速受影响OD查询';
COMMENT ON COLUMN dwd_section_path_bridge.section_id IS
    '收费单元ID，来自 fixed_intervalpath 按 | 拆分';
COMMENT ON COLUMN dwd_section_path_bridge.od_section_path_id IS
    'OD-Section-Path映射表ID，外键关联 dwd_od_section_path_map.id';
