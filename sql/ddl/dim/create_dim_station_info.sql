-- ============================================================
-- 收费站维表 DDL
-- ============================================================
-- 功能: 收费站标准维表
-- 模块: M0
-- 输入表: 外部系统的原始收费站数据
-- 输出表: dim_station_info
-- 粒度: 每个收费站一行
-- 关键字段: station_id

CREATE TABLE IF NOT EXISTS dim_station_info (
  -- 主键
  station_id VARCHAR(64) NOT NULL,

  -- 收费站属性
  station_name VARCHAR(256),
  station_type VARCHAR(32),  -- '主线站' / '匝道站' / '虚拟站'
  road_id VARCHAR(64),
  road_name VARCHAR(256),

  -- 位置
  longitude DECIMAL(10, 6),
  latitude DECIMAL(10, 6),

  -- 有效期
  valid_start_date DATE,
  valid_end_date DATE,

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_station_info PRIMARY KEY (station_id, valid_start_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_station_road ON dim_station_info(road_id);
CREATE INDEX IF NOT EXISTS idx_station_type ON dim_station_info(station_type);

COMMENT ON TABLE dim_station_info IS '收费站标准维表';
COMMENT ON COLUMN dim_station_info.station_type IS '收费站类型：主线站/匝道站/虚拟站';
