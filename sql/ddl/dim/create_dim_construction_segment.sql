-- ============================================================
-- M0: Create Dimension Table - Construction Segment Info
-- ============================================================
-- 作用: 存储施工区间信息，记录每个方案下各施工区间的基本属性
-- 输入表: 外部施工方案数据（Excel/CSV 导入）
-- 输出表: dim_construction_segment
-- 粒度: project_id × scheme_id × segment_start_point × segment_end_point × construction_direction
-- 关键字段: project_id, scheme_id, segment_start_point, segment_end_point, construction_direction
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_construction_segment (
  -- 自增主键
  id                         SERIAL       NOT NULL,

  -- 业务标识字段
  project_id                 VARCHAR(20)  NOT NULL,
  scheme_id                  VARCHAR(20)  NOT NULL,
  segment_start_point        VARCHAR(50)  NOT NULL,
  segment_end_point          VARCHAR(50)  NOT NULL,
  construction_direction     INTEGER      NOT NULL,

    -- 施工属性
  lane_occupancy_count       INTEGER      NOT NULL,
  construction_duration_days INTEGER      NOT NULL,
  construction_start_time    DATE,
  restricted_vehicle_types  VARCHAR(200),

  -- 计算派生字段（由 construction_start_time + construction_duration_days 推导） 计算派生字段（由 construction_start_time + construction_duration_days 推导）
  -- PostgreSQL: DATE + INTEGER = DATE
  construction_end_time      DATE GENERATED ALWAYS AS (
    construction_start_time + construction_duration_days
  ) STORED,

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_construction_segment PRIMARY KEY (id),
  CONSTRAINT uq_dim_construction_segment UNIQUE (
    project_id, scheme_id, segment_start_point, segment_end_point, construction_direction
  ),
  CONSTRAINT chk_construction_direction CHECK (construction_direction IN (1, 2, 3)),
  CONSTRAINT chk_lane_occupancy CHECK (lane_occupancy_count >= -1),
  CONSTRAINT chk_duration_positive CHECK (construction_duration_days > 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_cst_seg_project  ON dim_construction_segment(project_id);
CREATE INDEX IF NOT EXISTS idx_cst_seg_scheme   ON dim_construction_segment(project_id, scheme_id);
CREATE INDEX IF NOT EXISTS idx_cst_seg_start    ON dim_construction_segment(construction_start_time);

-- 表与字段注释
COMMENT ON TABLE dim_construction_segment IS '施工区间维表，记录各工程方案下每个施工区间的基本属性';
COMMENT ON COLUMN dim_construction_segment.id                         IS '自增主键';
COMMENT ON COLUMN dim_construction_segment.project_id                 IS '工程 ID';
COMMENT ON COLUMN dim_construction_segment.scheme_id                  IS '方案 ID，同一工程可有多个方案';
COMMENT ON COLUMN dim_construction_segment.segment_start_point        IS '施工区间起点名称';
COMMENT ON COLUMN dim_construction_segment.segment_end_point          IS '施工区间终点名称';
COMMENT ON COLUMN dim_construction_segment.construction_direction     IS '施工方向：1-上行，2-下行，3-双向';
COMMENT ON COLUMN dim_construction_segment.lane_occupancy_count       IS '施工占用车道数，-1 表示占用全部车道';
COMMENT ON COLUMN dim_construction_segment.construction_duration_days IS '施工时长，单位：天';
COMMENT ON COLUMN dim_construction_segment.construction_start_time    IS '施工开始时间';
COMMENT ON COLUMN dim_construction_segment.construction_end_time      IS '施工结束时间（由开始时间 + 时长计算）';
COMMENT ON COLUMN dim_construction_segment.restricted_vehicle_types   IS '限制车型，1-10 分别对应1-10型车，"|"分隔多车型，-1 表示全车型限制';
