-- ============================================================
-- 施工方案维表 DDL
-- ============================================================
-- 功能: 施工方案主表
-- 模块: M0
-- 输入表: 施工方案数据
-- 输出表: dim_scheme_info
-- 粒度: 每个方案一行
-- 关键字段: scheme_id

-- TODO: 确认方案状态枚举值
-- TODO: 确认项目编号格式

CREATE TABLE IF NOT EXISTS dim_scheme_info (
  -- 主键
  scheme_id VARCHAR(64) NOT NULL,

  -- 方案属性
  scheme_name VARCHAR(256),
  project_code VARCHAR(64),
  project_name VARCHAR(256),

  -- 时间范围
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,

  -- 状态
  scheme_status VARCHAR(32) DEFAULT 'draft',  -- 'draft' / 'approved' / 'in_progress' / 'completed' / 'cancelled'

  -- 描述
  description TEXT,

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_scheme_info PRIMARY KEY (scheme_id),
  CONSTRAINT chk_scheme_dates CHECK (end_date >= start_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_scheme_project ON dim_scheme_info(project_code);
CREATE INDEX IF NOT EXISTS idx_scheme_status ON dim_scheme_info(scheme_status);
CREATE INDEX IF NOT EXISTS idx_scheme_dates ON dim_scheme_info(start_date, end_date);

COMMENT ON TABLE dim_scheme_info IS '施工方案主表';
COMMENT ON COLUMN dim_scheme_info.scheme_status IS '施工方案状态：draft/approved/in_progress/completed/cancelled';
