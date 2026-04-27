-- ============================================================
-- 单次通行明细表 DDL
-- ============================================================
-- 功能: 标准化的单次通行记录
-- 模块: M0
-- 输入表: 收费系统的原始通行数据
-- 输出表: dwd_single_trip_info
-- 粒度: 每条通行记录一行
-- 关键字段: trip_id

-- TODO: 确认 vehicle_type 枚举
-- TODO: 确认 path_id 生成规则

CREATE TABLE IF NOT EXISTS dwd_single_trip_info (
  -- 主键
  trip_id VARCHAR(128) NOT NULL,

  -- 车辆信息
  vehicle_id VARCHAR(64),
  vehicle_type VARCHAR(32),

  -- 收费站信息
  entry_station_id VARCHAR(64),
  exit_station_id VARCHAR(64),
  entry_station_name VARCHAR(256),
  exit_station_name VARCHAR(256),

  -- 时间信息
  entry_time TIMESTAMP NOT NULL,
  exit_time TIMESTAMP,

  -- 路径信息
  path_id VARCHAR(64),

  -- 费用信息
  fee_amount DECIMAL(10, 2) DEFAULT 0,
  mileage DECIMAL(10, 2) DEFAULT 0,

  -- 数据质量
  data_status VARCHAR(32) DEFAULT 'valid',  -- 'valid' / 'invalid' / 'suspect'

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dwd_single_trip_info PRIMARY KEY (trip_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_trip_entry_station ON dwd_single_trip_info(entry_station_id);
CREATE INDEX IF NOT EXISTS idx_trip_exit_station ON dwd_single_trip_info(exit_station_id);
CREATE INDEX IF NOT EXISTS idx_trip_entry_time ON dwd_single_trip_info(entry_time);
CREATE INDEX IF NOT EXISTS idx_trip_vehicle_type ON dwd_single_trip_info(vehicle_type);
CREATE INDEX IF NOT EXISTS idx_trip_path ON dwd_single_trip_info(path_id);

-- 分区建议（针对大数据量）
-- PARTITION BY RANGE (entry_time)

COMMENT ON TABLE dwd_single_trip_info IS '单次通行标准明细表';
COMMENT ON COLUMN dwd_single_trip_info.vehicle_type IS '车型：passenger_small/medium/large, truck_small/medium/large/oversize, bus, other';
