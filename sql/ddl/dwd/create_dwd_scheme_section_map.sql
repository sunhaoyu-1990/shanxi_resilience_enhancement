-- ============================================================
-- 施工方案收费单元映射表 DDL
-- ============================================================
-- 功能: 施工方案与受影响收费单元的映射关系
-- 模块: M0
-- 输入表: 方案信息 + 收费单元信息
-- 输出表: dwd_scheme_section_map
-- 粒度: 每个（方案 × 收费单元 × 有效期）组合一行
-- 关键字段: scheme_id, section_id, valid_start_date

-- TODO: 确认 construction_mode 枚举值
-- TODO: 确认 lane_occupied_cnt 逻辑

CREATE TABLE IF NOT EXISTS dwd_scheme_section_map (
  -- 主键组成部分
  scheme_id VARCHAR(64) NOT NULL,
  section_id VARCHAR(64) NOT NULL,
  valid_start_date DATE NOT NULL,

  -- 施工详情
  lane_occupied_cnt INTEGER DEFAULT 0,  -- 施工期间占用车道数
  construction_mode VARCHAR(64),  -- 'single_lane' / 'double_lane' / 'hard_shoulder' / 'full_closure'
  speed_limit INTEGER,  -- 临时限速值（km/h）
  distance_limit INTEGER,  -- 最小跟车距离（m）

  -- 施工窗口
  valid_end_date DATE,

  -- 影响等级
  impact_level VARCHAR(32) DEFAULT 'medium',  -- 'low' / 'medium' / 'high' / 'severe'

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dwd_scheme_section_map PRIMARY KEY (
    scheme_id, section_id, valid_start_date
  ),
  CONSTRAINT chk_lane_occupied CHECK (lane_occupied_cnt >= 0),
  CONSTRAINT chk_dates_order CHECK (valid_end_date >= valid_start_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_scheme_map_scheme ON dwd_scheme_section_map(scheme_id);
CREATE INDEX IF NOT EXISTS idx_scheme_map_section ON dwd_scheme_section_map(section_id);
CREATE INDEX IF NOT EXISTS idx_scheme_map_validity ON dwd_scheme_section_map(valid_start_date, valid_end_date);

COMMENT ON TABLE dwd_scheme_section_map IS '施工方案与收费单元映射表';
COMMENT ON COLUMN dwd_scheme_section_map.lane_occupied_cnt IS '施工期间占用车道数';
