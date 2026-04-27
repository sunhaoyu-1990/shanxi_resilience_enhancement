-- ============================================================
-- 收费单元路网拓扑表 DDL
-- ============================================================
-- 功能: 收费单元之间的路网拓扑关系
-- 模块: M0
-- 输入表: 原始拓扑数据
-- 输出表: dim_road_topology
-- 粒度: 每个收费单元对关系一行
-- 关键字段: from_section_id, to_section_id, valid_start_date

-- TODO: 确认 relation_type 枚举值
-- TODO: 确认方向处理方式

CREATE TABLE IF NOT EXISTS dim_road_topology (
  -- 收费单元对关系
  from_section_id VARCHAR(64) NOT NULL,
  to_section_id VARCHAR(64) NOT NULL,

  -- 关系类型
  relation_type VARCHAR(32) DEFAULT 'next',  -- 'next' / 'merge' / 'split' / 'interchange' / 'ramp_on' / 'ramp_off'

  -- 道路信息
  road_id VARCHAR(64),
  direction VARCHAR(32),

  -- 有效期
  valid_start_date DATE,
  valid_end_date DATE,

  -- 元数据
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  -- 约束
  CONSTRAINT pk_dim_road_topology PRIMARY KEY (
    from_section_id, to_section_id, valid_start_date
  ),

  -- 防止明显的自环
  CONSTRAINT chk_no_self_loop CHECK (from_section_id != to_section_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_topology_from ON dim_road_topology(from_section_id);
CREATE INDEX IF NOT EXISTS idx_topology_to ON dim_road_topology(to_section_id);
CREATE INDEX IF NOT EXISTS idx_topology_road ON dim_road_topology(road_id);
CREATE INDEX IF NOT EXISTS idx_topology_relation ON dim_road_topology(relation_type);

COMMENT ON TABLE dim_road_topology IS '收费单元路网拓扑关系表';
COMMENT ON COLUMN dim_road_topology.from_section_id IS '本收费单元ID';
COMMENT ON COLUMN dim_road_topology.to_section_id IS '下一个收费单元ID（一对多关系）';
