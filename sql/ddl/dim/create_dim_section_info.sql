-- ============================================================
-- 收费单元维表 DDL
-- ============================================================
-- 功能: 收费单元标准维表
-- 模块: M0
-- 输入表: 外部系统的原始收费单元数据
-- 输出表: dim_section_info
-- 粒度: 每个收费单元一行
-- 关键字段: section_id, section_number

-- TODO: 与数据团队确认实际表结构
-- TODO: 确认 section_number 分配规则

CREATE TABLE IF NOT EXISTS dim_section_info (
  -- 主键
  section_id VARCHAR(64) NOT NULL,

  -- 收费单元属性
  section_name VARCHAR(256),
  road_id VARCHAR(64),
  road_name VARCHAR(256),
  direction VARCHAR(32),  -- '上行' / '下行' / '双向'

  -- 位置信息
  start_station_id VARCHAR(64),
  end_station_id VARCHAR(64),

  -- 通行能力信息
  lane_cnt INTEGER DEFAULT 0,
  section_number VARCHAR(64),  -- 重要：同一路径上的收费单元共享相同编号

  -- 有效期（用于历史版本）
  valid_start_date DATE,
  valid_end_date DATE,

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_section_info PRIMARY KEY (section_id, valid_start_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_section_road ON dim_section_info(road_id);
CREATE INDEX IF NOT EXISTS idx_section_number ON dim_section_info(section_number);
CREATE INDEX IF NOT EXISTS idx_section_direction ON dim_section_info(direction);
CREATE INDEX IF NOT EXISTS idx_section_validity ON dim_section_info(valid_start_date, valid_end_date);

-- 注释
COMMENT ON TABLE dim_section_info IS '收费单元标准维表 - 全项目收费单元统一主数据来源';
COMMENT ON COLUMN dim_section_info.section_number IS '同一单一路径上的收费单元归属同一编号，用于路径归并和收费单元映射';
COMMENT ON COLUMN dim_section_info.lane_cnt IS '收费单元标准车道数';
