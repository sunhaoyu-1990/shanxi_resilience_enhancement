-- ============================================================
-- M6: 批量运行检查点表 DDL
-- ============================================================
-- 作用: 记录每个版本的处理进度，支持断点续跑
-- 主键: (table_name, version_yyyyMM)
-- ============================================================

CREATE TABLE IF NOT EXISTS m6_checkpoint (
    -- 表标识
    table_name       VARCHAR(64)  NOT NULL,
    version_yyyyMM  VARCHAR(6)   NOT NULL,

    -- 处理进度
    batch_offset     BIGINT       NOT NULL DEFAULT 0,
    records_processed BIGINT      NOT NULL DEFAULT 0,
    last_batch_time  VARCHAR(10)  DEFAULT NULL,

    -- 状态
    status           VARCHAR(20)  NOT NULL DEFAULT 'running',
                        -- running:   运行中
                        -- completed: 已完成
                        -- failed:    失败

    -- 拓扑版本
    topo_version     VARCHAR(6)   NOT NULL DEFAULT '202512',

    -- 元数据
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    -- 主键
    CONSTRAINT pk_m6_checkpoint PRIMARY KEY (table_name, version_yyyyMM)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_m6cp_status
    ON m6_checkpoint(status);
CREATE INDEX IF NOT EXISTS idx_m6cp_version
    ON m6_checkpoint(version_yyyyMM);

-- 注释
COMMENT ON TABLE m6_checkpoint IS
    'M6批量运行检查点表 — 记录每个版本的处理进度，支持断点续跑';
COMMENT ON COLUMN m6_checkpoint.table_name IS
    'Hive表名，如 gstx_exit_with_min_fee202603';
COMMENT ON COLUMN m6_checkpoint.version_yyyyMM IS
    '版本年月（从表名提取），用于与输出表关联';
COMMENT ON COLUMN m6_checkpoint.batch_offset IS
    '已完成的最大偏移量（OFFSET值），下一批次从该值开始';
COMMENT ON COLUMN m6_checkpoint.records_processed IS
    '已处理的原始记录总数';
COMMENT ON COLUMN m6_checkpoint.last_batch_time IS
    '最后一批完成时间(HH:MI:SS)';
COMMENT ON COLUMN m6_checkpoint.status IS
    'running=运行中, completed=已完成, failed=失败';
COMMENT ON COLUMN m6_checkpoint.topo_version IS
    '该版本使用的拓扑版本（<=数据月份的最新拓扑版本）';
