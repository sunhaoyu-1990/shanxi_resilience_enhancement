-- ============================================================
-- M6: OD-Section-Path 映射表 DDL
-- ============================================================
-- 作用: 记录每个 (enid, exid, numpath) 组合对应的统计量最大的 fixed_intervalpath
-- 输入: Hive:gstx_exit_with_min_fee{yyyyMM} + dwd_section_path
-- 输出: dwd_od_section_path_map
-- 粒度: (enid, exid, numpath, version_yyyyMM) — 一行一个去重路径
-- 关键字段: enid, exid, numpath, fixed_intervalpath
-- 主键: id (自增) / 业务唯一键: (enid, exid, numpath, version_yyyyMM)
-- 说明: 由 freq 表统一派生（rank 计算后），不从 Python 直接写入
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_od_section_path_map (
    -- 自增主键（仅用于关联，不参与业务逻辑）
    id  BIGSERIAL PRIMARY KEY,

    -- 业务唯一键（复合唯一约束，用于 upsert）
    enid           VARCHAR(64)     NOT NULL,
    exid           VARCHAR(64)     NOT NULL,
    numpath        VARCHAR(512)    NOT NULL,
    version_yyyyMM VARCHAR(6)     NOT NULL,

    -- 修复后的路径（拓扑修复后，唯一写入的路径字段）
    fixed_intervalpath TEXT,

    intervalpath_cnt  BIGINT       DEFAULT 0,

    -- 统计
    total_trip_cnt   BIGINT       DEFAULT 0,
    path_freq_ratio  NUMERIC(5,4) DEFAULT 0,

    -- 拓扑版本（记录该数据使用的是哪个拓扑版本）
    topo_version     VARCHAR(6)   NOT NULL DEFAULT '202512',

    -- 元数据
    source_flag      VARCHAR(32)   DEFAULT 'hive_computed',
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    -- 业务唯一约束（用于 ON CONFLICT）
    CONSTRAINT uq_dwd_od_section_path_map
        UNIQUE (enid, exid, numpath, version_yyyyMM)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_odsp_enid
    ON dwd_od_section_path_map(enid);
CREATE INDEX IF NOT EXISTS idx_odsp_exid
    ON dwd_od_section_path_map(exid);
CREATE INDEX IF NOT EXISTS idx_odsp_version
    ON dwd_od_section_path_map(version_yyyyMM);
CREATE INDEX IF NOT EXISTS idx_odsp_numratio
    ON dwd_od_section_path_map(path_freq_ratio);
CREATE INDEX IF NOT EXISTS idx_odsp_topoversion
    ON dwd_od_section_path_map(topo_version);

-- 注释
COMMENT ON TABLE dwd_od_section_path_map IS
    'OD收费单元路径映射表 — 记录每个OD对下各去重路径的统计量最大修复路径（由freq表统一派生）';
COMMENT ON COLUMN dwd_od_section_path_map.id IS
    '自增主键，仅用于关联查询，不参与业务逻辑';
COMMENT ON COLUMN dwd_od_section_path_map.enid IS
    'OD起点ID，来自Hive表.enid';
COMMENT ON COLUMN dwd_od_section_path_map.exid IS
    'OD终点ID，来自Hive表.exid';
COMMENT ON COLUMN dwd_od_section_path_map.numpath IS
    '去重后的 section_number 序列，格式: "1|2|3"';
COMMENT ON COLUMN dwd_od_section_path_map.fixed_intervalpath IS
    '该 numpath 下统计量累加最大的 fixed_intervalgroup（拓扑修复后）';
COMMENT ON COLUMN dwd_od_section_path_map.intervalpath_cnt IS
    '该 fixed_intervalpath 在同一 numpath 下的统计量';
COMMENT ON COLUMN dwd_od_section_path_map.total_trip_cnt IS
    '该 (enid, exid, numpath) 组合的总通行记录数';
COMMENT ON COLUMN dwd_od_section_path_map.path_freq_ratio IS
    'intervalpath_cnt / total_trip_cnt，路径一致性比例，越接近1表示该numpath下fixed_intervalpath越一致';
COMMENT ON COLUMN dwd_od_section_path_map.topo_version IS
    '拓扑版本，用于计算 intervalgroup 的拓扑数据版本';
