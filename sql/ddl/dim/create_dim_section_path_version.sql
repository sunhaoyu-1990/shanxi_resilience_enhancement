-- ============================================================
-- DDL: dim_section_path_version
-- ============================================================
-- 作用: 收费单元唯一路径版本配置表
-- 输入: 无
-- 输出: 无
-- 粒度: 版本年月 (YYYYMM)
-- 关键字段: version_yyyyMM, effect_date, file_path
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_section_path_version (
    version_yyyyMM VARCHAR(6) NOT NULL,
    effect_date DATE NOT NULL,
    file_path VARCHAR(256) NOT NULL,
    description VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_dim_section_path_version PRIMARY KEY (version_yyyyMM)
);

COMMENT ON TABLE dim_section_path_version IS '收费单元唯一路径版本配置表';
COMMENT ON COLUMN dim_section_path_version.version_yyyyMM IS '版本年月（YYYYMM）';
COMMENT ON COLUMN dim_section_path_version.effect_date IS '生效日期';
COMMENT ON COLUMN dim_section_path_version.file_path IS '文件路径';
COMMENT ON COLUMN dim_section_path_version.description IS '说明';

-- ============================================================
-- 初始化版本配置数据
-- ============================================================

INSERT INTO dim_section_path_version
    (version_yyyyMM, effect_date, file_path, description)
VALUES
    ('202401', '2024-01-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202401单元唯一路径.xlsx', '2024年1月起生效'),
    ('202409', '2024-09-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202409单元唯一路径.xlsx', '2024年9月起生效'),
    ('202412', '2024-12-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202412单元唯一路径.xlsx', '2024年12月起生效'),
    ('202507', '2025-07-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202507单元唯一路径.xlsx', '2025年7月起生效'),
    ('202512', '2025-12-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202512单元唯一路径.xlsx', '2025年12月起生效'),
    ('202603', '2026-03-01', 'research/data/基础数据/2024-2026年收费单元唯一路径/202603单元唯一路径.xlsx', '2026年3月起生效')
ON CONFLICT (version_yyyyMM) DO UPDATE SET
    effect_date = EXCLUDED.effect_date,
    file_path = EXCLUDED.file_path,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;
