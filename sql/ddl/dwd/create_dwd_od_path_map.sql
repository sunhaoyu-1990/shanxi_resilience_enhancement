-- ============================================================
-- OD路径映射表 DDL
-- ============================================================
-- 功能: OD与路径映射关系
-- 模块: M0
-- 输入表: 历史通行数据 + 路径识别
-- 输出表: dwd_od_path_map
-- 粒度: 每个（OD × 路径）组合一行
-- 关键字段: od_id, path_id

-- TODO: 确认 path_sections 格式（JSON数组或分隔字符串）
-- TODO: 确认 path_id 生成规则

CREATE TABLE IF NOT EXISTS dwd_od_path_map (
  -- 主键组成部分
  od_id VARCHAR(128) NOT NULL,
  path_id VARCHAR(128) NOT NULL,

  -- OD信息
  entry_station_id VARCHAR(64) NOT NULL,
  exit_station_id VARCHAR(64) NOT NULL,

  -- 路径信息
  path_sections TEXT,  -- 收费单元ID有序数组的JSON格式，如：'["SEC001", "SEC002", "SEC003"]'
  section_count INTEGER,

  -- 路径属性
  mileage DECIMAL(10, 2),  -- 总里程（km）
  fee DECIMAL(10, 2),  -- 通行费（元）
  jk_fee DECIMAL(10, 2),  -- 监控费（元）

  -- 数据质量
  source_flag VARCHAR(32) DEFAULT 'api',  -- 'actual' / 'filled' / 'rule' / 'api'
  confidence DECIMAL(5, 4),  -- 置信度 0-1

  -- 有效期
  valid_start_date DATE,
  valid_end_date DATE,

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dwd_od_path_map PRIMARY KEY (od_id, path_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_od_path_entry ON dwd_od_path_map(entry_station_id);
CREATE INDEX IF NOT EXISTS idx_od_path_exit ON dwd_od_path_map(exit_station_id);
CREATE INDEX IF NOT EXISTS idx_od_path_source ON dwd_od_path_map(source_flag);
CREATE INDEX IF NOT EXISTS idx_od_path_validity ON dwd_od_path_map(valid_start_date, valid_end_date);

COMMENT ON TABLE dwd_od_path_map IS 'OD与路径映射关系标准表';
COMMENT ON COLUMN dwd_od_path_map.path_sections IS '路径经过的收费单元序列，JSON数组格式';
