-- ============================================================
-- DDL: dim_tom_noderelation_version
-- ============================================================
-- 作用: 高速路网拓扑结构版本配置表
-- 输入: 无
-- 输出: 无
-- 粒度: 版本年月 (YYYYMM)
-- 关键字段: version_yyyyMM, effect_date, file_path
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_tom_noderelation_version (
    version_yyyyMM VARCHAR(6) NOT NULL,
    effect_date DATE NOT NULL,
    file_path VARCHAR(256) NOT NULL,
    description VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dim_tom_noderelation_version PRIMARY KEY (version_yyyyMM)
);

COMMENT ON TABLE dim_tom_noderelation_version IS '高速路网拓扑结构版本配置表';
COMMENT ON COLUMN dim_tom_noderelation_version.version_yyyyMM IS '版本年月（YYYYMM）';
COMMENT ON COLUMN dim_tom_noderelation_version.effect_date IS '生效日期';
COMMENT ON COLUMN dim_tom_noderelation_version.file_path IS '文件路径';
COMMENT ON COLUMN dim_tom_noderelation_version.description IS '说明';

-- ============================================================
-- 初始化版本配置数据
-- ============================================================

INSERT INTO dim_tom_noderelation_version
    (version_yyyyMM, effect_date, file_path, description)
VALUES
    ('202312', '2023-12-01', 'research/data/基础数据/2024-2026年高速路网拓扑结构表/tom_noderelation202312.csv', '2023年12月起生效'),
    ('202409', '2024-09-01', 'research/data/基础数据/2024-2026年高速路网拓扑结构表/tom_noderelation202409.csv', '2024年9月起生效'),
    ('202411', '2024-11-01', 'research/data/基础数据/2024-2026年高速路网拓扑结构表/tom_noderelation202411.csv', '2024年11月起生效'),
    ('202507', '2025-07-01', 'research/data/基础数据/2024-2026年高速路网拓扑结构表/tom_noderelation202507.csv', '2025年7月起生效'),
    ('202512', '2025-12-01', 'research/data/基础数据/2024-2026年高速路网拓扑结构表/tom_noderelation202512.csv', '2025年12月起生效'),
    ('202603', '2026-03-01', 'research/data/基础数据/2024-2026年高速路网拓扑结构表/tom_noderelation202603.csv', '2026年3月起生效')
ON CONFLICT (version_yyyyMM) DO NOTHING;