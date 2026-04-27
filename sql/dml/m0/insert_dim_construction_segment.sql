-- ============================================================
-- M0: Insert Sample Data - Construction Segment Info
-- ============================================================
-- 作用: 向 dim_construction_segment 表插入施工区间初始数据
-- 输入表: 无（直接 VALUES 插入）
-- 输出表: dim_construction_segment
-- 粒度: project_id × scheme_id × segment_start_point × segment_end_point × construction_direction
-- 关键字段: project_id, scheme_id, segment_start_point, segment_end_point, construction_direction
-- ============================================================
-- 说明:
--   construction_direction: 1-上行, 2-下行, 3-双向
--   lane_occupancy_count: -1 表示占用全部车道
--   construction_end_time 为数据库自动计算列（不需要手动插入）
-- ============================================================

INSERT INTO dim_construction_segment (
  project_id,
  scheme_id,
  segment_start_point,
  segment_end_point,
  construction_direction,
  lane_occupancy_count,
  construction_duration_days,
  construction_start_time
)
VALUES
  ('1', '1', '席家河',  '蓝田南',   3, -1, 60,  '2026-07-01'),
  ('1', '1', '蓝田南',  '麻池河',   3, -1, 120, '2026-05-01'),
  ('1', '1', '麻池河',  '闫村',     3, -1, 120, '2026-05-01'),
  ('1', '1', '闫村',    '山阳北',   3, -1, 365, '2026-01-01'),
  ('1', '1', '山阳北',  '高坝南枢纽', 3, -1, 120, '2026-05-01'),
  ('1', '1', '高坝南',  '湖北省界', 1, -1, 90,  '2026-06-01'),
  ('1', '1', '高坝南',  '湖北省界', 2, -1, 120, '2026-09-01')
ON CONFLICT ON CONSTRAINT uq_dim_construction_segment
DO NOTHING;
