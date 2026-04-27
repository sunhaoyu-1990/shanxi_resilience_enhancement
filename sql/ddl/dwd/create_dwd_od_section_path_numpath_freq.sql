-- ============================================================
-- M6: numPath → fixed_intervalgroup 频率映射表 DDL
-- ============================================================
-- 作用: 记录每个 (enid, exid, numpath) 下各 fixed_intervalgroup 的统计量
-- 输入: 内存聚合结果（Python侧写入）
-- 输出: dwd_od_section_path_numpath_freq
-- 粒度: (enid, exid, numpath, fixed_intervalgroup, version_yyyyMM, topo_version) — 一行一种组合
-- 关键字段: enid, exid, numpath, fixed_intervalgroup, ig_count
-- 主键: id (自增) / 业务唯一键: (enid, exid, numpath, fixed_intervalgroup, version_yyyyMM, topo_version)
-- 说明: 每批实时 upsert 累加 ig_count，rank 由 rank 计算 SQL 统一派生
-- ============================================================

CREATE TABLE IF NOT EXISTS dwd_od_section_path_numpath_freq (
    -- 自增主键（仅用于关联，不参与业务逻辑）
    id  BIGSERIAL PRIMARY KEY,

    -- 业务唯一键
    enid           VARCHAR(64)  NOT NULL,
    exid           VARCHAR(64)  NOT NULL,
    numpath        VARCHAR(512) NOT NULL,
    fixed_intervalgroup TEXT    NOT NULL,
    version_yyyyMM VARCHAR(6)  NOT NULL,
    topo_version   VARCHAR(6)  NOT NULL DEFAULT '202512',

    -- 频率统计
    ig_count       BIGINT      DEFAULT 0,
    ig_rank        INT         DEFAULT 0,

    -- 元数据
    source_flag    VARCHAR(32) DEFAULT 'hive_computed',
    created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,

    -- 业务唯一约束（用于 ON CONFLICT）
    CONSTRAINT uq_dwd_od_section_path_numpath_freq
        UNIQUE (enid, exid, numpath, fixed_intervalgroup, version_yyyyMM, topo_version)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_odspf_enid
    ON dwd_od_section_path_numpath_freq(enid);
CREATE INDEX IF NOT EXISTS idx_odspf_exid
    ON dwd_od_section_path_numpath_freq(exid);
CREATE INDEX IF NOT EXISTS idx_odspf_numpath
    ON dwd_od_section_path_numpath_freq(numpath);
CREATE INDEX IF NOT EXISTS idx_odspf_version
    ON dwd_od_section_path_numpath_freq(version_yyyyMM);
CREATE INDEX IF NOT EXISTS idx_odspf_topoversion
    ON dwd_od_section_path_numpath_freq(topo_version);

-- 注释
COMMENT ON TABLE dwd_od_section_path_numpath_freq IS
    'numPath到fixed_intervalgroup频率映射表 — 记录每个去重路径下各修复后收费单元序列的统计量（每批实时upsert累加）';
COMMENT ON COLUMN dwd_od_section_path_numpath_freq.id IS
    '自增主键，仅用于关联查询，不参与业务逻辑';
COMMENT ON COLUMN dwd_od_section_path_numpath_freq.numpath IS
    '去重后的 section_number 序列';
COMMENT ON COLUMN dwd_od_section_path_numpath_freq.fixed_intervalgroup IS
    '修复后的 intervalgroup（拓扑修复后）';
COMMENT ON COLUMN dwd_od_section_path_numpath_freq.topo_version IS
    '拓扑版本，用于计算 intervalgroup 的拓扑数据版本';
COMMENT ON COLUMN dwd_od_section_path_numpath_freq.ig_count IS
    '该 fixed_intervalgroup 在此 numpath 下的统计量（每批累加）';
COMMENT ON COLUMN dwd_od_section_path_numpath_freq.ig_rank IS
    '在同numPath下按ig_count降序排名的序号，1为统计量最大（由rank计算SQL统一派生）';
